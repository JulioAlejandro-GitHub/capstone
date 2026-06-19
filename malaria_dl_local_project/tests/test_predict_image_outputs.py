import csv
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import predict_image


class PredictImageOutputsTests(unittest.TestCase):
    def test_external_predictions_csv_extends_columns_without_deleting_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "external_predictions.csv"
            csv_path.write_text("timestamp,image_path\nold,input.png\n", encoding="utf-8")

            original_path = predict_image.EXTERNAL_PREDICTIONS_CSV
            predict_image.EXTERNAL_PREDICTIONS_CSV = csv_path
            try:
                predict_image.append_external_prediction_csv(
                    {
                        "image_path": "input.png",
                        "stored_image_path": None,
                        "model_checkpoint": "outputs/vgg16/best_model.keras",
                        "model_name": "vgg16_transfer_learning",
                        "predicted_label": "parasitized",
                        "probability_parasitized": 0.9,
                        "probability_uninfected": 0.1,
                        "threshold": 0.5,
                        "confidence_level": "alta",
                        "decision_code": "compatible_con_celula_parasitada",
                        "human_readable_response": "Compatible con célula parasitada.",
                        "workflow": "clinical_inference_experimental",
                        "image": {
                            "original_path": "input.png",
                            "stored_path": None,
                            "quality": {"passed": True, "warnings": [], "metrics": {}},
                        },
                        "preprocessing": {"img_size": 200},
                        "model": {
                            "mode": "single_model",
                            "model_name": "vgg16_transfer_learning",
                            "tta_applied": False,
                            "n_aug": 0,
                            "ensemble_applied": False,
                            "ensemble_models": [],
                            "ensemble_weights": [],
                        },
                        "probabilities": {
                            "raw_model_score": 0.1,
                            "calibration": {
                                "method": "temperature_scaling",
                                "applied": True,
                                "calibration_file": "outputs/vgg16/calibration.json",
                                "params": {"temperature": 1.5},
                                "source": "calibration_file",
                            },
                        },
                        "decision": {
                            "decision_code": "compatible_con_celula_parasitada",
                            "human_readable_response": "Compatible con célula parasitada.",
                        },
                        "explainability": {"requested": False, "methods": [], "outputs": []},
                        "tracking": {"track_db": False, "prediction_id": None, "run_id": None},
                    }
                )
            finally:
                predict_image.EXTERNAL_PREDICTIONS_CSV = original_path

            with csv_path.open("r", newline="", encoding="utf-8") as file_handle:
                rows = list(csv.DictReader(file_handle))

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["timestamp"], "old")
        self.assertIn("workflow", rows[1])
        self.assertEqual(rows[1]["workflow"], "clinical_inference_experimental")
        self.assertEqual(rows[1]["calibration_applied"], "True")
        self.assertEqual(rows[1]["calibration_file"], "outputs/vgg16/calibration.json")
        self.assertEqual(rows[1]["calibration_temperature"], "1.5")


if __name__ == "__main__":
    unittest.main()
