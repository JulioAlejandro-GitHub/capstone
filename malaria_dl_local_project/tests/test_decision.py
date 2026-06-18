import unittest
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.decision import (
    POSITIVE_LABEL,
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


if __name__ == "__main__":
    unittest.main()
