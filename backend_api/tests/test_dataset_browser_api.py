import sys
import unittest
from pathlib import Path
from unittest import mock


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.routes.dataset import dataset_images, dataset_summary_endpoint  # noqa: E402


class DatasetBrowserApiTests(unittest.TestCase):
    def test_dataset_summary_endpoint_returns_physical_split_payload(self):
        summary = {
            "dataset": {
                "source_url": "https://www.tensorflow.org/datasets/catalog/malaria",
                "description": "Dataset de malaria",
            },
            "split_process": {"train_ratio": 0.8, "val_ratio": 0.1, "test_ratio": 0.1},
            "counts": {"train": {"total": 10}, "val": {"total": 2}, "test": {"total": 2}},
        }

        with mock.patch("app.routes.dataset.dataset_summary", return_value=summary):
            payload = dataset_summary_endpoint(datasource="malaria")

        self.assertTrue(payload["dataset"]["source_url"].endswith("/malaria"))
        self.assertEqual(payload["split_process"]["train_ratio"], 0.8)

    def test_dataset_images_endpoint_passes_filters_to_service(self):
        page = {
            "page": 2,
            "page_size": 24,
            "total_items": 1,
            "total_pages": 1,
            "items": [{"filename": "0001.png", "class_name": "parasitized"}],
        }

        with mock.patch("app.routes.dataset.paginated_dataset_images", return_value=page) as service:
            payload = dataset_images(
                datasource="malaria",
                split="test",
                class_name="parasitized",
                page=2,
                page_size=24,
            )

        self.assertEqual(payload["items"][0]["class_name"], "parasitized")
        service.assert_called_once_with(
            datasource="malaria",
            split="test",
            class_name="parasitized",
            page=2,
            page_size=24,
        )


if __name__ == "__main__":
    unittest.main()
