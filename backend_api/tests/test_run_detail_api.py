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
    get_run_explainability,
    get_run_image_predictions,
    get_run_threshold_calibration,
    list_runs,
)


RUN_ID = "11111111-1111-1111-1111-111111111111"


class RunDetailApiTests(unittest.TestCase):
    def test_list_runs_exposes_compact_report_contract_without_n_plus_one(self):
        row = {
            "run_id": RUN_ID,
            "command": "python -m src.train --model custom_cnn --max-epochs 50",
            "optimizer": "adam",
            "recall_parasitized": 0.98,
            "specificity": 0.81,
            "f2_parasitized": 0.95,
            "roc_auc_parasitized": 0.97,
            "tn": 100,
            "fp": 20,
            "fn": 2,
            "tp": 118,
            "confusion_matrix": [[100, 20], [2, 118]],
        }
        with mock.patch("app.routes.runs.fetch_all", return_value=[row]) as fetch_all:
            payload = list_runs(datasource="malaria", limit=100)

        self.assertEqual(payload["items"][0]["command"], row["command"])
        self.assertEqual(payload["items"][0]["specificity"], 0.81)
        self.assertEqual(payload["items"][0]["confusion_matrix"], row["confusion_matrix"])
        sql = fetch_all.call_args.args[1]
        self.assertIn("WITH page AS", sql)
        self.assertIn("r.command", sql)
        self.assertIn("run_clinical_metrics", sql)
        self.assertIn("confusion_matrices", sql)
        self.assertIn("cm.split_name = clinical.split_name", sql)
        self.assertIn(") selected_confusion ON TRUE", sql)
        self.assertNotIn("COALESCE(clinical.tn, legacy.true_negative)", sql)
        self.assertEqual(fetch_all.call_count, 1)

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

    def test_run_explainability_uses_visual_audit_contract(self):
        scope = [{"run_id": RUN_ID, "model_version_id": "version-1"}]
        cases = [
            {
                "explainability_id": "explain-1",
                "run_id": RUN_ID,
                "method": "gradcam",
                "case_type": "true_positive",
                "image_path": "data/source/cell.png",
                "explanation_output_path": "outputs/explainability/cell.png",
                "_total_count": 2,
            },
            {
                "explainability_id": "explain-2",
                "run_id": RUN_ID,
                "method": "lime",
                "case_type": "true_positive",
                "image_path": "data/source/cell.png",
                "explanation_output_path": "outputs/explainability/cell-lime.png",
                "_total_count": 2,
            },
        ]
        with (
            mock.patch(
                "app.services.explainability.resolve_artifact_reference",
                return_value=mock.Mock(),
            ),
            mock.patch(
                "app.routes.runs.fetch_all",
                side_effect=[scope, cases],
            ) as fetch_all,
        ):
            payload = get_run_explainability(
                run_id=RUN_ID,
                datasource="malaria",
                method=None,
                case_type=None,
                limit=25,
                offset=0,
                compact=True,
            )

        self.assertEqual(fetch_all.call_count, 2)
        scope_sql = fetch_all.call_args_list[0].args[1]
        audit_sql = fetch_all.call_args_list[1].args[1]
        self.assertIn("requested.run_type = 'training'", scope_sql)
        self.assertIn("requested.run_type = 'evaluation'", scope_sql)
        self.assertIn("evaluation.model_version_id IS NOT NULL", scope_sql)
        self.assertIn("evaluation.checkpoint_artifact_id IS NOT NULL", scope_sql)
        self.assertIn("evaluation.checkpoint_path IS NOT NULL", scope_sql)
        self.assertIn("child.dataset_version_id = evaluation.dataset_version_id", scope_sql)
        self.assertIn("vw_visual_explainability_audit", audit_sql)
        self.assertIn("COUNT(*) OVER ()", audit_sql)
        self.assertNotIn("SELECT COUNT(*) AS total", audit_sql)
        self.assertNotIn("audit.*", audit_sql)
        self.assertIn("audit.explanation_parameters", audit_sql)
        self.assertEqual(
            fetch_all.call_args_list[1].args[2]["scope_run_id_0"],
            RUN_ID,
        )
        self.assertEqual(payload["total"], 2)
        self.assertTrue(all("_total_count" not in item for item in payload["items"]))
        self.assertEqual(
            payload["items"][0]["image_url"],
            "/artifacts/file?path=data/source/cell.png",
        )
        self.assertIn("región microscópica plausible", payload["items"][0]["interpretation"])

    def test_run_explainability_keeps_total_for_an_out_of_range_page(self):
        scope = [{"run_id": RUN_ID, "model_version_id": None}]
        with (
            mock.patch(
                "app.routes.runs.fetch_all",
                side_effect=[scope, []],
            ) as fetch_all,
            mock.patch(
                "app.routes.runs.fetch_one", return_value={"total": 150}
            ) as fetch_one,
        ):
            payload = get_run_explainability(
                run_id=RUN_ID,
                datasource="malaria",
                method=None,
                case_type=None,
                limit=25,
                offset=200,
                compact=True,
            )

        self.assertEqual(fetch_all.call_count, 2)
        self.assertEqual(fetch_one.call_count, 1)
        self.assertIn("SELECT COUNT(*) AS total", fetch_one.call_args.args[1])
        self.assertEqual(payload["items"], [])
        self.assertEqual(payload["total"], 150)

    def test_run_explainability_returns_empty_when_run_does_not_exist(self):
        with mock.patch("app.routes.runs.fetch_all", return_value=[]) as fetch_all:
            payload = get_run_explainability(
                run_id=RUN_ID,
                datasource="malaria",
                method=None,
                case_type=None,
                limit=25,
                offset=0,
                compact=True,
            )

        self.assertEqual(fetch_all.call_count, 1)
        self.assertEqual(
            payload,
            {"items": [], "total": 0, "limit": 25, "offset": 0},
        )


if __name__ == "__main__":
    unittest.main()
