"""SWV2.2 persistence on the canonical PostgreSQL v2, without leaving history.

Runs as the backend runtime role (capstone_v2_runtime) inside capstone_backend. Every write
happens inside ONE outer transaction that is rolled back; savepoints emulate the production
``engine.begin()`` scope. Nothing is committed, no attempt is reserved and TRAIN never starts.
"""
import io
import json
import os
from contextlib import contextmanager, redirect_stdout
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.requires_docker_postgres

from src.malaria_dl.campaigns import configuration as cc  # noqa: E402
from src.malaria_dl.campaigns.contracts import CampaignError  # noqa: E402
from src.malaria_dl.campaigns.plan import resolve_plan  # noqa: E402
from src.malaria_dl.campaigns.repository import CampaignRepository  # noqa: E402
from src.malaria_dl.campaigns.service import CampaignService  # noqa: E402
from src.malaria_dl.data.dataset_integrity import VERIFIER_VERSION  # noqa: E402
from src.malaria_dl.data.governed_dataset import resolve_governed_dataset  # noqa: E402
from src.malaria_dl.execution import campaign as executor  # noqa: E402
from src.malaria_dl.execution.repository import ExecutionRepository  # noqa: E402
from src.malaria_dl.persistence.database import get_engine  # noqa: E402

DATASET = "d8c0cab5-09dd-597f-9de7-7ca01aee2ec2"
TABLES = ("experimental_campaigns", "campaign_configurations", "campaign_members", "campaign_attempts",
          "runs", "train_execution_sessions", "train_execution_records", "run_configurations", "evaluations",
          "audit_events", "models")


def counts(c):
    return {t: c.execute(text(f"SELECT count(*) FROM {t}")).scalar_one() for t in TABLES}


@pytest.fixture()
def connection():
    engine = get_engine()
    with engine.connect() as c:
        assert c.execute(text("SELECT current_user")).scalar_one() == "capstone_v2_runtime"
        before = counts(c)
        c.rollback()  # end the read-only autobegin; everything below is one outer transaction
        outer = c.begin()
        try:
            yield c
        finally:
            outer.rollback()
        assert counts(c) == before, "SWV2.2 test leaked rows into the canonical database"
        c.rollback()
    engine.dispose()


def scope_for(c):
    @contextmanager
    def scope(readonly=False):  # noqa: ARG001
        savepoint = c.begin_nested()
        try:
            yield c
        except BaseException:
            savepoint.rollback()
            raise
        savepoint.commit()

    return scope


def verifier_for(c):
    """Real read-only governed resolution; evidence row written in the rolled-back transaction."""

    def verify(dataset_version_id, consumer, expected_evidence_id=None):
        snapshot = resolve_governed_dataset(dataset_version_id)
        evidence_id = str(uuid4())
        payload = dict(verifier_version=VERIFIER_VERSION, consumer=consumer, training_run_id=None,
                       expected_evidence_id=expected_evidence_id, dataset_version_id=dataset_version_id,
                       snapshot=snapshot.metadata(), integrity_status="verified")
        c.execute(text("""INSERT INTO audit_events(id,event_type,action,resource_type,resource_id,request_method,
            request_path,correlation_id,after_state,metadata,success) VALUES (CAST(:id AS uuid),
            'ml.dataset_verification','verify','dataset_version',:version,'CLI',:source,:id,
            CAST(:payload AS jsonb),'{}'::jsonb,true)"""),
                  dict(id=evidence_id, version=dataset_version_id, source=consumer, payload=json.dumps(payload)))
        return replace(snapshot, evidence_id=evidence_id)

    return verify


def configuration():
    catalog = cc.catalog()
    c = next(p for p in catalog["presets"] if p["id"] == "system_batch_defaults")["configuration"]
    c["models"], c["optimizers"], c["seeds"] = ["custom_cnn", "densenet121"], ["adam", "sgd"], [11, 29, 47]
    c["variants"][0]["parameters"].pop("vgg16")
    c["variants"][0]["parameters"]["custom_cnn"]["max_epochs"] = 40
    c["variants"][0]["parameters"]["densenet121"]["fine_tune_epochs"] = 7
    c["protocol"]["early_stopping"]["patience"] = 9
    return c


def save(c, campaign_id=None, name="SWV2.2 rollback test"):
    snapshot = resolve_governed_dataset(DATASET)
    result = cc.resolve(configuration(), snapshot.counts)
    assert result["valid"], result["errors"]
    service = CampaignService(repository=CampaignRepository(scope=scope_for(c)), verifier=verifier_for(c))
    row = service.configure(campaign_id=campaign_id or str(uuid4()), name=name, purpose="rollback only",
                            dataset_version_id=DATASET, request=result["request"], protocol=result["protocol"],
                            actor="swv22-test")
    return row, result


def test_runtime_role_and_v2_schema(connection):
    from src.malaria_dl.execution.schema import require_e10_schema
    assert require_e10_schema(connection)["revision"] == "pg_v2_baseline"
    assert connection.execute(text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")).scalar_one() is False


def test_save_reload_and_plan_round_trip(connection):
    row, result = save(connection)
    reloaded = CampaignRepository(scope=scope_for(connection)).get(row["id"])
    plan = resolve_plan(reloaded)
    assert reloaded["state"] == "frozen"
    assert str(reloaded["dataset_version_id"]) == DATASET == plan["dataset_version_id"]
    assert reloaded["expected_count"] == result["summary"]["total_experiments"] == plan["total_experiments"] == 12
    assert len(reloaded["configurations"]) == result["summary"]["configurations"] == 4
    assert len(reloaded["members"]) == 12 and all(m["state"] == "pending" for m in reloaded["members"])
    assert reloaded["requested"] == result["request"] and reloaded["protocol"] == result["protocol"]
    assert {m["configuration_hash"] for m in reloaded["members"]} == set(result["matrix"]["configurations"])
    by_model = {c["model_id"]: c for c in plan["configurations"]}
    assert by_model["custom_cnn"]["execution"]["max_epochs"] == 40
    assert by_model["densenet121"]["execution"]["fine_tune_epochs"] == 7
    assert all(c["execution"]["early_stopping_patience"] == 9 for c in plan["configurations"])
    assert plan["command"] == f"python run_train_all_models.py --campaign-id {row['id']}"
    with pytest.raises(CampaignError, match="CAMPAIGN_DATASET_CONFLICT"):
        CampaignRepository(scope=scope_for(connection)).get(row["id"], str(uuid4()))
    stored = {r[0]: r[1] for r in connection.execute(text(
        "SELECT configuration_hash, canonical_configuration FROM campaign_configurations WHERE campaign_id=:id"),
        dict(id=row["id"]))}
    assert set(stored) == set(result["matrix"]["configurations"])


def test_retry_is_idempotent_and_conflicts_are_rejected(connection):
    campaign_id = str(uuid4())
    first, _ = save(connection, campaign_id)
    before = counts(connection)
    again, _ = save(connection, campaign_id)
    assert again["contract_hash"] == first["contract_hash"] and counts(connection) == before
    with pytest.raises(CampaignError, match="CAMPAIGN_ID_CONFLICT"):
        save(connection, campaign_id, name="otro nombre")
    assert counts(connection) == before


def test_failed_freeze_leaves_no_partial_campaign(connection, monkeypatch):
    original = CampaignRepository._materialize

    def drop_last_member(c, campaign_id, contract):
        broken = json.loads(json.dumps(contract))
        broken["matrix"]["members"] = broken["matrix"]["members"][:-1]
        # Configurations and all but one member are inserted; the freeze UPDATE must then fail.
        original(c, campaign_id, {**contract, "matrix": {**contract["matrix"],
                                                          "members": broken["matrix"]["members"]}})

    monkeypatch.setattr(CampaignRepository, "_materialize", staticmethod(drop_last_member))
    campaign_id = str(uuid4())
    before = counts(connection)
    with pytest.raises(CampaignError):
        save(connection, campaign_id)
    after = counts(connection)
    # Only the dataset evidence (written before the campaign transaction) remains.
    assert {t: after[t] - before[t] for t in TABLES} == {**dict.fromkeys(TABLES, 0), "audit_events": 1}
    assert connection.execute(text("SELECT count(*) FROM experimental_campaigns WHERE id=:id"),
                              dict(id=campaign_id)).scalar_one() == 0


def test_cli_plan_reaches_the_execution_boundary_without_train(connection, monkeypatch):
    row, result = save(connection)
    monkeypatch.setattr(executor, "ExecutionRepository", lambda: ExecutionRepository(scope=scope_for(connection)))
    monkeypatch.setattr(executor, "execute_campaign", lambda *a, **k: pytest.fail("TRAIN boundary crossed"))
    before = counts(connection)
    out = io.StringIO()
    with redirect_stdout(out):
        assert executor.main(["--campaign-id", str(row["id"]), "--plan"]) == 0
    plan = json.loads(out.getvalue())
    assert counts(connection) == before
    assert plan["campaign_id"] == str(row["id"]) and plan["dataset_version_id"] == DATASET
    assert plan["total_experiments"] == result["summary"]["total_experiments"]
    checks = {c["check"]: c for c in plan["execution_readiness"]["checks"]}
    assert checks["e10_schema"]["status"] == "PASS"
    assert checks["dataset_snapshot_unchanged"]["status"] == "PASS"
    assert checks["test_forbidden"]["status"] == "PASS"
    assert checks["frozen_adapters_available"]["status"] == "PASS"
    # Runtime identity is informational (recorded per run), never a precondition.
    assert checks["code_environment_identity"]["status"] == "INFO"
    assert checks["code_environment_identity"]["differing_keys"] == []  # same process environment as creation
    for table in ("campaign_attempts", "runs", "train_execution_sessions", "train_execution_records"):
        assert before[table] == 0


def test_role_cannot_delete_a_saved_campaign(connection):
    row, _ = save(connection)
    savepoint = connection.begin_nested()
    with pytest.raises(Exception, match="CAMPAIGN_DELETE_FORBIDDEN"):
        connection.execute(text("DELETE FROM experimental_campaigns WHERE id=:id"), dict(id=row["id"]))
    savepoint.rollback()


def test_running_inside_backend_container():
    assert os.environ.get("DATABASE_URL", "").startswith("postgresql+psycopg://capstone_v2_runtime:")
