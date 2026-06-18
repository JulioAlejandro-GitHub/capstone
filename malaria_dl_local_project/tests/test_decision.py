import unittest
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.decision import (
    POSITIVE_LABEL,
    build_clinical_inference_response,
    classify_by_threshold,
    get_confidence_level,
    build_prediction_response,
    probabilities_by_class_from_prediction,
)


class DecisionTests(unittest.TestCase):
    def test_scalar_sigmoid_maps_to_clinical_probabilities(self):
        probabilities = probabilities_by_class_from_prediction([[0.25]])

        self.assertAlmostEqual(
            probabilities["parasitized"] + probabilities["uninfected"],
            1.0,
            places=6,
        )
        self.assertAlmostEqual(probabilities["parasitized"], 0.75, places=6)
        self.assertAlmostEqual(probabilities["uninfected"], 0.25, places=6)

    def test_positive_label_default_is_parasitized(self):
        self.assertEqual(POSITIVE_LABEL, "parasitized")

    def test_prediction_response_has_required_keys(self):
        response = build_prediction_response(
            image_path="input.png",
            stored_image_path="data/prediction_uploads/input.png",
            model_checkpoint="outputs/vgg16/best_model.keras",
            probability_parasitized=0.91,
            threshold=0.5,
            model_name="vgg16_transfer_learning",
        )

        for key in [
            "image_path",
            "stored_image_path",
            "model_checkpoint",
            "model_name",
            "predicted_label",
            "probability_parasitized",
            "probability_uninfected",
            "threshold",
            "confidence_level",
            "decision",
            "human_readable_response",
            "recommendation",
            "explainability",
            "tracking",
        ]:
            self.assertIn(key, response)

        self.assertEqual(response["predicted_label"], "parasitized")
        self.assertEqual(response["confidence_level"], "alta")

    def test_classify_by_threshold_uses_parasitized_as_positive(self):
        self.assertEqual(classify_by_threshold(0.50, threshold=0.5), "parasitized")
        self.assertEqual(classify_by_threshold(0.49, threshold=0.5), "uninfected")

    def test_confidence_level_is_symmetric_around_uncertain_zone(self):
        self.assertEqual(get_confidence_level(0.85), "alta")
        self.assertEqual(get_confidence_level(0.65), "media")
        self.assertEqual(get_confidence_level(0.50), "baja")
        self.assertEqual(get_confidence_level(0.35), "media")
        self.assertEqual(get_confidence_level(0.10), "alta")

    def test_clinical_response_contains_workflow_probabilities_and_disclaimer(self):
        response = build_clinical_inference_response(
            image={
                "original_path": "input.png",
                "stored_path": None,
                "quality": {"passed": True, "warnings": [], "metrics": {}},
            },
            preprocessing={
                "img_size": 200,
                "normalization": "[0, 1]",
                "input_shape": [1, 200, 200, 3],
            },
            model={
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
                "probability_parasitized": 0.72,
                "probability_uninfected": 0.28,
                "raw_model_score": 0.28,
                "calibration": {"method": "none", "applied": False},
            },
            threshold=0.5,
        )

        self.assertEqual(response["workflow"], "clinical_inference_experimental")
        self.assertEqual(response["decision"]["predicted_label"], "parasitized")
        self.assertIn("probability_parasitized", response["probabilities"])
        self.assertIn("disclaimer", response)

    def test_clinical_response_decision_uses_custom_threshold(self):
        response = build_clinical_inference_response(
            image={"original_path": "input.png", "stored_path": None, "quality": {}},
            preprocessing={"img_size": 200, "normalization": "[0, 1]", "input_shape": [1, 200, 200, 3]},
            model={"mode": "single_model"},
            probabilities={
                "probability_parasitized": 0.65,
                "probability_uninfected": 0.35,
                "raw_model_score": 0.35,
                "calibration": {"method": "none", "applied": False},
            },
            threshold=0.7,
        )

        self.assertEqual(response["decision"]["predicted_label"], "uninfected")
        self.assertEqual(
            response["decision"]["decision_code"],
            "compatible_con_celula_no_parasitada",
        )


if __name__ == "__main__":
    unittest.main()
