import sys
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.routes.runs import get_run_clinical_summary  # noqa: E402


RUN_ID = "11111111-1111-1111-1111-111111111111"


class ClinicalSummaryApiTests(unittest.TestCase):
    def test_clinical_summary_returns_label_mapping_and_clinical_metrics(self):
        run = {
            "id": RUN_ID,
            "model_name": "custom_cnn",
            "script_name": "src.evaluate",
            "run_type": "evaluation",
            "status": "completed",
            "started_at": "2026-06-26T10:00:00",
            "finished_at": "2026-06-26T10:20:00",
        }
        clinical_metric = {
            "accuracy": 0.94,
            "precision_parasitized": 0.93,
            "recall_parasitized": 0.98,
            "sensitivity_parasitized": 0.98,
            "specificity": 0.91,
            "f2_parasitized": 0.97,
            "pr_auc_parasitized": 0.96,
            "roc_auc_parasitized": 0.98,
            "balanced_accuracy": 0.945,
            "prediction_collapse_detected": False,
            "confusion_matrix": [[1260, 125], [26, 1345]],
            "tn": 1260,
            "fp": 125,
            "fn": 26,
            "tp": 1345,
            "threshold_used": 0.32,
        }
        checkpoint = {
            "checkpoint_policy": "auc_with_min_recall",
            "min_recall_required": 0.98,
            "selected_epoch": 12,
            "policy_satisfied": True,
            "selected_metric": "val_auc",
            "selected_metric_value": 0.982,
            "checkpoint_warning": None,
        }
        threshold = {
            "threshold_source": "validation_calibration",
            "threshold_selected": 0.32,
            "default_threshold": 0.5,
            "target_recall": 0.98,
            "target_recall_satisfied": True,
            "validation_specificity_at_threshold": 0.91,
            "threshold_warning": None,
        }

        with (
            mock.patch(
                "app.routes.runs.fetch_one",
                side_effect=[run, {"total": 8}, {"total": 2756}],
            ),
            mock.patch(
                "app.routes.runs.fetch_all",
                side_effect=[[clinical_metric], [checkpoint], [threshold]],
            ),
        ):
            payload = get_run_clinical_summary(run_id=RUN_ID, datasource="malaria")

        self.assertEqual(payload["run_id"], RUN_ID)
        self.assertEqual(payload["label_mapping"]["0"], "uninfected")
        self.assertEqual(payload["label_mapping"]["1"], "parasitized")
        self.assertEqual(payload["label_mapping"]["positive_class_index"], 1)
        self.assertEqual(payload["label_mapping"]["raw_model_score_meaning"], "probability_parasitized")
        self.assertEqual(payload["clinical_metrics"]["f2_parasitized"], 0.97)
        self.assertEqual(payload["clinical_metrics"]["pr_auc_parasitized"], 0.96)
        self.assertEqual(payload["confusion_matrix"]["fn"], 26)
        self.assertEqual(payload["checkpoint_policy"]["policy"], "auc_with_min_recall")
        self.assertEqual(payload["clinical_threshold"]["threshold_selected"], 0.32)
        self.assertEqual(payload["artifacts_count"], 8)
        self.assertEqual(payload["image_predictions_count"], 2756)

    def test_clinical_summary_missing_run_returns_404(self):
        with mock.patch("app.routes.runs.fetch_one", return_value=None):
            with self.assertRaises(HTTPException) as context:
                get_run_clinical_summary(run_id=RUN_ID, datasource="malaria")

        self.assertEqual(context.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
