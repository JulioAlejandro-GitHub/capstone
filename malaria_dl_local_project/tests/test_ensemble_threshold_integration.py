import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ensemble import (
    ENSEMBLE_CLINICAL_THRESHOLD_ERROR,
    parse_args,
    probability_rows_from_predictions,
    resolve_ensemble_threshold,
)
from src.decision import POSITIVE_LABEL
from src.metrics import clinical_predictions_from_raw_scores
from src.model_metadata import (
    build_model_metadata,
    update_model_metadata_with_clinical_threshold,
    write_model_metadata,
)


def calibration_result():
    return {
        "threshold_selected": 0.55,
        "threshold_source": "validation_calibration",
        "target_recall": 0.98,
        "target_recall_satisfied": True,
        "target_recall_satisfied_on_validation": True,
        "selected_metrics": {"specificity": 0.9},
    }


class EnsembleThresholdIntegrationTests(unittest.TestCase):
    def test_ensemble_applies_threshold_after_combining(self):
        rows = probability_rows_from_predictions(
            np.asarray([[0.2], [0.8]], dtype=np.float32)
        )
        averaged_score = float(np.mean([row[POSITIVE_LABEL] for row in rows]))
        prediction = clinical_predictions_from_raw_scores(
            [averaged_score],
            threshold=0.6,
        )

        self.assertAlmostEqual(averaged_score, 0.5)
        self.assertEqual(int(prediction[0]), 0)

    def test_ensemble_clinical_threshold_requires_explicit_metadata(self):
        with self.assertRaisesRegex(ValueError, "No clinical threshold found for ensemble"):
            resolve_ensemble_threshold("clinical", [Path("a.keras")])

    def test_ensemble_clinical_threshold_uses_explicit_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            metadata_checkpoint = output_dir / "ensemble_threshold_reference.keras"
            metadata_checkpoint.write_text("placeholder", encoding="utf-8")
            write_model_metadata(output_dir, build_model_metadata("ensemble"))
            update_model_metadata_with_clinical_threshold(
                metadata_checkpoint,
                calibration_result(),
            )

            info = resolve_ensemble_threshold(
                "clinical",
                [Path("a.keras")],
                threshold_metadata_checkpoint=metadata_checkpoint,
            )

        self.assertEqual(info["threshold_mode"], "clinical")
        self.assertAlmostEqual(info["threshold_used"], 0.55)

    def test_ensemble_parser_accepts_clinical_threshold(self):
        args = parse_args(["--models", "a.keras", "b.keras", "--threshold", "clinical"])

        self.assertEqual(args.threshold, "clinical")
        self.assertIsNone(args.threshold_metadata_checkpoint)
        self.assertIn("ensemble", ENSEMBLE_CLINICAL_THRESHOLD_ERROR)


if __name__ == "__main__":
    unittest.main()
