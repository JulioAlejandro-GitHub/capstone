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


class ScientificBootstrapRepository:
    """Set-oriented primitives used by the atomic scientific bootstrap."""

    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def rows_by_key(self, table: str, columns: str, key: str) -> dict[Any, Mapping[str, Any]]:
        allowed = {
            "clinical_identities": "source_identifier",
            "dataset_source_records": "source_record_key",
            "identity_evidence": "source_record_id",
        }
        if allowed.get(table) != key:
            raise ValueError("Unsupported bootstrap lookup")
        rows = self.connection.execute(text(f"SELECT {columns} FROM {table}")).mappings()
        return {row[key]: row for row in rows}

    def insert_many(self, statement: str, rows: list[dict[str, Any]], batch_size: int = 1000) -> None:
        sql = text(statement)
        for offset in range(0, len(rows), batch_size):
            self.connection.execute(sql, rows[offset : offset + batch_size])

    def scalar(self, statement: str, parameters: Mapping[str, Any] | None = None) -> Any:
        return self.connection.execute(text(statement), parameters or {}).scalar_one()
