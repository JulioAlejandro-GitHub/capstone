import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.train import (  # noqa: E402
    parse_args,
    resolve_monitor_mode,
    uses_explicit_metric_checkpoint,
)


class MaxEpochsConfigTests(unittest.TestCase):
    def test_max_epochs_overrides_legacy_epochs(self):
        args = parse_args(
            [
                "--model",
                "custom_cnn",
                "--epochs",
                "5",
                "--max-epochs",
                "100",
            ]
        )

        self.assertEqual(args.max_epochs, 100)
        self.assertEqual(args.epochs, 100)
        self.assertEqual(args.epochs_legacy_requested, 5)
        self.assertEqual(args.epochs_source, "max_epochs")

    def test_epochs_is_used_as_legacy_alias(self):
        args = parse_args(["--model", "custom_cnn", "--epochs", "17"])

        self.assertEqual(args.max_epochs, 17)
        self.assertEqual(args.epochs, 17)
        self.assertEqual(args.epochs_source, "epochs_legacy")

    def test_model_default_is_used_when_epoch_flags_are_omitted(self):
        custom = parse_args(["--model", "custom_cnn"])
        transfer = parse_args(["--model", "vgg16"])

        self.assertEqual(custom.max_epochs, 50)
        self.assertEqual(transfer.max_epochs, 30)
        self.assertEqual(custom.epochs_source, "model_default")

    def test_training_controls_are_enabled_by_default(self):
        args = parse_args(["--model", "custom_cnn"])

        self.assertTrue(args.early_stopping)
        self.assertTrue(args.restore_best_weights)
        self.assertTrue(args.evaluate_best_on_test)
        self.assertAlmostEqual(args.early_stopping_min_delta, 0.0001)

    def test_training_controls_support_explicit_opt_out(self):
        args = parse_args(
            [
                "--model",
                "custom_cnn",
                "--no-early-stopping",
                "--no-restore-best-weights",
                "--no-evaluate-best-on-test",
            ]
        )

        self.assertFalse(args.early_stopping)
        self.assertFalse(args.restore_best_weights)
        self.assertFalse(args.evaluate_best_on_test)

    def test_skip_final_test_has_priority(self):
        args = parse_args(
            [
                "--model",
                "custom_cnn",
                "--evaluate-best-on-test",
                "--skip-final-test-evaluation",
            ]
        )

        self.assertFalse(args.evaluate_best_on_test)
        self.assertTrue(args.skip_final_test_evaluation)

    def test_checkpoint_mode_auto_uses_min_only_for_loss(self):
        self.assertEqual(resolve_monitor_mode("val_loss", "auto"), "min")
        self.assertEqual(
            resolve_monitor_mode("val_f2_parasitized", "auto"),
            "max",
        )
        self.assertEqual(resolve_monitor_mode("val_loss", "max"), "max")

    def test_explicit_mode_controls_checkpoint_even_without_monitor_flag(self):
        self.assertTrue(uses_explicit_metric_checkpoint(None, "min"))
        self.assertFalse(uses_explicit_metric_checkpoint(None, "max"))
        self.assertFalse(uses_explicit_metric_checkpoint(None, "auto"))


if __name__ == "__main__":
    unittest.main()
