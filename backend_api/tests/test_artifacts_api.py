import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.routes.artifacts import artifact_file  # noqa: E402
from app.services import artifacts  # noqa: E402


PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8


class ArtifactFileApiTests(unittest.TestCase):
    def test_allowed_image_returns_file_response_with_safe_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            allowed_root = Path(directory).resolve()
            image_path = allowed_root / "audit image.png"
            image_path.write_bytes(PNG_HEADER)

            with mock.patch.object(artifacts, "ALLOWED_ARTIFACT_ROOTS", (allowed_root,)):
                response = artifact_file(
                    datasource="malaria",
                    artifact_id=None,
                    path=str(image_path),
                )

            self.assertEqual(Path(response.path), image_path)
            self.assertEqual(response.media_type, "image/png")
            self.assertEqual(response.headers["x-content-type-options"], "nosniff")

    def test_path_traversal_is_forbidden(self):
        with tempfile.TemporaryDirectory() as directory:
            temp_root = Path(directory).resolve()
            allowed_root = temp_root / "allowed"
            allowed_root.mkdir()
            outside_image = temp_root / "secret.png"
            outside_image.write_bytes(PNG_HEADER)
            traversal_path = allowed_root / ".." / outside_image.name

            with mock.patch.object(artifacts, "ALLOWED_ARTIFACT_ROOTS", (allowed_root,)):
                with self.assertRaises(HTTPException) as context:
                    artifacts.resolve_artifact_reference(path=str(traversal_path))

            self.assertEqual(context.exception.status_code, 403)

    def test_missing_file_inside_allowed_root_returns_404(self):
        with tempfile.TemporaryDirectory() as directory:
            allowed_root = Path(directory).resolve()

            with mock.patch.object(artifacts, "ALLOWED_ARTIFACT_ROOTS", (allowed_root,)):
                with self.assertRaises(HTTPException) as context:
                    artifacts.resolve_artifact_reference(path=str(allowed_root / "missing.png"))

            self.assertEqual(context.exception.status_code, 404)

    def test_historical_absolute_project_path_is_safely_rebased(self):
        with tempfile.TemporaryDirectory() as directory:
            current_project = Path(directory).resolve() / "malaria_dl_local_project"
            current_data = current_project / "data"
            image_path = current_data / "split" / "case.png"
            image_path.parent.mkdir(parents=True)
            image_path.write_bytes(PNG_HEADER)
            historical_path = Path(
                "/old/checkout/capstone/malaria_dl_local_project/data/split/case.png"
            )

            with (
                mock.patch.object(artifacts, "MALARIA_PROJECT_ROOT", current_project),
                mock.patch.object(artifacts, "ALLOWED_ARTIFACT_ROOTS", (current_data,)),
            ):
                resolved = artifacts.resolve_artifact_reference(path=str(historical_path))

            self.assertEqual(resolved.path, image_path)
            self.assertEqual(resolved.media_type, "image/png")

    def test_non_whitelisted_extension_is_forbidden(self):
        with tempfile.TemporaryDirectory() as directory:
            allowed_root = Path(directory).resolve()
            image_path = allowed_root / "legacy.gif"
            image_path.write_bytes(b"GIF89a")

            with mock.patch.object(artifacts, "ALLOWED_ARTIFACT_ROOTS", (allowed_root,)):
                with self.assertRaises(HTTPException) as context:
                    artifacts.resolve_artifact_reference(path=str(image_path))

            self.assertEqual(context.exception.status_code, 403)

    def test_configured_roots_cover_project_outputs_and_both_data_locations(self):
        expected_roots = {
            (artifacts.MALARIA_PROJECT_ROOT / "outputs").resolve(),
            (artifacts.MALARIA_PROJECT_ROOT / "data").resolve(),
            (artifacts.CAPSTONE_ROOT / "data").resolve(),
            (artifacts.CAPSTONE_ROOT / "data" / "prediction_uploads").resolve(),
            artifacts.ARTIFACTS_ROOT,
        }
        self.assertTrue(expected_roots.issubset(set(artifacts.ALLOWED_ARTIFACT_ROOTS)))

    def test_runtime_root_honors_declared_ml_project_location(self):
        source = Path(artifacts.__file__).read_text()
        self.assertIn('os.getenv("MALARIA_DL_PROJECT_ROOT", "")', source)
        self.assertIn("MALARIA_PROJECT_ROOT.parent", source)


if __name__ == "__main__":
    unittest.main()
