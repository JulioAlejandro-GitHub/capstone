from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np

from src.config import (
    LABEL_MAPPING_METADATA,
    LABEL_MAPPING_VERSION,
    NEGATIVE_CLASS_INDEX,
    NEGATIVE_LABEL,
    POSITIVE_CLASS_INDEX,
    POSITIVE_LABEL,
    RAW_MODEL_SCORE_MEANING,
)
from src.metrics import compute_clinical_metrics


THRESHOLD_CALIBRATION_SCHEMA_VERSION = 1
THRESHOLD_CALIBRATION_FILENAME = "threshold_calibration.json"
DEFAULT_THRESHOLD = 0.5
LOW_THRESHOLD_WARNING_CUTOFF = 0.05
TEST_SET_CALIBRATION_ERROR = (
    "No se permite calibrar threshold usando test set. Use validation set."
)


def _as_float(value):
    if value is None:
        return None
    return float(value)


def _json_safe(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return value


def validate_calibration_split(dataset_split: str) -> str:
    split = str(dataset_split or "val").strip().lower()
    if split == "test":
        raise ValueError(TEST_SET_CALIBRATION_ERROR)
    if split in {"val", "validation"}:
        return "val"
    raise ValueError("La calibración de threshold debe usar dataset-split val.")


def build_threshold_candidates(y_scores, include_default: bool = True) -> list[float]:
    """
    Construye candidatos sobre probability_parasitized.

    Convención:
      0 = uninfected
      1 = parasitized
    """
    scores = np.asarray(y_scores, dtype=np.float64).reshape(-1)
    scores = scores[np.isfinite(scores)]
    scores = np.clip(scores, 0.0, 1.0)

    candidates = {0.0, 1.0}
    candidates.update(float(value) for value in np.unique(scores))
    if include_default:
        candidates.add(DEFAULT_THRESHOLD)

    return sorted(candidates)


def _metric_subset(metrics: dict) -> dict:
    keys = [
        "threshold",
        "recall_parasitized",
        "sensitivity_parasitized",
        "specificity",
        "precision_parasitized",
        "f1_parasitized",
        "f2_parasitized",
        "balanced_accuracy",
        "roc_auc_parasitized",
        "pr_auc_parasitized",
        "tn",
        "fp",
        "fn",
        "tp",
        "true_negative",
        "false_positive",
        "false_negative",
        "true_positive",
        "confusion_matrix",
        "prediction_collapse_detected",
        "n_pred_uninfected",
        "n_pred_parasitized",
        "percent_pred_uninfected",
        "percent_pred_parasitized",
    ]
    return {key: _json_safe(metrics.get(key)) for key in keys if key in metrics}


def evaluate_threshold(y_true, y_scores, threshold: float, beta: float = 2.0) -> dict:
    """
    Evalúa un threshold usando compute_clinical_metrics.

    y_scores debe ser probability_parasitized. El argumento beta se conserva para
    compatibilidad de API; las métricas clínicas actuales exponen F2.
    """
    metrics = compute_clinical_metrics(y_true, y_scores, threshold=float(threshold))
    metrics["threshold"] = float(threshold)
    metrics["beta"] = float(beta)
    return _json_safe(metrics)


def _selection_key(record: dict) -> tuple:
    metrics = record["metrics"]
    return (
        _as_float(metrics.get("specificity")) or 0.0,
        _as_float(metrics.get("precision_parasitized")) or 0.0,
        _as_float(metrics.get("f2_parasitized")) or 0.0,
        _as_float(metrics.get("balanced_accuracy")) or 0.0,
        float(record["threshold"]),
    )


def _fallback_key(record: dict) -> tuple:
    metrics = record["metrics"]
    return (
        _as_float(metrics.get("recall_parasitized")) or 0.0,
        _as_float(metrics.get("specificity")) or 0.0,
        _as_float(metrics.get("precision_parasitized")) or 0.0,
        _as_float(metrics.get("f2_parasitized")) or 0.0,
        _as_float(metrics.get("balanced_accuracy")) or 0.0,
        float(record["threshold"]),
    )


def _warnings(*items) -> str | None:
    warnings = [str(item) for item in items if item]
    return " ".join(warnings) if warnings else None


def find_threshold_for_target_recall(
    y_true,
    y_scores,
    target_recall: float = 0.98,
    min_specificity: float | None = None,
    beta: float = 2.0,
) -> dict:
    """
    Selecciona un threshold sobre probability_parasitized para alcanzar target_recall.

    Convención:
      0 = uninfected
      1 = parasitized

    La función no carga datos por sí misma: el llamador debe pasar aquí solo
    predicciones del conjunto de validación.
    """
    y_true = np.asarray(y_true).astype(int).reshape(-1)
    y_scores = np.asarray(y_scores, dtype=np.float64).reshape(-1)
    if len(y_true) == 0:
        raise ValueError("No hay muestras para calibrar threshold.")
    if len(y_true) != len(y_scores):
        raise ValueError("y_true y y_scores deben tener el mismo largo.")

    target_recall = float(target_recall)
    beta = float(beta)
    if not 0.0 <= target_recall <= 1.0:
        raise ValueError("target_recall debe estar entre 0 y 1.")
    if min_specificity is not None and not 0.0 <= float(min_specificity) <= 1.0:
        raise ValueError("min_specificity debe estar entre 0 y 1.")

    candidates = build_threshold_candidates(y_scores, include_default=True)
    records = [
        {
            "threshold": float(threshold),
            "metrics": evaluate_threshold(y_true, y_scores, threshold, beta=beta),
        }
        for threshold in candidates
    ]
    default_metrics = evaluate_threshold(
        y_true,
        y_scores,
        DEFAULT_THRESHOLD,
        beta=beta,
    )

    target_valid = [
        record
        for record in records
        if (_as_float(record["metrics"].get("recall_parasitized")) or 0.0)
        >= target_recall
    ]
    policy_valid = target_valid
    min_specificity_satisfied = None
    specificity_warning = None
    if min_specificity is not None:
        policy_valid = [
            record
            for record in target_valid
            if (_as_float(record["metrics"].get("specificity")) or 0.0)
            >= float(min_specificity)
        ]
        min_specificity_satisfied = bool(policy_valid)
        if not policy_valid and target_valid:
            specificity_warning = (
                "No threshold satisfied both target_recall and min_specificity; "
                "selected among thresholds satisfying target_recall."
            )
            policy_valid = target_valid

    target_recall_satisfied = bool(target_valid)
    if policy_valid:
        selected = max(policy_valid, key=_selection_key)
    else:
        selected = max(records, key=_fallback_key)

    selected_threshold = float(selected["threshold"])
    warning = None
    if not target_recall_satisfied:
        warning = "No threshold reached target_recall on validation set."
    if selected_threshold < LOW_THRESHOLD_WARNING_CUTOFF:
        warning = _warnings(
            warning,
            "Selected threshold is very low and may produce excessive false positives.",
        )
    warning = _warnings(warning, specificity_warning)

    selected_metrics = _metric_subset(selected["metrics"])
    default_threshold_metrics = _metric_subset(default_metrics)
    result = {
        "schema_version": THRESHOLD_CALIBRATION_SCHEMA_VERSION,
        "threshold_policy": "target_recall",
        "threshold_source": "validation_calibration",
        "threshold_selected": selected_threshold,
        "threshold_used": selected_threshold,
        "default_threshold": DEFAULT_THRESHOLD,
        "target_recall": target_recall,
        "target_recall_satisfied": bool(target_recall_satisfied),
        "target_recall_satisfied_on_validation": bool(target_recall_satisfied),
        "min_specificity": None if min_specificity is None else float(min_specificity),
        "min_specificity_satisfied": min_specificity_satisfied,
        "beta": beta,
        "selected_metrics": selected_metrics,
        "validation_metrics_at_threshold": selected_metrics,
        "default_threshold_metrics": default_threshold_metrics,
        "candidate_count": int(len(candidates)),
        "warning": warning,
        "calibration_split": "val",
        "positive_label": POSITIVE_LABEL,
        "negative_label": NEGATIVE_LABEL,
        "positive_class_index": POSITIVE_CLASS_INDEX,
        "negative_class_index": NEGATIVE_CLASS_INDEX,
        "label_mapping_version": LABEL_MAPPING_VERSION,
        "label_mapping": LABEL_MAPPING_METADATA,
        "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
        "score_name": "probability_parasitized",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    return _json_safe(result)


def write_threshold_calibration(output_json, calibration_result: dict) -> Path:
    output_path = Path(output_json).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(_json_safe(calibration_result), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


def default_threshold_calibration_path(output_dir) -> Path:
    return Path(output_dir) / THRESHOLD_CALIBRATION_FILENAME
