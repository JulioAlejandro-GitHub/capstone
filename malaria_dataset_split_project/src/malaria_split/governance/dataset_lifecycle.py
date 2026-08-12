"""Service-layer lifecycle helpers backed by PostgreSQL enforcement."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Connection, text


ALLOWED_LIFECYCLE_TRANSITIONS = {
    "DRAFT": frozenset({"GENERATED", "ARCHIVED"}),
    "GENERATED": frozenset({"VALIDATED", "ARCHIVED"}),
    "VALIDATED": frozenset({"FROZEN", "ARCHIVED"}),
    "FROZEN": frozenset({"ARCHIVED"}),
    "ARCHIVED": frozenset(),
}


class InvalidLifecycleTransition(ValueError):
    pass


def transition_dataset_version(
    connection: Connection, dataset_version_id: UUID, target_status: str
) -> dict:
    current = connection.execute(
        text("SELECT status FROM dataset_versions WHERE id=:id FOR UPDATE"),
        {"id": dataset_version_id},
    ).scalar_one()
    if target_status not in ALLOWED_LIFECYCLE_TRANSITIONS[current]:
        raise InvalidLifecycleTransition(f"{current} -> {target_status} is not allowed")
    return dict(
        connection.execute(
            text("UPDATE dataset_versions SET status=:status WHERE id=:id RETURNING *"),
            {"id": dataset_version_id, "status": target_status},
        ).mappings().one()
    )


def validate_run_dataset_snapshot(
    requested_dataset_version_id: UUID,
    persisted_dataset_version_id: UUID,
    requested_materialization_id: UUID,
    persisted_materialization_id: UUID,
) -> None:
    """Future run creation guard: snapshots cannot change after persistence."""
    if requested_dataset_version_id != persisted_dataset_version_id:
        raise ValueError("RUN_DATASET_VERSION_IMMUTABLE")
    if requested_materialization_id != persisted_materialization_id:
        raise ValueError("RUN_MATERIALIZATION_IMMUTABLE")
