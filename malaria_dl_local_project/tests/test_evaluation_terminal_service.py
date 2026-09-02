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
CONFIRMED_TRAIN = UUID("55555555-5555-4555-8555-555555555555")


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
    def test_authoritative_terminal_path_delegates_release_without_safe_track(self):
        source = inspect.getsource(service)
        self.assertIn("reconcile_training_release_eligibility", source)
        self.assertLess(
            source.index("create_or_confirm_evaluation_training_lineage("),
            source.index("finalize_evaluation_run("),
        )
        self.assertLess(
            source.index("finalize_evaluation_run("),
            source.index("reconcile_training_release_eligibility("),
        )
        for forbidden in (
            "safe_track",
            "release_status",
            "release_updated_at",
            "release_changed_by",
            "release_reason",
        ):
            self.assertNotIn(forbidden, source)

    def test_three_steps_use_same_external_connection_in_required_order(self):
        connection = MagicMock()
        calls = []
        lineage = SimpleNamespace(
            created=True,
            training_run_id=CONFIRMED_TRAIN,
            evaluation_run_id=EVALUATE,
        )
        finalization = SimpleNamespace(changed=True)
        release = SimpleNamespace(changed=True)

        def create(**kwargs):
            calls.append(("lineage", kwargs["connection"]))
            return lineage

        def finalize(*args, **kwargs):
            calls.append(("completion", kwargs["connection"]))
            self.assertEqual(args, (EVALUATE,))
            return finalization

        def reconcile(*args, **kwargs):
            calls.append(("release", kwargs["connection"]))
            self.assertEqual(args, (CONFIRMED_TRAIN,))
            return release

        with patch.object(
            service,
            "create_or_confirm_evaluation_training_lineage",
            side_effect=create,
        ) as create_mock, patch.object(
            service,
            "finalize_evaluation_run",
            side_effect=finalize,
        ) as finalize_mock, patch.object(service, "get_engine") as get_engine:
            with patch.object(
                service,
                "reconcile_training_release_eligibility",
                side_effect=reconcile,
            ) as release_mock:
                result = invoke(connection)

        self.assertIs(result.lineage, lineage)
        self.assertIs(result.finalization, finalization)
        self.assertIs(result.release_decision, release)
        self.assertEqual(
            calls,
            [
                ("lineage", connection),
                ("completion", connection),
                ("release", connection),
            ],
        )
        self.assertEqual(create_mock.call_args.kwargs["training_run_id"], TRAIN)
        self.assertEqual(create_mock.call_args.kwargs["model_version_id"], VERSION)
        self.assertEqual(
            create_mock.call_args.kwargs["checkpoint_artifact_id"], ARTIFACT
        )
        finalize_mock.assert_called_once()
        release_mock.assert_called_once_with(
            CONFIRMED_TRAIN, connection=connection
        )
        get_engine.assert_not_called()
        connection.commit.assert_not_called()
        connection.rollback.assert_not_called()
        connection.close.assert_not_called()

    def test_existing_lineage_and_new_completion_still_reconcile(self):
        connection = MagicMock()
        lineage = SimpleNamespace(created=False, training_run_id=TRAIN)
        finalization = SimpleNamespace(changed=True)
        release = SimpleNamespace(changed=True)
        with patch.object(
            service,
            "create_or_confirm_evaluation_training_lineage",
            return_value=lineage,
        ), patch.object(
            service, "finalize_evaluation_run", return_value=finalization
        ), patch.object(
            service,
            "reconcile_training_release_eligibility",
            return_value=release,
        ) as reconcile:
            result = invoke(connection)

        self.assertFalse(result.lineage.created)
        self.assertTrue(result.finalization.changed)
        self.assertIs(result.release_decision, release)
        reconcile.assert_called_once_with(TRAIN, connection=connection)

    def test_completed_retry_repairs_release_without_rewriting_completion(self):
        connection = MagicMock()
        lineage = SimpleNamespace(created=False, training_run_id=TRAIN)
        finalization = SimpleNamespace(changed=False)
        repaired = SimpleNamespace(changed=True)
        with patch.object(
            service,
            "create_or_confirm_evaluation_training_lineage",
            return_value=lineage,
        ), patch.object(
            service, "finalize_evaluation_run", return_value=finalization
        ), patch.object(
            service,
            "reconcile_training_release_eligibility",
            return_value=repaired,
        ) as reconcile:
            result = invoke(connection)

        self.assertFalse(result.finalization.changed)
        self.assertTrue(result.release_decision.changed)
        reconcile.assert_called_once_with(TRAIN, connection=connection)

    def test_lineage_failure_prevents_completion_and_release(self):
        connection = MagicMock()
        with patch.object(
            service,
            "create_or_confirm_evaluation_training_lineage",
            side_effect=RuntimeError("lineage conflict"),
        ), patch.object(
            service, "finalize_evaluation_run"
        ) as finalize, patch.object(
            service, "reconcile_training_release_eligibility"
        ) as reconcile:
            with self.assertRaisesRegex(RuntimeError, "lineage conflict"):
                invoke(connection)

        finalize.assert_not_called()
        reconcile.assert_not_called()
        connection.rollback.assert_not_called()

    def test_completion_failure_prevents_release_and_rolls_back_owned_transaction(self):
        connection = MagicMock()
        context = MagicMock()
        context.__enter__.return_value = connection
        context.__exit__.return_value = False
        engine = MagicMock()
        engine.begin.return_value = context

        with patch.object(service, "get_engine", return_value=engine), patch.object(
            service,
            "create_or_confirm_evaluation_training_lineage",
            return_value=SimpleNamespace(created=True, training_run_id=TRAIN),
        ) as create, patch.object(
            service,
            "finalize_evaluation_run",
            side_effect=RuntimeError("completion failed"),
        ), patch.object(
            service, "reconcile_training_release_eligibility"
        ) as reconcile:
            with self.assertRaisesRegex(RuntimeError, "completion failed"):
                invoke()

        create.assert_called_once()
        reconcile.assert_not_called()
        self.assertIs(context.__exit__.call_args.args[0], RuntimeError)

    def test_release_failure_rolls_back_lineage_and_completion_and_propagates(self):
        connection = MagicMock()
        context = MagicMock()
        context.__enter__.return_value = connection
        context.__exit__.return_value = False
        engine = MagicMock()
        engine.begin.return_value = context

        with patch.object(service, "get_engine", return_value=engine), patch.object(
            service,
            "create_or_confirm_evaluation_training_lineage",
            return_value=SimpleNamespace(created=True, training_run_id=TRAIN),
        ) as create, patch.object(
            service,
            "finalize_evaluation_run",
            return_value=SimpleNamespace(changed=True),
        ) as finalize, patch.object(
            service,
            "reconcile_training_release_eligibility",
            side_effect=RuntimeError("release failed"),
        ) as reconcile:
            with self.assertRaisesRegex(RuntimeError, "release failed"):
                invoke()

        create.assert_called_once()
        finalize.assert_called_once()
        reconcile.assert_called_once_with(TRAIN, connection=connection)
        engine.begin.assert_called_once_with()
        self.assertIs(context.__exit__.call_args.args[0], RuntimeError)

    def test_owned_transaction_commits_once_after_all_three_steps(self):
        connection = MagicMock()
        context = MagicMock()
        context.__enter__.return_value = connection
        context.__exit__.return_value = False
        engine = MagicMock()
        engine.begin.return_value = context
        release = SimpleNamespace(changed=False)

        with patch.object(service, "get_engine", return_value=engine), patch.object(
            service,
            "create_or_confirm_evaluation_training_lineage",
            return_value=SimpleNamespace(created=True, training_run_id=TRAIN),
        ), patch.object(
            service,
            "finalize_evaluation_run",
            return_value=SimpleNamespace(changed=True),
        ), patch.object(
            service,
            "reconcile_training_release_eligibility",
            return_value=release,
        ):
            result = invoke()

        self.assertIs(result.release_decision, release)
        engine.begin.assert_called_once_with()
        self.assertEqual(context.__exit__.call_args.args, (None, None, None))

    def test_owned_rollback_does_not_rewrite_an_existing_lineage(self):
        connection = MagicMock()
        context = MagicMock()
        context.__enter__.return_value = connection
        context.__exit__.return_value = False
        engine = MagicMock()
        engine.begin.return_value = context
        existing = SimpleNamespace(created=False, training_run_id=TRAIN)

        with patch.object(service, "get_engine", return_value=engine), patch.object(
            service,
            "create_or_confirm_evaluation_training_lineage",
            return_value=existing,
        ), patch.object(
            service,
            "finalize_evaluation_run",
            side_effect=RuntimeError("completion failed"),
        ), patch.object(
            service, "reconcile_training_release_eligibility"
        ) as reconcile:
            with self.assertRaisesRegex(RuntimeError, "completion failed"):
                invoke()

        reconcile.assert_not_called()
        self.assertIs(context.__exit__.call_args.args[0], RuntimeError)
        sql = "\n".join(str(call.args[0]) for call in connection.execute.call_args_list)
        self.assertNotIn("UPDATE run_lineage", sql)


if __name__ == "__main__":
    unittest.main()
