import sys
import unittest
from pathlib import Path
from unittest import mock


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.routes.dataset import dataset_images, dataset_summary_endpoint  # noqa: E402
from app.services.dataset_browser import paginated_dataset_images  # noqa: E402
from fastapi import HTTPException  # noqa: E402


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

    def test_auxiliary_image_page_accepts_every_contract_size(self):
        for page_size in (12, 24, 48, 96):
            with self.subTest(page_size=page_size), mock.patch(
                "app.services.dataset_browser.safe_fetch_one",
                return_value={"total": 0},
            ), mock.patch(
                "app.services.dataset_browser.safe_fetch_all",
                return_value=[],
            ):
                payload = paginated_dataset_images(
                    datasource="malaria", page=1, page_size=page_size
                )
            self.assertEqual(payload["page"], 1)
            self.assertEqual(payload["page_size"], page_size)
            self.assertEqual(payload["total_items"], 0)
            self.assertEqual(payload["total_pages"], 1)

    def test_auxiliary_image_page_rejects_historical_size_20(self):
        with self.assertRaises(HTTPException) as context:
            paginated_dataset_images(
                datasource="malaria", page=1, page_size=20
            )
        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("12, 24, 48 o 96", context.exception.detail)


if __name__ == "__main__":
    unittest.main()
