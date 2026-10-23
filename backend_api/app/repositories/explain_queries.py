"""EXPLAIN SQL selectors, independent of the HTTP engine so the host agent can reuse them."""
from typing import Any
from src.malaria_dl.assessment.repository import AssessmentRepository
from src.malaria_dl.campaigns.repository import execute
from src.malaria_dl.data.sample_repository import select_dataset_sample_ids


class ExplainQueries(AssessmentRepository):
    """EXPLAIN selectors shared by the backend (Docker) and the host GPU agent; no engine is chosen here."""

    def source(self, attempt_id: str) -> dict[str, Any] | None:
        with self.transaction(readonly=True) as connection:
            row = execute(connection, '''SELECT a.*, i.identity, i.training_run_id
                FROM assessment_attempts a JOIN assessment_identities i ON i.id=a.identity_id
                JOIN runs r ON r.id=i.training_run_id AND r.run_type='training'
                WHERE a.id=CAST(:id AS uuid) AND r.status='completed' ''', id=attempt_id).mappings().one_or_none()
            return dict(row) if row else None

    def samples(self, dataset: str, sample: str | None = None, limit: int | None = None, split: str = 'val') -> list[str]:
        with self.transaction(readonly=True) as connection:
            return [str(value) for value in select_dataset_sample_ids(connection, dataset, split, sample, limit)]

    def candidates(self, training: str, sample: str) -> list[dict[str, Any]]:
        with self.transaction(readonly=True) as connection:
            rows = execute(connection, '''SELECT a.*, i.identity
                FROM assessment_attempts a JOIN assessment_identities i ON i.id=a.identity_id
                WHERE i.training_run_id=CAST(:train AS uuid) AND i.kind='explain'
                  AND EXISTS (SELECT 1 FROM jsonb_array_elements(i.identity->'samples') s
                              WHERE s->>'sample_id'=:sample)
                ORDER BY a.started_at DESC, a.id DESC''', train=training, sample=sample).mappings()
            return [dict(row) for row in rows]

    def requests_for(self, source: str, sample: str) -> list[dict[str, Any]]:
        """Host GPU queue rows for one cell, most recent first (explain_requests)."""
        with self.transaction(readonly=True) as connection:
            rows = execute(connection, '''SELECT id, request, state, cause FROM explain_requests
                WHERE request->>'source_attempt_id'=:source AND request->>'sample_id'=:sample
                ORDER BY created_at DESC LIMIT 20''', source=source, sample=sample).mappings()
            return [dict(row) for row in rows]
