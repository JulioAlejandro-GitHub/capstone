"""Canonical persistence contract for release state owned by a TRAIN run."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Iterator, Mapping, Sequence
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from src.malaria_dl.persistence.database import get_engine


class TrainingReleaseStatus(str, Enum):
    NOT_AVAILABLE = "not_available"
    AVAILABLE_TO_PUBLISH = "available_to_publish"
    PRODUCTIVE_STAGE2 = "productive_stage2"


class TrainingReleaseError(RuntimeError):
    """Base error for the persisted TRAIN release contract."""


class TrainingRunNotFoundError(TrainingReleaseError):
    def __init__(self, training_run_id: UUID):
        self.training_run_id = training_run_id
        super().__init__(f"TRAIN run not found: {training_run_id}")


class NotTrainingRunError(TrainingReleaseError):
    def __init__(self, run_id: UUID):
        self.run_id = run_id
        super().__init__(f"Run is not a TRAIN: {run_id}")


class TrainingReleaseDataIntegrityError(TrainingReleaseError):
    """Persisted release columns do not satisfy the domain contract."""


class TrainingReleaseConflictError(TrainingReleaseError):
    def __init__(
        self,
        training_run_id: UUID,
        expected: TrainingReleaseStatus | None,
        actual: TrainingReleaseStatus | None,
    ):
        self.training_run_id = training_run_id
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Release status conflict for {training_run_id}: "
            f"expected={expected.value if expected else 'NULL'}, "
            f"actual={actual.value if actual else 'NULL'}"
        )


class ProductiveStage2ConflictError(TrainingReleaseError):
    """A different TRAIN already occupies the unique productive slot."""


@dataclass(frozen=True, slots=True)
class TrainingReleaseState:
    training_run_id: UUID
    release_status: TrainingReleaseStatus
    release_updated_at: datetime
    release_changed_by: str | None
    release_reason: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.training_run_id, UUID):
            raise TrainingReleaseDataIntegrityError("TRAIN id is not a UUID")
        if not isinstance(self.release_status, TrainingReleaseStatus):
            raise TrainingReleaseDataIntegrityError("Unknown TRAIN release status")
        if not isinstance(self.release_updated_at, datetime):
            raise TrainingReleaseDataIntegrityError("Release timestamp is missing")
        if (
            self.release_updated_at.tzinfo is None
            or self.release_updated_at.utcoffset() is None
        ):
            raise TrainingReleaseDataIntegrityError(
                "Release timestamp must be timezone-aware"
            )


@dataclass(frozen=True, slots=True)
class TrainingReleaseWriteResult:
    state: TrainingReleaseState
    changed: bool


_RELEASE_COLUMNS = """
    id AS training_run_id,
    release_status,
    release_updated_at,
    release_changed_by,
    release_reason
"""

_GET_TRAINING = text(
    f"""
    SELECT {_RELEASE_COLUMNS}
    FROM runs
    WHERE id = :training_run_id
      AND run_type = 'training'
    """
)

_GET_TRAINING_FOR_UPDATE = text(
    f"""
    SELECT {_RELEASE_COLUMNS}
    FROM runs
    WHERE id = :training_run_id
      AND run_type = 'training'
    FOR UPDATE
    """
)

_GET_RUN_TYPE = text("SELECT run_type FROM runs WHERE id = :training_run_id")

_LIST_TRAINING = text(
    f"""
    SELECT {_RELEASE_COLUMNS}, run_type
    FROM runs
    WHERE id IN :training_run_ids
    """
).bindparams(bindparam("training_run_ids", expanding=True))

_UPDATE_RELEASE = text(
    f"""
    UPDATE runs
    SET release_status = :target_status,
        release_updated_at = CURRENT_TIMESTAMP,
        release_changed_by = :changed_by,
        release_reason = :reason
    WHERE id = :training_run_id
      AND run_type = 'training'
      AND release_status IS NOT DISTINCT FROM :current_status
    RETURNING {_RELEASE_COLUMNS}
    """
)


class _AnyCurrentReleaseStatus:
    pass


ANY_CURRENT_RELEASE_STATUS = _AnyCurrentReleaseStatus()


def _uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _status(value: TrainingReleaseStatus | str) -> TrainingReleaseStatus:
    if isinstance(value, TrainingReleaseStatus):
        return value
    try:
        return TrainingReleaseStatus(value)
    except (TypeError, ValueError) as exc:
        raise TrainingReleaseDataIntegrityError("Unknown TRAIN release status") from exc


def _state(row) -> TrainingReleaseState:
    data = row if isinstance(row, Mapping) else row._mapping
    raw_status = data.get("release_status")
    if raw_status is None:
        raise TrainingReleaseDataIntegrityError("TRAIN release status is NULL")
    return TrainingReleaseState(
        training_run_id=_uuid(data["training_run_id"]),
        release_status=_status(raw_status),
        release_updated_at=data.get("release_updated_at"),
        release_changed_by=data.get("release_changed_by"),
        release_reason=data.get("release_reason"),
    )


def _missing_or_wrong_type(connection: Connection, training_run_id: UUID) -> None:
    run_type = connection.execute(
        _GET_RUN_TYPE, {"training_run_id": training_run_id}
    ).scalar_one_or_none()
    if run_type is None:
        raise TrainingRunNotFoundError(training_run_id)
    raise NotTrainingRunError(training_run_id)


def _locked_training_release_row(connection: Connection, training_run_id: UUID):
    row = connection.execute(
        _GET_TRAINING_FOR_UPDATE, {"training_run_id": training_run_id}
    ).mappings().one_or_none()
    if row is None:
        _missing_or_wrong_type(connection, training_run_id)
    return row


@contextmanager
def _read_connection(connection: Connection | None) -> Iterator[Connection]:
    if connection is not None:
        yield connection
        return
    with get_engine().connect() as owned:
        yield owned


@contextmanager
def _write_connection(connection: Connection | None) -> Iterator[Connection]:
    if connection is not None:
        yield connection
        return
    with get_engine().begin() as owned:
        yield owned


def get_training_release_state(
    training_run_id: UUID | str,
    *,
    connection: Connection | None = None,
    for_update: bool = False,
) -> TrainingReleaseState:
    run_id = _uuid(training_run_id)
    statement = _GET_TRAINING_FOR_UPDATE if for_update else _GET_TRAINING
    with _read_connection(connection) as active:
        row = active.execute(
            statement, {"training_run_id": run_id}
        ).mappings().one_or_none()
        if row is None:
            _missing_or_wrong_type(active, run_id)
        return _state(row)


def list_training_release_states(
    training_run_ids: Sequence[UUID | str],
    *,
    connection: Connection | None = None,
) -> Mapping[UUID, TrainingReleaseState]:
    unique_ids = tuple(dict.fromkeys(_uuid(value) for value in training_run_ids))
    if not unique_ids:
        return MappingProxyType({})

    with _read_connection(connection) as active:
        rows = active.execute(
            _LIST_TRAINING, {"training_run_ids": unique_ids}
        ).mappings().all()

    by_id = {_uuid(row["training_run_id"]): row for row in rows}
    for run_id in unique_ids:
        row = by_id.get(run_id)
        if row is None:
            raise TrainingRunNotFoundError(run_id)
        if row["run_type"] != "training":
            raise NotTrainingRunError(run_id)
    return MappingProxyType({run_id: _state(by_id[run_id]) for run_id in unique_ids})


def _constraint_name(error: IntegrityError) -> str | None:
    diagnostic = getattr(getattr(error, "orig", None), "diag", None)
    return getattr(diagnostic, "constraint_name", None)


def set_training_release_status(
    training_run_id: UUID | str,
    target_status: TrainingReleaseStatus | str,
    *,
    changed_by: str | None,
    reason: str | None,
    expected_current_status: (
        TrainingReleaseStatus | str | None | _AnyCurrentReleaseStatus
    ) = ANY_CURRENT_RELEASE_STATUS,
    connection: Connection | None = None,
) -> TrainingReleaseWriteResult:
    run_id = _uuid(training_run_id)
    target = _status(target_status)
    expected = (
        expected_current_status
        if expected_current_status is ANY_CURRENT_RELEASE_STATUS
        else (
            _status(expected_current_status)
            if expected_current_status is not None
            else None
        )
    )

    with _write_connection(connection) as active:
        current_row = _locked_training_release_row(active, run_id)
        current_status = (
            _status(current_row["release_status"])
            if current_row["release_status"] is not None
            else None
        )
        if expected is not ANY_CURRENT_RELEASE_STATUS and current_status != expected:
            raise TrainingReleaseConflictError(
                run_id, expected, current_status
            )
        if current_status == target:
            return TrainingReleaseWriteResult(
                state=_state(current_row), changed=False
            )

        try:
            with active.begin_nested():
                row = active.execute(
                    _UPDATE_RELEASE,
                    {
                        "training_run_id": run_id,
                        "target_status": target.value,
                        "current_status": (
                            current_status.value if current_status is not None else None
                        ),
                        "changed_by": changed_by,
                        "reason": reason,
                    },
                ).mappings().one_or_none()
        except IntegrityError as exc:
            if _constraint_name(exc) == "uq_runs_single_productive_stage2":
                raise ProductiveStage2ConflictError(
                    "A productive Stage 2 TRAIN already exists"
                ) from exc
            raise

        if row is None:
            actual_row = _locked_training_release_row(active, run_id)
            actual = (
                _status(actual_row["release_status"])
                if actual_row["release_status"] is not None
                else None
            )
            raise TrainingReleaseConflictError(
                run_id, current_status, actual
            )
        return TrainingReleaseWriteResult(state=_state(row), changed=True)


__all__ = [
    "ANY_CURRENT_RELEASE_STATUS",
    "NotTrainingRunError",
    "ProductiveStage2ConflictError",
    "TrainingReleaseConflictError",
    "TrainingReleaseDataIntegrityError",
    "TrainingReleaseError",
    "TrainingReleaseState",
    "TrainingReleaseStatus",
    "TrainingReleaseWriteResult",
    "TrainingRunNotFoundError",
    "get_training_release_state",
    "list_training_release_states",
    "set_training_release_status",
]
