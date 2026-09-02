import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.malaria_dl.evaluation import (  # noqa: E402
    evaluation_training_lineage_service as service,
)
from src.malaria_dl.evaluation.evaluation_finalization_service import (  # noqa: E402
    EvaluationRunNotFoundError,
    NotEvaluationRunError,
)


TRAIN = UUID("11111111-1111-4111-8111-111111111111")
EVALUATE = UUID("22222222-2222-4222-8222-222222222222")
VERSION = UUID("33333333-3333-4333-8333-333333333333")
ARTIFACT = UUID("44444444-4444-4444-8444-444444444444")
LINEAGE = UUID("55555555-5555-4555-8555-555555555555")
OTHER = UUID("66666666-6666-4666-8666-666666666666")


class FakeResult:
    def __init__(self, *, one=None, all_rows=None):
        self._one = one
        self._all = [] if all_rows is None else all_rows

    def mappings(self):
        return self

    def one_or_none(self):
        return self._one

    def all(self):
        return self._all


def identity_row(**overrides):
    row = {
        "lineage_id": LINEAGE,
        "training_run_id": TRAIN,
        "evaluation_run_id": EVALUATE,
        "relationship_type": service.EVALUATION_RELATIONSHIP_TYPE,
        "model_version_id": VERSION,
        "checkpoint_artifact_id": ARTIFACT,
        "checkpoint_path": "immutable/original.keras",
        "confidence": "explicit",
        "metadata": {"original": True},
    }
    row.update(overrides)
    return row


def connection_for(*, existing=None, inserted=None):
    connection = MagicMock()
    responses = [
        FakeResult(one={"id": EVALUATE, "run_type": "evaluation"}),
        FakeResult(one={"id": TRAIN, "run_type": "training"}),
        FakeResult(
            one={
                "model_version_id": VERSION,
                "training_run_id": TRAIN,
                "checkpoint_artifact_id": ARTIFACT,
            }
        ),
        FakeResult(
            one={
                "checkpoint_artifact_id": ARTIFACT,
                "training_run_id": TRAIN,
            }
        ),
        FakeResult(all_rows=[] if existing is None else existing),
    ]
    if inserted is not None:
        responses.append(FakeResult(one=inserted))
    connection.execute.side_effect = responses
    return connection


def invoke(connection, **overrides):
    kwargs = {
        "training_run_id": TRAIN,
        "evaluation_run_id": EVALUATE,
        "model_version_id": VERSION,
        "checkpoint_artifact_id": ARTIFACT,
        "checkpoint_path": "new/path.keras",
        "confidence": "explicit",
        "metadata": {"attempt": 1},
        "connection": connection,
    }
    kwargs.update(overrides)
    return service.create_or_confirm_evaluation_training_lineage(**kwargs)


class EvaluationTrainingLineageServiceTests(unittest.TestCase):
    def test_create_inserts_once_without_upsert_or_update(self):
        connection = connection_for(inserted=identity_row())

        result = invoke(connection)

        self.assertTrue(result.created)
        self.assertEqual(result.lineage_id, LINEAGE)
        self.assertEqual(result.training_run_id, TRAIN)
        insert_sql = str(connection.execute.call_args.args[0]).upper()
        self.assertIn("INSERT INTO RUN_LINEAGE", insert_sql)
        self.assertNotIn("ON CONFLICT", insert_sql)
        self.assertNotIn("UPDATE", insert_sql)
        params = connection.execute.call_args.args[1]
        self.assertEqual(params["model_version_id"], VERSION)
        self.assertEqual(params["checkpoint_artifact_id"], ARTIFACT)

    def test_exact_retry_is_read_only_and_preserves_descriptive_fields(self):
        original = identity_row()
        connection = connection_for(existing=[original])

        result = invoke(
            connection,
            checkpoint_path="changed/path.keras",
            confidence="unknown",
            metadata={"replacement": True},
        )

        self.assertFalse(result.created)
        self.assertEqual(connection.execute.call_count, 5)
        sql = "\n".join(str(call.args[0]) for call in connection.execute.call_args_list)
        self.assertNotIn("UPDATE run_lineage", sql)
        self.assertEqual(original["checkpoint_path"], "immutable/original.keras")
        self.assertEqual(original["metadata"], {"original": True})

    def test_parent_version_and_artifact_changes_are_conflicts(self):
        cases = (
            ("training_run_id", OTHER),
            ("model_version_id", OTHER),
            ("checkpoint_artifact_id", OTHER),
        )
        for field_name, changed in cases:
            with self.subTest(field_name=field_name):
                connection = connection_for(
                    existing=[identity_row(**{field_name: changed})]
                )
                with self.assertRaises(
                    service.EvaluationTrainingLineageConflictError
                ) as caught:
                    invoke(connection)
                self.assertIn(field_name, caught.exception.mismatched_fields)
                self.assertEqual(connection.execute.call_count, 5)

    def test_multiple_existing_parents_raise_cardinality_error_without_limit(self):
        connection = connection_for(
            existing=[identity_row(), identity_row(lineage_id=OTHER)]
        )

        with self.assertRaises(
            service.EvaluationTrainingLineageCardinalityError
        ) as caught:
            invoke(connection)

        self.assertEqual(caught.exception.count, 2)
        query = str(connection.execute.call_args.args[0]).upper()
        self.assertNotIn("LIMIT", query)
        self.assertNotIn("ORDER BY", query)

    def test_missing_and_wrong_run_types_are_domain_errors(self):
        for row, error in (
            (None, EvaluationRunNotFoundError),
            ({"id": EVALUATE, "run_type": "training"}, NotEvaluationRunError),
        ):
            with self.subTest(error=error.__name__):
                connection = MagicMock()
                connection.execute.return_value = FakeResult(one=row)
                with self.assertRaises(error):
                    invoke(connection)

        connection = MagicMock()
        connection.execute.side_effect = [
            FakeResult(one={"id": EVALUATE, "run_type": "evaluation"}),
            FakeResult(one=None),
        ]
        with self.assertRaises(service.TrainingRunNotFoundError):
            invoke(connection)

        connection = MagicMock()
        connection.execute.side_effect = [
            FakeResult(one={"id": EVALUATE, "run_type": "evaluation"}),
            FakeResult(one={"id": TRAIN, "run_type": "evaluation"}),
        ]
        with self.assertRaises(service.NotTrainingRunError):
            invoke(connection)

    def test_model_version_and_artifact_ownership_are_required(self):
        connection = MagicMock()
        connection.execute.side_effect = [
            FakeResult(one={"id": EVALUATE, "run_type": "evaluation"}),
            FakeResult(one={"id": TRAIN, "run_type": "training"}),
            FakeResult(one=None),
        ]
        with self.assertRaises(service.ModelVersionOwnershipError):
            invoke(connection)

        connection = MagicMock()
        connection.execute.side_effect = [
            FakeResult(one={"id": EVALUATE, "run_type": "evaluation"}),
            FakeResult(one={"id": TRAIN, "run_type": "training"}),
            FakeResult(
                one={
                    "model_version_id": VERSION,
                    "training_run_id": OTHER,
                    "checkpoint_artifact_id": ARTIFACT,
                }
            ),
        ]
        with self.assertRaises(service.ModelVersionOwnershipError):
            invoke(connection)

        connection = MagicMock()
        connection.execute.side_effect = [
            FakeResult(one={"id": EVALUATE, "run_type": "evaluation"}),
            FakeResult(one={"id": TRAIN, "run_type": "training"}),
            FakeResult(
                one={
                    "model_version_id": VERSION,
                    "training_run_id": TRAIN,
                    "checkpoint_artifact_id": OTHER,
                }
            ),
        ]
        with self.assertRaises(service.CheckpointArtifactOwnershipError):
            invoke(connection)

    def test_external_connection_is_never_managed(self):
        connection = connection_for(inserted=identity_row())
        with patch.object(service, "get_engine") as get_engine:
            invoke(connection)

        get_engine.assert_not_called()
        connection.commit.assert_not_called()
        connection.rollback.assert_not_called()
        connection.close.assert_not_called()

    def test_owned_transaction_commits_on_success_and_rolls_back_on_error(self):
        success_connection = connection_for(inserted=identity_row())
        success_context = MagicMock()
        success_context.__enter__.return_value = success_connection
        success_context.__exit__.return_value = False
        success_engine = MagicMock()
        success_engine.begin.return_value = success_context

        with patch.object(service, "get_engine", return_value=success_engine):
            result = service.create_or_confirm_evaluation_training_lineage(
                training_run_id=TRAIN,
                evaluation_run_id=EVALUATE,
                model_version_id=VERSION,
                checkpoint_artifact_id=ARTIFACT,
            )
        self.assertTrue(result.created)
        self.assertEqual(success_context.__exit__.call_args.args, (None, None, None))

        failed_connection = MagicMock()
        failed_connection.execute.side_effect = RuntimeError("database failure")
        failed_context = MagicMock()
        failed_context.__enter__.return_value = failed_connection
        failed_context.__exit__.return_value = False
        failed_engine = MagicMock()
        failed_engine.begin.return_value = failed_context

        with patch.object(service, "get_engine", return_value=failed_engine):
            with self.assertRaisesRegex(RuntimeError, "database failure"):
                service.create_or_confirm_evaluation_training_lineage(
                    training_run_id=TRAIN,
                    evaluation_run_id=EVALUATE,
                    model_version_id=VERSION,
                    checkpoint_artifact_id=ARTIFACT,
                )
        self.assertIs(failed_context.__exit__.call_args.args[0], RuntimeError)

    def test_rejects_invalid_identity_and_metadata_before_db_access(self):
        with patch.object(service, "get_engine") as get_engine:
            with self.assertRaises(
                service.EvaluationTrainingLineageDataIntegrityError
            ):
                service.create_or_confirm_evaluation_training_lineage(
                    training_run_id="not-a-uuid",
                    evaluation_run_id=EVALUATE,
                    model_version_id=VERSION,
                    checkpoint_artifact_id=ARTIFACT,
                )
            with self.assertRaises(
                service.EvaluationTrainingLineageDataIntegrityError
            ):
                service.create_or_confirm_evaluation_training_lineage(
                    training_run_id=TRAIN,
                    evaluation_run_id=TRAIN,
                    model_version_id=VERSION,
                    checkpoint_artifact_id=ARTIFACT,
                )
            with self.assertRaises(
                service.EvaluationTrainingLineageDataIntegrityError
            ):
                service.create_or_confirm_evaluation_training_lineage(
                    training_run_id=TRAIN,
                    evaluation_run_id=EVALUATE,
                    model_version_id=VERSION,
                    checkpoint_artifact_id=ARTIFACT,
                    metadata="not-a-mapping",
                )
        get_engine.assert_not_called()


if __name__ == "__main__":
    unittest.main()
