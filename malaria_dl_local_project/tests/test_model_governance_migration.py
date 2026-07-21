import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import init_db  # noqa: E402


MIGRATION_NAMES = (
    "023_schema_migrations_baseline.sql",
    "024_model_version_artifact_governance.sql",
    "025_deployed_model_versions.sql",
    "026_inference_jobs.sql",
    "027_model_governance_backfill_constraints.sql",
)


class ModelGovernanceMigrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = [PROJECT_ROOT / "db" / "init" / name for name in MIGRATION_NAMES]
        missing = [str(path) for path in cls.paths if not path.exists()]
        if missing:
            raise AssertionError(f"Faltan migraciones de gobernanza: {missing}")
        cls.sql_by_name = {
            path.name: path.read_text(encoding="utf-8") for path in cls.paths
        }
        cls.all_sql = "\n".join(cls.sql_by_name.values())

    def test_migrations_are_additive_and_keep_canonical_tables(self):
        upper_sql = self.all_sql.upper()
        for destructive_statement in ("DROP TABLE", "TRUNCATE", "DELETE FROM"):
            self.assertNotIn(destructive_statement, upper_sql)

        self.assertNotIn("CREATE TABLE INFERENCE_RUNS", upper_sql)
        self.assertNotIn("CREATE TABLE CELL_PREDICTIONS", upper_sql)
        self.assertIn("CREATE OR REPLACE VIEW inference_runs", self.all_sql)
        self.assertIn("CREATE OR REPLACE VIEW cell_predictions", self.all_sql)

    def test_migration_ledger_and_backfill_audit_are_append_only(self):
        sql = self.sql_by_name["023_schema_migrations_baseline.sql"]
        self.assertIn("CREATE TABLE IF NOT EXISTS schema_migrations", sql)
        self.assertIn(
            "CREATE TABLE IF NOT EXISTS model_governance_backfill_audit",
            sql,
        )
        self.assertIn("before_values JSONB", sql)
        self.assertIn("after_values JSONB", sql)
        self.assertIn("reversal_of_audit_id UUID", sql)
        self.assertIn("prevent_model_governance_audit_mutation", sql)
        self.assertIn("BEFORE UPDATE OR DELETE", sql)

    def test_model_versions_are_extended_with_identity_and_separate_statuses(self):
        sql = self.sql_by_name["024_model_version_artifact_governance.sql"]
        for column in (
            "model_name",
            "version_number",
            "checkpoint_artifact_id",
            "artifact_sha256",
            "artifact_size_bytes",
            "framework_version",
            "preprocessing_profile_snapshot",
            "class_mapping",
            "input_signature",
            "output_signature",
            "status",
            "lineage_status",
            "validated_at",
            "approved_at",
            "retired_at",
        ):
            self.assertIn(f"ADD COLUMN IF NOT EXISTS {column}", sql)

        self.assertIn("chk_model_versions_status", sql)
        self.assertIn("chk_model_versions_lineage_status", sql)
        self.assertIn("chk_model_versions_governed_hash", sql)
        self.assertIn("uq_model_versions_name_number", sql)
        self.assertIn("uq_model_versions_unjustified_sha256", sql)

    def test_deployment_contract_has_partial_active_uniqueness(self):
        sql = self.sql_by_name["025_deployed_model_versions.sql"]
        self.assertIn("CREATE TABLE IF NOT EXISTS deployed_model_versions", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS run_model_deployments", sql)
        for field in (
            "model_version_id",
            "deployment_name",
            "environment",
            "alias",
            "threshold_profile_snapshot",
            "preprocessing_profile_snapshot",
            "image_quality_policy_snapshot",
            "deployed_by",
        ):
            self.assertIn(field, sql)
        self.assertIn("uq_deployed_model_versions_active_slot", sql)
        self.assertIn("WHERE status = 'active'", sql)
        self.assertNotRegex(sql, r"status\s+TEXT\s+[^,;]*DEFAULT\s+'active'")

    def test_inference_jobs_and_cell_prediction_constraints_are_present(self):
        sql = self.sql_by_name["026_inference_jobs.sql"]
        self.assertIn("CREATE TABLE IF NOT EXISTS image_analysis_jobs", sql)
        for column in (
            "model_version_id",
            "deployed_model_version_id",
            "inference_run_id",
            "image_analysis_job_id",
            "classifier_model_version_id",
            "detector_model_version_id",
            "probability_parasitized",
            "probability_uninfected",
            "predicted_class",
            "threshold_used",
            "review_status",
        ):
            self.assertIn(column, sql)

        for constraint in (
            "chk_predictions_probability_parasitized",
            "chk_predictions_probability_uninfected",
            "chk_predictions_predicted_class",
            "chk_predictions_class_label",
            "chk_predictions_threshold_used",
            "uq_predictions_job_cell_index",
        ):
            self.assertIn(constraint, sql)

    def test_new_relationships_do_not_cascade_delete_evidence(self):
        for name, sql in self.sql_by_name.items():
            self.assertNotIn(
                "ON DELETE CASCADE",
                sql.upper(),
                f"{name} introduce una cascada destructiva",
            )
        final_sql = self.sql_by_name[
            "027_model_governance_backfill_constraints.sql"
        ]
        self.assertIn("run_lineage_parent_run_id_fkey", final_sql)
        self.assertIn("run_lineage_child_run_id_fkey", final_sql)
        self.assertIn("model_versions_training_run_id_fkey", final_sql)
        self.assertIn("ON DELETE RESTRICT", final_sql)

    def test_runner_supports_functions_comments_and_migration_checksums(self):
        sql = """
        -- un punto y coma en comentario ; no divide
        CREATE TABLE demo (value TEXT DEFAULT ';');
        DO $governance$
        BEGIN
            PERFORM 1;
            RAISE NOTICE 'sigue dentro; del bloque';
        END;
        $governance$;
        /* tampoco divide ; */ SELECT E'it\\'s valid; still one string';
        """
        statements = init_db.split_sql_statements(sql)
        self.assertEqual(len(statements), 3)
        self.assertIn("PERFORM 1;", statements[1])
        self.assertIn("RAISE NOTICE", statements[1])

        runner_source = (PROJECT_ROOT / "scripts" / "init_db.py").read_text(
            encoding="utf-8"
        )
        for contract in (
            "ensure_migration_ledger",
            "baseline_legacy_migrations",
            "migration_checksum",
            "MigrationChecksumMismatchError",
        ):
            self.assertIn(contract, runner_source)

    def test_every_governance_sql_file_is_parseable_as_complete_statements(self):
        for path in self.paths:
            statements = init_db.split_sql_statements(
                path.read_text(encoding="utf-8")
            )
            self.assertGreater(len(statements), 0, path.name)
            for statement in statements:
                self.assertNotEqual(statement.strip(), "", path.name)

    def test_runner_skips_only_an_identical_recorded_migration(self):
        sql_path = self.paths[0]
        checksum = init_db.migration_checksum(sql_path)
        with (
            patch.object(
                init_db,
                "recorded_migration_checksum",
                return_value=checksum,
            ),
            patch.object(init_db, "execute_sql_file") as execute_sql_file,
            patch.object(init_db, "record_migration") as record_migration,
        ):
            applied = init_db.execute_pending_sql_file(object(), sql_path)

        self.assertFalse(applied)
        execute_sql_file.assert_not_called()
        record_migration.assert_not_called()

    def test_runner_rejects_checksum_drift(self):
        sql_path = self.paths[0]
        with (
            patch.object(
                init_db,
                "recorded_migration_checksum",
                return_value="0" * 64,
            ),
            patch.object(init_db, "execute_sql_file") as execute_sql_file,
            self.assertRaises(init_db.MigrationChecksumMismatchError),
        ):
            init_db.execute_pending_sql_file(object(), sql_path)

        execute_sql_file.assert_not_called()

    def test_runner_records_a_new_migration_after_success(self):
        sql_path = self.paths[0]
        checksum = init_db.migration_checksum(sql_path)
        connection = object()
        with (
            patch.object(
                init_db,
                "recorded_migration_checksum",
                return_value=None,
            ),
            patch.object(init_db, "execute_sql_file", return_value=10),
            patch.object(init_db, "record_migration") as record_migration,
        ):
            applied = init_db.execute_pending_sql_file(connection, sql_path)

        self.assertTrue(applied)
        record_migration.assert_called_once_with(
            connection,
            sql_path,
            checksum,
            10,
        )


if __name__ == "__main__":
    unittest.main()
