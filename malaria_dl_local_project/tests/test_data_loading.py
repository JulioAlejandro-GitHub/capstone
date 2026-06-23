import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    CLASS_NAMES,
    LABEL_MAPPING_VERSION,
    NEGATIVE_CLASS_INDEX,
    NEGATIVE_LABEL,
    POSITIVE_CLASS_INDEX,
    POSITIVE_LABEL,
)
from src.data import (  # noqa: E402
    make_image_dataset_from_directory,
    validate_physical_split,
)


def write_dummy_image(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (2, 2), color=(128, 0, 0)).save(path)


def create_minimal_physical_split(root):
    counts = {}
    total = 0
    for split in ["train", "val", "test"]:
        counts[split] = {}
        split_total = 0
        for class_name in CLASS_NAMES:
            write_dummy_image(root / split / class_name / f"000001_{class_name}.png")
            counts[split][class_name] = 1
            split_total += 1
        counts[split]["total"] = split_total
        total += split_total
    counts["total"] = total
    metadata = {
        "dataset_source": "tensorflow_datasets/malaria",
        "split_type": "physical_stratified_split",
        "train_ratio": 0.8,
        "val_ratio": 0.1,
        "test_ratio": 0.1,
        "seed": 42,
        "label_mapping_version": LABEL_MAPPING_VERSION,
        "class_names": CLASS_NAMES,
        "negative_class_index": NEGATIVE_CLASS_INDEX,
        "negative_class_name": NEGATIVE_LABEL,
        "positive_class_index": POSITIVE_CLASS_INDEX,
        "positive_class_name": POSITIVE_LABEL,
        "tfds_original_mapping": {"0": "parasitized", "1": "uninfected"},
        "project_mapping": {"0": "uninfected", "1": "parasitized"},
        "created_at": "2026-06-23T00:00:00+00:00",
        "counts": counts,
    }
    (root / "metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    return metadata


class DataLoadingTests(unittest.TestCase):
    def test_physical_split_structure_validation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "malaria_physical_split"
            metadata = create_minimal_physical_split(root)

            result = validate_physical_split(root)

        self.assertEqual(result["label_mapping_version"], LABEL_MAPPING_VERSION)
        self.assertEqual(result["class_names"], CLASS_NAMES)
        self.assertEqual(result["counts"]["train"]["total"], metadata["counts"]["train"]["total"])

    def test_missing_physical_split_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing_split"
            with self.assertRaises(FileNotFoundError) as context:
                validate_physical_split(missing)

        self.assertIn("create_physical_dataset_split.py", str(context.exception))

    def test_metadata_label_mapping_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "malaria_physical_split"
            metadata = create_minimal_physical_split(root)
            metadata["class_names"] = ["parasitized", "uninfected"]
            (root / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaises(ValueError) as context:
                validate_physical_split(root)

        self.assertIn("metadata.json no coincide", str(context.exception))

    def test_image_dataset_from_directory_uses_explicit_class_names(self):
        with patch("src.data.tf.keras.utils.image_dataset_from_directory") as mocked:
            make_image_dataset_from_directory(
                directory="/tmp/example",
                img_size=32,
                batch_size=4,
                shuffle=False,
                seed=42,
            )

        self.assertEqual(mocked.call_args.kwargs["class_names"], ["uninfected", "parasitized"])
        self.assertEqual(mocked.call_args.kwargs["label_mode"], "binary")


if __name__ == "__main__":
    unittest.main()
