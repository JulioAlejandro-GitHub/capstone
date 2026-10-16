"""Read-only bridge to the same governed sample identities consumed by EXPLAIN."""
from collections import Counter
from typing import Any

from sqlalchemy import text
from app.db import read_only_transaction, resolve_datasource
from src.malaria_dl.data.governed_dataset import GovernedDatasetSnapshot, resolve_training_run_dataset
from src.malaria_dl.data.sample_repository import select_dataset_sample_ids, select_dataset_sample_records


class DatasetSampleReadRepository:
    def explanation_context(self, datasource: str | None, training_run_id: str,
                            attempt_id: str, sample_id: str) -> dict[str, Any] | None:
        with read_only_transaction(datasource) as connection:
            row = connection.execute(text("""
                SELECT i.id AS identity_id,i.identity,i.training_run_id
                FROM assessment_attempts a JOIN assessment_identities i ON i.id=a.identity_id
                JOIN runs r ON r.id=i.training_run_id AND r.run_type='training'
                WHERE a.id=CAST(:attempt AS uuid) AND i.training_run_id=CAST(:train AS uuid)
                  AND EXISTS (SELECT 1 FROM jsonb_array_elements(i.identity->'samples') s
                              WHERE s->>'sample_id'=:sample)
            """), {"attempt": attempt_id, "train": training_run_id, "sample": sample_id}).mappings().one_or_none()
        return dict(row) if row is not None else None

    def training_dataset(self, datasource: str | None, training_run_id: str) -> GovernedDatasetSnapshot:
        resolve_datasource(datasource)
        # Inspection only: execution verification persists audit evidence and is not a read API.
        # Verify governed DB metadata here and only the requested binary in the service.
        return resolve_training_run_dataset(training_run_id, required_splits=())

    def sample_reference(self, datasource: str | None, dataset_version_id: str,
                         split: str, sample_id: str) -> tuple[dict[str, Any], Counter] | None:
        with read_only_transaction(datasource) as connection:
            ids = select_dataset_sample_ids(connection, dataset_version_id, split, sample_id, 1)
            if not ids:
                return None
            rows = select_dataset_sample_records(connection, dataset_version_id)
        collisions = Counter((row['split_name'], row['class_name'], row['source_filename']) for row in rows)
        row = next((row for row in rows if str(row['source_record_id']) == str(ids[0]) and row['split_name'] == split), None)
        return (row, collisions) if row else None
