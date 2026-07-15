import json
import sys
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import run_tracker  # noqa: E402
from src.tracking_integration import (  # noqa: E402
    log_training_history,
    resolve_tracking_execution_type,
    resolve_tracking_total_epochs,
    start_tracking_run,
)


RUNTIME_ENVIRONMENT = {
    "user_name": "tester",
    "host_name": "localhost",
    "working_directory": str(PROJECT_ROOT),
    "git_commit": None,
    "git_branch": None,
    "python_version": "3.test",
    "tensorflow_version": None,
    "keras_version": None,
    "platform": "test",
    "machine": "test",
    "processor": "test",
    "gpu_available": False,
    "gpu_devices": [],
}


class FakeHistoryTracker:
    def __init__(self):
        self.execution_updates = []
        self.history_rows = []

    def safe_track(self, function, *args, **kwargs):
        return function(*args, **kwargs)

    def update_run_execution(self, run_id, **kwargs):
        self.execution_updates.append((run_id, kwargs))
        return True

    def log_training_history(self, run_id, epoch, **kwargs):
        self.history_rows.append((run_id, epoch, kwargs))
        return "history-id"


class ModelExecutionTrackingTests(unittest.TestCase):
    def test_finish_run_casts_optional_completed_epochs_for_postgres(self):
        with patch("src.run_tracker._execute", return_value=True) as execute:
            result = run_tracker.finish_run(
                "run-id",
                completed_epochs=None,
            )

        self.assertTrue(result)
        sql, params = execute.call_args.args
        self.assertIn("CAST(:completed_epochs AS integer) IS NULL", sql)
        self.assertIsNone(params["completed_epochs"])

    def test_resolves_canonical_execution_type_without_changing_run_type(self):
        self.assertEqual(
            resolve_tracking_execution_type("evaluation"),
            "evaluate",
        )
        self.assertEqual(
            resolve_tracking_execution_type("calibration"),
            "threshold_calibration",
        )
        self.assertEqual(
            resolve_tracking_execution_type(
                "training",
                {"epochs": 5, "fine_tune_epochs": 6},
            ),
            "train_combined",
        )
        self.assertEqual(
            resolve_tracking_execution_type(
                "training",
                {"fine_tune_epochs": 0},
                execution_type="train_base",
            ),
            "train_base",
        )

    def test_resolves_total_epochs_from_base_and_fine_tuning(self):
        self.assertEqual(
            resolve_tracking_total_epochs(
                {"epochs": 5, "fine_tune_epochs": 6},
            ),
            11,
        )
        self.assertEqual(
            resolve_tracking_total_epochs({"epochs": 5}, total_epochs=3),
            3,
        )

    def test_start_tracking_run_forwards_execution_contract(self):
        args = Namespace(
            img_size=200,
            data_source="tfds",
            epochs=5,
            fine_tune_epochs=6,
        )
        parameters = {
            "epochs": 5,
            "fine_tune_epochs": 6,
            "batch_size": 64,
        }

        with patch(
            "src.run_tracker.create_experiment",
            return_value="experiment-id",
        ), patch(
            "src.run_tracker.get_or_create_dataset",
            return_value="dataset-id",
        ), patch(
            "src.run_tracker.get_or_create_model",
            return_value="model-id",
        ), patch(
            "src.run_tracker.get_command_line",
            return_value="python -m src.train",
        ), patch(
            "src.run_tracker.start_run",
            return_value="run-id",
        ) as start_run_mock:
            context = start_tracking_run(
                args=args,
                run_type="training",
                script_name="src.train",
                model_name="densenet121",
                parameters=parameters,
                execution_type="train_combined",
                fine_tuning_start_epoch=4,
            )

        kwargs = start_run_mock.call_args.kwargs
        self.assertEqual(kwargs["run_type"], "training")
        self.assertEqual(kwargs["execution_type"], "train_combined")
        self.assertEqual(kwargs["total_epochs"], 11)
        self.assertEqual(kwargs["fine_tuning_start_epoch"], 4)
        self.assertEqual(kwargs["completed_epochs"], 0)
        self.assertEqual(kwargs["execution_parameters"]["batch_size"], 64)
        self.assertEqual(context["execution_type"], "train_combined")
        self.assertEqual(context["run_type"], "training")

    def test_run_tracker_start_run_serializes_new_columns(self):
        with patch(
            "src.run_tracker.collect_runtime_environment",
            return_value=RUNTIME_ENVIRONMENT,
        ), patch(
            "src.run_tracker._execute_returning_id",
            return_value="run-id",
        ) as execute:
            result = run_tracker.start_run(
                run_type="training",
                parameters={"epochs": 2},
                execution_type="train_base",
                execution_parameters={"epochs": 2, "batch_size": 32},
                total_epochs=2,
            )

        self.assertEqual(result, "run-id")
        sql, params = execute.call_args.args
        self.assertIn("execution_type", sql)
        self.assertIn("execution_parameters", sql)
        self.assertIn("fine_tuning_start_epoch", sql)
        self.assertIn("completed_epochs", sql)
        self.assertEqual(params["execution_type"], "train_base")
        self.assertEqual(json.loads(params["execution_parameters"])["batch_size"], 32)
        self.assertEqual(params["total_epochs"], 2)
        self.assertEqual(params["completed_epochs"], 0)

    def test_log_training_history_persists_phase_aliases_and_progress(self):
        with patch(
            "src.run_tracker._execute_returning_id",
            return_value="history-id",
        ) as execute:
            history_id = run_tracker.log_training_history(
                "run-id",
                epoch=3,
                phase="fine_tuning",
                train_loss=0.25,
                train_accuracy=0.91,
                val_loss=0.30,
                val_accuracy=0.89,
                learning_rate=1e-5,
            )

        self.assertEqual(history_id, "history-id")
        sql, params = execute.call_args.args
        self.assertIn("phase, loss, train_loss, accuracy, train_accuracy", sql)
        self.assertIn("completed_epochs", sql)
        self.assertEqual(params["phase"], "fine_tuning")
        self.assertEqual(params["loss"], 0.25)
        self.assertEqual(params["accuracy"], 0.91)
        self.assertEqual(params["train_loss"], 0.25)
        self.assertEqual(params["train_accuracy"], 0.91)
        self.assertEqual(params["learning_rate"], 1e-5)
        self.assertEqual(json.loads(params["metadata"])["phase"], "fine_tuning")

    def test_integration_records_actual_fine_tuning_start_and_epoch_metrics(self):
        tracker = FakeHistoryTracker()
        context = {
            "run_id": "run-id",
            "tracker": tracker,
            "fine_tuning_start_epoch": None,
            "completed_epochs": 2,
        }
        history = SimpleNamespace(
            epoch=[0],
            history={
                "loss": [0.25],
                "accuracy": [0.91],
                "val_loss": [0.30],
                "val_accuracy": [0.89],
                "learning_rate": [1e-5],
            },
        )

        log_training_history(
            context,
            history,
            phase="fine_tuning",
            epoch_offset=2,
        )

        self.assertEqual(
            tracker.execution_updates[0][1]["fine_tuning_start_epoch"],
            2,
        )
        _, epoch, values = tracker.history_rows[0]
        self.assertEqual(epoch, 2)
        self.assertEqual(values["phase"], "fine_tuning")
        self.assertEqual(values["loss"], 0.25)
        self.assertEqual(values["val_accuracy"], 0.89)
        self.assertEqual(values["learning_rate"], 1e-5)
        self.assertEqual(context["completed_epochs"], 3)

    def test_safe_track_swallows_tracking_failure(self):
        def fail():
            raise RuntimeError("database unavailable")

        with self.assertWarns(RuntimeWarning):
            result = run_tracker.safe_track(fail)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
