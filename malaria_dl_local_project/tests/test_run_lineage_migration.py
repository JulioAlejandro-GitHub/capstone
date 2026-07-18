import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RunLineageMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migration = PROJECT_ROOT / "db" / "init" / "022_run_lineage.sql"
        cls.sql = migration.read_text(encoding="utf-8")

    def test_creates_lineage_table_constraints_and_indexes(self):
        self.assertIn("CREATE TABLE IF NOT EXISTS run_lineage", self.sql)
        self.assertIn("uq_run_lineage_parent_child_type", self.sql)
        self.assertIn("chk_run_lineage_relationship_type", self.sql)
        self.assertIn("chk_run_lineage_confidence", self.sql)

        for relationship_type in (
            "evaluates_checkpoint_from",
            "explains_checkpoint_from",
            "derived_from",
        ):
            self.assertIn(f"'{relationship_type}'", self.sql)

        for confidence in (
            "explicit",
            "inferred_exact_checkpoint",
            "inferred_model_version",
            "inferred_heuristic",
            "unknown",
        ):
            self.assertIn(f"'{confidence}'", self.sql)

        for index_name in (
            "idx_run_lineage_parent_run_id",
            "idx_run_lineage_child_run_id",
            "idx_run_lineage_relationship_type",
            "idx_run_lineage_checkpoint_path",
        ):
            self.assertIn(f"CREATE INDEX IF NOT EXISTS {index_name}", self.sql)

    def test_creates_all_audit_views_with_required_fields(self):
        for view_name in (
            "vw_run_lineage",
            "vw_evaluation_lineage",
            "vw_explainability_lineage",
        ):
            self.assertIn(f"CREATE OR REPLACE VIEW {view_name}", self.sql)

        for field_name in (
            "parent_optimizer",
            "parent_command",
            "child_command",
            "evaluation_started_at",
            "accuracy",
            "recall",
            "specificity",
            "f2_score",
            "auc",
            "explain_started_at",
            "method",
            "total_explanations",
            "success_count",
            "failed_count",
        ):
            self.assertIn(field_name, self.sql)

    def test_is_non_destructive(self):
        upper_sql = self.sql.upper()
        for destructive_statement in (
            "DROP TABLE",
            "TRUNCATE",
            "DELETE FROM",
        ):
            self.assertNotIn(destructive_statement, upper_sql)


if __name__ == "__main__":
    unittest.main()
