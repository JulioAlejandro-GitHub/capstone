import sys
import unittest
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.metrics import clinical_predictions_from_raw_scores
from src.tta import parse_args, predict_with_tta


class StaticModel:
    def __init__(self, scores):
        self.scores = list(scores)

    def predict(self, batch, verbose=0):
        score = self.scores.pop(0)
        return np.asarray([[score]], dtype=np.float32)


class TTAThresholdIntegrationTests(unittest.TestCase):
    def test_tta_applies_threshold_after_averaging(self):
        model = StaticModel([0.2, 0.8])
        image = np.zeros((8, 8, 3), dtype=np.float32)
        score = predict_with_tta(
            model,
            image,
            augmentation=lambda value, training=True: value,
            n_aug=1,
        )
        prediction = clinical_predictions_from_raw_scores([score], threshold=0.6)

        self.assertAlmostEqual(score, 0.5)
        self.assertEqual(int(prediction[0]), 0)

    def test_tta_parser_accepts_clinical_threshold(self):
        args = parse_args(["--checkpoint", "model.keras", "--threshold", "clinical"])

        self.assertEqual(args.threshold, "clinical")


if __name__ == "__main__":
    unittest.main()
