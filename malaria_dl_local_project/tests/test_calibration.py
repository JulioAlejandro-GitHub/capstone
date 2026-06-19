import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.calibration import (
    apply_temperature_scaling,
    calibrate_probability,
    calibration_params_from_file,
    fit_temperature_scaling,
)


class CalibrationTests(unittest.TestCase):
    def test_none_calibration_keeps_probability(self):
        result = calibrate_probability(0.73, method="none")

        self.assertFalse(result["applied"])
        self.assertEqual(result["method"], "none")
        self.assertAlmostEqual(result["calibrated_probability"], 0.73, places=6)

    def test_temperature_scaling_without_temperature_is_safe_placeholder(self):
        result = calibrate_probability(0.73, method="temperature_scaling")

        self.assertFalse(result["applied"])
        self.assertEqual(result["method"], "temperature_scaling")
        self.assertAlmostEqual(result["calibrated_probability"], 0.73, places=6)
        self.assertIn("warning", result)

    def test_temperature_scaling_with_file_metadata_is_applied(self):
        payload = {
            "method": "temperature_scaling",
            "temperature": 2.0,
            "calibration_file": "outputs/vgg16/calibration.json",
            "metrics": {"nll_before": 0.7, "nll_after": 0.6},
        }

        result = calibrate_probability(
            0.9,
            method="temperature_scaling",
            calibration_params=calibration_params_from_file(payload),
        )

        self.assertTrue(result["applied"])
        self.assertEqual(result["calibration_file"], "outputs/vgg16/calibration.json")
        self.assertAlmostEqual(result["params"]["temperature"], 2.0)

    def test_fit_temperature_scaling_returns_positive_temperature(self):
        y_true = [1, 1, 0, 0]
        raw_probabilities = [0.95, 0.80, 0.20, 0.05]

        result = fit_temperature_scaling(
            y_true,
            raw_probabilities,
            temperature_min=0.1,
            temperature_max=5.0,
            grid_size=20,
            refinement_rounds=1,
        )

        self.assertGreater(result["temperature"], 0.0)
        self.assertIn("nll_before", result["metrics"])
        self.assertIn("nll_after", result["metrics"])
        self.assertEqual(len(result["calibrated_probabilities"]), 4)

    def test_apply_temperature_scaling_preserves_shape(self):
        probabilities = [0.2, 0.8]

        calibrated = apply_temperature_scaling(probabilities, temperature=2.0)

        self.assertEqual(calibrated.shape, (2,))


if __name__ == "__main__":
    unittest.main()
