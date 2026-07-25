"""Immutable domain entities for auditable model lineage."""

from __future__ import annotations

import re
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from .errors import GovernanceValidationError


CLINICAL_CLASS_MAPPING = {"0": "uninfected", "1": "parasitized"}
NEGATIVE_CLASS = 0
NEGATIVE_LABEL = "uninfected"
POSITIVE_CLASS = 1
POSITIVE_LABEL = "parasitized"
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


class ModelVersionStatus(str, Enum):
    """Functional lifecycle of an immutable model version."""

    DISCOVERED = "discovered"
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    APPROVED = "approved"
    DEPLOYED = "deployed"
    REJECTED = "rejected"
    RETIRED = "retired"


class LineageStatus(str, Enum):
    """Resolution state of a model version's training lineage."""

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"
    ARTIFACT_MISSING = "artifact_missing"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    LEGACY_UNRESOLVED = "legacy_unresolved"


class DeploymentStatus(str, Enum):
    """Lifecycle of a deployed-model authorization record."""

    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    RETIRED = "retired"
    FAILED = "failed"


class DeploymentAlias(str, Enum):
    """Supported deployment slots."""

    CANDIDATE = "candidate"
    CHALLENGER = "challenger"
    CHAMPION = "champion"
    EXPERIMENTAL = "experimental"


class RunStatus(str, Enum):
    """Statuses accepted for newly created inference runs."""

    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImageJobStatus(str, Enum):
    """Lifecycle of an image-analysis job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class QualityStatus(str, Enum):
    """Image or cell quality assessment."""

    NOT_ASSESSED = "not_assessed"
    PENDING = "pending"
    PASSED = "passed"
    WARNING = "warning"
    REJECTED = "rejected"
    FAILED = "failed"
    SKIPPED = "skipped"


class ConfidenceLevel(str, Enum):
    """Optional human-readable prediction confidence band."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNCERTAIN = "uncertain"
    NOT_ASSESSED = "not_assessed"


class ReviewStatus(str, Enum):
    """Clinical review state of a cell prediction."""

    UNREVIEWED = "unreviewed"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CORRECTED = "corrected"
    REJECTED = "rejected"


def _uuid(value: UUID | str | None, field_name: str, *, required: bool = True) -> str | None:
    if value in (None, ""):
        if required:
            raise GovernanceValidationError(f"{field_name} es obligatorio.")
        return None
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise GovernanceValidationError(
            f"{field_name} debe ser un UUID válido."
        ) from exc


def _non_empty(value: str | None, field_name: str, *, required: bool = True) -> str | None:
    if value is None:
        if required:
            raise GovernanceValidationError(f"{field_name} es obligatorio.")
        return None
    normalized = str(value).strip()
    if not normalized:
        if required:
            raise GovernanceValidationError(f"{field_name} no puede estar vacío.")
        return None
    return normalized


def _optional_non_blank(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        raise GovernanceValidationError(
            f"{field_name} no puede estar vacío cuando se entrega."
        )
    return normalized


def _enum_value(value: str | Enum, enum_type: type[Enum], field_name: str) -> str:
    raw_value = value.value if isinstance(value, Enum) else value
    try:
        return str(enum_type(raw_value).value)
    except (TypeError, ValueError) as exc:
        expected = ", ".join(item.value for item in enum_type)
        raise GovernanceValidationError(
            f"{field_name} inválido: {raw_value!r}. Esperado: {expected}."
        ) from exc


def _mapping(value: Mapping[str, Any] | None, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise GovernanceValidationError(f"{field_name} debe ser un objeto JSON.")
    return dict(value)


def _sha256(value: str) -> str:
    normalized = _non_empty(value, "artifact_sha256")
    if normalized is None or not SHA256_PATTERN.fullmatch(normalized):
        raise GovernanceValidationError(
            "artifact_sha256 debe contener exactamente 64 caracteres hexadecimales."
        )
    return normalized.lower()


def _optional_sha256(value: str | None, field_name: str) -> str | None:
    if value in (None, ""):
        return None
    normalized = _non_empty(value, field_name)
    if normalized is None or not SHA256_PATTERN.fullmatch(normalized):
        raise GovernanceValidationError(
            f"{field_name} debe contener exactamente 64 caracteres hexadecimales."
        )
    return normalized.lower()


def _probability(value: float, field_name: str) -> float:
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise GovernanceValidationError(
            f"{field_name} debe ser un número entre 0 y 1."
        ) from exc
    if not 0.0 <= normalized <= 1.0:
        raise GovernanceValidationError(f"{field_name} debe estar entre 0 y 1.")
    return normalized


def _non_negative_integer(value: int, field_name: str) -> int:
    if isinstance(value, bool):
        raise GovernanceValidationError(f"{field_name} debe ser un entero no negativo.")
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise GovernanceValidationError(
            f"{field_name} debe ser un entero no negativo."
        ) from exc
    if normalized != value or normalized < 0:
        raise GovernanceValidationError(f"{field_name} debe ser un entero no negativo.")
    return normalized


def _positive_integer(value: int, field_name: str) -> int:
    normalized = _non_negative_integer(value, field_name)
    if normalized == 0:
        raise GovernanceValidationError(f"{field_name} debe ser mayor que cero.")
    return normalized


def _class_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    normalized = _mapping(value or CLINICAL_CLASS_MAPPING, "class_mapping")
    string_keys = {str(key): item for key, item in normalized.items()}
    if (
        string_keys.get("0") != NEGATIVE_LABEL
        or string_keys.get("1") != POSITIVE_LABEL
    ):
        raise GovernanceValidationError(
            "class_mapping debe respetar 0=uninfected y 1=parasitized."
        )
    if "negative_class_index" in string_keys and string_keys["negative_class_index"] != 0:
        raise GovernanceValidationError("negative_class_index debe ser 0.")
    if "positive_class_index" in string_keys and string_keys["positive_class_index"] != 1:
        raise GovernanceValidationError("positive_class_index debe ser 1.")
    return string_keys


def _optional_timestamp(value: datetime | None, field_name: str) -> datetime | None:
    if value is not None and not isinstance(value, datetime):
        raise GovernanceValidationError(f"{field_name} debe ser datetime o None.")
    return value


@dataclass(frozen=True)
class ModelVersion:
    """Immutable identity and artifact snapshot produced by a training run."""

    training_run_id: UUID | str
    model_name: str
    version_number: int
    checkpoint_artifact_id: UUID | str
    artifact_path: str
    artifact_sha256: str
    artifact_size_bytes: int
    framework: str
    framework_version: str | None = None
    artifact_uri: str | None = None
    preprocessing_profile_snapshot: Mapping[str, Any] = field(default_factory=dict)
    class_mapping: Mapping[str, Any] = field(
        default_factory=lambda: dict(CLINICAL_CLASS_MAPPING)
    )
    input_signature: Mapping[str, Any] = field(default_factory=dict)
    output_signature: Mapping[str, Any] = field(default_factory=dict)
    status: ModelVersionStatus | str = ModelVersionStatus.DISCOVERED
    lineage_status: LineageStatus | str = LineageStatus.RESOLVED
    artifact_hash_reuse_justification: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    id: UUID | str | None = None
    created_at: datetime | None = None
    validated_at: datetime | None = None
    approved_at: datetime | None = None
    retired_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _uuid(self.id, "id", required=False))
        object.__setattr__(
            self, "training_run_id", _uuid(self.training_run_id, "training_run_id")
        )
        object.__setattr__(
            self,
            "checkpoint_artifact_id",
            _uuid(self.checkpoint_artifact_id, "checkpoint_artifact_id"),
        )
        object.__setattr__(self, "model_name", _non_empty(self.model_name, "model_name"))
        object.__setattr__(
            self,
            "version_number",
            _positive_integer(self.version_number, "version_number"),
        )
        object.__setattr__(
            self, "artifact_path", _non_empty(self.artifact_path, "artifact_path")
        )
        object.__setattr__(
            self,
            "artifact_uri",
            _non_empty(self.artifact_uri, "artifact_uri", required=False),
        )
        object.__setattr__(self, "artifact_sha256", _sha256(self.artifact_sha256))
        object.__setattr__(
            self,
            "artifact_size_bytes",
            _non_negative_integer(self.artifact_size_bytes, "artifact_size_bytes"),
        )
        object.__setattr__(self, "framework", _non_empty(self.framework, "framework"))
        object.__setattr__(
            self,
            "framework_version",
            _non_empty(self.framework_version, "framework_version", required=False),
        )
        object.__setattr__(
            self,
            "preprocessing_profile_snapshot",
            _mapping(
                self.preprocessing_profile_snapshot,
                "preprocessing_profile_snapshot",
            ),
        )
        object.__setattr__(self, "class_mapping", _class_mapping(self.class_mapping))
        object.__setattr__(
            self, "input_signature", _mapping(self.input_signature, "input_signature")
        )
        object.__setattr__(
            self, "output_signature", _mapping(self.output_signature, "output_signature")
        )
        object.__setattr__(
            self, "status", _enum_value(self.status, ModelVersionStatus, "status")
        )
        object.__setattr__(
            self,
            "lineage_status",
            _enum_value(self.lineage_status, LineageStatus, "lineage_status"),
        )
        object.__setattr__(
            self,
            "artifact_hash_reuse_justification",
            _optional_non_blank(
                self.artifact_hash_reuse_justification,
                "artifact_hash_reuse_justification",
            ),
        )
        object.__setattr__(self, "metadata", _mapping(self.metadata, "metadata"))
        for field_name in ("created_at", "validated_at", "approved_at", "retired_at"):
            object.__setattr__(
                self, field_name, _optional_timestamp(getattr(self, field_name), field_name)
            )


@dataclass(frozen=True)
class DeployedModelVersion:
    """Authorization snapshot for using one model version in inference."""

    model_version_id: UUID | str
    deployment_name: str
    environment: str
    alias: DeploymentAlias | str
    threshold_value: float
    threshold_profile_snapshot: Mapping[str, Any] = field(default_factory=dict)
    preprocessing_profile_snapshot: Mapping[str, Any] = field(default_factory=dict)
    image_quality_policy_snapshot: Mapping[str, Any] = field(default_factory=dict)
    label_mapping_snapshot: Mapping[str, Any] = field(default_factory=dict)
    status: DeploymentStatus | str = DeploymentStatus.PENDING
    checkpoint_artifact_id: UUID | str | None = None
    threshold_calibration_id: UUID | str | None = None
    artifact_sha256: str | None = None
    artifact_size_bytes: int | None = None
    positive_label: str = POSITIVE_LABEL
    score_name: str = "probability_parasitized"
    supersedes_deployment_id: UUID | str | None = None
    rollback_of_deployment_id: UUID | str | None = None
    deployed_by: str | None = None
    retired_by: str | None = None
    deployment_reason: str | None = None
    retirement_reason: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    id: UUID | str | None = None
    created_at: datetime | None = None
    deployed_at: datetime | None = None
    retired_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _uuid(self.id, "id", required=False))
        object.__setattr__(
            self, "model_version_id", _uuid(self.model_version_id, "model_version_id")
        )
        for field_name in (
            "checkpoint_artifact_id",
            "threshold_calibration_id",
            "supersedes_deployment_id",
            "rollback_of_deployment_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _uuid(getattr(self, field_name), field_name, required=False),
            )
        object.__setattr__(
            self, "deployment_name", _non_empty(self.deployment_name, "deployment_name")
        )
        object.__setattr__(self, "environment", _non_empty(self.environment, "environment"))
        alias = self.alias.value if isinstance(self.alias, Enum) else self.alias
        object.__setattr__(self, "alias", _non_empty(alias, "alias"))
        object.__setattr__(
            self, "threshold_value", _probability(self.threshold_value, "threshold_value")
        )
        for field_name in (
            "threshold_profile_snapshot",
            "preprocessing_profile_snapshot",
            "image_quality_policy_snapshot",
            "label_mapping_snapshot",
            "metadata",
        ):
            object.__setattr__(
                self, field_name, _mapping(getattr(self, field_name), field_name)
            )
        object.__setattr__(
            self, "status", _enum_value(self.status, DeploymentStatus, "status")
        )
        object.__setattr__(
            self,
            "artifact_sha256",
            _optional_sha256(self.artifact_sha256, "artifact_sha256"),
        )
        if self.artifact_size_bytes is not None:
            object.__setattr__(
                self,
                "artifact_size_bytes",
                _non_negative_integer(self.artifact_size_bytes, "artifact_size_bytes"),
            )
        if self.positive_label != POSITIVE_LABEL:
            raise GovernanceValidationError("positive_label debe ser parasitized.")
        if self.score_name != "probability_parasitized":
            raise GovernanceValidationError(
                "score_name debe ser probability_parasitized."
            )
        if self.label_mapping_snapshot:
            object.__setattr__(
                self,
                "label_mapping_snapshot",
                _class_mapping(self.label_mapping_snapshot),
            )
        for field_name in (
            "deployed_by",
            "retired_by",
            "deployment_reason",
            "retirement_reason",
        ):
            object.__setattr__(
                self,
                field_name,
                _non_empty(getattr(self, field_name), field_name, required=False),
            )
        for field_name in ("created_at", "deployed_at", "retired_at"):
            object.__setattr__(
                self, field_name, _optional_timestamp(getattr(self, field_name), field_name)
            )
        if self.status == DeploymentStatus.ACTIVE.value and self.deployed_at is None:
            raise GovernanceValidationError("deployed_at es obligatorio para status=active.")
        if self.status == DeploymentStatus.ACTIVE.value and self.deployed_by is None:
            raise GovernanceValidationError("deployed_by es obligatorio para status=active.")
        if self.status == DeploymentStatus.ACTIVE.value:
            object.__setattr__(
                self,
                "label_mapping_snapshot",
                _class_mapping(self.label_mapping_snapshot),
            )
        if self.status == DeploymentStatus.RETIRED.value and self.retired_at is None:
            raise GovernanceValidationError("retired_at es obligatorio para status=retired.")
        if (
            self.deployed_at is not None
            and self.retired_at is not None
            and self.retired_at < self.deployed_at
        ):
            raise GovernanceValidationError("retired_at no puede preceder deployed_at.")


@dataclass(frozen=True)
class InferenceRun:
    """Inference specialization of a row in the shared runs table."""

    deployed_model_version_id: UUID | str
    backend_version: str
    pipeline_version: str
    status: RunStatus | str = RunStatus.STARTED
    configuration: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    model_version_id: UUID | str | None = None
    id: UUID | str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _uuid(self.id, "id", required=False))
        object.__setattr__(
            self,
            "deployed_model_version_id",
            _uuid(self.deployed_model_version_id, "deployed_model_version_id"),
        )
        object.__setattr__(
            self,
            "model_version_id",
            _uuid(self.model_version_id, "model_version_id", required=False),
        )
        object.__setattr__(
            self, "backend_version", _non_empty(self.backend_version, "backend_version")
        )
        object.__setattr__(
            self, "pipeline_version", _non_empty(self.pipeline_version, "pipeline_version")
        )
        object.__setattr__(self, "status", _enum_value(self.status, RunStatus, "status"))
        object.__setattr__(
            self, "configuration", _mapping(self.configuration, "configuration")
        )
        object.__setattr__(self, "metadata", _mapping(self.metadata, "metadata"))
        object.__setattr__(
            self,
            "error_message",
            _non_empty(self.error_message, "error_message", required=False),
        )
        for field_name in ("started_at", "completed_at"):
            object.__setattr__(
                self, field_name, _optional_timestamp(getattr(self, field_name), field_name)
            )
        if (
            self.started_at is not None
            and self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            raise GovernanceValidationError("completed_at no puede preceder started_at.")


@dataclass(frozen=True)
class ImageAnalysisJob:
    """Auditable processing state for one source image."""

    inference_run_id: UUID | str
    deployed_model_version_id: UUID | str
    model_version_id: UUID | str
    status: ImageJobStatus | str = ImageJobStatus.PENDING
    quality_status: QualityStatus | str = QualityStatus.NOT_ASSESSED
    quality_metrics: Mapping[str, Any] = field(default_factory=dict)
    threshold_used: float | None = None
    threshold_source: str | None = None
    summary: Mapping[str, Any] = field(default_factory=dict)
    total_cells: int | None = None
    positive_cells: int | None = None
    source_image_id: UUID | str | None = None
    input_artifact_id: UUID | str | None = None
    idempotency_key: str | None = None
    sample_id: str | None = None
    patient_id: str | None = None
    slide_id: str | None = None
    error_message: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    id: UUID | str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _uuid(self.id, "id", required=False))
        object.__setattr__(
            self, "inference_run_id", _uuid(self.inference_run_id, "inference_run_id")
        )
        object.__setattr__(
            self,
            "deployed_model_version_id",
            _uuid(self.deployed_model_version_id, "deployed_model_version_id"),
        )
        object.__setattr__(
            self, "model_version_id", _uuid(self.model_version_id, "model_version_id")
        )
        object.__setattr__(
            self,
            "source_image_id",
            _uuid(self.source_image_id, "source_image_id", required=False),
        )
        object.__setattr__(
            self,
            "input_artifact_id",
            _uuid(self.input_artifact_id, "input_artifact_id", required=False),
        )
        if self.input_artifact_id is None and self.source_image_id is None:
            raise GovernanceValidationError(
                "input_artifact_id o source_image_id es obligatorio."
            )
        object.__setattr__(self, "status", _enum_value(self.status, ImageJobStatus, "status"))
        object.__setattr__(
            self,
            "quality_status",
            _enum_value(self.quality_status, QualityStatus, "quality_status"),
        )
        object.__setattr__(
            self, "quality_metrics", _mapping(self.quality_metrics, "quality_metrics")
        )
        if self.threshold_used is not None:
            object.__setattr__(
                self,
                "threshold_used",
                _probability(self.threshold_used, "threshold_used"),
            )
        for field_name in (
            "threshold_source",
            "sample_id",
            "patient_id",
            "slide_id",
            "error_message",
        ):
            object.__setattr__(
                self,
                field_name,
                _non_empty(getattr(self, field_name), field_name, required=False),
            )
        object.__setattr__(
            self,
            "idempotency_key",
            _optional_non_blank(self.idempotency_key, "idempotency_key"),
        )
        object.__setattr__(self, "summary", _mapping(self.summary, "summary"))
        object.__setattr__(self, "metadata", _mapping(self.metadata, "metadata"))
        for field_name in ("total_cells", "positive_cells"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self, field_name, _non_negative_integer(value, field_name)
                )
        if (
            self.total_cells is not None
            and self.positive_cells is not None
            and self.positive_cells > self.total_cells
        ):
            raise GovernanceValidationError(
                "positive_cells no puede ser mayor que total_cells."
            )
        for field_name in ("created_at", "updated_at", "started_at", "completed_at"):
            object.__setattr__(
                self, field_name, _optional_timestamp(getattr(self, field_name), field_name)
            )
        if (
            self.started_at is not None
            and self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            raise GovernanceValidationError("completed_at no puede preceder started_at.")


@dataclass(frozen=True)
class CellPrediction:
    """Cell-scoped prediction persisted in the existing predictions table."""

    image_analysis_job_id: UUID | str
    inference_run_id: UUID | str
    deployed_model_version_id: UUID | str
    classifier_model_version_id: UUID | str
    cell_index: int
    probability_parasitized: float
    probability_uninfected: float
    threshold_used: float
    predicted_class: int
    predicted_label: str
    detector_model_version_id: UUID | str | None = None
    bbox_x: float | None = None
    bbox_y: float | None = None
    bbox_width: float | None = None
    bbox_height: float | None = None
    crop_artifact_id: UUID | str | None = None
    confidence_level: ConfidenceLevel | str | None = ConfidenceLevel.NOT_ASSESSED
    quality_status: QualityStatus | str | None = QualityStatus.NOT_ASSESSED
    explanation_artifact_id: UUID | str | None = None
    source_image_id: UUID | str | None = None
    review_status: ReviewStatus | str = ReviewStatus.UNREVIEWED
    reviewed_label: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    model_version_id: UUID | str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    id: UUID | str | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "id",
            "detector_model_version_id",
            "crop_artifact_id",
            "explanation_artifact_id",
            "source_image_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _uuid(getattr(self, field_name), field_name, required=False),
            )
        for field_name in (
            "image_analysis_job_id",
            "inference_run_id",
            "deployed_model_version_id",
            "classifier_model_version_id",
        ):
            object.__setattr__(self, field_name, _uuid(getattr(self, field_name), field_name))
        normalized_model_version_id = _uuid(
            self.model_version_id,
            "model_version_id",
            required=False,
        ) or self.classifier_model_version_id
        if normalized_model_version_id != self.classifier_model_version_id:
            raise GovernanceValidationError(
                "model_version_id debe coincidir con classifier_model_version_id."
            )
        object.__setattr__(self, "model_version_id", normalized_model_version_id)
        object.__setattr__(
            self, "cell_index", _non_negative_integer(self.cell_index, "cell_index")
        )
        for field_name in (
            "probability_parasitized",
            "probability_uninfected",
            "threshold_used",
        ):
            object.__setattr__(
                self, field_name, _probability(getattr(self, field_name), field_name)
            )
        try:
            normalized_class = _non_negative_integer(
                self.predicted_class,
                "predicted_class",
            )
        except GovernanceValidationError as exc:
            raise GovernanceValidationError(
                "predicted_class solo puede ser 0 o 1."
            ) from exc
        if normalized_class not in (0, 1):
            raise GovernanceValidationError("predicted_class solo puede ser 0 o 1.")
        object.__setattr__(self, "predicted_class", normalized_class)
        expected_label = CLINICAL_CLASS_MAPPING[str(normalized_class)]
        if self.predicted_label != expected_label:
            raise GovernanceValidationError(
                "predicted_label debe coincidir con predicted_class: "
                f"{normalized_class}={expected_label}."
            )
        bbox_values = (self.bbox_x, self.bbox_y, self.bbox_width, self.bbox_height)
        if any(value is None for value in bbox_values):
            raise GovernanceValidationError(
                "bbox_x, bbox_y, bbox_width y bbox_height son obligatorios."
            )
        try:
            bbox_x, bbox_y, bbox_width, bbox_height = map(float, bbox_values)
        except (TypeError, ValueError) as exc:
            raise GovernanceValidationError("Los valores bbox deben ser numéricos.") from exc
        if (
            not all(math.isfinite(value) for value in (bbox_x, bbox_y, bbox_width, bbox_height))
            or bbox_x < 0
            or bbox_y < 0
            or bbox_width <= 0
            or bbox_height <= 0
        ):
            raise GovernanceValidationError(
                "bbox_x/bbox_y deben ser >= 0 y bbox_width/bbox_height > 0."
            )
        object.__setattr__(self, "bbox_x", bbox_x)
        object.__setattr__(self, "bbox_y", bbox_y)
        object.__setattr__(self, "bbox_width", bbox_width)
        object.__setattr__(self, "bbox_height", bbox_height)
        if self.confidence_level is not None:
            object.__setattr__(
                self,
                "confidence_level",
                _enum_value(self.confidence_level, ConfidenceLevel, "confidence_level"),
            )
        if self.quality_status is not None:
            object.__setattr__(
                self,
                "quality_status",
                _enum_value(self.quality_status, QualityStatus, "quality_status"),
            )
        object.__setattr__(
            self,
            "review_status",
            _enum_value(self.review_status, ReviewStatus, "review_status"),
        )
        if self.reviewed_label is not None:
            normalized_review = _non_empty(
                self.reviewed_label, "reviewed_label", required=False
            )
            if normalized_review not in CLINICAL_CLASS_MAPPING.values():
                raise GovernanceValidationError(
                    "reviewed_label solo puede ser uninfected o parasitized."
                )
            object.__setattr__(self, "reviewed_label", normalized_review)
        object.__setattr__(
            self,
            "reviewed_by",
            _non_empty(self.reviewed_by, "reviewed_by", required=False),
        )
        object.__setattr__(
            self, "reviewed_at", _optional_timestamp(self.reviewed_at, "reviewed_at")
        )
        object.__setattr__(self, "metadata", _mapping(self.metadata, "metadata"))
        object.__setattr__(
            self, "created_at", _optional_timestamp(self.created_at, "created_at")
        )


@dataclass(frozen=True)
class LineageRecord:
    """One flattened path through training, deployment and inference lineage."""

    training_run_id: UUID | str
    model_version_id: UUID | str
    checkpoint_artifact_id: UUID | str | None = None
    deployed_model_version_id: UUID | str | None = None
    inference_run_id: UUID | str | None = None
    image_analysis_job_id: UUID | str | None = None
    prediction_id: UUID | str | None = None
    derived_run_id: UUID | str | None = None
    derived_run_type: str | None = None
    relationship_type: str | None = None
    model_name: str | None = None
    version_number: int | None = None
    artifact_path: str | None = None
    artifact_sha256: str | None = None
    deployment_name: str | None = None
    environment: str | None = None
    alias: str | None = None
    model_version_status: str | None = None
    deployment_status: str | None = None
    inference_status: str | None = None
    image_job_status: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("training_run_id", "model_version_id"):
            object.__setattr__(self, field_name, _uuid(getattr(self, field_name), field_name))
        for field_name in (
            "deployed_model_version_id",
            "checkpoint_artifact_id",
            "inference_run_id",
            "image_analysis_job_id",
            "prediction_id",
            "derived_run_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _uuid(getattr(self, field_name), field_name, required=False),
            )
        for field_name in (
            "artifact_path",
            "deployment_name",
            "environment",
            "alias",
            "derived_run_type",
            "relationship_type",
        ):
            object.__setattr__(
                self,
                field_name,
                _non_empty(getattr(self, field_name), field_name, required=False),
            )
        object.__setattr__(
            self,
            "model_name",
            _non_empty(self.model_name, "model_name", required=False),
        )
        if self.version_number is not None:
            object.__setattr__(
                self,
                "version_number",
                _positive_integer(self.version_number, "version_number"),
            )
        object.__setattr__(
            self,
            "artifact_sha256",
            _optional_sha256(self.artifact_sha256, "artifact_sha256"),
        )
