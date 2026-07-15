import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from fastapi import HTTPException


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.routes.explainability import (  # noqa: E402
    explainability_cases,
    explainability_gallery,
    false_positive_cases,
    low_confidence_cases,
)


RUN_ID = "11111111-1111-1111-1111-111111111111"


def endpoint_arguments(**overrides):
    arguments = {
        "datasource": "malaria",
        "model_name": None,
        "dataset_name": None,
        "method": None,
        "case_type": None,
        "run_id": None,
        "true_label": None,
        "predicted_label": None,
        "threshold_source": None,
        "success": None,
        "date_from": None,
        "date_to": None,
        "limit": 50,
        "offset": 0,
    }
    arguments.update(overrides)
    return arguments


class ExplainabilityApiTests(unittest.TestCase):
    def test_cases_return_visual_audit_contract_and_encoded_urls(self):
        row = {
            "explainability_id": "explain-1",
            "run_id": RUN_ID,
            "model_name": "vgg16",
            "dataset_name": "malaria",
            "method": "gradcam",
            "case_type": "false_positive",
            "true_label": "uninfected",
            "predicted_label": "parasitized",
            "positive_label": "parasitized",
            "score_positive_label": 0.91,
            "threshold": 0.5,
            "threshold_source": "fixed_cli",
            "image_path": "data/crops/cell 01.png",
            "explanation_output_path": "malaria_dl_local_project/outputs/maps/cell&01.png",
            "prediction_metadata": {
                "source_image_path": "data/source/original 01.jpg",
                "crop_path": "data/crops/cell 01.png",
                "patient_id": "patient-7",
            },
            "last_conv_layer": "block5_conv3",
            "success": True,
            "error_message": None,
            "started_at": "2026-07-15T10:00:00+00:00",
        }

        with (
            mock.patch("app.routes.explainability.fetch_one", return_value={"total": 1}),
            mock.patch("app.routes.explainability.fetch_all", return_value=[row]) as fetch_all,
        ):
            payload = explainability_cases(**endpoint_arguments())

        item = payload["items"][0]
        self.assertEqual(payload["total"], 1)
        self.assertEqual(item["probability_parasitized"], 0.91)
        self.assertAlmostEqual(item["probability_uninfected"], 0.09)
        self.assertEqual(item["image_url"], "/artifacts/file?path=data/crops/cell%2001.png")
        self.assertEqual(
            item["explanation_url"],
            "/artifacts/file?path=malaria_dl_local_project/outputs/maps/cell%2601.png",
        )
        self.assertEqual(item["source_image_path"], "data/source/original 01.jpg")
        self.assertEqual(item["crop_url"], "/artifacts/file?path=data/crops/cell%2001.png")
        self.assertEqual(item["patient_id"], "patient-7")
        self.assertIn("posible confusión visual", item["interpretation"])
        self.assertIn("vw_visual_explainability_audit", fetch_all.call_args.args[1])

    def test_gallery_is_null_safe_when_image_path_is_missing(self):
        row = {
            "gallery_id": "gallery-1",
            "case_type": "low_confidence",
            "image_path": None,
            "explanation_output_path": "malaria_dl_local_project/outputs/maps/map.webp",
        }
        with (
            mock.patch("app.routes.explainability.fetch_one", return_value={"total": 1}),
            mock.patch("app.routes.explainability.fetch_all", return_value=[row]),
        ):
            payload = explainability_gallery(**endpoint_arguments())

        item = payload["items"][0]
        self.assertEqual(item["explainability_id"], "gallery-1")
        self.assertIsNone(item["image_path"])
        self.assertIsNone(item["image_url"])
        self.assertIsNone(item["source_image_url"])
        self.assertTrue(item["explanation_url"].endswith("/maps/map.webp"))

    def test_stored_image_precedes_external_original_in_source_fallback(self):
        row = {
            "explainability_id": "explain-2",
            "image_path": None,
            "prediction_metadata": {
                "original_image_path": "/external/scanner/private-slide.png",
                "image_stored_path": "data/prediction_uploads/safe-copy.png",
            },
        }
        with (
            mock.patch("app.routes.explainability.fetch_one", return_value={"total": 1}),
            mock.patch("app.routes.explainability.fetch_all", return_value=[row]),
        ):
            payload = explainability_cases(**endpoint_arguments())

        item = payload["items"][0]
        self.assertEqual(
            item["source_image_path"],
            "data/prediction_uploads/safe-copy.png",
        )
        self.assertEqual(
            item["source_image_url"],
            "/artifacts/file?path=data/prediction_uploads/safe-copy.png",
        )
        self.assertEqual(
            item["original_image_path"],
            "/external/scanner/private-slide.png",
        )

    def test_false_positive_endpoint_forces_case_type_on_shared_view(self):
        with (
            mock.patch("app.routes.explainability.fetch_one", return_value={"total": 0}),
            mock.patch("app.routes.explainability.fetch_all", return_value=[]) as fetch_all,
        ):
            false_positive_cases(
                **endpoint_arguments(case_type="true_positive", threshold_source="fixed_cli")
            )

        sql = fetch_all.call_args.args[1]
        params = fetch_all.call_args.args[2]
        self.assertIn("vw_visual_explainability_audit", sql)
        self.assertIn("case_type = :case_type", sql)
        self.assertEqual(params["case_type"], "false_positive")
        self.assertEqual(params["threshold_source"], "fixed_cli")

    def test_low_confidence_endpoint_keeps_distance_rule(self):
        with (
            mock.patch("app.routes.explainability.fetch_one", return_value={"total": 0}),
            mock.patch("app.routes.explainability.fetch_all", return_value=[]) as fetch_all,
        ):
            low_confidence_cases(**endpoint_arguments())

        self.assertIn("confidence_distance <= 0.10", fetch_all.call_args.args[1])

    def test_gallery_low_confidence_filter_keeps_distance_rule(self):
        with (
            mock.patch("app.routes.explainability.fetch_one", return_value={"total": 0}),
            mock.patch("app.routes.explainability.fetch_all", return_value=[]) as fetch_all,
        ):
            explainability_gallery(
                **endpoint_arguments(case_type="low_confidence")
            )

        sql = fetch_all.call_args.args[1]
        params = fetch_all.call_args.args[2]
        self.assertIn("confidence_distance <= 0.10", sql)
        self.assertNotIn("case_type", params)

    def test_filters_support_uuid_threshold_source_and_inclusive_date_range(self):
        with (
            mock.patch("app.routes.explainability.fetch_one", return_value={"total": 0}),
            mock.patch("app.routes.explainability.fetch_all", return_value=[]) as fetch_all,
        ):
            explainability_cases(
                **endpoint_arguments(
                    run_id=RUN_ID,
                    threshold_source="validation_calibration",
                    date_from="2026-07-01",
                    date_to="2026-07-15",
                )
            )

        sql = fetch_all.call_args.args[1]
        params = fetch_all.call_args.args[2]
        self.assertIn("run_id = CAST(:run_id AS uuid)", sql)
        self.assertIn("threshold_source = :threshold_source", sql)
        self.assertIn("started_at >= :date_from", sql)
        self.assertIn("started_at < :date_to", sql)
        self.assertEqual(params["run_id"], RUN_ID)
        self.assertEqual(params["date_from"], datetime(2026, 7, 1))
        self.assertEqual(params["date_to"], datetime(2026, 7, 16))

    def test_invalid_run_id_returns_422_before_querying_database(self):
        with mock.patch("app.routes.explainability.fetch_one") as fetch_one:
            with self.assertRaises(HTTPException) as context:
                explainability_cases(**endpoint_arguments(run_id="not-a-uuid"))

        self.assertEqual(context.exception.status_code, 422)
        fetch_one.assert_not_called()


if __name__ == "__main__":
    unittest.main()
