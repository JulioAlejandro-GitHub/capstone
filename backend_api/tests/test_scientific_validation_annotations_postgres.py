import json
import os
from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError

import app.audit as audit
import app.routes.scientific_validation as validation_routes
import app.security as security
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
def annotation_client(monkeypatch):
    if os.getenv("TEST_EXECUTION", "").lower() != "true":
        pytest.skip("requiere gate PostgreSQL local explícito")
    settings = Settings.from_env()
    engine = create_engine(normalize_sqlalchemy_url(settings.database_url))
    connection = engine.connect()
    outer = connection.begin()
    assert_capstone_database(
        settings, connection.execute(text("SELECT current_database()")).scalar_one()
    )
    candidate = connection.execute(text("""
      SELECT detection.id cell_id,detection.analysis_run_id,detection.detection_run_id,
             detection.microscopy_image_id,image.sha256
      FROM cell_detections detection
      JOIN microscopy_images image ON image.id=detection.microscopy_image_id
      ORDER BY detection.created_at LIMIT 1
    """)).mappings().one()
    users = {}
    password_hash = security.hash_password(uuid4().hex)
    for role in ("researcher", "reviewer", "read_only"):
        user_id = uuid4()
        username = f"annotation_{role}_{uuid4().hex[:8]}"
        connection.execute(text("""
          INSERT INTO users(id,username,email,password_hash,status)
          VALUES(:id,:username,:email,:password,'active')
        """), {"id": user_id, "username": username,
                "email": f"{username}@invalid.test", "password": password_hash})
        connection.execute(text("""
          INSERT INTO user_roles(user_id,role_id)
          SELECT :user_id,id FROM roles WHERE name=:role
        """), {"user_id": user_id, "role": role})
        users[role] = (user_id, username)
    session_id = uuid4()
    connection.execute(text("""
      INSERT INTO scientific_validation_sessions(
        id,name,datasource,protocol_key,protocol_version,matching_iou_threshold,
        initial_snapshot,snapshot_sha256,created_by,updated_by
      ) VALUES(
        :id,'Annotation integration','malaria','annotation-test','1',0.5,
        '{}'::jsonb,:digest,:actor,:actor
      )
    """), {"id": session_id, "digest": "0" * 64, "actor": users["researcher"][0]})
    connection.execute(text("""
      INSERT INTO scientific_validation_images(
        session_id,microscopy_image_id,image_sha256,sequence_number
      ) VALUES(:session,:image,:sha,1)
    """), {"session": session_id, "image": candidate["microscopy_image_id"],
            "sha": candidate["sha256"]})
    connection.execute(text("""
      INSERT INTO scientific_validation_detection_runs(session_id,detection_run_id)
      VALUES(:session,:run)
    """), {"session": session_id, "run": candidate["detection_run_id"]})
    shared = TransactionEngine(connection)
    monkeypatch.setattr(security, "get_primary_engine", lambda: shared)
    monkeypatch.setattr(audit, "get_primary_engine", lambda: shared)
    monkeypatch.setattr(validation_routes.service, "engine", shared)
    headers = {
        role: {"Authorization": f"Bearer {security.create_access_token(user_id, username, [role])}"}
        for role, (user_id, username) in users.items()
    }
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, connection, headers, users, str(session_id), candidate
    finally:
        validation_routes.service.engine = None
        outer.rollback()
        connection.close()
        engine.dispose()


def test_annotation_schema_constraints_and_append_only_history(annotation_client):
    _, connection, _, _, _, _ = annotation_client
    inspector = inspect(connection)
    assert {
        "scientific_validation_annotations",
        "scientific_validation_annotation_events",
    } <= set(inspector.get_table_names())
    annotation_checks = {
        item["name"] for item in inspector.get_check_constraints(
            "scientific_validation_annotations"
        )
    }
    assert "ck_validation_annotation_exact_target" in annotation_checks
    triggers = {
        row[0] for row in connection.execute(text("""
          SELECT tgname FROM pg_trigger
          WHERE tgrelid IN (
            'scientific_validation_annotations'::regclass,
            'scientific_validation_annotation_events'::regclass
          ) AND NOT tgisinternal
        """))
    }
    assert {
        "trg_validation_annotation_protected",
        "trg_validation_annotation_events_append_only",
    } <= triggers


def test_cell_analysis_multiple_edit_history_rbac_audit_and_conflict(annotation_client):
    client, connection, headers, users, session_id, candidate = annotation_client
    cell_payload = {
        "target_type": "cell", "cell_id": str(candidate["cell_id"]),
        "category": "morphology", "content": "Initial observation",
    }
    first = client.post(
        f"/api/v1/scientific-validation/sessions/{session_id}/annotations",
        headers=headers["researcher"], json=cell_payload,
    )
    assert first.status_code == 201, first.text
    first_body = first.json()
    assert first_body["created_by"] == str(users["researcher"][0])
    assert first_body["updated_by"] == str(users["researcher"][0])
    assert first_body["version"] == 1

    second = client.post(
        f"/api/v1/scientific-validation/sessions/{session_id}/annotations",
        headers=headers["reviewer"], json={**cell_payload, "category": "quality"},
    )
    assert second.status_code == 201
    analysis = client.post(
        f"/api/v1/scientific-validation/sessions/{session_id}/annotations",
        headers=headers["researcher"], json={
            "target_type": "analysis",
            "analysis_run_id": str(candidate["analysis_run_id"]),
            "category": "global_quality", "content": "Analysis-level observation",
        },
    )
    assert analysis.status_code == 201, analysis.text

    listing = client.get(
        f"/api/v1/scientific-validation/sessions/{session_id}/annotations",
        headers=headers["read_only"], params={"target_type": "cell"},
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 2

    updated = client.patch(
        f"/api/v1/scientific-validation/sessions/{session_id}/annotations/{first_body['id']}",
        headers=headers["reviewer"],
        json={"version": 1, "content": "Revised observation"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["version"] == 2
    assert updated.json()["created_by"] == str(users["researcher"][0])
    assert updated.json()["updated_by"] == str(users["reviewer"][0])

    conflict = client.patch(
        f"/api/v1/scientific-validation/sessions/{session_id}/annotations/{first_body['id']}",
        headers=headers["researcher"],
        json={"version": 1, "content": "Stale update"},
    )
    assert conflict.status_code == 409
    history = client.get(
        f"/api/v1/scientific-validation/sessions/{session_id}/annotations/{first_body['id']}/history",
        headers=headers["read_only"],
    )
    assert history.status_code == 200
    events = history.json()["items"]
    assert [item["event_type"] for item in events] == ["created", "updated"]
    assert events[1]["before_state"]["content"] == "Initial observation"
    assert events[1]["after_state"]["content"] == "Revised observation"
    assert events[1]["actor_user_id"] == str(users["reviewer"][0])
    with pytest.raises(DBAPIError):
        with connection.begin_nested():
            connection.execute(text("""
              UPDATE scientific_validation_annotation_events
              SET after_state='{}'::jsonb
              WHERE annotation_id=CAST(:id AS uuid)
            """), {"id": first_body["id"]})

    assert client.post(
        f"/api/v1/scientific-validation/sessions/{session_id}/annotations",
        headers=headers["read_only"], json=cell_payload,
    ).status_code == 403
    invalid = client.post(
        f"/api/v1/scientific-validation/sessions/{session_id}/annotations",
        headers=headers["researcher"],
        json={**cell_payload, "analysis_run_id": str(candidate["analysis_run_id"])},
    )
    assert invalid.status_code == 422
    outside = client.post(
        f"/api/v1/scientific-validation/sessions/{session_id}/annotations",
        headers=headers["researcher"], json={**cell_payload, "cell_id": str(uuid4())},
    )
    assert outside.status_code == 409
    missing_session = client.post(
        f"/api/v1/scientific-validation/sessions/{uuid4()}/annotations",
        headers=headers["researcher"], json=cell_payload,
    )
    assert missing_session.status_code == 404

    audit_rows = connection.execute(text("""
      SELECT action,actor_user_id,before_state,after_state
      FROM audit_events WHERE resource_type='scientific_validation_annotation'
        AND resource_id=:id ORDER BY created_at,id
    """), {"id": first_body["id"]}).mappings().all()
    assert {row["action"] for row in audit_rows} == {
        "scientific.validation.annotation.created",
        "scientific.validation.annotation.updated",
    }
    updated_audit = next(
        row for row in audit_rows
        if row["action"] == "scientific.validation.annotation.updated"
    )
    assert updated_audit["actor_user_id"] == users["reviewer"][0]
    assert updated_audit["before_state"]["content"] == "Initial observation"
    assert updated_audit["after_state"]["content"] == "Revised observation"
