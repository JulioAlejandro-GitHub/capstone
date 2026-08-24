import tempfile
import unittest
from pathlib import Path

from malaria_split.discovery import classify_table, has_column, scan_current_physical_split


class SystemContractAuditorTests(unittest.TestCase):
    def test_classifies_existing_table(self):
        self.assertEqual(classify_table("datasets", {"datasets", "runs"}), "EXISTING")
        self.assertEqual(classify_table("missing", {"datasets"}), "MISSING")

    def test_detects_present_and_absent_column(self):
        columns = [{"name": "image_id"}, {"name": "patient_id"}]
        self.assertTrue(has_column(columns, "patient_id"))
        self.assertFalse(has_column(columns, "dataset_version_id"))

    def test_physical_configuration_and_layout_are_read_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for split in ("train", "val", "test"):
                for class_name in ("parasitized", "uninfected"):
                    (root / split / class_name).mkdir(parents=True)
            before = {path.relative_to(root): path.stat().st_mtime_ns for path in root.rglob("*")}
            result = scan_current_physical_split(root)
            after = {path.relative_to(root): path.stat().st_mtime_ns for path in root.rglob("*")}
            self.assertEqual(before, after)
            self.assertEqual([item.split_name for item in result.partitions], ["train", "val", "test"])

    def test_auditor_source_contains_no_ddl_or_dml_statements(self):
        source = Path(__file__).parents[2] / "src/malaria_split/discovery/system_contract_auditor.py"
        text = source.read_text(encoding="utf-8").upper()
        for forbidden in ("INSERT INTO", "UPDATE ", "DELETE FROM", "CREATE TABLE", "ALTER TABLE", "DROP TABLE", "TRUNCATE"):
            self.assertNotIn(forbidden, text)
        self.assertIn("SET TRANSACTION READ ONLY", text)


if __name__ == "__main__":
    unittest.main()
