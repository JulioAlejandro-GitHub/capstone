import base64
import sys
import tempfile
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

    from app.routes.dataset import dataset_images, dataset_summary_endpoint
    from app.services import dataset_browser
except Exception as exc:  # pragma: no cover
    HTTPException = None
    dataset_images = None
    dataset_summary_endpoint = None
    dataset_browser = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


@unittest.skipIf(dataset_browser is None, f"Backend no disponible: {IMPORT_ERROR}")
class DatasetBrowserApiTests(unittest.TestCase):
    def test_summary_endpoint_delegates_summary_payload(self):
        expected = {
            "dataset": {"name": "malaria_physical_split"},
            "label_mapping": {"0": "uninfected", "1": "parasitized"},
            "split_process": {},
            "counts": {},
        }

        with mock.patch("app.routes.dataset.dataset_summary", return_value=expected):
            payload = dataset_summary_endpoint(datasource="malaria")

        self.assertEqual(payload, expected)

    def test_images_endpoint_returns_paginated_payload(self):
        expected = {
            "page": 1,
            "page_size": 24,
            "total_items": 0,
            "total_pages": 1,
            "items": [],
        }

        with mock.patch("app.routes.dataset.paginated_dataset_images", return_value=expected):
            payload = dataset_images(
                datasource="malaria",
                split="train",
                class_name="parasitized",
                page=1,
                page_size=24,
            )

        self.assertEqual(payload["page_size"], 24)

    def test_image_file_blocks_path_traversal_from_database_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "malaria_physical_split"
            root.mkdir()
            outside = Path(temp_dir) / "outside.png"
            outside.write_bytes(PNG_1X1)
            row = {
                "image_id": "11111111-1111-1111-1111-111111111111",
                "dataset_dir": str(root),
                "absolute_path": str(outside),
                "relative_path": "../outside.png",
            }

            with (
                mock.patch.object(dataset_browser, "PHYSICAL_DATASET_ROOT", root.resolve()),
                mock.patch("app.services.dataset_browser.fetch_one", return_value=row),
                self.assertRaises(HTTPException) as context,
            ):
                dataset_browser.resolve_dataset_image_file("malaria", row["image_id"])

        self.assertEqual(context.exception.status_code, 403)

    def test_image_file_missing_returns_404(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "malaria_physical_split"
            root.mkdir()
            row = {
                "image_id": "11111111-1111-1111-1111-111111111111",
                "dataset_dir": str(root),
                "absolute_path": str(root / "missing.png"),
                "relative_path": "train/parasitized/missing.png",
            }

            with (
                mock.patch.object(dataset_browser, "PHYSICAL_DATASET_ROOT", root.resolve()),
                mock.patch("app.services.dataset_browser.fetch_one", return_value=row),
                self.assertRaises(HTTPException) as context,
            ):
                dataset_browser.resolve_dataset_image_file("malaria", row["image_id"])

        self.assertEqual(context.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
