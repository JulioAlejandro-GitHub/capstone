"""Strict transactional lifecycle operations for persisted EVALUATE runs."""

from __future__ import annotations

import json
import math
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator, Mapping
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.malaria_dl.persistence.database import get_engine


class EvaluationFinalizationError(RuntimeError):
    """Base error for the strict EVALUATE lifecycle contract."""


class EvaluationRunNotFoundError(EvaluationFinalizationError):
    def __init__(self, evaluation_run_id: UUID):
        self.evaluation_run_id = evaluation_run_id
        super().__init__(f"EVALUATE run not found: {evaluation_run_id}")


class NotEvaluationRunError(EvaluationFinalizationError):
    def __init__(self, run_id: UUID):
        self.run_id = run_id
        super().__init__(f"Run is not an EVALUATE: {run_id}")


class EvaluationFinalizationConflictError(EvaluationFinalizationError):
    def __init__(
        self,
        evaluation_run_id: UUID,
        *,
        expected_status: str,
        observed_status: str | None,
    ):
        self.evaluation_run_id = evaluation_run_id
        self.expected_status = expected_status
        self.observed_status = observed_status
        super().__init__(
            f"EVALUATE finalization conflict for {evaluation_run_id}: "
            f"expected={expected_status}, observed={observed_status or 'unknown'}"
        )


class InvalidEvaluationTransitionError(EvaluationFinalizationError):
    def __init__(
        self,
        evaluation_run_id: UUID,
        *,
        previous_status: str,
        target_status: str,
    ):
        self.evaluation_run_id = evaluation_run_id
        self.previous_status = previous_status
        self.target_status = target_status
        super().__init__(
            f"Invalid EVALUATE transition for {evaluation_run_id}: "
            f"{previous_status} -> {target_status}"
        )


class EvaluationFinalizationDataIntegrityError(EvaluationFinalizationError):
    """The persisted EVALUATE row is inconsistent with its lifecycle status."""


@dataclass(frozen=True, slots=True)
class EvaluationFinalizationResult:
    evaluation_run_id: UUID
    previous_status: str
    final_status: str
    changed: bool
    completed_at: datetime
    duration_seconds: float | None


@dataclass(frozen=True, slots=True)
class EvaluationFailureResult:
    evaluation_run_id: UUID
    previous_status: str
    final_status: str
    changed: bool
    failed_at: datetime | None


_LOCK_RUN = text(
    """
    SELECT
        id AS evaluation_run_id,
        run_type,
        status,
        started_at,
        finished_at AS completed_at,
        duration_seconds,
        metadata
    FROM runs
    WHERE id = :evaluation_run_id
    FOR UPDATE
    """
)

_GET_RUN_STATUS = text(
    "SELECT status FROM runs WHERE id = :evaluation_run_id"
)

_UPDATE_EVALUATION_COMPLETED = text(
    """
    UPDATE runs
    SET status = 'completed',
        finished_at = CAST(:completed_at AS timestamptz),
        duration_seconds = COALESCE(
            CAST(:duration_seconds AS numeric),
            EXTRACT(
                EPOCH FROM (
                    CAST(:completed_at AS timestamptz) - started_at
                )
            )
        ),
        updated_at = CURRENT_TIMESTAMP,
        metadata = COALESCE(metadata, '{}'::jsonb) || CAST(:summary AS jsonb)
    WHERE id = :evaluation_run_id
      AND run_type = 'evaluation'
      AND status = 'started'
    RETURNING
        id AS evaluation_run_id,
        status,
        finished_at AS completed_at,
        duration_seconds
    """
)

_UPDATE_EVALUATION_FAILED = text(
    """
    UPDATE runs
    SET status = 'failed',
        finished_at = CURRENT_TIMESTAMP,
        duration_seconds = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - started_at)),
        updated_at = CURRENT_TIMESTAMP,
        metadata = COALESCE(metadata, '{}'::jsonb) || CAST(:summary AS jsonb)
    WHERE id = :evaluation_run_id
      AND run_type = 'evaluation'
      AND status = 'started'
    RETURNING
        id AS evaluation_run_id,
        status,
        finished_at AS failed_at
    """
)


def _uuid(value: UUID | str) -> UUID:
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise EvaluationFinalizationDataIntegrityError(
            "evaluation_run_id is not a valid UUID"
        ) from exc


def _aware_datetime(value: datetime | None, *, field_name: str) -> datetime:
    if value is None:
        raise EvaluationFinalizationDataIntegrityError(
            f"EVALUATE {field_name} is missing"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise EvaluationFinalizationDataIntegrityError(
            f"EVALUATE {field_name} must be timezone-aware"
        )
    return value


def _duration(value: object | None) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise EvaluationFinalizationDataIntegrityError(
            "EVALUATE duration_seconds is not numeric"
        ) from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise EvaluationFinalizationDataIntegrityError(
            "EVALUATE duration_seconds must be finite and non-negative"
        )
    return parsed


def _json_safe(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "item") and callable(value.item):
        try:
            return value.item()
        except Exception:
            pass
    if hasattr(value, "tolist") and callable(value.tolist):
        try:
            return value.tolist()
        except Exception:
            pass
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return value


def _summary(value: Mapping[str, object] | None) -> str:
    if value is None:
        return "{}"
    if not isinstance(value, Mapping):
        raise EvaluationFinalizationDataIntegrityError(
            "EVALUATE summary must be a mapping"
        )
    try:
        return json.dumps(_json_safe(value), ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise EvaluationFinalizationDataIntegrityError(
            "EVALUATE summary is not JSON serializable"
        ) from exc


@contextmanager
def _service_connection(
    connection: Connection | None,
) -> Iterator[Connection]:
    if connection is not None:
        yield connection
        return
    with get_engine().begin() as owned:
        yield owned


def _locked_run(connection: Connection, evaluation_run_id: UUID):
    row = connection.execute(
        _LOCK_RUN, {"evaluation_run_id": evaluation_run_id}
    ).mappings().one_or_none()
    if row is None:
        raise EvaluationRunNotFoundError(evaluation_run_id)
    if row["run_type"] != "evaluation":
        raise NotEvaluationRunError(evaluation_run_id)
    return row


def _observed_status(
    connection: Connection, evaluation_run_id: UUID
) -> str | None:
    row = connection.execute(
        _GET_RUN_STATUS, {"evaluation_run_id": evaluation_run_id}
    ).mappings().one_or_none()
    return str(row["status"]) if row is not None else None


def _completed_result(row, *, changed: bool) -> EvaluationFinalizationResult:
    completed_at = _aware_datetime(
        row.get("completed_at"), field_name="completed_at"
    )
    return EvaluationFinalizationResult(
        evaluation_run_id=_uuid(row["evaluation_run_id"]),
        previous_status="started" if changed else "completed",
        final_status="completed",
        changed=changed,
        completed_at=completed_at,
        duration_seconds=_duration(row.get("duration_seconds")),
    )


def finalize_evaluation_run(
    evaluation_run_id: UUID | str,
    *,
    completed_at: datetime | None = None,
    duration_seconds: float | None = None,
    summary: Mapping[str, object] | None = None,
    connection: Connection | None = None,
) -> EvaluationFinalizationResult:
    """Finalize one persisted EVALUATE with lock, CAS, and strict errors."""

    run_id = _uuid(evaluation_run_id)
    requested_completed_at = completed_at or datetime.now(UTC)
    _aware_datetime(requested_completed_at, field_name="completed_at")
    requested_duration = _duration(duration_seconds)
    serialized_summary = _summary(summary)

    with _service_connection(connection) as active:
        locked = _locked_run(active, run_id)
        current_status = locked.get("status")
        if current_status == "completed":
            return _completed_result(locked, changed=False)
        if current_status == "failed":
            raise InvalidEvaluationTransitionError(
                run_id,
                previous_status="failed",
                target_status="completed",
            )
        if current_status != "started":
            raise EvaluationFinalizationDataIntegrityError(
                f"Unknown EVALUATE status for {run_id}: {current_status!r}"
            )
        _aware_datetime(locked.get("started_at"), field_name="started_at")

        updated = active.execute(
            _UPDATE_EVALUATION_COMPLETED,
            {
                "evaluation_run_id": run_id,
                "completed_at": requested_completed_at,
                "duration_seconds": requested_duration,
                "summary": serialized_summary,
            },
        ).mappings().one_or_none()
        if updated is None:
            raise EvaluationFinalizationConflictError(
                run_id,
                expected_status="started",
                observed_status=_observed_status(active, run_id),
            )
        return _completed_result(updated, changed=True)


def fail_evaluation_run(
    evaluation_run_id: UUID | str,
    *,
    summary: Mapping[str, object] | None = None,
    connection: Connection | None = None,
) -> EvaluationFailureResult:
    """Mark a started EVALUATE failed without rewriting terminal runs."""

    run_id = _uuid(evaluation_run_id)
    serialized_summary = _summary(summary)
    with _service_connection(connection) as active:
        locked = _locked_run(active, run_id)
        current_status = locked.get("status")
        if current_status in {"completed", "failed"}:
            return EvaluationFailureResult(
                evaluation_run_id=run_id,
                previous_status=current_status,
                final_status=current_status,
                changed=False,
                failed_at=(
                    locked.get("completed_at")
                    if current_status == "failed"
                    else None
                ),
            )
        if current_status != "started":
            raise EvaluationFinalizationDataIntegrityError(
                f"Unknown EVALUATE status for {run_id}: {current_status!r}"
            )
        _aware_datetime(locked.get("started_at"), field_name="started_at")
        updated = active.execute(
            _UPDATE_EVALUATION_FAILED,
            {
                "evaluation_run_id": run_id,
                "summary": serialized_summary,
            },
        ).mappings().one_or_none()
        if updated is None:
            raise EvaluationFinalizationConflictError(
                run_id,
                expected_status="started",
                observed_status=_observed_status(active, run_id),
            )
        return EvaluationFailureResult(
            evaluation_run_id=_uuid(updated["evaluation_run_id"]),
            previous_status="started",
            final_status="failed",
            changed=True,
            failed_at=updated.get("failed_at"),
        )


__all__ = [
    "EvaluationFailureResult",
    "EvaluationFinalizationConflictError",
    "EvaluationFinalizationDataIntegrityError",
    "EvaluationFinalizationError",
    "EvaluationFinalizationResult",
    "EvaluationRunNotFoundError",
    "InvalidEvaluationTransitionError",
    "NotEvaluationRunError",
    "fail_evaluation_run",
    "finalize_evaluation_run",
]
