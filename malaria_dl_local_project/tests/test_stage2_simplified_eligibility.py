import unittest
from contextlib import contextmanager

from src.stage2_model_availability_service import Stage2ModelAvailabilityService


class Result:
    def __init__(self, *, row=None, rows=None, scalar=None):
        self.row, self.rows, self.scalar = row, rows or [], scalar
    def mappings(self): return self
    def one_or_none(self): return self.row
    def scalars(self): return self
    def all(self): return self.rows
    def scalar_one_or_none(self): return self.scalar


class Connection:
    def __init__(self, training, evaluation):
        self.training, self.evaluation, self.calls = training, evaluation, 0
    def execute(self, statement, params=None):
        sql = str(statement)
        if "SELECT r.*" in sql: return Result(row=self.training)
        if "evaluates_checkpoint_from" in sql: return Result(row=self.evaluation)
        if "explains_checkpoint_from" in sql: return Result(rows=[])
        if "FROM model_versions" in sql: return Result(rows=[])
        if "FROM deployed_model_versions" in sql: return Result(scalar=None)
        raise AssertionError(sql)


class SimplifiedEligibilityTests(unittest.TestCase):
    training_id = "371a9e75-2e87-4c22-b1d0-8f249007cc33"
    evaluation_id = "11111111-1111-4111-8111-111111111111"

    def service(self, training_status="completed", evaluation_status="completed"):
        training = {
            "id": self.training_id, "run_type": "training", "status": training_status,
            "run_name": "real_train", "model_name": "custom_cnn", "metadata": {},
        }
        evaluation = None if evaluation_status is None else {
            "evaluation_run_id": self.evaluation_id, "status": evaluation_status,
        }
        connection = Connection(training, evaluation)
        @contextmanager
        def factory():
            yield connection
        return Stage2ModelAvailabilityService(
            factory, environment="production", alias="champion",
            production_scope="stage2_technical",
        )

    def test_completed_train_and_linked_completed_evaluate_are_eligible(self):
        status = self.service().preview(self.training_id)
        self.assertTrue(status["eligible_for_stage2_production"])
        self.assertEqual(status["evaluation_run_id"], self.evaluation_id)
        self.assertEqual(status["explainability_run_ids"], [])

    def test_missing_evaluate_is_not_eligible(self):
        status = self.service(evaluation_status=None).preview(self.training_id)
        self.assertFalse(status["eligible"])
        self.assertEqual(status["blockers"][0]["code"], "EVALUATION_REQUIRED")

    def test_incomplete_train_is_not_eligible_even_with_evaluate(self):
        status = self.service(training_status="started").preview(self.training_id)
        self.assertFalse(status["eligible"])
        self.assertEqual(status["blockers"][0]["code"], "TRAINING_NOT_COMPLETED")

    def test_explain_is_not_required(self):
        status = self.service().preview(self.training_id)
        self.assertNotIn("EXPLAIN", " ".join(item["code"] for item in status["blockers"]))


if __name__ == "__main__":
    unittest.main()
