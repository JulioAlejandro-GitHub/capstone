"""One transaction for EVALUATE lineage, completion, and TRAIN release."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Mapping
from uuid import UUID

from sqlalchemy.engine import Connection

from src.malaria_dl.evaluation.evaluation_finalization_service import (
    EvaluationFinalizationResult,
    finalize_evaluation_run,
)
from src.malaria_dl.evaluation.evaluation_training_lineage_service import (
    EvaluationTrainingLineageResult,
    create_or_confirm_evaluation_training_lineage,
)
from src.malaria_dl.governance.services.training_release_eligibility_service import (
    TrainingReleaseEligibilityDecision,
    reconcile_training_release_eligibility,
)
from src.malaria_dl.persistence.database import get_engine


@dataclass(frozen=True, slots=True)
class EvaluationTerminalResult:
    lineage: EvaluationTrainingLineageResult
    finalization: EvaluationFinalizationResult
    release_decision: TrainingReleaseEligibilityDecision


@contextmanager
def _terminal_connection(
    connection: Connection | None,
) -> Iterator[Connection]:
    if connection is not None:
        yield connection
        return
    with get_engine().begin() as owned:
        yield owned


def finalize_evaluation_with_lineage(
    *,
    training_run_id: UUID | str,
    evaluation_run_id: UUID | str,
    model_version_id: UUID | str,
    checkpoint_artifact_id: UUID | str,
    checkpoint_path: str | None = None,
    confidence: str | None = None,
    lineage_metadata: Mapping[str, object] | None = None,
    completed_at: datetime | None = None,
    duration_seconds: float | None = None,
    summary: Mapping[str, object] | None = None,
    connection: Connection | None = None,
) -> EvaluationTerminalResult:
    """Confirm lineage, complete EVALUATE, and reconcile its TRAIN atomically."""

    with _terminal_connection(connection) as active:
        lineage = create_or_confirm_evaluation_training_lineage(
            training_run_id=training_run_id,
            evaluation_run_id=evaluation_run_id,
            model_version_id=model_version_id,
            checkpoint_artifact_id=checkpoint_artifact_id,
            checkpoint_path=checkpoint_path,
            confidence=confidence,
            metadata=lineage_metadata,
            connection=active,
        )
        finalization = finalize_evaluation_run(
            evaluation_run_id,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            summary=summary,
            connection=active,
        )
        release_decision = reconcile_training_release_eligibility(
            lineage.training_run_id,
            connection=active,
        )
        return EvaluationTerminalResult(
            lineage=lineage,
            finalization=finalization,
            release_decision=release_decision,
        )


__all__ = [
    "EvaluationTerminalResult",
    "finalize_evaluation_with_lineage",
]
