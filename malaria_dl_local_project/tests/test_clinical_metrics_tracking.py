import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import run_tracker  # noqa: E402
from src.config import LABEL_MAPPING_VERSION, RAW_MODEL_SCORE_MEANING  # noqa: E402
from src.tracking_integration import record_clinical_metrics  # noqa: E402


class FakeTracker:
    def __init__(self):
        self.calls = []

    def safe_track(self, function, *args, **kwargs):
        self.calls.append((function.__name__, args, kwargs))
        return function(*args, **kwargs)

    def log_clinical_metrics(self, *args, **kwargs):
        self.logged_args = args
        self.logged_kwargs = kwargs
        return "clinical-metric-id"


class ClinicalMetricsTrackingTests(unittest.TestCase):
    def test_record_clinical_metrics_passes_context_and_threshold(self):
        tracker = FakeTracker()
        context = {
            "run_id": "run-uuid",
            "model_id": "model-uuid",
            "model_name": "custom_cnn",
            "tracker": tracker,
        }

        result = record_clinical_metrics(
            context,
            {"recall_parasitized": 0.99, "threshold_used": 0.42},
            split_name="validation",
            threshold_source="validation_calibration",
        )

        self.assertEqual(result, "clinical-metric-id")
        self.assertEqual(tracker.logged_args[0], "run-uuid")
        self.assertEqual(tracker.logged_kwargs["split_name"], "val")
        self.assertEqual(tracker.logged_kwargs["model_id"], "model-uuid")
        self.assertEqual(tracker.logged_kwargs["model_name"], "custom_cnn")
        self.assertEqual(
            tracker.logged_kwargs["threshold_source"],
            "validation_calibration",
        )

    def test_log_clinical_metrics_maps_confusion_matrix_and_json_payloads(self):
        metrics = {
            "accuracy": 0.95,
            "precision_parasitized": 0.96,
            "recall_parasitized": 0.97,
            "sensitivity_parasitized": 0.97,
            "specificity": 0.93,
            "f2_parasitized": 0.98,
            "balanced_accuracy": 0.95,
            "confusion_matrix": [[10, 2], [1, 20]],
            "classification_report_dict": {"parasitized": {"recall": 0.97}},
            "prediction_collapse": {"collapsed": False},
            "threshold_used": 0.42,
            "threshold_source": "validation_calibration",
        }

        with patch(
            "src.run_tracker._execute_returning_id",
            return_value="clinical-metric-id",
        ) as execute:
            result = run_tracker.log_clinical_metrics(
                "run-uuid",
                metrics,
                split_name="test",
                model_id="model-uuid",
                model_name="custom_cnn",
            )

        self.assertEqual(result, "clinical-metric-id")
        sql, params = execute.call_args.args
        self.assertIn("INSERT INTO run_clinical_metrics", sql)
        self.assertEqual(params["tn"], 10)
        self.assertEqual(params["fp"], 2)
        self.assertEqual(params["fn"], 1)
        self.assertEqual(params["tp"], 20)
        self.assertEqual(params["threshold_used"], 0.42)
        self.assertEqual(params["label_mapping_version"], LABEL_MAPPING_VERSION)
        self.assertEqual(params["raw_model_score_meaning"], RAW_MODEL_SCORE_MEANING)
        self.assertEqual(json.loads(params["confusion_matrix"]), [[10, 2], [1, 20]])
        self.assertFalse(json.loads(params["prediction_collapse"])["collapsed"])


if __name__ == "__main__":
    unittest.main()
