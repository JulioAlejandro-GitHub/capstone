import os
from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

import app.audit as audit
import app.security as security
import app.services.scientific as scientific_service
from app.config import Settings
from app.database_safety import assert_capstone_database
from app.db import normalize_sqlalchemy_url
from app.main import app


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
def scientific_client(monkeypatch):
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
    monkeypatch.setattr(security, "get_primary_engine", lambda: shared)
    monkeypatch.setattr(audit, "get_primary_engine", lambda: shared)
    monkeypatch.setattr(scientific_service, "get_primary_engine", lambda: shared)
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
    assert connection.execute(
        text("SELECT count(*) FROM audit_events WHERE resource_id IS NOT NULL "
             "AND event_type='SCIENTIFIC_SUBJECT_CREATED'")
    ).scalar_one() == 0
