from __future__ import annotations

from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.audit import record_event
from app.db import get_primary_engine
from app.services.microscopy_analysis import AnalysisError, MicroscopyAnalysisService


class QualityQueueService:
    engine = get_primary_engine()

    @staticmethod
    def _safe_error(exc: Exception) -> tuple[str, str]:
        if isinstance(exc, AnalysisError):
            return "QUALITY_ASSESSMENT_REJECTED", str(exc.detail)[:500]
        return "QUALITY_ASSESSMENT_FAILED", "El control técnico no pudo completarse."

    @staticmethod
    def _audit(connection, event_type, action, item, principal, request, error_code=None):
        state = {key: str(item[key]) if key in ("id", "analysis_run_id", "requested_by") else item[key]
                 for key in ("id", "analysis_run_id", "priority", "status", "attempt_count", "requested_by")}
        record_event(event_type=event_type, action=action, principal=principal, request=request,
                     success=event_type != "scientific.quality_queue.failed", error_code=error_code,
                     connection=connection, resource_type="quality_assessment_queue_item",
                     resource_id=str(item["id"]), after_state=state)

    def enqueue(self, run_id, priority, principal, request):
        try:
            with self.engine.begin() as connection:
                run = connection.execute(text("""
                  SELECT id,run_status FROM microscopy_analysis_runs
                  WHERE id=CAST(:id AS uuid) FOR SHARE
                """), {"id": str(run_id)}).mappings().first()
                if not run:
                    raise AnalysisError(404, "Ejecución inexistente.")
                if run["run_status"] not in ("created", "quality_pending"):
                    raise AnalysisError(409, "La ejecución no admite control de calidad.")
                item = connection.execute(text("""
                  INSERT INTO quality_assessment_queue_items(id,analysis_run_id,priority,requested_by)
                  VALUES(:id,:run,:priority,CAST(:actor AS uuid)) RETURNING *
                """), {"id": uuid4(), "run": run["id"], "priority": priority,
                       "actor": principal.user_id}).mappings().one()
                self._audit(connection, "scientific.quality_queue.enqueued", "enqueue",
                            item, principal, request)
                return dict(item)
        except IntegrityError as exc:
            raise AnalysisError(409, "Ya existe una solicitud activa para esta ejecución.") from exc

    def list(self, limit=50, offset=0, **filters):
        clauses, params = [], {"limit": limit, "offset": offset}
        for key, expression in (
            ("status", "q.status=:status"), ("priority", "q.priority=:priority"),
            ("run_code", "r.run_code ILIKE :run_code"),
            ("subject_code", "rs.subject_code ILIKE :subject_code"),
            ("sample_code", "bs.sample_code ILIKE :sample_code"),
        ):
            value = filters.get(key)
            if value is not None and value != "":
                clauses.append(expression)
                params[key] = f"%{value}%" if key.endswith("_code") else value
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        base = f"""FROM quality_assessment_queue_items q
          JOIN microscopy_analysis_runs r ON r.id=q.analysis_run_id
          JOIN research_subjects rs ON rs.id=r.subject_id
          JOIN blood_samples bs ON bs.id=r.sample_id
          JOIN users u ON u.id=q.requested_by {where}"""
        with self.engine.connect() as connection:
            rows = connection.execute(text(f"""SELECT q.id queue_item_id,q.analysis_run_id,
              r.run_code,rs.subject_code,bs.sample_code,q.priority,q.status,q.attempt_count,
              q.requested_by,u.username requested_by_username,q.requested_at,q.started_at,
              q.completed_at,q.failed_at,q.last_error_message {base}
              ORDER BY q.priority DESC,q.requested_at ASC,q.id ASC LIMIT :limit OFFSET :offset"""),
              params).mappings().all()
            total = connection.execute(text(f"SELECT count(*) {base}"), params).scalar_one()
        return {"items": [dict(row) for row in rows], "total": total, "limit": limit, "offset": offset}

    def claim(self, item_id, principal, request):
        with self.engine.begin() as connection:
            item = connection.execute(text("""SELECT * FROM quality_assessment_queue_items
              WHERE id=CAST(:id AS uuid) FOR UPDATE"""), {"id": str(item_id)}).mappings().first()
            if not item:
                raise AnalysisError(404, "Solicitud inexistente.")
            if item["status"] != "queued":
                raise AnalysisError(409, "Solo puede ejecutarse una solicitud en cola.")
            item = connection.execute(text("""UPDATE quality_assessment_queue_items
              SET status='running',attempt_count=attempt_count+1,started_at=now(),
                  completed_at=NULL,failed_at=NULL,updated_at=now()
              WHERE id=:id RETURNING *"""), {"id": item["id"]}).mappings().one()
            self._audit(connection, "scientific.quality_queue.started", "execute", item, principal, request)
            return dict(item)

    def complete(self, item_id, principal, request):
        with self.engine.begin() as connection:
            item = connection.execute(text("""UPDATE quality_assessment_queue_items
              SET status='completed',completed_at=now(),failed_at=NULL,last_error_code=NULL,
                  last_error_message=NULL,updated_at=now() WHERE id=:id AND status='running'
              RETURNING *"""), {"id": item_id}).mappings().one()
            self._audit(connection, "scientific.quality_queue.completed", "execute", item, principal, request)
            return dict(item)

    def fail(self, item_id, exc, principal, request):
        code, message = self._safe_error(exc)
        with self.engine.begin() as connection:
            item = connection.execute(text("""UPDATE quality_assessment_queue_items
              SET status='failed',failed_at=now(),completed_at=NULL,last_error_code=:code,
                  last_error_message=:message,updated_at=now()
              WHERE id=:id AND status='running' RETURNING *"""),
              {"id": item_id, "code": code, "message": message}).mappings().one()
            self._audit(connection, "scientific.quality_queue.failed", "execute",
                        item, principal, request, code)
            return dict(item)

    def execute(self, item_id, principal, request):
        item = self.claim(item_id, principal, request)
        analysis = MicroscopyAnalysisService()
        try:
            run, results = analysis.measurements(str(item["analysis_run_id"]))
            analysis.persist_measurements(run, results, principal, request)
        except Exception as exc:
            self.fail(item["id"], exc, principal, request)
            if isinstance(exc, AnalysisError):
                raise
            raise AnalysisError(500, "El control técnico no pudo completarse.") from exc
        return self.complete(item["id"], principal, request)

    def retry(self, item_id, priority, principal, request):
        with self.engine.begin() as connection:
            item = connection.execute(text("""SELECT * FROM quality_assessment_queue_items
              WHERE id=CAST(:id AS uuid) FOR UPDATE"""), {"id": str(item_id)}).mappings().first()
            if not item:
                raise AnalysisError(404, "Solicitud inexistente.")
            if item["status"] != "failed":
                raise AnalysisError(409, "Solo puede reintentarse una solicitud fallida.")
            item = connection.execute(text("""UPDATE quality_assessment_queue_items
              SET status='queued',priority=:priority,requested_at=now(),started_at=NULL,
                  completed_at=NULL,failed_at=NULL,updated_at=now() WHERE id=:id RETURNING *"""),
              {"id": item["id"], "priority": priority}).mappings().one()
            self._audit(connection, "scientific.quality_queue.retried", "retry",
                        item, principal, request)
            return dict(item)
