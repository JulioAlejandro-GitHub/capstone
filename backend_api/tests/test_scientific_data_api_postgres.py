import json
import os
from contextlib import contextmanager
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from PIL import Image

import app.audit as audit
import app.routes.analysis as analysis_routes
import app.routes.cell_analysis as cell_analysis_routes
import app.routes.scientific as scientific_routes
import app.security as security
import app.services.scientific as scientific_service
from app.config import Settings, reset_settings_cache
from app.database_safety import assert_capstone_database
from app.db import normalize_sqlalchemy_url
from app.main import app
from app.services.microscopy_analysis import MicroscopyAnalysisService


pytestmark = pytest.mark.requires_local_postgres


class TransactionEngine:
    def __init__(self, connection):
        self.connection = connection

    @contextmanager
    def begin(self):
        with self.connection.begin_nested():
            yield self.connection

    @contextmanager
    def connect(self):
        yield self.connection


@pytest.fixture()
def scientific_client(monkeypatch, tmp_path):
    if os.getenv("TEST_EXECUTION", "").lower() != "true":
        pytest.skip("requiere gate PostgreSQL local explícito")
    settings = Settings.from_env()
    engine = create_engine(normalize_sqlalchemy_url(settings.database_url))
    connection = engine.connect()
    outer = connection.begin()
    assert_capstone_database(settings, connection.execute(text("SELECT current_database()")).scalar_one())
    admin_id, reviewer_id = uuid4(), uuid4()
    suffix = uuid4().hex[:10]
    admin_name, reviewer_name = f"sci_admin_{suffix}", f"sci_reviewer_{suffix}"
    password = uuid4().hex
    connection.execute(text("""
      INSERT INTO users(id,username,email,password_hash,status)
      VALUES(:admin,:admin_name,:admin_email,:password_hash,'active'),
            (:reviewer,:reviewer_name,:reviewer_email,:password_hash,'active')
    """), {
        "admin": admin_id, "admin_name": admin_name, "admin_email": f"{admin_name}@invalid.test",
        "reviewer": reviewer_id, "reviewer_name": reviewer_name,
        "reviewer_email": f"{reviewer_name}@invalid.test",
        "password_hash": security.hash_password(password),
    })
    connection.execute(text("""
      INSERT INTO user_roles(user_id,role_id)
      SELECT :admin,id FROM roles WHERE name='administrator'
      UNION ALL SELECT :reviewer,id FROM roles WHERE name='reviewer'
    """), {"admin": admin_id, "reviewer": reviewer_id})
    shared = TransactionEngine(connection)
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))
    reset_settings_cache()
    monkeypatch.setattr(security, "get_primary_engine", lambda: shared)
    monkeypatch.setattr(audit, "get_primary_engine", lambda: shared)
    monkeypatch.setattr(scientific_service, "get_primary_engine", lambda: shared)
    monkeypatch.setattr(analysis_routes.service, "engine", shared)
    monkeypatch.setattr(analysis_routes.queue_service, "engine", shared)
    monkeypatch.setattr(MicroscopyAnalysisService, "engine", shared)
    monkeypatch.setattr(cell_analysis_routes.service, "engine", shared)
    monkeypatch.setattr(scientific_routes.workflow_service, "engine", shared)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield (
                client,
                connection,
                {"Authorization": f"Bearer {security.create_access_token(admin_id, admin_name, ['administrator'])}"},
                {"Authorization": f"Bearer {security.create_access_token(reviewer_id, reviewer_name, ['reviewer'])}"},
                suffix,
            )
    finally:
        reset_settings_cache()
        outer.rollback()
        connection.close()
        engine.dispose()


def test_migration_schema_constraints_and_indexes(scientific_client):
    _, connection, _, _, _ = scientific_client
    inspector = inspect(connection)
    expected = {
        "research_subjects", "scientific_cases", "blood_samples",
        "smear_slides", "microscopy_images",
    }
    assert expected <= set(inspector.get_table_names())
    assert {"slide_id", "image_code", "sha256"} <= {
        column["name"] for column in inspector.get_columns("microscopy_images")
    }
    checks = {item["name"] for item in inspector.get_check_constraints("microscopy_images")}
    assert "ck_microscopy_image_archive_state" in checks
    unique = {item["name"] for item in inspector.get_unique_constraints("microscopy_images")}
    assert {"uq_microscopy_images_slide_code", "uq_microscopy_images_slide_sha256"} <= unique
    indexes = {item["name"] for item in inspector.get_indexes("microscopy_images")}
    assert {"ix_microscopy_images_sha256", "ix_microscopy_images_slide",
            "ix_microscopy_images_status_created"} <= indexes


def test_scientific_api_rbac_traceability_archive_and_audit(scientific_client):
    client, connection, admin, reviewer, suffix = scientific_client
    assert client.post("/api/v1/scientific/subjects", json={}).status_code == 401
    forbidden = client.post(
        "/api/v1/scientific/subjects",
        headers=reviewer,
        json={"subject_code": f"SUB-{suffix}"},
    )
    assert forbidden.status_code == 403
    pii = client.post(
        "/api/v1/scientific/subjects",
        headers=admin,
        json={"subject_code": f"SUB-PII-{suffix}", "metadata_json": {"email": "hidden@example.test"}},
    )
    assert pii.status_code == 422

    subject = client.post(
        "/api/v1/scientific/subjects", headers=admin,
        json={"subject_code": f"SUB-{suffix}", "age_group": "adult", "metadata_json": {"cohort": "A"}},
    )
    assert subject.status_code == 201
    subject_id = subject.json()["id"]
    duplicate = client.post(
        "/api/v1/scientific/subjects", headers=admin,
        json={"subject_code": f"SUB-{suffix}"},
    )
    assert duplicate.status_code == 409

    case = client.post(
        "/api/v1/scientific/cases", headers=admin,
        json={"case_code": f"CASE-{suffix}", "subject_id": subject_id,
              "source_type": "physical_microscope"},
    )
    assert case.status_code == 201
    case_id = case.json()["id"]
    case_update = client.patch(
        f"/api/v1/scientific/cases/{case_id}", headers=admin,
        json={"status": "registered", "priority": "high"},
    )
    assert case_update.status_code == 200
    assert case_update.json()["status"] == "registered"
    invalid_transition = client.patch(
        f"/api/v1/scientific/cases/{case_id}", headers=admin, json={"status": "draft"},
    )
    assert invalid_transition.status_code == 409
    sample = client.post(
        f"/api/v1/scientific/cases/{case_id}/samples", headers=admin,
        json={"sample_code": f"SAMPLE-{suffix}"},
    )
    assert sample.status_code == 201
    sample_id = sample.json()["id"]
    slide = client.post(
        f"/api/v1/scientific/samples/{sample_id}/slides", headers=admin,
        json={"slide_code": f"SLIDE-{suffix}", "smear_type": "thin"},
    )
    assert slide.status_code == 201
    slide_id = slide.json()["id"]
    invalid_image = client.post(
        f"/api/v1/scientific/slides/{slide_id}/images", headers=admin,
        json={"image_code": "BAD", "storage_key": "x", "mime_type": "image/png",
              "file_size_bytes": 0, "sha256": "not-a-hash", "width_px": 0, "height_px": 1},
    )
    assert invalid_image.status_code == 422
    image_ids = []
    for index in (1, 2):
        image = client.post(
            f"/api/v1/scientific/slides/{slide_id}/images", headers=admin,
            json={
                "image_code": f"IMG-{index}-{suffix}",
                "storage_key": f"scientific/{suffix}/{index}.png",
                "mime_type": "image/png", "file_size_bytes": 1024 + index,
                "sha256": f"{index:064x}", "width_px": 640, "height_px": 480,
            },
        )
        assert image.status_code == 201
        image_ids.append(image.json()["id"])

    trace = client.get(f"/api/v1/scientific/cases/{case_id}/traceability", headers=reviewer)
    assert trace.status_code == 200
    body = trace.json()
    assert body["case"]["case_code"] == f"CASE-{suffix}"
    assert body["subject"]["subject_code"] == f"SUB-{suffix}"
    assert len(body["samples"][0]["slides"][0]["images"]) == 2
    assert "storage_key" not in str(body)
    assert client.get(
        f"/api/v1/scientific/cases/{case_id}/samples?limit=1&offset=0", headers=reviewer
    ).json()["total"] == 1
    assert client.get(f"/api/v1/scientific/images/{uuid4()}", headers=reviewer).status_code == 404

    blocked = client.post(f"/api/v1/scientific/cases/{case_id}/archive", headers=admin, json={})
    assert blocked.status_code == 409
    archived = client.post(
        f"/api/v1/scientific/images/{image_ids[0]}/archive",
        headers=admin, json={"reason": "duplicate capture"},
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    events = connection.execute(text("""
      SELECT event_type,action,actor_user_id,before_state,after_state,correlation_id
      FROM audit_events WHERE resource_id IN (:subject,:case,:image)
      ORDER BY created_at
    """), {"subject": subject_id, "case": case_id, "image": image_ids[0]}).mappings().all()
    assert any(row["action"] == "scientific.subject.created" and row["after_state"] for row in events)
    assert any(row["action"] == "scientific.case.updated"
               and row["before_state"] and row["after_state"] for row in events)
    assert any(row["action"] == "scientific.image.archived"
               and row["before_state"] and row["after_state"] for row in events)
    assert all(row["actor_user_id"] and row["correlation_id"] for row in events)


def test_real_audit_failure_rolls_back_mutation(scientific_client):
    client, connection, admin, _, suffix = scientific_client
    connection.execute(text("""
      ALTER TABLE audit_events ADD CONSTRAINT ck_test_scientific_audit_failure
      CHECK (event_type <> 'SCIENTIFIC_SUBJECT_CREATED') NOT VALID
    """))
    response = client.post(
        "/api/v1/scientific/subjects", headers=admin,
        json={"subject_code": f"ROLLBACK-{suffix}"},
    )
    assert response.status_code == 500
    assert connection.execute(
        text("SELECT count(*) FROM research_subjects WHERE subject_code=:code"),
        {"code": f"ROLLBACK-{suffix}"},
    ).scalar_one() == 0


def _png(index: int) -> bytes:
    output = BytesIO()
    Image.new("RGB", (16, 12), (index, 20, 30)).save(output, "PNG")
    return output.getvalue()


def _quality_png() -> bytes:
    image = Image.new("RGB", (160, 160))
    image.putdata([
        (
            20 + ((x * 37 + y * 73 + x * y) % 216),
            20 + ((x * 61 + y * 29 + x * y * 3) % 216),
            20 + ((x * 17 + y * 89 + x * y * 5) % 216),
        )
        for y in range(image.height)
        for x in range(image.width)
    ])
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def test_secure_nih_upload_identity_content_and_idempotent_retry(scientific_client):
    client, connection, admin, reviewer, suffix = scientific_client
    data = {
        "subject_mode": "automatic_new",
        "sample_mode": "automatic_new",
        "acquisition_origin": "research_dataset_import",
        "source_system": "nih_nlm_thin_blood_smears_pf",
        "external_patient_id": f"opaque-{suffix}",
    }
    first = client.post(
        "/api/v1/scientific/images/upload", headers=admin, data=data,
        files=[("files", (f"image_{index}.png", _png(index), "application/octet-stream"))
               for index in range(1, 5)] + [
                   ("files", ("Thumbs.db", b"ignored", "application/octet-stream")),
                   ("files", (".DS_Store", b"ignored", "application/octet-stream")),
               ],
    )
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["status"] == "incomplete"
    assert body["counts"]["received"] == 4
    assert body["counts"]["ignored"] == 2
    assert body["ingestion_batch"]["expected_image_count"] == 5
    subject_id, sample_id = body["subject"]["id"], body["sample"]["id"]
    assert connection.execute(text("""
      SELECT external_patient_id FROM research_subjects WHERE id=:id
    """), {"id": subject_id}).scalar_one() == f"opaque-{suffix}"
    sample = connection.execute(text("""
      SELECT external_sample_id,sample_identity_origin,source_group_key
      FROM blood_samples WHERE id=:id
    """), {"id": sample_id}).mappings().one()
    assert sample["external_sample_id"] is None
    assert sample["sample_identity_origin"] == "generated_by_capstone"
    assert sample["source_group_key"] == f"opaque-{suffix}"
    image_id = body["images"][0]["id"]
    content = client.get(f"/api/v1/scientific/images/{image_id}/content", headers=reviewer)
    assert content.status_code == 200
    assert content.headers["x-content-type-options"] == "nosniff"
    assert content.content == _png(1)

    retry = client.post(
        "/api/v1/scientific/images/upload", headers=admin, data=data,
        files=[
            ("files", ("image_1.png", _png(1), "image/png")),
            ("files", ("image_5.png", _png(5), "image/png")),
        ],
    )
    assert retry.status_code == 201, retry.text
    retried = retry.json()
    assert retried["status"] == "complete"
    assert retried["counts"]["received"] == 5
    assert retried["subject"]["id"] == subject_id
    assert retried["sample"]["id"] == sample_id
    assert connection.execute(text("""
      SELECT count(*) FROM microscopy_images WHERE ingestion_batch_id=:id
    """), {"id": retried["ingestion_batch"]["id"]}).scalar_one() == 5
    assert connection.execute(text("""
      SELECT count(*) FROM audit_events
      WHERE actor_user_id=(SELECT created_by FROM microscopy_images WHERE id=:image)
        AND event_type='scientific.image.imported'
    """), {"image": image_id}).scalar_one() >= 1

    excess = client.post(
        "/api/v1/scientific/images/upload", headers=admin, data=data,
        files=[("files", ("image_6.png", _png(6), "image/png"))],
    )
    assert excess.status_code == 201
    assert excess.json()["status"] == "inconsistent"
    assert excess.json()["counts"]["received"] == 6
    assert connection.execute(
        text("SELECT count(*) FROM audit_events WHERE resource_id IS NOT NULL "
             "AND event_type='SCIENTIFIC_SUBJECT_CREATED'")
    ).scalar_one() == 0


def test_manual_upload_is_immediately_eligible_and_refreshable(scientific_client):
    client, connection, admin, reviewer, _ = scientific_client
    upload_data = {
        "subject_mode": "automatic_new",
        "sample_mode": "automatic_new",
        "acquisition_origin": "manual_upload",
        "metadata_json": json.dumps({"client_request_id": str(uuid4())}),
    }
    upload = client.post(
        "/api/v1/scientific/images/upload",
        headers=admin,
        data=upload_data,
        files=[("files", ("manual-smear.png", _quality_png(), "image/png"))],
    )
    assert upload.status_code == 201, upload.text
    uploaded = upload.json()
    batch_id = uploaded["ingestion_batch"]["id"]
    replayed = client.post(
        "/api/v1/scientific/images/upload",
        headers=admin,
        data=upload_data,
        files=[("files", ("manual-smear.png", _quality_png(), "image/png"))],
    )
    assert replayed.status_code == 201
    assert replayed.json()["ingestion_batch"]["id"] == batch_id
    assert replayed.json()["subject"]["id"] == uploaded["subject"]["id"]
    assert connection.execute(
        text(
            "SELECT count(*) FROM image_ingestion_batches "
            "WHERE metadata_json->>'client_request_id'=:request_id"
        ),
        {"request_id": json.loads(upload_data["metadata_json"])["client_request_id"]},
    ).scalar_one() == 1
    lineage = connection.execute(
        text(
            """
            SELECT c.status case_status,bs.status sample_status
            FROM image_ingestion_batches b
            JOIN scientific_cases c ON c.id=b.case_id
            JOIN blood_samples bs ON bs.id=b.sample_id
            WHERE b.id=:id
            """
        ),
        {"id": batch_id},
    ).mappings().one()
    assert lineage == {"case_status": "registered", "sample_status": "registered"}

    eligible = client.get("/api/v1/analysis/eligible-batches", headers=reviewer)
    assert eligible.status_code == 200
    assert batch_id in {item["id"] for item in eligible.json()["items"]}

    before = client.get(
        f"/api/v1/scientific/workflows/{batch_id}", headers=reviewer
    )
    assert before.status_code == 200
    assert before.json()["stage"] == "ingested"
    assert before.json()["analysis_run"] is None
    assert "storage_key" not in before.text

    created = client.post(
        "/api/v1/analysis/runs",
        headers=admin,
        json={"ingestion_batch_id": batch_id},
    )
    assert created.status_code == 201, created.text
    after = client.get(
        f"/api/v1/scientific/workflows/{batch_id}", headers=reviewer
    )
    assert after.status_code == 200
    assert after.json()["analysis_run"]["id"] == created.json()["id"]
    assert after.json()["analysis_run"]["run_status"] == "quality_pending"
    assert after.json()["analysis_run"]["images"]
    assert after.json()["analysis_run"]["events"]
    assert after.json()["stage"] == "creating_analysis"

    equivalent = client.post(
        "/api/v1/analysis/runs",
        headers=admin,
        json={"ingestion_batch_id": batch_id},
    )
    assert equivalent.status_code == 201
    assert equivalent.json()["id"] == created.json()["id"]
    assert connection.execute(
        text(
            "SELECT count(*) FROM microscopy_analysis_runs "
            "WHERE ingestion_batch_id=:id"
        ),
        {"id": batch_id},
    ).scalar_one() == 1

    queued = client.post(
        "/api/v1/analysis/queue",
        headers=admin,
        json={"analysis_run_id": created.json()["id"], "priority": 50},
    )
    assert queued.status_code == 201, queued.text
    queue_item = queued.json()
    assert queue_item["priority"] == 50
    duplicate_queue = client.post(
        "/api/v1/analysis/queue",
        headers=admin,
        json={"analysis_run_id": created.json()["id"], "priority": 50},
    )
    assert duplicate_queue.status_code == 409
    assert connection.execute(
        text(
            "SELECT count(*) FROM quality_assessment_queue_items "
            "WHERE analysis_run_id=:id"
        ),
        {"id": created.json()["id"]},
    ).scalar_one() == 1

    quality_queued = client.get(
        f"/api/v1/scientific/workflows/{batch_id}", headers=reviewer
    )
    assert quality_queued.status_code == 200
    assert quality_queued.json()["stage"] == "quality_queued"
    assert quality_queued.json()["queue_item"]["queue_item_id"] == queue_item["id"]

    executed = client.post(
        f"/api/v1/analysis/queue/{queue_item['id']}/execute",
        headers=admin,
    )
    assert executed.status_code == 200, executed.text
    ready = client.get(
        f"/api/v1/scientific/workflows/{batch_id}", headers=reviewer
    )
    assert ready.status_code == 200
    assert ready.json()["stage"] == "ready_for_detection"
    assert ready.json()["analysis_run"]["quality_gate_status"] == "pass"
    assert ready.json()["analysis_run"]["ready_for_analysis"] is True

    forbidden_detection = client.post(
        "/api/v1/cell-analysis/detection-runs",
        headers=reviewer,
        json={"analysis_run_id": created.json()["id"]},
    )
    assert forbidden_detection.status_code == 403
    detected = client.post(
        "/api/v1/cell-analysis/detection-runs",
        headers=admin,
        json={"analysis_run_id": created.json()["id"]},
    )
    assert detected.status_code == 201, detected.text
    assert detected.json()["status"] in {"completed", "completed_with_warnings"}
    equivalent_detection = client.post(
        "/api/v1/cell-analysis/detection-runs",
        headers=admin,
        json={"analysis_run_id": created.json()["id"]},
    )
    assert equivalent_detection.status_code == 201
    assert equivalent_detection.json()["id"] == detected.json()["id"]
    assert equivalent_detection.json()["idempotent"] is True

    review_ready = client.get(
        f"/api/v1/scientific/workflows/{batch_id}", headers=reviewer
    )
    assert review_ready.status_code == 200
    refreshed = review_ready.json()
    assert refreshed["stage"] == "review_ready"
    assert refreshed["batch"]["id"] == batch_id
    assert refreshed["images"][0]["id"] == uploaded["images"][0]["id"]
    assert refreshed["analysis_run"]["id"] == created.json()["id"]
    assert refreshed["queue_item"]["queue_item_id"] == queue_item["id"]
    assert refreshed["detection_run"]["id"] == detected.json()["id"]
    assert "storage_key" not in review_ready.text
    row_counts_before = connection.execute(text("""
      SELECT
        (SELECT count(*) FROM microscopy_analysis_runs),
        (SELECT count(*) FROM quality_assessment_queue_items),
        (SELECT count(*) FROM cell_detection_runs),
        (SELECT count(*) FROM scientific_reviews)
    """)).one()
    history = client.get(
        "/api/v1/scientific/workflows",
        headers=reviewer,
        params={"run_code": created.json()["run_code"], "limit": 1, "offset": 0},
    )
    assert history.status_code == 200, history.text
    history_page = history.json()
    assert history_page["total"] == 1
    assert history_page["limit"] == 1
    assert history_page["offset"] == 0
    history_row = history_page["items"][0]
    assert history_row["analysis_run_id"] == created.json()["id"]
    assert history_row["ingestion_batch_id"] == batch_id
    assert history_row["run_code"] == created.json()["run_code"]
    assert history_row["subject_code"] == uploaded["subject"]["subject_code"]
    assert history_row["sample_code"] == uploaded["sample"]["sample_code"]
    assert history_row["quality_gate_status"] == "pass"
    assert history_row["ready_for_analysis"] is True
    assert history_row["detection_run_id"] == detected.json()["id"]
    assert history_row["detection_count"] == detected.json()["detection_count"]
    assert history_row["reviewed_count"] == 0
    assert "storage_key" not in history.text
    assert client.get(
        "/api/v1/scientific/workflows",
        headers=reviewer,
        params={"subject_code": uploaded["subject"]["subject_code"]},
    ).json()["total"] == 1
    assert client.get(
        "/api/v1/scientific/workflows",
        headers=reviewer,
        params={"sample_code": uploaded["sample"]["sample_code"]},
    ).json()["total"] == 1
    assert client.get(
        "/api/v1/scientific/workflows",
        headers=reviewer,
        params={"status": "ready_for_analysis"},
    ).json()["total"] == 1
    assert client.get(
        "/api/v1/scientific/workflows",
        headers=reviewer,
        params={"created_from": "2999-01-01"},
    ).json()["total"] == 0
    detail = client.get(
        f"/api/v1/scientific/analysis-history/{created.json()['id']}",
        headers=reviewer,
    )
    assert detail.status_code == 200
    assert detail.json()["analysis_run"]["id"] == created.json()["id"]
    assert detail.json()["detection_run"]["id"] == detected.json()["id"]
    assert "storage_key" not in detail.text
    assert client.get(
        f"/api/v1/scientific/analysis-history/{uuid4()}",
        headers=reviewer,
    ).status_code == 404
    row_counts_after = connection.execute(text("""
      SELECT
        (SELECT count(*) FROM microscopy_analysis_runs),
        (SELECT count(*) FROM quality_assessment_queue_items),
        (SELECT count(*) FROM cell_detection_runs),
        (SELECT count(*) FROM scientific_reviews)
    """)).one()
    assert row_counts_after == row_counts_before
    assert connection.execute(
        text(
            "SELECT count(*) FROM audit_events "
            "WHERE resource_id IN (:analysis_id,:queue_id,:detection_id)"
        ),
        {
            "analysis_id": created.json()["id"],
            "queue_id": queue_item["id"],
            "detection_id": detected.json()["id"],
        },
    ).scalar_one() >= 3


def test_upload_rejects_an_archived_subject(scientific_client):
    client, _, admin, _, suffix = scientific_client
    code = f"ARCHIVED-{suffix}"
    created = client.post(
        "/api/v1/scientific/subjects",
        headers=admin,
        json={"subject_code": code},
    )
    assert created.status_code == 201
    archived = client.post(
        f"/api/v1/scientific/subjects/{created.json()['id']}/archive",
        headers=admin,
        json={"reason": "fixture de estado"},
    )
    assert archived.status_code == 200

    rejected = client.post(
        "/api/v1/scientific/images/upload",
        headers=admin,
        data={
            "subject_mode": "existing",
            "subject_code": code,
            "sample_mode": "automatic_new",
            "acquisition_origin": "manual_upload",
        },
        files=[("files", ("must-not-persist.png", _png(8), "image/png"))],
    )
    assert rejected.status_code == 409
    assert "archivado" in rejected.text.lower()
