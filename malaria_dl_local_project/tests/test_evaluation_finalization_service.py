from __future__ import annotations

import json
from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest

from src.malaria_dl.evaluation.evaluation_finalization_service import (
    EvaluationFinalizationConflictError,
    EvaluationFinalizationDataIntegrityError,
    EvaluationRunNotFoundError,
    InvalidEvaluationTransitionError,
    NotEvaluationRunError,
    fail_evaluation_run,
    finalize_evaluation_run,
)


STARTED_AT = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
COMPLETED_AT = STARTED_AT + timedelta(seconds=19)
ENGINE = (
    "src.malaria_dl.evaluation."
    "evaluation_finalization_service.get_engine"
)


class Result:
    def __init__(self, value=None):
        self.value = value

    def mappings(self):
        return self

    def one_or_none(self):
        return self.value


class Connection:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []
        self.commit_calls = 0
        self.rollback_calls = 0
        self.close_calls = 0

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params or {}))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def commit(self):
        self.commit_calls += 1

    def rollback(self):
        self.rollback_calls += 1

    def close(self):
        self.close_calls += 1


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

    def begin(self):
        self.context = EngineContext(self.connection)
        return self.context


def run_row(run_id, *, run_type="evaluation", status="started", **overrides):
    row = {
        "evaluation_run_id": run_id,
        "run_type": run_type,
        "status": status,
        "started_at": STARTED_AT,
        "completed_at": None,
        "duration_seconds": None,
        "metadata": {"original": True},
    }
    row.update(overrides)
    return row


def completed_row(run_id, *, duration=19):
    return {
        "evaluation_run_id": run_id,
        "status": "completed",
        "completed_at": COMPLETED_AT,
        "duration_seconds": duration,
    }


def failed_row(run_id):
    return {
        "evaluation_run_id": run_id,
        "status": "failed",
        "failed_at": COMPLETED_AT,
    }


def test_started_to_completed_uses_lock_and_strict_compare_and_set_once():
    run_id = uuid4()
    connection = Connection(
        [Result(run_row(run_id)), Result(completed_row(run_id))]
    )

    result = finalize_evaluation_run(
        run_id,
        completed_at=COMPLETED_AT,
        duration_seconds=19,
        summary={"status_detail": "evaluation completed"},
        connection=connection,
    )

    assert result.changed
    assert result.previous_status == "started"
    assert result.final_status == "completed"
    assert result.completed_at == COMPLETED_AT
    assert result.duration_seconds == 19
    assert len(connection.calls) == 2
    lock_sql, _ = connection.calls[0]
    update_sql, update_params = connection.calls[1]
    assert "FOR UPDATE" in lock_sql
    assert "run_type = 'evaluation'" in update_sql
    assert "status = 'started'" in update_sql
    assert "RETURNING" in update_sql
    assert json.loads(update_params["summary"]) == {
        "status_detail": "evaluation completed"
    }


def test_completed_retry_is_read_only_and_preserves_terminal_fields():
    run_id = uuid4()
    preserved_at = COMPLETED_AT - timedelta(seconds=3)
    connection = Connection(
        [
            Result(
                run_row(
                    run_id,
                    status="completed",
                    completed_at=preserved_at,
                    duration_seconds=16,
                    metadata={"preserved": True},
                )
            )
        ]
    )

    result = finalize_evaluation_run(
        run_id,
        completed_at=COMPLETED_AT,
        duration_seconds=999,
        summary={"must_not_be_written": True},
        connection=connection,
    )

    assert not result.changed
    assert result.previous_status == "completed"
    assert result.completed_at == preserved_at
    assert result.duration_seconds == 16
    assert len(connection.calls) == 1
    assert "UPDATE runs" not in connection.calls[0][0]


def test_missing_run_has_explicit_domain_error():
    run_id = uuid4()
    with pytest.raises(EvaluationRunNotFoundError):
        finalize_evaluation_run(run_id, connection=Connection([Result()]))


def test_non_evaluation_run_is_distinct_from_missing_and_never_updated():
    run_id = uuid4()
    connection = Connection(
        [Result(run_row(run_id, run_type="training"))]
    )
    with pytest.raises(NotEvaluationRunError):
        finalize_evaluation_run(run_id, connection=connection)
    assert len(connection.calls) == 1


def test_failed_to_completed_is_rejected_without_update():
    run_id = uuid4()
    connection = Connection([Result(run_row(run_id, status="failed"))])
    with pytest.raises(InvalidEvaluationTransitionError) as captured:
        finalize_evaluation_run(run_id, connection=connection)
    assert captured.value.previous_status == "failed"
    assert captured.value.target_status == "completed"
    assert len(connection.calls) == 1


@pytest.mark.parametrize("status", ["running", "pending", "corrupt", None])
def test_unknown_status_is_data_integrity_error(status):
    run_id = uuid4()
    connection = Connection([Result(run_row(run_id, status=status))])
    with pytest.raises(EvaluationFinalizationDataIntegrityError):
        finalize_evaluation_run(run_id, connection=connection)
    assert len(connection.calls) == 1


def test_zero_row_compare_and_set_is_explicit_conflict():
    run_id = uuid4()
    connection = Connection(
        [Result(run_row(run_id)), Result(), Result({"status": "failed"})]
    )
    with pytest.raises(EvaluationFinalizationConflictError) as captured:
        finalize_evaluation_run(run_id, connection=connection)
    assert captured.value.expected_status == "started"
    assert captured.value.observed_status == "failed"
    assert len(connection.calls) == 3


def test_external_connection_is_reused_without_transaction_management():
    run_id = uuid4()
    connection = Connection(
        [Result(run_row(run_id)), Result(completed_row(run_id))]
    )
    with patch(ENGINE) as get_engine:
        result = finalize_evaluation_run(run_id, connection=connection)
    assert result.changed
    get_engine.assert_not_called()
    assert connection.commit_calls == 0
    assert connection.rollback_calls == 0
    assert connection.close_calls == 0


def test_owned_transaction_commits_only_after_success():
    run_id = uuid4()
    connection = Connection(
        [Result(run_row(run_id)), Result(completed_row(run_id))]
    )
    engine = Engine(connection)
    with patch(ENGINE, return_value=engine):
        result = finalize_evaluation_run(run_id)
    assert result.changed
    assert engine.context.committed
    assert not engine.context.rolled_back


def test_owned_transaction_rolls_back_and_propagates_sql_error():
    connection = Connection([RuntimeError("unexpected SQL failure")])
    engine = Engine(connection)
    with patch(ENGINE, return_value=engine):
        with pytest.raises(RuntimeError, match="unexpected SQL failure"):
            finalize_evaluation_run(uuid4())
    assert not engine.context.committed
    assert engine.context.rolled_back


def test_started_at_and_terminal_values_must_be_consistent():
    run_id = uuid4()
    missing_start = Connection(
        [Result(run_row(run_id, started_at=None))]
    )
    with pytest.raises(EvaluationFinalizationDataIntegrityError):
        finalize_evaluation_run(run_id, connection=missing_start)

    missing_finished = Connection(
        [Result(run_row(run_id, status="completed", completed_at=None))]
    )
    with pytest.raises(EvaluationFinalizationDataIntegrityError):
        finalize_evaluation_run(run_id, connection=missing_finished)


def test_failure_cas_marks_only_started_evaluation():
    run_id = uuid4()
    connection = Connection(
        [Result(run_row(run_id)), Result(failed_row(run_id))]
    )
    result = fail_evaluation_run(run_id, connection=connection)
    assert result.changed
    assert result.previous_status == "started"
    assert result.final_status == "failed"
    assert "status = 'started'" in connection.calls[1][0]


def test_failure_handler_never_changes_completed_to_failed():
    run_id = uuid4()
    connection = Connection(
        [
            Result(
                run_row(
                    run_id,
                    status="completed",
                    completed_at=COMPLETED_AT,
                    duration_seconds=19,
                )
            )
        ]
    )
    result = fail_evaluation_run(run_id, connection=connection)
    assert not result.changed
    assert result.final_status == "completed"
    assert len(connection.calls) == 1
