import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.checkpoint_policy import (
    CheckpointPolicyConfig,
    get_monitor_for_policy,
    select_best_epoch_from_history,
)


class CheckpointPolicyTests(unittest.TestCase):
    def test_f2_policy_selects_highest_val_f2(self):
        records = [
            {"epoch": 1, "val_f2_parasitized": 0.80},
            {"epoch": 2, "val_f2_parasitized": 0.92},
            {"epoch": 3, "val_f2_parasitized": 0.88},
        ]

        selected = select_best_epoch_from_history(
            records,
            CheckpointPolicyConfig(policy="f2"),
        )

        self.assertEqual(selected["selected_epoch"], 2)
        self.assertEqual(selected["selected_metric"], "val_f2_parasitized")
        self.assertTrue(selected["policy_satisfied"])

    def test_auc_with_min_recall_selects_best_auc_among_valid_epochs(self):
        records = [
            {
                "epoch": 1,
                "val_auc": 0.90,
                "val_recall_parasitized": 0.95,
                "val_f2_parasitized": 0.93,
                "val_specificity": 0.85,
                "val_loss": 0.30,
                "val_prediction_collapse_detected": False,
            },
            {
                "epoch": 2,
                "val_auc": 0.92,
                "val_recall_parasitized": 0.981,
                "val_f2_parasitized": 0.94,
                "val_specificity": 0.82,
                "val_loss": 0.28,
                "val_prediction_collapse_detected": False,
            },
            {
                "epoch": 3,
                "val_auc": 0.94,
                "val_recall_parasitized": 0.982,
                "val_f2_parasitized": 0.95,
                "val_specificity": 0.20,
                "val_loss": 0.26,
                "val_prediction_collapse_detected": True,
            },
        ]

        selected = select_best_epoch_from_history(
            records,
            CheckpointPolicyConfig(
                policy="auc_with_min_recall",
                min_recall=0.98,
                reject_prediction_collapse=True,
            ),
        )

        self.assertEqual(selected["selected_epoch"], 2)
        self.assertEqual(selected["selected_metric"], "val_auc")
        self.assertTrue(selected["policy_satisfied"])
        self.assertFalse(selected["prediction_collapse_detected"])

    def test_auc_with_min_recall_fallback_when_no_epoch_reaches_min_recall(self):
        records = [
            {"epoch": 1, "val_auc": 0.90, "val_recall_parasitized": 0.91},
            {"epoch": 2, "val_auc": 0.92, "val_recall_parasitized": 0.94},
        ]

        selected = select_best_epoch_from_history(
            records,
            CheckpointPolicyConfig(policy="auc_with_min_recall", min_recall=0.98),
        )

        self.assertEqual(selected["selected_epoch"], 2)
        self.assertFalse(selected["policy_satisfied"])
        self.assertIn("No epoch reached min_recall", selected["warning"])

    def test_policy_rejects_collapsed_epoch_when_enabled(self):
        records = [
            {
                "epoch": 1,
                "val_auc": 0.91,
                "val_recall_parasitized": 0.981,
                "val_prediction_collapse_detected": False,
            },
            {
                "epoch": 2,
                "val_auc": 0.99,
                "val_recall_parasitized": 1.0,
                "val_prediction_collapse_detected": True,
            },
        ]

        selected = select_best_epoch_from_history(
            records,
            CheckpointPolicyConfig(
                policy="auc_with_min_recall",
                min_recall=0.98,
                reject_prediction_collapse=True,
            ),
        )

        self.assertEqual(selected["selected_epoch"], 1)
        self.assertEqual(selected["rejected_collapsed_epochs"], 1)

    def test_policy_all_epochs_collapsed_returns_warning(self):
        records = [
            {
                "epoch": 1,
                "val_auc": 0.91,
                "val_recall_parasitized": 0.981,
                "val_prediction_collapse_detected": True,
            },
            {
                "epoch": 2,
                "val_auc": 0.93,
                "val_recall_parasitized": 0.982,
                "val_prediction_collapse_detected": True,
            },
        ]

        selected = select_best_epoch_from_history(
            records,
            CheckpointPolicyConfig(
                policy="auc_with_min_recall",
                min_recall=0.98,
                reject_prediction_collapse=True,
            ),
        )

        self.assertEqual(selected["selected_epoch"], 2)
        self.assertTrue(selected["all_epochs_collapsed"])
        self.assertIn("All candidate epochs showed prediction collapse", selected["warning"])

    def test_get_monitor_for_f2_policy(self):
        self.assertEqual(
            get_monitor_for_policy(CheckpointPolicyConfig(policy="f2")),
            ("val_f2_parasitized", "max"),
        )


if __name__ == "__main__":
    unittest.main()
