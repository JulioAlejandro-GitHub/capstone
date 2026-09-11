"""E6 opt-in Compose. Writes only to E4's disposable schema, never operational TEST."""

import os
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from src.malaria_dl.assessment.contracts import prediction, verify_rows
from src.malaria_dl.assessment.repository import AssessmentRepository
from src.malaria_dl.assessment.service import explanation_spec, run
from src.malaria_dl.campaigns.contracts import CampaignError, canonical, digest
from src.malaria_dl.execution.repository import ExecutionRepository
from test_assessment_e6 import Runtime, value
from test_campaigns_postgres import isolated, migration, safe_test  # noqa: F401

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_STAGE6_POSTGRES_TESTS") != "1",
    reason="Authorized Compose E6 opt-in required",
)


@pytest.fixture
def assessment(isolated, tmp_path):  # noqa: F811
    s = isolated
    for name in ("20260912_01_train_execution", "20260912_02_assessments"):
        mod = migration(name)
        mod.op = Operations(MigrationContext.configure(s.c))
        mod.upgrade()
    campaign = s.freeze()
    train = ExecutionRepository(s.repo.scope).claim(
        campaign["id"], str(uuid4()), "synthetic", 1, tmp_path / "train"
    )
    v = value(tmp_path)
    v["model"]["training_run_id"] = str(train["run_id"])
    v["dataset"] = s.dataset
    return SimpleNamespace(
        s=s,
        repo=AssessmentRepository(s.repo.scope),
        value=v,
        root=tmp_path,
        train=train,
        campaign=campaign,
    )


@safe_test
def test_roundtrip_batches_duplicate_failure_and_retry(assessment):
    x = assessment
    v = x.value
    a, _ = x.repo.reserve(v, x.root)
    rows = [prediction(s, 0.4, v["decision"]) for s in v["samples"]]
    x.repo.write_batch(a["id"], a["owner"], rows[:1])
    x.repo.write_batch(a["id"], a["owner"], rows[:1])
    assert len(x.repo.results(a["id"])) == 1
    bad = deepcopy(rows[0])
    bad["raw_score"] = 0.9
    with pytest.raises(CampaignError):
        x.repo.write_batch(a["id"], a["owner"], [bad])
    with pytest.raises(CampaignError):
        x.repo.finish(a["id"], a["owner"], "verified", {"count": 2, "sha256": "a" * 64})
    x.repo.finish(a["id"], a["owner"], "failed", cause="SYNTHETIC_FAILURE")
    b = run(x.repo, v, x.root, Runtime)
    assert b["state"] == "verified" and b["id"] != a["id"]
    assert len(x.repo.results(a["id"])) == 1 and len(x.repo.results(b["id"])) == 2
    assert (
        run(x.repo, v, x.root, lambda v: pytest.fail("reuse predicted"))["id"]
        == b["id"]
    )


@safe_test
def test_owner_fenced_and_verified_results_immutable(assessment):
    x = assessment
    a, _ = x.repo.reserve(x.value, x.root)
    with pytest.raises(CampaignError):
        x.repo.write_batch(
            a["id"],
            str(uuid4()),
            [prediction(x.value["samples"][0], 0.2, x.value["decision"])],
        )
    with pytest.raises(CampaignError):
        x.repo.finish(a["id"], str(uuid4()), "failed")
    rows = [prediction(s, 0.4, x.value["decision"]) for s in x.value["samples"]]
    x.repo.write_batch(a["id"], a["owner"], rows)
    x.repo.finish(a["id"], a["owner"], "verified", verify_rows(x.value, rows))
    with pytest.raises(CampaignError):
        x.repo.write_batch(a["id"], a["owner"], rows)
    with pytest.raises(CampaignError):
        x.repo.finish(a["id"], a["owner"], "failed")


def reservation_diagnostic(exc, phase):
    original = getattr(exc, "orig", exc)
    name = getattr(getattr(original, "diag", None), "constraint_name", None)
    allowed = {
        "assessment_identities_identity_hash_key",
        "assessment_identities_structural_hash_key",
        "uq_assessment_live",
    }
    return {
        "phase": phase,
        "type": type(original).__name__,
        "sqlstate": getattr(original, "sqlstate", None),
        "constraint": name if name in allowed else None,
    }


@safe_test
def test_concurrent_equivalent_requests_have_one_owner(assessment, monkeypatch):
    from src.malaria_dl.assessment import repository as implementation

    x = assessment
    repo = AssessmentRepository(x.s.make_visible())
    original_execute = implementation.execute
    diagnostics = []
    backend_pids = set()
    mode = "original"
    insert_barrier = Barrier(2)

    def observed(c, statement, **params):
        insertion = "INSERT INTO assessment_identities" in statement
        if insertion:
            # Both independent connections reach INSERT before either is executed.
            backend_pids.add(c.exec_driver_sql("SELECT pg_backend_pid()").scalar_one())
            insert_barrier.wait(timeout=5)
            if mode == "original":
                statement = statement.replace(
                    "ON CONFLICT DO NOTHING", "ON CONFLICT(identity_hash) DO NOTHING"
                )
        try:
            return original_execute(c, statement, **params)
        except Exception as exc:
            diagnostics.append(
                reservation_diagnostic(exc, mode + (":INSERT" if insertion else ":SQL"))
            )
            raise

    monkeypatch.setattr(implementation, "execute", observed)

    def contend(v):
        successes, failures = [], []
        with ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(repo.reserve, v, x.root) for _ in range(2)]
            # Collect both outcomes; never lose the second worker's diagnostic.
            for future in futures:
                try:
                    successes.append(future.result(timeout=15))
                except Exception as exc:  # noqa: BLE001 -- no exception text or SQL parameters
                    failures.append(reservation_diagnostic(exc, mode + ":RESERVE"))
        return successes, failures

    # Diagnostic-only reproduction of the prior query in the disposable schema.
    # Scheduling may not reproduce it; no assertion requires the old code to fail.
    old_results, old_failures = contend(x.value)
    print(
        {
            "E6_original_reservation": {
                "successes": len(old_results),
                "failures": old_failures,
                "sql": list(diagnostics),
            }
        }
    )
    assert len(backend_pids) == 2

    mode = "corrected"
    diagnostics.clear()
    backend_pids.clear()
    insert_barrier = Barrier(2)
    corrected = deepcopy(x.value)
    corrected["seed"] += 1  # a fresh identity; do not reuse the diagnostic reservation
    results, failures = contend(corrected)
    if failures:
        pytest.fail(
            f"E6 corrected reservation: {failures}; SQL diagnostics: {diagnostics}",
            pytrace=False,
        )
    assert len(backend_pids) == 2
    assert sum(created for _, created in results) == 1
    assert len({str(a["id"]) for a, _ in results}) == 1
    assert len({str(a["owner"]) for a, _ in results}) == 1
    assert all(a["state"] == "active" for a, _ in results)
    with repo.transaction(readonly=True) as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM assessment_identities WHERE identity_hash=:hash"
                ),
                {"hash": digest(corrected)},
            ).scalar_one()
            == 1
        )
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM assessment_attempts WHERE identity_id=CAST(:id AS uuid)"
                ),
                {"id": str(results[0][0]["identity_id"])},
            ).scalar_one()
            == 1
        )
    print(
        "E6 corrected reservation: two connections, one identity, one active attempt, one owner"
    )


@safe_test
def test_final_requires_prior_exact_lock_and_synthetic_allow(assessment):
    x = assessment
    v = deepcopy(x.value)
    v["purpose"] = "final"
    v["split"] = "test"
    v["protocol"].update(purposes=["final"], splits=["test"])
    for s in v["samples"]:
        s["split"] = "test"
    with pytest.raises(CampaignError):
        x.repo.reserve(v, x.root)
    evidence = {
        "status": "locked",
        "identity_hash": digest(v),
        "candidate": v["model"],
        "decision": v["decision"],
    }
    with x.repo.transaction() as c:
        c.execute(
            text(
                "INSERT INTO assessment_final_locks VALUES(CAST(:id AS uuid),:hash,CAST(:evidence AS jsonb),DEFAULT)"
            ),
            {"id": str(uuid4()), "hash": digest(v), "evidence": canonical(evidence)},
        )
    assert run(x.repo, v, x.root, Runtime)["state"] == "verified"


@pytest.mark.parametrize(
    "path",
    [
        ("model", "sha256"),
        ("model", "input_contract"),
        ("decision", "effective"),
        ("dataset",),
        ("samples",),
        ("purpose",),
    ],
)
@safe_test
def test_sql_rejects_json_null_identity(assessment, path):
    x = assessment
    v = deepcopy(x.value)
    node = v
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = None
    with pytest.raises(CampaignError):
        x.repo.reserve(v, x.root)


@safe_test
def test_structural_hash_normalizes_numeric_spellings(assessment):
    x = assessment
    with x.repo.transaction(readonly=True) as c:
        a = c.execute(
            text("SELECT assessment_structural_hash(CAST(:v AS jsonb))"),
            {"v": '{"score":0.5,"tiny":0.00000001}'},
        ).scalar_one()
        b = c.execute(
            text("SELECT assessment_structural_hash(CAST(:v AS jsonb))"),
            {"v": '{"tiny":1e-8,"score":0.50}'},
        ).scalar_one()
        assert a == b


@safe_test
def test_explain_artifacts_roundtrip(assessment):
    x = assessment
    v = deepcopy(x.value)
    v.update(
        kind="explain", explanation=explanation_spec("gradcam", "conv", 1, None, [])
    )
    a = run(x.repo, v, x.root, Runtime)
    assert a["state"] == "verified" and len(x.repo.artifacts(a["id"])) == 4
    assert (
        run(x.repo, v, x.root, lambda v: pytest.fail("reuse explained"))["id"]
        == a["id"]
    )


@safe_test
def test_readback_after_commit_in_separate_connection(assessment):
    x = assessment
    scope = x.s.make_visible()
    repo = AssessmentRepository(scope)
    a = run(repo, x.value, x.root, Runtime)
    other = AssessmentRepository(scope)
    assert other.attempt(a["id"])["state"] == "verified"
    assert other.results(a["id"]) == repo.results(a["id"])


@safe_test
def test_public_e6_revision_readonly():
    from src.malaria_dl.campaigns.repository import connection_scope

    with connection_scope(readonly=True) as c:
        revisions = list(
            c.execute(text("SELECT version_num FROM alembic_version")).scalars()
        )
        tables = set(
            c.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'assessment_%'"
                )
            ).scalars()
        )
        enabled = c.execute(
            text(
                "SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND t.tgname IN ('assessment_attempt_guard','assessment_result_guard','assessment_artifact_guard','assessment_consumer_guard','assessment_identity_guard','assessment_identity_immutable','assessment_lock_immutable','assessment_consumer_immutable') AND t.tgenabled='O'"
            )
        ).scalar_one()
    expected = {
        "assessment_identities",
        "assessment_attempts",
        "assessment_results",
        "assessment_artifacts",
        "assessment_final_locks",
        "assessment_campaign_consumers",
    }
    if revisions != ["20260912_02"] or not expected <= tables or enabled != 8:
        pytest.fail(
            f"E6 public READ ONLY: phase=revision expected=['20260912_02'] obtained={revisions}; phase=tables missing={sorted(expected - tables)}; phase=triggers expected=8 obtained={enabled}",
            pytrace=False,
        )


@safe_test
def test_raw_sql_rejects_wrong_patient_and_preserves_outer_transaction(assessment):
    x = assessment
    a, _ = x.repo.reserve(x.value, x.root)
    bad = prediction(x.value["samples"][0], 0.4, x.value["decision"])
    bad["patient_id"] = str(uuid4())
    with pytest.raises(CampaignError):
        x.repo.write_batch(a["id"], a["owner"], [bad])
    assert x.repo.attempt(a["id"])["state"] == "active" and not x.repo.results(a["id"])


@safe_test
def test_corrupt_verification_count_rejected(assessment):
    x = assessment
    a, _ = x.repo.reserve(x.value, x.root)
    rows = [prediction(s, 0.4, x.value["decision"]) for s in x.value["samples"]]
    x.repo.write_batch(a["id"], a["owner"], rows)
    with pytest.raises(CampaignError):
        x.repo.finish(
            a["id"], a["owner"], "verified", {"count": None, "sha256": "a" * 64}
        )
    assert x.repo.attempt(a["id"])["state"] == "active"


@safe_test
def test_campaign_consumer_requires_exact_accepted_train(assessment, monkeypatch):
    from src.malaria_dl.execution.artifacts import verify_session
    from test_campaign_executor_postgres import synthetic_train

    x = assessment
    repo = ExecutionRepository(x.s.repo.scope)
    original_put = repo.put

    def put(run_id, owner, kind, phase, key, payload):
        if kind == "artifact":
            payload = dict(payload, version_id=x.value["model"]["model_version_id"])
        original_put(run_id, owner, kind, phase, key, payload)

    monkeypatch.setattr(repo, "put", put)
    a, _ = x.repo.reserve(x.value, x.root)
    member = x.campaign["members"][0]["id"]
    with pytest.raises(CampaignError):
        x.repo.consume(x.campaign["id"], member, a)
    synthetic_train(repo, x.train)
    session = repo.session(x.train["run_id"])
    proof = verify_session(repo, session, lambda *a: None)
    repo.finish(session["run_id"], session["owner"], "verified", proof)
    exact = deepcopy(x.value)
    exact["model"].update(
        {k: proof["artifact"][k] for k in ("path", "sha256", "bytes")}
    )
    exact["model"]["input_contract"] = session["configuration"]["resolved"][
        "input_contract"
    ]
    b = run(x.repo, exact, x.root, Runtime)
    x.repo.consume(x.campaign["id"], member, b)
    x.repo.consume(x.campaign["id"], member, b)
    with x.repo.transaction(readonly=True) as c:
        assert (
            c.execute(
                text("SELECT count(*) FROM assessment_campaign_consumers")
            ).scalar_one()
            == 1
        )
    other = x.s.freeze()
    with pytest.raises(CampaignError):
        x.repo.consume(other["id"], other["members"][0]["id"], b)
