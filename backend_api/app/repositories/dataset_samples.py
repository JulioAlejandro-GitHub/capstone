"""Read-only bridge to the same governed sample identities consumed by EXPLAIN."""
from collections import Counter
from typing import Any
from uuid import UUID

from sqlalchemy import text
from app.db import read_only_transaction, resolve_datasource
from src.malaria_dl.data.governed_dataset import GovernedDatasetSnapshot, local_dataset_root, training_dataset_metadata


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
        # Serving one image: the TRAIN's persisted snapshot (frozen version, its root) is enough. The full population
        # was verified when TRAIN/EVALUATE/EXPLAIN ran; the service checks the requested file's SHA-256.
        persisted = training_dataset_metadata(training_run_id)
        return GovernedDatasetSnapshot(
            UUID(persisted['dataset_version_id']), UUID(persisted['dataset_materialization_id']),
            local_dataset_root(persisted['dataset_root']), persisted['patient_assignment_fingerprint'],
            persisted['record_assignment_fingerprint'], persisted['source_population_fingerprint'],
            persisted['clinical_identity_fingerprint'], persisted['counts'])

    def sample_reference(self, datasource: str | None, dataset_version_id: str,
                         split: str, sample_id: str) -> tuple[dict[str, Any], Counter] | None:
        # The record plus how many records of the version share its split/class/filename: the only input the
        # materialized path needs to disambiguate collisions.
        with read_only_transaction(datasource) as connection:
            row = connection.execute(text("""
                SELECT a.source_record_id,a.clinical_identity_id,a.split_name,r.class_name,
                       r.source_filename,r.source_file_sha256,
                       (SELECT count(*) FROM dataset_split_assignments a2
                        JOIN dataset_source_records r2 ON r2.id=a2.source_record_id
                        WHERE a2.dataset_version_id=a.dataset_version_id AND a2.split_name=a.split_name
                          AND r2.class_name=r.class_name AND r2.source_filename=r.source_filename) AS collisions
                FROM dataset_split_assignments a JOIN dataset_source_records r ON r.id=a.source_record_id
                WHERE a.dataset_version_id=CAST(:dataset AS uuid) AND a.split_name=:split
                  AND a.source_record_id=CAST(:sample AS uuid)
            """), {"dataset": dataset_version_id, "split": split, "sample": sample_id}).mappings().one_or_none()
        if row is None:
            return None
        record = dict(row)
        count = record.pop('collisions')
        return record, Counter({(record['split_name'], record['class_name'], record['source_filename']): count})
