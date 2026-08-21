import unittest

from src.malaria_dl.governance.services.stage2_publication_service import (
    Stage2PublicationService,
)
from src.malaria_dl.governance.services.deployment_service import _project_path
from src.malaria_dl.common.paths import PROJECT_ROOT


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

    def test_historical_host_artifact_path_is_rebased_to_runtime_project(self):
        resolved = _project_path(
            "/historical/checkout/malaria_dl_local_project/outputs/model.keras"
        )
        self.assertEqual(resolved, PROJECT_ROOT / "outputs/model.keras")


if __name__ == "__main__":
    unittest.main()
