import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.model_metadata import (
    build_model_metadata,
    load_clinical_threshold_for_checkpoint,
    resolve_threshold_for_checkpoint,
    update_model_metadata_with_clinical_threshold,
    write_model_metadata,
)


def calibration_result():
    return {
        "threshold_policy": "target_recall",
        "threshold_source": "validation_calibration",
        "threshold_selected": 0.32,
        "default_threshold": 0.5,
        "target_recall": 0.98,
        "target_recall_satisfied": True,
        "target_recall_satisfied_on_validation": True,
        "selected_metrics": {
            "recall_parasitized": 0.981,
            "sensitivity_parasitized": 0.981,
            "specificity": 0.91,
            "precision_parasitized": 0.93,
            "f2_parasitized": 0.97,
            "balanced_accuracy": 0.945,
            "pr_auc_parasitized": 0.978,
            "roc_auc_parasitized": 0.982,
        },
        "default_threshold_metrics": {
            "threshold": 0.5,
            "recall_parasitized": 0.94,
            "specificity": 0.96,
            "f2_parasitized": 0.946,
        },
        "warning": None,
    }


class ModelMetadataThresholdTests(unittest.TestCase):
    def test_clinical_threshold_loaded_from_model_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            checkpoint = output_dir / "best_model.keras"
            checkpoint.write_text("placeholder", encoding="utf-8")
            write_model_metadata(
                output_dir,
                build_model_metadata("custom_cnn"),
            )

            update_model_metadata_with_clinical_threshold(
                checkpoint,
                calibration_result(),
            )
            threshold = load_clinical_threshold_for_checkpoint(checkpoint)

        self.assertAlmostEqual(threshold["threshold_selected"], 0.32)
        self.assertEqual(threshold["threshold_source"], "validation_calibration")
        self.assertEqual(threshold["validation_metrics_at_threshold"]["specificity"], 0.91)

    def test_resolve_threshold_for_checkpoint_supports_fixed_and_clinical(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            checkpoint = output_dir / "best_model.keras"
            checkpoint.write_text("placeholder", encoding="utf-8")
            write_model_metadata(output_dir, build_model_metadata("custom_cnn"))
            update_model_metadata_with_clinical_threshold(
                checkpoint,
                calibration_result(),
            )

            fixed = resolve_threshold_for_checkpoint("0.7", checkpoint)
            clinical = resolve_threshold_for_checkpoint("clinical", checkpoint)

        self.assertEqual(fixed["threshold_mode"], "fixed")
        self.assertAlmostEqual(fixed["threshold_used"], 0.7)
        self.assertEqual(clinical["threshold_mode"], "clinical")
        self.assertAlmostEqual(clinical["threshold_used"], 0.32)

    def test_clinical_threshold_fails_without_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint = Path(temp_dir) / "best_model.keras"
            checkpoint.write_text("placeholder", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "No clinical threshold found"):
                resolve_threshold_for_checkpoint("clinical", checkpoint)


if __name__ == "__main__":
    unittest.main()
