import os
from datetime import datetime, timedelta, timezone

import jwt

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("JWT_SECRET", "test-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("DATABASE_URL", "postgresql://capstone_local:local-only@localhost:55432/capstone_local")

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app, raise_server_exceptions=False)


def test_health_does_not_require_database():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_correlation_id_generated_and_returned():
    response = client.get("/health")
    assert response.headers["X-Correlation-ID"]


def test_valid_correlation_id_propagated():
    value = "00000000-0000-4000-8000-000000000001"
    response = client.get("/health", headers={"X-Correlation-ID": value})
    assert response.headers["X-Correlation-ID"] == value


def test_auth_me_requires_token_with_error_envelope():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
    assert response.json()["error"]["correlation_id"]


def test_auth_me_rejects_tampered_token():
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalid.invalid.invalid"}
    )
    assert response.status_code == 401


def test_auth_me_rejects_expired_token():
    now = datetime.now(timezone.utc)
    token = jwt.encode({
        "sub": "00000000-0000-4000-8000-000000000001",
        "username": "capstone_test_expired",
        "roles": ["read_only"], "type": "access",
        "iat": now - timedelta(minutes=2), "exp": now - timedelta(minutes=1),
    }, os.environ["JWT_SECRET"], algorithm="HS256")
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
