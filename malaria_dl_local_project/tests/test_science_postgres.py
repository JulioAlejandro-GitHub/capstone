"""E7 opt-in Compose: synthetic schema, no operational results or TEST inference."""

import os
from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from src.malaria_dl.campaigns.contracts import CampaignError
from src.malaria_dl.science.comparison import compare
from src.malaria_dl.science.protocol import load_protocol
from src.malaria_dl.science.repository import EVENT, ScienceRepository
from test_assessment_postgres import assessment  # noqa: F401
from test_campaigns_postgres import isolated, safe_test  # noqa: F401

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_STAGE7_POSTGRES_TESTS") != "1",
    reason="Authorized Compose E7 opt-in required",
)


def preparation(dataset):
    return compare(
        load_protocol(),
        dataset,
        "val",
        [],
        lambda *_: pytest.fail("no reader expected"),
        provenance={"synthetic_test": True},
    )


@safe_test
def test_report_roundtrip_idempotent_immutable_and_rollback(isolated):  # noqa: F811
    s = isolated
    # Commit ONLY the disposable fixture schema, as E4/E6 concurrency tests do.
    # All E7 report writes below stay within an explicit outer transaction.
    s.make_visible()
    outer = s.c.begin()
    s.c.execute(text(f"SET LOCAL search_path TO {s.schema},pg_catalog"))
    repo = ScienceRepository(s.repo.scope)
    report = preparation(s.dataset)
    report_id = None
    try:
        report_id = repo.persist_report(report)
        assert repo.read_report(report_id) == report
        assert repo.persist_report(report) == report_id
        assert (
            s.c.execute(
                text("SELECT count(*) FROM audit_events WHERE event_type=:event"),
                {"event": EVENT},
            ).scalar_one()
            == 1
        )
        with pytest.raises(DBAPIError), s.c.begin_nested():
            s.c.execute(
                text(
                    "UPDATE audit_events SET success=false WHERE id=CAST(:id AS uuid)"
                ),
                {"id": report_id},
            )
        assert s.c.execute(text("SELECT 1")).scalar_one() == 1
        with s.c.engine.connect() as probe, probe.begin():
            probe.execute(text("SET TRANSACTION READ ONLY"))
            assert (
                probe.execute(
                    text(
                        f"SELECT count(*) FROM {s.schema}.audit_events WHERE id=CAST(:id AS uuid)"
                    ),
                    {"id": report_id},
                ).scalar_one()
                == 0
            )
        print(
            "E7 synthetic report: exact readback, one event, append-only rejection, outer transaction usable"
        )
    finally:
        outer.rollback()
        # Runs even if the body fails. Pytest retains primary and cleanup failures.
        with s.c.engine.connect() as probe, probe.begin():
            probe.execute(text("SET TRANSACTION READ ONLY"))
            assert (
                probe.execute(
                    text(
                        f"SELECT count(*) FROM {s.schema}.audit_events WHERE event_type=:event"
                    ),
                    {"event": EVENT},
                ).scalar_one()
                == 0
            )
        print(
            "E7 report rollback: zero events from another connection; no commit durability claimed"
        )


@safe_test
def test_report_failed_write_no_export_and_savepoint_recovery(
    isolated,  # noqa: F811
    monkeypatch,
    tmp_path,
):
    from src.malaria_dl.science import repository as module
    from src.malaria_dl.science.reporting import export_report

    repo = ScienceRepository(isolated.repo.scope)
    real = module.execute

    def broken(c, sql, **params):
        if "INSERT INTO audit_events" in sql:
            return c.execute(text("SELECT 1/0"))
        return real(c, sql, **params)

    monkeypatch.setattr(module, "execute", broken)
    with pytest.raises(CampaignError, match="DATABASE_OPERATION_FAILED"):
        repo.persist_report(preparation(isolated.dataset))
    assert isolated.c.execute(text("SELECT 1")).scalar_one() == 1
    assert (
        isolated.c.execute(
            text("SELECT count(*) FROM audit_events WHERE event_type=:e"), {"e": EVENT}
        ).scalar_one()
        == 0
    )
    with pytest.raises(CampaignError):
        export_report(repo, str(uuid4()), tmp_path / "export")
    assert not (tmp_path / "export").exists()
    monkeypatch.setattr(module, "execute", real)
    assert (
        repo.read_report(repo.persist_report(preparation(isolated.dataset)))["state"]
        == "preparation_missing_evidence"
    )


@safe_test
def test_e6_explanation_inventory_and_final_lock_without_inference(
    assessment,  # noqa: F811
    monkeypatch,
):
    """Exercise E6 SQL constraints with synthetic lineage; no model load or runtime."""
    from src.malaria_dl.assessment import lineage
    from src.malaria_dl.assessment.contracts import threshold
    from src.malaria_dl.campaigns.contracts import digest
    from src.malaria_dl.science import comparison
    from src.malaria_dl.science.protocol import e6_protocol

    x = assessment
    repo = ScienceRepository(x.s.repo.scope)
    assert repo.associated_explanations(str(uuid4())) == []
    v = deepcopy(x.value)
    v["protocol"] = e6_protocol(load_protocol(), 0.5)
    v["decision"] = threshold(".5", v["protocol"])
    # This test isolates the final-lock SQL path; pure tests verify candidate selection.
    report = preparation(x.s.dataset)
    report["selection"] = {
        "candidate": {
            "model": v["model"],
            "decision": v["decision"],
            "evaluation_id": str(uuid4()),
            "e6_protocol": v["protocol"],
        }
    }
    monkeypatch.setattr(repo, "read_report", lambda _: report)
    monkeypatch.setattr(comparison, "read_evaluation", lambda *args: {"identity": v})
    final = deepcopy(v)
    final["split"] = "test"
    final["purpose"] = "final"
    for sample in final["samples"]:
        sample["split"] = "test"
    monkeypatch.setattr(
        lineage, "dataset_samples", lambda *args, **kwargs: final["samples"]
    )
    report_id = str(uuid4())
    fingerprint = repo.freeze_final(report_id, final)
    assert (
        fingerprint == digest(final)
        and repo.freeze_final(report_id, final) == fingerprint
    )
    assert (
        x.s.c.execute(text("SELECT count(*) FROM assessment_final_locks")).scalar_one()
        == 1
    )
    # Reserving an attempt is allowed by E6 only for the exact locked synthetic identity.
    attempt, created = repo.reserve(final, x.root)
    assert created and attempt["state"] == "active"
    changed = deepcopy(final)
    changed["seed"] += 1
    with pytest.raises(CampaignError):
        repo.reserve(changed, x.root)
    assert (
        x.s.c.execute(text("SELECT count(*) FROM assessment_results")).scalar_one() == 0
    )
    assert x.s.c.execute(text("SELECT 1")).scalar_one() == 1
