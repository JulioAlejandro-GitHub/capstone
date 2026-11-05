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
            records = [dict(record) for record in records]
            # A logical TRAIN (zero-shot) records no execution: its registered version carries the frozen protocol.
            version = None if records else connection.execute(text("""
                SELECT mv.id AS model_version_id,mv.training_run_id,mv.preprocessing_profile_snapshot AS profile,
                       mv.class_mapping,mv.input_signature,mv.output_signature,a.checksum AS sha256,a.file_size_bytes AS bytes
                FROM model_versions mv JOIN artifacts a ON a.id=mv.checkpoint_artifact_id AND a.run_id=mv.training_run_id
                WHERE mv.training_run_id=:run AND mv.status NOT IN ('rejected','retired') AND mv.lineage_status='resolved'
                ORDER BY mv.created_at DESC LIMIT 1
            """), {'run': run_id}).mappings().one_or_none()
            return dict(run=dict(run), configuration=configurations[0] if configurations else None,
                        records=records, logical_version=dict(version) if version else None,
                        checkpoint=ScientificReadRepository().comparison_checkpoint(connection, run_id))
