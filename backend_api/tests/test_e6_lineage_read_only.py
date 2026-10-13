"""Execute production queries against SELECT-only fixtures and existing E6 evidence.

JSON CTEs shadow tables for synthetic scenarios. No INSERT, temp tables, schema
changes, or scientific executions are needed, even for retry/deduplication cases.
"""

import json
from contextlib import contextmanager
from uuid import UUID

import httpx
import pytest
from sqlalchemy import text

from app.db import read_only_transaction
from app.main import app
from app.services import lineage_children, training_summaries

pytestmark = pytest.mark.requires_docker_postgres

TRAIN = "11111111-1111-4111-8111-111111111111"
LEGACY = "22222222-2222-4222-8222-222222222222"
EXPLAIN = "33333333-3333-4333-8333-333333333333"
IDENTITY = "44444444-4444-4444-8444-444444444444"
STAMP = "2026-10-08T12:00:00+00:00"
REAL_TRAIN = "bbbd5b60-afaa-4034-a504-a60ed642aafe"
REAL_ATTEMPT = "dded6222-12ae-407a-82c6-601e265e3f7d"
TABLES = (
    "runs", "run_lineage", "assessment_identities", "assessment_attempts",
    "evaluations", "run_metrics", "run_clinical_metrics", "confusion_matrices",
    "explainability_results", "models", "datasets", "run_configurations", "assessment_artifacts",
    "train_execution_sessions", "train_execution_records",
)
METRICS = dict(count=2, tn=1, fp=0, fn=0, tp=1, accuracy=1., precision=1.,
               recall=1., specificity=1., f2=1., confusion_matrix=[[1, 0], [0, 1]],
               definition="binary_counts_rates_v1")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def attempt_id(ordinal: int) -> str:
    return str(UUID(int=ordinal + 100))


def fixtures(states: tuple[str, ...], legacy: bool, explain: bool, projected: bool) -> dict:
    values = {name: [] for name in TABLES}
    values["runs"].append(dict(id=TRAIN, run_type="training", status="completed",
                               started_at=STAMP, created_at=STAMP, parameters={}))
    for child, kind, relationship, enabled in (
        (LEGACY, "evaluation", "evaluates_checkpoint_from", legacy),
        (EXPLAIN, "explainability", "explains_checkpoint_from", explain),
    ):
        if enabled:
            values["runs"].append(dict(id=child, run_type=kind, status="completed",
                                       started_at=STAMP, created_at=STAMP))
            values["run_lineage"].append(dict(id=child, parent_run_id=TRAIN,
                child_run_id=child, relationship_type=relationship,
                confidence="explicit", created_at=STAMP))
    if states:
        values["assessment_identities"].append(dict(id=IDENTITY,
            training_run_id=TRAIN, kind="evaluate", created_at=STAMP,
            identity=dict(split="val", purpose="development")))
    for ordinal, state in enumerate(states, 1):
        values["assessment_attempts"].append(dict(id=attempt_id(ordinal),
            identity_id=IDENTITY, ordinal=ordinal, state=state, started_at=STAMP,
            finished_at=None if state == "active" else STAMP,
            verification=dict(count=2, sha256="a" * 64, metrics=METRICS) if state == "verified" else None))
    if projected:
        values["evaluations"].append(dict(id=LEGACY, run_id=LEGACY,
            training_run_id=TRAIN, source_kind="assessment",
            source_assessment_attempt_id=attempt_id(1)))
    return values


def install_fixtures(monkeypatch: pytest.MonkeyPatch, values: dict) -> None:
    prefix = ", ".join(
        f"{table} AS (SELECT * FROM jsonb_populate_recordset(NULL::public.{table}, CAST(:fixture_{table} AS jsonb)))"
        for table in TABLES
    )
    fixture_params = {f"fixture_{table}": json.dumps(rows) for table, rows in values.items()}

    @contextmanager
    def connection(_datasource: str):
        with read_only_transaction("malaria") as db:
            assert db.execute(text("SHOW transaction_read_only")).scalar_one() == "on"

            class SelectFixtures:
                def execute(self, statement, params=None):
                    sql = str(statement).strip()
                    sql = "WITH " + prefix + (", " + sql[5:] if sql.startswith("WITH ") else " " + sql)
                    return db.execute(text(sql), {**fixture_params, **(params or {})})

            yield SelectFixtures()

    monkeypatch.setattr(lineage_children, "read_only_transaction", connection)
    monkeypatch.setattr(training_summaries, "read_only_transaction", connection)
    from app.repositories import assessments
    monkeypatch.setattr(assessments, "read_only_transaction", connection)


@pytest.mark.parametrize("states,legacy,explain,projected,expected,selected", [
    ((), False, False, False, 0, None),
    ((), True, False, False, 1, None),
    (("verified",), False, False, False, 1, 1),
    (("verified",), True, True, False, 2, 1),
    (("failed", "verified"), False, False, False, 1, 2),
    (("verified", "failed"), False, False, False, 1, 1),
    (("failed", "active"), False, False, False, 1, 2),
    (("failed", "interrupted"), False, True, False, 1, 2),
    (("failed",), False, False, False, 1, 1),
    (("verified",), True, True, True, 1, 1),
    (("failed", "verified"), True, False, True, 1, 2),
])
def test_selection_counts_pagination_and_legacy_compatibility(
    monkeypatch, states, legacy, explain, projected, expected, selected,
) -> None:
    expected = len(states) + int(legacy and not projected)
    install_fixtures(monkeypatch, fixtures(states, legacy, explain, projected))
    summary = training_summaries.list_training_summaries("malaria", 100).items[0]
    result = lineage_children.get_training_lineage_children(UUID(TRAIN), "malaria", 100)
    assert summary.evaluation_count == result.evaluation_count == len(result.evaluations) == expected
    assert summary.explainability_count == result.explainability_count == len(result.explainabilities) == int(explain)
    assert result.total_count == expected + int(explain)
    e6 = [item for item in result.evaluations if item.source_kind == "assessment_e6"]
    if selected:
        assert len(e6) == len(states)
        assert {str(item.attempt_id) for item in e6} == {attempt_id(n) for n in range(1,len(states)+1)}
        item = next(item for item in e6 if str(item.attempt_id) == attempt_id(selected))
        assert str(item.attempt_id) == attempt_id(selected)
        assert str(item.identity_id) == IDENTITY
        assert str(item.training_run_id) == TRAIN
        assert item.state == states[selected - 1]
        assert "run_id" not in item.model_dump()
        assert (item.verification is not None) == (item.state == "verified")
        if item.verification:
            assert item.verification["metrics"] == METRICS
    if legacy and not projected:
        assert any(item.source_kind == "run" and str(item.run_id) == LEGACY for item in result.evaluations)
    if explain:
        assert str(result.explainabilities[0].run_id) == EXPLAIN
        assert result.explainabilities[0].source_kind == "run"
    limited = lineage_children.get_training_lineage_children(UUID(TRAIN), "malaria", 1)
    assert limited.total_count == result.total_count
    assert len(limited.evaluations) + len(limited.explainabilities) == min(1, result.total_count)
    assert limited.truncated == (result.total_count > 1)


def test_scope_distinct_identities_and_explain_assessments(monkeypatch) -> None:
    values = fixtures(("verified",), False, False, False)
    for offset, kind, train in ((1, "evaluate", TRAIN), (2, "explain", TRAIN), (3, "evaluate", LEGACY)):
        identity = str(UUID(int=500 + offset))
        values["assessment_identities"].append({**values["assessment_identities"][0],
            "id": identity, "kind": kind, "training_run_id": train})
        values["assessment_attempts"].append({**values["assessment_attempts"][0],
            "id": str(UUID(int=600 + offset)), "identity_id": identity})
    install_fixtures(monkeypatch, values)
    result = lineage_children.get_training_lineage_children(UUID(TRAIN), "malaria", 100)
    assert len(result.evaluations) == result.evaluation_count == 2
    assert result.explainability_count == len(result.explainabilities) == 1
    assert result.explainabilities[0].source_kind == "assessment_explain_e6"
    assert training_summaries.list_training_summaries("malaria", 100).items[0].evaluation_count == 2


@pytest.mark.anyio
async def test_http_discriminated_mixed_response(monkeypatch) -> None:
    install_fixtures(monkeypatch, fixtures(("verified",), True, True, False))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/runs/{TRAIN}/lineage-children")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["evaluation_count"] == 2
    assert {item["source_kind"] for item in payload["evaluations"]} == {"run", "assessment_e6"}
    assert payload["explainabilities"][0]["run_id"] == EXPLAIN


def scientific_fingerprint() -> dict:
    with read_only_transaction("malaria") as db:
        return {table: db.execute(text(
            f"SELECT md5(coalesce(string_agg(to_jsonb(t)::text, '' ORDER BY to_jsonb(t)::text), '')) FROM public.{table} t"
        )).scalar_one() for table in (
            "runs", "run_lineage", "evaluations", "assessment_identities",
            "assessment_attempts", "assessment_results", "assessment_artifacts",
        )}



def explain_fixture(values, index, states=("verified",)):
    identity = str(UUID(int=1000 + index))
    values["assessment_identities"].append(dict(id=identity, training_run_id=TRAIN,
        kind="explain", created_at=STAMP, identity=dict(split="val", purpose="development",
        explanation=dict(method="gradcam"), model=dict(model_version_id=TRAIN, checkpoint_artifact_id=LEGACY))))
    for ordinal, state in enumerate(states, 1):
        aid = str(UUID(int=10000 + index * 10 + ordinal))
        values["assessment_attempts"].append(dict(id=aid, identity_id=identity, ordinal=ordinal,
            state=state, started_at=STAMP, finished_at=None if state == "active" else STAMP,
            verification=dict(count=2693, sha256="a" * 64, artifacts_hash="b" * 64) if state == "verified" else None))
    return identity


@pytest.mark.anyio
async def test_fourteen_trainings_one_evaluate_two_explain_and_detail(monkeypatch):
    values = fixtures(("verified",), False, False, False)
    for index in range(13):
        values["runs"].append({**values["runs"][0], "id": str(UUID(int=2000 + index))})
    for index in range(2):
        explain_fixture(values, index)
        aid = values["assessment_attempts"][-1]["id"]
        values["assessment_artifacts"].append(dict(attempt_id=aid, sample_id=TRAIN,
            role="overlay", artifact_id=str(UUID(int=3000 + index)), payload=dict(
            artifact_id=str(UUID(int=3000 + index)), role="overlay", path="outputs/db02a-missing.png",
            sha256="c" * 64, bytes=100)))
    before = scientific_fingerprint()
    install_fixtures(monkeypatch, values)
    summaries = training_summaries.list_training_summaries("malaria", 100)
    assert len(summaries.items) == 14
    for summary in summaries.items:
        children = lineage_children.get_training_lineage_children(summary.run_id, "malaria", 100)
        assert summary.evaluation_count == children.evaluation_count == len(children.evaluations)
        assert summary.explainability_count == children.explainability_count == len(children.explainabilities)
        assert (children.evaluation_count, children.explainability_count) == ((1, 2) if str(summary.run_id) == TRAIN else (0, 0))
    children = lineage_children.get_training_lineage_children(UUID(TRAIN), "malaria", 100)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        for item in children.explainabilities:
            assert item.method == "gradcam" and item.result_count == 2693
            assert "run_id" not in item.model_dump()
            detail = await client.get(f"/assessments/{item.attempt_id}")
            artifacts = await client.get(item.artifact_reference)
            assert detail.status_code == artifacts.status_code == 200
            assert detail.json()["identity"]["explanation"]["method"] == "gradcam"
            assert detail.json()["id"] == str(item.attempt_id)
            assert artifacts.json()["items"][0]["path"] == "outputs/db02a-missing.png"
    assert scientific_fingerprint() == before


@pytest.mark.parametrize("states,expected", [(("failed", "active"), "active"), (("verified", "failed"), "verified"), (("failed",), "failed")])
def test_explain_attempt_selection(monkeypatch, states, expected):
    values = fixtures((), False, False, False)
    explain_fixture(values, 0, states)
    install_fixtures(monkeypatch, values)
    children = lineage_children.get_training_lineage_children(UUID(TRAIN), "malaria", 100)
    assert children.explainability_count == len(children.explainabilities) == len(states)
    child = next(item for item in children.explainabilities if item.state == expected)
    assert child.state == expected
    assert (child.verification is not None) == (expected == "verified")
    assert (child.result_count is not None) == (expected == "verified")


def test_more_than_one_hundred_children_pages(monkeypatch):
    values = fixtures(("verified",), False, False, False)
    for index in range(105):
        explain_fixture(values, index, ("verified", "failed"))
    install_fixtures(monkeypatch, values)
    first = lineage_children.get_training_lineage_children(UUID(TRAIN), "malaria", 100)
    second = lineage_children.get_training_lineage_children(UUID(TRAIN), "malaria", 100, offset=100)
    assert first.total_count == second.total_count == 211
    assert first.explainability_count == second.explainability_count == 210
    assert len(first.evaluations) + len(first.explainabilities) == 100
    assert len(second.evaluations) + len(second.explainabilities) == 100
    third = lineage_children.get_training_lineage_children(UUID(TRAIN), "malaria", 100, offset=200)
    assert len(third.evaluations) + len(third.explainabilities) == 11
    assert first.truncated and second.truncated and not third.truncated
    ids = [x.attempt_id for page in (first, second, third) for x in (*page.evaluations, *page.explainabilities)]
    assert len(set(ids)) == 211
    assert "assessment_results" not in lineage_children.LINEAGE_CHILDREN_SQL
    assert "assessment_artifacts" not in lineage_children.LINEAGE_CHILDREN_SQL


@pytest.mark.anyio
async def test_test_history_list_selects_exact_attempt_without_mixing_metrics(monkeypatch):
    values = fixtures(('verified',),False,False,False)
    values['assessment_identities'][0]['identity'].update(split='test',purpose='final')
    second_identity,second_attempt = str(UUID(int=5001)),str(UUID(int=5002))
    values['assessment_identities'].append({**values['assessment_identities'][0],'id':second_identity})
    values['assessment_attempts'].append({**values['assessment_attempts'][0],
        'id':second_attempt,'identity_id':second_identity,
        'verification':{'count':2,'sha256':'b'*64,'metrics':{**METRICS,'recall':.5}}})
    install_fixtures(monkeypatch,values)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        response = await client.get('/assessments',params={'training_run_id':TRAIN})
        assert response.status_code == 200
        listed = response.json()['items']
        assert {x['attempt_id'] for x in listed} == {attempt_id(1),second_attempt}
        assert all(x['split'] == 'test' and x['purpose'] == 'final' for x in listed)
        first = (await client.get('/assessments/'+attempt_id(1))).json()
        second = (await client.get('/assessments/'+second_attempt)).json()
        assert first['verification']['metrics']['recall'] == 1
        assert second['verification']['metrics']['recall'] == .5
