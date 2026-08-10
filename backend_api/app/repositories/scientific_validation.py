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
