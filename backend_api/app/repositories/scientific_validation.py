from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection


class ScientificValidationRepository:
    def __init__(self, connection: Connection):
        self.connection = connection

    def source_rows(self, table: str, identifiers: list[str]) -> list[dict]:
        allowed = {
            "microscopy_images", "cell_detection_runs", "cell_classification_runs"
        }
        if table not in allowed:
            raise ValueError("Fuente de validación no permitida")
        rows = []
        for identifier in identifiers:
            row = self.connection.execute(
                text(f"SELECT * FROM {table} WHERE id=CAST(:id AS uuid)"),
                {"id": identifier},
            ).mappings().first()
            if row:
                rows.append(dict(row))
        return rows

    def image_run_membership(self, image_ids: list[str], run_ids: list[str], run_table: str) -> set[tuple[str, str]]:
        if run_table == "cell_detection_runs":
            join = "JOIN microscopy_analysis_run_images ari ON ari.analysis_run_id=r.analysis_run_id"
        elif run_table == "cell_classification_runs":
            join = "JOIN cell_classification_inputs ci ON ci.classification_run_id=r.id"
            rows = self.connection.execute(text("""
              SELECT DISTINCT r.id run_id,ci.microscopy_image_id image_id
              FROM cell_classification_runs r
              JOIN cell_classification_inputs ci ON ci.classification_run_id=r.id
              WHERE r.id=ANY(CAST(:runs AS uuid[])) AND ci.microscopy_image_id=ANY(CAST(:images AS uuid[]))
            """), {"runs": run_ids, "images": image_ids}).mappings().all()
            return {(str(row["run_id"]), str(row["image_id"])) for row in rows}
        else:
            raise ValueError("Run no permitido")
        rows = self.connection.execute(text(f"""
          SELECT DISTINCT r.id run_id,ari.microscopy_image_id image_id
          FROM {run_table} r {join}
          WHERE r.id=ANY(CAST(:runs AS uuid[])) AND ari.microscopy_image_id=ANY(CAST(:images AS uuid[]))
        """), {"runs": run_ids, "images": image_ids}).mappings().all()
        return {(str(row["run_id"]), str(row["image_id"])) for row in rows}

    def create(self, values: dict, snapshot: dict, digest: str, actor_id: str) -> dict:
        session_id = uuid4()
        params = {
            "id": session_id, "name": values["name"], "description": values.get("description"),
            "datasource": values["datasource"], "protocol_key": values["protocol_key"],
            "protocol_version": values["protocol_version"],
            "iou": values["matching_iou_threshold"], "snapshot": json.dumps(snapshot),
            "digest": digest, "actor": actor_id,
        }
        self.connection.execute(text("""
          INSERT INTO scientific_validation_sessions(
            id,name,description,datasource,protocol_key,protocol_version,
            matching_iou_threshold,initial_snapshot,snapshot_sha256,created_by,updated_by
          ) VALUES(
            :id,:name,:description,:datasource,:protocol_key,:protocol_version,
            :iou,CAST(:snapshot AS jsonb),:digest,CAST(:actor AS uuid),CAST(:actor AS uuid)
          )
        """), params)
        for sequence, image in enumerate(snapshot["images"], 1):
            self.connection.execute(text("""
              INSERT INTO scientific_validation_images(
                session_id,microscopy_image_id,image_sha256,sequence_number
              ) VALUES(:session,CAST(:image AS uuid),:sha,:sequence)
            """), {"session": session_id, "image": image["id"], "sha": image["sha256"], "sequence": sequence})
        for run in snapshot["detection_runs"]:
            self.connection.execute(text("""
              INSERT INTO scientific_validation_detection_runs(session_id,detection_run_id)
              VALUES(:session,CAST(:run AS uuid))
            """), {"session": session_id, "run": run["id"]})
        for run in snapshot["classification_runs"]:
            self.connection.execute(text("""
              INSERT INTO scientific_validation_classification_runs(session_id,classification_run_id)
              VALUES(:session,CAST(:run AS uuid))
            """), {"session": session_id, "run": run["id"]})
        return self.get(str(session_id), for_update=True)

    def get(self, session_id: str, *, for_update: bool = False) -> dict | None:
        lock = " FOR UPDATE" if for_update else ""
        row = self.connection.execute(text(
            "SELECT * FROM scientific_validation_sessions WHERE id=CAST(:id AS uuid)" + lock
        ), {"id": session_id}).mappings().first()
        if not row:
            return None
        result = dict(row)
        result["image_ids"] = [str(item[0]) for item in self.connection.execute(text("""
          SELECT microscopy_image_id FROM scientific_validation_images
          WHERE session_id=CAST(:id AS uuid) ORDER BY sequence_number
        """), {"id": session_id}).all()]
        result["detection_run_ids"] = [str(item[0]) for item in self.connection.execute(text("""
          SELECT detection_run_id FROM scientific_validation_detection_runs
          WHERE session_id=CAST(:id AS uuid) ORDER BY created_at,detection_run_id
        """), {"id": session_id}).all()]
        result["classification_run_ids"] = [str(item[0]) for item in self.connection.execute(text("""
          SELECT classification_run_id FROM scientific_validation_classification_runs
          WHERE session_id=CAST(:id AS uuid) ORDER BY created_at,classification_run_id
        """), {"id": session_id}).all()]
        return result

    def list(self, status: str | None, limit: int, offset: int) -> dict:
        where = " WHERE status=:status" if status else ""
        params = {"status": status, "limit": limit, "offset": offset}
        rows = self.connection.execute(text(f"""
          SELECT s.*,
            (SELECT count(*) FROM scientific_validation_images i WHERE i.session_id=s.id) image_count,
            (SELECT count(*) FROM scientific_validation_detection_runs d WHERE d.session_id=s.id) detection_run_count,
            (SELECT count(*) FROM scientific_validation_classification_runs c WHERE c.session_id=s.id) classification_run_count
          FROM scientific_validation_sessions s{where}
          ORDER BY created_at DESC,id DESC LIMIT :limit OFFSET :offset
        """), params).mappings().all()
        total = self.connection.execute(text(
            f"SELECT count(*) FROM scientific_validation_sessions{where}"
        ), params).scalar_one()
        return {"items": [dict(row) for row in rows], "total": total, "limit": limit, "offset": offset}

    def update(self, session_id: str, values: dict, actor_id: str) -> dict:
        assignments = [f"{key}=:{key}" for key in values]
        params = {**values, "id": session_id, "actor": actor_id}
        self.connection.execute(text(f"""
          UPDATE scientific_validation_sessions SET {','.join(assignments)},
            updated_by=CAST(:actor AS uuid),updated_at=now()
          WHERE id=CAST(:id AS uuid)
        """), params)
        return self.get(session_id, for_update=True)

    def archive(self, session_id: str, actor_id: str) -> dict:
        self.connection.execute(text("""
          UPDATE scientific_validation_sessions
          SET status='archived',archived_at=now(),archived_by=CAST(:actor AS uuid),
              updated_by=CAST(:actor AS uuid),updated_at=now()
          WHERE id=CAST(:id AS uuid)
        """), {"id": session_id, "actor": actor_id})
        return self.get(session_id, for_update=True)

    def target_belongs_to_session(
        self,
        session_id: str,
        *,
        target_type: str,
        target_id: str,
    ) -> bool:
        if target_type == "cell":
            statement = text("""
              SELECT 1
              FROM cell_detections detection
              JOIN scientific_validation_detection_runs membership
                ON membership.detection_run_id=detection.detection_run_id
              WHERE membership.session_id=CAST(:session_id AS uuid)
                AND detection.id=CAST(:target_id AS uuid)
            """)
        elif target_type == "analysis":
            statement = text("""
              SELECT 1 FROM microscopy_analysis_runs analysis
              WHERE analysis.id=CAST(:target_id AS uuid) AND (
                EXISTS(
                  SELECT 1 FROM scientific_validation_detection_runs membership
                  JOIN cell_detection_runs run ON run.id=membership.detection_run_id
                  WHERE membership.session_id=CAST(:session_id AS uuid)
                    AND run.analysis_run_id=analysis.id
                ) OR EXISTS(
                  SELECT 1 FROM scientific_validation_classification_runs membership
                  JOIN cell_classification_runs run ON run.id=membership.classification_run_id
                  WHERE membership.session_id=CAST(:session_id AS uuid)
                    AND run.analysis_run_id=analysis.id
                ) OR EXISTS(
                  SELECT 1 FROM scientific_validation_images membership
                  JOIN microscopy_analysis_run_images run_image
                    ON run_image.microscopy_image_id=membership.microscopy_image_id
                  WHERE membership.session_id=CAST(:session_id AS uuid)
                    AND run_image.analysis_run_id=analysis.id
                )
              )
            """)
        elif target_type == "sample":
            statement = text("""
              SELECT 1 FROM blood_samples sample
              WHERE sample.id=CAST(:target_id AS uuid) AND (
                EXISTS(
                  SELECT 1 FROM scientific_validation_detection_runs membership
                  JOIN cell_detection_runs run ON run.id=membership.detection_run_id
                  JOIN microscopy_analysis_runs analysis ON analysis.id=run.analysis_run_id
                  WHERE membership.session_id=CAST(:session_id AS uuid)
                    AND analysis.sample_id=sample.id
                ) OR EXISTS(
                  SELECT 1 FROM scientific_validation_classification_runs membership
                  JOIN cell_classification_runs run ON run.id=membership.classification_run_id
                  JOIN microscopy_analysis_runs analysis ON analysis.id=run.analysis_run_id
                  WHERE membership.session_id=CAST(:session_id AS uuid)
                    AND analysis.sample_id=sample.id
                ) OR EXISTS(
                  SELECT 1 FROM scientific_validation_images membership
                  JOIN microscopy_analysis_run_images run_image
                    ON run_image.microscopy_image_id=membership.microscopy_image_id
                  JOIN microscopy_analysis_runs analysis ON analysis.id=run_image.analysis_run_id
                  WHERE membership.session_id=CAST(:session_id AS uuid)
                    AND analysis.sample_id=sample.id
                )
              )
            """)
        else:
            return False
        return bool(self.connection.execute(
            statement, {"session_id": session_id, "target_id": target_id}
        ).scalar())

    @staticmethod
    def _annotation_state(row: dict) -> dict:
        return {
            "id": str(row["id"]),
            "validation_session_id": str(row["validation_session_id"]),
            "target_type": row["target_type"],
            "cell_id": str(row["cell_detection_id"]) if row.get("cell_detection_id") else None,
            "analysis_run_id": str(row["analysis_run_id"]) if row.get("analysis_run_id") else None,
            "sample_id": str(row["sample_id"]) if row.get("sample_id") else None,
            "category": row["category"],
            "content": row["content"],
            "version": row["version"],
            "created_by": str(row["created_by"]),
            "created_at": row["created_at"].isoformat(),
            "updated_by": str(row["updated_by"]),
            "updated_at": row["updated_at"].isoformat(),
        }

    def _append_annotation_event(
        self,
        row: dict,
        event_type: str,
        actor_id: str,
        before: dict | None,
    ) -> dict:
        after_state = self._annotation_state(row)
        event = self.connection.execute(text("""
          INSERT INTO scientific_validation_annotation_events(
            id,annotation_id,validation_session_id,event_type,annotation_version,
            actor_user_id,before_state,after_state
          ) VALUES(
            :id,:annotation_id,:session_id,:event_type,:version,
            CAST(:actor AS uuid),CAST(:before AS jsonb),CAST(:after AS jsonb)
          ) RETURNING *
        """), {
            "id": uuid4(), "annotation_id": row["id"],
            "session_id": row["validation_session_id"], "event_type": event_type,
            "version": row["version"], "actor": actor_id,
            "before": json.dumps(before, default=str) if before is not None else None,
            "after": json.dumps(after_state, default=str),
        }).mappings().one()
        return dict(event)

    def create_annotation(self, session_id: str, values: dict, actor_id: str) -> dict:
        annotation_id = uuid4()
        row = self.connection.execute(text("""
          INSERT INTO scientific_validation_annotations(
            id,validation_session_id,target_type,cell_detection_id,analysis_run_id,sample_id,
            category,content,created_by,updated_by
          ) VALUES(
            :id,CAST(:session_id AS uuid),:target_type,CAST(:cell_id AS uuid),
            CAST(:analysis_run_id AS uuid),CAST(:sample_id AS uuid),:category,:content,
            CAST(:actor AS uuid),CAST(:actor AS uuid)
          ) RETURNING *
        """), {
            "id": annotation_id, "session_id": session_id,
            "target_type": values["target_type"], "cell_id": values.get("cell_id"),
            "analysis_run_id": values.get("analysis_run_id"),
            "sample_id": values.get("sample_id"),
            "category": values["category"], "content": values["content"],
            "actor": actor_id,
        }).mappings().one()
        result = dict(row)
        self._append_annotation_event(result, "created", actor_id, None)
        return result

    def get_annotation(self, session_id: str, annotation_id: str) -> dict | None:
        row = self.connection.execute(text("""
          SELECT annotation.*,creator.username created_by_username,
                 updater.username updated_by_username
          FROM scientific_validation_annotations annotation
          JOIN users creator ON creator.id=annotation.created_by
          JOIN users updater ON updater.id=annotation.updated_by
          WHERE annotation.validation_session_id=CAST(:session_id AS uuid)
            AND annotation.id=CAST(:annotation_id AS uuid)
        """), {"session_id": session_id, "annotation_id": annotation_id}).mappings().first()
        return dict(row) if row else None

    def list_annotations(
        self,
        session_id: str,
        *,
        target_type: str | None,
        cell_id: str | None,
        analysis_run_id: str | None,
        sample_id: str | None,
        category: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        clauses = ["annotation.validation_session_id=CAST(:session_id AS uuid)"]
        params = {"session_id": session_id, "limit": limit, "offset": offset}
        for name, column, cast in (
            ("target_type", "annotation.target_type", ""),
            ("cell_id", "annotation.cell_detection_id", "::uuid"),
            ("analysis_run_id", "annotation.analysis_run_id", "::uuid"),
            ("sample_id", "annotation.sample_id", "::uuid"),
            ("category", "annotation.category", ""),
        ):
            value = locals()[name]
            if value is not None:
                clauses.append(f"{column}=CAST(:{name} AS uuid)" if cast else f"{column}=:{name}")
                params[name] = value
        where = " AND ".join(clauses)
        rows = self.connection.execute(text(f"""
          SELECT annotation.*,creator.username created_by_username,
                 updater.username updated_by_username
          FROM scientific_validation_annotations annotation
          JOIN users creator ON creator.id=annotation.created_by
          JOIN users updater ON updater.id=annotation.updated_by
          WHERE {where}
          ORDER BY annotation.created_at,annotation.id LIMIT :limit OFFSET :offset
        """), params).mappings().all()
        total = self.connection.execute(text(f"""
          SELECT count(*) FROM scientific_validation_annotations annotation WHERE {where}
        """), params).scalar_one()
        return {"items": [dict(row) for row in rows], "total": total, "limit": limit, "offset": offset}

    def update_annotation(
        self,
        session_id: str,
        annotation_id: str,
        values: dict,
        expected_version: int,
        actor_id: str,
    ) -> tuple[dict, dict] | None:
        before_row = self.connection.execute(text("""
          SELECT * FROM scientific_validation_annotations
          WHERE validation_session_id=CAST(:session_id AS uuid)
            AND id=CAST(:annotation_id AS uuid)
        """), {"session_id": session_id, "annotation_id": annotation_id}).mappings().first()
        if not before_row:
            return None
        assignments = [f"{column}=:{column}" for column in values]
        row = self.connection.execute(text(f"""
          UPDATE scientific_validation_annotations
          SET {','.join(assignments)},version=version+1,updated_by=CAST(:actor AS uuid),
              updated_at=clock_timestamp()
          WHERE validation_session_id=CAST(:session_id AS uuid)
            AND id=CAST(:annotation_id AS uuid) AND version=:expected_version
          RETURNING *
        """), {
            **values, "actor": actor_id, "session_id": session_id,
            "annotation_id": annotation_id, "expected_version": expected_version,
        }).mappings().first()
        if not row:
            return ({}, dict(before_row))
        before = self._annotation_state(dict(before_row))
        result = dict(row)
        self._append_annotation_event(result, "updated", actor_id, before)
        return result, dict(before_row)

    def annotation_history(
        self, session_id: str, annotation_id: str, *, limit: int, offset: int
    ) -> dict | None:
        if not self.get_annotation(session_id, annotation_id):
            return None
        params = {"session_id": session_id, "annotation_id": annotation_id,
                  "limit": limit, "offset": offset}
        rows = self.connection.execute(text("""
          SELECT event.*,actor.username actor_username
          FROM scientific_validation_annotation_events event
          JOIN users actor ON actor.id=event.actor_user_id
          WHERE event.validation_session_id=CAST(:session_id AS uuid)
            AND event.annotation_id=CAST(:annotation_id AS uuid)
          ORDER BY event.annotation_version,event.created_at,event.id
          LIMIT :limit OFFSET :offset
        """), params).mappings().all()
        total = self.connection.execute(text("""
          SELECT count(*) FROM scientific_validation_annotation_events
          WHERE validation_session_id=CAST(:session_id AS uuid)
            AND annotation_id=CAST(:annotation_id AS uuid)
        """), params).scalar_one()
        return {"items": [dict(row) for row in rows], "total": total,
                "limit": limit, "offset": offset}
