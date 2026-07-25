"""Strict transactional persistence for governed model lineage."""

from __future__ import annotations

import json
from collections.abc import Mapping
from contextlib import contextmanager
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.db import get_connection

from .entities import (
    CLINICAL_CLASS_MAPPING,
    POSITIVE_LABEL,
    CellPrediction,
    ConfidenceLevel,
    DeployedModelVersion,
    DeploymentAlias,
    DeploymentStatus,
    ImageAnalysisJob,
    ImageJobStatus,
    InferenceRun,
    LineageRecord,
    LineageStatus,
    ModelVersion,
    ModelVersionStatus,
    QualityStatus,
    ReviewStatus,
    RunStatus,
)
from .errors import (
    GovernanceConflictError,
    GovernanceNotFoundError,
    GovernanceOwnershipError,
    GovernancePersistenceError,
    GovernanceStateError,
    GovernanceValidationError,
)


@contextmanager
def _connection(connection_or_session=None):
    """Reuse an external transaction or open one owned transaction."""

    if connection_or_session is not None:
        yield connection_or_session
        return
    with get_connection() as connection:
        yield connection


def _json(value: Mapping[str, Any] | None, field_name: str) -> str:
    try:
        return json.dumps(dict(value or {}), ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise GovernanceValidationError(
            f"{field_name} debe contener valores serializables como JSON."
        ) from exc


def _uuid_string(value: UUID | str, field_name: str) -> str:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise GovernanceValidationError(
            f"{field_name} debe ser un UUID válido."
        ) from exc


def _optional_uuid_string(value: UUID | str | None, field_name: str) -> str | None:
    if value in (None, ""):
        return None
    return _uuid_string(value, field_name)


def _execute_one(connection, statement, params, operation: str) -> dict[str, Any]:
    try:
        row = connection.execute(text(statement), params).mappings().one_or_none()
    except IntegrityError as exc:
        constraint = getattr(getattr(exc, "orig", None), "diag", None)
        constraint_name = getattr(constraint, "constraint_name", None)
        detail = f" Constraint: {constraint_name}." if constraint_name else ""
        raise GovernanceConflictError(
            f"Conflicto de integridad al {operation}.{detail}"
        ) from exc
    except SQLAlchemyError as exc:
        raise GovernancePersistenceError(f"No se pudo {operation}: {exc}") from exc
    if row is None:
        raise GovernancePersistenceError(
            f"La base no devolvió la fila esperada al {operation}."
        )
    return dict(row)


def _fetch_optional(connection, statement, params, operation: str) -> dict[str, Any] | None:
    try:
        row = connection.execute(text(statement), params).mappings().one_or_none()
    except SQLAlchemyError as exc:
        raise GovernancePersistenceError(f"No se pudo {operation}: {exc}") from exc
    return dict(row) if row is not None else None


def _execute_optional(connection, statement, params, operation: str) -> dict[str, Any] | None:
    try:
        row = connection.execute(text(statement), params).mappings().one_or_none()
    except IntegrityError as exc:
        constraint = getattr(getattr(exc, "orig", None), "diag", None)
        constraint_name = getattr(constraint, "constraint_name", None)
        detail = f" Constraint: {constraint_name}." if constraint_name else ""
        raise GovernanceConflictError(
            f"Conflicto de integridad al {operation}.{detail}"
        ) from exc
    except SQLAlchemyError as exc:
        raise GovernancePersistenceError(f"No se pudo {operation}: {exc}") from exc
    return dict(row) if row is not None else None


def _fetch_all(connection, statement, params, operation: str) -> list[dict[str, Any]]:
    try:
        rows = connection.execute(text(statement), params).mappings().all()
    except SQLAlchemyError as exc:
        raise GovernancePersistenceError(f"No se pudo {operation}: {exc}") from exc
    return [dict(row) for row in rows]


def _model_version_from_row(row: Mapping[str, Any]) -> ModelVersion:
    return ModelVersion(
        id=row["id"],
        training_run_id=row["training_run_id"],
        model_name=row["model_name"],
        version_number=row["version_number"],
        checkpoint_artifact_id=row["checkpoint_artifact_id"],
        artifact_path=row["checkpoint_path"],
        artifact_uri=row.get("artifact_uri"),
        artifact_sha256=row["artifact_sha256"],
        artifact_size_bytes=row["artifact_size_bytes"],
        framework=row["framework"],
        framework_version=row.get("framework_version"),
        preprocessing_profile_snapshot=row.get("preprocessing_profile_snapshot") or {},
        class_mapping=row.get("class_mapping") or CLINICAL_CLASS_MAPPING,
        input_signature=row.get("input_signature") or {},
        output_signature=row.get("output_signature") or {},
        status=row["status"],
        lineage_status=row["lineage_status"],
        artifact_hash_reuse_justification=row.get(
            "artifact_hash_reuse_justification"
        ),
        metadata=row.get("metadata") or {},
        created_at=row.get("created_at"),
        validated_at=row.get("validated_at"),
        approved_at=row.get("approved_at"),
        retired_at=row.get("retired_at"),
    )


def _deployment_from_row(row: Mapping[str, Any]) -> DeployedModelVersion:
    return DeployedModelVersion(
        id=row["id"],
        model_version_id=row["model_version_id"],
        checkpoint_artifact_id=row["checkpoint_artifact_id"],
        threshold_calibration_id=row.get("threshold_calibration_id"),
        deployment_name=row["deployment_name"],
        environment=row["environment"],
        alias=row["alias"],
        artifact_sha256=row["artifact_sha256"],
        artifact_size_bytes=row.get("artifact_size_bytes"),
        threshold_value=row["threshold_value"],
        threshold_profile_snapshot=row.get("threshold_profile_snapshot") or {},
        preprocessing_profile_snapshot=row.get("preprocessing_profile_snapshot") or {},
        image_quality_policy_snapshot=row.get("image_quality_policy_snapshot") or {},
        label_mapping_snapshot=row.get("label_mapping_snapshot") or {},
        positive_label=row.get("positive_label") or POSITIVE_LABEL,
        score_name=row.get("score_name") or "probability_parasitized",
        status=row["status"],
        supersedes_deployment_id=row.get("supersedes_deployment_id"),
        rollback_of_deployment_id=row.get("rollback_of_deployment_id"),
        deployed_at=row.get("deployed_at"),
        retired_at=row.get("retired_at"),
        deployed_by=row.get("deployed_by"),
        retired_by=row.get("retired_by"),
        deployment_reason=row.get("deployment_reason"),
        retirement_reason=row.get("retirement_reason"),
        created_at=row.get("created_at"),
        metadata=row.get("metadata") or {},
    )


def _training_and_artifact(connection, training_run_id: str, artifact_id: str):
    row = _fetch_optional(
        connection,
        """
        SELECT
            training.id AS training_run_id,
            training.run_type,
            training.model_id,
            artifact.id AS checkpoint_artifact_id,
            artifact.run_id AS artifact_run_id,
            artifact.path AS artifact_path,
            artifact.artifact_uri,
            artifact.checksum AS artifact_sha256,
            artifact.file_size_bytes AS artifact_size_bytes
        FROM runs AS training
        LEFT JOIN artifacts AS artifact
          ON artifact.id = :checkpoint_artifact_id
        WHERE training.id = :training_run_id
        FOR SHARE OF training
        """,
        {
            "training_run_id": training_run_id,
            "checkpoint_artifact_id": artifact_id,
        },
        "resolver el training run y su artifact",
    )
    if row is None:
        raise GovernanceNotFoundError(
            f"No existe el training run {training_run_id}."
        )
    if row["run_type"] != "training":
        raise GovernanceOwnershipError(
            f"El run {training_run_id} no es de tipo training."
        )
    if row["checkpoint_artifact_id"] is None:
        raise GovernanceNotFoundError(f"No existe el artifact {artifact_id}.")
    if str(row["artifact_run_id"]) != training_run_id:
        raise GovernanceOwnershipError(
            "El checkpoint artifact no pertenece al training_run_id indicado."
        )
    return row


def create_model_version(
    *,
    training_run_id: UUID | str,
    model_name: str,
    version_number: int,
    checkpoint_artifact_id: UUID | str,
    artifact_path: str,
    artifact_sha256: str,
    artifact_size_bytes: int,
    framework: str,
    framework_version: str | None = None,
    artifact_uri: str | None = None,
    preprocessing_profile_snapshot: Mapping[str, Any] | None = None,
    class_mapping: Mapping[str, Any] | None = None,
    input_signature: Mapping[str, Any] | None = None,
    output_signature: Mapping[str, Any] | None = None,
    status: ModelVersionStatus | str = ModelVersionStatus.DISCOVERED,
    lineage_status: LineageStatus | str = LineageStatus.RESOLVED,
    artifact_hash_reuse_justification: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    validated_at: datetime | None = None,
    approved_at: datetime | None = None,
    retired_at: datetime | None = None,
    connection_or_session=None,
) -> ModelVersion:
    """Create one immutable model version after verifying run/artifact ownership."""

    entity = ModelVersion(
        training_run_id=training_run_id,
        model_name=model_name,
        version_number=version_number,
        checkpoint_artifact_id=checkpoint_artifact_id,
        artifact_path=artifact_path,
        artifact_uri=artifact_uri,
        artifact_sha256=artifact_sha256,
        artifact_size_bytes=artifact_size_bytes,
        framework=framework,
        framework_version=framework_version,
        preprocessing_profile_snapshot=preprocessing_profile_snapshot or {},
        class_mapping=class_mapping or CLINICAL_CLASS_MAPPING,
        input_signature=input_signature or {},
        output_signature=output_signature or {},
        status=status,
        lineage_status=lineage_status,
        artifact_hash_reuse_justification=artifact_hash_reuse_justification,
        metadata=metadata or {},
        validated_at=validated_at,
        approved_at=approved_at,
        retired_at=retired_at,
    )

    with _connection(connection_or_session) as connection:
        ownership = _training_and_artifact(
            connection,
            entity.training_run_id,
            entity.checkpoint_artifact_id,
        )
        registered_path = str(ownership["artifact_path"])
        if registered_path != entity.artifact_path:
            raise GovernanceOwnershipError(
                "artifact_path no coincide con el path registrado para el artifact."
            )
        registered_sha256 = ownership.get("artifact_sha256")
        if registered_sha256 is None or str(registered_sha256).lower() != entity.artifact_sha256:
            raise GovernanceOwnershipError(
                "artifact_sha256 no coincide con el checksum registrado para el artifact."
            )
        registered_size = ownership.get("artifact_size_bytes")
        if registered_size is None or int(registered_size) != entity.artifact_size_bytes:
            raise GovernanceOwnershipError(
                "artifact_size_bytes no coincide con el tamaño registrado para el artifact."
            )

        duplicate_hash = _fetch_optional(
            connection,
            """
            SELECT id, model_name, version_number
            FROM model_versions
            WHERE artifact_sha256 = :artifact_sha256
            LIMIT 1
            FOR SHARE
            """,
            {"artifact_sha256": entity.artifact_sha256},
            "comprobar la reutilización del hash",
        )
        if duplicate_hash is not None and not entity.artifact_hash_reuse_justification:
            raise GovernanceConflictError(
                "Ya existe una model version con el mismo artifact_sha256; "
                "artifact_hash_reuse_justification es obligatorio para otra versión."
            )

        row = _execute_one(
            connection,
            """
            INSERT INTO model_versions (
                model_id,
                version_name,
                checkpoint_path,
                training_run_id,
                model_name,
                version_number,
                checkpoint_artifact_id,
                artifact_uri,
                artifact_sha256,
                artifact_size_bytes,
                artifact_hash_reuse_justification,
                framework,
                framework_version,
                preprocessing_profile_snapshot,
                class_mapping,
                input_signature,
                output_signature,
                status,
                lineage_status,
                validated_at,
                approved_at,
                retired_at,
                metadata
            )
            VALUES (
                :model_id,
                :version_name,
                :checkpoint_path,
                :training_run_id,
                :model_name,
                :version_number,
                :checkpoint_artifact_id,
                :artifact_uri,
                :artifact_sha256,
                :artifact_size_bytes,
                :artifact_hash_reuse_justification,
                :framework,
                :framework_version,
                CAST(:preprocessing_profile_snapshot AS jsonb),
                CAST(:class_mapping AS jsonb),
                CAST(:input_signature AS jsonb),
                CAST(:output_signature AS jsonb),
                :status,
                :lineage_status,
                :validated_at,
                :approved_at,
                :retired_at,
                CAST(:metadata AS jsonb)
            )
            RETURNING
                id, training_run_id, model_name, version_number,
                checkpoint_artifact_id, checkpoint_path, artifact_uri,
                artifact_sha256, artifact_size_bytes,
                artifact_hash_reuse_justification, framework, framework_version,
                preprocessing_profile_snapshot, class_mapping, input_signature,
                output_signature, status, lineage_status, created_at,
                validated_at, approved_at, retired_at, metadata
            """,
            {
                "model_id": ownership.get("model_id"),
                "version_name": str(entity.version_number),
                "checkpoint_path": entity.artifact_path,
                "training_run_id": entity.training_run_id,
                "model_name": entity.model_name,
                "version_number": entity.version_number,
                "checkpoint_artifact_id": entity.checkpoint_artifact_id,
                "artifact_uri": entity.artifact_uri or ownership.get("artifact_uri"),
                "artifact_sha256": entity.artifact_sha256,
                "artifact_size_bytes": entity.artifact_size_bytes,
                "artifact_hash_reuse_justification": (
                    entity.artifact_hash_reuse_justification
                ),
                "framework": entity.framework,
                "framework_version": entity.framework_version,
                "preprocessing_profile_snapshot": _json(
                    entity.preprocessing_profile_snapshot,
                    "preprocessing_profile_snapshot",
                ),
                "class_mapping": _json(entity.class_mapping, "class_mapping"),
                "input_signature": _json(entity.input_signature, "input_signature"),
                "output_signature": _json(entity.output_signature, "output_signature"),
                "status": entity.status,
                "lineage_status": entity.lineage_status,
                "validated_at": entity.validated_at,
                "approved_at": entity.approved_at,
                "retired_at": entity.retired_at,
                "metadata": _json(entity.metadata, "metadata"),
            },
            "crear la model version",
        )
    return _model_version_from_row(row)


def _governed_model_version(connection, model_version_id: str) -> dict[str, Any]:
    row = _fetch_optional(
        connection,
        """
        SELECT
            id,
            training_run_id,
            checkpoint_artifact_id,
            artifact_sha256,
            artifact_size_bytes,
            preprocessing_profile_snapshot,
            class_mapping,
            status,
            lineage_status
        FROM model_versions
        WHERE id = :model_version_id
        FOR SHARE
        """,
        {"model_version_id": model_version_id},
        "resolver la model version",
    )
    if row is None:
        raise GovernanceNotFoundError(
            f"No existe la model version {model_version_id}."
        )
    required = ("checkpoint_artifact_id", "artifact_sha256", "training_run_id")
    if any(row.get(field_name) is None for field_name in required):
        raise GovernanceStateError(
            "La model version no tiene artifact y linaje gobernados completos."
        )
    if row["lineage_status"] != LineageStatus.RESOLVED.value:
        raise GovernanceStateError(
            "La model version debe tener lineage_status=resolved para un deployment."
        )
    return row


def create_deployed_model_version(
    *,
    model_version_id: UUID | str,
    deployment_name: str,
    environment: str,
    alias: DeploymentAlias | str,
    threshold_value: float,
    threshold_profile_snapshot: Mapping[str, Any] | None = None,
    preprocessing_profile_snapshot: Mapping[str, Any] | None = None,
    image_quality_policy_snapshot: Mapping[str, Any] | None = None,
    label_mapping_snapshot: Mapping[str, Any] | None = None,
    threshold_calibration_id: UUID | str | None = None,
    status: DeploymentStatus | str = DeploymentStatus.PENDING,
    supersedes_deployment_id: UUID | str | None = None,
    rollback_of_deployment_id: UUID | str | None = None,
    deployed_at: datetime | None = None,
    retired_at: datetime | None = None,
    deployed_by: str | None = None,
    retired_by: str | None = None,
    deployment_reason: str | None = None,
    retirement_reason: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    connection_or_session=None,
) -> DeployedModelVersion:
    """Create a deployment revision; the default status is always pending."""

    normalized_id = _uuid_string(model_version_id, "model_version_id")
    with _connection(connection_or_session) as connection:
        version = _governed_model_version(connection, normalized_id)
        effective_preprocessing = (
            preprocessing_profile_snapshot
            if preprocessing_profile_snapshot is not None
            else version.get("preprocessing_profile_snapshot") or {}
        )
        effective_mapping = (
            label_mapping_snapshot
            if label_mapping_snapshot is not None
            else version.get("class_mapping") or CLINICAL_CLASS_MAPPING
        )
        entity = DeployedModelVersion(
            model_version_id=normalized_id,
            checkpoint_artifact_id=version["checkpoint_artifact_id"],
            threshold_calibration_id=threshold_calibration_id,
            deployment_name=deployment_name,
            environment=environment,
            alias=alias,
            artifact_sha256=version["artifact_sha256"],
            artifact_size_bytes=version.get("artifact_size_bytes"),
            threshold_value=threshold_value,
            threshold_profile_snapshot=threshold_profile_snapshot or {},
            preprocessing_profile_snapshot=effective_preprocessing,
            image_quality_policy_snapshot=image_quality_policy_snapshot or {},
            label_mapping_snapshot=effective_mapping,
            status=status,
            supersedes_deployment_id=supersedes_deployment_id,
            rollback_of_deployment_id=rollback_of_deployment_id,
            deployed_at=deployed_at,
            retired_at=retired_at,
            deployed_by=deployed_by,
            retired_by=retired_by,
            deployment_reason=deployment_reason,
            retirement_reason=retirement_reason,
            metadata=metadata or {},
        )
        if (
            entity.status == DeploymentStatus.ACTIVE.value
            and version["status"]
            not in (ModelVersionStatus.APPROVED.value, ModelVersionStatus.DEPLOYED.value)
        ):
            raise GovernanceStateError(
                "Un deployment active exige una model version approved o deployed."
            )
        row = _execute_one(
            connection,
            """
            INSERT INTO deployed_model_versions (
                model_version_id, checkpoint_artifact_id,
                threshold_calibration_id, deployment_name, environment, alias,
                artifact_sha256, artifact_size_bytes, threshold_value,
                threshold_profile_snapshot, preprocessing_profile_snapshot,
                image_quality_policy_snapshot, label_mapping_snapshot,
                positive_label, score_name, status, supersedes_deployment_id,
                rollback_of_deployment_id, deployed_at, retired_at, deployed_by,
                retired_by, deployment_reason, retirement_reason, metadata
            )
            VALUES (
                :model_version_id, :checkpoint_artifact_id,
                :threshold_calibration_id, :deployment_name, :environment, :alias,
                :artifact_sha256, :artifact_size_bytes, :threshold_value,
                CAST(:threshold_profile_snapshot AS jsonb),
                CAST(:preprocessing_profile_snapshot AS jsonb),
                CAST(:image_quality_policy_snapshot AS jsonb),
                CAST(:label_mapping_snapshot AS jsonb),
                :positive_label, :score_name, :status, :supersedes_deployment_id,
                :rollback_of_deployment_id, :deployed_at, :retired_at, :deployed_by,
                :retired_by, :deployment_reason, :retirement_reason,
                CAST(:metadata AS jsonb)
            )
            RETURNING *
            """,
            {
                "model_version_id": entity.model_version_id,
                "checkpoint_artifact_id": entity.checkpoint_artifact_id,
                "threshold_calibration_id": entity.threshold_calibration_id,
                "deployment_name": entity.deployment_name,
                "environment": entity.environment,
                "alias": entity.alias,
                "artifact_sha256": entity.artifact_sha256,
                "artifact_size_bytes": entity.artifact_size_bytes,
                "threshold_value": entity.threshold_value,
                "threshold_profile_snapshot": _json(
                    entity.threshold_profile_snapshot,
                    "threshold_profile_snapshot",
                ),
                "preprocessing_profile_snapshot": _json(
                    entity.preprocessing_profile_snapshot,
                    "preprocessing_profile_snapshot",
                ),
                "image_quality_policy_snapshot": _json(
                    entity.image_quality_policy_snapshot,
                    "image_quality_policy_snapshot",
                ),
                "label_mapping_snapshot": _json(
                    entity.label_mapping_snapshot,
                    "label_mapping_snapshot",
                ),
                "positive_label": entity.positive_label,
                "score_name": entity.score_name,
                "status": entity.status,
                "supersedes_deployment_id": entity.supersedes_deployment_id,
                "rollback_of_deployment_id": entity.rollback_of_deployment_id,
                "deployed_at": entity.deployed_at,
                "retired_at": entity.retired_at,
                "deployed_by": entity.deployed_by,
                "retired_by": entity.retired_by,
                "deployment_reason": entity.deployment_reason,
                "retirement_reason": entity.retirement_reason,
                "metadata": _json(entity.metadata, "metadata"),
            },
            "crear el deployed model version",
        )
    return _deployment_from_row(row)


def _inference_run_from_row(
    row: Mapping[str, Any],
    deployed_model_version_id: UUID | str,
    model_version_id: UUID | str,
) -> InferenceRun:
    return InferenceRun(
        id=row.get("id") or row.get("run_id"),
        deployed_model_version_id=deployed_model_version_id,
        model_version_id=model_version_id,
        backend_version=row["backend_version"],
        pipeline_version=row["pipeline_version"],
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at") or row.get("finished_at"),
        status=row["status"],
        configuration=row.get("configuration") or {},
        metadata=row.get("metadata") or {},
        error_message=row.get("error_message"),
    )


def _active_deployment(connection, deployment_id: str) -> dict[str, Any]:
    row = _fetch_optional(
        connection,
        """
        SELECT
            deployment.id AS deployed_model_version_id,
            deployment.model_version_id,
            deployment.status AS deployment_status,
            deployment.threshold_value,
            version.model_id
        FROM deployed_model_versions AS deployment
        JOIN model_versions AS version
          ON version.id = deployment.model_version_id
        WHERE deployment.id = :deployed_model_version_id
        FOR SHARE OF deployment, version
        """,
        {"deployed_model_version_id": deployment_id},
        "resolver el deployed model version",
    )
    if row is None:
        raise GovernanceNotFoundError(
            f"No existe el deployed model version {deployment_id}."
        )
    if row["deployment_status"] != DeploymentStatus.ACTIVE.value:
        raise GovernanceStateError(
            "El deployed model version debe estar active para iniciar inferencia."
        )
    return row


def create_inference_run(
    *,
    deployed_model_version_id: UUID | str,
    backend_version: str,
    pipeline_version: str,
    configuration: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    status: RunStatus | str = RunStatus.STARTED,
    run_name: str | None = None,
    experiment_id: UUID | str | None = None,
    dataset_id: UUID | str | None = None,
    command: str | None = None,
    script_name: str | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    error_message: str | None = None,
    binding_metadata: Mapping[str, Any] | None = None,
    connection_or_session=None,
) -> InferenceRun:
    """Insert an inference run and its primary deployment binding atomically."""

    deployment_id = _uuid_string(
        deployed_model_version_id, "deployed_model_version_id"
    )
    normalized_experiment_id = _optional_uuid_string(experiment_id, "experiment_id")
    normalized_dataset_id = _optional_uuid_string(dataset_id, "dataset_id")
    with _connection(connection_or_session) as connection:
        deployment = _active_deployment(connection, deployment_id)
        entity = InferenceRun(
            deployed_model_version_id=deployment_id,
            model_version_id=deployment["model_version_id"],
            backend_version=backend_version,
            pipeline_version=pipeline_version,
            status=status,
            configuration=configuration or {},
            metadata=metadata or {},
            error_message=error_message,
            started_at=started_at,
            completed_at=completed_at,
        )
        if (
            entity.status
            in (RunStatus.COMPLETED.value, RunStatus.FAILED.value, RunStatus.CANCELLED.value)
            and entity.completed_at is None
        ):
            raise GovernanceValidationError(
                "completed_at es obligatorio para un inference run terminal."
            )

        row = _execute_one(
            connection,
            """
            INSERT INTO runs (
                experiment_id, model_id, dataset_id, run_name, run_type, status,
                command, script_name, started_at, finished_at, backend_version,
                pipeline_version, configuration, error_message, parameters, metadata
            )
            VALUES (
                :experiment_id, :model_id, :dataset_id, :run_name, 'inference',
                :status, :command, :script_name, COALESCE(:started_at, NOW()),
                :completed_at, :backend_version, :pipeline_version,
                CAST(:configuration AS jsonb), :error_message,
                CAST(:configuration AS jsonb), CAST(:metadata AS jsonb)
            )
            RETURNING
                id, backend_version, pipeline_version, started_at, finished_at,
                status, configuration, metadata, error_message
            """,
            {
                "experiment_id": normalized_experiment_id,
                "model_id": deployment.get("model_id"),
                "dataset_id": normalized_dataset_id,
                "run_name": run_name,
                "status": entity.status,
                "command": command,
                "script_name": script_name,
                "started_at": entity.started_at,
                "completed_at": entity.completed_at,
                "backend_version": entity.backend_version,
                "pipeline_version": entity.pipeline_version,
                "configuration": _json(entity.configuration, "configuration"),
                "error_message": entity.error_message,
                "metadata": _json(entity.metadata, "metadata"),
            },
            "crear el inference run",
        )
        _execute_one(
            connection,
            """
            INSERT INTO run_model_deployments (
                run_id, deployed_model_version_id, model_version_id,
                role, ordinal, metadata
            )
            VALUES (
                :run_id, :deployed_model_version_id, :model_version_id,
                'primary', 0, CAST(:metadata AS jsonb)
            )
            RETURNING id
            """,
            {
                "run_id": str(row["id"]),
                "deployed_model_version_id": deployment_id,
                "model_version_id": str(deployment["model_version_id"]),
                "metadata": _json(binding_metadata, "binding_metadata"),
            },
            "vincular el inference run con su deployment",
        )
    return _inference_run_from_row(
        row,
        deployed_model_version_id=deployment_id,
        model_version_id=deployment["model_version_id"],
    )


def _image_job_from_row(row: Mapping[str, Any]) -> ImageAnalysisJob:
    return ImageAnalysisJob(
        id=row["id"],
        inference_run_id=row["inference_run_id"],
        deployed_model_version_id=row["deployed_model_version_id"],
        model_version_id=row["model_version_id"],
        input_artifact_id=row.get("input_artifact_id"),
        source_image_id=row.get("source_image_id"),
        idempotency_key=row.get("idempotency_key"),
        sample_id=row.get("sample_id"),
        patient_id=row.get("patient_id"),
        slide_id=row.get("slide_id"),
        status=row["status"],
        quality_status=row["quality_status"],
        quality_metrics=row.get("quality_metrics") or {},
        threshold_used=row.get("threshold_used"),
        threshold_source=row.get("threshold_source"),
        summary=row.get("summary") or {},
        total_cells=row.get("total_cells"),
        positive_cells=row.get("positive_cells"),
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
        error_message=row.get("error_message"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        metadata=row.get("metadata") or {},
    )


def _inference_binding(
    connection,
    inference_run_id: str,
    deployed_model_version_id: str,
) -> dict[str, Any]:
    row = _fetch_optional(
        connection,
        """
        SELECT
            run.id AS inference_run_id,
            run.run_type,
            run.status AS inference_status,
            binding.deployed_model_version_id,
            binding.model_version_id,
            deployment.status AS deployment_status,
            deployment.threshold_value
        FROM runs AS run
        JOIN run_model_deployments AS binding
          ON binding.run_id = run.id
         AND binding.deployed_model_version_id = :deployed_model_version_id
        JOIN deployed_model_versions AS deployment
          ON deployment.id = binding.deployed_model_version_id
         AND deployment.model_version_id = binding.model_version_id
        WHERE run.id = :inference_run_id
        FOR SHARE OF run, binding, deployment
        """,
        {
            "inference_run_id": inference_run_id,
            "deployed_model_version_id": deployed_model_version_id,
        },
        "resolver el vínculo entre inference run y deployment",
    )
    if row is None:
        raise GovernanceNotFoundError(
            "No existe el vínculo solicitado entre inference run y deployment."
        )
    if row["run_type"] != "inference":
        raise GovernanceOwnershipError(
            f"El run {inference_run_id} no es de tipo inference."
        )
    if row["deployment_status"] != DeploymentStatus.ACTIVE.value:
        raise GovernanceStateError(
            "El deployed model version debe estar active para crear un image job."
        )
    if row["inference_status"] != RunStatus.STARTED.value:
        raise GovernanceStateError(
            "El inference run debe estar started para crear un image analysis job."
        )
    return row


def create_image_analysis_job(
    *,
    inference_run_id: UUID | str,
    deployed_model_version_id: UUID | str,
    input_artifact_id: UUID | str | None = None,
    source_image_id: UUID | str | None = None,
    idempotency_key: str | None = None,
    sample_id: str | None = None,
    patient_id: str | None = None,
    slide_id: str | None = None,
    status: ImageJobStatus | str = ImageJobStatus.PENDING,
    quality_status: QualityStatus | str = QualityStatus.NOT_ASSESSED,
    quality_metrics: Mapping[str, Any] | None = None,
    threshold_used: float | None = None,
    threshold_source: str | None = None,
    summary: Mapping[str, Any] | None = None,
    total_cells: int | None = None,
    positive_cells: int | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    error_message: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    connection_or_session=None,
) -> ImageAnalysisJob:
    """Create one image job bound to an existing inference/deployment pair."""

    run_id = _uuid_string(inference_run_id, "inference_run_id")
    deployment_id = _uuid_string(
        deployed_model_version_id, "deployed_model_version_id"
    )
    with _connection(connection_or_session) as connection:
        binding = _inference_binding(connection, run_id, deployment_id)
        effective_threshold = (
            threshold_used
            if threshold_used is not None
            else float(binding["threshold_value"])
        )
        entity = ImageAnalysisJob(
            inference_run_id=run_id,
            deployed_model_version_id=deployment_id,
            model_version_id=binding["model_version_id"],
            input_artifact_id=input_artifact_id,
            source_image_id=source_image_id,
            idempotency_key=idempotency_key,
            sample_id=sample_id,
            patient_id=patient_id,
            slide_id=slide_id,
            status=status,
            quality_status=quality_status,
            quality_metrics=quality_metrics or {},
            threshold_used=effective_threshold,
            threshold_source=threshold_source or "deployment_snapshot",
            summary=summary or {},
            total_cells=total_cells,
            positive_cells=positive_cells,
            started_at=started_at,
            completed_at=completed_at,
            error_message=error_message,
            metadata=metadata or {},
        )
        row = _execute_optional(
            connection,
            """
            INSERT INTO image_analysis_jobs (
                inference_run_id, deployed_model_version_id, model_version_id,
                input_artifact_id, source_image_id, idempotency_key, sample_id,
                patient_id, slide_id, status, quality_status, quality_metrics,
                threshold_used, threshold_source, summary, total_cells,
                positive_cells, started_at, completed_at, error_message, metadata
            )
            VALUES (
                :inference_run_id, :deployed_model_version_id, :model_version_id,
                :input_artifact_id, :source_image_id, :idempotency_key, :sample_id,
                :patient_id, :slide_id, :status, :quality_status,
                CAST(:quality_metrics AS jsonb), :threshold_used, :threshold_source,
                CAST(:summary AS jsonb), :total_cells, :positive_cells, :started_at,
                :completed_at, :error_message, CAST(:metadata AS jsonb)
            )
            ON CONFLICT (inference_run_id, idempotency_key)
                WHERE idempotency_key IS NOT NULL
            DO NOTHING
            RETURNING *
            """,
            {
                "inference_run_id": entity.inference_run_id,
                "deployed_model_version_id": entity.deployed_model_version_id,
                "model_version_id": entity.model_version_id,
                "input_artifact_id": entity.input_artifact_id,
                "source_image_id": entity.source_image_id,
                "idempotency_key": entity.idempotency_key,
                "sample_id": entity.sample_id,
                "patient_id": entity.patient_id,
                "slide_id": entity.slide_id,
                "status": entity.status,
                "quality_status": entity.quality_status,
                "quality_metrics": _json(entity.quality_metrics, "quality_metrics"),
                "threshold_used": entity.threshold_used,
                "threshold_source": entity.threshold_source,
                "summary": _json(entity.summary, "summary"),
                "total_cells": entity.total_cells,
                "positive_cells": entity.positive_cells,
                "started_at": entity.started_at,
                "completed_at": entity.completed_at,
                "error_message": entity.error_message,
                "metadata": _json(entity.metadata, "metadata"),
            },
            "crear el image analysis job",
        )
        if row is None:
            row = _fetch_optional(
                connection,
                """
                SELECT *
                FROM image_analysis_jobs
                WHERE inference_run_id = :inference_run_id
                  AND idempotency_key = :idempotency_key
                FOR SHARE
                """,
                {
                    "inference_run_id": entity.inference_run_id,
                    "idempotency_key": entity.idempotency_key,
                },
                "recuperar el image analysis job idempotente",
            )
            if row is None:
                raise GovernancePersistenceError(
                    "El conflicto idempotente no devolvió el image analysis job existente."
                )
            identity_fields = (
                "deployed_model_version_id",
                "model_version_id",
                "input_artifact_id",
                "source_image_id",
                "sample_id",
                "patient_id",
                "slide_id",
                "threshold_used",
            )
            for field_name in identity_fields:
                existing = row.get(field_name)
                requested = getattr(entity, field_name)
                if existing is not None and field_name.endswith("_id"):
                    existing = str(existing)
                values_match = existing == requested
                if field_name == "threshold_used" and existing is not None:
                    values_match = abs(float(existing) - float(requested)) <= 1e-12
                if not values_match:
                    raise GovernanceConflictError(
                        "idempotency_key ya existe con otro payload de identidad."
                    )
    return _image_job_from_row(row)


def _cell_prediction_from_row(row: Mapping[str, Any]) -> CellPrediction:
    return CellPrediction(
        id=row["id"],
        image_analysis_job_id=row["image_analysis_job_id"],
        inference_run_id=row["inference_run_id"],
        deployed_model_version_id=row["deployed_model_version_id"],
        model_version_id=row["model_version_id"],
        classifier_model_version_id=row["classifier_model_version_id"],
        detector_model_version_id=row.get("detector_model_version_id"),
        cell_index=row["cell_index"],
        source_image_id=row.get("source_image_id"),
        bbox_x=row["bbox_x"],
        bbox_y=row["bbox_y"],
        bbox_width=row["bbox_width"],
        bbox_height=row["bbox_height"],
        crop_artifact_id=row.get("crop_artifact_id"),
        probability_parasitized=row["probability_parasitized"],
        probability_uninfected=row["probability_uninfected"],
        threshold_used=row["threshold_used"],
        predicted_class=row["predicted_class"],
        predicted_label=row["predicted_label"],
        confidence_level=row.get("confidence_level"),
        quality_status=row.get("quality_status"),
        explanation_artifact_id=row.get("explanation_artifact_id"),
        review_status=row.get("review_status") or ReviewStatus.UNREVIEWED,
        reviewed_label=row.get("reviewed_label"),
        reviewed_by=row.get("reviewed_by"),
        reviewed_at=row.get("reviewed_at"),
        created_at=row.get("created_at"),
        metadata=row.get("metadata") or {},
    )


def _image_job_context(connection, image_analysis_job_id: str) -> dict[str, Any]:
    row = _fetch_optional(
        connection,
        """
        SELECT
            job.id AS image_analysis_job_id,
            job.inference_run_id,
            job.deployed_model_version_id,
            job.model_version_id,
            job.source_image_id,
            job.threshold_used,
            job.status AS job_status,
            run.status AS inference_status,
            run.run_type,
            source.dataset_id AS source_dataset_id
        FROM image_analysis_jobs AS job
        JOIN runs AS run
          ON run.id = job.inference_run_id
        LEFT JOIN dataset_split_images AS source
          ON source.image_id = job.source_image_id
        WHERE job.id = :image_analysis_job_id
        FOR SHARE OF job, run
        """,
        {"image_analysis_job_id": image_analysis_job_id},
        "resolver el image analysis job",
    )
    if row is None:
        raise GovernanceNotFoundError(
            f"No existe el image analysis job {image_analysis_job_id}."
        )
    if row["run_type"] != "inference":
        raise GovernanceOwnershipError(
            "El image analysis job no pertenece a un run de tipo inference."
        )
    if row["inference_status"] != RunStatus.STARTED.value:
        raise GovernanceStateError(
            "El inference run debe estar started para registrar predicciones."
        )
    if row["job_status"] not in (
        ImageJobStatus.PENDING.value,
        ImageJobStatus.RUNNING.value,
    ):
        raise GovernanceStateError(
            "El image analysis job debe estar pending o running para registrar predicciones."
        )
    return row


def create_cell_prediction(
    *,
    image_analysis_job_id: UUID | str,
    classifier_model_version_id: UUID | str,
    cell_index: int,
    bbox_x: float,
    bbox_y: float,
    bbox_width: float,
    bbox_height: float,
    probability_parasitized: float,
    probability_uninfected: float,
    threshold_used: float,
    predicted_class: int,
    predicted_label: str,
    detector_model_version_id: UUID | str | None = None,
    source_image_id: UUID | str | None = None,
    crop_artifact_id: UUID | str | None = None,
    confidence_level: ConfidenceLevel | str | None = ConfidenceLevel.NOT_ASSESSED,
    quality_status: QualityStatus | str | None = QualityStatus.NOT_ASSESSED,
    explanation_artifact_id: UUID | str | None = None,
    review_status: ReviewStatus | str = ReviewStatus.UNREVIEWED,
    reviewed_label: str | None = None,
    reviewed_by: str | None = None,
    reviewed_at: datetime | None = None,
    metadata: Mapping[str, Any] | None = None,
    connection_or_session=None,
) -> CellPrediction:
    """Persist one cell-scoped row in the canonical predictions table."""

    job_id = _uuid_string(image_analysis_job_id, "image_analysis_job_id")
    classifier_id = _uuid_string(
        classifier_model_version_id, "classifier_model_version_id"
    )
    with _connection(connection_or_session) as connection:
        job = _image_job_context(connection, job_id)
        if classifier_id != str(job["model_version_id"]):
            raise GovernanceOwnershipError(
                "classifier_model_version_id no coincide con la versión del image job."
            )
        effective_source_image_id = source_image_id or job.get("source_image_id")
        if (
            source_image_id is not None
            and job.get("source_image_id") is not None
            and _uuid_string(source_image_id, "source_image_id")
            != str(job["source_image_id"])
        ):
            raise GovernanceOwnershipError(
                "source_image_id no coincide con la imagen del image job."
            )
        entity = CellPrediction(
            image_analysis_job_id=job_id,
            inference_run_id=job["inference_run_id"],
            deployed_model_version_id=job["deployed_model_version_id"],
            model_version_id=classifier_id,
            classifier_model_version_id=classifier_id,
            detector_model_version_id=detector_model_version_id,
            cell_index=cell_index,
            source_image_id=effective_source_image_id,
            bbox_x=bbox_x,
            bbox_y=bbox_y,
            bbox_width=bbox_width,
            bbox_height=bbox_height,
            crop_artifact_id=crop_artifact_id,
            probability_parasitized=probability_parasitized,
            probability_uninfected=probability_uninfected,
            threshold_used=threshold_used,
            predicted_class=predicted_class,
            predicted_label=predicted_label,
            confidence_level=confidence_level,
            quality_status=quality_status,
            explanation_artifact_id=explanation_artifact_id,
            review_status=review_status,
            reviewed_label=reviewed_label,
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
            metadata=metadata or {},
        )
        if (
            job.get("threshold_used") is not None
            and abs(float(job["threshold_used"]) - entity.threshold_used) > 1e-12
        ):
            raise GovernanceOwnershipError(
                "threshold_used no coincide con el threshold congelado en el image job."
            )
        row = _execute_one(
            connection,
            """
            INSERT INTO predictions (
                run_id, dataset_id, image_id, predicted_label, score,
                score_positive_label, threshold, image_analysis_job_id,
                model_version_id, deployed_model_version_id, inference_run_id,
                classifier_model_version_id, detector_model_version_id,
                prediction_scope, cell_index, source_image_id, bbox_x, bbox_y,
                bbox_width, bbox_height, crop_artifact_id,
                explanation_artifact_id, probability_parasitized,
                probability_uninfected, threshold_used, predicted_class,
                confidence_level, quality_status, review_status, reviewed_label,
                reviewed_by, reviewed_at, metadata
            )
            VALUES (
                :run_id, :dataset_id, :image_id, :predicted_label,
                :probability_parasitized, :probability_parasitized,
                :threshold_used, :image_analysis_job_id, :model_version_id,
                :deployed_model_version_id, :inference_run_id,
                :classifier_model_version_id, :detector_model_version_id,
                'cell', :cell_index, :source_image_id, :bbox_x, :bbox_y,
                :bbox_width, :bbox_height, :crop_artifact_id,
                :explanation_artifact_id, :probability_parasitized,
                :probability_uninfected, :threshold_used, :predicted_class,
                :confidence_level, :quality_status, :review_status,
                :reviewed_label, :reviewed_by, :reviewed_at,
                CAST(:metadata AS jsonb)
            )
            RETURNING *
            """,
            {
                "run_id": entity.inference_run_id,
                "dataset_id": job.get("source_dataset_id"),
                "image_id": entity.source_image_id,
                "predicted_label": entity.predicted_label,
                "image_analysis_job_id": entity.image_analysis_job_id,
                "model_version_id": entity.model_version_id,
                "deployed_model_version_id": entity.deployed_model_version_id,
                "inference_run_id": entity.inference_run_id,
                "classifier_model_version_id": entity.classifier_model_version_id,
                "detector_model_version_id": entity.detector_model_version_id,
                "cell_index": entity.cell_index,
                "source_image_id": entity.source_image_id,
                "bbox_x": entity.bbox_x,
                "bbox_y": entity.bbox_y,
                "bbox_width": entity.bbox_width,
                "bbox_height": entity.bbox_height,
                "crop_artifact_id": entity.crop_artifact_id,
                "explanation_artifact_id": entity.explanation_artifact_id,
                "probability_parasitized": entity.probability_parasitized,
                "probability_uninfected": entity.probability_uninfected,
                "threshold_used": entity.threshold_used,
                "predicted_class": entity.predicted_class,
                "confidence_level": entity.confidence_level,
                "quality_status": entity.quality_status,
                "review_status": entity.review_status,
                "reviewed_label": entity.reviewed_label,
                "reviewed_by": entity.reviewed_by,
                "reviewed_at": entity.reviewed_at,
                "metadata": _json(entity.metadata, "metadata"),
            },
            "crear la cell prediction",
        )
    return _cell_prediction_from_row(row)


def get_lineage(
    *,
    training_run_id: UUID | str | None = None,
    model_version_id: UUID | str | None = None,
    deployed_model_version_id: UUID | str | None = None,
    inference_run_id: UUID | str | None = None,
    image_analysis_job_id: UUID | str | None = None,
    prediction_id: UUID | str | None = None,
    connection_or_session=None,
) -> list[LineageRecord]:
    """Return flattened auditable paths from training through derived/inference data."""

    anchors = {
        "training_run_id": training_run_id,
        "model_version_id": model_version_id,
        "deployed_model_version_id": deployed_model_version_id,
        "inference_run_id": inference_run_id,
        "image_analysis_job_id": image_analysis_job_id,
        "prediction_id": prediction_id,
    }
    selected = [(name, value) for name, value in anchors.items() if value not in (None, "")]
    if len(selected) != 1:
        raise GovernanceValidationError(
            "get_lineage exige exactamente uno de training_run_id, model_version_id, "
            "deployed_model_version_id, inference_run_id, image_analysis_job_id o "
            "prediction_id."
        )
    anchor_name, anchor_value = selected[0]
    normalized_anchor = _uuid_string(anchor_value, anchor_name)
    anchor_columns = {
        "training_run_id": "version.training_run_id",
        "model_version_id": "version.id",
        "deployed_model_version_id": "deployment.id",
        "inference_run_id": "inference.id",
        "image_analysis_job_id": "job.id",
        "prediction_id": "prediction.id",
    }
    where_clause = f"{anchor_columns[anchor_name]} = :anchor_id"

    with _connection(connection_or_session) as connection:
        rows = _fetch_all(
            connection,
            f"""
            SELECT DISTINCT
                version.training_run_id,
                version.id AS model_version_id,
                version.checkpoint_artifact_id,
                version.model_name,
                version.version_number,
                version.checkpoint_path AS artifact_path,
                version.artifact_sha256,
                version.status AS model_version_status,
                deployment.id AS deployed_model_version_id,
                deployment.deployment_name,
                deployment.environment,
                deployment.alias,
                deployment.status AS deployment_status,
                inference.id AS inference_run_id,
                inference.status AS inference_status,
                job.id AS image_analysis_job_id,
                job.status AS image_job_status,
                prediction.id AS prediction_id,
                derived.id AS derived_run_id,
                derived.run_type AS derived_run_type,
                lineage.relationship_type
            FROM model_versions AS version
            LEFT JOIN deployed_model_versions AS deployment
              ON deployment.model_version_id = version.id
            LEFT JOIN run_model_deployments AS binding
              ON binding.deployed_model_version_id = deployment.id
             AND binding.model_version_id = version.id
            LEFT JOIN runs AS inference
              ON inference.id = binding.run_id
             AND inference.run_type = 'inference'
            LEFT JOIN image_analysis_jobs AS job
              ON job.inference_run_id = inference.id
             AND job.deployed_model_version_id = deployment.id
             AND job.model_version_id = version.id
            LEFT JOIN predictions AS prediction
              ON prediction.image_analysis_job_id = job.id
             AND prediction.inference_run_id = inference.id
             AND prediction.deployed_model_version_id = deployment.id
             AND prediction.model_version_id = version.id
             AND prediction.prediction_scope = 'cell'
            LEFT JOIN run_lineage AS lineage
              ON lineage.model_version_id = version.id
            LEFT JOIN runs AS derived
              ON derived.id = lineage.child_run_id
            WHERE {where_clause}
            ORDER BY
                version.version_number NULLS LAST,
                deployment.id NULLS LAST,
                inference.id NULLS LAST,
                job.id NULLS LAST,
                prediction.id NULLS LAST,
                derived.id NULLS LAST
            """,
            {"anchor_id": normalized_anchor},
            "recuperar el linaje gobernado",
        )
    if not rows:
        raise GovernanceNotFoundError(
            f"No existe linaje gobernado para {anchor_name}={normalized_anchor}."
        )
    return [
        LineageRecord(
            training_run_id=row["training_run_id"],
            model_version_id=row["model_version_id"],
            checkpoint_artifact_id=row.get("checkpoint_artifact_id"),
            model_name=row.get("model_name"),
            version_number=row.get("version_number"),
            artifact_path=row.get("artifact_path"),
            artifact_sha256=row.get("artifact_sha256"),
            model_version_status=row.get("model_version_status"),
            deployed_model_version_id=row.get("deployed_model_version_id"),
            deployment_name=row.get("deployment_name"),
            environment=row.get("environment"),
            alias=row.get("alias"),
            deployment_status=row.get("deployment_status"),
            inference_run_id=row.get("inference_run_id"),
            inference_status=row.get("inference_status"),
            image_analysis_job_id=row.get("image_analysis_job_id"),
            image_job_status=row.get("image_job_status"),
            prediction_id=row.get("prediction_id"),
            derived_run_id=row.get("derived_run_id"),
            derived_run_type=row.get("derived_run_type"),
            relationship_type=row.get("relationship_type"),
        )
        for row in rows
    ]
