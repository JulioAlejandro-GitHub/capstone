"""Strict immutable lineage contract between one EVALUATE and one TRAIN."""

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, Mapping
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.malaria_dl.evaluation.evaluation_finalization_service import (
    EvaluationRunNotFoundError,
    NotEvaluationRunError,
)
from src.malaria_dl.persistence.database import get_engine


EVALUATION_RELATIONSHIP_TYPE = "evaluates_checkpoint_from"
LINEAGE_CONFIDENCES = {
    "explicit",
    "inferred_exact_checkpoint",
    "inferred_model_version",
    "inferred_heuristic",
    "unknown",
}


class EvaluationTrainingLineageError(RuntimeError):
    """Base error for strict EVALUATE-to-TRAIN lineage operations."""


class TrainingRunNotFoundError(EvaluationTrainingLineageError):
    def __init__(self, training_run_id: UUID):
        self.training_run_id = training_run_id
        super().__init__(f"TRAIN run not found: {training_run_id}")


class NotTrainingRunError(EvaluationTrainingLineageError):
    def __init__(self, run_id: UUID):
        self.run_id = run_id
        super().__init__(f"Run is not a TRAIN: {run_id}")


class EvaluationTrainingLineageConflictError(EvaluationTrainingLineageError):
    def __init__(
        self,
        evaluation_run_id: UUID,
        *,
        mismatched_fields: tuple[str, ...],
    ):
        self.evaluation_run_id = evaluation_run_id
        self.mismatched_fields = mismatched_fields
        fields = ", ".join(mismatched_fields)
        super().__init__(
            f"EVALUATE lineage identity conflict for {evaluation_run_id}: {fields}"
        )


class EvaluationTrainingLineageCardinalityError(
    EvaluationTrainingLineageError
):
    def __init__(self, evaluation_run_id: UUID, count: int):
        self.evaluation_run_id = evaluation_run_id
        self.count = count
        super().__init__(
            f"EVALUATE {evaluation_run_id} has {count} direct TRAIN lineages; "
            "expected at most one"
        )


class ModelVersionOwnershipError(EvaluationTrainingLineageError):
    """The requested model version does not belong to the requested TRAIN."""


class CheckpointArtifactOwnershipError(EvaluationTrainingLineageError):
    """The requested checkpoint artifact does not belong to the version/TRAIN."""


class EvaluationTrainingLineageDataIntegrityError(
    EvaluationTrainingLineageError
):
    """Persisted lineage data does not satisfy the strict contract."""


@dataclass(frozen=True, slots=True)
class EvaluationTrainingLineageResult:
    lineage_id: UUID
    training_run_id: UUID
    evaluation_run_id: UUID
    model_version_id: UUID
    checkpoint_artifact_id: UUID
    relationship_type: str
    created: bool


_LOCK_EVALUATION = text(
    """
    SELECT id, run_type
    FROM runs
    WHERE id = :evaluation_run_id
    FOR UPDATE
    """
)

_LOCK_TRAINING = text(
    """
    SELECT id, run_type
    FROM runs
    WHERE id = :training_run_id
    FOR UPDATE
    """
)

_GET_MODEL_VERSION = text(
    """
    SELECT
        id AS model_version_id,
        training_run_id,
        checkpoint_artifact_id
    FROM model_versions
    WHERE id = :model_version_id
    FOR KEY SHARE
    """
)

_GET_CHECKPOINT_ARTIFACT = text(
    """
    SELECT
        id AS checkpoint_artifact_id,
        run_id AS training_run_id
    FROM artifacts
    WHERE id = :checkpoint_artifact_id
    FOR KEY SHARE
    """
)

_GET_DIRECT_LINEAGES = text(
    """
    SELECT
        id AS lineage_id,
        parent_run_id AS training_run_id,
        child_run_id AS evaluation_run_id,
        relationship_type,
        model_version_id,
        checkpoint_artifact_id,
        checkpoint_path,
        confidence,
        metadata,
        created_at
    FROM run_lineage
    WHERE child_run_id = :evaluation_run_id
      AND relationship_type = 'evaluates_checkpoint_from'
    FOR UPDATE
    """
)

_INSERT_LINEAGE = text(
    """
    INSERT INTO run_lineage (
        parent_run_id,
        child_run_id,
        relationship_type,
        model_version_id,
        checkpoint_artifact_id,
        checkpoint_path,
        confidence,
        metadata
    )
    VALUES (
        :training_run_id,
        :evaluation_run_id,
        'evaluates_checkpoint_from',
        :model_version_id,
        :checkpoint_artifact_id,
        :checkpoint_path,
        :confidence,
        CAST(:metadata AS jsonb)
    )
    RETURNING
        id AS lineage_id,
        parent_run_id AS training_run_id,
        child_run_id AS evaluation_run_id,
        relationship_type,
        model_version_id,
        checkpoint_artifact_id
    """
)


def _uuid(value: UUID | str, *, field_name: str) -> UUID:
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise EvaluationTrainingLineageDataIntegrityError(
            f"{field_name} is not a valid UUID"
        ) from exc


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


def _metadata(value: Mapping[str, object] | None) -> str:
    if value is None:
        return "{}"
    if not isinstance(value, Mapping):
        raise EvaluationTrainingLineageDataIntegrityError(
            "lineage metadata must be a mapping"
        )
    try:
        return json.dumps(_json_safe(value), ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise EvaluationTrainingLineageDataIntegrityError(
            "lineage metadata is not JSON serializable"
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


def _lock_evaluation(connection: Connection, evaluation_run_id: UUID) -> None:
    row = connection.execute(
        _LOCK_EVALUATION, {"evaluation_run_id": evaluation_run_id}
    ).mappings().one_or_none()
    if row is None:
        raise EvaluationRunNotFoundError(evaluation_run_id)
    if row["run_type"] != "evaluation":
        raise NotEvaluationRunError(evaluation_run_id)


def _lock_training(connection: Connection, training_run_id: UUID) -> None:
    row = connection.execute(
        _LOCK_TRAINING, {"training_run_id": training_run_id}
    ).mappings().one_or_none()
    if row is None:
        raise TrainingRunNotFoundError(training_run_id)
    if row["run_type"] != "training":
        raise NotTrainingRunError(training_run_id)


def _validate_ownership(
    connection: Connection,
    *,
    training_run_id: UUID,
    model_version_id: UUID,
    checkpoint_artifact_id: UUID,
) -> None:
    version = connection.execute(
        _GET_MODEL_VERSION, {"model_version_id": model_version_id}
    ).mappings().one_or_none()
    if version is None:
        raise ModelVersionOwnershipError(
            f"Model version not found: {model_version_id}"
        )
    if _uuid(
        version["training_run_id"], field_name="model_versions.training_run_id"
    ) != training_run_id:
        raise ModelVersionOwnershipError(
            f"Model version {model_version_id} does not belong to TRAIN "
            f"{training_run_id}"
        )
    version_artifact_id = version.get("checkpoint_artifact_id")
    if version_artifact_id is None or _uuid(
        version_artifact_id,
        field_name="model_versions.checkpoint_artifact_id",
    ) != checkpoint_artifact_id:
        raise CheckpointArtifactOwnershipError(
            f"Checkpoint artifact {checkpoint_artifact_id} does not belong "
            f"to model version {model_version_id}"
        )

    artifact = connection.execute(
        _GET_CHECKPOINT_ARTIFACT,
        {"checkpoint_artifact_id": checkpoint_artifact_id},
    ).mappings().one_or_none()
    if artifact is None:
        raise CheckpointArtifactOwnershipError(
            f"Checkpoint artifact not found: {checkpoint_artifact_id}"
        )
    if _uuid(
        artifact["training_run_id"], field_name="artifacts.run_id"
    ) != training_run_id:
        raise CheckpointArtifactOwnershipError(
            f"Checkpoint artifact {checkpoint_artifact_id} does not belong "
            f"to TRAIN {training_run_id}"
        )


def _result(row, *, created: bool) -> EvaluationTrainingLineageResult:
    relationship_type = row.get("relationship_type")
    if relationship_type != EVALUATION_RELATIONSHIP_TYPE:
        raise EvaluationTrainingLineageDataIntegrityError(
            f"Unexpected lineage relationship_type: {relationship_type!r}"
        )
    return EvaluationTrainingLineageResult(
        lineage_id=_uuid(row["lineage_id"], field_name="lineage_id"),
        training_run_id=_uuid(
            row["training_run_id"], field_name="training_run_id"
        ),
        evaluation_run_id=_uuid(
            row["evaluation_run_id"], field_name="evaluation_run_id"
        ),
        model_version_id=_uuid(
            row["model_version_id"], field_name="model_version_id"
        ),
        checkpoint_artifact_id=_uuid(
            row["checkpoint_artifact_id"],
            field_name="checkpoint_artifact_id",
        ),
        relationship_type=relationship_type,
        created=created,
    )


def _identity_mismatches(
    row,
    *,
    training_run_id: UUID,
    evaluation_run_id: UUID,
    model_version_id: UUID,
    checkpoint_artifact_id: UUID,
) -> tuple[str, ...]:
    expected = {
        "training_run_id": training_run_id,
        "evaluation_run_id": evaluation_run_id,
        "model_version_id": model_version_id,
        "checkpoint_artifact_id": checkpoint_artifact_id,
    }
    mismatches = []
    for field_name, expected_value in expected.items():
        persisted = row.get(field_name)
        if persisted is None or _uuid(
            persisted, field_name=f"run_lineage.{field_name}"
        ) != expected_value:
            mismatches.append(field_name)
    if row.get("relationship_type") != EVALUATION_RELATIONSHIP_TYPE:
        mismatches.append("relationship_type")
    return tuple(mismatches)


def create_or_confirm_evaluation_training_lineage(
    *,
    training_run_id: UUID | str,
    evaluation_run_id: UUID | str,
    model_version_id: UUID | str,
    checkpoint_artifact_id: UUID | str,
    checkpoint_path: str | None = None,
    confidence: str | None = None,
    metadata: Mapping[str, object] | None = None,
    connection: Connection | None = None,
) -> EvaluationTrainingLineageResult:
    """Create or confirm the exact scientific identity without any UPDATE."""

    training_id = _uuid(training_run_id, field_name="training_run_id")
    evaluation_id = _uuid(evaluation_run_id, field_name="evaluation_run_id")
    version_id = _uuid(model_version_id, field_name="model_version_id")
    artifact_id = _uuid(
        checkpoint_artifact_id, field_name="checkpoint_artifact_id"
    )
    if training_id == evaluation_id:
        raise EvaluationTrainingLineageDataIntegrityError(
            "TRAIN and EVALUATE ids must be different"
        )
    normalized_confidence = confidence or "unknown"
    if normalized_confidence not in LINEAGE_CONFIDENCES:
        raise EvaluationTrainingLineageDataIntegrityError(
            f"Unknown lineage confidence: {normalized_confidence!r}"
        )
    serialized_metadata = _metadata(metadata)

    with _service_connection(connection) as active:
        _lock_evaluation(active, evaluation_id)
        _lock_training(active, training_id)
        _validate_ownership(
            active,
            training_run_id=training_id,
            model_version_id=version_id,
            checkpoint_artifact_id=artifact_id,
        )
        existing = active.execute(
            _GET_DIRECT_LINEAGES,
            {"evaluation_run_id": evaluation_id},
        ).mappings().all()
        if len(existing) > 1:
            raise EvaluationTrainingLineageCardinalityError(
                evaluation_id, len(existing)
            )
        if existing:
            row = existing[0]
            mismatches = _identity_mismatches(
                row,
                training_run_id=training_id,
                evaluation_run_id=evaluation_id,
                model_version_id=version_id,
                checkpoint_artifact_id=artifact_id,
            )
            if mismatches:
                raise EvaluationTrainingLineageConflictError(
                    evaluation_id,
                    mismatched_fields=mismatches,
                )
            return _result(row, created=False)

        inserted = active.execute(
            _INSERT_LINEAGE,
            {
                "training_run_id": training_id,
                "evaluation_run_id": evaluation_id,
                "model_version_id": version_id,
                "checkpoint_artifact_id": artifact_id,
                "checkpoint_path": (
                    str(checkpoint_path) if checkpoint_path is not None else None
                ),
                "confidence": normalized_confidence,
                "metadata": serialized_metadata,
            },
        ).mappings().one_or_none()
        if inserted is None:
            raise EvaluationTrainingLineageDataIntegrityError(
                f"Could not insert lineage for EVALUATE {evaluation_id}"
            )
        return _result(inserted, created=True)


__all__ = [
    "CheckpointArtifactOwnershipError",
    "EVALUATION_RELATIONSHIP_TYPE",
    "EvaluationTrainingLineageCardinalityError",
    "EvaluationTrainingLineageConflictError",
    "EvaluationTrainingLineageDataIntegrityError",
    "EvaluationTrainingLineageError",
    "EvaluationTrainingLineageResult",
    "ModelVersionOwnershipError",
    "NotTrainingRunError",
    "TrainingRunNotFoundError",
    "create_or_confirm_evaluation_training_lineage",
]
