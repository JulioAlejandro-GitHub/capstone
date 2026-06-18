import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.calibration import calibrate_probability


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


if __name__ == "__main__":
    unittest.main()
