"""Read-only population of an activation trace: the verified EVALUATE of one TRAIN."""
from typing import Any
from uuid import UUID
from sqlalchemy import text
from app.db import read_only_transaction

CATEGORIES = {'false_negative': (1, 0), 'false_positive': (0, 1), 'true_positive': (1, 1), 'true_negative': (0, 0)}


class ActivationTraceRepository:
    def evaluation(self, run_id: UUID, datasource: str | None) -> dict[str, Any] | None:
        """VAL first, as EXPLAIN: TEST stays reserved for the final evaluation."""
        with read_only_transaction(datasource) as connection:
            row = connection.execute(text("""
                SELECT a.id,i.identity->>'split' AS split FROM assessment_attempts a
                JOIN assessment_identities i ON i.id=a.identity_id
                WHERE i.training_run_id=:run AND i.kind='evaluate' AND a.state='verified'
                ORDER BY (i.identity->>'split')='val' DESC,a.started_at DESC LIMIT 1
            """), {'run': run_id}).mappings().one_or_none()
            return dict(row) if row else None

    def candidates(self, attempt_id: UUID, category: str, limit: int, datasource: str | None) -> list[dict[str, Any]]:
        label, predicted = CATEGORIES[category]
        with read_only_transaction(datasource) as connection:
            return [dict(row) for row in connection.execute(text("""
                SELECT sample_id,(payload->>'label')::int AS label,(payload->>'predicted')::int AS predicted,
                       (payload->>'raw_score')::float AS score,(payload->>'threshold')::float AS threshold
                FROM assessment_results WHERE attempt_id=:attempt
                  AND (payload->>'label')::int=:label AND (payload->>'predicted')::int=:predicted
                ORDER BY abs((payload->>'raw_score')::float-(payload->>'threshold')::float) DESC,sample_id LIMIT :limit
            """), {'attempt': attempt_id, 'label': label, 'predicted': predicted, 'limit': limit}).mappings()]

    def result(self, attempt_id: UUID, sample_id: UUID, datasource: str | None) -> dict[str, Any] | None:
        with read_only_transaction(datasource) as connection:
            row = connection.execute(text(
                'SELECT payload FROM assessment_results WHERE attempt_id=:attempt AND sample_id=:sample'
            ), {'attempt': attempt_id, 'sample': sample_id}).mappings().one_or_none()
            return dict(row['payload']) if row else None
