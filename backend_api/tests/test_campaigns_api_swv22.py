"""SWV2.2 Campaign API: configure/validate/save only; the backend is the validation authority."""
import json
import os
from copy import deepcopy

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "postgresql://unused:unused@db:5432/capstone")
os.environ.setdefault("JWT_SECRET", "test-secret-with-at-least-thirty-two-characters")

from app.main import app  # noqa: E402
from app.security import Permission, Principal, ROLE_PERMISSIONS, current_principal  # noqa: E402
from app.services import campaign_configuration as service  # noqa: E402

DATASET = "d8c0cab5-09dd-597f-9de7-7ca01aee2ec2"
GOVERNED = {"items": [{
    "dataset_version_id": DATASET, "name": "malaria", "semantic_version": "1.0.0", "status": "FROZEN",
    "trainable": True, "train_records": 22180, "val_records": 2693, "test_records": 2685,
    "source_record_count": 27558, "patient_count": 201,
}]}


def routes():
    def walk(items):
        for route in items:
            if isinstance(route, APIRoute):
                yield route
            elif hasattr(route, "original_router"):
                yield from walk(route.original_router.routes)
            elif hasattr(route, "routes"):
                yield from walk(route.routes)
    return [r for r in walk(app.routes) if r.path.startswith("/api/campaigns")]


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(service, "list_governed_dataset_versions", lambda datasource: deepcopy(GOVERNED))
    app.dependency_overrides[current_principal] = lambda: Principal(
        "u", "admin", ("administrator",), frozenset(Permission))
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(current_principal, None)


def default_configuration(client):
    catalog = client.get("/api/campaigns/catalog").json()
    return catalog, deepcopy(next(p for p in catalog["presets"] if p["id"] == catalog["default_preset"])["configuration"])


def preview(client, configuration, dataset=DATASET):
    params = {"configuration": json.dumps(configuration)}
    if dataset:
        params["dataset_version_id"] = dataset
    return client.get("/api/campaigns/preview", params=params)


def test_only_configuration_routes_exist_no_execution():
    found = {(m, r.path) for r in routes() for m in r.methods}
    assert found == {("GET", "/api/campaigns/catalog"), ("GET", "/api/campaigns/preview"),
                     ("POST", "/api/campaigns"), ("GET", "/api/campaigns/{campaign_id}")}
    for word in ("execute", "run", "start", "train", "launch"):
        assert not any(word in r.path for r in routes())


def test_create_requires_the_configure_permission_with_central_audit():
    create = next(r for r in routes() if "POST" in r.methods)
    modules = set()

    def walk(dependant):
        modules.add(getattr(getattr(dependant, "call", None), "__module__", ""))
        for child in dependant.dependencies:
            walk(child)
    walk(create.dependant)
    assert "app.audit" in modules
    assert Permission.CAMPAIGNS_CONFIGURE in ROLE_PERMISSIONS["administrator"]
    assert Permission.CAMPAIGNS_CONFIGURE in ROLE_PERMISSIONS["researcher"]
    for role in ("read_only", "operator", "reviewer"):
        assert Permission.CAMPAIGNS_CONFIGURE not in ROLE_PERMISSIONS[role]


def test_catalog_discovers_models_and_closed_optimizer_domain(client):
    catalog, configuration = default_configuration(client)
    assert {m["id"] for m in catalog["models"]} == {"custom_cnn", "vgg16", "densenet121"}
    assert [o["id"] for o in catalog["optimizers"]] == ["adam", "adamw", "sgd", "adadelta"]
    assert configuration["models"] == [m["id"] for m in catalog["models"]]


def test_preview_returns_backend_total_and_checks(client):
    _, configuration = default_configuration(client)
    body = preview(client, configuration).json()
    assert body["valid"] is True
    assert body["summary"]["total_experiments"] == 36 and body["summary"]["configurations"] == 12
    assert [c["check"] for c in body["checks"]] == ["dataset", "models", "configurations", "parameters",
                                                    "total_experiments"]
    assert all(c["status"] == "PASS" for c in body["checks"])
    assert body["dataset"]["dataset_version_id"] == DATASET


def test_preview_matches_the_canonical_resolution(client):
    from src.malaria_dl.campaigns.configuration import resolve
    _, configuration = default_configuration(client)
    configuration["seeds"] = [1, 2]
    configuration["optimizers"] = ["adam"]
    body = preview(client, configuration).json()
    canonical = resolve(configuration, {"train": 22180, "val": 2693, "test": 2685})
    assert body["summary"]["total_experiments"] == canonical["matrix"]["expected_count"] == 3 * 1 * 1 * 2


def test_invalid_parameters_and_optimizers_are_rejected(client):
    _, configuration = default_configuration(client)
    configuration["variants"][0]["parameters"]["vgg16"]["max_epochs"] = 0
    body = preview(client, configuration).json()
    assert body["valid"] is False
    assert {"field": "variants[0].parameters.vgg16.max_epochs", "code": "INVALID_PARAMETER_VALUE"} in body["errors"]
    assert next(c for c in body["checks"] if c["check"] == "parameters")["status"] == "FAIL"
    _, configuration = default_configuration(client)
    configuration["optimizers"] = ["adam", "rmsprop"]
    assert preview(client, configuration).json()["valid"] is False


def test_dataset_must_exist_and_be_trainable(client):
    _, configuration = default_configuration(client)
    assert preview(client, configuration, dataset=None).json()["checks"][0]["errors"][0]["code"] == "DATASET_VERSION_REQUIRED"
    body = preview(client, configuration, dataset="00000000-0000-4000-8000-000000000001").json()
    assert body["valid"] is False and body["checks"][0]["status"] == "FAIL"


def test_malformed_documents_are_rejected_before_resolution(client):
    assert client.get("/api/campaigns/preview", params={"configuration": "{"}).status_code == 422
    _, configuration = default_configuration(client)
    configuration["seeds"] = ["11"]  # strict JSON types, no coercion
    assert preview(client, configuration).status_code == 422
    configuration["seeds"] = [11]
    configuration["unexpected"] = True
    assert preview(client, configuration).status_code == 422

