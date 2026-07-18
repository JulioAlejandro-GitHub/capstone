import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import run_lineage  # noqa: E402


PARENT_ID = "11111111-1111-4111-8111-111111111111"
CHILD_ID = "22222222-2222-4222-8222-222222222222"
LINEAGE_ID = "33333333-3333-4333-8333-333333333333"


def connection_context():
    connection = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = connection
    context.__exit__.return_value = False
    return context, connection


class RunLineagePersistenceTests(unittest.TestCase):
    def test_create_run_lineage_inserts_and_returns_id(self):
        context, connection = connection_context()
        connection.execute.return_value.first.return_value = [LINEAGE_ID]

        with patch("src.run_lineage.get_connection", return_value=context):
            result = run_lineage.create_run_lineage(
                parent_run_id=PARENT_ID,
                child_run_id=CHILD_ID,
                relationship_type="evaluates_checkpoint_from",
                checkpoint_path="outputs/model/runs/parent/best_model.keras",
                confidence="explicit",
                metadata={"source": "unit-test"},
            )

        self.assertEqual(result, LINEAGE_ID)
        sql = str(connection.execute.call_args.args[0])
        params = connection.execute.call_args.args[1]
        self.assertIn("INSERT INTO run_lineage", sql)
        self.assertEqual(params["parent_run_id"], PARENT_ID)
        self.assertEqual(params["child_run_id"], CHILD_ID)
        self.assertEqual(json.loads(params["metadata"])["source"], "unit-test")

    def test_create_run_lineage_is_idempotent_by_unique_key(self):
        context, connection = connection_context()
        connection.execute.return_value.first.return_value = [LINEAGE_ID]

        with patch("src.run_lineage.get_connection", return_value=context):
            first = run_lineage.create_run_lineage(
                PARENT_ID,
                CHILD_ID,
                "evaluates_checkpoint_from",
            )
            second = run_lineage.create_run_lineage(
                PARENT_ID,
                CHILD_ID,
                "evaluates_checkpoint_from",
            )

        self.assertEqual(first, second)
        for call in connection.execute.call_args_list:
            sql = str(call.args[0])
            self.assertIn(
                "ON CONFLICT (parent_run_id, child_run_id, relationship_type)",
                sql,
            )

    def test_create_run_lineage_rejects_unknown_contract_values(self):
        with self.assertRaisesRegex(ValueError, "relationship_type inválido"):
            run_lineage.create_run_lineage(PARENT_ID, CHILD_ID, "latest_model")

        with self.assertRaisesRegex(ValueError, "confidence inválido"):
            run_lineage.create_run_lineage(
                PARENT_ID,
                CHILD_ID,
                "derived_from",
                confidence="guess",
            )

    def test_attach_source_training_metadata_merges_requested_fields(self):
        context, connection = connection_context()
        source_run = {
            "training_run_id": PARENT_ID,
            "run_name": "train_combined:densenet121",
            "model_name": "densenet121",
            "optimizer": "adamw",
            "confidence": "explicit",
            "resolution_method": "explicit_training_run_id",
        }

        with patch("src.run_lineage.get_connection", return_value=context):
            run_lineage.attach_source_training_metadata(
                CHILD_ID,
                source_run,
                "explains_checkpoint_from",
                checkpoint_path="outputs/densenet121/runs/run/best_model.keras",
            )

        params = connection.execute.call_args.args[1]
        metadata = json.loads(params["metadata"])
        self.assertEqual(metadata["source_training_run_id"], PARENT_ID)
        self.assertEqual(metadata["source_optimizer"], "adamw")
        self.assertEqual(metadata["lineage_status"], "resolved")
        self.assertNotIn("lineage_warning", metadata)
        self.assertIn(
            "- 'lineage_warning'",
            str(connection.execute.call_args.args[0]),
        )
        self.assertEqual(
            metadata["source_relationship_type"],
            "explains_checkpoint_from",
        )

    def test_mark_lineage_unresolved_keeps_auditable_warning(self):
        context, connection = connection_context()

        with patch("src.run_lineage.get_connection", return_value=context):
            run_lineage.mark_lineage_unresolved(
                CHILD_ID,
                "outputs/densenet121/best_model.keras",
                "Use --source-training-run-id.",
            )

        metadata = json.loads(connection.execute.call_args.args[1]["metadata"])
        self.assertEqual(metadata["lineage_status"], "unresolved")
        self.assertEqual(metadata["lineage_confidence"], "unknown")
        self.assertNotIn("source_training_run_id", metadata)
        self.assertIn(
            "'source_training_run_id'",
            str(connection.execute.call_args.args[0]),
        )
        self.assertIn("--source-training-run-id", metadata["lineage_warning"])

    def test_create_with_metadata_is_atomic_on_one_connection(self):
        context, connection = connection_context()
        insert_result = MagicMock()
        insert_result.first.return_value = [LINEAGE_ID]
        update_result = SimpleNamespace(rowcount=1)
        connection.execute.side_effect = [insert_result, update_result]
        source_run = {
            "training_run_id": PARENT_ID,
            "run_name": "train:custom_cnn",
            "run_type": "training",
            "model_name": "custom_cnn",
            "optimizer": "adamw",
            "confidence": "explicit",
        }

        with patch("src.run_lineage.get_connection", return_value=context) as get_db:
            result = run_lineage.create_run_lineage_with_metadata(
                parent_run_id=PARENT_ID,
                child_run_id=CHILD_ID,
                relationship_type="evaluates_checkpoint_from",
                source_training_run=source_run,
                checkpoint_path="outputs/custom_cnn/best_model.keras",
            )

        self.assertEqual(result, LINEAGE_ID)
        get_db.assert_called_once_with()
        self.assertEqual(connection.execute.call_count, 2)

    def test_atomic_create_propagates_metadata_failure_for_transaction_rollback(self):
        context, connection = connection_context()
        insert_result = MagicMock()
        insert_result.first.return_value = [LINEAGE_ID]
        connection.execute.side_effect = [insert_result, RuntimeError("update failed")]
        source_run = {"training_run_id": PARENT_ID, "confidence": "explicit"}

        with patch("src.run_lineage.get_connection", return_value=context):
            with self.assertRaisesRegex(RuntimeError, "update failed"):
                run_lineage.create_run_lineage_with_metadata(
                    parent_run_id=PARENT_ID,
                    child_run_id=CHILD_ID,
                    relationship_type="derived_from",
                    source_training_run=source_run,
                )

        self.assertEqual(connection.execute.call_count, 2)
        self.assertIs(context.__exit__.call_args.args[0], RuntimeError)


if __name__ == "__main__":
    unittest.main()
