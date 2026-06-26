import argparse
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import ensemble, evaluate, predict_image, tta
from src.decision import NEGATIVE_LABEL, POSITIVE_LABEL
from src.metrics import clinical_predictions_from_raw_scores
from src.model_metadata import (
    build_model_metadata,
    update_model_metadata_with_clinical_threshold,
    write_model_metadata,
)


def calibration_result(threshold=0.6):
    return {
        "threshold_policy": "target_recall",
        "threshold_source": "validation_calibration",
        "threshold_selected": threshold,
        "default_threshold": 0.5,
        "target_recall": 0.98,
        "target_recall_satisfied": True,
        "target_recall_satisfied_on_validation": True,
        "selected_metrics": {
            "recall_parasitized": 0.98,
            "specificity": 0.9,
            "precision_parasitized": 0.92,
            "f2_parasitized": 0.96,
            "balanced_accuracy": 0.94,
        },
        "default_threshold_metrics": {
            "threshold": 0.5,
            "recall_parasitized": 0.94,
            "specificity": 0.96,
            "f2_parasitized": 0.946,
        },
    }


def checkpoint_with_threshold(temp_dir, threshold=0.6):
    output_dir = Path(temp_dir)
    checkpoint = output_dir / "best_model.keras"
    checkpoint.write_text("placeholder", encoding="utf-8")
    write_model_metadata(output_dir, build_model_metadata("custom_cnn"))
    update_model_metadata_with_clinical_threshold(
        checkpoint,
        calibration_result(threshold=threshold),
    )
    return checkpoint


class StaticModel:
    def __init__(self, scores):
        self.scores = list(scores)

    def predict(self, batch, verbose=0):
        if len(self.scores) == 1:
            return np.asarray([[self.scores[0]]], dtype=np.float32)
        score = self.scores.pop(0)
        return np.asarray([[score]], dtype=np.float32)


class ThresholdClinicalModeTests(unittest.TestCase):
    def test_evaluate_parse_args_accepts_clinical_threshold(self):
        args = evaluate.parse_args(
            ["--checkpoint", "model.keras", "--threshold", "clinical"]
        )

        self.assertEqual(args.threshold, "clinical")

    def test_evaluate_threshold_clinical_fails_without_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint = Path(temp_dir) / "best_model.keras"
            checkpoint.write_text("placeholder", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "No clinical threshold found"):
                evaluate.resolve_threshold_for_checkpoint("clinical", checkpoint)

    def test_predict_image_threshold_clinical_uses_metadata_threshold(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint = checkpoint_with_threshold(temp_dir, threshold=0.6)
            args = predict_image.build_inference_args(
                checkpoint=str(checkpoint),
                image_path="sample.png",
                threshold="clinical",
            )
            args.threshold_info = predict_image.resolve_threshold_for_checkpoint(
                args.threshold,
                checkpoint,
            )
            args.threshold = args.threshold_info["threshold_used"]

            result = predict_image.build_result(
                args,
                image_path="sample.png",
                stored_image=None,
                checkpoint=checkpoint,
                prediction_result={
                    "probability_parasitized": 0.55,
                    "probability_uninfected": 0.45,
                    "raw_model_output": [[0.55]],
                    "raw_model_score": 0.55,
                    "tta_predictions": None,
                    "calibration": {"method": "none", "applied": False},
                },
            )

        self.assertEqual(result["predicted_label"], NEGATIVE_LABEL)
        self.assertAlmostEqual(result["threshold"], 0.6)
        self.assertEqual(result["threshold_source"], "validation_calibration")
        self.assertTrue(result["clinical_threshold"]["enabled"])

    def test_tta_applies_threshold_after_averaging_scores(self):
        model = StaticModel([0.2, 0.8])
        image = np.zeros((8, 8, 3), dtype=np.float32)
        score = tta.predict_with_tta(
            model,
            image,
            augmentation=lambda value, training=True: value,
            n_aug=1,
        )
        y_pred = clinical_predictions_from_raw_scores([score], threshold=0.6)

        self.assertAlmostEqual(score, 0.5)
        self.assertEqual(int(y_pred[0]), 0)

    def test_ensemble_applies_threshold_after_combining_scores(self):
        result = ensemble.probability_rows_from_predictions(
            np.asarray([[0.2], [0.8]], dtype=np.float32)
        )
        averaged_score = float(np.mean([row[POSITIVE_LABEL] for row in result]))
        y_pred = clinical_predictions_from_raw_scores([averaged_score], threshold=0.6)

        self.assertAlmostEqual(averaged_score, 0.5)
        self.assertEqual(int(y_pred[0]), 0)

    def test_cli_parsers_accept_clinical_threshold(self):
        tta_args = tta.parse_args(["--checkpoint", "model.keras", "--threshold", "clinical"])
        ensemble_args = ensemble.parse_args(
            ["--models", "a.keras", "b.keras", "--threshold", "clinical"]
        )

        self.assertEqual(tta_args.threshold, "clinical")
        self.assertEqual(ensemble_args.threshold, "clinical")


if __name__ == "__main__":
    unittest.main()
