import base64
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


CAPSTONE_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = CAPSTONE_ROOT / "malaria_dl_local_project"
BACKEND_ROOT = CAPSTONE_ROOT / "backend_api"
for path in (PROJECT_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    from fastapi import HTTPException

    from app.routes.artifacts import artifact_file
    from app.routes.health import health
    from app.routes.predictions import uploaded_predictions
    from app.routes.runs import get_run_image_predictions, list_clinical_run_summary
except Exception as exc:  # pragma: no cover - exercised only when backend deps are missing.
    HTTPException = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


@unittest.skipIf(HTTPException is None, f"Dependencias backend no disponibles: {IMPORT_ERROR}")
class BackendEndpointTests(unittest.TestCase):
    def test_health_endpoint_uses_mocked_connection(self):
        with mock.patch(
            "app.routes.health.check_connection",
            return_value={"datasource": "malaria", "database": "test_db", "user": "tester"},
        ):
            response = health(datasource="malaria")

        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["database"], "test_db")

    def test_uploaded_predictions_endpoint_reads_clinical_view(self):
        row = {
            "prediction_id": "prediction-1",
            "run_id": "11111111-1111-1111-1111-111111111111",
            "model_name": "custom_cnn",
            "predicted_label": "parasitized",
            "probability_parasitized": 0.82,
            "probability_uninfected": 0.18,
            "quality_passed": True,
            "quality_warnings": [],
            "calibration_method": "none",
            "calibration_applied": False,
            "ensemble_applied": False,
            "tta_applied": False,
            "human_readable_response": "Compatible con celula parasitada.",
            "image_stored_path": "data/prediction_uploads/input.png",
            "image_original_path": "/tmp/input.png",
            "artifact_path": "data/prediction_uploads/input.png",
            "decision": "compatible_con_celula_parasitada",
            "tta": False,
        }

        with (
            mock.patch("app.routes.predictions.fetch_one", return_value={"total": 1}) as fetch_one,
            mock.patch("app.routes.predictions.fetch_all", return_value=[row]) as fetch_all,
        ):
            payload = uploaded_predictions(
                datasource="malaria",
                quality_passed=True,
                calibration_method="none",
                limit=10,
            )

        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["quality_passed"], True)
        self.assertEqual(payload["items"][0]["human_readable_response"], row["human_readable_response"])
        self.assertIn("vw_clinical_inference_predictions", fetch_one.call_args.args[1])
        self.assertIn("vw_clinical_inference_predictions", fetch_all.call_args.args[1])
        self.assertTrue(fetch_all.call_args.args[2]["quality_passed"])

    def test_clinical_run_summary_endpoint_reads_new_view(self):
        row = {
            "run_id": "11111111-1111-1111-1111-111111111111",
            "model_name": "custom_cnn",
            "run_type": "evaluation",
            "threshold_used": 0.42,
            "recall_parasitized": 0.97,
        }

        with mock.patch("app.routes.runs.fetch_all", return_value=[row]) as fetch_all:
            payload = list_clinical_run_summary(
                datasource="malaria",
                run_type="evaluation",
                model_name="custom_cnn",
                limit=10,
            )

        self.assertEqual(payload["items"][0]["threshold_used"], 0.42)
        self.assertIn("vw_clinical_run_summary", fetch_all.call_args.args[1])
        self.assertEqual(fetch_all.call_args.args[2]["run_type"], "evaluation")
        self.assertEqual(fetch_all.call_args.args[2]["model_name"], "custom_cnn")

    def test_run_image_predictions_endpoint_reads_new_view(self):
        row = {
            "run_id": "11111111-1111-1111-1111-111111111111",
            "filename": "0001.png",
            "predicted_label_name": "parasitized",
            "probability_parasitized": 0.91,
        }

        with mock.patch("app.routes.runs.fetch_all", return_value=[row]) as fetch_all:
            payload = get_run_image_predictions(
                run_id=row["run_id"],
                datasource="malaria",
                limit=10,
                offset=5,
            )

        self.assertEqual(payload["items"][0]["predicted_label_name"], "parasitized")
        self.assertIn("vw_run_image_predictions_summary", fetch_all.call_args.args[1])
        self.assertEqual(fetch_all.call_args.args[2]["limit"], 10)
        self.assertEqual(fetch_all.call_args.args[2]["offset"], 5)

    def test_artifact_endpoint_serves_allowed_png_path_fallback(self):
        outputs_dir = PROJECT_ROOT / "outputs"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=outputs_dir) as temp_dir:
            image_path = Path(temp_dir) / "artifact.png"
            image_path.write_bytes(PNG_1X1)
            relative_path = image_path.relative_to(CAPSTONE_ROOT).as_posix()

            response = artifact_file(datasource="malaria", artifact_id=None, path=relative_path)

        self.assertEqual(Path(response.path), image_path)
        self.assertEqual(response.media_type, "image/png")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")

    def test_artifact_endpoint_blocks_paths_outside_allowed_roots(self):
        with self.assertRaises(HTTPException) as context:
            artifact_file(
                datasource="malaria",
                artifact_id=None,
                path="malaria_dl_local_project/README.md",
            )

        self.assertEqual(context.exception.status_code, 403)

    def test_artifact_endpoint_rejects_fake_png_mime(self):
        outputs_dir = PROJECT_ROOT / "outputs"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=outputs_dir) as temp_dir:
            image_path = Path(temp_dir) / "fake.png"
            image_path.write_text("not a real png", encoding="utf-8")
            relative_path = image_path.relative_to(CAPSTONE_ROOT).as_posix()

            with self.assertRaises(HTTPException) as context:
                artifact_file(datasource="malaria", artifact_id=None, path=relative_path)

        self.assertEqual(context.exception.status_code, 415)


if __name__ == "__main__":
    unittest.main()
