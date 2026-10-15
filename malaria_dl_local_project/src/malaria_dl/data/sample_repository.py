"""Read sample identities using the caller's PostgreSQL connection/transaction."""
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection


def select_dataset_sample_ids(
    connection: Connection,
    dataset_version_id: UUID | str,
    split: str,
    sample_id: UUID | str | None = None,
    limit: int | None = None,
) -> list[UUID]:
    """Keep EXPLAIN's exact predicates, deterministic order and LIMIT NULL semantics."""
    return list(connection.execute(text("""
        SELECT source_record_id FROM dataset_split_assignments
        WHERE dataset_version_id=CAST(:dataset AS uuid) AND split_name=:split
          AND (CAST(:sample AS uuid) IS NULL OR source_record_id=CAST(:sample AS uuid))
        ORDER BY source_record_id LIMIT :limit
    """), {"dataset": str(dataset_version_id), "split": split,
           "sample": str(sample_id) if sample_id is not None else None, "limit": limit}).scalars())


def select_dataset_sample_records(
    connection: Connection, dataset_version_id: UUID | str,
) -> list[dict[str, Any]]:
    """Shared source records for the governed materialization, including collisions."""
    return [dict(row) for row in connection.execute(text("""
        SELECT a.source_record_id,a.clinical_identity_id,a.split_name,r.class_name,
               r.source_filename,r.source_file_sha256
        FROM dataset_split_assignments a JOIN dataset_source_records r ON r.id=a.source_record_id
        WHERE a.dataset_version_id=CAST(:id AS uuid) ORDER BY a.source_record_id
    """), {"id": str(dataset_version_id)}).mappings().all()]
