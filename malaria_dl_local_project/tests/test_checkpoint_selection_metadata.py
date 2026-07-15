import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.checkpoint_policy import CheckpointPolicyConfig  # noqa: E402
from src.train import (  # noqa: E402
    FINAL_TEST_ARTIFACT_NAMES,
    clear_final_test_artifacts,
    evaluate_selected_checkpoint_if_enabled,
    evaluate_selected_checkpoint_once,
    finalize_checkpoint_test_evaluation,
    resolve_threshold_calibration_output_path,
    write_checkpoint_selection_report,
    write_model_execution_summary,
)


class FakeCheckpointCallback:
    best_selection = {
        "selected_epoch": 25,
        "selected_metric": "val_f2_parasitized",
        "selected_metric_value": 0.9721,
    }

    def selection_summary(self):
        return {
            "policy": "f2",
            "selected_epoch": 25,
            "selected_metric": "val_f2_parasitized",
            "selected_metric_value": 0.9721,
            "selected_metrics": {"val_f2_parasitized": 0.9721},
            "policy_satisfied": True,
        }


class FakeRecallFallbackCallback:
    best_selection = {
        "selected_epoch": 19,
        "selected_metric": "val_recall_parasitized",
        "selected_metric_value": 0.95,
    }

    def selection_summary(self):
        return {
            "policy": "auc_with_min_recall",
            "selected_epoch": 19,
            "selected_metric": "val_recall_parasitized",
            "selected_metric_value": 0.95,
            "selected_metrics": {"val_recall_parasitized": 0.95},
            "policy_satisfied": False,
        }


class CheckpointSelectionMetadataTests(unittest.TestCase):
    def _write_report(self, output_dir, **overrides):
        kwargs = {
            "output_dir": output_dir,
            "checkpoint_policy_config": CheckpointPolicyConfig(policy="f2"),
            "checkpoint_monitor": "val_f2_parasitized",
            "checkpoint_mode": "max",
            "early_stopping_monitor": "val_f2_parasitized",
            "early_stopping_mode": "max",
            "checkpoint_callback": FakeCheckpointCallback(),
            "fine_tuning_enabled": True,
            "base_max_epochs": 60,
            "fine_tune_max_epochs": 40,
            "completed_epochs": 37,
            "stopped_epoch": 37,
            "early_stopping_enabled": True,
            "early_stopping_patience": 12,
            "early_stopping_min_delta": 0.0001,
            "restore_best_weights": True,
            "evaluate_best_on_test": True,
            "early_stopping_phases": [],
        }
        kwargs.update(overrides)
        return write_checkpoint_selection_report(**kwargs)

    def test_checkpoint_selection_contains_required_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = self._write_report(temp_dir)
            persisted = json.loads(
                (Path(temp_dir) / "checkpoint_selection.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(report, persisted)
        self.assertEqual(report["selection_policy"], "validation_best_checkpoint")
        self.assertEqual(report["max_epochs"], 60)
        self.assertEqual(report["total_max_epochs"], 100)
        self.assertEqual(report["completed_epochs"], 37)
        self.assertEqual(report["stopped_epoch"], 37)
        self.assertEqual(report["best_epoch"], 25)
        self.assertAlmostEqual(report["best_validation_value"], 0.9721)
        self.assertFalse(report["test_used_for_selection"])
        self.assertFalse(report["test_used_for_early_stopping"])
        self.assertEqual(report["test_evaluation_policy"], "pending")
        self.assertFalse(report["test_evaluation_completed"])

    def test_finalized_checkpoint_report_records_completed_test(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = self._write_report(temp_dir)
            finalized = finalize_checkpoint_test_evaluation(
                temp_dir,
                report,
                evaluated=True,
            )

        self.assertTrue(finalized["test_evaluation_completed"])
        self.assertTrue(finalized["test_evaluation_after_selection"])
        self.assertEqual(
            finalized["test_evaluation_policy"],
            "single_final_evaluation",
        )

    def test_completed_epochs_cannot_exceed_total_maximum(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                self._write_report(
                    temp_dir,
                    base_max_epochs=2,
                    fine_tune_max_epochs=1,
                    completed_epochs=4,
                )

    def test_fallback_value_is_paired_with_its_actual_validation_metric(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = self._write_report(
                temp_dir,
                checkpoint_callback=FakeRecallFallbackCallback(),
                checkpoint_policy_config=CheckpointPolicyConfig(
                    policy="auc_with_min_recall"
                ),
                checkpoint_monitor="val_auc",
            )

        self.assertEqual(report["checkpoint_monitor_configured"], "val_auc")
        self.assertEqual(report["checkpoint_monitor"], "val_recall_parasitized")
        self.assertAlmostEqual(report["best_validation_value"], 0.95)

    def test_final_test_contract_is_written_once(self):
        fake_metrics = {
            "accuracy": 0.95,
            "classification_report_dict": {
                "parasitized": {"recall": 0.97}
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "src.train.evaluate_keras_model",
            return_value=fake_metrics,
        ) as evaluator:
            metrics = evaluate_selected_checkpoint_once(
                model=object(),
                dataset=object(),
                class_names=["uninfected", "parasitized"],
                output_dir=temp_dir,
                checkpoint_path=Path(temp_dir) / "best_model.keras",
                threshold=0.42,
                metadata={"evaluation_split": "test"},
            )
            persisted = json.loads(
                (Path(temp_dir) / "test_metrics.json").read_text(encoding="utf-8")
            )
            report = json.loads(
                (Path(temp_dir) / "classification_report.json").read_text(
                    encoding="utf-8"
                )
            )

        evaluator.assert_called_once()
        self.assertEqual(metrics["test_evaluation_policy"], "single_final_evaluation")
        self.assertFalse(persisted["test_used_for_checkpoint_selection"])
        self.assertFalse(persisted["test_used_for_early_stopping"])
        self.assertFalse(persisted["test_used_for_threshold_selection"])
        self.assertEqual(report["parasitized"]["recall"], 0.97)

    def test_skip_clears_stale_test_files_and_does_not_call_evaluator(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            for filename in FINAL_TEST_ARTIFACT_NAMES:
                (Path(temp_dir) / filename).write_text("stale", encoding="utf-8")
            clear_final_test_artifacts(temp_dir)
            with patch("src.train.evaluate_selected_checkpoint_once") as evaluator:
                result = evaluate_selected_checkpoint_if_enabled(False)

            self.assertIsNone(result)
            evaluator.assert_not_called()
            self.assertFalse(
                any((Path(temp_dir) / filename).exists() for filename in FINAL_TEST_ARTIFACT_NAMES)
            )

    def test_threshold_output_rejects_reserved_artifact_names(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                resolve_threshold_calibration_output_path(
                    temp_dir,
                    Path(temp_dir) / "test_metrics.json",
                )

            valid = resolve_threshold_calibration_output_path(
                temp_dir,
                Path(temp_dir) / "threshold_custom.json",
            )

        self.assertEqual(valid.name, "threshold_custom.json")

    def test_threshold_output_cannot_overwrite_an_immutable_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            historical_output = (
                Path(temp_dir)
                / "runs"
                / "previous-execution"
                / "threshold_custom.json"
            )
            with self.assertRaisesRegex(ValueError, "snapshots inmutables"):
                resolve_threshold_calibration_output_path(
                    temp_dir,
                    historical_output,
                )

    def test_execution_summary_explains_validation_selection_and_single_test(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_model_execution_summary(
                temp_dir,
                {
                    "model_name": "custom_cnn",
                    "parameters": {},
                    "total_max_epochs": 100,
                    "completed_epochs": 37,
                    "stopped_epoch": 37,
                    "best_epoch": 25,
                    "checkpoint_monitor": "val_f2_parasitized",
                    "checkpoint_mode": "max",
                    "best_validation_value": 0.9721,
                    "test_evaluation_policy": "single_final_evaluation",
                    "test_used_for_selection": False,
                    "artifacts": [],
                },
            )
            markdown = Path(paths["markdown"]).read_text(encoding="utf-8")

        self.assertIn("máximo de 100 épocas", markdown)
        self.assertIn("mejor checkpoint corresponde a la época 25", markdown)
        self.assertIn("test se evaluó una sola vez", markdown)


if __name__ == "__main__":
    unittest.main()
