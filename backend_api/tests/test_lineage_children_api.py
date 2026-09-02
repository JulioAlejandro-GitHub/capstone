from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes import runs as runs_routes
from app.schemas.lineage_children import TrainingLineageChildren
from app.services import lineage_children as service
from app.services import training_summaries


TRAINING_ID = UUID("11111111-1111-4111-8111-111111111111")
EVALUATION_ID = UUID("22222222-2222-4222-8222-222222222222")
EXPLAIN_ID = UUID("33333333-3333-4333-8333-333333333333")
VERSION_ID = UUID("44444444-4444-4444-8444-444444444444")
ARTIFACT_ID = UUID("55555555-5555-4555-8555-555555555555")


def child_row(run_type="evaluation", **overrides):
    evaluation = run_type == "evaluation"
    row = {
        "evaluation_count": 1 if evaluation else 0,
        "explainability_count": 0 if evaluation else 1,
        "run_id": EVALUATION_ID if evaluation else EXPLAIN_ID,
        "run_type": run_type,
        "status": "completed",
        "run_name": "evaluate:model" if evaluation else "explain:model",
        "model_name": "densenet121",
        "dataset_name": "malaria",
        "dataset_version_id": UUID("66666666-6666-4666-8666-666666666666"),
        "optimizer": "adamw",
        "started_at": datetime(2026, 8, 30, tzinfo=timezone.utc),
        "finished_at": datetime(2026, 8, 30, 0, 2, tzinfo=timezone.utc),
        "duration_seconds": 120.5,
        "parent_run_id": TRAINING_ID,
        "relationship_type": (
            "evaluates_checkpoint_from"
            if evaluation
            else "explains_checkpoint_from"
        ),
        "confidence": "explicit",
        "model_version_id": VERSION_ID,
        "checkpoint_artifact_id": ARTIFACT_ID,
        "accuracy": 0.94,
        "precision_parasitized": 0.93,
        "recall": 0.98,
        "recall_parasitized": 0.98,
        "sensitivity_parasitized": 0.98,
        "specificity": 0.91,
        "f2_score": 0.97,
        "f2_parasitized": 0.97,
        "auc": 0.99,
        "roc_auc_parasitized": 0.99,
        "pr_auc_parasitized": 0.98,
        "balanced_accuracy": 0.945,
        "threshold_used": 0.32,
        "tn": 100,
        "fp": 10,
        "fn": 2,
        "tp": 110,
        "confusion_matrix": [[100, 10], [2, 110]],
        "prediction_collapse_detected": False,
        "methods": ["gradcam", "lime"] if not evaluation else None,
        "fallback_method": None,
        "total_explanations": 6 if not evaluation else 0,
        "success_count": 5 if not evaluation else 0,
        "failed_count": 1 if not evaluation else 0,
        "created_at": datetime(2026, 8, 30, tzinfo=timezone.utc),
    }
    row.update(overrides)
    return row


class FakeResult:
    def __init__(self, *, first=None, rows=None):
        self._first = first
        self._rows = rows or []

    def mappings(self):
        return self

    def first(self):
        return self._first

    def all(self):
        return self._rows


class FakeConnection:
    def __init__(self, parent=None, rows=None):
        self.parent = parent
        self.rows = rows or []
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        if len(self.calls) == 1:
            return FakeResult(first=self.parent)
        return FakeResult(rows=self.rows)


def install_connection(monkeypatch, *, parent=None, rows=None):
    connection = FakeConnection(
        parent=parent or {"id": TRAINING_ID, "run_type": "training"},
        rows=rows,
    )
    opened = []

    @contextmanager
    def fake_read_only(datasource):
        opened.append(datasource)
        yield connection

    monkeypatch.setattr(service, "read_only_transaction", fake_read_only)
    return connection, opened


def test_existing_training_returns_typed_evaluation_and_explainability(monkeypatch):
    evaluation = child_row(
        "evaluation", evaluation_count=1, explainability_count=1
    )
    explanation = child_row(
        "explainability", evaluation_count=1, explainability_count=1
    )
    connection, opened = install_connection(
        monkeypatch, rows=[evaluation, explanation]
    )

    result = service.get_training_lineage_children(TRAINING_ID, "malaria", 100)

    assert result.training_run_id == TRAINING_ID
    assert result.evaluation_count == 1
    assert result.explainability_count == 1
    assert result.total_count == 2
    assert result.truncated is False
    assert [item.run_id for item in result.evaluations] == [EVALUATION_ID]
    assert result.evaluations[0].parent_run_id == TRAINING_ID
    assert result.evaluations[0].model_version_id == VERSION_ID
    assert result.evaluations[0].recall == 0.98
    assert [item.run_id for item in result.explainabilities] == [EXPLAIN_ID]
    assert result.explainabilities[0].methods == ["gradcam", "lime"]
    assert result.explainabilities[0].method == "multiple"
    assert result.explainabilities[0].total_explanations == 6
    assert opened == ["malaria"]
    assert len(connection.calls) == 2
    assert connection.calls[0][1] == {"training_run_id": TRAINING_ID}
    assert connection.calls[1][1] == {
        "training_run_id": TRAINING_ID,
        "limit": 100,
    }


def test_training_without_children_has_stable_empty_contract(monkeypatch):
    empty = {
        "evaluation_count": 0,
        "explainability_count": 0,
        "run_id": None,
    }
    install_connection(monkeypatch, rows=[empty])
    result = service.get_training_lineage_children(TRAINING_ID, "malaria", 100)
    assert result.evaluation_count == result.explainability_count == 0
    assert result.total_count == 0
    assert result.evaluations == []
    assert result.explainabilities == []
    assert result.truncated is False


@pytest.mark.parametrize(
    ("run_type", "evaluation_count", "explainability_count"),
    [("evaluation", 1, 0), ("explainability", 0, 1)],
)
def test_single_child_category_is_kept_separate(
    monkeypatch, run_type, evaluation_count, explainability_count
):
    row = child_row(
        run_type,
        evaluation_count=evaluation_count,
        explainability_count=explainability_count,
    )
    install_connection(monkeypatch, rows=[row])
    result = service.get_training_lineage_children(TRAINING_ID, "malaria", 100)
    assert len(result.evaluations) == evaluation_count
    assert len(result.explainabilities) == explainability_count
    assert result.total_count == 1


def test_limit_is_global_and_truncation_uses_total_counts(monkeypatch):
    row = child_row(
        "evaluation", evaluation_count=2, explainability_count=1
    )
    install_connection(monkeypatch, rows=[row])
    result = service.get_training_lineage_children(TRAINING_ID, "malaria", 1)
    assert result.total_count == 3
    assert len(result.evaluations) + len(result.explainabilities) == 1
    assert result.limit == 1
    assert result.truncated is True


def test_sql_only_loads_direct_matching_children_with_stable_global_order():
    sql = " ".join(service.LINEAGE_CHILDREN_SQL.lower().split())
    assert "lineage.parent_run_id = :training_run_id" in sql
    assert "child.id = lineage.child_run_id" in sql
    assert "lineage.relationship_type = 'evaluates_checkpoint_from'" in sql
    assert "child.run_type = 'evaluation'" in sql
    assert "lineage.relationship_type = 'explains_checkpoint_from'" in sql
    assert "child.run_type = 'explainability'" in sql
    assert "partition by lineage.child_run_id" in sql
    assert "count(distinct child_run_id) filter" in sql
    assert "order by started_at asc nulls last, created_at asc, run_id asc" in sql
    assert "limit :limit" in sql
    for forbidden_scope in (
        "with recursive",
        "unlinked",
        "ancestor",
        "grandchild",
        "metadata->>'parent_run_id'",
    ):
        assert forbidden_scope not in sql


def test_count_rules_match_training_summaries_contract():
    lazy_sql = " ".join(service.LINEAGE_CHILDREN_SQL.lower().split())
    summary_sql = " ".join(
        training_summaries.TRAINING_SUMMARIES_SQL.lower().split()
    )
    for relationship, run_type in (
        ("evaluates_checkpoint_from", "evaluation"),
        ("explains_checkpoint_from", "explainability"),
    ):
        assert relationship in lazy_sql and relationship in summary_sql
        assert f"run_type = '{run_type}'" in lazy_sql
        assert f"child.run_type = '{run_type}'" in summary_sql
    assert "count(distinct child_run_id) filter" in lazy_sql
    assert "count(distinct lineage.child_run_id) filter" in summary_sql


def test_no_n_plus_one_release_or_forbidden_dependencies():
    sql = service.LINEAGE_CHILDREN_SQL.lower()
    assert ":training_run_id" in sql and ":limit" in sql
    for forbidden in (
        "model_versions",
        "stage2_model_publications",
        "deployed_model_versions",
        "release_status",
        "available_to_publish",
        "productive_stage2",
        "not_available",
        "stage2.eligible",
        "advisory",
        "checkpoint_path",
    ):
        assert forbidden not in sql
    names = set(service.get_training_lineage_children.__code__.co_names)
    for forbidden in (
        "mutation_connection",
        "Stage2PublicationService",
        "Stage2ModelAvailabilityService",
        "ProductiveModelResolver",
        "tensorflow",
        "keras",
        "sha256",
        "open",
    ):
        assert forbidden not in names


def test_missing_run_and_non_training_run_are_distinguished(monkeypatch):
    missing, _ = install_connection(monkeypatch, parent={"sentinel": True})
    missing.parent = None
    with pytest.raises(service.TrainingRunNotFoundError):
        service.get_training_lineage_children(TRAINING_ID, "malaria", 100)
    assert len(missing.calls) == 1

    non_training, _ = install_connection(
        monkeypatch,
        parent={"id": EVALUATION_ID, "run_type": "evaluation"},
    )
    with pytest.raises(service.TrainingParentTypeError):
        service.get_training_lineage_children(EVALUATION_ID, "malaria", 100)
    assert len(non_training.calls) == 1


def test_direct_service_limit_is_validated_before_connection(monkeypatch):
    def forbidden_connection(_datasource):
        raise AssertionError("connection should not be opened")

    monkeypatch.setattr(service, "read_only_transaction", forbidden_connection)
    for value in (0, 501):
        with pytest.raises(ValueError, match="limit"):
            service.get_training_lineage_children(TRAINING_ID, "malaria", value)


def response_payload():
    return TrainingLineageChildren(
        training_run_id=TRAINING_ID,
        evaluation_count=0,
        explainability_count=0,
        total_count=0,
        evaluations=[],
        explainabilities=[],
        limit=100,
        truncated=False,
    )


def test_http_response_model_alias_route_and_parameter_validation(monkeypatch):
    calls = []

    def fake_service(training_run_id, datasource, limit):
        calls.append((training_run_id, datasource, limit))
        return response_payload()

    monkeypatch.setattr(runs_routes, "get_training_lineage_children", fake_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(f"/runs/{TRAINING_ID}/lineage-children")
        alias = client.get(f"/api/runs/{TRAINING_ID}/lineage-children")
        invalid_uuid = client.get("/runs/not-a-uuid/lineage-children")
        invalid_low = client.get(f"/runs/{TRAINING_ID}/lineage-children?limit=0")
        invalid_high = client.get(f"/runs/{TRAINING_ID}/lineage-children?limit=501")

    assert response.status_code == alias.status_code == 200
    assert response.json() == alias.json()
    assert len(calls) == 2
    assert calls[0] == (TRAINING_ID, "malaria", 100)
    assert invalid_uuid.status_code == 422
    assert invalid_low.status_code == invalid_high.status_code == 422

    paths = [route.path for route in runs_routes.router.routes]
    assert paths.index("/runs/{training_run_id}/lineage-children") < paths.index(
        "/runs/{run_id}"
    )
    operation = app.openapi()[
        "paths"
    ]["/runs/{training_run_id}/lineage-children"]["get"]
    schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema["$ref"].endswith("TrainingLineageChildren")
    assert {"200", "404", "409", "422"}.issubset(operation["responses"])
    assert "post" not in app.openapi()["paths"][
        "/runs/{training_run_id}/lineage-children"
    ]


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (service.TrainingRunNotFoundError("missing"), 404),
        (service.TrainingParentTypeError("not-training"), 409),
    ],
)
def test_http_parent_domain_errors(monkeypatch, error, status):
    def fail(**_kwargs):
        raise error

    monkeypatch.setattr(runs_routes, "get_training_lineage_children", fail)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(f"/runs/{TRAINING_ID}/lineage-children")
    assert response.status_code == status


def test_unknown_datasource_uses_existing_error_contract():
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            f"/runs/{TRAINING_ID}/lineage-children?datasource=unknown"
        )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
