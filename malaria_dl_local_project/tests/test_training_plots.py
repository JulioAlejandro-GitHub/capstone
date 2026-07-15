import csv
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.training_plots import plot_combined_training_curves


class TrainingPlotsTests(unittest.TestCase):
    @staticmethod
    def _write_history(path: Path, include_fine_tuning: bool) -> None:
        rows = [
            {
                "epoch": 0,
                "phase": "base",
                "accuracy": 0.70,
                "val_accuracy": 0.68,
                "loss": 0.60,
                "val_loss": 0.63,
                "learning_rate": 0.001,
            },
            {
                "epoch": 1,
                "phase": "base",
                "accuracy": 0.78,
                "val_accuracy": 0.75,
                "loss": 0.48,
                "val_loss": 0.52,
                "learning_rate": 0.001,
            },
        ]
        if include_fine_tuning:
            rows.extend(
                [
                    {
                        "epoch": 2,
                        "phase": "fine_tuning",
                        "accuracy": 0.84,
                        "val_accuracy": 0.80,
                        "loss": 0.38,
                        "val_loss": 0.44,
                        "learning_rate": 0.00001,
                    },
                    {
                        "epoch": 3,
                        "phase": "fine_tuning",
                        "accuracy": 0.88,
                        "val_accuracy": 0.83,
                        "loss": 0.31,
                        "val_loss": 0.39,
                        "learning_rate": 0.00001,
                    },
                ]
            )

        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def _assert_generated_plots(self, plots: dict) -> None:
        self.assertEqual(
            set(plots),
            {
                "combined_accuracy",
                "combined_loss",
                "combined_training_curves",
            },
        )
        for plot_path in plots.values():
            with self.subTest(plot_path=plot_path):
                path = Path(plot_path)
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 0)

    def test_generates_plots_without_fine_tuning_marker(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            history_path = root / "combined_training_history.csv"
            self._write_history(history_path, include_fine_tuning=False)

            plots = plot_combined_training_curves(
                str(history_path),
                "CustomCNN",
                str(root / "plots"),
                fine_tuning_start_epoch=None,
            )

            self._assert_generated_plots(plots)

    def test_generates_plots_for_base_and_fine_tuning_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            history_path = root / "combined_training_history.csv"
            self._write_history(history_path, include_fine_tuning=True)

            plots = plot_combined_training_curves(
                str(history_path),
                "DenseNet121",
                str(root / "plots"),
                fine_tuning_start_epoch=1,
            )

            self._assert_generated_plots(plots)


if __name__ == "__main__":
    unittest.main()
