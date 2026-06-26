import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.threshold_calibration import (
    TEST_SET_CALIBRATION_ERROR,
    build_threshold_candidates,
    evaluate_threshold,
    find_threshold_for_target_recall,
    validate_calibration_split,
)


class ThresholdCalibrationTests(unittest.TestCase):
    def test_find_threshold_for_target_recall_satisfies_target_when_possible(self):
        y_true = [1, 1, 1, 0, 0, 0]
        y_scores = [0.90, 0.80, 0.20, 0.70, 0.10, 0.05]

        result = find_threshold_for_target_recall(
            y_true,
            y_scores,
            target_recall=0.98,
        )

        self.assertTrue(result["target_recall_satisfied"])
        self.assertAlmostEqual(result["threshold_selected"], 0.20, places=6)
        self.assertGreaterEqual(
            result["selected_metrics"]["recall_parasitized"],
            0.98,
        )
        self.assertEqual(result["threshold_source"], "validation_calibration")

    def test_find_threshold_uses_secondary_specificity_then_highest_threshold(self):
        y_true = [1, 1, 1, 0, 0, 0]
        y_scores = [0.90, 0.80, 0.20, 0.70, 0.10, 0.05]

        result = find_threshold_for_target_recall(
            y_true,
            y_scores,
            target_recall=2 / 3,
        )

        self.assertTrue(result["target_recall_satisfied"])
        self.assertAlmostEqual(result["threshold_selected"], 0.80, places=6)
        self.assertAlmostEqual(result["selected_metrics"]["specificity"], 1.0)

    def test_find_threshold_fallback_when_target_not_reached(self):
        y_true = [0, 0, 0]
        y_scores = [0.2, 0.4, 0.8]

        result = find_threshold_for_target_recall(
            y_true,
            y_scores,
            target_recall=0.98,
        )

        self.assertFalse(result["target_recall_satisfied"])
        self.assertIn("No threshold reached target_recall", result["warning"])

    def test_threshold_applied_to_probability_parasitized(self):
        metrics = evaluate_threshold(
            y_true=[1, 0],
            y_scores=[0.40, 0.60],
            threshold=0.50,
        )

        self.assertEqual(metrics["fn"], 1)
        self.assertEqual(metrics["fp"], 1)
        self.assertEqual(metrics["tp"], 0)
        self.assertEqual(metrics["tn"], 0)

    def test_build_threshold_candidates_includes_default_threshold(self):
        candidates = build_threshold_candidates([0.2, 0.8])

        self.assertIn(0.5, candidates)
        self.assertIn(0.0, candidates)
        self.assertIn(1.0, candidates)

    def test_test_set_cannot_be_used_for_calibration(self):
        with self.assertRaisesRegex(ValueError, TEST_SET_CALIBRATION_ERROR):
            validate_calibration_split("test")


if __name__ == "__main__":
    unittest.main()
