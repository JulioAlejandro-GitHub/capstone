import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import predict_image
from src.model_metadata import (
    build_model_metadata,
    update_model_metadata_with_clinical_threshold,
    write_model_metadata,
)


def calibration_result(threshold=0.6):
    return {
        "threshold_policy": "target_recall",
        "threshold_source": "validation_calibration",
        "threshold_selected": threshold,
        "default_threshold": 0.5,
        "target_recall": 0.98,
        "target_recall_satisfied": True,
        "target_recall_satisfied_on_validation": True,
        "selected_metrics": {"specificity": 0.9, "f2_parasitized": 0.96},
    }


class PredictImageThresholdModeTests(unittest.TestCase):
    def test_predict_image_uses_clinical_threshold_from_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            checkpoint = output_dir / "best_model.keras"
            checkpoint.write_text("placeholder", encoding="utf-8")
            write_model_metadata(output_dir, build_model_metadata("custom_cnn"))
            update_model_metadata_with_clinical_threshold(
                checkpoint,
                calibration_result(threshold=0.6),
            )
            args = predict_image.build_inference_args(
                checkpoint=str(checkpoint),
                image_path="sample.png",
                threshold="clinical",
            )
            args.threshold_info = predict_image.resolve_threshold_for_checkpoint(
                args.threshold,
                checkpoint,
            )
            args.threshold = args.threshold_info["threshold_used"]

            result = predict_image.build_result(
                args,
                image_path="sample.png",
                stored_image=None,
                checkpoint=checkpoint,
                prediction_result={
                    "probability_parasitized": 0.55,
                    "probability_uninfected": 0.45,
                    "raw_model_output": [[0.55]],
                    "raw_model_score": 0.55,
                    "tta_predictions": None,
                    "calibration": {"method": "none", "applied": False},
                },
            )

        self.assertEqual(result["predicted_label"], "uninfected")
        self.assertAlmostEqual(result["threshold_used"], 0.6)
        self.assertEqual(result["threshold_source"], "validation_calibration")
        self.assertTrue(result["clinical_threshold"]["enabled"])


if __name__ == "__main__":
    unittest.main()
