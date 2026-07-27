from __future__ import annotations

import hashlib
import json
import secrets
from uuid import uuid4

from sqlalchemy import text

from app.audit import mutation_connection, record_event
from app.db import get_primary_engine
from app.services.image_quality import assess_image
from app.services.local_storage import LocalStorage
from app.services.quality_profiles import select_profile


class AnalysisError(ValueError):
    def __init__(self, status_code: int, detail: str):
        self.status_code, self.detail = status_code, detail
        super().__init__(detail)


def _dict(row):
    return dict(row) if row else None


def _event(connection, run_id, event_type, stage, status, image_id=None, current=None, total=None, code=None, message=None):
    connection.execute(text("""INSERT INTO microscopy_analysis_events(
      id,analysis_run_id,microscopy_image_id,event_type,stage,status,message_code,message,
      progress_current,progress_total) VALUES(
      :id,:run,CAST(:image AS uuid),:type,:stage,:status,:code,:message,:current,:total)"""),
      {"id": uuid4(), "run": run_id, "image": str(image_id) if image_id else None, "type": event_type,
       "stage": stage, "status": status, "code": code, "message": message, "current": current, "total": total})


def manifest(images: list[dict]) -> tuple[str, str]:
    items = [{"microscopy_image_id": str(item["id"]), "sha256": item["sha256"].strip(),
              "file_size_bytes": item["file_size_bytes"], "width_px": item["width_px"],
              "height_px": item["height_px"], "sequence_number": item["image_sequence_number"]}
             for item in sorted(images, key=lambda x: (x["image_sequence_number"], str(x["id"])))]
    canonical = json.dumps(items, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest(), canonical


class MicroscopyAnalysisService:
    engine = get_primary_engine()

    def eligible_batches(self, **filters):
        clauses = ["rs.status='active'", "c.status='active'", "bs.status='active'",
                   "ss.status<>'archived'", "b.status NOT IN ('failed','inconsistent')",
                   "b.received_image_count=(SELECT count(*) FROM microscopy_images mi WHERE mi.ingestion_batch_id=b.id)",
                   "NOT EXISTS(SELECT 1 FROM microscopy_images mi WHERE mi.ingestion_batch_id=b.id AND mi.status<>'available')",
                   "((b.acquisition_origin='research_dataset_import' AND lower(coalesce(b.source_system,'')) LIKE '%nih%' AND b.status='complete' AND b.received_image_count=5) OR (b.acquisition_origin<>'research_dataset_import' AND b.received_image_count>0 AND b.status IN ('complete','incomplete')))"]
        params = {"limit": filters.get("limit", 50), "offset": filters.get("offset", 0)}
        for key, expression in (("subject_code","rs.subject_code ILIKE :subject_code"),("sample_code","bs.sample_code ILIKE :sample_code"),
                                ("source_system","b.source_system=:source_system"),("status","b.status=:status")):
            if filters.get(key):
                clauses.append(expression); params[key] = f"%{filters[key]}%" if key.endswith("_code") else filters[key]
        where = " AND ".join(clauses)
        sql = f"""FROM image_ingestion_batches b JOIN research_subjects rs ON rs.id=b.subject_id
          JOIN scientific_cases c ON c.id=b.case_id JOIN blood_samples bs ON bs.id=b.sample_id
          JOIN smear_slides ss ON ss.id=b.slide_id WHERE {where}"""
        with self.engine.connect() as connection:
            rows = connection.execute(text(f"""SELECT b.id,b.status,b.acquisition_origin,b.source_system,
              b.received_image_count,b.created_at,rs.subject_code,bs.sample_code,ss.slide_code,
              (SELECT mar.run_code FROM microscopy_analysis_runs mar WHERE mar.ingestion_batch_id=b.id ORDER BY mar.created_at DESC LIMIT 1) previous_run_code
              {sql} ORDER BY b.created_at DESC LIMIT :limit OFFSET :offset"""), params).mappings().all()
            total = connection.execute(text(f"SELECT count(*) {sql}"), params).scalar_one()
        return {"items": [dict(row) for row in rows], "total": total, "limit": params["limit"], "offset": params["offset"]}

    def _batch(self, connection, batch_id):
        return _dict(connection.execute(text("""SELECT b.*,rs.subject_code,rs.status subject_status,
          c.status case_status,bs.sample_code,bs.status sample_status,ss.slide_code,ss.status slide_status
          FROM image_ingestion_batches b JOIN research_subjects rs ON rs.id=b.subject_id
          JOIN scientific_cases c ON c.id=b.case_id JOIN blood_samples bs ON bs.id=b.sample_id
          JOIN smear_slides ss ON ss.id=b.slide_id WHERE b.id=CAST(:id AS uuid) FOR UPDATE OF b"""),
          {"id": str(batch_id)}).mappings().first())

    def create(self, batch_id, principal, request):
        with mutation_connection(self.engine) as connection:
            batch = self._batch(connection, batch_id)
            if not batch: raise AnalysisError(404, "Lote de ingesta inexistente.")
            images = [dict(row) for row in connection.execute(text("""SELECT * FROM microscopy_images
              WHERE ingestion_batch_id=:batch ORDER BY image_sequence_number,id"""), {"batch": batch["id"]}).mappings()]
            active = all(batch[key] == "active" for key in ("subject_status","case_status","sample_status"))
            is_nih = batch["acquisition_origin"] == "research_dataset_import" and "nih" in (batch["source_system"] or "").lower()
            eligible = active and batch["slide_status"] != "archived" and batch["status"] not in ("failed","inconsistent")
            eligible = eligible and len(images) == batch["received_image_count"] and images and all(i["status"] == "available" for i in images)
            eligible = eligible and (not is_nih or (batch["status"] == "complete" and len(images) == 5))
            if not eligible: raise AnalysisError(409, "El lote no cumple las condiciones técnicas de elegibilidad.")
            profile = select_profile(batch["acquisition_origin"], batch["source_system"])
            digest, _ = manifest(images)
            existing = _dict(connection.execute(text("""SELECT * FROM microscopy_analysis_runs WHERE
              ingestion_batch_id=:batch AND quality_profile_key=:key AND quality_profile_version=:version
              AND quality_algorithm_version=:algorithm AND input_manifest_sha256=:manifest"""),
              {"batch": batch["id"], "key": profile["profile_key"], "version": profile["profile_version"],
               "algorithm": profile["algorithm_version"], "manifest": digest}).mappings().first())
            if existing:
                if existing["run_status"] in ("created","quality_pending","quality_processing"):
                    return self.get(str(existing["id"]), connection)
                raise AnalysisError(409, f"Ya existe la ejecución equivalente {existing['run_code']}.")
            run_id, run_code = uuid4(), f"ANL-{secrets.token_hex(4).upper()}"
            run = _dict(connection.execute(text("""INSERT INTO microscopy_analysis_runs(
              id,ingestion_batch_id,subject_id,case_id,sample_id,slide_id,run_code,run_status,active_stage,
              quality_gate_status,quality_profile_key,quality_profile_version,quality_algorithm_version,
              quality_profile_snapshot,input_manifest_sha256,input_image_count,requested_by)
              VALUES(:id,:batch,:subject,:case,:sample,:slide,:code,'quality_pending','created','pending',
              :key,:version,:algorithm,CAST(:profile AS jsonb),:manifest,:count,CAST(:actor AS uuid)) RETURNING *"""),
              {"id": run_id, "batch": batch["id"], "subject": batch["subject_id"], "case": batch["case_id"],
               "sample": batch["sample_id"], "slide": batch["slide_id"], "code": run_code,
               "key": profile["profile_key"], "version": profile["profile_version"],
               "algorithm": profile["algorithm_version"], "profile": json.dumps(profile),
               "manifest": digest, "count": len(images), "actor": principal.user_id}).mappings().one())
            for image in images:
                connection.execute(text("""INSERT INTO microscopy_analysis_run_images(
                  id,analysis_run_id,microscopy_image_id,sequence_number,input_sha256,input_file_size_bytes,
                  input_width_px,input_height_px,image_status_at_creation)
                  VALUES(:id,:run,:image,:sequence,:sha,:size,:width,:height,:status)"""),
                  {"id": uuid4(), "run": run_id, "image": image["id"], "sequence": image["image_sequence_number"],
                   "sha": image["sha256"], "size": image["file_size_bytes"], "width": image["width_px"],
                   "height": image["height_px"], "status": image["status"]})
            _event(connection, run_id, "analysis.run.created", "created", "completed", total=len(images))
            record_event(event_type="scientific.analysis.created", action="create", principal=principal, request=request,
              success=True, connection=connection, resource_type="microscopy_analysis_run", resource_id=str(run_id),
              after_state={"analysis_run_id": str(run_id), "run_code": run_code, "ingestion_batch_id": str(batch["id"]),
              "subject_id": str(batch["subject_id"]), "sample_id": str(batch["sample_id"]), "slide_id": str(batch["slide_id"]),
              "input_manifest_sha256": digest, "input_image_count": len(images),
              "quality_profile_key": profile["profile_key"], "quality_profile_version": profile["profile_version"]})
            return self.get(str(run_id), connection)

    def measurements(self, run_id):
        with self.engine.connect() as connection:
            run = _dict(connection.execute(text("SELECT * FROM microscopy_analysis_runs WHERE id=CAST(:id AS uuid)"), {"id": run_id}).mappings().first())
            if not run: raise AnalysisError(404, "Ejecución inexistente.")
            if run["run_status"] not in ("quality_pending","created"): raise AnalysisError(409, "La ejecución no admite evaluación.")
            images = [dict(row) for row in connection.execute(text("""SELECT mi.*,ri.id run_image_id
              FROM microscopy_analysis_run_images ri JOIN microscopy_images mi ON mi.id=ri.microscopy_image_id
              WHERE ri.analysis_run_id=:run ORDER BY ri.sequence_number"""), {"run": run["id"]}).mappings()]
        storage = LocalStorage()
        return run, [(image, assess_image(image, run["quality_profile_snapshot"], storage)) for image in images]

    def persist_measurements(self, run, results, principal, request):
        with mutation_connection(self.engine) as connection:
            locked = _dict(connection.execute(text("SELECT * FROM microscopy_analysis_runs WHERE id=:id FOR UPDATE"), {"id": run["id"]}).mappings().one())
            if locked["run_status"] not in ("quality_pending","created"): raise AnalysisError(409, "La ejecución cambió de estado.")
            connection.execute(text("""UPDATE microscopy_analysis_runs SET run_status='quality_processing',
              active_stage='quality_assessment',started_at=now(),updated_at=now() WHERE id=:id"""), {"id": run["id"]})
            _event(connection, run["id"], "quality.run.started", "quality_assessment", "processing", total=len(results))
            record_event(event_type="scientific.quality.started", action="quality-assessment", principal=principal,
                         request=request, success=True, connection=connection, resource_type="microscopy_analysis_run", resource_id=str(run["id"]))
            verdicts = []
            for current, (image, result) in enumerate(results, 1):
                _event(connection, run["id"], "quality.image.started", "quality_assessment", "processing", image["id"], current, len(results))
                fields = ["integrity_verified","checksum_verified","decoded_successfully","width_px","height_px","pixel_count",
                  "channel_count","bit_depth","color_space","analyzed_width_px","analyzed_height_px","analysis_scale",
                  "brightness_mean","brightness_p05","brightness_p50","brightness_p95","contrast_p95_p05","luminance_stddev",
                  "entropy_bits","laplacian_variance","tenengrad_mean","dark_pixel_ratio","bright_pixel_ratio",
                  "near_black_border_ratio","usable_field_ratio","error_code","error_message"]
                params = {key: result.get(key) for key in fields}
                params.update({"id": uuid4(), "run": run["id"], "run_image": image["run_image_id"], "image": image["id"],
                  "status": result["assessment_status"], "verdict": result["quality_verdict"],
                  "warnings": json.dumps(result["warning_codes"]), "failures": json.dumps(result["failure_codes"]),
                  "metrics": json.dumps(result["metrics_json"])})
                columns = ",".join(fields)
                values = ",".join(f":{field}" for field in fields)
                connection.execute(text(f"""INSERT INTO image_quality_assessments(
                  id,analysis_run_id,analysis_run_image_id,microscopy_image_id,assessment_status,quality_verdict,
                  {columns},warning_codes,failure_codes,metrics_json,started_at,completed_at)
                  VALUES(:id,:run,:run_image,:image,:status,:verdict,{values},CAST(:warnings AS jsonb),
                  CAST(:failures AS jsonb),CAST(:metrics AS jsonb),now(),now())"""), params)
                verdicts.append(result["quality_verdict"])
                connection.execute(text("UPDATE microscopy_analysis_run_images SET quality_status=:verdict WHERE id=:id"),
                                   {"verdict": result["quality_verdict"], "id": image["run_image_id"]})
                event = "quality.image.failed" if result["quality_verdict"] in ("fail","error") else "quality.image.warning" if result["quality_verdict"]=="warning" else "quality.image.completed"
                _event(connection, run["id"], event, "quality_assessment", result["quality_verdict"], image["id"], current, len(results))
            gate = "fail" if any(v in ("fail","error") for v in verdicts) else "warning" if "warning" in verdicts else "pass"
            status = {"fail":"blocked","warning":"review_required","pass":"ready_for_analysis"}[gate]
            ready = gate == "pass"
            connection.execute(text("""UPDATE microscopy_analysis_runs SET run_status=:status,active_stage=:stage,
              quality_gate_status=:gate,ready_for_analysis=:ready,completed_at=now(),updated_at=now() WHERE id=:id"""),
              {"status": status, "stage": "technical_review" if gate=="warning" else "completed", "gate": gate, "ready": ready, "id": run["id"]})
            _event(connection, run["id"], "quality.run.blocked" if gate=="fail" else "quality.run.completed",
                   "quality_aggregation", gate, current=len(results), total=len(results))
            counts = {name: verdicts.count(name) for name in ("pass","warning","fail","error")}
            audit_type = "scientific.quality.blocked" if gate=="fail" else "scientific.quality.completed"
            record_event(event_type=audit_type, action="quality-assessment", principal=principal, request=request,
              success=True, connection=connection, resource_type="microscopy_analysis_run", resource_id=str(run["id"]),
              after_state={"analysis_run_id":str(run["id"]),"quality_gate_status":gate,"ready_for_analysis":ready,
                           **{f"{key}_count":value for key,value in counts.items()}})
            return self.get(str(run["id"]), connection)

    def review(self, run_id, decision, comment, principal, request):
        with mutation_connection(self.engine) as connection:
            run = _dict(connection.execute(text("SELECT * FROM microscopy_analysis_runs WHERE id=CAST(:id AS uuid) FOR UPDATE"), {"id": run_id}).mappings().first())
            if not run: raise AnalysisError(404, "Ejecución inexistente.")
            if run["quality_gate_status"] != "warning": raise AnalysisError(409, "Solo pueden revisarse ejecuciones con advertencias.")
            clean = comment.strip()
            if not clean: raise AnalysisError(422, "El comentario es obligatorio.")
            connection.execute(text("""INSERT INTO quality_gate_decisions(id,analysis_run_id,decision,comment,actor_user_id)
              VALUES(:id,:run,:decision,:comment,CAST(:actor AS uuid))"""),
              {"id":uuid4(),"run":run["id"],"decision":decision,"comment":clean,"actor":principal.user_id})
            approved = decision == "approve_with_warnings"
            connection.execute(text("""UPDATE microscopy_analysis_runs SET run_status=:status,ready_for_analysis=:ready,
              active_stage='completed',updated_at=now() WHERE id=:id"""),
              {"status":"ready_for_analysis" if approved else "blocked","ready":approved,"id":run["id"]})
            _event(connection,run["id"],"quality.review.approved" if approved else "quality.review.rejected",
                   "technical_review","approved" if approved else "rejected")
            record_event(event_type="scientific.quality.warning_approved" if approved else "scientific.quality.warning_rejected",
              action="quality-decision",principal=principal,request=request,success=True,connection=connection,
              resource_type="microscopy_analysis_run",resource_id=str(run["id"]),
              after_state={"analysis_run_id":str(run["id"]),"decision":decision,"actor_user_id":principal.user_id,"comment":clean})
            return self.get(str(run["id"]), connection)

    def list_runs(self, limit=50, offset=0, **filters):
        clauses, params = [], {"limit":limit,"offset":offset}
        mapping = {"run_code":"r.run_code ILIKE :run_code","subject_code":"rs.subject_code ILIKE :subject_code",
                   "sample_code":"bs.sample_code ILIKE :sample_code","run_status":"r.run_status=:run_status",
                   "quality_gate_status":"r.quality_gate_status=:quality_gate_status","source_system":"b.source_system=:source_system"}
        for key, expr in mapping.items():
            if filters.get(key): clauses.append(expr); params[key]=f"%{filters[key]}%" if key.endswith("_code") else filters[key]
        where = "WHERE "+" AND ".join(clauses) if clauses else ""
        base = f"""FROM microscopy_analysis_runs r JOIN research_subjects rs ON rs.id=r.subject_id
          JOIN blood_samples bs ON bs.id=r.sample_id JOIN smear_slides ss ON ss.id=r.slide_id
          JOIN image_ingestion_batches b ON b.id=r.ingestion_batch_id {where}"""
        with self.engine.connect() as connection:
            rows=connection.execute(text(f"""SELECT r.*,rs.subject_code,bs.sample_code,ss.slide_code,b.source_system {base}
              ORDER BY r.created_at DESC LIMIT :limit OFFSET :offset"""),params).mappings().all()
            total=connection.execute(text(f"SELECT count(*) {base}"),params).scalar_one()
        return {"items":[dict(r) for r in rows],"total":total,"limit":limit,"offset":offset}

    def get(self, run_id, connection=None):
        owns = connection is None
        connection = connection or self.engine.connect()
        try:
            run = _dict(connection.execute(text("""SELECT r.*,rs.subject_code,bs.sample_code,ss.slide_code,
              b.status ingestion_status,b.source_system,u.username requested_by_username
              FROM microscopy_analysis_runs r JOIN research_subjects rs ON rs.id=r.subject_id
              JOIN blood_samples bs ON bs.id=r.sample_id JOIN smear_slides ss ON ss.id=r.slide_id
              JOIN image_ingestion_batches b ON b.id=r.ingestion_batch_id JOIN users u ON u.id=r.requested_by
              WHERE r.id=CAST(:id AS uuid)"""),{"id":run_id}).mappings().first())
            if not run: raise AnalysisError(404,"Ejecución inexistente.")
            images=[dict(r) for r in connection.execute(text("""SELECT ri.*,mi.original_filename,mi.mime_type,
              qa.quality_verdict,qa.integrity_verified,qa.warning_codes,qa.failure_codes,qa.brightness_mean,
              qa.contrast_p95_p05,qa.entropy_bits,qa.laplacian_variance,qa.tenengrad_mean,
              qa.dark_pixel_ratio,qa.bright_pixel_ratio,qa.usable_field_ratio,qa.near_black_border_ratio
              FROM microscopy_analysis_run_images ri JOIN microscopy_images mi ON mi.id=ri.microscopy_image_id
              LEFT JOIN image_quality_assessments qa ON qa.analysis_run_image_id=ri.id
              WHERE ri.analysis_run_id=:id ORDER BY ri.sequence_number"""),{"id":run["id"]}).mappings()]
            events=[dict(r) for r in connection.execute(text("SELECT * FROM microscopy_analysis_events WHERE analysis_run_id=:id ORDER BY created_at,id"),{"id":run["id"]}).mappings()]
            decisions=[dict(r) for r in connection.execute(text("""SELECT q.*,u.username actor_username FROM quality_gate_decisions q
              JOIN users u ON u.id=q.actor_user_id WHERE q.analysis_run_id=:id ORDER BY q.created_at,q.id"""),{"id":run["id"]}).mappings()]
            return {**run,"images":images,"events":events,"decisions":decisions}
        finally:
            if owns: connection.close()

    def events(self,run_id,limit=100,offset=0):
        with self.engine.connect() as connection:
            if not connection.execute(text("SELECT 1 FROM microscopy_analysis_runs WHERE id=CAST(:id AS uuid)"),{"id":run_id}).first():
                raise AnalysisError(404,"Ejecución inexistente.")
            rows=connection.execute(text("""SELECT * FROM microscopy_analysis_events WHERE analysis_run_id=CAST(:id AS uuid)
              ORDER BY created_at,id LIMIT :limit OFFSET :offset"""),{"id":run_id,"limit":limit,"offset":offset}).mappings().all()
            total=connection.execute(text("SELECT count(*) FROM microscopy_analysis_events WHERE analysis_run_id=CAST(:id AS uuid)"),{"id":run_id}).scalar_one()
        return {"items":[dict(r) for r in rows],"total":total,"limit":limit,"offset":offset}
