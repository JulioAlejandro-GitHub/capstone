import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class DbMigrationTests(unittest.TestCase):
    def test_dataset_tracking_migration_exists_with_expected_objects(self):
        migration = PROJECT_ROOT / "db" / "init" / "012_dataset_split_image_tracking.sql"

        sql = migration.read_text(encoding="utf-8")

        self.assertIn("CREATE TABLE IF NOT EXISTS dataset_split_images", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS run_dataset_images", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS run_io_records", sql)
        self.assertIn("CREATE VIEW vw_dataset_split_images_summary", sql)
        self.assertIn("CREATE VIEW vw_run_dataset_usage_summary", sql)
        self.assertIn("CREATE VIEW vw_run_io_summary", sql)
        self.assertIn("run_id UUID NOT NULL REFERENCES runs(id)", sql)
        self.assertIn("dataset_id UUID REFERENCES datasets(id)", sql)
        self.assertIn("0, 1", sql)
        self.assertIn("'uninfected', 'parasitized'", sql)

    def test_dataset_browser_views_migration_exists(self):
        migration = PROJECT_ROOT / "db" / "init" / "013_dataset_browser_views.sql"

        sql = migration.read_text(encoding="utf-8")

        self.assertIn("DROP VIEW IF EXISTS vw_dataset_browser_summary CASCADE", sql)
        self.assertIn("CREATE VIEW vw_dataset_browser_summary", sql)
        self.assertIn("CREATE VIEW vw_dataset_browser_images", sql)
        self.assertIn("FROM dataset_split_images", sql)
        self.assertIn("label_mapping_version", sql)


if __name__ == "__main__":
    unittest.main()
