import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import tensorflow as tf


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.checkpoint_policy import (  # noqa: E402
    CheckpointPolicyConfig,
    ClinicalCheckpointCallback,
    select_best_epoch_by_monitor,
)
from src.train import (  # noqa: E402
    build_phase_callbacks,
    early_stopping_phase_summary,
    find_early_stopping_callback,
)


class EarlyStoppingPolicyTests(unittest.TestCase):
    def _callbacks(self, output_dir, enabled=True):
        return build_phase_callbacks(
            output_dir=output_dir,
            checkpoint_callback=object(),
            clinical_validation_callback=object(),
            phase="training_base",
            early_stopping_monitor="val_f2_parasitized",
            early_stopping_mode="max",
            early_stopping_patience=12,
            early_stopping_enabled=enabled,
            early_stopping_min_delta=0.0001,
            restore_best_weights=True,
        )

    def test_builder_configures_validation_monitor_and_controls(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            callback = find_early_stopping_callback(self._callbacks(temp_dir))

        self.assertIsInstance(callback, tf.keras.callbacks.EarlyStopping)
        self.assertEqual(callback.monitor, "val_f2_parasitized")
        self.assertEqual(callback.mode, "max")
        self.assertEqual(callback.patience, 12)
        self.assertAlmostEqual(callback.min_delta, 0.0001)
        self.assertTrue(callback.restore_best_weights)

    def test_disabled_early_stopping_does_not_add_callback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            callback = find_early_stopping_callback(
                self._callbacks(temp_dir, enabled=False)
            )

        self.assertIsNone(callback)

    def test_phase_summary_converts_epochs_to_global_one_based_values(self):
        summary = early_stopping_phase_summary(
            SimpleNamespace(stopped_epoch=3, best_epoch=1, best=0.91),
            phase="fine_tuning",
            epoch_offset=5,
            completed_epochs=4,
        )

        self.assertTrue(summary["triggered"])
        self.assertEqual(summary["stopped_epoch"], 9)
        self.assertEqual(summary["best_epoch"], 7)
        self.assertAlmostEqual(summary["best_validation_value"], 0.91)

    def test_explicit_monitor_selects_minimum_validation_loss(self):
        selection = select_best_epoch_by_monitor(
            [
                {"epoch": 1, "val_loss": 0.5},
                {"epoch": 2, "val_loss": 0.3},
                {"epoch": 3, "val_loss": 0.4},
            ],
            CheckpointPolicyConfig(),
            monitor="val_loss",
            mode="min",
        )

        self.assertEqual(selection["selected_epoch"], 2)
        self.assertAlmostEqual(selection["selected_metric_value"], 0.3)

    def test_checkpoint_monitor_selects_global_best_across_phases(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            callback = ClinicalCheckpointCallback(
                temp_dir,
                CheckpointPolicyConfig(),
                monitor="val_f2_parasitized",
                mode="max",
                verbose=0,
            )
            model = MagicMock()
            callback.set_model(model)
            callback.set_phase("training_base", epoch_offset=0)
            callback.on_epoch_end(0, {"val_f2_parasitized": 0.70})
            callback.set_phase("fine_tuning", epoch_offset=1)
            callback.on_epoch_end(0, {"val_f2_parasitized": 0.82})

        summary = callback.selection_summary()
        self.assertEqual(summary["selected_epoch"], 2)
        self.assertEqual(summary["phase"], "fine_tuning")
        self.assertEqual(summary["selected_metric"], "val_f2_parasitized")
        self.assertEqual(model.save.call_count, 2)

    def test_phase_summary_uses_raw_logical_value_for_min_monitor(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            callbacks = build_phase_callbacks(
                output_dir=temp_dir,
                checkpoint_callback=object(),
                clinical_validation_callback=object(),
                phase="training_base",
                early_stopping_monitor="val_early_stopping_score",
                early_stopping_value_monitor="val_loss",
                early_stopping_mode="max",
                early_stopping_patience=2,
            )
            callback = find_early_stopping_callback(callbacks)
            model = MagicMock()
            model.get_weights.return_value = []
            callback.set_model(model)
            callback.on_train_begin()
            callback.on_epoch_end(
                0,
                {
                    "val_early_stopping_score": -0.25,
                    "val_loss": 0.25,
                },
            )
            summary = early_stopping_phase_summary(
                callback,
                phase="base",
                epoch_offset=0,
                completed_epochs=1,
            )

        self.assertAlmostEqual(summary["best_validation_value"], 0.25)


if __name__ == "__main__":
    unittest.main()
