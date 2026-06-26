import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.train import parse_args


class TrainCheckpointPolicyArgsTests(unittest.TestCase):
    def test_train_cli_defaults_to_auc_with_min_recall(self):
        args = parse_args(["--model", "custom_cnn"])

        self.assertEqual(args.checkpoint_policy, "auc_with_min_recall")
        self.assertAlmostEqual(args.min_recall, 0.98)
        self.assertAlmostEqual(args.beta, 2.0)
        self.assertTrue(args.reject_prediction_collapse)
        self.assertAlmostEqual(args.min_class_fraction, 0.05)
        self.assertIsNone(args.checkpoint_monitor)

    def test_train_cli_accepts_f2_policy(self):
        args = parse_args(
            [
                "--model",
                "custom_cnn",
                "--checkpoint-policy",
                "f2",
                "--beta",
                "2.5",
            ]
        )

        self.assertEqual(args.checkpoint_policy, "f2")
        self.assertAlmostEqual(args.beta, 2.5)

    def test_allow_collapsed_checkpoint_disables_rejection(self):
        args = parse_args(
            [
                "--model",
                "custom_cnn",
                "--allow-collapsed-checkpoint",
            ]
        )

        self.assertFalse(args.reject_prediction_collapse)


if __name__ == "__main__":
    unittest.main()
