"""Tests for FastAPI promotion endpoints: prepare-release and promotion-status."""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_promotion_status_run_not_found():
    fake_id = str(uuid4())
    response = client.get(f"/api/training-runs/{fake_id}/promotion-status")
    assert response.status_code == 200
    data = response.json()
    assert data["training_run_id"] == fake_id
    assert data["next_action"] == "unavailable"
    assert data["button_enabled"] is False
    assert any("TRAINING_RUN_NOT_FOUND" in r for r in data["blocking_reasons"])


def test_prepare_release_invalid_uuid():
    response = client.post("/api/training-runs/not-a-uuid/prepare-release")
    assert response.status_code == 422


def test_promotion_status_invalid_uuid():
    response = client.get("/api/training-runs/not-a-uuid/promotion-status")
    assert response.status_code == 422
