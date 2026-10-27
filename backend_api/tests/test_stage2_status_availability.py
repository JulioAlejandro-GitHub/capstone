"""An active publication is available only while the backend can read its checkpoint."""

from contextlib import contextmanager
from uuid import UUID, uuid4

from app.services import stage2_status

TRAIN = UUID("31d27b2d-6e90-4530-a589-ae92c91281df")
VERSION = str(uuid4())


def install(monkeypatch, checkpoint):
    @contextmanager
    def transaction(_datasource):
        yield object()

    repository = stage2_status.repository
    monkeypatch.setattr(stage2_status, "read_only_transaction", transaction)
    monkeypatch.setattr(repository, "read_training", lambda *_: {
        "train_status": "completed", "model_name": "biomedclip_zero_shot",
        "metadata": {"training_performed": False},
    })
    monkeypatch.setattr(repository, "read_evaluations", lambda *_: [])
    monkeypatch.setattr(repository, "read_explanations", lambda *_: [])
    monkeypatch.setattr(repository, "read_version", lambda *_: {
        "id": VERSION, "checkpoint_artifact_id": str(uuid4()), "artifact_path": str(checkpoint),
        "artifact_sha256": "0" * 64, "artifact_size_bytes": 1, "model_name": "biomedclip_zero_shot",
        "framework": "tensorflow", "preprocessing_profile_snapshot": {"mode": "rescale_0_1"},
    })
    monkeypatch.setattr(repository, "read_publication", lambda *_: {"is_active": True})
    monkeypatch.setattr(repository, "read_deployment", lambda *_: {
        "deployment_status": "active", "smoke_status": "PASS",
    })


def test_published_model_with_unreadable_checkpoint_is_not_available(monkeypatch, tmp_path):
    install(monkeypatch, tmp_path / "missing" / "open_clip_pytorch_model.bin")

    result = stage2_status.Stage2StatusService().status(TRAIN, "malaria")

    assert result.published is True
    assert result.available is result.available_for_inference is result.is_stage2_available is False
    assert result.stage2_status == "not_available"
    assert any(b.code == "CHECKPOINT_UNAVAILABLE" for b in result.technical_blockers)


def test_active_zero_shot_offers_the_newer_val_calibrated_threshold(monkeypatch, tmp_path):
    install(monkeypatch, tmp_path / "missing.bin")
    calibrated = {
        "evaluation_source_kind": "assessment_e6", "evaluation_attempt_id": str(uuid4()),
        "evaluation_identity_id": str(uuid4()), "evaluation_status": "verified",
        "evaluation_finished_at": "2026-10-27T00:00:00+00:00", "evaluation_verified_evidence": True,
        "evaluation_link_valid": True, "evaluation_split": "val",
        "evaluation_decision_source": "zero_shot_val_calibration_v1",
        "model_binding": {"input_contract": {"schema_version": "openclip_input_v1"}},
        "model_version_id": VERSION,
    }
    repository = stage2_status.repository
    monkeypatch.setattr(repository, "read_evaluations", lambda *_: [calibrated])

    published_argmax = stage2_status.Stage2StatusService().status(TRAIN, "malaria")
    assert published_argmax.threshold_update_available is True

    monkeypatch.setattr(repository, "read_publication", lambda *_: {
        "is_active": True, "evaluation_attempt_id": calibrated["evaluation_attempt_id"]})
    assert stage2_status.Stage2StatusService().status(TRAIN, "malaria").threshold_update_available is False
