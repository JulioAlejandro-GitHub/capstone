"""E8 opt-in, synthetic audit documents; no operational predictions or TRAIN."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from src.malaria_dl.campaigns.contracts import CampaignError
from src.malaria_dl.science.ensemble_reporting import compare_results
from src.malaria_dl.science.ensemble_repository import (
    ComparisonRepository,
    ConfigurationRepository,
    EvaluationRepository,
    FailureRepository,
)
from test_campaigns_postgres import isolated, safe_test  # noqa: F401
from test_ensemble_e8 import ready

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_STAGE8_POSTGRES_TESTS") != "1",
    reason="Authorized Compose E8 opt-in required",
)


@safe_test
def test_configuration_evaluation_comparison_roundtrip_and_rollback(isolated, tmp_path):  # noqa: F811
    s = isolated
    s.make_visible()
    outer = s.c.begin()
    s.c.execute(text(f"SET LOCAL search_path TO {s.schema},pg_catalog"))
    try:
        _es, _req, config, result, _reader = ready(tmp_path)
        configs = ConfigurationRepository(s.repo.scope)
        results = EvaluationRepository(s.repo.scope)
        reports = ComparisonRepository(s.repo.scope)
        cid = configs.persist_report(config)
        assert configs.read_report(cid) == config
        assert (
            cid == result["configuration_id"] and configs.persist_report(config) == cid
        )
        eid = results.persist_report(result)
        assert results.read_report(eid) == result
        report = compare_results([eid], results.read_report)
        rid = reports.persist_report(report)
        assert reports.read_report(rid) == report
        assert (
            s.c.execute(
                text(
                    "SELECT count(*) FROM audit_events WHERE event_type LIKE 'ml.ensemble%' "
                )
            ).scalar_one()
            == 3
        )
        with pytest.raises(DBAPIError), s.c.begin_nested():
            s.c.execute(
                text(
                    "UPDATE audit_events SET success=false WHERE id=CAST(:id AS uuid)"
                ),
                {"id": eid},
            )
        assert s.c.execute(text("SELECT 1")).scalar_one() == 1
        print(
            "E8 configuration/evaluation/comparison: exact readback, 3 events, immutable; no synthetic TRAIN inserted"
        )
    finally:
        outer.rollback()
        with s.c.engine.connect() as probe, probe.begin():
            probe.execute(text("SET TRANSACTION READ ONLY"))
            assert (
                probe.execute(
                    text(
                        f"SELECT count(*) FROM {s.schema}.audit_events WHERE event_type LIKE 'ml.ensemble%' "
                    )
                ).scalar_one()
                == 0
            )
        print(
            "E8 rollback: zero ensemble events from another connection; commit durability not claimed"
        )


@safe_test
def test_failed_write_and_failure_audit_are_explicit(isolated, tmp_path, monkeypatch):  # noqa: F811
    from src.malaria_dl.science import repository as base

    _es, _req, config, result, _reader = ready(tmp_path)
    configs = ConfigurationRepository(isolated.repo.scope)
    configs.persist_report(config)
    repo = EvaluationRepository(isolated.repo.scope)
    original = base.execute

    def broken(c, sql, **params):
        if "INSERT INTO audit_events" in sql:
            return c.execute(text("SELECT 1/0"))
        return original(c, sql, **params)

    monkeypatch.setattr(base, "execute", broken)
    with pytest.raises(CampaignError):
        repo.persist_report(result)
    assert isolated.c.execute(text("SELECT 1")).scalar_one() == 1
    assert (
        isolated.c.execute(
            text(
                "SELECT count(*) FROM audit_events WHERE event_type='ml.ensemble_evaluation'"
            )
        ).scalar_one()
        == 0
    )
    monkeypatch.setattr(base, "execute", original)
    failure = {
        "schema": "ensemble_failure_e8_v1",
        "state": "failed",
        "command": "combine",
        "configuration_id": result["configuration_id"],
        "reason": "SYNTHETIC_MEMBER_FAILED",
    }
    audit = FailureRepository(isolated.repo.scope)
    fid = audit.persist_report(failure)
    assert audit.read_report(fid) == failure
    assert (
        isolated.c.execute(
            text("SELECT success FROM audit_events WHERE id=CAST(:id AS uuid)"),
            {"id": fid},
        ).scalar_one()
        is False
    )
    assert repo.read_report(repo.persist_report(result)) == result


@safe_test
def test_configuration_reference_required_and_event_types_separate(isolated, tmp_path):  # noqa: F811
    _es, _req, config, result, _reader = ready(tmp_path)
    repo = EvaluationRepository(isolated.repo.scope)
    with pytest.raises(CampaignError):
        repo.persist_report(result)
    cid = ConfigurationRepository(isolated.repo.scope).persist_report(config)
    with pytest.raises(CampaignError):
        repo.read_report(cid)
    result["configuration_id"] = str(uuid4())
    with pytest.raises(CampaignError):
        repo.persist_report(result)
    assert (
        isolated.c.execute(
            text(
                "SELECT count(*) FROM audit_events WHERE event_type='ml.ensemble_evaluation'"
            )
        ).scalar_one()
        == 0
    )
