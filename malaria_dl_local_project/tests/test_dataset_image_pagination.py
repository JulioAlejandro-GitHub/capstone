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
    from fastapi import HTTPException

    from app.services.dataset_browser import paginated_dataset_images
except Exception as exc:  # pragma: no cover
    HTTPException = None
    paginated_dataset_images = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


@unittest.skipIf(paginated_dataset_images is None, f"Backend no disponible: {IMPORT_ERROR}")
class DatasetImagePaginationTests(unittest.TestCase):
    def test_paginated_images_filters_train_and_parasitized(self):
        rows = [
            {
                "image_id": "11111111-1111-1111-1111-111111111111",
                "filename": "000001_parasitized.png",
                "split_name": "train",
                "display_split_name": "train",
                "class_name": "parasitized",
                "class_index": 1,
                "relative_path": "train/parasitized/000001_parasitized.png",
                "image_width": 200,
                "image_height": 200,
                "file_size_bytes": 123,
            }
        ]
        captured = {}

        def fake_fetch_one(_datasource, sql, params):
            captured["count_sql"] = sql
            captured["count_params"] = params
            return {"total": 1}

        def fake_fetch_all(_datasource, sql, params):
            captured["rows_sql"] = sql
            captured["rows_params"] = params
            return rows

        with (
            mock.patch("app.services.dataset_browser.fetch_one", side_effect=fake_fetch_one),
            mock.patch("app.services.dataset_browser.fetch_all", side_effect=fake_fetch_all),
        ):
            payload = paginated_dataset_images(
                "malaria",
                split="train",
                class_name="parasitized",
                page=1,
                page_size=24,
            )

        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["page_size"], 24)
        self.assertEqual(payload["total_items"], 1)
        self.assertEqual(payload["items"][0]["class_name"], "parasitized")
        self.assertIn("split_name = :split", captured["rows_sql"])
        self.assertEqual(captured["rows_params"]["split"], "train")
        self.assertEqual(captured["rows_params"]["class_name"], "parasitized")

    def test_paginated_images_rejects_invalid_page_size(self):
        with self.assertRaises(HTTPException) as context:
            paginated_dataset_images("malaria", page_size=13)

        self.assertEqual(context.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
