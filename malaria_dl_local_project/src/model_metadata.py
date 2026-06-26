import json
from pathlib import Path

from src.config import (
    CLASS_NAMES,
    LABEL_MAPPING_VERSION,
    NEGATIVE_CLASS_INDEX,
    NEGATIVE_LABEL,
    POSITIVE_CLASS_INDEX,
    POSITIVE_LABEL,
    RAW_MODEL_SCORE_MEANING,
)


MODEL_METADATA_FILENAME = "model_metadata.json"
CLINICAL_METRICS_AVAILABLE = [
    "accuracy",
    "precision_parasitized",
    "recall_parasitized",
    "sensitivity_parasitized",
    "specificity",
    "f1_parasitized",
    "f2_parasitized",
    "roc_auc_parasitized",
    "pr_auc_parasitized",
    "balanced_accuracy",
]
CLINICAL_THRESHOLD_NOT_CALIBRATED_WARNING = (
    "Clinical threshold has not been calibrated."
)


def build_model_metadata(
    model_name,
    threshold_default=0.5,
    preprocessing="rescale_0_1",
    checkpoint_monitor="val_auc",
    early_stopping_monitor="val_auc",
    optimizer="adam",
    learning_rate=None,
    extra=None,
):
    metadata = {
        "model_name": model_name,
        "label_mapping_version": LABEL_MAPPING_VERSION,
        "class_names": CLASS_NAMES,
        "negative_class_index": NEGATIVE_CLASS_INDEX,
        "negative_class_name": NEGATIVE_LABEL,
        "positive_class_index": POSITIVE_CLASS_INDEX,
        "positive_class_name": POSITIVE_LABEL,
        "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
        "clinical_metrics_available": CLINICAL_METRICS_AVAILABLE,
        "clinical_threshold": disabled_clinical_threshold_metadata(),
        "threshold_default": float(threshold_default),
        "preprocessing": preprocessing,
        "checkpoint_monitor": checkpoint_monitor,
        "early_stopping_monitor": early_stopping_monitor,
        "optimizer": optimizer,
        "learning_rate": None if learning_rate is None else float(learning_rate),
    }
    if extra:
        metadata.update(extra)
    return metadata


def metadata_path_for_checkpoint(checkpoint):
    checkpoint = Path(checkpoint)
    return checkpoint.parent / MODEL_METADATA_FILENAME


def disabled_clinical_threshold_metadata(warning=CLINICAL_THRESHOLD_NOT_CALIBRATED_WARNING):
    return {
        "enabled": False,
        "warning": warning,
    }


def write_model_metadata(output_dir, metadata, merge_existing=True):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = output_dir / MODEL_METADATA_FILENAME
    if merge_existing and metadata_path.exists():
        existing_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        existing_metadata.update(metadata)
        metadata = existing_metadata
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return metadata_path


def load_model_metadata_for_checkpoint(checkpoint):
    metadata_path = metadata_path_for_checkpoint(checkpoint)
    if not metadata_path.exists():
        return None
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def clinical_threshold_metadata_from_calibration(calibration_result):
    selected_metrics = calibration_result.get("selected_metrics") or {}
    default_metrics = calibration_result.get("default_threshold_metrics") or {}
    return {
        "enabled": True,
        "threshold_policy": calibration_result.get("threshold_policy", "target_recall"),
        "threshold_source": calibration_result.get(
            "threshold_source",
            "validation_calibration",
        ),
        "threshold_selected": float(calibration_result["threshold_selected"]),
        "threshold_used": float(calibration_result["threshold_selected"]),
        "default_threshold": float(calibration_result.get("default_threshold", 0.5)),
        "target_recall": float(calibration_result.get("target_recall", 0.98)),
        "target_recall_satisfied": bool(
            calibration_result.get("target_recall_satisfied", False)
        ),
        "target_recall_satisfied_on_validation": bool(
            calibration_result.get(
                "target_recall_satisfied_on_validation",
                calibration_result.get("target_recall_satisfied", False),
            )
        ),
        "min_specificity": calibration_result.get("min_specificity"),
        "min_specificity_satisfied": calibration_result.get("min_specificity_satisfied"),
        "validation_metrics_at_threshold": selected_metrics,
        "default_threshold_metrics": default_metrics,
        "candidate_count": calibration_result.get("candidate_count"),
        "warning": calibration_result.get("warning"),
        "calibration_split": calibration_result.get("calibration_split", "val"),
        "positive_label": POSITIVE_LABEL,
        "negative_label": NEGATIVE_LABEL,
        "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
    }


def update_model_metadata_with_clinical_threshold(checkpoint, calibration_result):
    metadata = load_model_metadata_for_checkpoint(checkpoint) or {}
    metadata.update(
        {
            "label_mapping_version": metadata.get(
                "label_mapping_version",
                LABEL_MAPPING_VERSION,
            ),
            "class_names": metadata.get("class_names", CLASS_NAMES),
            "negative_class_index": metadata.get(
                "negative_class_index",
                NEGATIVE_CLASS_INDEX,
            ),
            "negative_class_name": metadata.get("negative_class_name", NEGATIVE_LABEL),
            "positive_class_index": metadata.get(
                "positive_class_index",
                POSITIVE_CLASS_INDEX,
            ),
            "positive_class_name": metadata.get("positive_class_name", POSITIVE_LABEL),
            "raw_model_score_meaning": metadata.get(
                "raw_model_score_meaning",
                RAW_MODEL_SCORE_MEANING,
            ),
            "clinical_threshold": clinical_threshold_metadata_from_calibration(
                calibration_result
            ),
        }
    )
    metadata_path = metadata_path_for_checkpoint(checkpoint)
    write_model_metadata(metadata_path.parent, metadata, merge_existing=True)
    return metadata_path, metadata


def load_clinical_threshold_for_checkpoint(checkpoint_path: Path) -> dict:
    metadata = load_model_metadata_for_checkpoint(checkpoint_path)
    if not metadata:
        raise ValueError(
            "No clinical threshold found in model metadata. "
            "Run calibration first or use --threshold 0.5."
        )

    clinical_threshold = metadata.get("clinical_threshold") or {}
    if not clinical_threshold.get("enabled"):
        raise ValueError(
            "No clinical threshold found in model metadata. "
            "Run calibration first or use --threshold 0.5."
        )
    threshold_selected = clinical_threshold.get("threshold_selected")
    if threshold_selected is None:
        raise ValueError(
            "No clinical threshold found in model metadata. "
            "Run calibration first or use --threshold 0.5."
        )

    return {
        **clinical_threshold,
        "threshold_used": float(threshold_selected),
        "threshold_selected": float(threshold_selected),
        "threshold_source": clinical_threshold.get(
            "threshold_source",
            "validation_calibration",
        ),
        "model_metadata_path": str(metadata_path_for_checkpoint(checkpoint_path)),
    }


def resolve_threshold_for_checkpoint(threshold, checkpoint_path: Path) -> dict:
    if isinstance(threshold, str) and threshold.strip().lower() == "clinical":
        clinical_threshold = load_clinical_threshold_for_checkpoint(checkpoint_path)
        return {
            "threshold_requested": "clinical",
            "threshold_mode": "clinical",
            "threshold_used": float(clinical_threshold["threshold_used"]),
            "threshold_source": clinical_threshold.get(
                "threshold_source",
                "validation_calibration",
            ),
            "clinical_threshold": clinical_threshold,
            "target_recall": clinical_threshold.get("target_recall"),
            "target_recall_satisfied_on_validation": clinical_threshold.get(
                "target_recall_satisfied_on_validation",
                clinical_threshold.get("target_recall_satisfied"),
            ),
            "expected_specificity": (
                (clinical_threshold.get("validation_metrics_at_threshold") or {}).get(
                    "specificity"
                )
            ),
            "warning": clinical_threshold.get("warning"),
        }

    try:
        threshold_value = float(threshold)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "threshold debe ser un número entre 0 y 1 o el valor 'clinical'."
        ) from exc
    if not 0.0 <= threshold_value <= 1.0:
        raise ValueError("threshold debe estar entre 0 y 1.")
    return {
        "threshold_requested": threshold,
        "threshold_mode": "fixed",
        "threshold_used": threshold_value,
        "threshold_source": "fixed_cli",
        "clinical_threshold": None,
        "target_recall": None,
        "target_recall_satisfied_on_validation": None,
        "expected_specificity": None,
        "warning": None,
    }


def resolve_threshold(checkpoint_path: Path, threshold) -> dict:
    return resolve_threshold_for_checkpoint(threshold, checkpoint_path)


def verify_checkpoint_metadata(
    checkpoint,
    expected_label_mapping=LABEL_MAPPING_VERSION,
    expected_raw_score_meaning=RAW_MODEL_SCORE_MEANING,
    warn=True,
):
    metadata = load_model_metadata_for_checkpoint(checkpoint)
    warnings = []
    if metadata is None:
        warnings.append(
            "No se pudo verificar label mapping del checkpoint. "
            "Este modelo debe estar entrenado con 0 = uninfected, "
            "1 = parasitized."
        )
    else:
        label_mapping_version = metadata.get("label_mapping_version")
        raw_model_score_meaning = metadata.get("raw_model_score_meaning")
        class_names = metadata.get("class_names")
        if label_mapping_version != expected_label_mapping:
            warnings.append(
                "El label mapping del checkpoint "
                f"({label_mapping_version}) no coincide con el solicitado "
                f"({expected_label_mapping})."
            )
        if raw_model_score_meaning != expected_raw_score_meaning:
            warnings.append(
                "El significado de raw_model_score del checkpoint "
                f"({raw_model_score_meaning}) no coincide con "
                f"{expected_raw_score_meaning}."
            )
        if class_names != CLASS_NAMES:
            warnings.append(
                f"El orden de clases del checkpoint ({class_names}) no coincide "
                f"con {CLASS_NAMES}."
            )

    if warn:
        for warning in warnings:
            print(f"WARNING: {warning}")

    return {"metadata": metadata, "warnings": warnings}
