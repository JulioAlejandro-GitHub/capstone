import os
import re

import pytest
from fastapi.routing import APIRoute

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "postgresql://unused:unused@db:5432/capstone")
os.environ.setdefault("JWT_SECRET", "test-secret-with-at-least-thirty-two-characters")

from app.main import app
from app.security import Permission, ROLE_PERMISSIONS


MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
SERVICE_AUDITED_LEGACY_ROUTES = {
    ("POST", "/api/v1/analysis/queue"),
    ("POST", "/api/v1/analysis/queue/{queue_item_id}/execute"),
    ("POST", "/api/v1/analysis/queue/{queue_item_id}/retry"),
}


def _api_routes(routes):
    """Traverse FastAPI 0.137's lazy ``_IncludedRouter`` wrappers."""

    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        elif hasattr(route, "original_router"):
            yield from _api_routes(route.original_router.routes)
        elif hasattr(route, "routes"):
            yield from _api_routes(route.routes)


def _mutable_routes():
    return [
        route
        for route in _api_routes(app.routes)
        if set(route.methods) & MUTATING_METHODS
        and route.path != "/api/v1/auth/login"
    ]


def _dependency_tree(dependant):
    yield dependant
    for child in getattr(dependant, "dependencies", ()):
        yield from _dependency_tree(child)


def _has_central_audit_policy(route):
    return any(
        getattr(getattr(item, "call", None), "__module__", "") == "app.audit"
        for item in _dependency_tree(route.dependant)
    )


def _openapi_path(path):
    return re.sub(r"{([^}:]+):[^}]+}", r"{\1}", path)


def test_every_legacy_mutation_has_central_audited_policy():
    routes = _mutable_routes()
    assert routes, "el inventario de mutaciones no puede ser vacío"

    route_operations = {
        (method, _openapi_path(route.path))
        for route in routes
        for method in set(route.methods) & MUTATING_METHODS
    }
    openapi_operations = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method.upper() in MUTATING_METHODS
        and path != "/api/v1/auth/login"
    }
    assert route_operations == openapi_operations

    # These three pre-existing queue operations write their audit event inside
    # QualityQueueService's own transaction. Every other mutation must expose a
    # central app.audit dependency in FastAPI's resolved dependency tree.
    service_audited = {
        (method, route.path)
        for route in routes
        if not _has_central_audit_policy(route)
        for method in set(route.methods) & MUTATING_METHODS
    }
    assert service_audited == SERVICE_AUDITED_LEGACY_ROUTES


def test_cell_classification_mutations_are_not_audit_policy_exceptions():
    routes = [
        route
        for route in _mutable_routes()
        if route.path.startswith("/api/v1/cell-classification/")
    ]
    assert {route.path for route in routes} == {
        "/api/v1/cell-classification/classification-runs",
        "/api/v1/cell-classification/predictions/{prediction_id}/explanation",
        "/api/v1/cell-classification/predictions/{prediction_id}/human-classification",
        "/api/v1/cell-classification/predictions/{prediction_id}/reviews",
    }
    assert all(_has_central_audit_policy(route) for route in routes)


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


def test_cell_classification_role_matrix_is_least_privilege():
    read = Permission.SCIENTIFIC_CELL_CLASSIFICATION_READ
    execute = Permission.SCIENTIFIC_CELL_CLASSIFICATION_EXECUTE
    explain = Permission.SCIENTIFIC_CELL_CLASSIFICATION_EXPLAIN
    review = Permission.SCIENTIFIC_CELL_CLASSIFICATION_REVIEW

    assert {read, execute, explain, review} <= ROLE_PERMISSIONS["administrator"]
    assert {read, execute, explain, review} <= ROLE_PERMISSIONS["researcher"]
    assert {read, execute} <= ROLE_PERMISSIONS["operator"]
    assert explain not in ROLE_PERMISSIONS["operator"]
    assert review not in ROLE_PERMISSIONS["operator"]
    assert {read, explain, review} <= ROLE_PERMISSIONS["reviewer"]
    assert execute not in ROLE_PERMISSIONS["reviewer"]
    assert read in ROLE_PERMISSIONS["read_only"]
    assert not {execute, explain, review} & ROLE_PERMISSIONS["read_only"]
