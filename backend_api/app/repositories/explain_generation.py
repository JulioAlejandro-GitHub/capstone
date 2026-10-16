"""EXPLAIN HTTP catalog, using the canonical scientific repository and SQL selectors."""
from contextlib import contextmanager
from typing import Any, Iterator
from sqlalchemy.engine import Connection
from app.db import get_primary_engine
from src.malaria_dl.assessment.repository import AssessmentRepository
from src.malaria_dl.campaigns.repository import execute
from src.malaria_dl.data.sample_repository import select_dataset_sample_ids


@contextmanager
def assessment_scope(readonly: bool = False) -> Iterator[Connection]:
    with get_primary_engine().begin() as connection:
        if readonly:
            execute(connection, 'SET TRANSACTION READ ONLY')
        yield connection


class ExplainRepository(AssessmentRepository):
    def __init__(self) -> None:
        super().__init__(scope=assessment_scope)

    def source(self, attempt_id: str) -> dict[str, Any] | None:
        with self.transaction(readonly=True) as connection:
            row = execute(connection, '''SELECT a.*, i.identity, i.training_run_id
                FROM assessment_attempts a JOIN assessment_identities i ON i.id=a.identity_id
                JOIN runs r ON r.id=i.training_run_id AND r.run_type='training'
                WHERE a.id=CAST(:id AS uuid) AND r.status='completed' ''', id=attempt_id).mappings().one_or_none()
            return dict(row) if row else None

    def samples(self, dataset: str, sample: str | None = None, limit: int | None = None) -> list[str]:
        with self.transaction(readonly=True) as connection:
            return [str(value) for value in select_dataset_sample_ids(connection, dataset, 'val', sample, limit)]

    def candidates(self, training: str, sample: str) -> list[dict[str, Any]]:
        with self.transaction(readonly=True) as connection:
            rows = execute(connection, '''SELECT a.*, i.identity
                FROM assessment_attempts a JOIN assessment_identities i ON i.id=a.identity_id
                WHERE i.training_run_id=CAST(:train AS uuid) AND i.kind='explain'
                  AND EXISTS (SELECT 1 FROM jsonb_array_elements(i.identity->'samples') s
                              WHERE s->>'sample_id'=:sample)
                ORDER BY a.started_at DESC, a.id DESC''', train=training, sample=sample).mappings()
            return [dict(row) for row in rows]
