"""Stage 2 evidence and eligibility: SELECT-only fixtures, never publication."""

from uuid import UUID
from unittest.mock import Mock
import httpx
import pytest
from sqlalchemy import text

from app.db import read_only_transaction
from app.main import app
from app.routes import governance
from app.services import stage2_status, training_summaries
from src.malaria_dl.governance.eligibility import stage2_eligibility
from test_e6_lineage_read_only import (
    TRAIN, REAL_TRAIN, REAL_ATTEMPT, LEGACY, fixtures, install_fixtures,
    scientific_fingerprint, attempt_id,
)

pytestmark = pytest.mark.requires_docker_postgres


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def install(monkeypatch, states=("verified",), legacy=False, train_state="completed", *, mismatch=False, unfinished=False, projected=False):
    values = fixtures(states, legacy, False, projected)
    values["runs"][0]["status"] = train_state
    for identity in values["assessment_identities"]:
        identity["identity"].update(kind="evaluate", model={"training_run_id": LEGACY if mismatch else TRAIN})
    for attempt in values["assessment_attempts"]:
        if unfinished:
            attempt["finished_at"] = None
        if attempt["verification"]:
            attempt["verification"]["metrics"] = {
                **attempt["verification"]["metrics"], "recall": .1, "f2": .1,
            }
    install_fixtures(monkeypatch, values)
    monkeypatch.setattr(stage2_status, "read_only_transaction", training_summaries.read_only_transaction)


@pytest.mark.parametrize("states,legacy,train_state,expected", [
    (("verified",), False, "completed", True),
    (("failed",), False, "completed", False),
    (("active",), False, "completed", False),
    (("interrupted",), False, "completed", False),
    (("verified",), False, "running", False),
    ((), True, "completed", True),
    ((), False, "completed", False),
    (("failed", "verified"), False, "completed", True),
    (("verified", "failed"), False, "completed", True),
    (("failed",), True, "completed", True),
])
def test_minimum_rule_ignores_missing_descriptors_explain_and_low_metrics(monkeypatch, states, legacy, train_state, expected):
    install(monkeypatch, states, legacy, train_state)
    result = stage2_status.Stage2StatusService().status(UUID(TRAIN), "malaria")
    assert result.eligible is expected
    assert result.eligible_for_stage2_production is expected
    assert result.explainability_run_ids == []
    assert result.model_name is None and result.version_number is None
    assert result.deployment_readiness.ready is False
    assert result.deployment_readiness.checkpoint_accessible is False
    assert result.published is result.available is False
    assert any(b.code == "CHECKPOINT_UNAVAILABLE" for b in result.technical_blockers)
    if states and "verified" in states:
        assert str(result.evaluation_attempt_id) == attempt_id(states.index("verified") + 1)
        assert result.evaluation_run_id is None


@pytest.mark.parametrize("mismatch,unfinished", [(True, False), (False, True)])
def test_e6_requires_exact_identity_and_finished_verification(monkeypatch, mismatch, unfinished):
    install(monkeypatch, mismatch=mismatch, unfinished=unfinished)
    result = stage2_status.Stage2StatusService().status(UUID(TRAIN), "malaria")
    assert result.eligible is False
    assert result.eligibility.evaluate_completed is False


def test_projected_retry_uses_the_same_canonical_e6_identity(monkeypatch):
    install(monkeypatch, ("failed", "verified"), legacy=True, projected=True)
    result = stage2_status.Stage2StatusService().status(UUID(TRAIN), "malaria")
    assert result.eligible
    assert str(result.evaluation_attempt_id) == attempt_id(2)
    assert result.evaluation_source_kind == "assessment_e6"
    assert result.evaluation_run_id is None


def test_readiness_never_changes_the_minimum_rule():
    context = dict(train_status="completed", evaluation_status="completed", evaluation_run_id="legacy",
                   recall=.1, f2=.1, model_name=None, architecture=None, version_number=None,
                   checkpoint_accessible=False, explainability_run_ids=[])
    assert stage2_eligibility(context)[0] is True
    context["evaluation_link_valid"] = False
    assert stage2_eligibility(context)[0] is False


@pytest.mark.parametrize("operational_blockers", [[], [{"code": "MODEL_NOT_LOADABLE", "message": "Modelo no cargable."}]])
def test_registered_legacy_candidate_preserves_operational_checks(monkeypatch, operational_blockers):
    version_id = "88888888-8888-4888-8888-888888888888"
    artifact_id = "99999999-9999-4999-8999-999999999999"
    repository = stage2_status.repository
    monkeypatch.setattr(repository, "read_training", lambda *args: {"train_status": "completed", "run_type": "training"})
    monkeypatch.setattr(repository, "read_evaluations", lambda *args: [{
        "evaluation_source_kind": "run", "evaluation_run_id": LEGACY,
        "evaluation_status": "completed", "evaluation_link_valid": True,
        "model_version_id": version_id, "checkpoint_artifact_id": artifact_id,
    }])
    monkeypatch.setattr(repository, "read_explanations", lambda *args: [])
    monkeypatch.setattr(repository, "read_version", lambda *args: {
        "id": version_id, "checkpoint_artifact_id": artifact_id, "artifact_path": "/fixture/model.keras",
        "artifact_sha256": "a" * 64, "artifact_size_bytes": 123,
    })
    monkeypatch.setattr(repository, "read_publication", lambda *args: None)
    monkeypatch.setattr(repository, "read_deployment", lambda *args: None)
    monkeypatch.setattr(stage2_status, "checkpoint_readiness", lambda *args: (True, True))
    preview = Mock()
    preview.preview.return_value = {"model_version_id": version_id, "technical_blockers": operational_blockers}
    factory = Mock(return_value=preview)
    monkeypatch.setattr(stage2_status, "Stage2ModelAvailabilityService", factory)
    result = stage2_status.Stage2StatusService().status(UUID(TRAIN), "malaria")
    assert result.eligible
    assert result.deployment_readiness.ready == (not operational_blockers)
    assert result.next_action == ("enable_for_stage2" if not operational_blockers else "unavailable")
    preview.preview.assert_called_once_with(TRAIN)
    preview.enable.assert_not_called()
    with factory.call_args.args[0]() as connection:
        assert connection.execute(text("SHOW transaction_read_only")).scalar_one() == "on"


@pytest.mark.anyio
async def test_query_failure_is_http_error_not_false_eligibility():
    service = Mock()
    service.status.side_effect = RuntimeError("database unavailable")
    app.dependency_overrides[governance.get_stage2_status_service] = lambda: service
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/training-runs/{TRAIN}/stage2-release-status")
        assert response.status_code == 503
        assert '"eligible":false' not in response.text
        assert "consultar el estado de liberación" in response.text
    finally:
        app.dependency_overrides.pop(governance.get_stage2_status_service, None)


def publication_fingerprint() -> dict:
    with read_only_transaction("malaria") as connection:
        return {table: connection.execute(text(
            f"SELECT md5(coalesce(string_agg(to_jsonb(t)::text, '' ORDER BY to_jsonb(t)::text), '')) FROM public.{table} t"
        )).scalar_one() for table in (
            "stage2_model_publications", "stage2_model_publication_events",
            "deployed_model_versions", "model_versions", "artifacts",
        )}


@pytest.mark.anyio
async def test_real_status_is_eligible_read_only_and_not_published():
    before = scientific_fingerprint(), publication_fingerprint()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        release = await client.get(f"/api/training-runs/{REAL_TRAIN}/stage2-release-status")
        availability = await client.get(f"/api/training-runs/{REAL_TRAIN}/stage2-availability")
    assert release.status_code == availability.status_code == 200
    assert release.json() == availability.json()
    result = release.json()
    assert result["eligible"] is True
    assert result["train_status"] == "completed"
    assert result["evaluation_status"] == "verified"
    assert result["evaluation_attempt_id"] == REAL_ATTEMPT
    assert result["evaluation_run_id"] is None
    assert result["model_name"] == "custom_cnn"
    assert result["architecture"] == "Custom CNN"
    assert result["model_version_id"] == "3ffcb0ec-324f-43fb-8521-d55cbe81f229"
    assert result["model_version_registered"] is False
    assert result["version_number"] is None
    assert result["checkpoint"] == "epoch_2.keras"
    assert result["checkpoint_bytes"] == 5150164
    assert result["deployment_readiness"]["ready"] is False
    assert result["published"] is result["available"] is False
    assert result["blockers"] == []
    assert {b["code"] for b in result["technical_blockers"]} >= {
        "MODEL_VERSION_NOT_REGISTERED", "E6_PUBLICATION_REFERENCE_UNSUPPORTED",
    }
    assert (scientific_fingerprint(), publication_fingerprint()) == before
