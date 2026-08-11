"""Minimal domain-facing records for the PostgreSQL foundation.

The canonical schema remains the Alembic migration. These immutable records keep
repositories independent from backend API models and deliberately contain no ORM
hooks, bootstrap, or filesystem behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class DatasetVersionStatus(StrEnum):
    DRAFT = "DRAFT"
    GENERATED = "GENERATED"
    VALIDATED = "VALIDATED"
    FROZEN = "FROZEN"
    ARCHIVED = "ARCHIVED"


class MaterializationStatus(StrEnum):
    NOT_MATERIALIZED = "NOT_MATERIALIZED"
    MATERIALIZING = "MATERIALIZING"
    READY = "READY"
    FAILED = "FAILED"


class ReconciliationStatus(StrEnum):
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True, slots=True)
class DatasetVersionDefinition:
    id: UUID
    name: str
    semantic_version: str
    status: DatasetVersionStatus
    target_train_ratio: Decimal
    target_val_ratio: Decimal
    target_test_ratio: Decimal

    @property
    def is_trainable_without_physical_state(self) -> bool:
        """A lifecycle-only guard; READY/reconciliation are checked separately."""
        return self.status is DatasetVersionStatus.FROZEN


@dataclass(frozen=True, slots=True)
class MaterializationState:
    id: UUID
    dataset_version_id: UUID
    status: MaterializationStatus
    reconciliation_status: ReconciliationStatus

    @property
    def is_trainable_physical_state(self) -> bool:
        return (
            self.status is MaterializationStatus.READY
            and self.reconciliation_status is ReconciliationStatus.PASS
        )
