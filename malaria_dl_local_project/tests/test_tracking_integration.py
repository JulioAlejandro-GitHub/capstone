import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.tracking_integration import (  # noqa: E402
    build_run_dataset_image_rows,
    record_run_dataset_images,
)


class FakeTracker:
    def __init__(self):
        self.rows = None

    def safe_track(self, function, *args, **kwargs):
        return function(*args, **kwargs)

    def log_run_dataset_images(self, run_id, rows):
        self.run_id = run_id
        self.rows = rows
        return {"total": len(rows), "inserted_or_updated": len(rows)}


class TrackingIntegrationTests(unittest.TestCase):
    def test_build_run_dataset_image_rows_sets_flags_and_metadata(self):
        rows = build_run_dataset_image_rows(
            [
                {
                    "image_id": "image-1",
                    "dataset_dir": "/tmp/split",
                    "split_name": "test",
                    "class_index": 1,
                    "class_name": "parasitized",
                    "relative_path": "test/parasitized/000001.png",
                    "filename": "000001.png",
                    "label_mapping_version": "clinical_v1_parasitized_positive",
                }
            ],
            usage_context="explainability",
            metadata_by_sample_index={
                0: {
                    "case_type": "true_positive",
                    "explainability_method": "gradcam",
                }
            },
            batch_size=64,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["usage_context"], "explainability")
        self.assertTrue(rows[0]["used_for_test"])
        self.assertFalse(rows[0]["used_for_training"])
        self.assertEqual(rows[0]["sample_index"], 0)
        self.assertEqual(rows[0]["batch_index"], 0)
        self.assertEqual(rows[0]["metadata"]["case_type"], "true_positive")

    def test_record_run_dataset_images_uses_registry_and_tracker(self):
        tracker = FakeTracker()
        context = {"run_id": "run-uuid", "tracker": tracker}
        dataset_info = {
            "data_source": "physical",
            "dataset_dir": "/tmp/malaria_physical_split",
        }
        registered_images = [
            {
                "image_id": "image-1",
                "dataset_dir": "/tmp/malaria_physical_split",
                "split_name": "test",
                "class_index": 0,
                "class_name": "uninfected",
                "relative_path": "test/uninfected/000001.png",
                "filename": "000001.png",
                "label_mapping_version": "clinical_v1_parasitized_positive",
            }
        ]

        with patch(
            "src.dataset_registry.register_physical_split_images",
            return_value={"total": 1},
        ) as register_mock, patch(
            "src.dataset_registry.load_registered_split_images",
            return_value=registered_images,
        ) as load_mock:
            result = record_run_dataset_images(
                context,
                dataset_info=dataset_info,
                usage_context="evaluation",
                splits=["test"],
                batch_size=32,
            )

        self.assertEqual(result["total"], 1)
        register_mock.assert_called_once()
        load_mock.assert_called_once()
        self.assertEqual(tracker.run_id, "run-uuid")
        self.assertEqual(tracker.rows[0]["class_name"], "uninfected")
        self.assertTrue(tracker.rows[0]["used_for_test"])

    def test_record_run_dataset_images_ignores_tfds_source(self):
        tracker = FakeTracker()
        context = {"run_id": "run-uuid", "tracker": tracker}

        result = record_run_dataset_images(
            context,
            dataset_info={"data_source": "tfds"},
            usage_context="evaluation",
            splits=["test"],
        )

        self.assertIsNone(result)
        self.assertIsNone(tracker.rows)


if __name__ == "__main__":
    unittest.main()
