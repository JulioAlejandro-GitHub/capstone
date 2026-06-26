import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import run_tracker  # noqa: E402
from src.config import RAW_MODEL_SCORE_MEANING  # noqa: E402
from src.tracking_integration import (  # noqa: E402
    artifact_record,
    record_image_predictions,
    record_output_artifacts,
)


class FakeTracker:
    def __init__(self):
        self.artifacts = []
        self.predictions = None

    def safe_track(self, function, *args, **kwargs):
        return function(*args, **kwargs)

    def log_artifact(self, *args, **kwargs):
        self.artifacts.append((args, kwargs))
        return f"artifact-{len(self.artifacts)}"

    def log_image_predictions(self, run_id, predictions):
        self.run_id = run_id
        self.predictions = predictions
        return {"total": len(predictions), "inserted": len(predictions)}


class ArtifactTrackingTests(unittest.TestCase):
    def test_artifact_record_includes_existence_and_size(self):
        path = PROJECT_ROOT / "README_2.md"

        record = artifact_record(path, artifact_type="documentation")

        self.assertEqual(record["artifact_type"], "documentation")
        self.assertEqual(record["path"], str(path))
        self.assertTrue(record["exists"])
        self.assertGreater(record["file_size_bytes"], 0)

    def test_record_output_artifacts_logs_each_path_with_exists_metadata(self):
        tracker = FakeTracker()
        context = {"run_id": "run-uuid", "tracker": tracker}

        artifact_ids = record_output_artifacts(
            context,
            [
                {
                    "artifact_type": "metrics_json",
                    "path": "outputs/metrics.json",
                    "exists": False,
                    "metadata": {"source": "unit-test"},
                }
            ],
        )

        self.assertEqual(artifact_ids, ["artifact-1"])
        args, kwargs = tracker.artifacts[0]
        self.assertEqual(args[0], "run-uuid")
        self.assertEqual(kwargs["artifact_type"], "metrics_json")
        self.assertFalse(kwargs["metadata"]["exists"])
        self.assertEqual(kwargs["metadata"]["source"], "unit-test")

    def test_record_image_predictions_delegates_sanitized_rows(self):
        tracker = FakeTracker()
        context = {"run_id": "run-uuid", "tracker": tracker}

        result = record_image_predictions(
            context,
            [
                {
                    "image_id": None,
                    "split_name": "external",
                    "usage_context": "inference",
                    "predicted_label": 1,
                    "predicted_label_name": "parasitized",
                    "probability_parasitized": 0.91,
                }
            ],
        )

        self.assertEqual(result["inserted"], 1)
        self.assertEqual(tracker.run_id, "run-uuid")
        self.assertEqual(tracker.predictions[0]["predicted_label"], 1)
        self.assertEqual(
            tracker.predictions[0]["predicted_label_name"],
            "parasitized",
        )

    def test_log_image_predictions_writes_probability_parasitized_rows(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.execute.return_value.first.return_value = ["image-prediction-id"]

        with patch("src.run_tracker.get_connection", return_value=connection):
            result = run_tracker.log_image_predictions(
                "run-uuid",
                [
                    {
                        "image_id": None,
                        "split_name": "external",
                        "usage_context": "inference",
                        "filename": "upload.png",
                        "true_label": 0,
                        "true_label_name": "uninfected",
                        "predicted_label": 1,
                        "predicted_label_name": "parasitized",
                        "probability_parasitized": 0.91,
                        "probability_uninfected": 0.09,
                        "raw_model_score": 0.91,
                        "threshold_used": 0.42,
                        "threshold_source": "validation_calibration",
                        "is_correct": False,
                        "case_type": "false_positive",
                        "metadata": {"source": "unit-test"},
                    }
                ],
            )

        self.assertEqual(result, {"total": 1, "inserted": 1})
        params = connection.execute.call_args.args[1]
        self.assertIsNone(params["image_id"])
        self.assertEqual(params["raw_model_score_meaning"], RAW_MODEL_SCORE_MEANING)
        self.assertEqual(params["probability_parasitized"], 0.91)
        self.assertEqual(params["threshold_used"], 0.42)
        self.assertFalse(params["is_correct"])
        self.assertEqual(json.loads(params["metadata"])["source"], "unit-test")


if __name__ == "__main__":
    unittest.main()
