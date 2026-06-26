import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Optional

import numpy as np
import tensorflow as tf

from src.config import CLASS_NAMES
from src.metrics import (
    clinical_predictions_from_probabilities,
    collect_predictions,
    compute_clinical_metrics,
    detect_prediction_collapse,
)


CheckpointPolicyName = Literal[
    "f2",
    "auc_with_min_recall",
    "val_auc",
    "balanced_accuracy",
]

CHECKPOINT_POLICY_CHOICES = [
    "f2",
    "auc_with_min_recall",
    "val_auc",
    "balanced_accuracy",
]


@dataclass
class CheckpointPolicyConfig:
    policy: CheckpointPolicyName = "auc_with_min_recall"
    min_recall: float = 0.98
    beta: float = 2.0
    threshold: float = 0.5
    reject_prediction_collapse: bool = True
    min_class_fraction: float = 0.05

    def __post_init__(self):
        if self.policy not in CHECKPOINT_POLICY_CHOICES:
            raise ValueError(f"Política de checkpoint no soportada: {self.policy}")
        self.min_recall = float(self.min_recall)
        self.beta = float(self.beta)
        self.threshold = float(self.threshold)
        self.reject_prediction_collapse = bool(self.reject_prediction_collapse)
        self.min_class_fraction = float(self.min_class_fraction)


def checkpoint_policy_config_dict(config: CheckpointPolicyConfig) -> dict:
    return asdict(config)


def get_monitor_for_policy(config: CheckpointPolicyConfig) -> tuple[str, str]:
    if config.policy == "f2":
        return "val_f2_parasitized", "max"
    if config.policy == "balanced_accuracy":
        return "val_balanced_accuracy", "max"
    return "val_auc", "max"


def _json_safe(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _to_float(value, default=None):
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip()
        if normalized == "":
            return default
        if normalized.lower() in {"none", "nan", "null"}:
            return default
        value = normalized
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return default
    if np.isnan(numeric_value):
        return default
    return numeric_value


def _to_bool(value) -> bool:
    if isinstance(value, dict):
        return bool(value.get("collapsed", False))
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "collapsed"}
    if value is None:
        return False
    return bool(value)


def _metric(record, names, default=None):
    for name in names:
        if name in record:
            return _to_float(record.get(name), default=default)
    return default


def _metric_name_present(record, names):
    for name in names:
        if _to_float(record.get(name), default=None) is not None:
            return name
    return names[0]


def _epoch(record):
    epoch_value = _to_float(record.get("epoch"), default=0.0)
    return int(epoch_value)


def _is_collapsed(record) -> bool:
    for key in (
        "val_prediction_collapse_detected",
        "val_prediction_collapse",
        "prediction_collapse_detected",
        "prediction_collapse",
        "collapsed",
    ):
        if key in record:
            return _to_bool(record.get(key))
    return False


def _selected_metrics(record) -> dict:
    keys = [
        "val_auc",
        "val_roc_auc_parasitized",
        "val_pr_auc_parasitized",
        "val_recall_parasitized",
        "val_sensitivity_parasitized",
        "val_f2_parasitized",
        "val_specificity",
        "val_balanced_accuracy",
        "val_loss",
        "val_prediction_collapse_detected",
    ]
    return {
        key: _json_safe(record.get(key))
        for key in keys
        if key in record and record.get(key) is not None
    }


def _selection_result(
    *,
    selected_record,
    config: CheckpointPolicyConfig,
    selected_metric,
    selected_metric_value,
    policy_satisfied=True,
    warning=None,
    all_epochs_collapsed=False,
    rejected_collapsed_epochs=0,
) -> dict:
    collapsed = _is_collapsed(selected_record)
    return {
        "policy": config.policy,
        "selected_epoch": _epoch(selected_record),
        "phase": selected_record.get("phase"),
        "phase_epoch": selected_record.get("phase_epoch"),
        "policy_satisfied": bool(policy_satisfied),
        "selected_metric": selected_metric,
        "selected_metric_value": _json_safe(selected_metric_value),
        "min_recall_required": float(config.min_recall),
        "beta": float(config.beta),
        "threshold": float(config.threshold),
        "reject_prediction_collapse": bool(config.reject_prediction_collapse),
        "min_class_fraction": float(config.min_class_fraction),
        "val_recall_parasitized": _metric(
            selected_record,
            ["val_recall_parasitized", "val_sensitivity_parasitized", "val_recall"],
        ),
        "val_f2_parasitized": _metric(selected_record, ["val_f2_parasitized"]),
        "val_specificity": _metric(selected_record, ["val_specificity"]),
        "val_auc": _metric(
            selected_record,
            ["val_auc", "val_roc_auc_parasitized", "val_auc_parasitized"],
        ),
        "val_balanced_accuracy": _metric(selected_record, ["val_balanced_accuracy"]),
        "prediction_collapse_detected": bool(collapsed),
        "all_epochs_collapsed": bool(all_epochs_collapsed),
        "rejected_collapsed_epochs": int(rejected_collapsed_epochs),
        "checkpoint_path": selected_record.get("checkpoint_path"),
        "warning": warning,
        "selected_metrics": _selected_metrics(selected_record),
        "selected_record": _json_safe(selected_record),
    }


def _records_after_collapse_filter(history_records, config: CheckpointPolicyConfig):
    records = [dict(record) for record in history_records]
    if not records:
        raise ValueError("history_records no puede estar vacío.")

    collapsed_count = sum(1 for record in records if _is_collapsed(record))
    if not config.reject_prediction_collapse:
        return records, False, 0, None

    non_collapsed = [record for record in records if not _is_collapsed(record)]
    if non_collapsed:
        return (
            non_collapsed,
            False,
            collapsed_count,
            None,
        )

    return (
        records,
        True,
        collapsed_count,
        "All candidate epochs showed prediction collapse. Checkpoint is not clinically reliable.",
    )


def _max_by_metric(records, metric_names):
    selected_metric = _metric_name_present(records[0], metric_names)
    return max(
        records,
        key=lambda record: (
            _metric(record, metric_names, default=float("-inf")),
            _epoch(record),
        ),
    ), selected_metric


def _min_by_metric(records, metric_names):
    selected_metric = _metric_name_present(records[0], metric_names)
    return min(
        records,
        key=lambda record: (
            _metric(record, metric_names, default=float("inf")),
            -_epoch(record),
        ),
    ), selected_metric


def select_best_epoch_from_history(
    history_records: list[dict],
    config: CheckpointPolicyConfig,
) -> dict:
    """
    Selecciona el mejor epoch según una política clínicamente segura.

    Convención obligatoria del proyecto:
      0 = uninfected
      1 = parasitized
      raw_model_score = probability_parasitized
    """
    records, all_collapsed, rejected_collapsed, collapse_warning = (
        _records_after_collapse_filter(history_records, config)
    )

    if config.policy == "f2":
        selected, metric_name = _max_by_metric(records, ["val_f2_parasitized"])
        return _selection_result(
            selected_record=selected,
            config=config,
            selected_metric=metric_name,
            selected_metric_value=_metric(selected, [metric_name]),
            all_epochs_collapsed=all_collapsed,
            rejected_collapsed_epochs=rejected_collapsed,
            warning=collapse_warning,
        )

    if config.policy == "val_auc":
        auc_names = ["val_auc", "val_roc_auc_parasitized", "val_auc_parasitized"]
        selected, metric_name = _max_by_metric(records, auc_names)
        return _selection_result(
            selected_record=selected,
            config=config,
            selected_metric=metric_name,
            selected_metric_value=_metric(selected, auc_names),
            all_epochs_collapsed=all_collapsed,
            rejected_collapsed_epochs=rejected_collapsed,
            warning=collapse_warning,
        )

    if config.policy == "balanced_accuracy":
        selected, metric_name = _max_by_metric(records, ["val_balanced_accuracy"])
        return _selection_result(
            selected_record=selected,
            config=config,
            selected_metric=metric_name,
            selected_metric_value=_metric(selected, [metric_name]),
            all_epochs_collapsed=all_collapsed,
            rejected_collapsed_epochs=rejected_collapsed,
            warning=collapse_warning,
        )

    recall_names = [
        "val_recall_parasitized",
        "val_sensitivity_parasitized",
        "val_recall",
    ]
    auc_names = ["val_auc", "val_roc_auc_parasitized", "val_auc_parasitized"]
    valid_candidates = [
        record
        for record in records
        if _metric(record, recall_names, default=float("-inf")) >= config.min_recall
    ]

    if valid_candidates:
        metric_name = _metric_name_present(valid_candidates[0], auc_names)
        selected = max(
            valid_candidates,
            key=lambda record: (
                _metric(record, auc_names, default=float("-inf")),
                _metric(record, ["val_f2_parasitized"], default=float("-inf")),
                _metric(record, ["val_specificity"], default=float("-inf")),
                -_metric(record, ["val_loss"], default=float("inf")),
                _epoch(record),
            ),
        )
        return _selection_result(
            selected_record=selected,
            config=config,
            selected_metric=metric_name,
            selected_metric_value=_metric(selected, auc_names),
            all_epochs_collapsed=all_collapsed,
            rejected_collapsed_epochs=rejected_collapsed,
            warning=collapse_warning,
        )

    selected, metric_name = _max_by_metric(records, recall_names)
    warning = "No epoch reached min_recall. Selected fallback by best recall."
    if collapse_warning:
        warning = f"{collapse_warning} {warning}"
    return _selection_result(
        selected_record=selected,
        config=config,
        selected_metric=metric_name,
        selected_metric_value=_metric(selected, recall_names),
        policy_satisfied=False,
        all_epochs_collapsed=all_collapsed,
        rejected_collapsed_epochs=rejected_collapsed,
        warning=warning,
    )


def checkpoint_policy_summary(
    config: CheckpointPolicyConfig,
    selection: dict,
    checkpoint_path=None,
) -> dict:
    selected_metrics = dict(selection.get("selected_metrics") or {})
    return {
        "policy": config.policy,
        "min_recall": float(config.min_recall),
        "beta": float(config.beta),
        "threshold": float(config.threshold),
        "reject_prediction_collapse": bool(config.reject_prediction_collapse),
        "min_class_fraction": float(config.min_class_fraction),
        "selected_epoch": selection.get("selected_epoch"),
        "phase": selection.get("phase"),
        "phase_epoch": selection.get("phase_epoch"),
        "policy_satisfied": bool(selection.get("policy_satisfied")),
        "selected_metric": selection.get("selected_metric"),
        "selected_metric_value": selection.get("selected_metric_value"),
        "selected_metrics": selected_metrics,
        "prediction_collapse_detected": bool(
            selection.get("prediction_collapse_detected")
        ),
        "all_epochs_collapsed": bool(selection.get("all_epochs_collapsed")),
        "checkpoint_path": str(checkpoint_path or selection.get("checkpoint_path") or ""),
        "warning": selection.get("warning"),
    }


def write_checkpoint_policy_summary(output_dir, summary: dict) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "checkpoint_policy_summary.json"
    summary_path.write_text(
        json.dumps(_json_safe(summary), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return summary_path


class ClinicalValidationMetricsCallback(tf.keras.callbacks.Callback):
    def __init__(
        self,
        validation_data,
        threshold: float = 0.5,
        min_class_fraction: float = 0.05,
        class_names=None,
        verbose: int = 0,
    ):
        super().__init__()
        self.validation_data = validation_data
        self.threshold = float(threshold)
        self.min_class_fraction = float(min_class_fraction)
        self.class_names = list(class_names or CLASS_NAMES)
        self.verbose = int(verbose)

    def on_epoch_end(self, epoch, logs=None):
        logs = logs if logs is not None else {}
        y_true, _, y_score = collect_predictions(
            self.model,
            self.validation_data,
            class_names=self.class_names,
            threshold=self.threshold,
        )
        clinical_metrics = compute_clinical_metrics(
            y_true,
            y_score,
            threshold=self.threshold,
        )
        y_pred = clinical_predictions_from_probabilities(
            y_score,
            class_names=self.class_names,
            threshold=self.threshold,
        )
        collapse_summary = detect_prediction_collapse(
            y_pred,
            class_names=self.class_names,
            min_class_fraction=self.min_class_fraction,
        )
        clinical_metrics["prediction_collapse"] = collapse_summary
        clinical_metrics["prediction_collapse_detected"] = bool(
            collapse_summary["collapsed"]
        )

        metric_updates = {
            "val_f2_parasitized": clinical_metrics.get("f2_parasitized"),
            "val_pr_auc_parasitized": clinical_metrics.get("pr_auc_parasitized"),
            "val_roc_auc_parasitized": clinical_metrics.get("roc_auc_parasitized"),
            "val_recall_parasitized": clinical_metrics.get("recall_parasitized"),
            "val_sensitivity_parasitized": clinical_metrics.get(
                "sensitivity_parasitized"
            ),
            "val_specificity": clinical_metrics.get("specificity"),
            "val_balanced_accuracy": clinical_metrics.get("balanced_accuracy"),
            "val_prediction_collapse_detected": float(
                bool(collapse_summary["collapsed"])
            ),
            "val_prediction_collapse": float(bool(collapse_summary["collapsed"])),
            "val_n_pred_uninfected": collapse_summary.get("n_pred_uninfected"),
            "val_n_pred_parasitized": collapse_summary.get("n_pred_parasitized"),
            "val_percent_pred_uninfected": collapse_summary.get(
                "percent_pred_uninfected"
            ),
            "val_percent_pred_parasitized": collapse_summary.get(
                "percent_pred_parasitized"
            ),
        }
        for key, value in metric_updates.items():
            if value is not None:
                logs[key] = float(value)

        if self.verbose:
            print(
                "val_f2_parasitized="
                f"{logs.get('val_f2_parasitized'):.4f} "
                "val_recall_parasitized="
                f"{logs.get('val_recall_parasitized'):.4f} "
                "val_specificity="
                f"{logs.get('val_specificity'):.4f}"
            )


class ClinicalCheckpointCallback(tf.keras.callbacks.Callback):
    def __init__(
        self,
        output_dir,
        config: CheckpointPolicyConfig,
        checkpoint_filename: str = "best_model.keras",
        verbose: int = 1,
    ):
        super().__init__()
        self.output_dir = Path(output_dir)
        self.config = config
        self.checkpoint_path = self.output_dir / checkpoint_filename
        self.records: list[dict] = []
        self.phase = "training_base"
        self.epoch_offset = 0
        self.best_selection: Optional[dict] = None
        self.verbose = int(verbose)

    def set_phase(self, phase: str, epoch_offset: int = 0):
        self.phase = str(phase)
        self.epoch_offset = int(epoch_offset)

    def _record_from_logs(self, epoch: int, logs: dict) -> dict:
        phase_epoch = int(epoch) + 1
        global_epoch = self.epoch_offset + phase_epoch
        record = {
            "epoch": global_epoch,
            "phase": self.phase,
            "phase_epoch": phase_epoch,
            "checkpoint_path": str(self.checkpoint_path),
        }
        for key, value in (logs or {}).items():
            if isinstance(value, (int, float, np.integer, np.floating, np.bool_)):
                record[key] = _json_safe(value)
        return record

    def _write_summary(self, selection: dict):
        summary = checkpoint_policy_summary(
            self.config,
            selection,
            checkpoint_path=self.checkpoint_path,
        )
        write_checkpoint_policy_summary(self.output_dir, summary)
        return summary

    def on_epoch_end(self, epoch, logs=None):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        record = self._record_from_logs(epoch, logs or {})
        self.records.append(record)
        selection = select_best_epoch_from_history(self.records, self.config)
        self.best_selection = selection
        selected_is_current = selection.get("selected_epoch") == record["epoch"]
        if selected_is_current:
            self.model.save(self.checkpoint_path, overwrite=True)
            if self.verbose:
                print(
                    "Clinical checkpoint saved: "
                    f"epoch={record['epoch']} "
                    f"policy={self.config.policy} "
                    f"{selection.get('selected_metric')}="
                    f"{selection.get('selected_metric_value')}"
                )
        self._write_summary(selection)

    def on_train_end(self, logs=None):
        if self.records:
            self.best_selection = select_best_epoch_from_history(
                self.records,
                self.config,
            )
            self._write_summary(self.best_selection)

    def selection_summary(self):
        if not self.records:
            return None
        selection = select_best_epoch_from_history(self.records, self.config)
        self.best_selection = selection
        return checkpoint_policy_summary(
            self.config,
            selection,
            checkpoint_path=self.checkpoint_path,
        )
