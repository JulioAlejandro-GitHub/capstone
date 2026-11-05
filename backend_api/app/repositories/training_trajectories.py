"""Read-only VAL predictions recorded by TRAIN at every epoch. Nothing is recomputed."""
from typing import Any
from uuid import UUID
from sqlalchemy import text
from app.db import read_only_transaction


class TrainingTrajectoryRepository:
    def read(self, run_id: UUID, datasource: str | None) -> dict[str, Any] | None:
        """One snapshot: the TRAIN, its per-epoch VAL predictions and the identity of its latest verified VAL EVALUATE."""
        with read_only_transaction(datasource, repeatable_read=True) as connection:
            run = connection.execute(text('SELECT id,run_type FROM runs WHERE id=:run'),
                                     {'run': run_id}).mappings().one_or_none()
            if run is None:
                return None
            predictions = [dict(row) for row in connection.execute(text("""
                SELECT phase,record_key,payload FROM train_execution_records
                WHERE run_id=:run AND kind='predictions' AND payload->>'role'='val'
                ORDER BY (payload->>'epoch')::int,phase,record_key
            """), {'run': run_id}).mappings()]
            evaluation = connection.execute(text("""
                SELECT a.id AS attempt_id,i.identity->'samples' AS samples FROM assessment_attempts a
                JOIN assessment_identities i ON i.id=a.identity_id
                WHERE i.training_run_id=:run AND i.kind='evaluate' AND a.state='verified'
                  AND i.identity->>'split'='val'
                ORDER BY a.started_at DESC LIMIT 1
            """), {'run': run_id}).mappings().one_or_none()
            return dict(run=dict(run), predictions=predictions, evaluation=dict(evaluation) if evaluation else None)
