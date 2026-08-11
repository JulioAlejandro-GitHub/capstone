"""Small read/write primitives; callers own transaction boundaries."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import Connection, text


class DatasetVersionRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def get(self, dataset_version_id: UUID) -> Mapping[str, Any] | None:
        row = self._connection.execute(
            text("SELECT * FROM dataset_versions WHERE id = :id"),
            {"id": dataset_version_id},
        ).mappings().one_or_none()
        return row

    def add_draft(self, values: Mapping[str, Any]) -> UUID:
        """Persist an explicitly supplied draft; no scientific defaults are invented."""
        statement = text(
            """
            INSERT INTO dataset_versions (
              id, name, semantic_version, status, grouping_strategy, grouping_field,
              stratification_strategy, split_algorithm, split_algorithm_version,
              random_seed, target_train_ratio, target_val_ratio, target_test_ratio,
              positive_class, class_mapping, source_record_count, methodology_json
            ) VALUES (
              :id, :name, :semantic_version, 'DRAFT', :grouping_strategy, :grouping_field,
              :stratification_strategy, :split_algorithm, :split_algorithm_version,
              :random_seed, :target_train_ratio, :target_val_ratio, :target_test_ratio,
              :positive_class, CAST(:class_mapping AS jsonb), :source_record_count,
              CAST(:methodology_json AS jsonb)
            ) RETURNING id
            """
        )
        return self._connection.execute(statement, dict(values)).scalar_one()


class SourceRecordRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def get_by_source_key(
        self, dataset_id: UUID, source_record_key: str
    ) -> Mapping[str, Any] | None:
        return self._connection.execute(
            text(
                """
                SELECT * FROM dataset_source_records
                WHERE dataset_id = :dataset_id AND source_record_key = :source_record_key
                """
            ),
            {"dataset_id": dataset_id, "source_record_key": source_record_key},
        ).mappings().one_or_none()
