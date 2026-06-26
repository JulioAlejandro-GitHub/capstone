import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.model_metadata import (
    build_model_metadata,
    load_model_metadata_for_checkpoint,
    write_model_metadata,
)


class ModelMetadataIntegrationTests(unittest.TestCase):
    def test_model_metadata_contains_checkpoint_policy_and_clinical_threshold(self):
        metadata = build_model_metadata(
            "custom_cnn",
            extra={
                "checkpoint_policy": "auc_with_min_recall",
                "checkpoint_policy_config": {
                    "min_recall": 0.98,
                    "beta": 2.0,
                    "reject_prediction_collapse": True,
                    "min_class_fraction": 0.05,
                },
                "checkpoint_selection": {
                    "selected_epoch": 12,
                    "policy_satisfied": True,
                    "prediction_collapse_detected": False,
                },
            },
        )

        self.assertEqual(metadata["positive_class_index"], 1)
        self.assertEqual(metadata["raw_model_score_meaning"], "probability_parasitized")
        self.assertEqual(metadata["checkpoint_policy"], "auc_with_min_recall")
        self.assertFalse(metadata["clinical_threshold"]["enabled"])

    def test_write_model_metadata_merges_existing_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            checkpoint = output_dir / "best_model.keras"
            checkpoint.write_text("placeholder", encoding="utf-8")
            write_model_metadata(output_dir, {"existing_key": "keep"})
            metadata_path = write_model_metadata(
                output_dir,
                build_model_metadata("custom_cnn", extra={"new_key": "value"}),
            )
            loaded = load_model_metadata_for_checkpoint(checkpoint)

        self.assertEqual(metadata_path.name, "model_metadata.json")
        self.assertEqual(loaded["existing_key"], "keep")
        self.assertEqual(loaded["new_key"], "value")
        self.assertEqual(loaded["class_names"], ["uninfected", "parasitized"])

    def test_write_model_metadata_can_replace_existing_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            write_model_metadata(output_dir, {"old": True})
            write_model_metadata(output_dir, {"new": True}, merge_existing=False)
            data = json.loads((output_dir / "model_metadata.json").read_text())

        self.assertNotIn("old", data)
        self.assertTrue(data["new"])


if __name__ == "__main__":
    unittest.main()
