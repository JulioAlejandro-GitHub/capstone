"""Read the runtime architecture record persisted by each TRAIN phase."""
from typing import Any
from uuid import UUID
from sqlalchemy import text
from app.db import read_only_transaction
from app.repositories.scientific_results import ScientificReadRepository, read_run_configurations


class ModelArchitectureRepository:
    def read(self, run_id: UUID, datasource: str | None) -> dict[str, Any] | None:
        with read_only_transaction(datasource) as connection:
            run = connection.execute(text("""
                SELECT r.id,r.run_type,m.name AS model_name
                FROM runs r LEFT JOIN models m ON m.id=r.model_id WHERE r.id=:run
            """), {'run': run_id}).mappings().one_or_none()
            if run is None:
                return None
            configurations = read_run_configurations(connection, run_id)
            records = connection.execute(text("""
                SELECT phase,payload FROM train_execution_records
                WHERE run_id=:run AND kind='runtime' AND record_key='configuration'
                ORDER BY event_sequence NULLS LAST,created_at
            """), {'run': run_id}).mappings()
            return dict(run=dict(run), configuration=configurations[0] if configurations else None,
                        records=[dict(record) for record in records],
                        checkpoint=ScientificReadRepository().comparison_checkpoint(connection, run_id))
