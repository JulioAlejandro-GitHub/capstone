import sys
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.train import parse_args, resolve_training_execution_type


class TrainIntegrationTests(unittest.TestCase):
    def test_execution_type_is_derived_from_fine_tune_epochs(self):
        self.assertEqual(resolve_training_execution_type(0), "train_base")
        self.assertEqual(resolve_training_execution_type(1), "train_combined")

    def test_train_accepts_densenet_combined_execution_parameters(self):
        args = parse_args(
            [
                "--model",
                "densenet121",
                "--epochs",
                "5",
                "--fine-tune-epochs",
                "6",
                "--learning-rate",
                "0.001",
                "--fine-tune-learning-rate",
                "0.00001",
                "--positive-label",
                "parasitized",
                "--pretrained-weights",
                "none",
            ]
        )

        self.assertEqual(args.model, "densenet121")
        self.assertEqual(args.fine_tune_epochs, 6)
        self.assertAlmostEqual(args.learning_rate, 0.001)
        self.assertAlmostEqual(args.fine_tune_learning_rate, 0.00001)
        self.assertEqual(args.positive_label, "parasitized")
        self.assertEqual(args.pretrained_weights, "none")

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

    def test_densenet_rejects_vgg16_preprocessing(self):
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            parse_args(
                [
                    "--model",
                    "densenet121",
                    "--preprocessing",
                    "vgg16_imagenet",
                ]
            )


if __name__ == "__main__":
    unittest.main()
