import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.train import parse_args


class TrainIntegrationTests(unittest.TestCase):
    def test_train_accepts_checkpoint_policy_and_calibration_args(self):
        args = parse_args(
            [
                "--model",
                "custom_cnn",
                "--epochs",
                "30",
                "--img-size",
                "200",
                "--batch-size",
                "64",
                "--checkpoint-policy",
                "auc_with_min_recall",
                "--min-recall",
                "0.98",
                "--beta",
                "2.0",
                "--calibrate-threshold",
                "--target-recall",
                "0.98",
                "--track-db",
            ]
        )

        self.assertEqual(args.checkpoint_policy, "auc_with_min_recall")
        self.assertAlmostEqual(args.min_recall, 0.98)
        self.assertAlmostEqual(args.beta, 2.0)
        self.assertTrue(args.reject_prediction_collapse)
        self.assertTrue(args.calibrate_threshold)
        self.assertAlmostEqual(args.target_recall, 0.98)
        self.assertTrue(args.track_db)


if __name__ == "__main__":
    unittest.main()
