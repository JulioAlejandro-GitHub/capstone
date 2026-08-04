from __future__ import annotations

import hashlib
import io
import json
import logging
import math
import os
import secrets
import stat
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median
from typing import Any
from uuid import UUID, uuid4

from fastapi import Request
from PIL import Image, UnidentifiedImageError
from sqlalchemy.engine import Engine

from app.audit import record_event
from app.config import Settings, get_settings
from app.db import get_primary_engine
from app.security import Principal
from app.services.cell_explanation_storage import (
    CellExplanationStorage,
    StagedCellExplanation,
)
from app.services.local_storage import LocalStorage, StorageError
from app.services.productive_model import (
    EXPECTED_LABEL_MAPPING,
    ProductiveModelError,
    ProductiveModelResolver,
    ResolvedProductiveModel,
    sha256_file,
)


INFERENCE_VERSION = "cell-classification-v1"
GRADCAM_METHOD_VERSION = "gradcam-v1"
AGGREGATION_POLICY_VERSION = "cell-candidate-aggregation-v1"
PROBABILITY_SUM_TOLERANCE = 1e-6
ACTIVE_RUN_STALE_AFTER_SECONDS = 60 * 60
PENDING_EXPLANATION_STALE_AFTER_SECONDS = 15 * 60
logger = logging.getLogger(__name__)


class CellClassificationError(ValueError):
    def __init__(
        self,
        status_code: int,
        detail: str,
        code: str = "CELL_CLASSIFICATION_ERROR",
        *,
        classification_run_id: str | None = None,
        stage: str | None = None,
        retryable: bool | None = None,
    ):
        self.status_code = status_code
        self.detail = detail
        self.code = code
        self.classification_run_id = classification_run_id
        self.stage = stage
        self.retryable = retryable
        super().__init__(detail)


class GradCAMUnsupportedError(ValueError):
    """Typed boundary for a genuine model/Grad-CAM incompatibility."""


def canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _value(row: Mapping[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in row and row[name] is not None:
            return row[name]
    return default


def freeze_classification_inputs(
    detections: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    """Freeze every candidate and deterministically include exclusions."""

    ordered = sorted(
        detections,
        key=lambda row: (
            str(_value(row, "microscopy_image_id", default="")),
            int(_value(row, "cell_index", default=0)),
            str(_value(row, "cell_detection_id", "id", default="")),
        ),
    )
    frozen: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    for input_order, source in enumerate(ordered, 1):
        detection_id = str(_value(source, "cell_detection_id", "id", default=""))
        crop_id = _value(source, "crop_id")
        crop_sha = str(_value(source, "crop_sha256", "sha256", default="")).lower()
        crop_width = _value(source, "crop_width_px")
        crop_height = _value(source, "crop_height_px")
        storage_key = _value(
            source,
            "crop_storage_key",
            "relative_storage_key",
            "crop_relative_storage_key",
        )
        review_status = str(
            _value(
                source,
                "detection_review_status",
                "review_status",
                default="unreviewed",
            )
        )
        exclusion_reason: str | None = _value(
            source, "_exclusion_reason", default=None
        )
        if exclusion_reason is not None:
            exclusion_reason = str(exclusion_reason)
        elif review_status == "rejected":
            exclusion_reason = "DETECTION_REJECTED_BY_REVIEW"
        elif not crop_id or not storage_key:
            exclusion_reason = "CROP_MISSING"
        elif (
            len(crop_sha) != 64
            or not all(char in "0123456789abcdef" for char in crop_sha)
            or not crop_width
            or not crop_height
            or int(crop_width) < 1
            or int(crop_height) < 1
        ):
            exclusion_reason = "CROP_METADATA_INVALID"
        eligible = exclusion_reason is None
        item = {
            "id": uuid4(),
            "cell_detection_id": UUID(detection_id),
            "microscopy_image_id": UUID(
                str(_value(source, "microscopy_image_id"))
            ),
            "crop_id": UUID(str(crop_id)) if crop_id else None,
            "input_order": input_order,
            "image_sequence_number": int(
                _value(
                    source,
                    "image_sequence_number",
                    "source_sequence_number",
                    "sequence_number",
                )
            ),
            "cell_index": int(_value(source, "cell_index")),
            "cell_code": str(_value(source, "cell_code")),
            "detector_key": str(_value(source, "detector_key")),
            "detector_version": str(_value(source, "detector_version")),
            "detector_algorithm_version": str(
                _value(source, "detector_algorithm_version", "algorithm_version")
            ),
            "crop_sha256": crop_sha if crop_id else None,
            "crop_file_size_bytes": _value(source, "crop_file_size_bytes"),
            "crop_width_px": int(crop_width) if crop_width else None,
            "crop_height_px": int(crop_height) if crop_height else None,
            "detection_review_status_at_creation": review_status,
            "eligible": eligible,
            "exclusion_reason": exclusion_reason,
            # Runtime-only. Repository adapters must omit underscore keys.
            "_crop_storage_key": str(storage_key) if storage_key else None,
        }
        frozen.append(item)
        manifest.append(
            {
                "cell_detection_id": detection_id,
                "microscopy_image_id": str(item["microscopy_image_id"]),
                "cell_index": item["cell_index"],
                "cell_code": item["cell_code"],
                "crop_id": str(item["crop_id"]) if item["crop_id"] else None,
                "crop_sha256": item["crop_sha256"],
                "crop_width_px": item["crop_width_px"],
                "crop_height_px": item["crop_height_px"],
                "detector": {
                    "key": item["detector_key"],
                    "version": item["detector_version"],
                    "algorithm_version": item["detector_algorithm_version"],
                },
                "detection_run_id": str(_value(source, "detection_run_id")),
                "detection_review_status": review_status,
                "eligible": eligible,
                "exclusion_reason": exclusion_reason,
            }
        )
    return frozen, canonical_json_sha256(manifest)


def _output_width(output_signature: Mapping[str, Any] | None) -> int | None:
    signature = dict(output_signature or {})
    shape = (
        signature.get("shape")
        or signature.get("output_shape")
        or signature.get("outputs")
    )
    if (
        isinstance(shape, list)
        and len(shape) == 1
        and isinstance(shape[0], Mapping)
    ):
        return _output_width(shape[0])
    if isinstance(shape, (list, tuple)) and shape:
        try:
            return int(shape[-1])
        except (TypeError, ValueError):
            return None
    return None


def normalize_binary_outputs(
    outputs: Any,
    *,
    batch_size: int,
    label_mapping: Mapping[str, Any],
    output_signature: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Normalize a declared sigmoid or two-class softmax output safely."""

    mapping = {str(key): value for key, value in label_mapping.items()}
    try:
        mapping["positive_class"] = int(mapping["positive_class"])
    except (KeyError, TypeError, ValueError):
        pass
    if any(mapping.get(key) != value for key, value in EXPECTED_LABEL_MAPPING.items()):
        raise ValueError("label_mapping binario no canónico")
    if batch_size < 1:
        raise ValueError("batch_size debe ser positivo")
    if isinstance(outputs, (list, tuple)) and len(outputs) != 1:
        # A plain numeric list is one output tensor, not a list of tensors.
        if not all(isinstance(item, (int, float)) for item in outputs):
            if not all(isinstance(item, (list, tuple)) for item in outputs):
                raise ValueError("salidas múltiples no soportadas")
    if (
        isinstance(outputs, (list, tuple))
        and len(outputs) == 1
        and hasattr(outputs[0], "shape")
    ):
        outputs = outputs[0]
    raw_value = outputs.tolist() if hasattr(outputs, "tolist") else outputs
    width = _output_width(output_signature)
    if isinstance(raw_value, (int, float)):
        rows = [[float(raw_value)]]
    elif isinstance(raw_value, (list, tuple)):
        if all(isinstance(item, (int, float)) for item in raw_value):
            if batch_size == 1 and len(raw_value) == 2 and width == 2:
                rows = [[float(item) for item in raw_value]]
            elif len(raw_value) == batch_size:
                rows = [[float(item)] for item in raw_value]
            else:
                raise ValueError("shape de salida no coincide con el batch")
        elif all(isinstance(item, (list, tuple)) for item in raw_value):
            rows = [[float(value) for value in item] for item in raw_value]
        else:
            raise ValueError("rank de salida no soportado")
    else:
        raise ValueError("tipo de salida no soportado")
    if len(rows) != batch_size:
        raise ValueError("shape de salida no coincide con el batch")
    if any(len(row) not in {1, 2} for row in rows):
        raise ValueError("sólo se admite salida binaria")
    if len({len(row) for row in rows}) != 1:
        raise ValueError("filas de salida no homogéneas")
    if width not in {1, 2}:
        raise ValueError("output_signature congelada ausente o inválida")
    if len(rows[0]) != width:
        raise ValueError(
            "ancho real de salida no coincide con output_signature congelada"
        )
    if any(not math.isfinite(value) for row in rows for value in row):
        raise ValueError("salida contiene NaN o infinito")

    signature = dict(output_signature or {})
    from_logits = signature.get("from_logits") is True or str(
        signature.get("activation") or ""
    ).lower() in {"linear", "logits"}
    probabilities: list[float] = []
    if len(rows[0]) == 1:
        for row in rows:
            scalar = row[0]
            if from_logits:
                scalar = 1.0 / (1.0 + math.exp(-max(-80.0, min(80.0, scalar))))
            elif not 0.0 <= scalar <= 1.0:
                raise ValueError("salida sigmoid fuera de [0,1]")
            probabilities.append(scalar)
    else:
        for row in rows:
            values = list(row)
            if from_logits:
                maximum = max(values)
                exponentials = [math.exp(value - maximum) for value in values]
                total = sum(exponentials)
                values = [value / total for value in exponentials]
            elif any(value < 0.0 or value > 1.0 for value in values):
                raise ValueError("salida softmax fuera de [0,1]")
            total = sum(values)
            if abs(total - 1.0) > PROBABILITY_SUM_TOLERANCE:
                raise ValueError("salida softmax no suma 1")
            values = [value / total for value in values]
            probabilities.append(values[int(mapping["positive_class"])])

    normalized = []
    for index, probability in enumerate(probabilities):
        parasitized = float(probability)
        if not math.isfinite(parasitized) or not 0.0 <= parasitized <= 1.0:
            raise ValueError("probabilidad parasitized inválida")
        normalized.append(
            {
                "raw_output": list(rows[index]),
                "probability_parasitized": parasitized,
                "probability_uninfected": float(1.0 - parasitized),
            }
        )
    return normalized


def iter_batches(
    items: Sequence[Any], batch_size: int
) -> list[Sequence[Any]]:
    if batch_size < 1:
        raise ValueError("batch_size debe ser positivo")
    return [
        items[start : start + batch_size]
        for start in range(0, len(items), batch_size)
    ]


def classification_decision(
    probability_parasitized: float,
    *,
    threshold: float,
    review_margin: float,
) -> dict[str, Any]:
    probability = float(probability_parasitized)
    threshold = float(threshold)
    review_margin = float(review_margin)
    if not all(math.isfinite(item) for item in (probability, threshold, review_margin)):
        raise ValueError("decisión contiene valores no finitos")
    if not 0.0 <= probability <= 1.0 or not 0.0 <= threshold <= 1.0:
        raise ValueError("probabilidad o threshold fuera de rango")
    if not 0.0 <= review_margin <= 1.0:
        raise ValueError("review_margin fuera de rango")
    predicted_class_index = 1 if probability >= threshold else 0
    distance = abs(probability - threshold)
    return {
        "predicted_label": (
            "parasitized" if predicted_class_index == 1 else "uninfected"
        ),
        "predicted_class_index": predicted_class_index,
        "decision_margin": distance,
        "near_threshold": distance <= review_margin,
    }


def aggregation_policy_snapshot() -> dict[str, Any]:
    return {
        "version": AGGREGATION_POLICY_VERSION,
        "scope": "candidate_cells",
        "suspicious_when_any_parasitized": True,
        "near_threshold_makes_negative_inconclusive": True,
        "partial_failure_makes_negative_inconclusive": True,
        "terminology": "experimental_screening_not_diagnosis",
    }


def build_automatic_summary(
    *,
    classification_run_id: str | UUID,
    analysis_run_id: str | UUID,
    detection_run_id: str | UUID,
    frozen_inputs: Sequence[Mapping[str, Any]],
    predictions: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    policy_snapshot = dict(policy or aggregation_policy_snapshot())
    eligible = [item for item in frozen_inputs if item.get("eligible") is True]
    completed = [
        item for item in predictions if item.get("prediction_status") == "completed"
    ]
    failed_count = sum(
        item.get("prediction_status") == "failed" for item in predictions
    )
    # A missing terminal prediction is treated as failed/inconclusive, never
    # silently removed from the denominator.
    failed_count += max(0, len(eligible) - len(predictions))
    parasitized = sum(item.get("predicted_label") == "parasitized" for item in completed)
    uninfected = sum(item.get("predicted_label") == "uninfected" for item in completed)
    near = sum(bool(item.get("near_threshold")) for item in completed)
    probabilities = [float(item["probability_parasitized"]) for item in completed]

    if parasitized > 0:
        outcome = "suspicious_cells_detected"
    elif (
        eligible
        and len(completed) == len(eligible)
        and failed_count == 0
        and (
            not policy_snapshot.get("near_threshold_makes_negative_inconclusive", True)
            or near == 0
        )
    ):
        outcome = "no_suspicious_cells_detected"
    else:
        outcome = "inconclusive"

    inputs_by_id = {
        str(item["id"]): item for item in frozen_inputs if item.get("eligible") is True
    }
    per_image: dict[str, dict[str, Any]] = {}
    for item in eligible:
        image_id = str(item["microscopy_image_id"])
        summary = per_image.setdefault(
            image_id,
            {
                "microscopy_image_id": image_id,
                "image_sequence_number": int(item["image_sequence_number"]),
                "eligible_cell_count": 0,
                "classified_cell_count": 0,
                "parasitized_candidate_count": 0,
                "uninfected_candidate_count": 0,
                "near_threshold_count": 0,
                "failed_prediction_count": 0,
            },
        )
        summary["eligible_cell_count"] += 1
    for prediction in predictions:
        source = inputs_by_id.get(str(prediction.get("classification_input_id")))
        if source is None:
            continue
        summary = per_image[str(source["microscopy_image_id"])]
        if prediction.get("prediction_status") == "completed":
            summary["classified_cell_count"] += 1
            key = (
                "parasitized_candidate_count"
                if prediction.get("predicted_label") == "parasitized"
                else "uninfected_candidate_count"
            )
            summary[key] += 1
            summary["near_threshold_count"] += int(
                bool(prediction.get("near_threshold"))
            )
        else:
            summary["failed_prediction_count"] += 1

    classified_count = len(completed)
    return {
        "id": uuid4(),
        "classification_run_id": UUID(str(classification_run_id)),
        "analysis_run_id": UUID(str(analysis_run_id)),
        "detection_run_id": UUID(str(detection_run_id)),
        "outcome": outcome,
        "eligible_cell_count": len(eligible),
        "classified_cell_count": classified_count,
        "parasitized_candidate_count": parasitized,
        "uninfected_candidate_count": uninfected,
        "near_threshold_count": near,
        "failed_prediction_count": failed_count,
        "parasitized_candidate_fraction": (
            float(parasitized / classified_count) if classified_count else None
        ),
        "maximum_probability_parasitized": (
            max(probabilities) if probabilities else None
        ),
        "mean_probability_parasitized": (
            mean(probabilities) if probabilities else None
        ),
        "median_probability_parasitized": (
            median(probabilities) if probabilities else None
        ),
        "per_image_summary": {
            "images": sorted(
                per_image.values(),
                key=lambda item: (
                    item["image_sequence_number"],
                    item["microscopy_image_id"],
                ),
            )
        },
        "aggregation_policy_snapshot": policy_snapshot,
    }


def build_revised_summary(
    automatic_summary: Mapping[str, Any],
    review_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Calculate a read-only human-reviewed projection.

    Detection rejections remove a candidate from the revised denominator.
    Classification corrections replace the displayed effective label only;
    the automatic prediction and stored automatic summary remain unchanged.
    """

    population = [
        row
        for row in review_rows
        if row.get("detection_review_status") != "rejected"
    ]
    considered = [
        row
        for row in population
        if row.get("prediction_status", "completed") == "completed"
    ]
    effective_labels: list[str] = []
    attention_count = 0
    for row in considered:
        decision = row.get(
            "classification_review_decision",
            row.get("classification_review_status"),
        )
        if decision == "corrected" and row.get("reviewed_label") in {
            "parasitized",
            "uninfected",
        }:
            effective_labels.append(str(row["reviewed_label"]))
        else:
            # confirmed never changes the scientific automatic label.
            effective_labels.append(
                str(row.get("predicted_label", row.get("automatic_label")))
            )
        if (
            decision == "needs_attention"
            or row.get("detection_review_status") == "needs_attention"
        ):
            attention_count += 1
    attention_count += sum(
        row.get("detection_review_status") == "needs_attention"
        for row in population
        if row.get("prediction_status", "completed") != "completed"
    )
    parasitized = effective_labels.count("parasitized")
    uninfected = effective_labels.count("uninfected")
    failed = sum(
        row.get("prediction_status", "completed") == "failed"
        for row in population
    )
    near = sum(bool(row.get("near_threshold")) for row in considered)
    if parasitized:
        outcome = "suspicious_cells_detected"
    elif (
        population
        and len(considered) == len(population)
        and not failed
        and not near
        and not attention_count
    ):
        outcome = "no_suspicious_cells_detected"
    else:
        outcome = "inconclusive"
    return {
        "kind": "reviewed_projection",
        "outcome": outcome,
        "eligible_cell_count": len(population),
        "classified_cell_count": len(effective_labels),
        "parasitized_candidate_count": parasitized,
        "uninfected_candidate_count": uninfected,
        "needs_attention_count": attention_count,
        "failed_prediction_count": failed,
        "near_threshold_count": near,
        "parasitized_candidate_fraction": (
            float(parasitized / len(effective_labels))
            if effective_labels
            else None
        ),
        "automatic_summary_unchanged": True,
    }


class CellClassificationService:
    def __init__(
        self,
        *,
        engine: Engine | None = None,
        settings: Settings | None = None,
        repository_factory: Callable[[Any], Any] | None = None,
        model_resolver: ProductiveModelResolver | None = None,
        local_storage: LocalStorage | None = None,
        explanation_storage: CellExplanationStorage | None = None,
        preprocessor: Callable[[Mapping[str, Any], ResolvedProductiveModel], Any]
        | None = None,
        predictor: Callable[[Any, Any], Any] | None = None,
        gradcam: Callable[..., Any] | None = None,
        auditor: Callable[..., None] = record_event,
        active_run_stale_after_seconds: int = ACTIVE_RUN_STALE_AFTER_SECONDS,
        pending_explanation_stale_after_seconds: int = (
            PENDING_EXPLANATION_STALE_AFTER_SECONDS
        ),
    ):
        if active_run_stale_after_seconds < 1:
            raise ValueError("active_run_stale_after_seconds debe ser positivo")
        if pending_explanation_stale_after_seconds < 1:
            raise ValueError(
                "pending_explanation_stale_after_seconds debe ser positivo"
            )
        self.engine = engine or get_primary_engine()
        self.settings = settings
        self.repository_factory = repository_factory
        self.model_resolver = model_resolver or ProductiveModelResolver(
            engine=self.engine
        )
        self.local_storage = local_storage
        self.explanation_storage = explanation_storage
        self.preprocessor = preprocessor
        self.predictor = predictor
        self.gradcam = gradcam
        self.auditor = auditor
        self.active_run_stale_after_seconds = active_run_stale_after_seconds
        self.pending_explanation_stale_after_seconds = (
            pending_explanation_stale_after_seconds
        )

    def _settings(self) -> Settings:
        return self.settings or get_settings()

    def _local(self) -> LocalStorage:
        return self.local_storage or LocalStorage(self._settings())

    def _explanations(self) -> CellExplanationStorage:
        return self.explanation_storage or CellExplanationStorage(self._local())

    def _repository(self, connection: Any) -> Any:
        if self.repository_factory is not None:
            return self.repository_factory(connection)
        from app.repositories.cell_classification import CellClassificationRepository

        return CellClassificationRepository(connection)

    @staticmethod
    def _public_input(item: Mapping[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in item.items() if not key.startswith("_")}

    @classmethod
    def public_model_snapshot(
        cls,
        snapshot: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Return an explicit public projection of the immutable model snapshot."""

        scalar_keys = (
            "schema_version",
            "model_registry_id",
            "production_model_id",
            "stage2_publication_id",
            "model_name",
            "model_version",
            "source_training_run_id",
            "source_evaluation_run_id",
            "checkpoint_artifact_id",
            "checkpoint_sha256",
            "checkpoint_size_bytes",
            "framework",
            "framework_version",
            "architecture",
            "input_width",
            "input_height",
            "input_channels",
            "positive_label",
            "positive_class_index",
            "threshold",
            "threshold_source",
            "published_at",
            "production_status",
            "loader_version",
            "inference_version",
            "batch_size",
            "review_margin",
        )
        result = {
            key: snapshot[key]
            for key in scalar_keys
            if key in snapshot
        }
        for signature_key in ("input_signature", "output_signature"):
            signature = snapshot.get(signature_key)
            if isinstance(signature, Mapping):
                result[signature_key] = {
                    key: signature[key]
                    for key in (
                        "shape",
                        "input_shape",
                        "output_shape",
                        "dtype",
                        "activation",
                        "from_logits",
                    )
                    if key in signature
                }
        preprocessing = snapshot.get("preprocessing")
        if isinstance(preprocessing, Mapping) and "mode" in preprocessing:
            result["preprocessing"] = {"mode": preprocessing["mode"]}
        mapping = snapshot.get("label_mapping")
        if isinstance(mapping, Mapping):
            result["label_mapping"] = {
                key: mapping[key]
                for key in (
                    "0",
                    "1",
                    "positive_class",
                    "positive_label",
                )
                if key in mapping
            }
        calibration = snapshot.get("calibration_metadata")
        if isinstance(calibration, Mapping):
            result["calibration_metadata"] = {
                key: calibration[key]
                for key in (
                    "threshold_calibration_id",
                    "threshold_policy",
                    "calibration_split",
                    "calibration_status",
                )
                if key in calibration
            }
        stage2 = snapshot.get("stage2_default")
        if isinstance(stage2, Mapping):
            result["stage2_default"] = {
                key: stage2[key]
                for key in (
                    "deployment_name",
                    "environment",
                    "alias",
                    "production_scope",
                    "deployment_id",
                )
                if key in stage2
            }
        policy = snapshot.get("explainability_policy")
        if isinstance(policy, Mapping):
            result["explainability_policy"] = {
                key: policy[key]
                for key in (
                    "version",
                    "method",
                    "scope",
                    "automatic_generation",
                    "manual_retry_required",
                    "bulk_generation",
                    "priority_hints",
                )
                if key in policy
            }
        return cls._public_record(result)

    @classmethod
    def _public_record(cls, value: Any) -> Any:
        if isinstance(value, Mapping):
            result: dict[str, Any] = {}
            for key, item in value.items():
                lowered = key.lower()
                if key == "model_snapshot":
                    if isinstance(item, Mapping):
                        result[key] = cls.public_model_snapshot(item)
                    continue
                if key == "preprocessing_snapshot":
                    if isinstance(item, Mapping) and "mode" in item:
                        result[key] = {"mode": item["mode"]}
                    continue
                if (
                    key.endswith("_storage_key")
                    or lowered in {"checkpoint_path", "artifact_path", "path"}
                    or lowered.endswith("_path")
                    or lowered.endswith("_uri")
                    or any(
                        marker in lowered
                        for marker in ("secret", "token", "password")
                    )
                ):
                    continue
                result[key] = cls._public_record(item)
            return result
        if isinstance(value, list):
            return [cls._public_record(item) for item in value]
        return value

    @classmethod
    def _public_explanation(cls, row: Mapping[str, Any]) -> dict[str, Any]:
        result = cls._public_record(dict(row))
        explanation_id = result.get("id")
        if explanation_id and result.get("status") == "generated":
            base = f"/api/v1/cell-classification/explanations/{explanation_id}"
            result["heatmap_content_url"] = f"{base}/heatmap"
            result["overlay_content_url"] = f"{base}/overlay"
        return result

    @staticmethod
    def _timestamp(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str) and value.strip():
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        else:
            return None
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed

    @classmethod
    def _is_stale(
        cls,
        row: Mapping[str, Any],
        *,
        timestamp_fields: Sequence[str],
        timeout_seconds: int,
        now: datetime | None = None,
    ) -> bool:
        timestamp = next(
            (
                parsed
                for field in timestamp_fields
                if (parsed := cls._timestamp(row.get(field))) is not None
            ),
            None,
        )
        if timestamp is None:
            # Active rows are required to carry a creation/start timestamp.
            # Missing or malformed timing metadata cannot remain active forever.
            return True
        current = now or datetime.now(UTC)
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        return (current - timestamp).total_seconds() >= timeout_seconds

    @staticmethod
    def _eligible_detection_run(run: Mapping[str, Any]) -> None:
        if run.get("ready_for_analysis") is not True:
            raise CellClassificationError(
                409,
                "El análisis no está habilitado para clasificación.",
                "ANALYSIS_NOT_READY",
            )
        if run.get("status") not in {"completed", "completed_with_warnings"}:
            raise CellClassificationError(
                409,
                "La ejecución de detección no está terminada.",
                "DETECTION_RUN_NOT_COMPLETED",
            )
        if "detections" not in run:
            raise CellClassificationError(
                409,
                "No fue posible congelar las detecciones candidatas.",
                "DETECTION_INPUTS_UNAVAILABLE",
            )
        detections = run["detections"]
        if not isinstance(detections, Sequence) or isinstance(
            detections, (str, bytes)
        ):
            raise CellClassificationError(
                409,
                "No fue posible congelar las detecciones candidatas.",
                "DETECTION_INPUTS_UNAVAILABLE",
            )
        detector_values = {
            "detector_key": run.get("detector_key"),
            "detector_version": run.get("detector_version"),
            "detector_algorithm_version": run.get(
                "algorithm_version",
                run.get("detector_algorithm_version"),
            ),
        }
        if any(not str(value or "").strip() for value in detector_values.values()):
            raise CellClassificationError(
                409,
                "El detector y sus versiones deben estar registrados.",
                "DETECTOR_IDENTITY_MISSING",
            )
        try:
            detection_count = int(run.get("detection_count"))
            crop_count = int(run.get("crop_count"))
        except (TypeError, ValueError) as exc:
            raise CellClassificationError(
                409,
                "Los conteos de detección y crops no son válidos.",
                "DETECTION_COUNTS_INVALID",
            ) from exc
        actual_crop_count = sum(bool(row.get("crop_id")) for row in detections)
        if detection_count < 1:
            raise CellClassificationError(
                409,
                "La ejecución no contiene detecciones candidatas.",
                "NO_DETECTIONS",
            )
        if crop_count < 1:
            raise CellClassificationError(
                409,
                "La ejecución no contiene crops para clasificación.",
                "NO_CROPS",
            )
        if (
            detection_count != len(detections)
            or crop_count != actual_crop_count
            or crop_count > detection_count
        ):
            raise CellClassificationError(
                409,
                "Los conteos de detección y crops no coinciden con sus registros.",
                "DETECTION_COUNTS_INVALID",
            )
        run_id = str(run.get("id") or "")
        for row in detections:
            if (
                str(row.get("detection_run_id") or "") != run_id
                or any(
                    str(row.get(key) or "").strip() != str(expected).strip()
                    for key, expected in detector_values.items()
                )
            ):
                raise CellClassificationError(
                    409,
                    "La identidad del detector no coincide en las detecciones.",
                    "DETECTOR_IDENTITY_MISMATCH",
                )

    def _preflight_detections(
        self, detections: Sequence[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        checked: list[dict[str, Any]] = []
        for source in detections:
            row = dict(source)
            if not row.get("crop_id") or not row.get("crop_storage_key"):
                checked.append(row)
                continue
            try:
                checksum = str(row.get("crop_sha256") or "").lower()
                file_size = int(row["crop_file_size_bytes"])
                width = int(row["crop_width_px"])
                height = int(row["crop_height_px"])
                if (
                    len(checksum) != 64
                    or any(
                        character not in "0123456789abcdef"
                        for character in checksum
                    )
                    or file_size < 1
                    or width < 1
                    or height < 1
                ):
                    raise ValueError("crop metadata inválida")
            except (KeyError, TypeError, ValueError, OverflowError):
                row["_exclusion_reason"] = "CROP_METADATA_INVALID"
                checked.append(row)
                continue
            try:
                path = self._local().resolve(
                    str(row["crop_storage_key"]), must_exist=True
                )
                info = path.lstat()
                if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                    row["_exclusion_reason"] = "CROP_NOT_REGULAR"
                elif (
                    info.st_size != file_size
                ):
                    row["_exclusion_reason"] = "CROP_SIZE_MISMATCH"
                elif sha256_file(path) != str(row.get("crop_sha256") or ""):
                    row["_exclusion_reason"] = "CROP_CHECKSUM_MISMATCH"
                else:
                    try:
                        with Image.open(path) as image:
                            if image.size != (
                                width,
                                height,
                            ):
                                row["_exclusion_reason"] = (
                                    "CROP_DIMENSIONS_MISMATCH"
                                )
                            image.verify()
                    except (UnidentifiedImageError, OSError, SyntaxError):
                        row["_exclusion_reason"] = "CROP_DECODE_FAILED"
            except FileNotFoundError:
                row["_exclusion_reason"] = "CROP_FILE_MISSING"
            except (OSError, StorageError):
                row["_exclusion_reason"] = "CROP_STORAGE_UNSAFE"
            checked.append(row)
        return checked

    def _terminalize_stale_run(
        self,
        repository: Any,
        row: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        if row.get("status") not in {"created", "processing"} or not self._is_stale(
            row,
            timestamp_fields=("updated_at", "started_at", "created_at"),
            timeout_seconds=self.active_run_stale_after_seconds,
        ):
            return None
        failed = repository.fail_run(
            row["id"],
            error_code="STALE_ACTIVE_RUN_TERMINATED",
            error_message=(
                "La ejecución activa excedió el tiempo de recuperación; "
                "un nuevo intento requiere una acción manual explícita."
            ),
        )
        if not failed:
            raise CellClassificationError(
                409,
                "La ejecución cambió de estado durante la recuperación.",
                "RUN_STATE_CONFLICT",
            )
        event = repository.add_event(
            classification_run_id=row["id"],
            event_type="cell_classification.run.failed",
            status="failed",
            message_code="STALE_ACTIVE_RUN_TERMINATED",
            metadata={"recovery_policy": "terminalize_only_no_automatic_retry"},
        )
        if not event:
            raise CellClassificationError(
                500,
                "No fue posible registrar la recuperación de la ejecución.",
                "RUN_RECOVERY_EVENT_FAILED",
            )
        return dict(failed)

    def _terminalize_stale_explanation(
        self,
        repository: Any,
        explanation: Mapping[str, Any],
        *,
        prediction: Mapping[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if explanation.get("status") != "pending" or not self._is_stale(
            explanation,
            timestamp_fields=("started_at", "created_at"),
            timeout_seconds=self.pending_explanation_stale_after_seconds,
        ):
            return None
        failed = repository.fail_explanation(
            explanation["id"],
            error_code="STALE_EXPLANATION_TERMINATED",
            error_message=(
                "La explicación pendiente excedió el tiempo de recuperación; "
                "un retry requiere una acción manual explícita."
            ),
            unsupported=False,
        )
        if not failed:
            raise CellClassificationError(
                409,
                "La explicación cambió de estado durante la recuperación.",
                "EXPLANATION_STATE_CONFLICT",
            )
        if prediction is not None:
            event = repository.add_event(
                classification_run_id=prediction["classification_run_id"],
                cell_detection_id=prediction["cell_detection_id"],
                cell_prediction_id=prediction["id"],
                event_type="cell_explanation.failed",
                status="failed",
                message_code="STALE_EXPLANATION_TERMINATED",
                metadata={"recovery_policy": "terminalize_only_no_automatic_retry"},
            )
            if not event:
                raise CellClassificationError(
                    500,
                    "No fue posible registrar la recuperación de la explicación.",
                    "EXPLANATION_RECOVERY_EVENT_FAILED",
                )
        return dict(failed)

    def eligible_detection_runs(
        self,
        *,
        detection_run_id: str | None = None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        resolved: ResolvedProductiveModel | None = None
        model_error: ProductiveModelError | None = None
        try:
            resolved = self.model_resolver.resolve()
        except ProductiveModelError as exc:
            model_error = exc
        with self.engine.connect() as connection:
            repository = self._repository(connection)
            result = repository.eligible_detection_runs(
                detection_run_id=detection_run_id,
                limit=limit,
                offset=offset,
            )
            enriched = []
            for item in result["items"]:
                full = repository.detection_run_input(item["id"])
                detection_error: CellClassificationError | None = None
                if full is None:
                    detection_error = CellClassificationError(
                        409,
                        "No fue posible congelar las detecciones candidatas.",
                        "DETECTION_INPUTS_UNAVAILABLE",
                    )
                else:
                    try:
                        self._eligible_detection_run(full)
                    except CellClassificationError as exc:
                        detection_error = exc
                checked = self._preflight_detections(
                    full["detections"] if full else []
                )
                inputs, manifest_sha256 = freeze_classification_inputs(checked)
                eligible_count = sum(input_row["eligible"] for input_row in inputs)
                excluded_count = len(inputs) - eligible_count
                exclusion_reasons = sorted(
                    {
                        str(input_row["exclusion_reason"])
                        for input_row in inputs
                        if input_row["exclusion_reason"]
                    }
                )
                equivalent = None
                if (
                    detection_error is None
                    and model_error is None
                    and resolved is not None
                    and eligible_count > 0
                ):
                    equivalent = repository.find_equivalent(
                        detection_run_id=UUID(str(item["id"])),
                        production_model_id=UUID(resolved.deployment_id),
                        model_version=resolved.model_version,
                        checkpoint_sha256=resolved.checkpoint_sha256,
                        inference_version=INFERENCE_VERSION,
                        input_manifest_sha256=manifest_sha256,
                    )
                if detection_error is not None:
                    eligible = False
                    reason = detection_error.code
                    message = detection_error.detail
                elif model_error is not None:
                    eligible = False
                    reason = model_error.code
                    message = model_error.detail
                elif eligible_count == 0:
                    eligible = False
                    reason = "NO_ELIGIBLE_CROPS"
                    message = (
                        "La ejecución no contiene crops íntegros y elegibles "
                        "para clasificación."
                    )
                elif equivalent is not None:
                    eligible = False
                    reason = "EQUIVALENT_CLASSIFICATION_EXISTS"
                    message = (
                        "Ya existe una clasificación activa o completada "
                        "para el mismo modelo e inputs."
                    )
                else:
                    eligible = True
                    reason = None
                    message = (
                        "Disponible para clasificación."
                        if excluded_count == 0
                        else "Disponible para clasificación con entradas excluidas."
                    )
                productive_model = (
                    {
                        "production_model_id": resolved.deployment_id,
                        "stage2_publication_id": resolved.publication_id,
                        "model_registry_id": resolved.model_version_id,
                        "model_name": resolved.model_name,
                        "model_version": resolved.model_version,
                        "checkpoint_sha256": resolved.checkpoint_sha256,
                        "threshold": resolved.threshold,
                        "threshold_source": resolved.threshold_source,
                        "input_width": resolved.input_width,
                        "input_height": resolved.input_height,
                        "input_channels": resolved.input_channels,
                        "preprocessing": resolved.preprocessing,
                        "environment": "stage2",
                        "alias": "default",
                        "production_scope": "stage2_experimental",
                    }
                    if resolved is not None
                    else None
                )
                enriched.append(
                    {
                        **item,
                        "detection_run_id": str(item["id"]),
                        "eligible": eligible,
                        "reason": reason,
                        "reason_code": reason,
                        "reasons": exclusion_reasons,
                        "message": message,
                        "input_count": len(inputs),
                        "eligible_count": eligible_count,
                        "excluded_count": excluded_count,
                        "productive_model": productive_model,
                    }
                )
            result["items"] = enriched
            return self._public_record(result)

    def _audit(
        self,
        *,
        connection: Any,
        event_type: str,
        action: str,
        principal: Principal,
        request: Request,
        success: bool,
        run_id: str,
        error_code: str | None = None,
        after_state: dict[str, Any] | None = None,
    ) -> None:
        self.auditor(
            event_type=event_type,
            action=action,
            principal=principal,
            request=request,
            success=success,
            error_code=error_code,
            connection=connection,
            resource_type="cell_classification_run",
            resource_id=run_id,
            after_state=after_state,
        )

    def _audit_rejected_request(
        self,
        *,
        detection_run_id: str,
        principal: Principal,
        request: Request,
        error_code: str,
    ) -> None:
        with self.engine.begin() as connection:
            self.auditor(
                event_type="scientific.cell_classification.rejected",
                action="execute",
                principal=principal,
                request=request,
                success=False,
                error_code=error_code,
                connection=connection,
                resource_type="cell_detection_run",
                resource_id=detection_run_id,
                after_state={
                    "detection_run_id": detection_run_id,
                    "automatic_retry": False,
                },
            )

    def _create_or_existing(
        self,
        detection_run_id: str,
        resolved: ResolvedProductiveModel,
        principal: Principal,
        request: Request,
    ) -> tuple[dict[str, Any], list[dict[str, Any]], bool]:
        settings = self._settings()
        with self.engine.begin() as connection:
            repository = self._repository(connection)
            revalidate = getattr(self.model_resolver, "revalidate", None)
            if revalidate is None:
                raise CellClassificationError(
                    500,
                    "El resolver productivo no admite revalidación transaccional.",
                    "PRODUCTIVE_REVALIDATION_UNAVAILABLE",
                )
            try:
                resolved = revalidate(resolved, connection=connection)
            except ProductiveModelError as exc:
                raise CellClassificationError(409, exc.detail, exc.code) from exc
            snapshot = resolved.snapshot(
                inference_version=INFERENCE_VERSION,
                review_margin=settings.cell_classification_review_margin,
                batch_size=settings.cell_classification_batch_size,
            )
            detection = repository.detection_run_input(
                detection_run_id, for_update=True
            )
            if not detection:
                raise CellClassificationError(
                    404, "Ejecución de detección inexistente.", "NOT_FOUND"
                )
            self._eligible_detection_run(detection)
            checked_detections = self._preflight_detections(
                detection["detections"]
            )
            inputs, manifest_sha256 = freeze_classification_inputs(
                checked_detections
            )
            eligible_count = sum(item["eligible"] for item in inputs)
            if eligible_count == 0:
                raise CellClassificationError(
                    409,
                    "La ejecución no contiene crops íntegros y elegibles "
                    "para clasificación.",
                    "NO_ELIGIBLE_CROPS",
                )
            existing = repository.find_equivalent(
                detection_run_id=UUID(str(detection["id"])),
                production_model_id=UUID(resolved.deployment_id),
                model_version=resolved.model_version,
                checkpoint_sha256=resolved.checkpoint_sha256,
                inference_version=INFERENCE_VERSION,
                input_manifest_sha256=manifest_sha256,
            )
            if existing:
                terminalized = self._terminalize_stale_run(repository, existing)
                if terminalized is not None:
                    self._audit(
                        connection=connection,
                        event_type="scientific.cell_classification.rejected",
                        action="reuse",
                        principal=principal,
                        request=request,
                        success=False,
                        error_code="STALE_ACTIVE_RUN_TERMINATED",
                        run_id=str(existing["id"]),
                        after_state={
                            "classification_run_id": str(existing["id"]),
                            "idempotency_outcome": "stale_terminalized",
                            "automatic_retry": False,
                        },
                    )
                    terminalized["_idempotency_outcome"] = "stale_terminalized"
                    return terminalized, inputs, True
                reuse_event = repository.add_event(
                    classification_run_id=existing["id"],
                    event_type="cell_classification.run.reused",
                    status=str(existing["status"]),
                    metadata={
                        "idempotency_outcome": "reused",
                        "automatic_retry": False,
                    },
                )
                if not reuse_event:
                    raise CellClassificationError(
                        500,
                        "No fue posible registrar la reutilización idempotente.",
                        "IDEMPOTENT_REUSE_EVENT_FAILED",
                    )
                self._audit(
                    connection=connection,
                    event_type="scientific.cell_classification.reused",
                    action="reuse",
                    principal=principal,
                    request=request,
                    success=True,
                    run_id=str(existing["id"]),
                    after_state={
                        "classification_run_id": str(existing["id"]),
                        "idempotency_outcome": "reused",
                        "automatic_retry": False,
                    },
                )
                result = dict(existing)
                result["_idempotency_outcome"] = "reused"
                return result, inputs, True
            find_failed = getattr(repository, "find_failed_equivalent", None)
            failed = (
                find_failed(
                    detection_run_id=UUID(str(detection["id"])),
                    production_model_id=UUID(resolved.deployment_id),
                    model_version=resolved.model_version,
                    checkpoint_sha256=resolved.checkpoint_sha256,
                    inference_version=INFERENCE_VERSION,
                    input_manifest_sha256=manifest_sha256,
                )
                if find_failed is not None
                else None
            )
            run_id = uuid4()
            run = repository.create_run(
                run_id=run_id,
                analysis_run_id=detection["analysis_run_id"],
                detection_run_id=detection["id"],
                classification_run_code=f"CLS-{secrets.token_hex(4).upper()}",
                production_model_id=UUID(resolved.deployment_id),
                stage2_publication_id=UUID(resolved.publication_id),
                model_registry_id=UUID(resolved.model_version_id),
                model_name=resolved.model_name,
                model_version=resolved.model_version,
                model_snapshot=snapshot,
                input_manifest_sha256=manifest_sha256,
                input_count=len(inputs),
                eligible_count=eligible_count,
                excluded_count=sum(not item["eligible"] for item in inputs),
                requested_by=UUID(str(principal.user_id)),
                retry_of_run_id=failed["id"] if failed else None,
            )
            for item in inputs:
                item["classification_run_id"] = run_id
                item["detection_run_id"] = UUID(str(detection["id"]))
            repository.insert_inputs(
                run_id,
                [self._public_input(item) for item in inputs],
            )
            repository.add_event(
                classification_run_id=run_id,
                event_type="cell_classification.run.created",
                status="created",
                progress_current=0,
                progress_total=eligible_count,
                metadata={
                    "production_model_id": resolved.deployment_id,
                    "model_version": resolved.model_version,
                    "checkpoint_sha256": resolved.checkpoint_sha256,
                    "input_manifest_sha256": manifest_sha256,
                },
            )
            self._audit(
                connection=connection,
                event_type="scientific.cell_classification.created",
                action="create",
                principal=principal,
                request=request,
                success=True,
                run_id=str(run_id),
                after_state={
                    "classification_run_id": str(run_id),
                    "detection_run_id": str(detection["id"]),
                    "production_model_id": resolved.deployment_id,
                    "model_version": resolved.model_version,
                    "checkpoint_sha256": resolved.checkpoint_sha256,
                    "threshold": resolved.threshold,
                    "input_manifest_sha256": manifest_sha256,
                    "input_count": len(inputs),
                },
            )
            result = dict(run)
            result["analysis_run_id"] = detection["analysis_run_id"]
            result["detection_run_id"] = detection["id"]
            return result, inputs, False

    def _start(
        self,
        run_id: UUID,
        *,
        eligible_count: int,
        principal: Principal,
        request: Request,
    ) -> None:
        with self.engine.begin() as connection:
            repository = self._repository(connection)
            started = repository.start_run(run_id)
            if not started:
                raise CellClassificationError(
                    409,
                    "La ejecución no admite la transición a processing.",
                    "RUN_START_STATE_CONFLICT",
                )
            event = repository.add_event(
                classification_run_id=run_id,
                event_type="cell_classification.run.started",
                status="processing",
                progress_current=0,
                progress_total=eligible_count,
            )
            if not event:
                raise CellClassificationError(
                    500,
                    "No fue posible registrar el inicio de la ejecución.",
                    "RUN_START_EVENT_FAILED",
                )
            self._audit(
                connection=connection,
                event_type="scientific.cell_classification.started",
                action="execute",
                principal=principal,
                request=request,
                success=True,
                run_id=str(run_id),
            )

    def _record_model_loaded(
        self, run_id: UUID, resolved: ResolvedProductiveModel
    ) -> None:
        with self.engine.begin() as connection:
            event = self._repository(connection).add_event(
                classification_run_id=run_id,
                event_type="cell_classification.model.loaded",
                status="completed",
                metadata={
                    "model_registry_id": resolved.model_version_id,
                    "checkpoint_sha256": resolved.checkpoint_sha256,
                    "loader_version": "productive-model-loader-v1",
                },
            )
            if not event:
                raise CellClassificationError(
                    500,
                    "No fue posible registrar la carga del modelo.",
                    "MODEL_LOAD_EVENT_FAILED",
                )

    @staticmethod
    def _model_shape(value: Any) -> tuple[Any, ...] | None:
        if value is None:
            return None
        if (
            isinstance(value, (list, tuple))
            and len(value) == 1
            and isinstance(value[0], (list, tuple))
        ):
            value = value[0]
        if hasattr(value, "as_list"):
            value = value.as_list()
        if not isinstance(value, (list, tuple)):
            return None
        return tuple(value)

    @classmethod
    def _validate_loaded_model_contract(
        cls,
        model: Any,
        resolved: ResolvedProductiveModel,
    ) -> None:
        """Validate exposed Keras shapes while allowing shape-less test doubles."""

        raw_input = getattr(model, "input_shape", None)
        raw_output = getattr(model, "output_shape", None)
        input_shape = cls._model_shape(raw_input)
        output_shape = cls._model_shape(raw_output)
        try:
            if input_shape is not None:
                if len(input_shape) < 4 or tuple(
                    int(value) for value in input_shape[-3:]
                ) != (
                    resolved.input_height,
                    resolved.input_width,
                    resolved.input_channels,
                ):
                    raise CellClassificationError(
                        409,
                        "La forma de entrada del modelo cargado no coincide "
                        "con el snapshot.",
                        "LOADED_MODEL_INPUT_SIGNATURE_MISMATCH",
                    )
            if output_shape is not None:
                declared_width = _output_width(resolved.output_signature)
                if (
                    not output_shape
                    or output_shape[-1] is None
                    or int(output_shape[-1]) != declared_width
                ):
                    raise CellClassificationError(
                        409,
                        "La forma de salida del modelo cargado no coincide "
                        "con el snapshot.",
                        "LOADED_MODEL_OUTPUT_SIGNATURE_MISMATCH",
                    )
        except CellClassificationError:
            raise
        except (TypeError, ValueError, OverflowError) as exc:
            raise CellClassificationError(
                409,
                "Las formas expuestas por el modelo cargado no son válidas.",
                "LOADED_MODEL_SIGNATURE_INVALID",
            ) from exc

    def _verified_crop_bytes(self, item: Mapping[str, Any]) -> bytes:
        """Read and verify one crop from the same no-follow file descriptor."""

        file_descriptor: int | None = None
        try:
            path = self._local().resolve(
                str(item["_crop_storage_key"]), must_exist=True
            )
            flags = os.O_RDONLY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            file_descriptor = os.open(path, flags)
            before = os.fstat(file_descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise StorageError("Crop no regular.")
            expected_size = item.get("crop_file_size_bytes")
            if expected_size is None or before.st_size != int(expected_size):
                raise StorageError("Tamaño de crop no coincide.")
            chunks: list[bytes] = []
            remaining = int(expected_size) + 1
            while remaining > 0:
                chunk = os.read(file_descriptor, min(1024 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            data = b"".join(chunks)
            after = os.fstat(file_descriptor)
            if (
                len(data) != int(expected_size)
                or before.st_dev != after.st_dev
                or before.st_ino != after.st_ino
                or before.st_size != after.st_size
                or before.st_mtime_ns != after.st_mtime_ns
            ):
                raise StorageError("El crop cambió durante la lectura.")
            if hashlib.sha256(data).hexdigest() != str(item["crop_sha256"]):
                raise StorageError("Checksum de crop no coincide.")
            try:
                with Image.open(io.BytesIO(data)) as image:
                    if image.size != (
                        int(item["crop_width_px"]),
                        int(item["crop_height_px"]),
                    ):
                        raise StorageError("Dimensiones de crop no coinciden.")
                    image.load()
            except (UnidentifiedImageError, OSError, SyntaxError) as exc:
                raise StorageError("Crop no decodificable.") from exc
            return data
        except (FileNotFoundError, OSError, StorageError) as exc:
            raise CellClassificationError(
                409,
                "Un crop no supera la verificación de integridad.",
                "CROP_INTEGRITY_ERROR",
            ) from exc
        finally:
            if file_descriptor is not None:
                os.close(file_descriptor)

    def _preprocess(
        self,
        item: Mapping[str, Any],
        resolved: ResolvedProductiveModel,
    ) -> Any:
        if self.preprocessor is not None:
            return self.preprocessor(item, resolved)
        import numpy as np
        import tensorflow as tf

        capstone_root = Path(__file__).resolve().parents[3]
        ml_root = capstone_root / "malaria_dl_local_project"
        if str(ml_root) not in sys.path:
            sys.path.insert(0, str(ml_root))
        from src.malaria_dl.data.preprocessing import apply_model_preprocessing

        crop_bytes = self._verified_crop_bytes(item)
        mode = resolved.preprocessing["mode"]
        with Image.open(io.BytesIO(crop_bytes)) as image:
            image = image.convert("L" if resolved.input_channels == 1 else "RGB")
            values = np.asarray(image, dtype=np.float32)
        if resolved.input_channels == 1:
            values = values[..., None]
        resized = tf.image.resize(
            values, (resolved.input_height, resolved.input_width), method="bilinear"
        )
        return apply_model_preprocessing(resized, mode).numpy().astype("float32")

    def _predict(self, model: Any, batch: Any) -> Any:
        if self.predictor is not None:
            return self.predictor(model, batch)
        return model.predict(batch, verbose=0)

    @staticmethod
    def _failed_prediction(
        *,
        run_id: UUID,
        item: Mapping[str, Any],
        resolved: ResolvedProductiveModel,
        code: str,
        message: str,
        duration_ms: float,
    ) -> dict[str, Any]:
        return {
            "id": uuid4(),
            "classification_run_id": run_id,
            "classification_input_id": item["id"],
            "cell_detection_id": item["cell_detection_id"],
            "crop_id": item["crop_id"],
            "prediction_status": "failed",
            "raw_output": {"status": "failed", "error_code": code},
            "probability_parasitized": None,
            "probability_uninfected": None,
            "predicted_label": None,
            "predicted_class_index": None,
            "positive_label": "parasitized",
            "positive_class_index": 1,
            "threshold_used": resolved.threshold,
            "threshold_source": resolved.threshold_source,
            "decision_margin": None,
            "near_threshold": False,
            "preprocessing_snapshot": resolved.preprocessing,
            "inference_duration_ms": max(0.0, duration_ms),
            "error_code": code,
            "error_message": message,
        }

    def _persist_batch(
        self,
        *,
        run_id: UUID,
        progress_before: int,
        progress_total: int,
        predictions: list[dict[str, Any]],
        cumulative_predictions: Sequence[Mapping[str, Any]],
    ) -> None:
        with self.engine.begin() as connection:
            repository = self._repository(connection)
            for prediction in predictions:
                persisted = repository.insert_prediction(prediction)
                if not persisted:
                    raise CellClassificationError(
                        500,
                        "No fue posible persistir una predicción.",
                        "PREDICTION_PERSISTENCE_FAILED",
                    )
                prediction_id = (
                    persisted["id"] if isinstance(persisted, Mapping) else prediction["id"]
                )
                event = repository.add_event(
                    classification_run_id=run_id,
                    cell_detection_id=prediction["cell_detection_id"],
                    cell_prediction_id=prediction_id,
                    event_type=(
                        "cell_classification.prediction.completed"
                        if prediction["prediction_status"] == "completed"
                        else "cell_classification.prediction.failed"
                    ),
                    status=prediction["prediction_status"],
                    message_code=prediction.get("error_code"),
                    progress_current=progress_before + 1,
                    progress_total=progress_total,
                )
                if not event:
                    raise CellClassificationError(
                        500,
                        "No fue posible registrar el evento de predicción.",
                        "PREDICTION_EVENT_FAILED",
                    )
                progress_before += 1
            updated = repository.update_counts(
                run_id,
                processed_count=len(cumulative_predictions),
                parasitized_count=sum(
                    item.get("predicted_label") == "parasitized"
                    for item in cumulative_predictions
                ),
                uninfected_count=sum(
                    item.get("predicted_label") == "uninfected"
                    for item in cumulative_predictions
                ),
                near_threshold_count=sum(
                    bool(item.get("near_threshold"))
                    for item in cumulative_predictions
                ),
                failed_count=sum(
                    item.get("prediction_status") == "failed"
                    for item in cumulative_predictions
                ),
            )
            if not updated:
                raise CellClassificationError(
                    409,
                    "La ejecución no admite la actualización de conteos.",
                    "RUN_COUNTS_STATE_CONFLICT",
                )

    def _record_batch_started(
        self,
        *,
        run_id: UUID,
        batch_number: int,
        batch_size: int,
        progress_before: int,
        progress_total: int,
    ) -> None:
        with self.engine.begin() as connection:
            event = self._repository(connection).add_event(
                classification_run_id=run_id,
                event_type="cell_classification.batch.started",
                status="processing",
                progress_current=progress_before,
                progress_total=progress_total,
                metadata={
                    "batch_number": batch_number,
                    "batch_size": batch_size,
                },
            )
            if not event:
                raise CellClassificationError(
                    500,
                    "No fue posible registrar el inicio del batch.",
                    "BATCH_EVENT_FAILED",
                )

    def _run_batches(
        self,
        *,
        run_id: UUID,
        model: Any,
        resolved: ResolvedProductiveModel,
        inputs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        eligible = [item for item in inputs if item["eligible"]]
        batch_size = self._settings().cell_classification_batch_size
        review_margin = self._settings().cell_classification_review_margin
        all_predictions: list[dict[str, Any]] = []
        for batch_number, source_batch in enumerate(
            iter_batches(eligible, batch_size), 1
        ):
            start = (batch_number - 1) * batch_size
            self._record_batch_started(
                run_id=run_id,
                batch_number=batch_number,
                batch_size=len(source_batch),
                progress_before=start,
                progress_total=len(eligible),
            )
            valid: list[tuple[dict[str, Any], Any, float]] = []
            terminal: list[dict[str, Any]] = []
            for item in source_batch:
                started = time.perf_counter()
                try:
                    prepared = self._preprocess(item, resolved)
                    valid.append((item, prepared, started))
                except Exception:
                    terminal.append(
                        self._failed_prediction(
                            run_id=run_id,
                            item=item,
                            resolved=resolved,
                            code="CROP_PREPROCESSING_FAILED",
                            message="El crop no pudo preprocesarse de forma segura.",
                            duration_ms=(time.perf_counter() - started) * 1000.0,
                        )
                    )
            if valid:
                inference_started = time.perf_counter()
                try:
                    prepared_values = [item[1] for item in valid]
                    try:
                        import numpy as np

                        values = np.stack(prepared_values, axis=0)
                    except ImportError:
                        # Keeps dependency-free synthetic unit tests possible.
                        # The operational ML runtime provides NumPy/TensorFlow.
                        values = prepared_values
                    raw = self._predict(model, values)
                    normalized = normalize_binary_outputs(
                        raw,
                        batch_size=len(valid),
                        label_mapping=resolved.label_mapping,
                        output_signature=resolved.output_signature,
                    )
                    inference_ms = (
                        (time.perf_counter() - inference_started)
                        * 1000.0
                        / len(valid)
                    )
                    for (item, _, prepared_started), output in zip(
                        valid, normalized, strict=True
                    ):
                        decision = classification_decision(
                            output["probability_parasitized"],
                            threshold=resolved.threshold,
                            review_margin=review_margin,
                        )
                        terminal.append(
                            {
                                "id": uuid4(),
                                "classification_run_id": run_id,
                                "classification_input_id": item["id"],
                                "cell_detection_id": item["cell_detection_id"],
                                "crop_id": item["crop_id"],
                                "prediction_status": "completed",
                                **output,
                                **decision,
                                "positive_label": "parasitized",
                                "positive_class_index": 1,
                                "threshold_used": resolved.threshold,
                                "threshold_source": resolved.threshold_source,
                                "preprocessing_snapshot": resolved.preprocessing,
                                "inference_duration_ms": max(
                                    0.0,
                                    (time.perf_counter() - prepared_started) * 1000.0
                                    + inference_ms,
                                ),
                                "error_code": None,
                                "error_message": None,
                            }
                        )
                except Exception:
                    elapsed = (
                        (time.perf_counter() - inference_started)
                        * 1000.0
                        / len(valid)
                    )
                    terminal.extend(
                        self._failed_prediction(
                            run_id=run_id,
                            item=item,
                            resolved=resolved,
                            code="MODEL_INFERENCE_FAILED",
                            message="El batch no pudo clasificarse.",
                            duration_ms=elapsed,
                        )
                        for item, _, _ in valid
                    )
            terminal.sort(
                key=lambda prediction: next(
                    item["input_order"]
                    for item in source_batch
                    if item["id"] == prediction["classification_input_id"]
                )
            )
            self._persist_batch(
                run_id=run_id,
                progress_before=start,
                progress_total=len(eligible),
                predictions=terminal,
                cumulative_predictions=[*all_predictions, *terminal],
            )
            all_predictions.extend(terminal)
        return all_predictions

    def _finalize(
        self,
        *,
        run: Mapping[str, Any],
        inputs: list[dict[str, Any]],
        predictions: list[dict[str, Any]],
        principal: Principal,
        request: Request,
    ) -> str:
        completed = sum(
            item["prediction_status"] == "completed" for item in predictions
        )
        failed = sum(item["prediction_status"] == "failed" for item in predictions)
        parasitized = sum(
            item.get("predicted_label") == "parasitized" for item in predictions
        )
        uninfected = sum(
            item.get("predicted_label") == "uninfected" for item in predictions
        )
        near = sum(bool(item.get("near_threshold")) for item in predictions)
        eligible_count = sum(item["eligible"] for item in inputs)
        summary = build_automatic_summary(
            classification_run_id=run["id"],
            analysis_run_id=run["analysis_run_id"],
            detection_run_id=run["detection_run_id"],
            frozen_inputs=inputs,
            predictions=predictions,
        )
        if eligible_count > 0 and completed == 0:
            status = "failed"
            error_code = "ALL_CROPS_FAILED"
        elif failed:
            status = "completed_with_warnings"
            error_code = None
        else:
            status = "completed"
            error_code = None
        with self.engine.begin() as connection:
            repository = self._repository(connection)
            persisted_summary = repository.create_summary(summary)
            if not persisted_summary:
                raise CellClassificationError(
                    500,
                    "No fue posible persistir el resumen agregado.",
                    "SUMMARY_PERSISTENCE_FAILED",
                )
            summary_event = repository.add_event(
                classification_run_id=run["id"],
                event_type="cell_classification.summary.created",
                status="completed",
                progress_current=eligible_count,
                progress_total=eligible_count,
                metadata={"outcome": summary["outcome"]},
            )
            if not summary_event:
                raise CellClassificationError(
                    500,
                    "No fue posible registrar el resumen agregado.",
                    "SUMMARY_EVENT_FAILED",
                )
            counts = {
                "processed_count": len(predictions),
                "parasitized_count": parasitized,
                "uninfected_count": uninfected,
                "near_threshold_count": near,
                "failed_count": failed,
            }
            if status == "failed":
                updated = repository.update_counts(run["id"], **counts)
                if not updated:
                    raise CellClassificationError(
                        409,
                        "La ejecución no admite la actualización final de conteos.",
                        "RUN_COUNTS_STATE_CONFLICT",
                    )
                transitioned = repository.fail_run(
                    run["id"],
                    error_code=error_code,
                    error_message="No fue posible clasificar ningún crop elegible.",
                )
            else:
                transitioned = repository.complete_run(
                    run["id"], status=status, **counts
                )
            if not transitioned:
                raise CellClassificationError(
                    409,
                    "La ejecución no admite la transición terminal.",
                    "RUN_TERMINAL_STATE_CONFLICT",
                )
            terminal_event_type = (
                "cell_classification.run.failed"
                if status == "failed"
                else "cell_classification.run.completed"
            )
            terminal_event = repository.add_event(
                classification_run_id=run["id"],
                event_type=terminal_event_type,
                status=status,
                message_code=error_code,
                progress_current=eligible_count,
                progress_total=eligible_count,
                metadata={"outcome": summary["outcome"], **counts},
            )
            if not terminal_event:
                raise CellClassificationError(
                    500,
                    "No fue posible registrar el estado terminal.",
                    "RUN_TERMINAL_EVENT_FAILED",
                )
            if status == "completed_with_warnings":
                warning_event = repository.add_event(
                    classification_run_id=run["id"],
                    event_type="cell_classification.run.completed_with_warnings",
                    status=status,
                    progress_current=eligible_count,
                    progress_total=eligible_count,
                    metadata={"outcome": summary["outcome"], **counts},
                )
                if not warning_event:
                    raise CellClassificationError(
                        500,
                        "No fue posible registrar las advertencias terminales.",
                        "RUN_WARNING_EVENT_FAILED",
                    )
            self._audit(
                connection=connection,
                event_type=f"scientific.cell_classification.{status}",
                action="execute",
                principal=principal,
                request=request,
                success=status != "failed",
                error_code=error_code,
                run_id=str(run["id"]),
                after_state={
                    "classification_run_id": str(run["id"]),
                    "detection_run_id": str(run["detection_run_id"]),
                    "production_model_id": str(run["production_model_id"]),
                    "model_version": run.get("model_version"),
                    "checkpoint_sha256": run["model_snapshot"][
                        "checkpoint_sha256"
                    ],
                    "threshold": run["model_snapshot"]["threshold"],
                    "input_manifest_sha256": run["input_manifest_sha256"],
                    "outcome": summary["outcome"],
                    **counts,
                },
            )
        return status

    def _fail_run(
        self,
        run: Mapping[str, Any],
        principal: Principal,
        request: Request,
        *,
        code: str,
        detail: str,
    ) -> None:
        with self.engine.begin() as connection:
            repository = self._repository(connection)
            failed = repository.fail_run(
                run["id"],
                error_code=code,
                error_message=detail,
            )
            if not failed:
                raise CellClassificationError(
                    500,
                    "No fue posible terminalizar la ejecución fallida.",
                    "RUN_FAILURE_TRANSITION_FAILED",
                )
            event = repository.add_event(
                classification_run_id=run["id"],
                event_type="cell_classification.run.failed",
                status="failed",
                message_code=code,
            )
            if not event:
                raise CellClassificationError(
                    500,
                    "No fue posible registrar la ejecución fallida.",
                    "RUN_FAILURE_EVENT_FAILED",
                )
            self._audit(
                connection=connection,
                event_type="scientific.cell_classification.failed",
                action="execute",
                principal=principal,
                request=request,
                success=False,
                error_code=code,
                run_id=str(run["id"]),
            )

    def execute_classification(
        self,
        detection_run_id: str,
        principal: Principal,
        request: Request,
    ) -> dict[str, Any]:
        try:
            resolved = self.model_resolver.resolve()
        except ProductiveModelError as exc:
            self._audit_rejected_request(
                detection_run_id=detection_run_id,
                principal=principal,
                request=request,
                error_code=exc.code,
            )
            raise CellClassificationError(409, exc.detail, exc.code) from exc
        try:
            run, inputs, idempotent = self._create_or_existing(
                detection_run_id, resolved, principal, request
            )
        except CellClassificationError as exc:
            self._audit_rejected_request(
                detection_run_id=detection_run_id,
                principal=principal,
                request=request,
                error_code=exc.code,
            )
            raise
        if idempotent:
            if run.get("_idempotency_outcome") == "stale_terminalized":
                raise CellClassificationError(
                    409,
                    "La ejecución activa vencida fue terminalizada. "
                    "Confirme una nueva acción para reintentar.",
                    "STALE_ACTIVE_RUN_TERMINATED",
                )
            result = self.get_run(str(run["id"]))
            result["idempotent"] = True
            return self._public_record(result)
        run_id = UUID(str(run["id"]))
        eligible_count = sum(item["eligible"] for item in inputs)
        stage = "run_start"
        try:
            self._start(
                run_id,
                eligible_count=eligible_count,
                principal=principal,
                request=request,
            )
            stage = "model_loading"
            model = self.model_resolver.load(resolved)
            stage = "model_contract_validation"
            self._validate_loaded_model_contract(model, resolved)
            self._record_model_loaded(run_id, resolved)
            stage = "inference"
            predictions = self._run_batches(
                run_id=run_id,
                model=model,
                resolved=resolved,
                inputs=inputs,
            )
            stage = "summary_persistence"
            status = self._finalize(
                run=run,
                inputs=inputs,
                predictions=predictions,
                principal=principal,
                request=request,
            )
        except Exception as exc:
            logger.exception(
                "Cell classification execution failed",
                extra={
                    "classification_run_id": str(run_id),
                    "detection_run_id": detection_run_id,
                    "stage": stage,
                },
            )
            if isinstance(exc, CellClassificationError):
                code, detail = exc.code, exc.detail
            else:
                code, detail = (
                    "CELL_CLASSIFICATION_EXECUTION_FAILED",
                    "La clasificación celular no pudo completarse.",
                )
            self._fail_run(run, principal, request, code=code, detail=detail)
            raise CellClassificationError(
                500,
                detail,
                code,
                classification_run_id=str(run_id),
                stage=stage,
                retryable=True,
            ) from exc
        result = self.get_run(str(run_id))
        result["idempotent"] = False
        if status == "failed":
            result["warning"] = "No fue posible clasificar ningún crop elegible."
        return self._public_record(result)

    def list_runs(
        self,
        *,
        status: str | None,
        analysis_run_id: str | None,
        detection_run_id: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        with self.engine.connect() as connection:
            result = self._repository(connection).list_runs(
                status=status,
                analysis_run_id=analysis_run_id,
                detection_run_id=detection_run_id,
                limit=limit,
                offset=offset,
            )
        return self._public_record(result)

    def get_run(self, classification_run_id: str) -> dict[str, Any]:
        with self.engine.connect() as connection:
            repository = self._repository(connection)
            run = repository.get_run(classification_run_id)
            if run:
                events = repository.events(classification_run_id)
        if not run:
            raise CellClassificationError(
                404, "Ejecución de clasificación inexistente.", "NOT_FOUND"
            )
        result = dict(run)
        result["events"] = events or []
        return self._public_record(result)

    def list_predictions(
        self,
        classification_run_id: str,
        *,
        microscopy_image_id: str | None = None,
        predicted_label: str | None = None,
        near_threshold: bool | None = None,
        prediction_status: str | None = None,
        review_status: str | None = None,
        cell_code: str | None = None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        with self.engine.connect() as connection:
            result = self._repository(connection).list_predictions(
                classification_run_id=classification_run_id,
                microscopy_image_id=microscopy_image_id,
                predicted_label=predicted_label,
                near_threshold=near_threshold,
                prediction_status=prediction_status,
                review_status=review_status,
                cell_code=cell_code,
                limit=limit,
                offset=offset,
            )
        if result is None:
            raise CellClassificationError(
                404, "Ejecución de clasificación inexistente.", "NOT_FOUND"
            )
        result["items"] = [
            {
                **self._public_record(item),
                "detection_review_status": item.get(
                    "detection_review_status_at_creation"
                ),
            }
            for item in result.get("items", [])
        ]
        return result

    def get_summary(self, classification_run_id: str) -> dict[str, Any]:
        with self.engine.connect() as connection:
            repository = self._repository(connection)
            summary = repository.get_summary(classification_run_id)
            review_rows = (
                repository.latest_reviews_for_summary(classification_run_id)
                if summary
                else []
            )
        if not summary:
            raise CellClassificationError(404, "Resumen inexistente.", "NOT_FOUND")
        return {
            "automatic_summary": self._public_record(dict(summary)),
            "reviewed_summary": self._public_record(
                build_revised_summary(summary, review_rows)
            ),
        }

    def get_prediction(self, prediction_id: str) -> dict[str, Any]:
        with self.engine.connect() as connection:
            prediction = self._repository(connection).get_prediction(prediction_id)
        if not prediction:
            raise CellClassificationError(404, "Predicción inexistente.", "NOT_FOUND")
        return {
            **self._public_record(dict(prediction)),
            "detection_review_status": prediction.get(
                "detection_review_status_at_creation"
            ),
        }

    def _gradcam_callable(self) -> Callable[..., Any]:
        if self.gradcam is not None:
            return self.gradcam
        capstone_root = Path(__file__).resolve().parents[3]
        ml_root = capstone_root / "malaria_dl_local_project"
        if str(ml_root) not in sys.path:
            sys.path.insert(0, str(ml_root))
        from src.malaria_dl.explainability.gradcam import (
            GradCAMUnsupportedError as MLGradCAMUnsupportedError,
        )
        from src.malaria_dl.explainability.gradcam import compute_gradcam_artifacts

        def invoke(**kwargs: Any) -> Any:
            try:
                return compute_gradcam_artifacts(**kwargs)
            except MLGradCAMUnsupportedError as exc:
                raise GradCAMUnsupportedError(str(exc)) from exc

        return invoke

    def _resolved_for_prediction(
        self, prediction: Mapping[str, Any]
    ) -> ResolvedProductiveModel:
        snapshot = dict(prediction["model_snapshot"])
        exact = getattr(self.model_resolver, "resolve_snapshot", None)
        if exact is None:
            raise CellClassificationError(
                409,
                "El resolver no admite la identidad histórica congelada.",
                "FROZEN_MODEL_RESOLVER_UNAVAILABLE",
            )
        resolved = exact(snapshot)
        expected = (
            str(snapshot["model_registry_id"]),
            str(snapshot["checkpoint_artifact_id"]),
            str(snapshot["checkpoint_sha256"]),
        )
        actual = (
            resolved.model_version_id,
            resolved.checkpoint_artifact_id,
            resolved.checkpoint_sha256,
        )
        if expected != actual:
            raise CellClassificationError(
                409,
                "El modelo congelado de la predicción ya no está disponible.",
                "FROZEN_MODEL_UNAVAILABLE",
            )
        return resolved

    def generate_explanation(
        self,
        prediction_id: str,
        retry: bool,
        principal: Principal,
        request: Request,
    ) -> dict[str, Any]:
        storage: CellExplanationStorage | None = None
        staged: StagedCellExplanation | None = None
        promoted: list[Path] = []
        with self.engine.begin() as connection:
            repository = self._repository(connection)
            prediction = repository.prediction_for_explanation(
                prediction_id, for_update=True
            )
            if not prediction:
                raise CellClassificationError(
                    404, "Predicción inexistente.", "NOT_FOUND"
                )
            if prediction["prediction_status"] != "completed":
                raise CellClassificationError(
                    409,
                    "Sólo una predicción completada admite explicación.",
                    "PREDICTION_NOT_EXPLAINABLE",
                )
            existing = repository.find_explanation(prediction_id)
            if existing and existing["status"] == "pending":
                terminalized = self._terminalize_stale_explanation(
                    repository,
                    existing,
                    prediction=prediction,
                )
                if terminalized is not None:
                    self.auditor(
                        event_type="scientific.cell_explanation.failed",
                        action="recover",
                        principal=principal,
                        request=request,
                        success=False,
                        error_code="STALE_EXPLANATION_TERMINATED",
                        connection=connection,
                        resource_type="cell_prediction",
                        resource_id=prediction_id,
                        after_state={
                            "classification_run_id": str(
                                prediction["classification_run_id"]
                            ),
                            "prediction_id": prediction_id,
                            "explanation_id": str(existing["id"]),
                            "automatic_retry": False,
                            "manual_retry_required": True,
                        },
                    )
                    return self._public_explanation(terminalized)
                self.auditor(
                    event_type="scientific.cell_explanation.reused",
                    action="reuse",
                    principal=principal,
                    request=request,
                    success=True,
                    connection=connection,
                    resource_type="cell_prediction",
                    resource_id=prediction_id,
                    after_state={
                        "explanation_id": str(existing["id"]),
                        "status": "pending",
                    },
                )
                return self._public_explanation(existing)
            if existing and existing["status"] in {"generated", "unsupported"}:
                self.auditor(
                    event_type="scientific.cell_explanation.reused",
                    action="reuse",
                    principal=principal,
                    request=request,
                    success=True,
                    connection=connection,
                    resource_type="cell_prediction",
                    resource_id=prediction_id,
                    after_state={
                        "explanation_id": str(existing["id"]),
                        "status": str(existing["status"]),
                    },
                )
                return self._public_explanation(existing)
            if existing and existing["status"] == "failed" and not retry:
                self.auditor(
                    event_type="scientific.cell_explanation.retry_rejected",
                    action="retry",
                    principal=principal,
                    request=request,
                    success=False,
                    error_code="EXPLICIT_RETRY_REQUIRED",
                    connection=connection,
                    resource_type="cell_prediction",
                    resource_id=prediction_id,
                    after_state={
                        "explanation_id": str(existing["id"]),
                        "automatic_retry": False,
                        "manual_retry_required": True,
                    },
                )
                return self._public_explanation(existing)
            explanation_id = (
                UUID(str(existing["id"])) if existing else uuid4()
            )
            parameters = {
                "method": "gradcam",
                "method_version": GRADCAM_METHOD_VERSION,
                "target_class_index": int(prediction["predicted_class_index"]),
                "positive_class_index": 1,
                "preprocessing": prediction["preprocessing_snapshot"],
            }
            if existing is None:
                repository.create_explanation(
                    explanation_id=explanation_id,
                    cell_prediction_id=UUID(str(prediction_id)),
                    method_version=GRADCAM_METHOD_VERSION,
                    parameters=parameters,
                    status="not_requested",
                )
            explanation = repository.start_explanation(
                explanation_id, retry=bool(existing)
            )
            if not explanation:
                raise CellClassificationError(
                    409,
                    "La explicación no admite esta transición.",
                    "EXPLANATION_STATE_CONFLICT",
                )
        try:
            resolved = self._resolved_for_prediction(prediction)
            model = self.model_resolver.load(resolved)
            self._validate_loaded_model_contract(model, resolved)
            item = {
                **prediction,
                "_crop_storage_key": prediction["crop_storage_key"],
                "crop_sha256": prediction["crop_sha256"],
                "crop_file_size_bytes": prediction.get("crop_file_size_bytes"),
                "crop_width_px": prediction["crop_width_px"],
                "crop_height_px": prediction["crop_height_px"],
            }
            model_image = self._preprocess(item, resolved)
            heatmap, overlay, last_conv_layer = self._gradcam_callable()(
                model=model,
                image=model_image,
                pred_idx=int(prediction["predicted_class_index"]),
                invert_scalar_output=(
                    int(prediction["predicted_class_index"]) == 0
                ),
                preprocessing_mode=resolved.preprocessing["mode"],
            )
            storage = self._explanations()
            heatmap_png = storage.encode_heatmap_png(heatmap)
            overlay_png = storage.encode_overlay_png(overlay)
            staged = storage.stage(
                analysis_run_id=UUID(str(prediction["analysis_run_id"])),
                classification_run_id=UUID(
                    str(prediction["classification_run_id"])
                ),
                cell_detection_id=UUID(str(prediction["cell_detection_id"])),
                explanation_id=explanation_id,
                heatmap_png=heatmap_png,
                overlay_png=overlay_png,
                expected_width_px=resolved.input_width,
                expected_height_px=resolved.input_height,
            )
            heatmap_path, overlay_path = storage.promote(staged)
            promoted.extend((heatmap_path, overlay_path))
            with self.engine.begin() as connection:
                repository = self._repository(connection)
                result = repository.complete_explanation(
                    explanation_id,
                    last_conv_layer=last_conv_layer,
                    heatmap_storage_key=staged.heatmap.relative_storage_key,
                    heatmap_sha256=staged.heatmap.sha256,
                    heatmap_file_size_bytes=staged.heatmap.file_size_bytes,
                    overlay_storage_key=staged.overlay.relative_storage_key,
                    overlay_sha256=staged.overlay.sha256,
                    overlay_file_size_bytes=staged.overlay.file_size_bytes,
                    width_px=resolved.input_width,
                    height_px=resolved.input_height,
                )
                if not result:
                    raise CellClassificationError(
                        409,
                        "La explicación no admite la transición a generated.",
                        "EXPLANATION_COMPLETE_STATE_CONFLICT",
                    )
                event = repository.add_event(
                    classification_run_id=prediction["classification_run_id"],
                    cell_detection_id=prediction["cell_detection_id"],
                    cell_prediction_id=prediction_id,
                    event_type="cell_explanation.generated",
                    status="generated",
                    metadata={
                        "method": "gradcam",
                        "method_version": GRADCAM_METHOD_VERSION,
                        "last_conv_layer": last_conv_layer,
                        "heatmap_sha256": staged.heatmap.sha256,
                        "overlay_sha256": staged.overlay.sha256,
                    },
                )
                if not event:
                    raise CellClassificationError(
                        500,
                        "No fue posible registrar la explicación generada.",
                        "EXPLANATION_EVENT_FAILED",
                    )
                self.auditor(
                    event_type="scientific.cell_explanation.generated",
                    action="explain",
                    principal=principal,
                    request=request,
                    success=True,
                    connection=connection,
                    resource_type="cell_prediction",
                    resource_id=prediction_id,
                    after_state={
                        "classification_run_id": str(
                            prediction["classification_run_id"]
                        ),
                        "prediction_id": prediction_id,
                        "explanation_id": str(explanation_id),
                        "method": "gradcam",
                        "outcome": "generated",
                    },
                )
            return self._public_explanation(result)
        except Exception as exc:
            if storage is not None:
                cleanup = promoted[:]
                if staged is not None:
                    cleanup.extend((staged.heatmap.path, staged.overlay.path))
                storage.cleanup(cleanup)
            unsupported = isinstance(exc, GradCAMUnsupportedError)
            status = "unsupported" if unsupported else "failed"
            code = (
                "GRADCAM_UNSUPPORTED" if unsupported else "GRADCAM_GENERATION_FAILED"
            )
            message = (
                "El modelo productivo no admite Grad-CAM con la configuración registrada."
                if unsupported
                else "No fue posible generar la explicación Grad-CAM."
            )
            with self.engine.begin() as connection:
                repository = self._repository(connection)
                result = repository.fail_explanation(
                    explanation_id,
                    error_code=code,
                    error_message=message,
                    unsupported=unsupported,
                )
                if not result:
                    raise CellClassificationError(
                        500,
                        "No fue posible terminalizar la explicación fallida.",
                        "EXPLANATION_FAILURE_TRANSITION_FAILED",
                    ) from exc
                event = repository.add_event(
                    classification_run_id=prediction["classification_run_id"],
                    cell_detection_id=prediction["cell_detection_id"],
                    cell_prediction_id=prediction_id,
                    event_type="cell_explanation.failed",
                    status=status,
                    message_code=code,
                )
                if not event:
                    raise CellClassificationError(
                        500,
                        "No fue posible registrar la explicación fallida.",
                        "EXPLANATION_FAILURE_EVENT_FAILED",
                    ) from exc
                self.auditor(
                    event_type="scientific.cell_explanation.failed",
                    action="explain",
                    principal=principal,
                    request=request,
                    success=False,
                    error_code=code,
                    connection=connection,
                    resource_type="cell_prediction",
                    resource_id=prediction_id,
                    after_state={
                        "classification_run_id": str(
                            prediction["classification_run_id"]
                        ),
                        "prediction_id": prediction_id,
                        "explanation_id": str(explanation_id),
                        "outcome": status,
                    },
                )
            return self._public_explanation(result)

    def get_prediction_explanation(self, prediction_id: str) -> dict[str, Any]:
        with self.engine.connect() as connection:
            result = self._repository(connection).find_explanation(prediction_id)
        if not result:
            raise CellClassificationError(
                404, "Explicación inexistente.", "NOT_FOUND"
            )
        return self._public_explanation(result)

    def explanation_content(
        self, explanation_id: str, kind: str
    ) -> tuple[dict[str, Any], bytes]:
        if kind not in {"heatmap", "overlay"}:
            raise CellClassificationError(
                422, "Tipo de explicación inválido.", "INVALID_CONTENT_KIND"
            )
        with self.engine.connect() as connection:
            explanation = self._repository(connection).get_explanation(
                explanation_id
            )
        if not explanation or explanation["status"] != "generated":
            raise CellClassificationError(
                404, "Artefacto de explicación inexistente.", "NOT_FOUND"
            )
        key = explanation[f"{kind}_storage_key"]
        expected_sha = explanation[f"{kind}_sha256"]
        expected_size = explanation[f"{kind}_file_size_bytes"]
        file_descriptor: int | None = None
        try:
            path = self._explanations().resolve(key, must_exist=True)
            flags = os.O_RDONLY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            file_descriptor = os.open(path, flags)
            before = os.fstat(file_descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_size != int(expected_size)
            ):
                raise StorageError("Integridad inválida.")
            chunks: list[bytes] = []
            remaining = int(expected_size) + 1
            while remaining > 0:
                chunk = os.read(file_descriptor, min(1024 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            content = b"".join(chunks)
            after = os.fstat(file_descriptor)
            if (
                len(content) != int(expected_size)
                or before.st_dev != after.st_dev
                or before.st_ino != after.st_ino
                or before.st_size != after.st_size
                or before.st_mtime_ns != after.st_mtime_ns
                or hashlib.sha256(content).hexdigest() != str(expected_sha)
            ):
                raise StorageError("Integridad inválida.")
        except (FileNotFoundError, OSError, StorageError) as exc:
            raise CellClassificationError(
                404, "Artefacto de explicación no disponible.", "CONTENT_UNAVAILABLE"
            ) from exc
        finally:
            if file_descriptor is not None:
                os.close(file_descriptor)
        return self._public_record(dict(explanation)), content

    @staticmethod
    def _validate_review(
        decision: str,
        reviewed_label: str | None,
        comment: str | None,
    ) -> tuple[str | None, str | None]:
        clean = comment.strip() if comment else None
        if reviewed_label not in {None, "parasitized", "uninfected"}:
            raise CellClassificationError(
                422, "reviewed_label no es canónico.", "INVALID_REVIEW_LABEL"
            )
        if decision == "corrected":
            if reviewed_label is None or clean is None:
                raise CellClassificationError(
                    422,
                    "corrected requiere reviewed_label y comentario.",
                    "REVIEW_PAYLOAD_INVALID",
                )
        elif decision in {"needs_attention", "comment_only"}:
            if reviewed_label is not None or clean is None:
                raise CellClassificationError(
                    422,
                    f"{decision} requiere comentario y no admite reviewed_label.",
                    "REVIEW_PAYLOAD_INVALID",
                )
        elif decision == "confirmed":
            pass
        else:
            raise CellClassificationError(
                422, "Decisión de revisión inválida.", "INVALID_REVIEW_DECISION"
            )
        return reviewed_label, clean

    def create_review(
        self,
        prediction_id: str,
        decision: str,
        reviewed_label: str | None,
        comment: str | None,
        principal: Principal,
        request: Request,
    ) -> dict[str, Any]:
        reviewed_label, clean = self._validate_review(
            decision, reviewed_label, comment
        )
        with self.engine.begin() as connection:
            repository = self._repository(connection)
            prediction = repository.prediction_for_review(prediction_id)
            if not prediction:
                raise CellClassificationError(
                    404, "Predicción inexistente.", "NOT_FOUND"
                )
            if prediction.get("prediction_status") != "completed":
                raise CellClassificationError(
                    409,
                    "Sólo una predicción completada admite revisión.",
                    "PREDICTION_NOT_REVIEWABLE",
                )
            if (
                decision == "confirmed"
                and reviewed_label is not None
                and reviewed_label != prediction.get("predicted_label")
            ):
                raise CellClassificationError(
                    422,
                    "confirmed no puede cambiar la etiqueta automática; "
                    "use corrected con comentario.",
                    "CONFIRMED_LABEL_MISMATCH",
                )
            review = repository.create_review(
                cell_prediction_id=UUID(prediction_id),
                decision=decision,
                reviewed_label=reviewed_label,
                comment=clean,
                actor_user_id=UUID(str(principal.user_id)),
            )
            if not review:
                raise CellClassificationError(
                    409,
                    "La predicción cambió durante la revisión.",
                    "REVIEW_STATE_CONFLICT",
                )
            repository.add_event(
                classification_run_id=review["classification_run_id"],
                cell_detection_id=review["cell_detection_id"],
                cell_prediction_id=prediction_id,
                event_type="cell_classification.review.created",
                status="completed",
                metadata={
                    "decision": decision,
                    "reviewed_label": reviewed_label,
                    "comment_present": clean is not None,
                    "comment_length": len(clean) if clean else 0,
                },
            )
            self.auditor(
                event_type="scientific.cell_classification.reviewed",
                action="review",
                principal=principal,
                request=request,
                success=True,
                connection=connection,
                resource_type="cell_prediction",
                resource_id=prediction_id,
                after_state={
                    "classification_run_id": str(
                        review["classification_run_id"]
                    ),
                    "prediction_id": prediction_id,
                    "review_decision": decision,
                    "reviewed_label": reviewed_label,
                    "comment_present": clean is not None,
                    "comment_length": len(clean) if clean else 0,
                },
            )
        return self._public_record(dict(review))

    def reviews(
        self, prediction_id: str, *, limit: int, offset: int
    ) -> dict[str, Any]:
        with self.engine.connect() as connection:
            result = self._repository(connection).reviews(
                prediction_id, limit=limit, offset=offset
            )
        if result is None:
            raise CellClassificationError(
                404, "Predicción inexistente.", "NOT_FOUND"
            )
        return self._public_record(result)
