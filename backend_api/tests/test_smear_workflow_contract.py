from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.microscopy_analysis import (
    ELIGIBLE_CASE_STATUSES,
    ELIGIBLE_SAMPLE_STATUSES,
    eligible_lineage,
)
from app.services.smear_workflow import (
    build_workflow_payload,
    derive_workflow_stage,
)


def _batch(**overrides):
    return {
        "id": uuid4(),
        "status": "complete",
        **overrides,
    }


def _analysis(**overrides):
    return {
        "ready_for_analysis": False,
        "quality_gate_status": "pending",
        "run_status": "quality_pending",
        **overrides,
    }


@pytest.mark.parametrize(
    ("case_status", "sample_status"),
    [
        ("registered", "registered"),
        ("registered", "received"),
        ("ready", "prepared"),
    ],
)
def test_uploaded_scientific_lineage_is_eligible(case_status, sample_status):
    assert ELIGIBLE_CASE_STATUSES == {"registered", "ready"}
    assert ELIGIBLE_SAMPLE_STATUSES == {"registered", "received", "prepared"}
    assert eligible_lineage(
        {
            "subject_status": "active",
            "case_status": case_status,
            "sample_status": sample_status,
            "slide_status": "registered",
        }
    )


@pytest.mark.parametrize(
    ("lineage", "eligible"),
    [
        ({"subject_status": "archived"}, False),
        ({"case_status": "draft"}, False),
        ({"case_status": "archived"}, False),
        ({"sample_status": "archived"}, False),
        ({"slide_status": "archived"}, False),
    ],
)
def test_archived_or_draft_lineage_is_not_eligible(lineage, eligible):
    values = {
        "subject_status": "active",
        "case_status": "registered",
        "sample_status": "registered",
        "slide_status": "registered",
        **lineage,
    }
    assert eligible_lineage(values) is eligible


def test_ready_flag_has_precedence_over_warning_gate():
    assert derive_workflow_stage(
        _batch(),
        _analysis(ready_for_analysis=True, quality_gate_status="warning"),
        {"status": "completed"},
        None,
    ) == "ready_for_detection"


@pytest.mark.parametrize(
    ("analysis", "queue", "detection", "expected"),
    [
        (None, None, None, "ingested"),
        (_analysis(), None, None, "creating_analysis"),
        (_analysis(), {"status": "queued"}, None, "quality_queued"),
        (_analysis(), {"status": "running"}, None, "quality_processing"),
        (
            _analysis(quality_gate_status="warning", run_status="review_required"),
            {"status": "completed"},
            None,
            "quality_warning",
        ),
        (
            _analysis(quality_gate_status="fail", run_status="blocked"),
            {"status": "completed"},
            None,
            "quality_failed",
        ),
        (_analysis(), {"status": "failed"}, None, "error"),
        (
            _analysis(ready_for_analysis=True, quality_gate_status="pass"),
            {"status": "completed"},
            {"status": "processing"},
            "detection_processing",
        ),
        (
            _analysis(ready_for_analysis=False, quality_gate_status="warning"),
            {"status": "completed"},
            {"status": "completed_with_warnings"},
            "review_ready",
        ),
        (
            _analysis(ready_for_analysis=True, quality_gate_status="pass"),
            {"status": "completed"},
            {"status": "failed"},
            "error",
        ),
    ],
)
def test_workflow_stage_derives_from_durable_backend_state(
    analysis, queue, detection, expected
):
    assert derive_workflow_stage(
        _batch(), analysis, queue, detection
    ) == expected


@pytest.mark.parametrize(
    ("classification_status", "expected"),
    [
        ("created", "classification_pending"),
        ("processing", "classification_processing"),
        ("completed", "classification_completed"),
        ("completed_with_warnings", "classification_warning"),
        ("failed", "classification_failed"),
    ],
)
def test_workflow_stage_includes_durable_classification_state(
    classification_status, expected
):
    assert derive_workflow_stage(
        _batch(),
        _analysis(ready_for_analysis=True, quality_gate_status="pass"),
        {"status": "completed"},
        {"status": "completed"},
        {"status": classification_status},
        True,
    ) == expected


def test_workflow_stage_blocks_safely_without_productive_model():
    assert derive_workflow_stage(
        _batch(),
        _analysis(ready_for_analysis=True, quality_gate_status="pass"),
        {"status": "completed"},
        {"status": "completed"},
        None,
        False,
    ) == "awaiting_productive_model"


def test_workflow_payload_is_curated_and_never_exposes_storage_paths():
    ids = [uuid4() for _ in range(6)]
    batch_row = {
        "batch_id": ids[0],
        "subject_id": ids[1],
        "case_id": ids[2],
        "sample_id": ids[3],
        "slide_id": ids[4],
        "acquisition_origin": "manual_upload",
        "source_system": None,
        "expected_image_count": None,
        "received_image_count": 1,
        "batch_status": "complete",
        "batch_created_at": None,
        "batch_updated_at": None,
        "batch_completed_at": None,
        "subject_code": "PAT-TEST",
        "subject_status": "active",
        "case_code": "CAS-TEST",
        "case_status": "registered",
        "sample_code": "SMP-TEST",
        "sample_status": "registered",
        "slide_code": "SLD-TEST",
        "slide_status": "registered",
        "storage_key": "/must/not/leak",
    }
    image = {
        "id": ids[5],
        "image_code": "IMG-TEST",
        "original_filename": "smear.png",
        "mime_type": "image/png",
        "file_size_bytes": 123,
        "sha256": "a" * 64,
        "width_px": 128,
        "height_px": 128,
        "bit_depth": 8,
        "detected_format": "PNG",
        "channel_count": 3,
        "color_space": "RGB",
        "orientation": None,
        "status": "available",
        "image_sequence_number": 1,
        "captured_at": None,
        "created_at": None,
        "storage_key": "../../private/image.png",
        "source_relative_path": "/private/source.png",
    }
    payload = build_workflow_payload(batch_row, [image], None, None, None)
    serialized = str(payload).lower()
    assert payload["stage"] == "ingested"
    assert payload["batch"]["id"] == ids[0]
    assert payload["images"][0]["content_url"] == (
        f"/api/v1/scientific/images/{ids[5]}/content"
    )
    assert "storage_key" not in serialized
    assert "source_relative_path" not in serialized
    assert "/must/not/leak" not in serialized
    assert "/private/" not in serialized


def test_workflow_payload_preserves_analysis_and_detection_detail_contracts():
    ids = [uuid4() for _ in range(6)]
    batch_row = {
        "batch_id": ids[0],
        "subject_id": ids[1],
        "case_id": ids[2],
        "sample_id": ids[3],
        "slide_id": ids[4],
        "acquisition_origin": "manual_upload",
        "source_system": None,
        "expected_image_count": None,
        "received_image_count": 1,
        "batch_status": "complete",
        "batch_created_at": None,
        "batch_updated_at": None,
        "batch_completed_at": None,
        "subject_code": "PAT-DETAIL",
        "subject_status": "active",
        "case_code": "CAS-DETAIL",
        "case_status": "registered",
        "sample_code": "SMP-DETAIL",
        "sample_status": "registered",
        "slide_code": "SLD-DETAIL",
        "slide_status": "registered",
    }
    analysis = {
        "id": ids[5],
        "ready_for_analysis": True,
        "quality_gate_status": "pass",
        "run_status": "ready_for_analysis",
        "subject_code": "PAT-DETAIL",
        "sample_code": "SMP-DETAIL",
        "slide_code": "SLD-DETAIL",
        "requested_by_username": "researcher",
        "images": [{"id": uuid4(), "quality_verdict": "pass"}],
        "events": [{"event_type": "quality.run.completed"}],
        "decisions": [],
    }
    detection = {
        "id": uuid4(),
        "status": "completed",
        "profile_snapshot": {"coordinate_space": "original_image_pixels"},
        "images": [{"microscopy_image_id": uuid4()}],
        "events": [{"event_type": "cell_detection.run.completed"}],
        "review_counts": {"reviewed": 0, "unreviewed": 1},
    }
    payload = build_workflow_payload(
        batch_row, [], analysis, {"status": "completed"}, detection
    )
    assert payload["stage"] == "review_ready"
    assert payload["batch"]["subject_code"] == "PAT-DETAIL"
    assert payload["batch"]["sample_code"] == "SMP-DETAIL"
    assert payload["batch"]["slide_code"] == "SLD-DETAIL"
    assert payload["analysis_run"]["images"] == analysis["images"]
    assert payload["analysis_run"]["events"] == analysis["events"]
    assert payload["analysis_run"]["decisions"] == []
    assert payload["detection_run"]["review_counts"] == detection["review_counts"]
    assert payload["detection_run"]["images"] == detection["images"]


def test_workflow_endpoint_requires_authentication():
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(f"/api/v1/scientific/workflows/{uuid4()}")
    assert response.status_code == 401


def test_history_endpoints_require_authentication():
    client = TestClient(app, raise_server_exceptions=False)
    assert client.get("/api/v1/scientific/workflows").status_code == 401
    assert client.get(
        f"/api/v1/scientific/analysis-history/{uuid4()}"
    ).status_code == 401


def test_history_routes_are_get_only_and_use_existing_read_permission():
    client = TestClient(app, raise_server_exceptions=False)
    assert client.post("/api/v1/scientific/workflows").status_code == 405
    assert client.post(
        f"/api/v1/scientific/analysis-history/{uuid4()}"
    ).status_code == 405
