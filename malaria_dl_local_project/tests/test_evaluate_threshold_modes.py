import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import evaluate
from src.model_metadata import (
    build_model_metadata,
    update_model_metadata_with_clinical_threshold,
    write_model_metadata,
)


def calibration_result(threshold=0.32):
    return {
        "threshold_policy": "target_recall",
        "threshold_source": "validation_calibration",
        "threshold_selected": threshold,
        "default_threshold": 0.5,
        "target_recall": 0.98,
        "target_recall_satisfied": True,
        "target_recall_satisfied_on_validation": True,
        "selected_metrics": {
            "recall_parasitized": 0.981,
            "specificity": 0.91,
            "precision_parasitized": 0.93,
            "f2_parasitized": 0.97,
            "balanced_accuracy": 0.945,
        },
    }


class EvaluateThresholdModeTests(unittest.TestCase):
    def test_evaluate_accepts_numeric_threshold(self):
        args = evaluate.parse_args(["--checkpoint", "model.keras", "--threshold", "0.5"])
        info = evaluate.resolve_threshold_for_checkpoint(args.threshold, Path("model.keras"))

        self.assertEqual(info["threshold_mode"], "fixed")
        self.assertEqual(info["threshold_source"], "fixed_cli")
        self.assertAlmostEqual(info["threshold_used"], 0.5)

    def test_evaluate_accepts_clinical_threshold_from_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            checkpoint = output_dir / "best_model.keras"
            checkpoint.write_text("placeholder", encoding="utf-8")
            write_model_metadata(output_dir, build_model_metadata("custom_cnn"))
            update_model_metadata_with_clinical_threshold(
                checkpoint,
                calibration_result(),
            )

            info = evaluate.resolve_threshold_for_checkpoint("clinical", checkpoint)

        self.assertEqual(info["threshold_mode"], "clinical")
        self.assertEqual(info["threshold_source"], "validation_calibration")
        self.assertAlmostEqual(info["threshold_used"], 0.32)
        self.assertAlmostEqual(info["expected_specificity"], 0.91)

    def test_evaluate_threshold_clinical_fails_without_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint = Path(temp_dir) / "best_model.keras"
            checkpoint.write_text("placeholder", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "No clinical threshold found"):
                evaluate.resolve_threshold_for_checkpoint("clinical", checkpoint)


if __name__ == "__main__":
    unittest.main()
