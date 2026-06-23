import sys
import unittest
from argparse import Namespace
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.create_physical_dataset_split import (  # noqa: E402
    build_metadata,
    count_assignments,
    stratified_split_records,
    validate_ratios,
)
from src.config import CLASS_NAMES, LABEL_MAPPING_VERSION  # noqa: E402


class PhysicalDatasetSplitTests(unittest.TestCase):
    def test_class_names_are_clinical_order(self):
        self.assertEqual(CLASS_NAMES, ["uninfected", "parasitized"])

    def test_validate_ratios_requires_sum_one(self):
        ratios = validate_ratios(0.8, 0.1, 0.1)
        self.assertEqual(ratios["train_ratio"], 0.8)
        with self.assertRaises(ValueError):
            validate_ratios(0.8, 0.2, 0.2)

    def test_stratified_split_is_reproducible_and_balanced(self):
        records = []
        for index in range(20):
            records.append(
                {
                    "tfds_index": index,
                    "original_tfds_label": 1,
                    "project_label": 0,
                    "class_name": "uninfected",
                }
            )
        for index in range(20, 40):
            records.append(
                {
                    "tfds_index": index,
                    "original_tfds_label": 0,
                    "project_label": 1,
                    "class_name": "parasitized",
                }
            )

        first = stratified_split_records(records, 42, 0.8, 0.1, 0.1)
        second = stratified_split_records(records, 42, 0.8, 0.1, 0.1)
        counts = count_assignments(records, first)

        self.assertEqual(first, second)
        self.assertEqual(counts["train"]["uninfected"], 16)
        self.assertEqual(counts["train"]["parasitized"], 16)
        self.assertEqual(counts["val"]["uninfected"], 2)
        self.assertEqual(counts["val"]["parasitized"], 2)
        self.assertEqual(counts["test"]["uninfected"], 2)
        self.assertEqual(counts["test"]["parasitized"], 2)

    def test_metadata_label_mapping_matches_config(self):
        args = Namespace(
            train_ratio=0.8,
            val_ratio=0.1,
            test_ratio=0.1,
            seed=42,
            image_format="png",
        )
        counts = {
            "train": {"uninfected": 16, "parasitized": 16, "total": 32},
            "val": {"uninfected": 2, "parasitized": 2, "total": 4},
            "test": {"uninfected": 2, "parasitized": 2, "total": 4},
            "total": 40,
        }

        metadata = build_metadata(args, counts)

        self.assertEqual(metadata["label_mapping_version"], LABEL_MAPPING_VERSION)
        self.assertEqual(metadata["class_names"], ["uninfected", "parasitized"])
        self.assertEqual(metadata["project_mapping"], {"0": "uninfected", "1": "parasitized"})
        self.assertEqual(metadata["tfds_original_mapping"], {"0": "parasitized", "1": "uninfected"})


if __name__ == "__main__":
    unittest.main()
