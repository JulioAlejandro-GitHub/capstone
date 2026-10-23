"""REPRESENT SQL selectors, independent of the HTTP engine so the host agent can reuse them."""
from typing import Any
from app.repositories.explain_queries import ExplainQueries
from src.malaria_dl.campaigns.repository import execute


class RepresentQueries(ExplainQueries):
    """Same source and sample selectors as EXPLAIN; attempts and queue rows of kind REPRESENT."""

    def represent_candidates(self, training: str) -> list[dict[str, Any]]:
        with self.transaction(readonly=True) as connection:
            rows = execute(connection, '''SELECT a.*, i.identity
                FROM assessment_attempts a JOIN assessment_identities i ON i.id=a.identity_id
                WHERE i.training_run_id=CAST(:train AS uuid) AND i.kind='represent'
                ORDER BY a.started_at DESC, a.id DESC''', train=training).mappings()
            return [dict(row) for row in rows]

    def represent_requests(self, source: str) -> list[dict[str, Any]]:
        """Host GPU queue rows for one EVALUATE source, most recent first."""
        with self.transaction(readonly=True) as connection:
            rows = execute(connection, '''SELECT id, request, state, cause FROM explain_requests
                WHERE request->>'operation'='represent' AND request->>'source_attempt_id'=:source
                ORDER BY created_at DESC LIMIT 5''', source=source).mappings()
            return [dict(row) for row in rows]
