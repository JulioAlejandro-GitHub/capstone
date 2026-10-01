"""SWV2.2 Campaign API: configure/validate/save only; the backend is the validation authority."""
import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from uuid import UUID

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
    assert found == {("GET", "/api/campaigns"), ("GET", "/api/campaigns/catalog"),
                     ("GET", "/api/campaigns/preview"), ("POST", "/api/campaigns"),
                     ("GET", "/api/campaigns/{campaign_id}")}
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


# --- SWV2.3 report of created campaigns ----------------------------------------------------

def test_list_reports_created_campaigns_with_states_and_dataset(client, monkeypatch):
    from src.malaria_dl.campaigns.repository import CampaignRepository

    rows = [
        dict(
            id="11111111-1111-4111-8111-111111111111", name="Campaña demo", purpose="Validación SWV2.2",
            state="frozen", contract_hash="ab" * 32,
            frozen_at=datetime(2026, 9, 30, 22, 41, tzinfo=timezone.utc),
            created_at=datetime(2026, 9, 30, 22, 41, tzinfo=timezone.utc),
            actor="admin", dataset_version_id=DATASET, expected_count=6,
            requested={"models": ["custom_cnn", "vgg16"], "optimizers": ["adam"], "seeds": [11, 29]},
            dataset_name="malaria", dataset_semantic_version="1.0.0",
            members_by_state={"pending": 4, "excluded": 2},
        ),
        dict(
            id="22222222-2222-4222-8222-222222222222", name="Campaña antigua", purpose="Plano E7",
            state="active", contract_hash="cd" * 32,
            frozen_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            actor="admin", dataset_version_id=DATASET, expected_count=36,
            requested={"models": ["densenet121", "custom_cnn", "vgg16"],
                       "optimizers": ["adam", "sgd"], "seeds": [1, 2, 3]},
            dataset_name="malaria", dataset_semantic_version="1.0.0",
            members_by_state={"pending": 30, "active": 6},
        ),
    ]
    monkeypatch.setattr(CampaignRepository, "list_campaigns", lambda self, limit, offset: rows)
    body = client.get("/api/campaigns", params={"limit": 50, "offset": 0}).json()
    assert [i["campaign_id"] for i in body["items"]] == [
        "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"]
    first = body["items"][0]
    assert first["state"] == "frozen" and first["contract_hash"] == "ab" * 32
    assert first["dataset_name"] == "malaria" and first["dataset_semantic_version"] == "1.0.0"
    assert first["dataset_version_id"] == DATASET
    assert first["models"] == ["custom_cnn", "vgg16"] and first["optimizers"] == ["adam"]
    assert first["seeds"] == [11, 29]
    assert first["total_experiments"] == 6
    assert first["members_by_state"] == {"pending": 4, "excluded": 2}
    assert first["frozen_at"].startswith("2026-09-30T22:41")
    assert first["command"] == (
        f"python run_train_all_models.py --campaign-id {first['campaign_id']}")
    assert "configuration" not in first  # detail-only; the report stays lightweight


def test_list_limit_bounds(client, monkeypatch):
    from src.malaria_dl.campaigns.repository import CampaignRepository

    calls = []

    def fake(self, limit, offset):
        calls.append((limit, offset))
        return []

    monkeypatch.setattr(CampaignRepository, "list_campaigns", fake)
    assert client.get("/api/campaigns", params={"limit": 0}).status_code == 422
    assert client.get("/api/campaigns", params={"limit": 501}).status_code == 422
    assert client.get("/api/campaigns", params={"limit": 500, "offset": 10}).status_code == 200
    assert calls == [(500, 10)]


def test_detail_includes_the_operator_document_for_editing(client, monkeypatch):
    from src.malaria_dl.campaigns.configuration import document_from_request, resolve
    from src.malaria_dl.campaigns.contracts import CampaignError, digest
    from src.malaria_dl.campaigns.repository import CampaignRepository

    campaign_id = "22222222-2222-4222-8222-222222222222"
    _, configuration = default_configuration(client)
    configuration["seeds"] = [11, 29]
    configuration["optimizers"] = ["adam"]
    result = resolve(configuration, {"train": 22180, "val": 2693, "test": 2685})
    contract = dict(
        version="campaign_contract_v1", name="Campaña prueba", purpose="Prueba de detalle",
        experiment_id=None,
        dataset={"dataset_version_id": DATASET,
                 "counts": {"train": 22180, "val": 2693, "test": 2685},
                 "dataset_materialization_id": DATASET, "dataset_root": "/governed/malaria"},
        dataset_evidence_id=DATASET,
        requested=result["request"], protocol=result["protocol"],
        environment={"source_sha256": "ab" * 32, "python": "3.11", "tensorflow": "2.16.1",
                     "packages": {}, "determinism_environment": {}},
        matrix=result["matrix"],
    )
    row = dict(
        id=UUID(campaign_id), name="Campaña prueba", purpose="Prueba de detalle", state="frozen",
        contract_hash=digest(contract),
        frozen_at=datetime(2026, 9, 30, 22, 41, tzinfo=timezone.utc),
        dataset_version_id=UUID(DATASET), dataset_snapshot=contract["dataset"],
        dataset_evidence_id=UUID(DATASET), expected_count=result["matrix"]["expected_count"],
        requested=result["request"], protocol=result["protocol"], environment=contract["environment"],
        contract=contract,
        configurations=[dict(id=UUID(int=int(h[:32], 16), version=4), campaign_id=UUID(campaign_id),
                             configuration_hash=h, configuration=item["configuration"],
                             canonical_configuration=h, requests=item["requests"])
                        for h, item in contract["matrix"]["configurations"].items()],
        members=[dict(id=UUID(f"44444444-4444-4444-8444-{i:012d}"), campaign_id=UUID(campaign_id),
                      **m, state="excluded" if m["exclusion_reason"] else "pending",
                      accepted_attempt_id=None)
                  for i, m in enumerate(contract["matrix"]["members"])],
    )

    def fake_get(self, requested_id, dataset_version_id=None):
        if str(requested_id) != campaign_id:
            raise CampaignError("CAMPAIGN_NOT_FOUND")
        return row

    monkeypatch.setattr(CampaignRepository, "get", fake_get)
    body = client.get(f"/api/campaigns/{campaign_id}").json()
    assert body["campaign_id"] == campaign_id
    assert body["total_experiments"] == 3 * 1 * 1 * 2 == len(body["experiments"])
    assert body["state"] == "frozen" and body["frozen_at"].startswith("2026-09-30T22:41")
    assert body["configuration"] == document_from_request(result["request"], result["protocol"])
    # build_request persists the models sorted; the operator document reflects that order.
    assert body["configuration"]["models"] == ["custom_cnn", "densenet121", "vgg16"]
    assert body["configuration"]["seeds"] == [11, 29]
    assert client.get("/api/campaigns/00000000-0000-4000-8000-000000000001").status_code == 404

