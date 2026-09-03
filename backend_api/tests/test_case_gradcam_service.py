import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from uuid import UUID

import pytest
from PIL import Image
from starlette.requests import Request


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.security import Permission, Principal  # noqa: E402
from app.services.case_gradcam import CaseGradCamService  # noqa: E402
from app.services.model_explanation_storage import (  # noqa: E402
    ModelExplanationStorage,
    ModelExplanationStorageError,
)


def principal():
    return Principal(
        user_id="11111111-1111-1111-1111-111111111111",
        username="scientist",
        roles=("researcher",),
        permissions=frozenset({Permission.SCIENTIFIC_CELL_CLASSIFICATION_EXPLAIN}),
    )


def request():
    return Request({
        "type": "http", "method": "POST",
        "path": "/api/v1/explainability/cases/source/gradcam",
        "headers": [], "query_string": b"", "server": ("test", 80),
        "client": ("test", 1), "scheme": "http",
    })


class StubCaseGradCamService(CaseGradCamService):
    def __init__(self, engine, image_path, existing=None):
        super().__init__(engine=engine)
        self.image_path = image_path
        self.existing = existing
        self.runtime_called = False

    def _target(self, _source_id):
        return {
            "prediction_id": UUID("22222222-2222-2222-2222-222222222222"),
            "run_id": UUID("33333333-3333-3333-3333-333333333333"),
            "predicted_label": "uninfected", "true_label": "uninfected",
            "score_positive_label": 0.2, "case_type": "true_negative",
            "run_parameters": {"img_size": 8, "preprocessing": "rescale_0_1"},
            "run_metadata": {},
        }

    def _existing(self, _target):
        return self.existing

    def _resolve_model(self, _target):
        return Path("/governed/model.keras"), "44444444-4444-4444-4444-444444444444", {
            "preprocessing": {"mode": "rescale_0_1"},
            "input_signature": {"width": 8},
            "class_mapping": {"0": "uninfected", "1": "parasitized"},
            "checkpoint_sha256": "a" * 64,
        }

    def _input(self, _target):
        return self.image_path, "b" * 64

    def _runtime(self):
        self.runtime_called = True
        return (
            lambda _path: object(),
            lambda image, size, mode: object(),
            lambda **kwargs: (
                object(),
                object(),
                "last_conv",
            ),
        )

    def _persist_png(self, prediction_id, explanation_id, payload):
        assert prediction_id == "22222222-2222-2222-2222-222222222222"
        assert payload.startswith(b"\x89PNG")
        return (
            f"var/artifacts/model-explanations/{prediction_id}/{explanation_id}/gradcam_overlay.png",
            "c" * 64,
            len(payload),
            self.image_path.parent / "generated.png",
        )


def _engine(final_row=None):
    engine = mock.MagicMock()
    connection = mock.MagicMock()
    engine.begin.return_value.__enter__.return_value = connection
    engine.connect.return_value.__enter__.return_value = connection
    result = mock.MagicMock()
    result.mappings.return_value.one.return_value = final_row or {
        "explainability_id": "55555555-5555-5555-5555-555555555555",
        "method": "gradcam", "success": True,
        "explanation_output_path": "var/storage/model-explanations/generated.png",
    }
    connection.execute.return_value = result
    return engine, connection


def test_model_case_generation_uses_frozen_input_model_and_only_inserts(tmp_path):
    image_path = tmp_path / "input.png"
    Image.new("RGB", (10, 10), "white").save(image_path)
    engine, connection = _engine()
    service = StubCaseGradCamService(engine, image_path)

    with (
        mock.patch("app.services.case_gradcam.enrich_explainability_case", side_effect=lambda row: dict(row)),
        mock.patch("app.services.case_gradcam.CellExplanationStorage.encode_overlay_png", return_value=b"\x89PNG\r\n\x1a\nvalid"),
    ):
        result = service.generate("source", principal(), request())

    assert service.runtime_called
    assert result["method"] == "gradcam"
    sql = "\n".join(str(call.args[0]) for call in connection.execute.call_args_list)
    assert "INSERT INTO explainability_results" in sql
    assert "INSERT INTO artifacts" in sql
    assert "INSERT INTO audit_events" in sql
    assert "UPDATE predictions" not in sql
    assert "classification_runs" not in sql
    explain_params = connection.execute.call_args_list[0].args[1]
    frozen = __import__("json").loads(explain_params["parameters"])
    assert frozen["model_version_id"] == "44444444-4444-4444-4444-444444444444"
    assert frozen["input_sha256"] == "b" * 64
    assert frozen["preprocessing"] == "rescale_0_1"
    assert frozen["target_class_index"] == 0


def test_idempotency_reuses_valid_existing_without_loading_model(tmp_path):
    engine, _ = _engine()
    existing = {"explainability_id": "existing", "method": "gradcam", "success": True}
    service = StubCaseGradCamService(engine, tmp_path / "unused.png", existing=existing)

    with mock.patch("app.services.case_gradcam.record_event") as audit:
        result = service.generate("source", principal(), request())

    assert result is existing
    assert not service.runtime_called
    assert audit.call_args.kwargs["event_type"] == "scientific.case_gradcam.reused"


def test_generation_failure_is_persisted_as_failed_not_artifact_missing(tmp_path):
    image_path = tmp_path / "input.png"
    Image.new("RGB", (10, 10), "white").save(image_path)
    engine, connection = _engine({
        "explainability_id": "55555555-5555-5555-5555-555555555555",
        "method": "gradcam", "success": False,
        "explanation_output_path": None,
        "error_message": "No fue posible generar Grad-CAM para este caso.",
    })
    service = StubCaseGradCamService(engine, image_path)
    service._runtime = lambda: (
        lambda _path: object(), lambda image, size, mode: object(),
        lambda **kwargs: (_ for _ in ()).throw(ValueError("gradient failed")),
    )

    with mock.patch("app.services.case_gradcam.enrich_explainability_case", side_effect=lambda row: dict(row)):
        result = service.generate("source", principal(), request())

    assert result["success"] is False
    sql = "\n".join(str(call.args[0]) for call in connection.execute.call_args_list)
    assert "INSERT INTO explainability_results" in sql
    assert "scientific.case_gradcam.failed" not in sql  # event type is a bound value
    audit_calls = [call for call in connection.execute.call_args_list if "audit_events" in str(call.args[0])]
    assert audit_calls[0].args[1]["event_type"] == "scientific.case_gradcam.failed"


def test_endpoint_requires_shared_explain_permission_contract():
    source = (BACKEND_ROOT / "app/routes/explainability.py").read_text()
    assert "Permission.SCIENTIFIC_CELL_CLASSIFICATION_EXPLAIN" in source
    assert "/api/v1/explainability/cases/{explainability_id}/gradcam" in source


def test_model_explanations_use_artifacts_root_and_separate_staging(tmp_path):
    artifacts_root = tmp_path / "artifacts"
    clinical_root = tmp_path / "clinical"
    storage = ModelExplanationStorage(artifacts_root)
    assert not artifacts_root.exists()
    prediction_id = "22222222-2222-2222-2222-222222222222"
    explanation_id = UUID("55555555-5555-5555-5555-555555555555")
    payload = b"\x89PNG\r\n\x1a\nmodel-explanation"

    stored = storage.persist(prediction_id, explanation_id, payload)

    assert stored.path.is_relative_to(artifacts_root / "model-explanations")
    assert not stored.path.is_relative_to(clinical_root)
    assert not (clinical_root / ".staging").exists()
    assert stored.sha256 == __import__("hashlib").sha256(payload).hexdigest()
    with pytest.raises(ModelExplanationStorageError, match="no se sobrescribe"):
        storage.persist(prediction_id, explanation_id, payload)


def test_case_gradcam_source_has_no_clinical_storage_writer():
    source = (BACKEND_ROOT / "app/services/case_gradcam.py").read_text()
    assert "LocalStorage" not in source
    assert "var/storage" not in source
    assert "ModelExplanationStorage" in source


def test_engine_supports_nested_keras_inbound_nodes_contract():
    source = (
        BACKEND_ROOT.parent
        / "malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py"
    ).read_text()
    assert 'getattr(target_layer, "_inbound_nodes", ())' in source
    assert 'getattr(node, "output_tensors", None)' in source
