import sys
import unittest
from pathlib import Path
from unittest import mock


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.routes.runs import (  # noqa: E402
    get_run_artifacts_summary,
    get_run_checkpoint_policy,
    get_run_image_predictions,
    get_run_threshold_calibration,
)


RUN_ID = "11111111-1111-1111-1111-111111111111"


class RunDetailApiTests(unittest.TestCase):
    def test_checkpoint_policy_endpoint_returns_policy(self):
        with mock.patch(
            "app.routes.runs.fetch_all",
            return_value=[{"run_id": RUN_ID, "checkpoint_policy": "auc_with_min_recall"}],
        ):
            payload = get_run_checkpoint_policy(run_id=RUN_ID, datasource="malaria")

        self.assertEqual(payload["items"][0]["checkpoint_policy"], "auc_with_min_recall")

    def test_threshold_calibration_endpoint_returns_threshold_selected(self):
        with mock.patch(
            "app.routes.runs.fetch_all",
            return_value=[{"run_id": RUN_ID, "threshold_selected": 0.32}],
        ):
            payload = get_run_threshold_calibration(run_id=RUN_ID, datasource="malaria")

        self.assertEqual(payload["items"][0]["threshold_selected"], 0.32)

    def test_artifacts_endpoint_lists_artifacts(self):
        with mock.patch(
            "app.routes.runs.fetch_all",
            return_value=[{"artifact_type": "metrics_json", "artifact_path": "outputs/metrics.json"}],
        ):
            payload = get_run_artifacts_summary(run_id=RUN_ID, datasource="malaria")

        self.assertEqual(payload["items"][0]["artifact_type"], "metrics_json")

    def test_image_predictions_endpoint_paginates_and_filters(self):
        with (
            mock.patch("app.routes.runs.fetch_one", return_value={"total": 1}),
            mock.patch(
                "app.routes.runs.fetch_all",
                return_value=[
                    {
                        "filename": "0001.png",
                        "case_type": "false_negative",
                        "probability_parasitized": 0.21,
                    }
                ],
            ) as fetch_all,
        ):
            payload = get_run_image_predictions(
                run_id=RUN_ID,
                datasource="malaria",
                split="test",
                case_type="false_negative",
                class_name="parasitized",
                is_correct=False,
                limit=25,
                offset=50,
            )

        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["limit"], 25)
        self.assertEqual(payload["offset"], 50)
        self.assertEqual(payload["items"][0]["case_type"], "false_negative")
        params = fetch_all.call_args.args[2]
        self.assertEqual(params["split"], "test")
        self.assertEqual(params["case_type"], "false_negative")
        self.assertEqual(params["class_name"], "parasitized")
        self.assertIs(params["is_correct"], False)


if __name__ == "__main__":
    unittest.main()
