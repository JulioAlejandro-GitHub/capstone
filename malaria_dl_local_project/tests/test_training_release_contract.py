from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from src.malaria_dl.persistence.training_release import (
    NotTrainingRunError,
    ProductiveStage2ConflictError,
    TrainingReleaseConflictError,
    TrainingReleaseDataIntegrityError,
    TrainingReleaseState,
    TrainingReleaseStatus,
    TrainingRunNotFoundError,
    get_training_release_state,
    list_training_release_states,
    set_training_release_status,
)


NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def release_row(run_id, status="available_to_publish", **overrides):
    row = {
        "training_run_id": run_id,
        "run_type": "training",
        "release_status": status,
        "release_updated_at": NOW,
        "release_changed_by": None,
        "release_reason": "initial",
    }
    row.update(overrides)
    return row


class Result:
    def __init__(self, *, one=None, rows=None, scalar=None):
        self.one = one
        self.rows = rows or []
        self.scalar = scalar

    def mappings(self):
        return self

    def one_or_none(self):
        return self.one

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.scalar


class Nested(AbstractContextManager):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class Connection:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []
        self.commit_calls = 0
        self.rollback_calls = 0

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params or {}))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def begin_nested(self):
        return Nested()

    def commit(self):
        self.commit_calls += 1

    def rollback(self):
        self.rollback_calls += 1


class EngineContext(AbstractContextManager):
    def __init__(self, connection):
        self.connection = connection
        self.committed = False
        self.rolled_back = False

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc, traceback):
        self.committed = exc_type is None
        self.rolled_back = exc_type is not None
        return False


class Engine:
    def __init__(self, connection):
        self.connection = connection
        self.context = None

    def connect(self):
        self.context = EngineContext(self.connection)
        return self.context

    def begin(self):
        self.context = EngineContext(self.connection)
        return self.context


def integrity_error(constraint):
    original = Exception("database constraint")
    original.diag = SimpleNamespace(constraint_name=constraint)
    return IntegrityError("statement", {}, original)


def test_enum_has_exact_serializable_values_and_strict_conversion():
    assert {item.value for item in TrainingReleaseStatus} == {
        "not_available",
        "available_to_publish",
        "productive_stage2",
    }
    assert TrainingReleaseStatus("available_to_publish") is TrainingReleaseStatus.AVAILABLE_TO_PUBLISH
    with pytest.raises(ValueError):
        TrainingReleaseStatus("available")


def test_state_is_immutable_and_rejects_unknown_null_or_naive_data():
    state = TrainingReleaseState(
        uuid4(), TrainingReleaseStatus.NOT_AVAILABLE, NOW, None, None
    )
    with pytest.raises((AttributeError, TypeError)):
        state.release_reason = "changed"
    with pytest.raises(TrainingReleaseDataIntegrityError):
        TrainingReleaseState(uuid4(), "unknown", NOW, None, None)
    with pytest.raises(TrainingReleaseDataIntegrityError):
        TrainingReleaseState(uuid4(), TrainingReleaseStatus.NOT_AVAILABLE, None, None, None)
    with pytest.raises(TrainingReleaseDataIntegrityError):
        TrainingReleaseState(
            uuid4(), TrainingReleaseStatus.NOT_AVAILABLE, datetime(2026, 1, 1), None, None
        )


def test_individual_read_uses_training_run_id_and_direct_run_columns():
    run_id = uuid4()
    connection = Connection([Result(one=release_row(run_id))])
    state = get_training_release_state(run_id, connection=connection)
    assert state.training_run_id == run_id
    assert state.release_status is TrainingReleaseStatus.AVAILABLE_TO_PUBLISH
    sql = connection.calls[0][0].lower()
    assert "from runs" in sql and "id =" in sql and "run_type = 'training'" in sql
    assert "release_changed_by" in sql and "for update" not in sql
    for forbidden in ("model_versions", "stage2_model_publications", "deployed_model_versions", "artifacts"):
        assert forbidden not in sql


def test_locked_read_uses_for_update_and_integrity_checks_null_state():
    run_id = uuid4()
    connection = Connection([Result(one=release_row(run_id))])
    get_training_release_state(run_id, connection=connection, for_update=True)
    assert "FOR UPDATE" in connection.calls[0][0]
    connection = Connection([Result(one=release_row(run_id, status=None))])
    with pytest.raises(TrainingReleaseDataIntegrityError):
        get_training_release_state(run_id, connection=connection)


def test_individual_read_distinguishes_missing_and_non_training_run():
    run_id = uuid4()
    missing = Connection([Result(one=None), Result(scalar=None)])
    with pytest.raises(TrainingRunNotFoundError):
        get_training_release_state(run_id, connection=missing)
    evaluation = Connection([Result(one=None), Result(scalar="evaluation")])
    with pytest.raises(NotTrainingRunError):
        get_training_release_state(run_id, connection=evaluation)


def test_bulk_read_deduplicates_and_uses_one_query():
    first, second = uuid4(), uuid4()
    connection = Connection(
        [Result(rows=[release_row(second), release_row(first, status="not_available")])]
    )
    states = list_training_release_states(
        [first, second, first], connection=connection
    )
    assert list(states) == [first, second]
    assert states[first].release_status is TrainingReleaseStatus.NOT_AVAILABLE
    assert len(connection.calls) == 1
    assert tuple(connection.calls[0][1]["training_run_ids"]) == (first, second)


def test_bulk_empty_does_not_query_and_missing_or_nontrain_are_explicit():
    empty = Connection([])
    assert dict(list_training_release_states([], connection=empty)) == {}
    assert empty.calls == []
    run_id = uuid4()
    with pytest.raises(TrainingRunNotFoundError):
        list_training_release_states([run_id], connection=Connection([Result(rows=[])]))
    with pytest.raises(NotTrainingRunError):
        list_training_release_states(
            [run_id],
            connection=Connection(
                [Result(rows=[release_row(run_id, run_type="evaluation", release_status=None, release_updated_at=None)])]
            ),
        )


def test_write_updates_all_release_fields_with_postgres_timestamp():
    run_id = uuid4()
    updated = release_row(
        run_id,
        status="not_available",
        release_changed_by="actor",
        release_reason="reason",
    )
    connection = Connection(
        [Result(one=release_row(run_id)), Result(one=updated)]
    )
    result = set_training_release_status(
        run_id,
        TrainingReleaseStatus.NOT_AVAILABLE,
        changed_by="actor",
        reason="reason",
        connection=connection,
    )
    assert result.changed and result.state.release_status is TrainingReleaseStatus.NOT_AVAILABLE
    sql = connection.calls[1][0]
    assert "UPDATE runs" in sql and "CURRENT_TIMESTAMP" in sql and "RETURNING" in sql
    assert "status =" not in sql.replace("release_status =", "")
    assert "model_version_id" not in sql
    assert connection.commit_calls == connection.rollback_calls == 0


def test_compare_and_set_success_conflict_and_idempotency():
    run_id = uuid4()
    connection = Connection(
        [
            Result(one=release_row(run_id)),
            Result(one=release_row(run_id, status="not_available")),
        ]
    )
    result = set_training_release_status(
        run_id,
        TrainingReleaseStatus.NOT_AVAILABLE,
        expected_current_status=TrainingReleaseStatus.AVAILABLE_TO_PUBLISH,
        changed_by=None,
        reason=None,
        connection=connection,
    )
    assert result.changed
    conflict = Connection([Result(one=release_row(run_id, status="not_available"))])
    with pytest.raises(TrainingReleaseConflictError) as caught:
        set_training_release_status(
            run_id,
            TrainingReleaseStatus.AVAILABLE_TO_PUBLISH,
            expected_current_status=TrainingReleaseStatus.PRODUCTIVE_STAGE2,
            changed_by=None,
            reason=None,
            connection=conflict,
        )
    assert caught.value.actual is TrainingReleaseStatus.NOT_AVAILABLE
    idempotent = Connection([Result(one=release_row(run_id))])
    same = set_training_release_status(
        run_id,
        TrainingReleaseStatus.AVAILABLE_TO_PUBLISH,
        changed_by="ignored",
        reason="ignored",
        connection=idempotent,
    )
    assert not same.changed and same.state.release_updated_at == NOW
    assert len(idempotent.calls) == 1


def test_compare_and_set_distinguishes_expected_null_from_any_current_status():
    run_id = uuid4()
    null_row = release_row(
        run_id,
        status=None,
        release_updated_at=None,
        release_changed_by=None,
        release_reason=None,
    )
    updated = release_row(
        run_id,
        status="available_to_publish",
        release_changed_by="actor",
        release_reason="initialized",
    )
    connection = Connection([Result(one=null_row), Result(one=updated)])

    result = set_training_release_status(
        run_id,
        TrainingReleaseStatus.AVAILABLE_TO_PUBLISH,
        expected_current_status=None,
        changed_by="actor",
        reason="initialized",
        connection=connection,
    )

    assert result.changed
    assert connection.calls[1][1]["current_status"] is None
    assert "IS NOT DISTINCT FROM" in connection.calls[1][0]


def test_own_transaction_commits_on_success_and_rolls_back_on_error():
    run_id = uuid4()
    success_connection = Connection([Result(one=release_row(run_id))])
    success_engine = Engine(success_connection)
    with patch(
        "src.malaria_dl.persistence.training_release.get_engine",
        return_value=success_engine,
    ):
        result = set_training_release_status(
            run_id,
            TrainingReleaseStatus.AVAILABLE_TO_PUBLISH,
            changed_by=None,
            reason=None,
        )
    assert not result.changed and success_engine.context.committed

    failure_connection = Connection(
        [Result(one=release_row(run_id, status="not_available"))]
    )
    failure_engine = Engine(failure_connection)
    with patch(
        "src.malaria_dl.persistence.training_release.get_engine",
        return_value=failure_engine,
    ), pytest.raises(TrainingReleaseConflictError):
        set_training_release_status(
            run_id,
            TrainingReleaseStatus.AVAILABLE_TO_PUBLISH,
            expected_current_status=TrainingReleaseStatus.PRODUCTIVE_STAGE2,
            changed_by=None,
            reason=None,
        )
    assert failure_engine.context.rolled_back


def test_unique_productive_violation_is_mapped_and_other_integrity_error_propagates():
    run_id = uuid4()
    productive = integrity_error("uq_runs_single_productive_stage2")
    connection = Connection([Result(one=release_row(run_id)), productive])
    with pytest.raises(ProductiveStage2ConflictError) as caught:
        set_training_release_status(
            run_id,
            TrainingReleaseStatus.PRODUCTIVE_STAGE2,
            changed_by=None,
            reason=None,
            connection=connection,
        )
    assert caught.value.__cause__ is productive

    other = integrity_error("some_other_constraint")
    connection = Connection([Result(one=release_row(run_id)), other])
    with pytest.raises(IntegrityError) as caught:
        set_training_release_status(
            run_id,
            TrainingReleaseStatus.PRODUCTIVE_STAGE2,
            changed_by=None,
            reason=None,
            connection=connection,
        )
    assert caught.value is other


def test_public_api_has_no_model_version_or_latest_version_resolution():
    source = (
        __import__("pathlib").Path(__file__).parents[1]
        / "src/malaria_dl/persistence/training_release.py"
    ).read_text(encoding="utf-8")
    assert "model_version_id" not in source
    assert "ORDER BY created_at DESC LIMIT 1" not in source
