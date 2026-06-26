import sys
import unittest
from pathlib import Path
from unittest import mock


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.routes.catalog import model_comparison  # noqa: E402
from app.routes.dashboard import clinical_dashboard  # noqa: E402


class ModelComparisonApiTests(unittest.TestCase):
    def test_model_comparison_api_reads_clinical_run_summary(self):
        row = {
            "run_id": "11111111-1111-1111-1111-111111111111",
            "model_name": "custom_cnn",
            "f2_parasitized": 0.97,
            "pr_auc_parasitized": 0.96,
        }

        with mock.patch("app.routes.catalog.fetch_all", return_value=[row]) as fetch_all:
            payload = model_comparison(datasource="malaria", limit=10)

        self.assertEqual(payload["items"][0]["f2_parasitized"], 0.97)
        self.assertIn("vw_clinical_run_summary", fetch_all.call_args.args[1])

    def test_clinical_dashboard_returns_latest_run_and_warnings(self):
        rows = [
            {
                "run_id": "11111111-1111-1111-1111-111111111111",
                "model_name": "custom_cnn",
                "prediction_collapse_detected": True,
                "checkpoint_warning": "fallback checkpoint",
                "threshold_warning": None,
            }
        ]

        with mock.patch("app.routes.dashboard.fetch_all", return_value=rows):
            payload = clinical_dashboard(datasource="malaria", limit=5)

        self.assertEqual(payload["latest_run"]["model_name"], "custom_cnn")
        self.assertEqual(payload["label_mapping"]["1"], "parasitized")
        self.assertEqual(len(payload["warnings"]), 2)


if __name__ == "__main__":
    unittest.main()
