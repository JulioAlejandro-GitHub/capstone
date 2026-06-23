import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.dataset_registry import (  # noqa: E402
    compute_file_checksum,
    register_physical_split_images,
    scan_physical_split,
    summarize_records,
)
from scripts import register_physical_split_in_db as register_script  # noqa: E402


def write_image(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (3, 2), color=(64, 32, 16)).save(path)


def create_split(root):
    for split in ("train", "val", "test"):
        for class_name in ("uninfected", "parasitized"):
            write_image(root / split / class_name / f"000001_{class_name}.png")


class FakeResult:
    def __init__(self, row=None):
        self.row = row

    def first(self):
        return self.row


class FakeConnection:
    def __init__(self):
        self.dataset_id = None
        self.image_ids = {}
        self.image_upserts = []

    def execute(self, statement, params=None):
        sql = str(statement)
        params = params or {}
        if "SELECT id" in sql and "FROM datasets" in sql:
            return FakeResult((self.dataset_id,)) if self.dataset_id else FakeResult()
        if "INSERT INTO datasets" in sql:
            self.dataset_id = "dataset-uuid"
            return FakeResult((self.dataset_id,))
        if "INSERT INTO dataset_split_images" in sql:
            key = (params["dataset_dir"], params["relative_path"])
            inserted = key not in self.image_ids
            self.image_ids.setdefault(key, f"image-{len(self.image_ids) + 1}")
            self.image_upserts.append(params)
            return FakeResult((self.image_ids[key], inserted))
        raise AssertionError(f"SQL no esperado: {sql}")


class DatasetRegistryTests(unittest.TestCase):
    def test_scan_physical_split_detects_clinical_classes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "malaria_physical_split"
            create_split(root)

            records = scan_physical_split(root)
            counts = summarize_records(records)

        self.assertEqual(len(records), 6)
        self.assertEqual(counts["train"]["uninfected"], 1)
        self.assertEqual(counts["test"]["parasitized"], 1)
        by_class = {record["class_name"]: record["class_index"] for record in records}
        self.assertEqual(by_class["uninfected"], 0)
        self.assertEqual(by_class["parasitized"], 1)

    def test_compute_file_checksum_is_stable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.bin"
            path.write_bytes(b"abc")

            first = compute_file_checksum(path)
            second = compute_file_checksum(path)

        self.assertEqual(first, second)
        self.assertEqual(
            first,
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )

    def test_register_physical_split_images_is_idempotent_with_fake_connection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "malaria_physical_split"
            create_split(root)
            connection = FakeConnection()

            first = register_physical_split_images(
                root,
                dataset_name="test_split",
                dataset_source="unit_test",
                connection_or_session=connection,
            )
            second = register_physical_split_images(
                root,
                dataset_name="test_split",
                dataset_source="unit_test",
                connection_or_session=connection,
            )

        self.assertEqual(first["inserted"], 6)
        self.assertEqual(first["updated"], 0)
        self.assertEqual(second["inserted"], 0)
        self.assertEqual(second["updated"], 6)
        self.assertEqual(len(connection.image_ids), 6)
        self.assertTrue(all("metadata" in params for params in connection.image_upserts))

    def test_register_script_dry_run_does_not_write_to_db(self):
        records = [
            {
                "split_name": split,
                "class_name": class_name,
                "class_index": 0 if class_name == "uninfected" else 1,
                "relative_path": f"{split}/{class_name}/000001.png",
                "filename": "000001.png",
            }
            for split in ("train", "val", "test")
            for class_name in ("uninfected", "parasitized")
        ]

        with patch.object(
            sys,
            "argv",
            [
                "register_physical_split_in_db.py",
                "--dataset-dir",
                "data/malaria_physical_split",
            ],
        ), patch.object(
            register_script,
            "scan_physical_split",
            return_value=records,
        ), patch.object(
            register_script,
            "register_physical_split_images",
        ) as register_mock:
            register_script.main()

        register_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
