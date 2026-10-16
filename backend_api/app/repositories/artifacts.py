"""Read artifact identity from an explicit scientific catalog."""
from typing import Any
from contextlib import nullcontext
from sqlalchemy import text
from app.db import read_only_transaction


class ArtifactReadRepository:
    def get(self, datasource: str | None, artifact_id: str, source: str, *, connection=None) -> dict[str, Any] | None:
        if source == 'assessment':
            sql = """SELECT aa.artifact_id, aa.attempt_id, aa.sample_id, aa.payload,
                     a.artifact_root, a.identity_id, i.training_run_id
                     FROM assessment_artifacts aa
                     JOIN assessment_attempts a ON a.id=aa.attempt_id
                     JOIN assessment_identities i ON i.id=a.identity_id
                     JOIN runs r ON r.id=i.training_run_id
                     WHERE aa.artifact_id=CAST(:artifact_id AS uuid)"""
        else:
            sql = """SELECT a.id AS artifact_id,a.path,a.checksum,a.file_size_bytes,
                     a.run_id AS training_run_id FROM artifacts a
                     JOIN runs r ON r.id=a.run_id
                     WHERE a.id=CAST(:artifact_id AS uuid)"""
        with (nullcontext(connection) if connection is not None else read_only_transaction(datasource)) as active_connection:
            row = active_connection.execute(text(sql), {'artifact_id': artifact_id}).mappings().one_or_none()
        return dict(row) if row is not None else None
