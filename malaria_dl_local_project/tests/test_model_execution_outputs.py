import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.train import (  # noqa: E402
    acquire_training_output_lock,
    release_training_output_lock,
    resolve_artifact_snapshot_id,
    rewrite_snapshot_json_paths,
    snapshot_execution_artifacts,
    write_combined_training_history,
    write_model_execution_summary,
)


def fake_history(epoch_count, learning_rate):
    return SimpleNamespace(
        epoch=list(range(epoch_count)),
        history={
            "accuracy": [0.60 + index * 0.01 for index in range(epoch_count)],
            "val_accuracy": [0.58 + index * 0.01 for index in range(epoch_count)],
            "loss": [0.70 - index * 0.01 for index in range(epoch_count)],
            "val_loss": [0.72 - index * 0.01 for index in range(epoch_count)],
            "learning_rate": [learning_rate] * epoch_count,
        },
    )


class ModelExecutionOutputsTests(unittest.TestCase):
    def test_training_output_lock_rejects_concurrent_same_model_writer(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first_lock = acquire_training_output_lock(temp_dir)
            try:
                with self.assertRaisesRegex(
                    RuntimeError,
                    "otro entrenamiento activo",
                ):
                    acquire_training_output_lock(temp_dir)
            finally:
                release_training_output_lock(first_lock)

            second_lock = acquire_training_output_lock(temp_dir)
            release_training_output_lock(second_lock)

    def test_tracked_snapshot_uses_database_run_id_and_keeps_local_fallback(self):
        self.assertEqual(
            resolve_artifact_snapshot_id(
                "execution-id",
                {"run_id": "training-run-id"},
            ),
            "training-run-id",
        )
        self.assertEqual(
            resolve_artifact_snapshot_id("execution-id", {"run_id": None}),
            "execution-id",
        )

    def test_snapshot_json_paths_are_self_contained_but_cli_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "model"
            snapshot = root / "runs" / "execution-1"
            snapshot.mkdir(parents=True)
            metadata_path = snapshot / "model_metadata.json"
            metadata_path.write_text(
                json.dumps(
                    {
                        "combined_training_history": str(
                            root / "combined_training_history.csv"
                        ),
                        "checkpoint": str(root / "best_model.keras"),
                        "already_snapshot": str(snapshot / "combined_loss.png"),
                        "execution_parameters": {
                            "output_dir": str(root),
                            "cli_arguments": {"output_dir": str(root)},
                        },
                    }
                ),
                encoding="utf-8",
            )

            rewrite_snapshot_json_paths(snapshot, root)
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))

        self.assertEqual(
            payload["combined_training_history"],
            str(snapshot / "combined_training_history.csv"),
        )
        self.assertEqual(payload["checkpoint"], str(snapshot / "best_model.keras"))
        self.assertEqual(
            payload["already_snapshot"],
            str(snapshot / "combined_loss.png"),
        )
        self.assertEqual(
            payload["execution_parameters"]["output_dir"],
            str(snapshot),
        )
        self.assertEqual(
            payload["execution_parameters"]["cli_arguments"]["output_dir"],
            str(root),
        )

    def test_snapshot_copies_only_current_execution_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "model"
            root.mkdir()
            current = root / "combined_training_curves.png"
            stale = root / "threshold_calibration.json"
            current.write_bytes(b"current")
            stale.write_bytes(b"stale")

            snapshot_dir, copied = snapshot_execution_artifacts(
                root,
                "execution-1",
                artifact_paths=[current],
            )

            self.assertTrue((snapshot_dir / current.name).is_file())
            self.assertFalse((snapshot_dir / stale.name).exists())
            self.assertEqual(copied, [str(snapshot_dir / current.name)])

    def test_snapshot_preserves_required_checkpoint_lineage_artifacts(self):
        required_names = (
            "best_model.keras",
            "final_model.keras",
            "checkpoint_selection.json",
            "model_execution_summary.json",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "custom_cnn"
            root.mkdir()
            required_paths = []
            for name in required_names:
                path = root / name
                path.write_bytes(f"artifact:{name}".encode("utf-8"))
                required_paths.append(path)

            snapshot_dir, copied = snapshot_execution_artifacts(
                root,
                "training-run-id",
                artifact_paths=required_paths,
            )

            self.assertEqual(snapshot_dir, root / "runs" / "training-run-id")
            self.assertEqual(
                {Path(path).name for path in copied},
                set(required_names),
            )
            for name in required_names:
                self.assertTrue((snapshot_dir / name).is_file())

    def test_snapshot_rejects_different_artifacts_with_same_basename(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "model"
            first_dir = root / "first"
            second_dir = root / "second"
            first_dir.mkdir(parents=True)
            second_dir.mkdir(parents=True)
            first = first_dir / "metrics.json"
            second = second_dir / "metrics.json"
            first.write_text("first", encoding="utf-8")
            second.write_text("second", encoding="utf-8")

            with self.assertRaises(ValueError):
                snapshot_execution_artifacts(
                    root,
                    "execution-1",
                    artifact_paths=[first, second],
                )

    def test_combined_history_is_continuous_and_marks_boundary_epoch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path, marker_epoch, rows = write_combined_training_history(
                output_dir=temp_dir,
                base_history=fake_history(5, 1e-3),
                fine_tune_history=fake_history(6, 1e-5),
                base_learning_rate=1e-3,
                fine_tune_learning_rate=1e-5,
            )

            with Path(history_path).open(encoding="utf-8", newline="") as handle:
                csv_rows = list(csv.DictReader(handle))

        self.assertEqual([row["epoch"] for row in rows], list(range(11)))
        self.assertEqual([int(row["epoch"]) for row in csv_rows], list(range(11)))
        self.assertEqual([row["phase"] for row in rows[:5]], ["base"] * 5)
        self.assertEqual(
            [row["phase"] for row in rows[5:]],
            ["fine_tuning"] * 6,
        )
        # The marker identifies the first global 0-based fine-tuning epoch.
        self.assertEqual(marker_epoch, 5)

    def test_execution_summary_writes_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_model_execution_summary(
                temp_dir,
                {
                    "model_name": "densenet121",
                    "execution_type": "train_combined",
                    "parameters": {"batch_size": 64, "img_size": 200},
                    "base_epochs": 5,
                    "fine_tune_epochs": 6,
                    "completed_epochs": 11,
                    "fine_tuning_start_epoch": 4,
                    "best_epoch": 8,
                    "preprocessing": "rescale_0_1",
                    "positive_label": "parasitized",
                    "checkpoint_policy": "auc_with_min_recall",
                    "checkpoint_metric": "val_auc",
                    "artifacts": ["combined_training_history.csv"],
                    "plots": {"combined_training_curves": "curves.png"},
                    "run_id": "run-1",
                },
            )

            json_payload = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
            markdown = Path(paths["markdown"]).read_text(encoding="utf-8")

        self.assertEqual(json_payload["execution_type"], "train_combined")
        self.assertIn("Resumen de ejecución — densenet121", markdown)
        self.assertIn("combined_training_history.csv", markdown)


if __name__ == "__main__":
    unittest.main()
