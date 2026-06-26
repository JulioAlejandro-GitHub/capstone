import sys
import unittest
from argparse import Namespace
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import LABEL_MAPPING_VERSION, RAW_MODEL_SCORE_MEANING  # noqa: E402
from src.tracking_integration import args_to_parameters, record_run_io  # noqa: E402


class FakeTracker:
    def __init__(self):
        self.kwargs = None

    def get_command_line(self):
        return "python -m src.evaluate --track-db"

    def safe_track(self, function, *args, **kwargs):
        return function(*args, **kwargs)

    def log_run_io_record(self, run_id, **kwargs):
        self.run_id = run_id
        self.kwargs = kwargs
        return "run-io-id"


class RunIoTrackingTests(unittest.TestCase):
    def test_args_to_parameters_keeps_track_db(self):
        args = Namespace(track_db=True, img_size=200)

        params = args_to_parameters(args)

        self.assertTrue(params["track_db"])
        self.assertEqual(params["img_size"], 200)

    def test_record_run_io_serializes_input_and_output(self):
        tracker = FakeTracker()
        context = {
            "run_id": "run-uuid",
            "run_type": "evaluation",
            "model_name": "custom_cnn",
            "tracker": tracker,
        }

        run_io_id = record_run_io(
            context,
            script_name="src.evaluate",
            input_parameters={"checkpoint": Path("outputs/model.keras")},
            output_results={"confusion_matrix": np.asarray([[1, 0], [0, 1]])},
            output_artifacts=[{"path": Path("outputs/metrics.json")}],
            dataset_metadata={"data_source": "physical"},
            model_metadata={"architecture": "custom sequential CNN"},
            clinical_metadata={"threshold_used": np.float32(0.42)},
        )

        self.assertEqual(run_io_id, "run-io-id")
        self.assertEqual(tracker.run_id, "run-uuid")
        self.assertEqual(tracker.kwargs["script_name"], "src.evaluate")
        self.assertEqual(
            tracker.kwargs["input_parameters"]["checkpoint"],
            "outputs/model.keras",
        )
        self.assertEqual(
            tracker.kwargs["output_results"]["confusion_matrix"],
            [[1, 0], [0, 1]],
        )
        self.assertEqual(tracker.kwargs["run_type"], "evaluation")
        self.assertEqual(tracker.kwargs["model_name"], "custom_cnn")
        self.assertEqual(
            tracker.kwargs["model_metadata"]["architecture"],
            "custom sequential CNN",
        )
        self.assertAlmostEqual(tracker.kwargs["clinical_metadata"]["threshold_used"], 0.42)
        self.assertEqual(tracker.kwargs["label_mapping_version"], LABEL_MAPPING_VERSION)
        self.assertEqual(
            tracker.kwargs["raw_model_score_meaning"],
            RAW_MODEL_SCORE_MEANING,
        )


if __name__ == "__main__":
    unittest.main()
