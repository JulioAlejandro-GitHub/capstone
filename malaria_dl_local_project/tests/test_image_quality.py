import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.image_quality import check_image_quality


class ImageQualityTests(unittest.TestCase):
    def test_missing_image_returns_controlled_failure(self):
        result = check_image_quality("no_existe.png")

        self.assertFalse(result["passed"])
        self.assertTrue(result["fatal"])
        self.assertTrue(result["warnings"])

    def test_valid_image_returns_metrics(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "sample.png"
            Image.new("RGB", (80, 80), color=(120, 90, 180)).save(image_path)

            result = check_image_quality(image_path)

        self.assertTrue(result["passed"])
        self.assertFalse(result["fatal"])
        self.assertEqual(result["metrics"]["width"], 80)
        self.assertEqual(result["metrics"]["height"], 80)
        self.assertEqual(result["metrics"]["channels"], 3)
        self.assertIn("brightness_mean", result["metrics"])
        self.assertIn("contrast_std", result["metrics"])
        self.assertIn("blur_score", result["metrics"])


if __name__ == "__main__":
    unittest.main()
