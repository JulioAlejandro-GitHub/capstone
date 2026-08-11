import tempfile
import unittest
from pathlib import Path

from malaria_split.discovery import scan_current_physical_split


def make_fixture(root: Path) -> None:
    for split in ("train", "val", "test"):
        for class_name in ("parasitized", "uninfected"):
            directory = root / split / class_name
            directory.mkdir(parents=True)
            (directory / f"{split}_{class_name}.png").write_bytes(b"image")


class CurrentSplitScannerTests(unittest.TestCase):
    def test_scanner_is_read_only_and_detects_structure_classes_counts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "split"
            make_fixture(root)
            before = {
                p.relative_to(root): (p.stat().st_size, p.stat().st_mtime_ns)
                for p in root.rglob("*")
            }
            result = scan_current_physical_split(root)
            after = {
                p.relative_to(root): (p.stat().st_size, p.stat().st_mtime_ns)
                for p in root.rglob("*")
            }
            self.assertEqual(before, after)
            self.assertEqual(
                [item.split_name for item in result.partitions],
                ["train", "val", "test"],
            )
            self.assertEqual(
                {item.class_name for item in result.partitions[0].classes},
                {"parasitized", "uninfected"},
            )
            self.assertEqual(result.total_image_files, 6)

    def test_domain_paths_are_relative(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "split"
            make_fixture(root)
            result = scan_current_physical_split(root)
            self.assertTrue(
                all(not Path(item.relative_path).is_absolute() for item in result.partitions)
            )
            self.assertNotIn(str(root.resolve()), str(result.to_dict()))

    def test_unexpected_and_zero_byte_files_are_reported_not_removed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "split"
            make_fixture(root)
            unexpected = root / "train" / "parasitized" / "note.txt"
            empty = root / "test" / "uninfected" / "empty.png"
            unexpected.write_text("keep", encoding="utf-8")
            empty.touch()
            result = scan_current_physical_split(root)
            self.assertIn("train/parasitized/note.txt", result.unexpected_files)
            self.assertIn("test/uninfected/empty.png", result.zero_byte_files)
            self.assertTrue(unexpected.exists() and empty.exists())


if __name__ == "__main__":
    unittest.main()

