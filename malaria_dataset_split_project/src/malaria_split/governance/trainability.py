"""Derived TRAINABLE state and deterministic resource selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import Connection, text


REQUIRED_LOGICAL_VALIDATION_CHECKS = (
    "identity_coverage",
    "identity_conflicts",
    "patient_train_val_overlap",
    "patient_train_test_overlap",
    "patient_val_test_overlap",
    "duplicate_cross_split_overlap",
    "assignment_count",
    "source_record_count",
    "split_completeness",
    "class_presence_train",
    "class_presence_val",
    "class_presence_test",
)

DATASET_NOT_FROZEN = "DATASET_NOT_FROZEN"
VALIDATION_NOT_PASS = "VALIDATION_NOT_PASS"
NO_READY_RECONCILED_MATERIALIZATION = "NO_READY_RECONCILED_MATERIALIZATION"


@dataclass(frozen=True, slots=True)
class TrainabilityResult:
    dataset_version_id: UUID
    trainable: bool
    reasons: tuple[str, ...]
    resolved_materialization_id: UUID | None


def resolve_trainable_materialization(
    connection: Connection, dataset_version_id: UUID
) -> dict[str, Any] | None:
    row = connection.execute(
        text(
            """
            SELECT * FROM dataset_materializations
            WHERE dataset_version_id=:version_id
              AND status='READY' AND reconciliation_status='PASS'
            ORDER BY attempt_number DESC, completed_at DESC NULLS LAST, id DESC
            LIMIT 1
            """
        ),
        {"version_id": dataset_version_id},
    ).mappings().one_or_none()
    return dict(row) if row else None


def _latest_validation_checks(
    connection: Connection, dataset_version_id: UUID
) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        text(
            """
            SELECT DISTINCT ON (check_name) *
            FROM dataset_split_validation_checks
            WHERE dataset_version_id=:version_id
            ORDER BY check_name, executed_at DESC, id DESC
            """
        ),
        {"version_id": dataset_version_id},
    ).mappings()
    return {row["check_name"]: dict(row) for row in rows}


def logical_validation_passes(connection: Connection, dataset_version_id: UUID) -> bool:
    checks = _latest_validation_checks(connection, dataset_version_id)
    for name in REQUIRED_LOGICAL_VALIDATION_CHECKS:
        check = checks.get(name)
        if not check or not check["blocking_for_validation"] or check["status"] != "PASS":
            return False
    return not any(
        check["blocking_for_validation"] and check["status"] == "FAIL"
        for check in checks.values()
    )


def get_dataset_version_trainability(
    connection: Connection, dataset_version_id: UUID
) -> TrainabilityResult:
    status = connection.execute(
        text("SELECT status FROM dataset_versions WHERE id=:id"),
        {"id": dataset_version_id},
    ).scalar_one()
    reasons: list[str] = []
    if status != "FROZEN":
        reasons.append(DATASET_NOT_FROZEN)
    if not logical_validation_passes(connection, dataset_version_id):
        reasons.append(VALIDATION_NOT_PASS)
    materialization = resolve_trainable_materialization(connection, dataset_version_id)
    if materialization is None:
        reasons.append(NO_READY_RECONCILED_MATERIALIZATION)
    return TrainabilityResult(
        dataset_version_id=dataset_version_id,
        trainable=not reasons,
        reasons=tuple(reasons),
        resolved_materialization_id=materialization["id"] if materialization else None,
    )


def is_dataset_version_trainable(connection: Connection, dataset_version_id: UUID) -> bool:
    return get_dataset_version_trainability(connection, dataset_version_id).trainable


def list_trainable_dataset_versions(connection: Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        text(
            """
            SELECT id,name,semantic_version,status,methodology_json,grouping_field,frozen_at
            FROM dataset_versions WHERE status='FROZEN'
            ORDER BY frozen_at DESC NULLS LAST, id DESC
            """
        )
    ).mappings()
    result = []
    for row in rows:
        state = get_dataset_version_trainability(connection, row["id"])
        if state.trainable:
            result.append(
                {
                    "dataset_version_id": row["id"],
                    "name": row["name"],
                    "semantic_version": row["semantic_version"],
                    "status": row["status"],
                    "methodology": row["methodology_json"],
                    "grouping_field": row["grouping_field"],
                    "frozen_at": row["frozen_at"],
                    "resolved_materialization_id": state.resolved_materialization_id,
                }
            )
    return result


def resolve_default_trainable_dataset_version(
    connection: Connection,
) -> dict[str, Any] | None:
    candidates = list_trainable_dataset_versions(connection)
    return candidates[0] if candidates else None
