from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import db
from app.main import app
from app.routes import runs as runs_routes
from app.schemas.training_summaries import (
    TrainingReleaseStatus,
    TrainingSummary,
    TrainingSummaryCollection,
)
from app.services import training_summaries as service


TRAINING_ID = "11111111-1111-4111-8111-111111111111"
DATASET_VERSION_ID = "22222222-2222-4222-8222-222222222222"


def summary_row(**overrides):
    row = {
        "run_id": TRAINING_ID,
        "run_type": "training",
        "status": "completed",
        "release_status": "available_to_publish",
        "release_updated_at": datetime(2026, 8, 30, tzinfo=timezone.utc),
        "release_changed_by": "release-operator",
        "release_reason": "validated evaluation lineage",
        "evaluation_count": 0,
        "explainability_count": 0,
        "run_name": "train:densenet121",
        "model_name": "densenet121",
        "dataset_name": "malaria",
        "dataset_version_id": DATASET_VERSION_ID,
        "optimizer": "adamw",
        "command": "python -m src.train --model densenet121",
        "started_at": datetime(2026, 8, 29, tzinfo=timezone.utc),
        "finished_at": datetime(2026, 8, 29, 0, 5, tzinfo=timezone.utc),
        "duration_seconds": Decimal("300.5"),
        "recall": Decimal("0.98"),
        "recall_parasitized": Decimal("0.97"),
        "specificity": Decimal("0.91"),
        "f2_score": Decimal("0.96"),
        "f2_parasitized": Decimal("0.95"),
        "auc": Decimal("0.99"),
        "roc_auc_parasitized": Decimal("0.985"),
        "tn": 100,
        "fp": 10,
        "fn": 2,
        "tp": 110,
        "confusion_matrix": [[100, 10], [2, 110]],
        "prediction_collapse_detected": False,
    }
    row.update(overrides)
    return row


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        return FakeResult(self.rows)


@pytest.mark.parametrize("value", [item.value for item in TrainingReleaseStatus])
def test_schema_accepts_each_canonical_release_status(value):
    item = TrainingSummary.model_validate(summary_row(release_status=value))
    assert item.release_status.value == value


def test_schema_rejects_unknown_release_status():
    with pytest.raises(ValidationError):
        TrainingSummary.model_validate(summary_row(release_status="available"))


def test_schema_preserves_nullable_release_status_and_release_metadata():
    item = TrainingSummary.model_validate(
        summary_row(
            release_status=None,
            release_updated_at=None,
            release_changed_by=None,
            release_reason=None,
        )
    )
    assert item.release_status is None
    assert item.release_updated_at is None
    assert item.release_changed_by is None
    assert item.release_reason is None


def test_service_maps_release_fields_counts_and_metrics_without_transformation(monkeypatch):
    row = summary_row(evaluation_count=2, explainability_count=3)
    connection = FakeConnection([row])
    opened = []

    @contextmanager
    def fake_read_only(datasource):
        opened.append(datasource)
        yield connection

    monkeypatch.setattr(service, "read_only_transaction", fake_read_only)
    result = service.list_training_summaries("malaria", 25)

    assert opened == ["malaria"]
    assert result.count == 1
    assert result.limit == 25
    item = result.items[0]
    assert item.release_status.value == row["release_status"]
    assert item.release_updated_at == row["release_updated_at"]
    assert item.release_changed_by == row["release_changed_by"]
    assert item.release_reason == row["release_reason"]
    assert item.evaluation_count == 2
    assert item.explainability_count == 3
    assert item.recall == float(row["recall"])
    assert len(connection.calls) == 1
    assert connection.calls[0][1] == {"limit": 25}


def test_unknown_persisted_status_fails_with_explicit_contract_error(monkeypatch):
    connection = FakeConnection([summary_row(release_status="production")])

    @contextmanager
    def fake_read_only(_datasource):
        yield connection

    monkeypatch.setattr(service, "read_only_transaction", fake_read_only)
    with pytest.raises(service.TrainingSummaryContractError) as exc_info:
        service.list_training_summaries("malaria", 100)
    assert isinstance(exc_info.value.__cause__, ValidationError)


def test_service_limit_is_bounded_without_opening_a_connection(monkeypatch):
    def forbidden_connection(_datasource):
        raise AssertionError("database connection should not be opened")

    monkeypatch.setattr(service, "read_only_transaction", forbidden_connection)
    for value in (0, 501):
        with pytest.raises(ValueError, match="limit"):
            service.list_training_summaries("malaria", value)


def test_sql_is_scoped_deterministic_distinct_and_release_is_not_recomputed():
    sql = service.TRAINING_SUMMARIES_SQL
    normalized = " ".join(sql.lower().split())
    assert "where training.run_type = 'training'" in normalized
    assert (
        "training.started_at desc nulls last, training.created_at desc, training.id"
        in normalized
    )
    assert "limit :limit" in normalized
    for column in (
        "selected.release_status",
        "selected.release_updated_at",
        "selected.release_changed_by",
        "selected.release_reason",
    ):
        assert column in normalized
    assert "count(distinct lineage.child_run_id) filter" in normalized
    assert "evaluates_checkpoint_from" in normalized
    assert "explains_checkpoint_from" in normalized
    assert "coalesce(children.evaluation_count, 0)" in normalized
    assert "coalesce(children.explainability_count, 0)" in normalized
    assert "json_agg(" not in normalized
    assert "array_agg(" not in normalized
    assert "lineage.child_run_id as" not in normalized
    assert "case" not in normalized.split("selected.release_status", 1)[0]


def test_listing_has_no_governance_artifact_or_runtime_dependencies():
    source = service.TRAINING_SUMMARIES_SQL.lower()
    for forbidden in (
        "model_versions",
        "stage2_model_publications",
        "deployed_model_versions",
        "artifacts",
        "stage2.eligible",
        "exists",
        "advisory",
    ):
        assert forbidden not in source

    names = set(service.list_training_summaries.__code__.co_names)
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


def test_read_only_helper_sets_postgresql_mode_timeouts_and_rolls_back(monkeypatch):
    statements = []

    class Transaction:
        is_active = True

        def rollback(self):
            statements.append("ROLLBACK")

    class Connection:
        def begin(self):
            return Transaction()

        def execute(self, statement):
            statements.append(str(statement))

    class ConnectContext:
        def __enter__(self):
            return Connection()

        def __exit__(self, *_args):
            return False

    class Engine:
        def connect(self):
            return ConnectContext()

    monkeypatch.setattr(db, "get_engine", lambda _datasource: Engine())
    with db.read_only_transaction("malaria") as connection:
        assert isinstance(connection, Connection)

    assert statements == [
        "SET TRANSACTION READ ONLY",
        f"SET LOCAL statement_timeout = '{db.READ_ONLY_STATEMENT_TIMEOUT_MS}ms'",
        f"SET LOCAL lock_timeout = '{db.READ_ONLY_LOCK_TIMEOUT_MS}ms'",
        "ROLLBACK",
    ]


def test_http_contract_openapi_static_order_and_validation(monkeypatch):
    payload = TrainingSummaryCollection(
        items=[TrainingSummary.model_validate(summary_row())],
        count=1,
        limit=100,
    )
    calls = []

    def fake_listing(datasource, limit):
        calls.append((datasource, limit))
        return payload

    monkeypatch.setattr(runs_routes, "list_training_summaries", fake_listing)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/runs/training-summaries")
        too_small = client.get("/runs/training-summaries?limit=0")
        too_large = client.get("/runs/training-summaries?limit=501")

    assert response.status_code == 200
    assert calls == [("malaria", 100)]
    body = response.json()
    assert set(body) == {"items", "count", "limit"}
    assert body["count"] == 1
    item = body["items"][0]
    for field in (
        "release_status",
        "release_updated_at",
        "release_changed_by",
        "release_reason",
        "evaluation_count",
        "explainability_count",
    ):
        assert field in item
    for absent in (
        "evaluations",
        "explainability",
        "eligible",
        "stage2_status",
        "production_state",
        "is_stage2_production",
        "can_release",
    ):
        assert absent not in item
    assert too_small.status_code == 422
    assert too_large.status_code == 422

    paths = [route.path for route in runs_routes.router.routes]
    assert paths.index("/runs/training-summaries") < paths.index("/runs/{run_id}")
    assert paths.index("/api/runs/training-summaries") < paths.index("/api/runs/{run_id}")
    operation = app.openapi()["paths"]["/runs/training-summaries"]["get"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("TrainingSummaryCollection")
    assert "post" not in app.openapi()["paths"]["/runs/training-summaries"]


def test_unknown_datasource_uses_existing_error_contract():
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/runs/training-summaries?datasource=unknown")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_uuid_and_timestamp_serialization_is_standard():
    item = TrainingSummary.model_validate(summary_row())
    dumped = item.model_dump(mode="json")
    assert UUID(dumped["run_id"]) == UUID(TRAINING_ID)
    assert dumped["release_updated_at"].endswith("Z")
