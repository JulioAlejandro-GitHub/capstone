import sys
import unittest
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.explain import (
    get_case_type,
    make_summary_row,
    parse_args,
    predicted_labels_from_scores,
)


class ExplainThresholdIntegrationTests(unittest.TestCase):
    def test_explain_case_type_uses_threshold_used(self):
        y_score = np.asarray([0.61, 0.59], dtype=np.float32)
        y_pred = predicted_labels_from_scores(
            y_score,
            positive_idx=1,
            negative_idx=0,
            threshold=0.6,
        )

        self.assertEqual(int(y_pred[0]), 1)
        self.assertEqual(int(y_pred[1]), 0)
        self.assertEqual(get_case_type(1, int(y_pred[0]), 1, 0), "true_positive")
        self.assertEqual(get_case_type(1, int(y_pred[1]), 1, 0), "false_negative")

    def test_explain_parser_accepts_clinical_threshold(self):
        args = parse_args(
            [
                "--checkpoint",
                "model.keras",
                "--method",
                "gradcam",
                "--threshold",
                "clinical",
            ]
        )

        self.assertEqual(args.threshold, "clinical")

    def test_explanation_summary_includes_threshold_source(self):
        row = make_summary_row(
            {
                "case_id": 1,
                "case_type": "true_positive",
                "true_label": "parasitized",
                "predicted_label": "parasitized",
                "probability_parasitized": 0.8,
                "score_positive_label": 0.8,
                "positive_label": "parasitized",
                "threshold": 0.6,
                "threshold_used": 0.6,
                "threshold_source": "validation_calibration",
            },
            method="gradcam",
            image_path=Path("out.png"),
            success=True,
        )

        self.assertAlmostEqual(row["threshold_used"], 0.6)
        self.assertEqual(row["threshold_source"], "validation_calibration")


if __name__ == "__main__":
    unittest.main()
