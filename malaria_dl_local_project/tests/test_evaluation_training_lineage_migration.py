import ast
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    REPOSITORY_ROOT
    / "alembic"
    / "versions"
    / "20260901_01_single_evaluation_training_parent.py"
)


class EvaluationTrainingLineageMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MIGRATION.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_revision_is_linear_and_upgrade_prechecks_all_duplicates(self):
        self.assertIn('revision = "20260901_01"', self.source)
        self.assertIn('down_revision = "20260829_01"', self.source)
        self.assertIn("GROUP BY child_run_id", self.source)
        self.assertIn("HAVING COUNT(*) > 1", self.source)
        self.assertIn("if duplicates:", self.source)
        self.assertIn("raise RuntimeError", self.source)
        self.assertNotIn("LIMIT", self.source.upper())

    def test_unique_partial_index_has_exact_identity_predicate(self):
        self.assertIn(
            'INDEX_NAME = "uq_run_lineage_single_evaluation_training_parent"',
            self.source,
        )
        self.assertIn('"run_lineage"', self.source)
        self.assertIn('["child_run_id"]', self.source)
        self.assertIn("unique=True", self.source)
        self.assertIn(
            "relationship_type = 'evaluates_checkpoint_from'", self.source
        )

    def test_downgrade_is_symmetric_and_migration_does_not_rewrite_data(self):
        self.assertIn(
            'op.drop_index(INDEX_NAME, table_name="run_lineage")', self.source
        )
        upper = self.source.upper()
        for forbidden in (
            "UPDATE RUN_LINEAGE",
            "DELETE FROM RUN_LINEAGE",
            "INSERT INTO RUN_LINEAGE",
            "TRAINING_RELEASE_STATUS",
            "PUBLISHED_MODEL_VERSIONS",
            "DEPLOYED_MODEL_VERSIONS",
        ):
            self.assertNotIn(forbidden, upper)

    def test_file_is_valid_python(self):
        self.assertIsInstance(self.tree, ast.Module)


if __name__ == "__main__":
    unittest.main()
