import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.inference_pipeline import resolve_threshold
from src.model_metadata import (
    build_model_metadata,
    update_model_metadata_with_clinical_threshold,
    write_model_metadata,
)


def calibration_result():
    return {
        "threshold_selected": 0.42,
        "threshold_source": "validation_calibration",
        "target_recall": 0.98,
        "target_recall_satisfied": True,
        "target_recall_satisfied_on_validation": True,
        "selected_metrics": {"specificity": 0.88},
    }


class InferencePipelineThresholdTests(unittest.TestCase):
    def test_resolve_threshold_numeric(self):
        info = resolve_threshold(Path("model.keras"), "0.7")

        self.assertEqual(info["threshold_mode"], "fixed")
        self.assertEqual(info["threshold_source"], "fixed_cli")
        self.assertAlmostEqual(info["threshold_used"], 0.7)

    def test_resolve_threshold_clinical(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            checkpoint = output_dir / "best_model.keras"
            checkpoint.write_text("placeholder", encoding="utf-8")
            write_model_metadata(output_dir, build_model_metadata("custom_cnn"))
            update_model_metadata_with_clinical_threshold(
                checkpoint,
                calibration_result(),
            )

            info = resolve_threshold(checkpoint, "clinical")

        self.assertEqual(info["threshold_mode"], "clinical")
        self.assertAlmostEqual(info["threshold_used"], 0.42)
        self.assertAlmostEqual(info["expected_specificity"], 0.88)


if __name__ == "__main__":
    unittest.main()
