import sys
import unittest
from pathlib import Path
from unittest import mock


CAPSTONE_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = CAPSTONE_ROOT / "malaria_dl_local_project"
BACKEND_ROOT = CAPSTONE_ROOT / "backend_api"
for path in (PROJECT_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    from app.services.dataset_browser import dataset_summary
except Exception as exc:  # pragma: no cover
    dataset_summary = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


@unittest.skipIf(dataset_summary is None, f"Backend no disponible: {IMPORT_ERROR}")
class DatasetBrowserQueryTests(unittest.TestCase):
    def test_dataset_summary_shape_and_counts(self):
        rows = [
            {
                "dataset_name": "malaria_physical_split",
                "dataset_source": "tensorflow_datasets/malaria",
                "source_url": "https://www.tensorflow.org/datasets/catalog/malaria",
                "description": "Dataset clínico",
                "dataset_dir": "data/malaria_physical_split",
                "split_type": "physical_stratified_split",
                "train_ratio": 0.8,
                "val_ratio": 0.1,
                "test_ratio": 0.1,
                "seed": 42,
                "label_mapping_version": "clinical_v1_parasitized_positive",
                "split_name": "train",
                "class_name": "parasitized",
                "class_index": 1,
                "image_count": 7,
                "dataset_metadata": {},
            },
            {
                "dataset_name": "malaria_physical_split",
                "dataset_source": "tensorflow_datasets/malaria",
                "source_url": "https://www.tensorflow.org/datasets/catalog/malaria",
                "description": "Dataset clínico",
                "dataset_dir": "data/malaria_physical_split",
                "split_type": "physical_stratified_split",
                "train_ratio": 0.8,
                "val_ratio": 0.1,
                "test_ratio": 0.1,
                "seed": 42,
                "label_mapping_version": "clinical_v1_parasitized_positive",
                "split_name": "train",
                "class_name": "uninfected",
                "class_index": 0,
                "image_count": 5,
                "dataset_metadata": {},
            },
        ]

        with mock.patch("app.services.dataset_browser.fetch_all", return_value=rows):
            payload = dataset_summary("malaria")

        self.assertEqual(payload["dataset"]["name"], "malaria_physical_split")
        self.assertEqual(payload["dataset"]["source_url"], rows[0]["source_url"])
        self.assertEqual(payload["label_mapping"]["0"], "uninfected")
        self.assertEqual(payload["label_mapping"]["1"], "parasitized")
        self.assertEqual(payload["split_process"]["train_ratio"], 0.8)
        self.assertEqual(payload["counts"]["train"]["parasitized"], 7)
        self.assertEqual(payload["counts"]["train"]["uninfected"], 5)

    def test_dataset_summary_empty_db_returns_controlled_payload(self):
        with mock.patch("app.services.dataset_browser.fetch_all", return_value=[]):
            payload = dataset_summary("malaria")

        self.assertEqual(payload["counts"]["total"], 0)
        self.assertEqual(payload["dataset"]["source"], "tensorflow_datasets/malaria")
        self.assertEqual(payload["label_mapping"]["positive_class"], "parasitized")


if __name__ == "__main__":
    unittest.main()
