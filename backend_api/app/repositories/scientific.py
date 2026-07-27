from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection


ENTITY_CONFIG = {
    "subject": ("research_subjects", "subject_code"),
    "case": ("scientific_cases", "case_code"),
    "sample": ("blood_samples", "sample_code"),
    "slide": ("smear_slides", "slide_code"),
    "image": ("microscopy_images", "image_code"),
}


class ScientificRepository:
    def __init__(self, connection: Connection):
        self.connection = connection

    @staticmethod
    def _config(kind: str) -> tuple[str, str]:
        try:
            return ENTITY_CONFIG[kind]
        except KeyError as exc:
            raise ValueError("Entidad científica no permitida") from exc

    @staticmethod
    def _parameters(values: dict) -> dict:
        result = dict(values)
        if "metadata_json" in result:
            result["metadata_json"] = json.dumps(result["metadata_json"])
        return result

    @staticmethod
    def _value_expression(column: str) -> str:
        return f"CAST(:{column} AS jsonb)" if column == "metadata_json" else f":{column}"

    def create(self, kind: str, values: dict, actor_id: str) -> dict:
        table, _ = self._config(kind)
        entity_id = uuid4()
        data = {"id": entity_id, **values, "created_by": actor_id}
        columns = list(data)
        expressions = [self._value_expression(column) for column in columns]
        row = self.connection.execute(
            text(
                f"INSERT INTO {table} ({','.join(columns)}) "
                f"VALUES ({','.join(expressions)}) RETURNING *"
            ),
            self._parameters(data),
        ).mappings().one()
        return dict(row)

    def get(self, kind: str, entity_id: str, *, for_update: bool = False) -> dict | None:
        table, _ = self._config(kind)
        lock = " FOR UPDATE" if for_update else ""
        row = self.connection.execute(
            text(f"SELECT * FROM {table} WHERE id=CAST(:id AS uuid){lock}"),
            {"id": entity_id},
        ).mappings().first()
        return dict(row) if row else None

    def update(self, kind: str, entity_id: str, values: dict, actor_id: str) -> dict | None:
        table, _ = self._config(kind)
        data = {**values, "updated_by": actor_id}
        assignments = [
            f"{column}={self._value_expression(column)}" for column in data
        ]
        row = self.connection.execute(
            text(
                f"UPDATE {table} SET {','.join(assignments)},updated_at=NOW() "
                "WHERE id=CAST(:id AS uuid) RETURNING *"
            ),
            self._parameters({**data, "id": entity_id}),
        ).mappings().first()
        return dict(row) if row else None

    def archive(self, kind: str, entity_id: str, actor_id: str) -> dict | None:
        table, _ = self._config(kind)
        row = self.connection.execute(
            text(
                f"UPDATE {table} SET status='archived',archived_at=NOW(),"
                "archived_by=CAST(:actor AS uuid),updated_by=CAST(:actor AS uuid),updated_at=NOW() "
                "WHERE id=CAST(:id AS uuid) AND status<>'archived' RETURNING *"
            ),
            {"id": entity_id, "actor": actor_id},
        ).mappings().first()
        return dict(row) if row else None

    def list(
        self,
        kind: str,
        *,
        parent_column: str | None = None,
        parent_id: str | None = None,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        table, code_column = self._config(kind)
        clauses: list[str] = []
        params: dict = {"limit": limit, "offset": offset}
        if parent_column:
            if parent_column not in {"case_id", "sample_id", "slide_id"}:
                raise ValueError("Relación no permitida")
            clauses.append(f"{parent_column}=CAST(:parent_id AS uuid)")
            params["parent_id"] = parent_id
        if status:
            clauses.append("status=:status")
            params["status"] = status
        if search:
            clauses.append(f"{code_column} ILIKE :search")
            params["search"] = f"%{search}%"
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(
            text(
                f"SELECT * FROM {table}{where} "
                "ORDER BY created_at DESC,id DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        ).mappings().all()
        total = self.connection.execute(
            text(f"SELECT count(*) FROM {table}{where}"), params
        ).scalar_one()
        return {"items": [dict(row) for row in rows], "total": total, "limit": limit, "offset": offset}

    def active_child_count(self, kind: str, entity_id: str) -> int:
        relations = {
            "subject": ("scientific_cases", "subject_id"),
            "case": ("blood_samples", "case_id"),
            "sample": ("smear_slides", "sample_id"),
            "slide": ("microscopy_images", "slide_id"),
        }
        table, column = relations[kind]
        return self.connection.execute(
            text(
                f"SELECT count(*) FROM {table} "
                f"WHERE {column}=CAST(:id AS uuid) AND status<>'archived'"
            ),
            {"id": entity_id},
        ).scalar_one()

    def traceability(self, case_id: str) -> list[dict]:
        rows = self.connection.execute(text("""
          SELECT c.id case_id,c.case_code,c.status case_status,c.subject_id,
                 rs.subject_code,rs.status subject_status,
                 bs.id sample_id,bs.sample_code,bs.status sample_status,
                 ss.id slide_id,ss.slide_code,ss.status slide_status,ss.smear_type,
                 mi.id image_id,mi.image_code,mi.status image_status,mi.sha256,
                 mi.width_px,mi.height_px,mi.mime_type
          FROM scientific_cases c
          LEFT JOIN research_subjects rs ON rs.id=c.subject_id
          LEFT JOIN blood_samples bs ON bs.case_id=c.id
          LEFT JOIN smear_slides ss ON ss.sample_id=bs.id
          LEFT JOIN microscopy_images mi ON mi.slide_id=ss.id
          WHERE c.id=CAST(:id AS uuid)
          ORDER BY bs.created_at,ss.created_at,mi.created_at
        """), {"id": case_id}).mappings().all()
        return [dict(row) for row in rows]
