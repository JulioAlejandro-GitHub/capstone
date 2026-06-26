import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import run_tracker  # noqa: E402
from src.tracking_integration import record_threshold_calibration  # noqa: E402


class FakeTracker:
    def safe_track(self, function, *args, **kwargs):
        return function(*args, **kwargs)

    def log_threshold_calibration(self, *args, **kwargs):
        self.logged_args = args
        self.logged_kwargs = kwargs
        return "threshold-calibration-id"


class ThresholdCalibrationTrackingTests(unittest.TestCase):
    def test_record_threshold_calibration_passes_model_name_from_context(self):
        tracker = FakeTracker()
        context = {
            "run_id": "run-uuid",
            "model_name": "custom_cnn",
            "tracker": tracker,
        }

        result = record_threshold_calibration(
            context,
            {"threshold_selected": 0.42, "threshold_source": "validation_calibration"},
        )

        self.assertEqual(result, "threshold-calibration-id")
        self.assertEqual(tracker.logged_args[0], "run-uuid")
        self.assertEqual(tracker.logged_kwargs["model_name"], "custom_cnn")

    def test_log_threshold_calibration_extracts_selected_metrics(self):
        calibration = {
            "threshold_policy": "target_recall",
            "threshold_source": "validation_calibration",
            "threshold_selected": 0.42,
            "default_threshold": 0.5,
            "target_recall": 0.95,
            "target_recall_satisfied": True,
            "min_specificity": 0.7,
            "candidate_count": 101,
            "calibration_split": "val",
            "selected_metrics": {
                "recall_parasitized": 0.96,
                "specificity": 0.88,
                "precision_parasitized": 0.9,
                "f1_parasitized": 0.93,
                "f2_parasitized": 0.95,
                "balanced_accuracy": 0.92,
                "pr_auc_parasitized": 0.94,
                "roc_auc_parasitized": 0.95,
            },
            "default_threshold_metrics": {"recall_parasitized": 0.9},
        }

        with patch(
            "src.run_tracker._execute_returning_id",
            return_value="threshold-calibration-id",
        ) as execute:
            result = run_tracker.log_threshold_calibration(
                "run-uuid",
                calibration,
                model_name="custom_cnn",
            )

        self.assertEqual(result, "threshold-calibration-id")
        sql, params = execute.call_args.args
        self.assertIn("INSERT INTO run_threshold_calibration", sql)
        self.assertEqual(params["threshold_selected"], 0.42)
        self.assertEqual(params["default_threshold"], 0.5)
        self.assertEqual(params["validation_recall_at_threshold"], 0.96)
        self.assertEqual(params["validation_specificity_at_threshold"], 0.88)
        self.assertEqual(params["candidate_count"], 101)
        self.assertEqual(params["calibration_split"], "val")
        self.assertEqual(
            json.loads(params["selected_threshold_metrics"])["f2_parasitized"],
            0.95,
        )

    def test_log_threshold_calibration_skips_missing_selected_threshold(self):
        with patch("src.run_tracker._execute_returning_id") as execute:
            result = run_tracker.log_threshold_calibration(
                "run-uuid",
                {"threshold_source": "validation_calibration"},
            )

        self.assertIsNone(result)
        execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
