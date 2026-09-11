"""Opt-in E5 only; E4 fixture guarantees synthetic schema and later cleanup."""

import os
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from src.malaria_dl.campaigns.contracts import CampaignError, digest
from src.malaria_dl.execution.artifacts import file_identity
from src.malaria_dl.execution.campaign import execute_campaign
from src.malaria_dl.execution.repository import ExecutionRepository
from test_campaigns_postgres import isolated, migration, safe_test  # noqa: F401

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_STAGE5_POSTGRES_TESTS") != "1",
    reason="Authorized Compose E5 opt-in required",
)


@pytest.fixture
def execution(isolated):  # noqa: F811 -- imported pytest fixture
    mod = migration("20260912_01_train_execution")
    mod.op = Operations(MigrationContext.configure(isolated.c))
    mod.upgrade()
    return SimpleNamespace(s=isolated, repo=ExecutionRepository(isolated.repo.scope))


def synthetic_train(repo, s):
    run, owner = str(s["run_id"]), str(s["owner"])
    root = Path(s["artifact_root"])
    root.mkdir(parents=True, exist_ok=False)
    phases = ["base"] + (
        ["fine_tuning"]
        if s["configuration"]["resolved"]["execution"]["fine_tune_epochs"]
        else []
    )
    for n, phase in enumerate(phases, 1):
        p = root / f"{n}.keras"
        p.write_bytes(b"synthetic checkpoint")
        selection = {"selected_epoch": n}
        payloads = {
            ("runtime", "configuration"): {"synthetic": True},
            ("epoch", "1"): {"epoch": n},
            ("artifact_prepared", "1"): {"epoch": n},
            ("artifact", "1"): dict(
                path=str(p), epoch=n, run_id=run, **file_identity(p)
            ),
            ("predictions", "1"): {
                "samples": [{"sample": "val/a"}, {"sample": "val/b"}]
            },
            ("selection", "1"): selection,
            ("phase", "completed"): {"epochs": 1},
        }
        for (kind, key), payload in payloads.items():
            repo.put(run, owner, kind, phase, key, payload)
    repo.put(run, owner, "calibration", "val", "selected", {"synthetic": True})
    records = repo.records(run)
    repo.finish(
        run,
        owner,
        "completed",
        {
            "epochs": len(phases),
            "selection": selection,
            "records_hash": digest(records),
        },
    )
    return 0


@safe_test
def test_frozen_twelve_and_resume_without_retraining(execution, tmp_path):
    s, repo = execution.s, execution.repo
    row = s.freeze()
    cid = str(row["id"])
    calls = []

    def launch(session, _):
        calls.append(session["run_id"])
        return synthetic_train(repo, session)

    options = {"check": lambda *a: None, "launch": launch, "loader": lambda *a: None}
    code, summary = execute_campaign(repo, cid, tmp_path, **options)
    assert code == 0 and summary["accepted"] == 12 and len(calls) == 12
    code, summary = execute_campaign(repo, cid, tmp_path, resume=True, **options)
    assert code == 0 and len(calls) == 12 and summary["members"]["verified"] == 12


@safe_test
def test_individual_failure_continues(execution, tmp_path):
    row = execution.s.freeze()
    repo = execution.repo
    calls = []

    def launch(s, _):
        calls.append(s["run_id"])
        if s["configuration"]["model_id"] == "custom_cnn":
            return 2
        return synthetic_train(repo, s)

    code, summary = execute_campaign(
        repo,
        str(row["id"]),
        tmp_path,
        check=lambda *a: None,
        launch=launch,
        loader=lambda *a: None,
    )
    assert (
        code == 2
        and summary["members"]["verified"] == 8
        and summary["members"]["failed"] == 4
    )
    assert (
        len(calls) == 20
    )  # Four failed members each consume their frozen budget of three.


@safe_test
def test_idempotency_and_fenced_owner(execution, tmp_path):
    row = execution.s.freeze()
    repo = execution.repo
    s = repo.claim(str(row["id"]), str(uuid4()), "synthetic", 1, tmp_path)
    repo.put(s["run_id"], s["owner"], "runtime", "base", "test", {"x": 1})
    repo.put(s["run_id"], s["owner"], "runtime", "base", "test", {"x": 1})
    assert len(repo.records(s["run_id"])) == 1
    with pytest.raises(CampaignError):
        repo.put(s["run_id"], s["owner"], "runtime", "base", "test", {"x": 2})
    repo.finish(
        s["run_id"], s["owner"], "interrupted", cause="synthetic termination confirmed"
    )
    with pytest.raises(CampaignError):
        repo.put(s["run_id"], s["owner"], "epoch", "base", "1", {"x": 1})


@safe_test
def test_systemic_failure_pauses_before_claim(execution, tmp_path):
    row = execution.s.freeze()
    repo = execution.repo

    def reject(*a):
        raise CampaignError("DATASET_CHANGED")

    code, summary = execute_campaign(repo, str(row["id"]), tmp_path, check=reject)
    assert code == 3 and summary["state"] == "paused" and summary["attempts"] == 0


@safe_test
def test_zero_exit_without_evidence_never_verified(execution, tmp_path):
    row = execution.s.freeze()
    repo = execution.repo
    code, summary = execute_campaign(
        repo, str(row["id"]), tmp_path, check=lambda *a: None, launch=lambda *a: 0
    )
    assert (
        code == 2 and summary["members"]["verified"] == 0 and summary["attempts"] == 36
    )


@safe_test
def test_two_executors_claim_one_member(execution, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from test_campaigns_e4 import protocol, request

    s = execution.s
    req = request()
    req["models"] = ["custom_cnn"]
    req["optimizers"] = ["adam"]
    row = s.service.create(
        name="Single synthetic member",
        purpose="concurrency",
        dataset_version_id=s.dataset["dataset_version_id"],
        request=req,
        protocol=protocol(),
        actor="synthetic",
    )
    row = s.service.freeze(str(row["id"]))
    pids = []
    scope = s.make_visible(Barrier(2), pids)

    def claim():
        return ExecutionRepository(scope).claim(
            str(row["id"]), str(uuid4()), "synthetic", 1, tmp_path
        )

    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(claim) for _ in range(2)]
        results = [f.result(timeout=15) for f in futures]
    assert sum(r is not None for r in results) == 1 and len(set(pids)) == 2
    assert len(ExecutionRepository(scope).get(str(row["id"]))["attempts"]) == 1


@safe_test
def test_parent_interruption_retains_attempt(execution, tmp_path):
    row = execution.s.freeze()
    repo = execution.repo

    def launch(*args):
        raise KeyboardInterrupt

    code, summary = execute_campaign(
        repo, str(row["id"]), tmp_path, check=lambda *a: None, launch=launch
    )
    assert (
        code == 3
        and summary["members"]["interrupted"] == 1
        and summary["attempts"] == 1
    )


@pytest.mark.parametrize(
    "point",
    [
        "before_train",
        "metrics",
        "after_checkpoint",
        "after_artifact",
        "before_accept",
        "after_accept",
    ],
)
@safe_test
def test_injected_failure_keeps_evidence(execution, tmp_path, monkeypatch, point):
    row = execution.s.freeze()
    repo = execution.repo
    cid = str(row["id"])
    if point == "before_train":

        def fail_create(*a, **k):
            raise CampaignError("SYNTHETIC_BEFORE_TRAIN")

        monkeypatch.setattr(repo, "_create_run", fail_create)
    original_put = repo.put

    def put(run, owner, kind, phase, key, payload):
        if point == "metrics" and kind == "epoch":
            raise CampaignError("SYNTHETIC_METRIC_WRITE_FAILED")
        if point == "after_checkpoint" and kind == "artifact":
            raise CampaignError("SYNTHETIC_ARTIFACT_WRITE_FAILED")
        original_put(run, owner, kind, phase, key, payload)
        if point == "after_artifact" and kind == "artifact":
            raise CampaignError("SYNTHETIC_AFTER_ARTIFACT")

    monkeypatch.setattr(repo, "put", put)
    original_finish = repo.finish

    def finish(run, owner, state, *a, **kw):
        if point == "before_accept" and state == "verified":
            raise CampaignError("SYNTHETIC_BEFORE_ACCEPT")
        original_finish(run, owner, state, *a, **kw)
        if point == "after_accept" and state == "verified":
            raise CampaignError("SYNTHETIC_AFTER_ACCEPT")

    monkeypatch.setattr(repo, "finish", finish)
    code, summary = execute_campaign(
        repo,
        cid,
        tmp_path,
        check=lambda *a: None,
        launch=lambda s, r: synthetic_train(r, s),
        loader=lambda *a: None,
    )
    assert code == 3 and summary["state"] == "paused"
    assert summary["accepted"] == (1 if point == "after_accept" else 0)
    assert summary["attempts"] == (0 if point == "before_train" else 1)
    if point in ("after_checkpoint", "after_artifact", "before_accept", "after_accept"):
        assert list(
            tmp_path.rglob("*.keras")
        )  # No automatic deletion of partial evidence.


def test_public_e5_revision_readonly():
    import re

    from sqlalchemy import text
    from src.malaria_dl.persistence.database import get_engine
    from test_campaigns_postgres import sanitized

    engine = None
    try:
        engine = get_engine()
        with engine.begin() as c:
            c.execute(text("SET TRANSACTION READ ONLY"))
            versions = (
                c.execute(text("SELECT version_num FROM public.alembic_version"))
                .scalars()
                .all()
            )
            tables = (
                c.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('train_execution_sessions','train_execution_records','campaign_execution_events') ORDER BY table_name"
                    )
                )
                .scalars()
                .all()
            )
            triggers = c.execute(
                text(
                    "SELECT count(*) FROM pg_trigger WHERE tgrelid=to_regclass('public.train_execution_records') AND tgname='train_record_guard' AND tgenabled<>'D'"
                )
            ).scalar_one()
        problems = []
        if versions != ["20260912_01"]:
            safe_versions = [
                v
                if re.fullmatch(r"[A-Za-z0-9_]{1,64}", v)
                else "INVALID_REVISION_FORMAT"
                for v in versions
            ]
            problems.append(
                f"phase=revision expected=['20260912_01'] obtained={safe_versions}"
            )
        expected = {
            "train_execution_sessions",
            "train_execution_records",
            "campaign_execution_events",
        }
        if set(tables) != expected:
            problems.append(f"phase=tables missing={sorted(expected - set(tables))}")
        if triggers != 1:
            problems.append(f"phase=trigger expected_enabled=1 obtained={triggers}")
        if problems:
            pytest.fail("E5 public READ ONLY: " + "; ".join(problems), pytrace=False)
    except Exception as exc:  # noqa: BLE001 -- no driver SQL/parameters in public diagnostics
        raise pytest.fail.Exception(
            f"E5 public READ ONLY query: {sanitized(exc)}", pytrace=False
        ) from None
    finally:
        if engine is not None:
            engine.dispose()
