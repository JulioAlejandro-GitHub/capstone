"""Persist TRAIN release eligibility derived only from TRAIN/EVALUATE lineage."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Mapping
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.malaria_dl.persistence.database import get_engine
from src.malaria_dl.persistence.training_release import (
    NotTrainingRunError,
    TrainingReleaseDataIntegrityError,
    TrainingReleaseState,
    TrainingReleaseStatus,
    TrainingRunNotFoundError,
    set_training_release_status,
)


ELIGIBILITY_ACTOR = "system:training_release_eligibility"
ELIGIBLE_REASON = "eligibility:train_and_evaluate_completed"
TRAINING_NOT_COMPLETED_REASON = "eligibility:training_not_completed"
COMPLETED_EVALUATE_NOT_FOUND_REASON = (
    "eligibility:completed_evaluate_not_found"
)


@dataclass(frozen=True, slots=True)
class TrainingReleaseEligibilityDecision:
    training_run_id: UUID
    training_completed: bool
    completed_evaluate_exists: bool
    eligible: bool
    previous_status: TrainingReleaseStatus | None
    target_status: TrainingReleaseStatus
    final_state: TrainingReleaseState
    changed: bool
    productive_protected: bool

    def __post_init__(self) -> None:
        if self.productive_protected:
            if (
                self.target_status is not TrainingReleaseStatus.PRODUCTIVE_STAGE2
                or self.final_state.release_status
                is not TrainingReleaseStatus.PRODUCTIVE_STAGE2
                or self.changed
            ):
                raise TrainingReleaseDataIntegrityError(
                    "Invalid productive protection decision"
                )
            return
        if self.eligible != (
            self.training_completed and self.completed_evaluate_exists
        ):
            raise TrainingReleaseDataIntegrityError(
                "Eligibility decision is internally inconsistent"
            )
        expected_target = (
            TrainingReleaseStatus.AVAILABLE_TO_PUBLISH
            if self.eligible
            else TrainingReleaseStatus.NOT_AVAILABLE
        )
        if self.target_status is not expected_target:
            raise TrainingReleaseDataIntegrityError(
                "Eligibility target is internally inconsistent"
            )


_LOCK_TRAINING = text(
    """
    SELECT
        id AS training_run_id,
        status AS training_status,
        release_status,
        release_updated_at,
        release_changed_by,
        release_reason
    FROM runs
    WHERE id = :training_run_id
      AND run_type = 'training'
    FOR UPDATE
    """
)

_GET_RUN_TYPE = text("SELECT run_type FROM runs WHERE id = :training_run_id")

_ELIGIBILITY = text(
    """
    SELECT
        training.status = 'completed' AS training_completed,
        EXISTS (
            SELECT 1
            FROM run_lineage AS lineage
            JOIN runs AS evaluation
              ON evaluation.id = lineage.child_run_id
             AND evaluation.run_type = 'evaluation'
             AND evaluation.status = 'completed'
            WHERE lineage.parent_run_id = training.id
              AND lineage.relationship_type = 'evaluates_checkpoint_from'
        ) AS completed_evaluate_exists
    FROM runs AS training
    WHERE training.id = :training_run_id
      AND training.run_type = 'training'
    """
)


def _uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _status(value: str | TrainingReleaseStatus | None):
    if value is None or isinstance(value, TrainingReleaseStatus):
        return value
    try:
        return TrainingReleaseStatus(value)
    except (TypeError, ValueError) as exc:
        raise TrainingReleaseDataIntegrityError(
            "Unknown TRAIN release status"
        ) from exc


def _state(row: Mapping) -> TrainingReleaseState:
    status = _status(row["release_status"])
    if status is None:
        raise TrainingReleaseDataIntegrityError("TRAIN release status is NULL")
    return TrainingReleaseState(
        training_run_id=_uuid(row["training_run_id"]),
        release_status=status,
        release_updated_at=row["release_updated_at"],
        release_changed_by=row["release_changed_by"],
        release_reason=row["release_reason"],
    )


def _missing_or_wrong_type(connection: Connection, run_id: UUID) -> None:
    run_type = connection.execute(
        _GET_RUN_TYPE, {"training_run_id": run_id}
    ).scalar_one_or_none()
    if run_type is None:
        raise TrainingRunNotFoundError(run_id)
    raise NotTrainingRunError(run_id)


@contextmanager
def _service_connection(connection: Connection | None) -> Iterator[Connection]:
    if connection is not None:
        yield connection
        return
    with get_engine().begin() as owned:
        yield owned


def reconcile_training_release_eligibility(
    training_run_id: UUID | str,
    *,
    connection: Connection | None = None,
) -> TrainingReleaseEligibilityDecision:
    run_id = _uuid(training_run_id)
    with _service_connection(connection) as active:
        locked = active.execute(
            _LOCK_TRAINING, {"training_run_id": run_id}
        ).mappings().one_or_none()
        if locked is None:
            _missing_or_wrong_type(active, run_id)

        previous = _status(locked["release_status"])
        if previous is TrainingReleaseStatus.PRODUCTIVE_STAGE2:
            current = _state(locked)
            return TrainingReleaseEligibilityDecision(
                training_run_id=run_id,
                training_completed=locked["training_status"] == "completed",
                completed_evaluate_exists=False,
                eligible=False,
                previous_status=previous,
                target_status=TrainingReleaseStatus.PRODUCTIVE_STAGE2,
                final_state=current,
                changed=False,
                productive_protected=True,
            )

        eligibility = active.execute(
            _ELIGIBILITY, {"training_run_id": run_id}
        ).mappings().one()
        training_completed = bool(eligibility["training_completed"])
        completed_evaluate_exists = bool(
            eligibility["completed_evaluate_exists"]
        )
        eligible = training_completed and completed_evaluate_exists
        target = (
            TrainingReleaseStatus.AVAILABLE_TO_PUBLISH
            if eligible
            else TrainingReleaseStatus.NOT_AVAILABLE
        )

        if previous is target:
            final_state = _state(locked)
            changed = False
        else:
            reason = (
                ELIGIBLE_REASON
                if eligible
                else (
                    TRAINING_NOT_COMPLETED_REASON
                    if not training_completed
                    else COMPLETED_EVALUATE_NOT_FOUND_REASON
                )
            )
            result = set_training_release_status(
                run_id,
                target,
                changed_by=ELIGIBILITY_ACTOR,
                reason=reason,
                expected_current_status=previous,
                connection=active,
            )
            final_state = result.state
            changed = result.changed

        return TrainingReleaseEligibilityDecision(
            training_run_id=run_id,
            training_completed=training_completed,
            completed_evaluate_exists=completed_evaluate_exists,
            eligible=eligible,
            previous_status=previous,
            target_status=target,
            final_state=final_state,
            changed=changed,
            productive_protected=False,
        )


__all__ = [
    "COMPLETED_EVALUATE_NOT_FOUND_REASON",
    "ELIGIBILITY_ACTOR",
    "ELIGIBLE_REASON",
    "TRAINING_NOT_COMPLETED_REASON",
    "TrainingReleaseEligibilityDecision",
    "reconcile_training_release_eligibility",
]
