import json
import sys
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import run_tracker  # noqa: E402
from src.tracking_integration import (  # noqa: E402
    finish_tracking_run,
    resolve_max_epochs_tracking_fields,
    start_tracking_run,
    update_execution_tracking,
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


class FakeMaxEpochsTracker:
    def __init__(self):
        self.execution_update = None
        self.finished = None

    def safe_track(self, function, *args, **kwargs):
        return function(*args, **kwargs)

    def update_run_execution(self, run_id, **kwargs):
        self.execution_update = (run_id, kwargs)
        return True

    def finish_run(self, run_id, **kwargs):
        self.finished = (run_id, kwargs)
        return True


class MaxEpochsTrackingTests(unittest.TestCase):
    def test_migration_is_incremental_and_declares_release_columns(self):
        migration = PROJECT_ROOT / "db" / "init" / "020_max_epochs_release.sql"
        sql = migration.read_text(encoding="utf-8")

        for column in (
            "max_epochs",
            "completed_epochs",
            "stopped_epoch",
            "best_epoch",
            "checkpoint_monitor",
            "checkpoint_mode",
            "best_validation_value",
            "early_stopping_enabled",
            "early_stopping_patience",
            "early_stopping_min_delta",
            "restore_best_weights",
        ):
            self.assertIn(f"ADD COLUMN IF NOT EXISTS {column}", sql)

        self.assertNotIn("DROP TABLE", sql)
        self.assertNotIn("TRUNCATE", sql)
        self.assertNotIn("DELETE FROM", sql)

    def test_resolver_accepts_nested_metadata_and_preserves_false(self):
        fields = resolve_max_epochs_tracking_fields(
            {
                "execution_parameters": {
                    "base_max_epochs": "80",
                    "total_max_epochs": "100",
                    "early_stopping": "false",
                    "early_stopping_patience": "12",
                    "early_stopping_min_delta": "0.0001",
                    "restore_best_weights": "true",
                    "checkpoint_monitor": "val_f2_parasitized",
                    "checkpoint_mode": "max",
                },
                "checkpoint_selection": {
                    "best_epoch": "25",
                    "stopped_epoch": "37",
                    "best_validation_value": "0.9721",
                },
            }
        )

        self.assertEqual(fields["max_epochs"], 80)
        self.assertEqual(fields["stopped_epoch"], 37)
        self.assertEqual(fields["best_epoch"], 25)
        self.assertEqual(fields["checkpoint_monitor"], "val_f2_parasitized")
        self.assertEqual(fields["checkpoint_mode"], "max")
        self.assertAlmostEqual(fields["best_validation_value"], 0.9721)
        self.assertFalse(fields["early_stopping_enabled"])
        self.assertEqual(fields["early_stopping_patience"], 12)
        self.assertAlmostEqual(fields["early_stopping_min_delta"], 0.0001)
        self.assertTrue(fields["restore_best_weights"])

    def test_start_tracking_materializes_max_epochs_configuration(self):
        args = Namespace(img_size=200, data_source="physical")
        parameters = {
            "epochs": 80,
            "fine_tune_epochs": 20,
            "max_epochs": 80,
            "checkpoint_monitor": "val_f2_parasitized",
            "checkpoint_mode": "max",
            "early_stopping": True,
            "early_stopping_patience": 12,
            "early_stopping_min_delta": 0.0001,
            "restore_best_weights": True,
        }

        with patch(
            "src.run_tracker.create_experiment", return_value="experiment-id"
        ), patch(
            "src.run_tracker.get_or_create_dataset", return_value="dataset-id"
        ), patch(
            "src.run_tracker.get_or_create_model", return_value="model-id"
        ), patch(
            "src.run_tracker.get_command_line", return_value="python -m src.train"
        ), patch("src.run_tracker.start_run", return_value="run-id") as start_run:
            context = start_tracking_run(
                args=args,
                run_type="training",
                script_name="src.train",
                model_name="densenet121",
                parameters=parameters,
            )

        kwargs = start_run.call_args.kwargs
        self.assertEqual(kwargs["max_epochs"], 80)
        self.assertEqual(kwargs["total_epochs"], 100)
        self.assertEqual(kwargs["checkpoint_monitor"], "val_f2_parasitized")
        self.assertTrue(kwargs["early_stopping_enabled"])
        self.assertTrue(kwargs["restore_best_weights"])
        self.assertEqual(kwargs["execution_parameters"]["max_epochs"], 80)
        self.assertTrue(
            kwargs["execution_parameters"]["early_stopping_enabled"]
        )
        self.assertEqual(context["max_epochs"], 80)

    def test_explicit_execution_parameters_override_legacy_parameters(self):
        args = Namespace(img_size=200, data_source="physical")
        with patch(
            "src.run_tracker.create_experiment", return_value="experiment-id"
        ), patch(
            "src.run_tracker.get_or_create_dataset", return_value="dataset-id"
        ), patch(
            "src.run_tracker.get_or_create_model", return_value="model-id"
        ), patch(
            "src.run_tracker.get_command_line", return_value="python -m src.train"
        ), patch("src.run_tracker.start_run", return_value="run-id") as start_run:
            start_tracking_run(
                args=args,
                run_type="training",
                script_name="src.train",
                model_name="densenet121",
                parameters={
                    "epochs": 30,
                    "fine_tune_epochs": 5,
                    "checkpoint_monitor": "val_loss",
                },
                execution_parameters={
                    "max_epochs": 80,
                    "fine_tune_epochs": 20,
                    "checkpoint_monitor": "val_f2_parasitized",
                },
            )

        kwargs = start_run.call_args.kwargs
        self.assertEqual(kwargs["max_epochs"], 80)
        self.assertEqual(kwargs["total_epochs"], 100)
        self.assertEqual(kwargs["checkpoint_monitor"], "val_f2_parasitized")

    def test_total_epochs_is_not_misreported_as_base_max_epochs(self):
        fields = resolve_max_epochs_tracking_fields(
            {"fine_tune_epochs": 20},
            total_epochs=100,
        )

        self.assertIsNone(fields["max_epochs"])

    def test_update_effective_parameters_override_context_fallback(self):
        tracker = FakeMaxEpochsTracker()
        context = {
            "run_id": "run-id",
            "tracker": tracker,
            "max_epochs": 80,
            "execution_parameters": {"max_epochs": 80},
        }

        update_execution_tracking(
            context,
            execution_parameters={"max_epochs": 90},
        )

        kwargs = tracker.execution_update[1]
        self.assertEqual(kwargs["max_epochs"], 90)
        self.assertEqual(kwargs["execution_parameters"]["max_epochs"], 90)
        self.assertEqual(context["max_epochs"], 90)

    def test_run_tracker_serializes_release_summary(self):
        with patch(
            "src.run_tracker.collect_runtime_environment",
            return_value=RUNTIME_ENVIRONMENT,
        ), patch(
            "src.run_tracker._execute_returning_id", return_value="run-id"
        ) as execute:
            result = run_tracker.start_run(
                run_type="training",
                max_epochs=100,
                stopped_epoch=37,
                best_epoch=25,
                checkpoint_monitor="val_f2_parasitized",
                checkpoint_mode="max",
                best_validation_value=0.9721,
                early_stopping_enabled=True,
                early_stopping_patience=12,
                early_stopping_min_delta=0.0001,
                restore_best_weights=True,
            )

        self.assertEqual(result, "run-id")
        sql, params = execute.call_args.args
        self.assertIn("best_validation_value", sql)
        self.assertEqual(params["max_epochs"], 100)
        self.assertEqual(params["stopped_epoch"], 37)
        self.assertEqual(params["best_epoch"], 25)
        self.assertAlmostEqual(params["best_validation_value"], 0.9721)
        self.assertTrue(params["early_stopping_enabled"])
        self.assertTrue(params["restore_best_weights"])
        self.assertEqual(json.loads(params["parameters"]), {})

    def test_update_and_finish_extract_final_values(self):
        tracker = FakeMaxEpochsTracker()
        context = {
            "run_id": "run-id",
            "tracker": tracker,
            "total_epochs": 100,
            "completed_epochs": 0,
            "execution_parameters": {
                "checkpoint_monitor": "val_f2_parasitized",
                "checkpoint_mode": "max",
                "early_stopping": True,
                "early_stopping_patience": 12,
                "early_stopping_min_delta": 0.0001,
                "restore_best_weights": True,
            },
        }

        update_execution_tracking(
            context,
            execution_parameters={
                **context["execution_parameters"],
                "max_epochs": 100,
                "stopped_epoch": 37,
                "best_epoch": 25,
                "best_validation_value": 0.9721,
            },
            completed_epochs=37,
        )

        update_kwargs = tracker.execution_update[1]
        self.assertEqual(update_kwargs["max_epochs"], 100)
        self.assertEqual(update_kwargs["stopped_epoch"], 37)
        self.assertEqual(update_kwargs["best_epoch"], 25)
        self.assertEqual(update_kwargs["completed_epochs"], 37)
        self.assertEqual(
            update_kwargs["execution_parameters"]["stopped_epoch"],
            37,
        )
        self.assertAlmostEqual(
            update_kwargs["execution_parameters"]["best_validation_value"],
            0.9721,
        )

        finish_tracking_run(
            context,
            metadata={
                "checkpoint_selection": {
                    "selected_epoch": 25,
                    "selected_metric_value": 0.9721,
                }
            },
        )

        finish_kwargs = tracker.finished[1]
        self.assertEqual(finish_kwargs["completed_epochs"], 37)
        self.assertEqual(finish_kwargs["max_epochs"], 100)
        self.assertEqual(finish_kwargs["stopped_epoch"], 37)
        self.assertEqual(finish_kwargs["best_epoch"], 25)
        self.assertAlmostEqual(finish_kwargs["best_validation_value"], 0.9721)


if __name__ == "__main__":
    unittest.main()
