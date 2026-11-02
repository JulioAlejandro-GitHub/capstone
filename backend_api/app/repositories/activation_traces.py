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

    def candidates(self, attempt_id: UUID, category: str, limit: int, datasource: str | None,
                   explained_only: bool = False) -> list[dict[str, Any]]:
        """Cells of one outcome, most confident first; «explained» marks cells with a verified EXPLAIN of the same TRAIN."""
        label, predicted = CATEGORIES[category]
        with read_only_transaction(datasource) as connection:
            return [dict(row) for row in connection.execute(text("""
                WITH train AS (
                    SELECT i.training_run_id FROM assessment_attempts a
                    JOIN assessment_identities i ON i.id=a.identity_id WHERE a.id=:attempt
                ), cells AS (
                    SELECT r.sample_id,(r.payload->>'label')::int AS label,(r.payload->>'predicted')::int AS predicted,
                           (r.payload->>'raw_score')::float AS score,(r.payload->>'threshold')::float AS threshold,
                           EXISTS (SELECT 1 FROM assessment_identities e JOIN assessment_attempts x ON x.identity_id=e.id
                                   WHERE e.training_run_id=(SELECT training_run_id FROM train) AND e.kind='explain'
                                     AND x.state='verified'
                                     AND e.identity->'samples' @> jsonb_build_array(jsonb_build_object('sample_id', r.sample_id::text))
                           ) AS explained
                    FROM assessment_results r WHERE r.attempt_id=:attempt
                      AND (r.payload->>'label')::int=:label AND (r.payload->>'predicted')::int=:predicted
                )
                SELECT * FROM cells WHERE explained OR NOT :explained_only
                ORDER BY explained DESC,abs(score-threshold) DESC,sample_id LIMIT :limit
            """), {'attempt': attempt_id, 'label': label, 'predicted': predicted, 'limit': limit,
                     'explained_only': explained_only}).mappings()]

    def result(self, attempt_id: UUID, sample_id: UUID, datasource: str | None) -> dict[str, Any] | None:
        with read_only_transaction(datasource) as connection:
            row = connection.execute(text(
                'SELECT payload FROM assessment_results WHERE attempt_id=:attempt AND sample_id=:sample'
            ), {'attempt': attempt_id, 'sample': sample_id}).mappings().one_or_none()
            return dict(row['payload']) if row else None
