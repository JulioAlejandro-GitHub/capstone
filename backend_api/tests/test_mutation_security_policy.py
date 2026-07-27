import os

import pytest

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "postgresql://capstone_local:local-only@localhost:55432/capstone_local")
os.environ.setdefault("JWT_SECRET", "test-secret-with-at-least-thirty-two-characters")

from app.main import app
from app.security import Permission, ROLE_PERMISSIONS


def _mutable_routes():
    return [
        route for route in app.routes
        if set(getattr(route, "methods", set())) & {"POST", "PUT", "PATCH", "DELETE"}
        and route.path != "/api/v1/auth/login"
    ]


def test_every_legacy_mutation_has_central_audited_policy():
    unprotected = []
    for route in _mutable_routes():
        dependencies = getattr(route, "dependencies", [])
        if not any(getattr(item.call, "__name__", "") == "dependency"
                   and item.call.__module__ == "app.audit" for item in dependencies):
            unprotected.append(f"{','.join(sorted(route.methods))} {route.path}")
    assert unprotected == []


@pytest.mark.parametrize("role", ["read_only", "operator", "reviewer", "researcher"])
def test_non_admin_roles_cannot_administer_deployments(role):
    assert Permission.SYSTEM_ADMIN not in ROLE_PERMISSIONS[role]


@pytest.mark.parametrize("role", ["read_only", "operator", "reviewer", "researcher"])
def test_only_administrator_can_publish(role):
    assert Permission.MODELS_PUBLISH not in ROLE_PERMISSIONS[role]


def test_operator_and_researcher_can_request_traceable_inference():
    assert Permission.PREDICTIONS_EXECUTE in ROLE_PERMISSIONS["operator"]
    assert Permission.PREDICTIONS_EXECUTE in ROLE_PERMISSIONS["researcher"]
    assert Permission.PREDICTIONS_EXECUTE not in ROLE_PERMISSIONS["read_only"]
