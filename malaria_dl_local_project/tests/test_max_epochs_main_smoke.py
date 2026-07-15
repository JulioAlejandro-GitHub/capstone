import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.checkpoint_policy import ClinicalCheckpointCallback  # noqa: E402
from src.train import main, parse_args  # noqa: E402


class FakeTrainModel:
    def summary(self):
        return None

    def save(self, path, overwrite=True):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fake keras model", encoding="utf-8")

    def fit(self, *_args, callbacks=None, **_kwargs):
        logs = {
            "loss": 0.60,
            "accuracy": 0.70,
            "auc": 0.80,
            "pr_auc": 0.79,
            "recall_parasitized": 0.75,
            "val_loss": 0.55,
            "val_accuracy": 0.74,
            "val_auc": 0.84,
            "val_pr_auc": 0.82,
            "val_recall_parasitized": 0.99,
            "val_f2_parasitized": 0.88,
            "val_specificity": 0.80,
            "val_balanced_accuracy": 0.895,
            "val_prediction_collapse_detected": 0.0,
            "learning_rate": 0.0001,
        }
        for callback in callbacks or []:
            if hasattr(callback, "set_model"):
                callback.set_model(self)
            if isinstance(callback, ClinicalCheckpointCallback):
                callback.on_epoch_end(0, logs)
        return SimpleNamespace(
            epoch=[0],
            history={key: [value] for key, value in logs.items()},
        )


def fake_plots(*, output_dir, **_kwargs):
    paths = {}
    for name in (
        "combined_accuracy",
        "combined_loss",
        "combined_training_curves",
    ):
        path = Path(output_dir) / f"{name}.png"
        path.write_bytes(b"png")
        paths[name] = str(path)
    return paths


class MaxEpochsMainSmokeTests(unittest.TestCase):
    def _run(self, output_dir, skip_test):
        argv = [
            "--model",
            "custom_cnn",
            "--max-epochs",
            "2",
            "--output-dir",
            str(output_dir),
        ]
        if skip_test:
            argv.append("--skip-final-test-evaluation")
        args = parse_args(argv)
        fake_metrics = {
            "accuracy": 0.95,
            "metrics": {"accuracy": 0.95, "recall_parasitized": 0.97},
            "classification_report_dict": {
                "parasitized": {"recall": 0.97}
            },
        }
        with patch("src.train.parse_args", return_value=args), patch(
            "src.train.dataset_tracking_metadata",
            return_value={"data_source": "physical", "dataset_name": "smoke"},
        ), patch(
            "src.train.load_malaria_splits",
            return_value=(object(), object(), object(), {}),
        ), patch(
            "src.train.build_custom_cnn",
            return_value=FakeTrainModel(),
        ), patch(
            "src.train.tf.keras.models.load_model",
            return_value=FakeTrainModel(),
        ), patch(
            "src.training_plots.plot_combined_training_curves",
            side_effect=fake_plots,
        ), patch(
            "src.train.evaluate_keras_model",
            return_value=fake_metrics,
        ) as evaluator, redirect_stdout(StringIO()):
            main()
        return evaluator

    def test_main_finalizes_single_test_evaluation_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "run"
            evaluator = self._run(output_dir, skip_test=False)
            checkpoint = json.loads(
                (output_dir / "checkpoint_selection.json").read_text(
                    encoding="utf-8"
                )
            )
            summary = json.loads(
                (output_dir / "model_execution_summary.json").read_text(
                    encoding="utf-8"
                )
            )

            evaluator.assert_called_once()
            self.assertTrue(checkpoint["test_evaluation_completed"])
            self.assertEqual(
                checkpoint["test_evaluation_policy"],
                "single_final_evaluation",
            )
            self.assertEqual(summary["completed_epochs"], 1)
            self.assertEqual(summary["best_epoch"], 1)
            self.assertTrue((output_dir / "test_metrics.json").is_file())
            self.assertFalse((output_dir / ".latest_backups").exists())

    def test_main_skip_does_not_evaluate_or_leave_test_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "run"
            output_dir.mkdir(parents=True)
            (output_dir / "test_metrics.json").write_text("stale", encoding="utf-8")
            evaluator = self._run(output_dir, skip_test=True)
            checkpoint = json.loads(
                (output_dir / "checkpoint_selection.json").read_text(
                    encoding="utf-8"
                )
            )

            evaluator.assert_not_called()
            self.assertFalse(checkpoint["test_evaluation_completed"])
            self.assertEqual(
                checkpoint["test_evaluation_policy"],
                "skipped_by_configuration",
            )
            self.assertFalse((output_dir / "test_metrics.json").exists())
            self.assertFalse((output_dir / ".latest_backups").exists())

    def test_main_failure_restores_previous_latest_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "run"
            output_dir.mkdir(parents=True)
            previous_best = output_dir / "best_model.keras"
            previous_metrics = output_dir / "test_metrics.json"
            previous_best.write_text("previous best", encoding="utf-8")
            previous_metrics.write_text("previous metrics", encoding="utf-8")
            args = parse_args(
                [
                    "--model",
                    "custom_cnn",
                    "--max-epochs",
                    "2",
                    "--output-dir",
                    str(output_dir),
                ]
            )

            with patch("src.train.parse_args", return_value=args), patch(
                "src.train.dataset_tracking_metadata",
                return_value={"data_source": "physical", "dataset_name": "smoke"},
            ), patch(
                "src.train.load_malaria_splits",
                side_effect=RuntimeError("synthetic data failure"),
            ), redirect_stdout(StringIO()):
                with self.assertRaisesRegex(RuntimeError, "synthetic data failure"):
                    main()

            self.assertEqual(
                previous_best.read_text(encoding="utf-8"),
                "previous best",
            )
            self.assertEqual(
                previous_metrics.read_text(encoding="utf-8"),
                "previous metrics",
            )
            self.assertFalse((output_dir / ".latest_backups").exists())

    def test_keyboard_interrupt_restores_previous_latest_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "run"
            output_dir.mkdir(parents=True)
            previous_best = output_dir / "best_model.keras"
            previous_best.write_text("previous best", encoding="utf-8")
            args = parse_args(
                [
                    "--model",
                    "custom_cnn",
                    "--max-epochs",
                    "2",
                    "--output-dir",
                    str(output_dir),
                ]
            )

            with patch("src.train.parse_args", return_value=args), patch(
                "src.train.dataset_tracking_metadata",
                return_value={"data_source": "physical", "dataset_name": "smoke"},
            ), patch(
                "src.train.load_malaria_splits",
                side_effect=KeyboardInterrupt(),
            ), redirect_stdout(StringIO()):
                with self.assertRaises(KeyboardInterrupt):
                    main()

            self.assertEqual(
                previous_best.read_text(encoding="utf-8"),
                "previous best",
            )
            self.assertFalse((output_dir / ".latest_backups").exists())


if __name__ == "__main__":
    unittest.main()
