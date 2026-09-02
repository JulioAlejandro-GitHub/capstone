import inspect
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.malaria_dl.evaluation import evaluation_terminal_service as service  # noqa: E402


TRAIN = UUID("11111111-1111-4111-8111-111111111111")
EVALUATE = UUID("22222222-2222-4222-8222-222222222222")
VERSION = UUID("33333333-3333-4333-8333-333333333333")
ARTIFACT = UUID("44444444-4444-4444-8444-444444444444")


def invoke(connection=None):
    return service.finalize_evaluation_with_lineage(
        training_run_id=TRAIN,
        evaluation_run_id=EVALUATE,
        model_version_id=VERSION,
        checkpoint_artifact_id=ARTIFACT,
        checkpoint_path="checkpoint.keras",
        confidence="explicit",
        lineage_metadata={"phase": "terminal"},
        duration_seconds=12.5,
        summary={"test_accuracy": 0.9},
        connection=connection,
    )


class EvaluationTerminalServiceTests(unittest.TestCase):
    def test_authoritative_terminal_path_contains_no_release_writes(self):
        source = inspect.getsource(service)
        for release_field in (
            "release_status",
            "release_updated_at",
            "release_changed_by",
            "release_reason",
            "reconcile_training_release_eligibility",
        ):
            self.assertNotIn(release_field, source)

    def test_lineage_precedes_completion_on_the_same_external_connection(self):
        connection = MagicMock()
        calls = []
        lineage = SimpleNamespace(created=True)
        finalization = SimpleNamespace(changed=True)

        def create(**kwargs):
            calls.append(("lineage", kwargs["connection"]))
            return lineage

        def finalize(*args, **kwargs):
            calls.append(("completion", kwargs["connection"]))
            self.assertEqual(args, (EVALUATE,))
            return finalization

        with patch.object(
            service,
            "create_or_confirm_evaluation_training_lineage",
            side_effect=create,
        ) as create_mock, patch.object(
            service,
            "finalize_evaluation_run",
            side_effect=finalize,
        ) as finalize_mock, patch.object(service, "get_engine") as get_engine:
            result = invoke(connection)

        self.assertIs(result.lineage, lineage)
        self.assertIs(result.finalization, finalization)
        self.assertEqual(calls, [("lineage", connection), ("completion", connection)])
        self.assertEqual(create_mock.call_args.kwargs["training_run_id"], TRAIN)
        self.assertEqual(create_mock.call_args.kwargs["model_version_id"], VERSION)
        self.assertEqual(
            create_mock.call_args.kwargs["checkpoint_artifact_id"], ARTIFACT
        )
        finalize_mock.assert_called_once()
        get_engine.assert_not_called()
        connection.commit.assert_not_called()
        connection.rollback.assert_not_called()
        connection.close.assert_not_called()

    def test_lineage_failure_prevents_completion(self):
        connection = MagicMock()
        with patch.object(
            service,
            "create_or_confirm_evaluation_training_lineage",
            side_effect=RuntimeError("lineage conflict"),
        ), patch.object(service, "finalize_evaluation_run") as finalize:
            with self.assertRaisesRegex(RuntimeError, "lineage conflict"):
                invoke(connection)

        finalize.assert_not_called()
        connection.rollback.assert_not_called()

    def test_owned_transaction_rolls_back_new_lineage_if_completion_fails(self):
        connection = MagicMock()
        context = MagicMock()
        context.__enter__.return_value = connection
        context.__exit__.return_value = False
        engine = MagicMock()
        engine.begin.return_value = context

        with patch.object(service, "get_engine", return_value=engine), patch.object(
            service,
            "create_or_confirm_evaluation_training_lineage",
            return_value=SimpleNamespace(created=True),
        ) as create, patch.object(
            service,
            "finalize_evaluation_run",
            side_effect=RuntimeError("completion failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "completion failed"):
                invoke()

        create.assert_called_once()
        self.assertIs(context.__exit__.call_args.args[0], RuntimeError)

    def test_owned_rollback_does_not_rewrite_an_existing_lineage(self):
        connection = MagicMock()
        context = MagicMock()
        context.__enter__.return_value = connection
        context.__exit__.return_value = False
        engine = MagicMock()
        engine.begin.return_value = context
        existing = SimpleNamespace(created=False)

        with patch.object(service, "get_engine", return_value=engine), patch.object(
            service,
            "create_or_confirm_evaluation_training_lineage",
            return_value=existing,
        ), patch.object(
            service,
            "finalize_evaluation_run",
            side_effect=RuntimeError("completion failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "completion failed"):
                invoke()

        self.assertIs(context.__exit__.call_args.args[0], RuntimeError)
        sql = "\n".join(str(call.args[0]) for call in connection.execute.call_args_list)
        self.assertNotIn("UPDATE run_lineage", sql)


if __name__ == "__main__":
    unittest.main()
