"""The registered model catalog, including models without executions."""
from typing import Any
from sqlalchemy import text
from app.db import read_only_transaction

MODEL_CATALOG_SQL = """
SELECT s.*, m.framework, m.architecture, m.input_shape, m.output_shape,
       m.pretrained, m.pretrained_source, m.created_at, m.metadata,
       COALESCE(t.training_runs, '[]'::jsonb) AS training_runs
FROM models m
JOIN vw_model_run_summary s ON s.model_id = m.id
LEFT JOIN LATERAL (
    SELECT jsonb_agg(jsonb_build_object(
        'training_run_id', r.id, 'status', r.status, 'run_name', r.run_name,
        'dataset_version_id', r.dataset_version_id, 'started_at', r.started_at
    ) ORDER BY r.created_at, r.id) AS training_runs
    FROM runs r WHERE r.model_id = m.id AND r.run_type = 'training'
) t ON true
ORDER BY s.total_runs DESC, s.model_name
"""


class CatalogRepository:
    def models(self, datasource: str | None) -> list[dict[str, Any]]:
        with read_only_transaction(datasource) as connection:
            return [dict(row) for row in connection.execute(text(MODEL_CATALOG_SQL)).mappings()]
