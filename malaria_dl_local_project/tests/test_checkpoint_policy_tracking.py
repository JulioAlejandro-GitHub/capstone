import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import run_tracker  # noqa: E402
from src.tracking_integration import record_checkpoint_policy  # noqa: E402


class FakeTracker:
    def safe_track(self, function, *args, **kwargs):
        return function(*args, **kwargs)

    def log_checkpoint_policy(self, *args, **kwargs):
        self.logged_args = args
        self.logged_kwargs = kwargs
        return "checkpoint-policy-id"


class CheckpointPolicyTrackingTests(unittest.TestCase):
    def test_record_checkpoint_policy_passes_model_name_from_context(self):
        tracker = FakeTracker()
        context = {
            "run_id": "run-uuid",
            "model_name": "custom_cnn",
            "tracker": tracker,
        }

        result = record_checkpoint_policy(
            context,
            {"checkpoint_policy": "max_recall", "selected_epoch": 3},
        )

        self.assertEqual(result, "checkpoint-policy-id")
        self.assertEqual(tracker.logged_args[0], "run-uuid")
        self.assertEqual(tracker.logged_kwargs["model_name"], "custom_cnn")

    def test_log_checkpoint_policy_extracts_policy_metrics_and_defaults(self):
        summary = {
            "checkpoint_policy_config": {"policy": "max_recall", "min_recall": 0.95},
            "selected_epoch": 4,
            "policy_satisfied": True,
            "selected_metric": "val_f2_parasitized",
            "selected_metric_value": 0.91,
            "selected_metrics": {
                "val_recall_parasitized": 0.98,
                "val_f2_parasitized": 0.91,
                "val_specificity": 0.87,
                "val_pr_auc_parasitized": 0.94,
            },
            "prediction_collapse_detected": False,
            "all_epochs_collapsed": False,
            "checkpoint_path": "outputs/custom_cnn/best_model.keras",
        }

        with patch(
            "src.run_tracker._execute_returning_id",
            return_value="checkpoint-policy-id",
        ) as execute:
            result = run_tracker.log_checkpoint_policy(
                "run-uuid",
                summary,
                model_name="custom_cnn",
            )

        self.assertEqual(result, "checkpoint-policy-id")
        sql, params = execute.call_args.args
        self.assertIn("INSERT INTO run_checkpoint_policy", sql)
        self.assertEqual(params["checkpoint_policy"], "max_recall")
        self.assertEqual(json.loads(params["checkpoint_policy_config"])["min_recall"], 0.95)
        self.assertEqual(params["selected_epoch"], 4)
        self.assertTrue(params["policy_satisfied"])
        self.assertEqual(params["val_recall_parasitized_selected"], 0.98)
        self.assertEqual(params["val_specificity_selected"], 0.87)
        self.assertFalse(params["prediction_collapse_detected"])

    def test_log_checkpoint_policy_uses_unknown_when_policy_is_absent(self):
        with patch(
            "src.run_tracker._execute_returning_id",
            return_value="checkpoint-policy-id",
        ) as execute:
            run_tracker.log_checkpoint_policy("run-uuid", {}, model_name="custom_cnn")

        self.assertEqual(execute.call_args.args[1]["checkpoint_policy"], "unknown")


if __name__ == "__main__":
    unittest.main()
