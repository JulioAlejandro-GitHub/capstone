import unittest
from uuid import uuid4

from src.malaria_dl.governance.services.stage2_publication_service import (
    Stage2PublicationService,
)


class Stage2PublicationEligibilityTests(unittest.TestCase):
    def eligibility(self, train="completed", evaluation="completed", evaluation_id="eval"):
        return Stage2PublicationService._eligibility({
            "train_status": train,
            "evaluation_status": evaluation,
            "evaluation_run_id": evaluation_id,
            # EXPLAIN, signatures, runtime and metrics are intentionally absent.
        })

    def test_only_completed_train_and_evaluate_are_required(self):
        eligible, detail = self.eligibility()
        self.assertTrue(eligible)
        self.assertEqual(detail["missing_conditions"], [])

    def test_evaluate_is_required(self):
        eligible, detail = self.eligibility(evaluation=None, evaluation_id=None)
        self.assertFalse(eligible)
        self.assertEqual(detail["missing_conditions"], ["EVALUATE no encontrado"])

    def test_pending_evaluate_is_not_eligible(self):
        eligible, detail = self.eligibility(evaluation="pending")
        self.assertFalse(eligible)
        self.assertEqual(detail["missing_conditions"], ["EVALUATE no completado"])

    def test_incomplete_train_is_not_eligible(self):
        eligible, detail = self.eligibility(train="failed")
        self.assertFalse(eligible)
        self.assertEqual(detail["missing_conditions"], ["TRAIN no completado"])

    def test_explain_signatures_tensorflow_and_metrics_do_not_participate(self):
        eligible, _ = self.eligibility()
        self.assertTrue(eligible)

    def test_response_exposes_publication_identity_without_deployment(self):
        service = Stage2PublicationService(lambda: None)
        publication_id = uuid4()
        response = service._response(
            {
                "model_version_id": str(uuid4()),
                "training_run_id": str(uuid4()),
                "evaluation_run_id": str(uuid4()),
                "checkpoint_artifact_id": str(uuid4()),
                "checkpoint_name": "model.keras",
                "model_name": "custom_cnn",
                "version_number": 1,
                "train_status": "completed",
                "evaluation_status": "completed",
            },
            {
                "id": publication_id,
                "status": "active",
                "is_active": True,
                "published_at": "2026-08-04T12:00:00+00:00",
            },
        )

        self.assertTrue(response["eligible"])
        self.assertEqual(response["blockers"], [])
        self.assertEqual(response["publication_id"], str(publication_id))
        self.assertEqual(response["publication_status"], "active")
        self.assertNotIn("deployment_id", response)

    def test_evaluate_lookup_is_bound_to_published_model_and_checkpoint(self):
        model_version_id = str(uuid4())
        training_run_id = str(uuid4())
        checkpoint_artifact_id = str(uuid4())
        evaluation_run_id = str(uuid4())
        statements = []

        class Result:
            def __init__(self, row):
                self.row = row

            def mappings(self):
                return self

            def one_or_none(self):
                return self.row

        class Connection:
            def execute(self, statement, params):
                statements.append((" ".join(str(statement).split()), params))
                if len(statements) == 1:
                    return Result({
                        "model_version_id": model_version_id,
                        "training_run_id": training_run_id,
                        "checkpoint_artifact_id": checkpoint_artifact_id,
                        "model_name": "custom_cnn",
                        "version_number": 1,
                        "checkpoint_name": "model.keras",
                        "train_status": "completed",
                    })
                return Result({
                    "evaluation_run_id": evaluation_run_id,
                    "evaluation_status": "completed",
                })

        context = Stage2PublicationService(lambda: None)._context(
            Connection(), model_version_id
        )

        evaluation_sql, evaluation_params = statements[1]
        self.assertIn(
            "lineage.model_version_id=CAST(:model_version AS uuid)",
            evaluation_sql,
        )
        self.assertIn(
            "lineage.checkpoint_artifact_id=CAST(:checkpoint AS uuid)",
            evaluation_sql,
        )
        self.assertEqual(evaluation_params, {
            "training": training_run_id,
            "model_version": model_version_id,
            "checkpoint": checkpoint_artifact_id,
        })
        self.assertEqual(context["evaluation_run_id"], evaluation_run_id)


if __name__ == "__main__":
    unittest.main()
