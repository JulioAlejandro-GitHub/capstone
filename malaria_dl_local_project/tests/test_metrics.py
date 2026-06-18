import csv
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.metrics import (
    clinical_predictions_from_raw_scores,
    evaluate_binary_predictions,
)


class ClinicalMetricsTests(unittest.TestCase):
    def test_clinical_predictions_use_parasitized_probability(self):
        predictions = clinical_predictions_from_raw_scores(
            [0.20, 0.70],
            class_names=["parasitized", "uninfected"],
            threshold=0.5,
        )

        self.assertEqual(predictions.tolist(), [0, 1])

    def test_metrics_are_computed_against_parasitized_positive_label(self):
        y_true = [0, 0, 1, 1]
        raw_model_score = [0.10, 0.80, 0.20, 0.90]
        input_y_pred = [0, 1, 0, 1]

        with tempfile.TemporaryDirectory() as temp_dir:
            metrics = evaluate_binary_predictions(
                y_true=y_true,
                y_pred=input_y_pred,
                y_score=raw_model_score,
                class_names=["parasitized", "uninfected"],
                output_dir=temp_dir,
                prefix="clinical",
                threshold=0.5,
            )

            csv_path = Path(temp_dir) / "clinical_predictions.csv"
            with csv_path.open("r", newline="", encoding="utf-8") as file_handle:
                rows = list(csv.DictReader(file_handle))

        self.assertEqual(metrics["clinical_positive_label"], "parasitized")
        self.assertAlmostEqual(metrics["sensitivity_parasitized"], 0.5)
        self.assertAlmostEqual(metrics["specificity"], 0.5)
        self.assertAlmostEqual(metrics["false_negative_rate"], 0.5)
        self.assertAlmostEqual(metrics["false_positive_rate"], 0.5)
        self.assertAlmostEqual(metrics["balanced_accuracy"], 0.5)
        self.assertAlmostEqual(metrics["auc_parasitized"], 0.75)

        self.assertAlmostEqual(float(rows[0]["raw_model_score"]), 0.1, places=6)
        self.assertAlmostEqual(float(rows[0]["probability_parasitized"]), 0.9, places=6)
        self.assertAlmostEqual(float(rows[0]["probability_uninfected"]), 0.1, places=6)
        self.assertEqual(rows[0]["predicted_label"], "parasitized")
        self.assertIn("raw_model_predicted_label", rows[0])


if __name__ == "__main__":
    unittest.main()
