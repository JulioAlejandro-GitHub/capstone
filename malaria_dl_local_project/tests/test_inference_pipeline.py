import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.inference_pipeline import (
    build_structured_clinical_response,
    normalize_ensemble_weights,
    preprocess_external_image,
)


class InferencePipelineTests(unittest.TestCase):
    def test_preprocess_external_image_returns_normalized_batch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "sample.png"
            Image.new("RGB", (96, 64), color=(100, 150, 200)).save(image_path)

            batch, image = preprocess_external_image(image_path, img_size=32)

        self.assertEqual(batch.shape, (1, 32, 32, 3))
        self.assertEqual(image.shape, (32, 32, 3))
        self.assertGreaterEqual(float(np.min(batch)), 0.0)
        self.assertLessEqual(float(np.max(batch)), 1.0)

    def test_normalize_ensemble_weights_defaults_to_equal_weights(self):
        weights = normalize_ensemble_weights(2)

        self.assertAlmostEqual(float(weights[0]), 0.5, places=6)
        self.assertAlmostEqual(float(weights[1]), 0.5, places=6)

    def test_structured_response_is_clinical_inference_workflow(self):
        flat_result = {
            "image_path": "input.png",
            "stored_image_path": "data/prediction_uploads/input.png",
        }
        response = build_structured_clinical_response(
            flat_result=flat_result,
            quality_result={"passed": True, "warnings": [], "metrics": {}},
            img_size=200,
            input_shape=(1, 200, 200, 3),
            model_info={
                "mode": "single_model",
                "checkpoint": "outputs/vgg16/best_model.keras",
                "model_name": "vgg16_transfer_learning",
                "tta_applied": False,
                "n_aug": 0,
                "ensemble_applied": False,
                "ensemble_models": [],
                "ensemble_weights": [],
            },
            probabilities={
                "probability_parasitized": 0.81,
                "probability_uninfected": 0.19,
                "raw_model_score": 0.19,
                "calibration": {"method": "none", "applied": False},
            },
            threshold=0.5,
        )

        self.assertEqual(response["workflow"], "clinical_inference_experimental")
        self.assertEqual(response["probabilities"]["probability_parasitized"], 0.81)
        self.assertEqual(response["decision"]["predicted_label"], "parasitized")
        self.assertIn("disclaimer", response)


if __name__ == "__main__":
    unittest.main()
