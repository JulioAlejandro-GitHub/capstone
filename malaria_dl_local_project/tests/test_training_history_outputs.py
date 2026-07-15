import csv
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.train import write_combined_training_history  # noqa: E402


REQUIRED_COLUMNS = {
    "epoch",
    "phase",
    "loss",
    "accuracy",
    "val_loss",
    "val_accuracy",
    "auc",
    "val_auc",
    "pr_auc",
    "val_pr_auc",
    "recall_parasitized",
    "val_recall_parasitized",
    "f2_parasitized",
    "val_f2_parasitized",
    "learning_rate",
}


def fake_history(epoch_count, include_clinical=True):
    history = {
        "loss": [0.7 - 0.05 * index for index in range(epoch_count)],
        "accuracy": [0.6 + 0.05 * index for index in range(epoch_count)],
        "val_loss": [0.75 - 0.04 * index for index in range(epoch_count)],
        "val_accuracy": [0.58 + 0.04 * index for index in range(epoch_count)],
        "learning_rate": [0.0001] * epoch_count,
    }
    if include_clinical:
        history.update(
            {
                "auc": [0.70 + 0.02 * index for index in range(epoch_count)],
                "val_auc": [0.68 + 0.02 * index for index in range(epoch_count)],
                "pr_auc": [0.69 + 0.02 * index for index in range(epoch_count)],
                "val_pr_auc_parasitized": [
                    0.67 + 0.02 * index for index in range(epoch_count)
                ],
                "recall_parasitized": [0.80] * epoch_count,
                "val_recall_parasitized": [0.79] * epoch_count,
                "val_f2_parasitized": [0.78] * epoch_count,
            }
        )
    return SimpleNamespace(epoch=list(range(epoch_count)), history=history)


class TrainingHistoryOutputsTests(unittest.TestCase):
    def test_history_contains_required_columns_and_canonical_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            combined_path, marker, rows = write_combined_training_history(
                temp_dir,
                fake_history(2),
            )
            canonical_path = Path(temp_dir) / "training_history.csv"
            with canonical_path.open(encoding="utf-8", newline="") as handle:
                csv_rows = list(csv.DictReader(handle))

            self.assertTrue(Path(combined_path).is_file())
            self.assertTrue(canonical_path.is_file())
            self.assertIsNone(marker)
            self.assertEqual(len(rows), 2)
            self.assertTrue(REQUIRED_COLUMNS.issubset(csv_rows[0]))
            self.assertEqual(csv_rows[0]["val_pr_auc"], "0.67")

    def test_missing_optional_metrics_do_not_block_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, _, rows = write_combined_training_history(
                temp_dir,
                fake_history(1, include_clinical=False),
            )

        self.assertIsNone(rows[0]["auc"])
        self.assertIsNone(rows[0]["val_f2_parasitized"])

    def test_fine_tuning_epochs_are_continuous_and_marker_is_first_ft_epoch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, marker, rows = write_combined_training_history(
                temp_dir,
                fake_history(3),
                fine_tune_history=fake_history(2),
            )

        self.assertEqual([row["epoch"] for row in rows], [0, 1, 2, 3, 4])
        self.assertEqual([row["phase"] for row in rows], ["base"] * 3 + ["fine_tuning"] * 2)
        self.assertEqual(marker, 3)


if __name__ == "__main__":
    unittest.main()
