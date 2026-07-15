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

    def test_case_level_explainability_view_uses_drop_create(self):
        migration = PROJECT_ROOT / "db" / "init" / "007_case_level_explainability_views.sql"

        sql = migration.read_text(encoding="utf-8")

        self.assertIn("DROP VIEW IF EXISTS vw_case_level_explainability CASCADE", sql)
        self.assertIn("CREATE VIEW vw_case_level_explainability", sql)
        self.assertIn("probability_parasitized", sql)
        self.assertIn("threshold_used", sql)
        self.assertIn("threshold_source", sql)
        self.assertNotIn("CREATE OR REPLACE VIEW vw_case_level_explainability", sql)

    def test_clinical_inference_view_uses_drop_create_for_postgres(self):
        for migration_name in (
            "010_clinical_inference_tracking.sql",
            "011_label_mapping_clinical_v1.sql",
        ):
            migration = PROJECT_ROOT / "db" / "init" / migration_name

            sql = migration.read_text(encoding="utf-8")

            self.assertIn(
                "DROP VIEW IF EXISTS vw_clinical_inference_predictions CASCADE",
                sql,
            )
            self.assertIn("CREATE VIEW vw_clinical_inference_predictions", sql)
            self.assertNotIn(
                "CREATE OR REPLACE VIEW vw_clinical_inference_predictions",
                sql,
            )

    def test_clinical_run_tracking_migration_exists_with_expected_objects(self):
        migration = PROJECT_ROOT / "db" / "init" / "017_clinical_run_tracking.sql"

        sql = migration.read_text(encoding="utf-8")

        self.assertIn("ALTER TABLE run_io_records", sql)
        self.assertIn("ADD COLUMN IF NOT EXISTS run_type", sql)
        self.assertIn("ADD COLUMN IF NOT EXISTS model_metadata", sql)
        self.assertIn("ADD COLUMN IF NOT EXISTS clinical_metadata", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS run_clinical_metrics", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS run_checkpoint_policy", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS run_threshold_calibration", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS run_image_predictions", sql)
        self.assertIn("run_id UUID NOT NULL REFERENCES runs(id)", sql)
        self.assertIn("image_id UUID NULL REFERENCES dataset_split_images(image_id)", sql)
        self.assertIn("probability_parasitized", sql)
        self.assertIn("raw_model_score_meaning TEXT NOT NULL DEFAULT 'probability_parasitized'", sql)
        self.assertIn("DROP VIEW IF EXISTS vw_clinical_run_summary CASCADE", sql)
        self.assertIn("CREATE VIEW vw_clinical_run_summary", sql)
        self.assertIn("CREATE VIEW vw_checkpoint_policy_summary", sql)
        self.assertIn("CREATE VIEW vw_threshold_calibration_summary", sql)
        self.assertIn("CREATE VIEW vw_run_artifacts_summary", sql)
        self.assertIn("CREATE VIEW vw_run_image_predictions_summary", sql)
        self.assertNotIn("DROP TABLE", sql)
        self.assertNotIn("TRUNCATE", sql)

    def test_visual_audit_view_is_non_destructive_and_null_safe(self):
        migration = PROJECT_ROOT / "db" / "init" / "018_visual_audit_views.sql"

        sql = migration.read_text(encoding="utf-8")

        self.assertIn(
            "CREATE OR REPLACE VIEW vw_visual_explainability_audit",
            sql,
        )
        for required_field in (
            "source_image_path",
            "crop_path",
            "probability_uninfected",
            "threshold_source",
            "confidence_status",
            "explanation_output_path",
            "explanation_parameters",
            "patient_id",
            "slide_id",
            "bbox_width",
            "started_at",
            "created_at",
        ):
            self.assertIn(required_field, sql)
        self.assertIn("FROM explainability_results er", sql)
        self.assertIn("LEFT JOIN predictions p", sql)
        self.assertIn("LEFT JOIN runs r", sql)
        self.assertIn("LEFT JOIN models m", sql)
        self.assertIn("LEFT JOIN datasets d", sql)
        self.assertIn("FROM artifacts source_artifact", sql)
        self.assertNotIn("DROP TABLE", sql)
        self.assertNotIn("TRUNCATE", sql)
        self.assertNotIn("DELETE FROM", sql)

    def test_model_execution_tracking_migration_is_incremental(self):
        migration = (
            PROJECT_ROOT
            / "db"
            / "init"
            / "019_model_execution_parameters.sql"
        )

        sql = migration.read_text(encoding="utf-8")

        self.assertIn("ALTER TABLE runs", sql)
        for required_column in (
            "execution_type",
            "execution_parameters",
            "fine_tuning_start_epoch",
            "total_epochs",
            "completed_epochs",
        ):
            self.assertIn(f"ADD COLUMN IF NOT EXISTS {required_column}", sql)

        self.assertIn("ALTER TABLE training_history", sql)
        for required_column in ("phase", "train_loss", "train_accuracy"):
            self.assertIn(f"ADD COLUMN IF NOT EXISTS {required_column}", sql)

        self.assertIn("idx_runs_execution_type", sql)
        self.assertIn("idx_runs_execution_parameters_gin", sql)
        self.assertIn("idx_training_history_run_phase_epoch", sql)
        self.assertIn("SET train_loss = loss", sql)
        self.assertIn("SET train_accuracy = accuracy", sql)
        self.assertNotIn("DROP TABLE", sql)
        self.assertNotIn("TRUNCATE", sql)
        self.assertNotIn("DELETE FROM", sql)


if __name__ == "__main__":
    unittest.main()
