import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.metrics import detect_prediction_collapse


class PredictionCollapseTests(unittest.TestCase):
    def test_prediction_collapse_all_parasitized(self):
        result = detect_prediction_collapse([1, 1, 1, 1])

        self.assertTrue(result["collapsed"])
        self.assertEqual(result["predicted_classes"], ["parasitized"])
        self.assertEqual(result["n_pred_uninfected"], 0)
        self.assertEqual(result["n_pred_parasitized"], 4)
        self.assertEqual(result["percent_pred_uninfected"], 0.0)
        self.assertEqual(result["percent_pred_parasitized"], 1.0)
        self.assertIn("solo una clase", result["warning"])

    def test_prediction_distribution_balanced_is_not_collapse(self):
        result = detect_prediction_collapse([0, 1, 0, 1])

        self.assertFalse(result["collapsed"])
        self.assertEqual(result["n_pred_uninfected"], 2)
        self.assertEqual(result["n_pred_parasitized"], 2)


if __name__ == "__main__":
    unittest.main()
