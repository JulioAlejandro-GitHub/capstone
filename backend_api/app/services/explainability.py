import json
from collections.abc import Mapping
from numbers import Number
from urllib.parse import quote


LOW_CONFIDENCE_DISTANCE = 0.10

_METADATA_COLUMNS = (
    "prediction_metadata",
    "explainability_metadata",
    "explanation_parameters",
    "artifact_metadata",
    "source_usage_metadata",
    "source_dataset_metadata",
    "run_parameters",
    "run_metadata",
    "metadata",
)


def _is_present(value) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _as_mapping(value) -> Mapping:
    if isinstance(value, Mapping):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, Mapping) else {}
    return {}


def _metadata_records(item: Mapping):
    for column in _METADATA_COLUMNS:
        metadata = _as_mapping(item.get(column))
        if metadata:
            yield metadata


def _pick(item: Mapping, *keys, include_metadata: bool = True):
    for key in keys:
        value = item.get(key)
        if _is_present(value):
            return value

    if include_metadata:
        for metadata in _metadata_records(item):
            for key in keys:
                value = metadata.get(key)
                if _is_present(value):
                    return value
    return None


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Number):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _path(value):
    return str(value) if _is_present(value) else None


def artifact_file_url(path) -> str | None:
    normalized = _path(path)
    if normalized is None:
        return None
    return f"/artifacts/file?path={quote(normalized, safe='/')}"


def _infer_case_type(true_label, predicted_label, positive_label):
    if not all(_is_present(value) for value in (true_label, predicted_label, positive_label)):
        return None
    if true_label == positive_label and predicted_label == positive_label:
        return "true_positive"
    if true_label != positive_label and predicted_label != positive_label:
        return "true_negative"
    if true_label != positive_label and predicted_label == positive_label:
        return "false_positive"
    if true_label == positive_label and predicted_label != positive_label:
        return "false_negative"
    return None


def generate_case_interpretation(case_type: str | None) -> str | None:
    interpretations = {
        "false_positive": (
            "La imagen estaba etiquetada como no parasitada, pero el modelo la clasificó "
            "como parasitada. Este caso debe revisarse como posible confusión visual, "
            "artefacto o umbral demasiado sensible."
        ),
        "false_negative": (
            "La imagen estaba etiquetada como parasitada, pero el modelo la clasificó "
            "como no parasitada. Este caso es crítico porque representa una célula "
            "parasitada no detectada por el modelo."
        ),
        "true_positive": (
            "La imagen estaba etiquetada como parasitada y el modelo también la clasificó "
            "como parasitada. La explicación visual permite revisar si la decisión se "
            "apoya en una región microscópica plausible."
        ),
        "true_negative": (
            "La imagen estaba etiquetada como no parasitada y el modelo también la "
            "clasificó como no parasitada."
        ),
        "low_confidence": (
            "La predicción está cercana al umbral de decisión. Este caso debe "
            "priorizarse para revisión humana."
        ),
    }
    return interpretations.get(case_type)


def _bbox_value(item: Mapping, field: str):
    value = _pick(item, field)
    if _is_present(value):
        return value

    aliases = {
        "bbox_x": ("x", "left"),
        "bbox_y": ("y", "top"),
        "bbox_width": ("width", "w"),
        "bbox_height": ("height", "h"),
    }
    for metadata in _metadata_records(item):
        bbox = _as_mapping(metadata.get("bbox"))
        for alias in aliases[field]:
            value = bbox.get(alias)
            if _is_present(value):
                return value
    return None


def enrich_explainability_case(item: Mapping) -> dict:
    enriched = dict(item)

    positive_label = _pick(item, "positive_label") or "parasitized"
    true_label = _pick(item, "true_label")
    predicted_label = _pick(item, "predicted_label")
    case_type = _pick(item, "case_type") or _infer_case_type(
        true_label,
        predicted_label,
        positive_label,
    )

    probability_parasitized = _number(
        _pick(item, "probability_parasitized", "score_positive_label", "score")
    )
    probability_uninfected = _number(_pick(item, "probability_uninfected"))
    if probability_uninfected is None and probability_parasitized is not None:
        if 0.0 <= probability_parasitized <= 1.0:
            probability_uninfected = round(1.0 - probability_parasitized, 12)

    score_positive_label = _number(
        _pick(item, "score_positive_label", "probability_parasitized", "score")
    )
    threshold = _number(_pick(item, "threshold", "threshold_used"))
    confidence_distance = _number(_pick(item, "confidence_distance"))
    if confidence_distance is None and score_positive_label is not None and threshold is not None:
        confidence_distance = abs(score_positive_label - threshold)

    confidence_status = _pick(item, "confidence_status", "confidence_level")
    if confidence_status is None and confidence_distance is not None:
        confidence_status = (
            "low_confidence"
            if confidence_distance <= LOW_CONFIDENCE_DISTANCE
            else "confident"
        )

    image_path = _path(_pick(item, "image_path"))
    image_stored_path = _path(_pick(item, "image_stored_path", "stored_image_path"))
    declared_source_image_path = _path(_pick(item, "source_image_path"))
    original_image_path = _path(_pick(item, "original_image_path"))
    source_image_path = _path(
        declared_source_image_path
        or image_stored_path
        or image_path
        or original_image_path
    )
    crop_path = _path(_pick(item, "crop_path"))

    explanation_output_path = _path(
        _pick(item, "explanation_output_path", "output_path", "explainability_path")
    )
    if explanation_output_path is None:
        artifact_type = str(_pick(item, "artifact_type") or "").lower()
        if any(token in artifact_type for token in ("explain", "gradcam", "lime", "shap")):
            explanation_output_path = _path(_pick(item, "artifact_path"))

    started_at = _pick(item, "started_at", "created_at")

    contract = {
        "explainability_id": _pick(item, "explainability_id", "gallery_id", "id"),
        "run_id": _pick(item, "run_id"),
        "model_name": _pick(item, "model_name"),
        "dataset_name": _pick(item, "dataset_name"),
        "method": _pick(item, "method", "explainability_method"),
        "case_type": case_type,
        "true_label": true_label,
        "predicted_label": predicted_label,
        "positive_label": positive_label,
        "score_positive_label": score_positive_label,
        "probability_parasitized": probability_parasitized,
        "probability_uninfected": probability_uninfected,
        "threshold": threshold,
        "threshold_used": _number(_pick(item, "threshold_used", "threshold")),
        "threshold_source": _pick(item, "threshold_source"),
        "confidence_distance": confidence_distance,
        "confidence_status": confidence_status,
        "image_path": image_path,
        "image_url": artifact_file_url(image_path),
        "explanation_output_path": explanation_output_path,
        "explanation_url": artifact_file_url(explanation_output_path),
        "source_image_path": source_image_path,
        "source_image_url": artifact_file_url(source_image_path),
        "crop_path": crop_path,
        "crop_url": artifact_file_url(crop_path),
        "last_conv_layer": _pick(item, "last_conv_layer"),
        "success": _pick(item, "success"),
        "error_message": _pick(item, "error_message"),
        "started_at": started_at,
        "interpretation": (
            _pick(item, "interpretation", include_metadata=False)
            or generate_case_interpretation(case_type)
        ),
        "explanation_parameters": _pick(item, "explanation_parameters"),
        # Existing and future source-traceability fields. They are intentionally
        # always present so older rows remain safe for the visual audit client.
        "dataset_split": _pick(item, "dataset_split", "split"),
        "dataset_index": _pick(item, "dataset_index"),
        "manifest_id": _pick(item, "manifest_id"),
        "original_tfds_label": _pick(item, "original_tfds_label"),
        "remapped_label": _pick(item, "remapped_label"),
        "original_image_path": original_image_path,
        "image_stored_path": image_stored_path,
        "original_filename": _pick(item, "original_filename"),
        "uploaded_at": _pick(item, "uploaded_at"),
        "prediction_upload_id": _pick(item, "prediction_upload_id"),
        "source_image_id": _pick(item, "source_image_id"),
        "patient_id": _pick(item, "patient_id"),
        "slide_id": _pick(item, "slide_id"),
        "bbox_x": _bbox_value(item, "bbox_x"),
        "bbox_y": _bbox_value(item, "bbox_y"),
        "bbox_width": _bbox_value(item, "bbox_width"),
        "bbox_height": _bbox_value(item, "bbox_height"),
    }
    enriched.update(contract)
    return enriched


def enrich_explainability_items(items) -> list[dict]:
    return [enrich_explainability_case(item) for item in items]
