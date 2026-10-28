"""Keras callbacks over the framework-independent checkpoint policy."""
import json
from pathlib import Path

import numpy as np
import tensorflow as tf

from src.config import CLASS_NAMES
from src.metrics import collect_predictions

from .checkpoint_policy import *  # noqa: F401,F403 -- historical names used by the callbacks
from .checkpoint_policy import (
    _json_safe,
    clinical_validation_logs,
)


class ClinicalValidationMetricsCallback(tf.keras.callbacks.Callback):
    def __init__(
        self,
        validation_data,
        threshold: float = 0.5,
        min_class_fraction: float = 0.05,
        class_names=None,
        checkpoint_policy_config: CheckpointPolicyConfig | None = None,
        early_stopping_monitor: str | None = None,
        early_stopping_mode: str = "max",
        verbose: int = 0,
    ):
        super().__init__()
        self.validation_data = validation_data
        self.threshold = float(threshold)
        self.min_class_fraction = float(min_class_fraction)
        self.class_names = list(class_names or CLASS_NAMES)
        self.checkpoint_policy_config = checkpoint_policy_config
        self.early_stopping_monitor = early_stopping_monitor
        self.early_stopping_mode = str(early_stopping_mode)
        self.verbose = int(verbose)

    def on_epoch_end(self, epoch, logs=None):
        logs = logs if logs is not None else {}
        y_true, _, y_score = collect_predictions(
            self.model,
            self.validation_data,
            class_names=self.class_names,
            threshold=self.threshold,
        )
        clinical_validation_logs(
            logs, y_true, y_score, threshold=self.threshold,
            min_class_fraction=self.min_class_fraction, class_names=self.class_names,
            checkpoint_policy_config=self.checkpoint_policy_config,
            early_stopping_monitor=self.early_stopping_monitor,
            early_stopping_mode=self.early_stopping_mode,
        )

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
        monitor: str | None = None,
        mode: str = "max",
        verbose: int = 1,
    ):
        super().__init__()
        self.output_dir = Path(output_dir)
        self.config = config
        self.checkpoint_path = self.output_dir / checkpoint_filename
        self.monitor = monitor
        self.mode = str(mode)
        if self.mode not in {"min", "max"}:
            raise ValueError("mode debe ser 'min' o 'max'.")
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

    def _select_best(self) -> dict:
        if self.monitor:
            return select_best_epoch_by_monitor(
                self.records,
                self.config,
                monitor=self.monitor,
                mode=self.mode,
            )
        return select_best_epoch_from_history(self.records, self.config)

    def on_epoch_end(self, epoch, logs=None):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        record = self._record_from_logs(epoch, logs or {})
        self.records.append(record)
        selection = self._select_best()
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
            self.best_selection = self._select_best()
            self._write_summary(self.best_selection)

    def selection_summary(self):
        if not self.records:
            return None
        selection = self._select_best()
        self.best_selection = selection
        return checkpoint_policy_summary(
            self.config,
            selection,
            checkpoint_path=self.checkpoint_path,
        )
