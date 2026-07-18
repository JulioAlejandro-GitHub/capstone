import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import diagnose_run_lineage  # noqa: E402


def diagnostic_result(**overrides):
    result = {
        "run_counts": {
            "training": 2,
            "evaluation": 1,
            "explainability": 1,
        },
        "relationship_count": 2,
        "evaluations_without_lineage": 0,
        "explanations_without_lineage": 0,
        "ambiguous_checkpoints": [],
        "ambiguous_checkpoint_count": 0,
        "unresolved_runs": [],
        "unresolved_run_count": 0,
        "top_relationships": [],
    }
    result.update(overrides)
    return result


class DiagnoseRunLineageTests(unittest.TestCase):
    def test_schema_validation_reports_every_missing_object(self):
        connection = MagicMock()
        connection.execute.return_value.mappings.return_value.one.return_value = {
            "run_lineage": "run_lineage",
            "vw_run_lineage": None,
            "vw_evaluation_lineage": "vw_evaluation_lineage",
            "vw_explainability_lineage": None,
        }

        with self.assertRaises(
            diagnose_run_lineage.MissingLineageSchemaError
        ) as raised:
            diagnose_run_lineage.validate_lineage_schema(connection)

        self.assertEqual(
            raised.exception.missing_objects,
            ("vw_run_lineage", "vw_explainability_lineage"),
        )

    def test_prints_ok_only_when_lineage_has_no_findings(self):
        output = StringIO()
        with redirect_stdout(output):
            diagnose_run_lineage.print_diagnostics(diagnostic_result())

        self.assertIn("OK: lineage completo", output.getvalue())

    def test_prints_warning_for_children_without_parent(self):
        output = StringIO()
        with redirect_stdout(output):
            diagnose_run_lineage.print_diagnostics(
                diagnostic_result(evaluations_without_lineage=1)
            )

        self.assertIn(
            "WARNING: existen runs evaluate/explain sin parent training",
            output.getvalue(),
        )

    def test_main_returns_error_when_migration_objects_are_missing(self):
        missing = diagnose_run_lineage.MissingLineageSchemaError(
            ["run_lineage", "vw_run_lineage"]
        )
        output = StringIO()
        with patch.object(
            diagnose_run_lineage,
            "diagnose_run_lineage",
            side_effect=missing,
        ), redirect_stdout(output):
            exit_code = diagnose_run_lineage.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: tabla/vistas no existen", output.getvalue())

    def test_ambiguous_checkpoint_diagnostic_uses_runtime_resolver(self):
        children = [
            {
                "child_run_id": "evaluation-run",
                "run_type": "evaluation",
                "checkpoint_path": "outputs/model/best_model.keras",
                "model_name": "custom_cnn",
            },
            {
                "child_run_id": "explain-run",
                "run_type": "explainability",
                "checkpoint_path": "outputs/model/best_model.keras",
                "model_name": "custom_cnn",
            },
        ]
        resolution = {
            "status": "ambiguous",
            "resolution_method": "generic_checkpoint_model_candidates",
            "candidates": [
                {"training_run_id": "training-a"},
                {"training_run_id": "training-b"},
            ],
        }

        with patch.object(
            diagnose_run_lineage,
            "resolve_training_run_from_checkpoint",
            return_value=resolution,
        ) as resolve:
            result = diagnose_run_lineage.resolve_ambiguous_checkpoints(children)

        resolve.assert_called_once_with(
            "outputs/model/best_model.keras",
            model_name="custom_cnn",
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["training_run_count"], 2)
        self.assertEqual(
            result[0]["child_run_ids"],
            ["evaluation-run", "explain-run"],
        )


if __name__ == "__main__":
    unittest.main()
