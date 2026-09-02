from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest

from src.malaria_dl.governance.services.training_release_eligibility_service import (
    COMPLETED_EVALUATE_NOT_FOUND_REASON,
    ELIGIBILITY_ACTOR,
    ELIGIBLE_REASON,
    TRAINING_NOT_COMPLETED_REASON,
    reconcile_training_release_eligibility,
)
from src.malaria_dl.persistence.training_release import (
    NotTrainingRunError,
    TrainingReleaseConflictError,
    TrainingReleaseDataIntegrityError,
    TrainingReleaseState,
    TrainingReleaseStatus,
    TrainingReleaseWriteResult,
    TrainingRunNotFoundError,
)


NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
SETTER = (
    "src.malaria_dl.governance.services."
    "training_release_eligibility_service.set_training_release_status"
)
ENGINE = (
    "src.malaria_dl.governance.services."
    "training_release_eligibility_service.get_engine"
)


def locked_row(
    run_id,
    release="available_to_publish",
    training="completed",
    **overrides,
):
    row = {
        "training_run_id": run_id,
        "training_status": training,
        "release_status": release,
        "release_updated_at": NOW,
        "release_changed_by": "initial-actor",
        "release_reason": "initial-reason",
    }
    row.update(overrides)
    return row


def state(run_id, status, actor=ELIGIBILITY_ACTOR, reason=ELIGIBLE_REASON):
    return TrainingReleaseState(run_id, status, NOW, actor, reason)


class Result:
    def __init__(self, *, one=None, scalar=None):
        self.value = one
        self.scalar = scalar

    def mappings(self):
        return self

    def one_or_none(self):
        return self.value

    def one(self):
        return self.value

    def scalar_one_or_none(self):
        return self.scalar


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

    def begin(self):
        self.context = EngineContext(self.connection)
        return self.context


def eligibility(training_completed, evaluate_exists):
    return Result(
        one={
            "training_completed": training_completed,
            "completed_evaluate_exists": evaluate_exists,
        }
    )


def write_result(run_id, status, reason):
    return TrainingReleaseWriteResult(
        state(run_id, status, reason=reason), changed=True
    )


def test_completed_train_and_evaluate_becomes_available():
    run_id = uuid4()
    connection = Connection(
        [Result(one=locked_row(run_id, release="not_available")), eligibility(True, True)]
    )
    with patch(SETTER, return_value=write_result(run_id, TrainingReleaseStatus.AVAILABLE_TO_PUBLISH, ELIGIBLE_REASON)) as setter:
        decision = reconcile_training_release_eligibility(run_id, connection=connection)
    assert decision.eligible and decision.changed
    assert decision.target_status is TrainingReleaseStatus.AVAILABLE_TO_PUBLISH
    assert setter.call_args.kwargs == {
        "changed_by": ELIGIBILITY_ACTOR,
        "reason": ELIGIBLE_REASON,
        "expected_current_status": TrainingReleaseStatus.NOT_AVAILABLE,
        "connection": connection,
    }


@pytest.mark.parametrize(
    ("training_completed", "evaluate_exists", "reason"),
    [
        (False, False, TRAINING_NOT_COMPLETED_REASON),
        (False, True, TRAINING_NOT_COMPLETED_REASON),
        (True, False, COMPLETED_EVALUATE_NOT_FOUND_REASON),
    ],
)
def test_ineligible_cases_become_not_available_with_reason_precedence(
    training_completed, evaluate_exists, reason
):
    run_id = uuid4()
    connection = Connection(
        [Result(one=locked_row(run_id)), eligibility(training_completed, evaluate_exists)]
    )
    with patch(SETTER, return_value=write_result(run_id, TrainingReleaseStatus.NOT_AVAILABLE, reason)) as setter:
        decision = reconcile_training_release_eligibility(run_id, connection=connection)
    assert not decision.eligible
    assert decision.target_status is TrainingReleaseStatus.NOT_AVAILABLE
    assert setter.call_args.kwargs["reason"] == reason


def test_running_failed_wrong_relation_and_indirect_lineage_are_excluded_by_sql():
    run_id = uuid4()
    for _scenario in ("running", "failed", "wrong_relation", "indirect"):
        connection = Connection(
            [Result(one=locked_row(run_id, release="not_available")), eligibility(True, False)]
        )
        decision = reconcile_training_release_eligibility(run_id, connection=connection)
        assert not decision.eligible and not decision.changed
        sql = connection.calls[1][0]
        assert "evaluation.status = 'completed'" in sql
        assert "evaluation.run_type = 'evaluation'" in sql
        assert "lineage.parent_run_id = training.id" in sql
        assert "evaluation.id = lineage.child_run_id" in sql
        assert "lineage.relationship_type = 'evaluates_checkpoint_from'" in sql
        assert "EXISTS" in sql and "WITH RECURSIVE" not in sql


def test_multiple_completed_evaluates_are_accepted_by_exists_without_counting():
    run_id = uuid4()
    connection = Connection(
        [Result(one=locked_row(run_id, release="not_available")), eligibility(True, True)]
    )
    with patch(SETTER, return_value=write_result(run_id, TrainingReleaseStatus.AVAILABLE_TO_PUBLISH, ELIGIBLE_REASON)):
        decision = reconcile_training_release_eligibility(run_id, connection=connection)
    assert decision.completed_evaluate_exists and decision.eligible
    assert "COUNT(" not in connection.calls[1][0]


def test_available_eligible_and_not_available_ineligible_are_idempotent():
    run_id = uuid4()
    for release, train_done, evaluate_done in (
        ("available_to_publish", True, True),
        ("not_available", True, False),
    ):
        connection = Connection(
            [Result(one=locked_row(run_id, release=release)), eligibility(train_done, evaluate_done)]
        )
        with patch(SETTER) as setter:
            decision = reconcile_training_release_eligibility(run_id, connection=connection)
        assert not decision.changed
        assert decision.final_state.release_updated_at == NOW
        assert decision.final_state.release_changed_by == "initial-actor"
        assert decision.final_state.release_reason == "initial-reason"
        setter.assert_not_called()


def test_productive_is_protected_without_eligibility_query_or_write():
    run_id = uuid4()
    connection = Connection(
        [Result(one=locked_row(run_id, release="productive_stage2"))]
    )
    with patch(SETTER) as setter:
        decision = reconcile_training_release_eligibility(run_id, connection=connection)
    assert decision.productive_protected and not decision.changed
    assert decision.target_status is TrainingReleaseStatus.PRODUCTIVE_STAGE2
    assert decision.final_state.release_updated_at == NOW
    assert decision.final_state.release_changed_by == "initial-actor"
    assert decision.final_state.release_reason == "initial-reason"
    assert len(connection.calls) == 1
    setter.assert_not_called()


@pytest.mark.parametrize(
    ("training_completed", "evaluate_exists", "target", "reason"),
    [
        (True, True, TrainingReleaseStatus.AVAILABLE_TO_PUBLISH, ELIGIBLE_REASON),
        (False, False, TrainingReleaseStatus.NOT_AVAILABLE, TRAINING_NOT_COMPLETED_REASON),
    ],
)
def test_null_state_initializes_with_explicit_null_compare_and_set(
    training_completed, evaluate_exists, target, reason
):
    run_id = uuid4()
    connection = Connection(
        [
            Result(
                one=locked_row(
                    run_id,
                    release=None,
                    release_updated_at=None,
                    release_changed_by=None,
                    release_reason=None,
                )
            ),
            eligibility(training_completed, evaluate_exists),
        ]
    )
    with patch(SETTER, return_value=write_result(run_id, target, reason)) as setter:
        decision = reconcile_training_release_eligibility(run_id, connection=connection)
    assert decision.previous_status is None and decision.changed
    assert setter.call_args.kwargs["expected_current_status"] is None
    assert setter.call_args.kwargs["changed_by"] == ELIGIBILITY_ACTOR


def test_compare_and_set_conflict_propagates_and_external_connection_is_unmanaged():
    run_id = uuid4()
    connection = Connection(
        [Result(one=locked_row(run_id, release="not_available")), eligibility(True, True)]
    )
    conflict = TrainingReleaseConflictError(
        run_id,
        TrainingReleaseStatus.NOT_AVAILABLE,
        TrainingReleaseStatus.PRODUCTIVE_STAGE2,
    )
    with patch(SETTER, side_effect=conflict), pytest.raises(TrainingReleaseConflictError):
        reconcile_training_release_eligibility(run_id, connection=connection)
    assert connection.commit_calls == connection.rollback_calls == 0


def test_own_transaction_commits_success_and_rolls_back_error():
    run_id = uuid4()
    connection = Connection(
        [Result(one=locked_row(run_id)), eligibility(True, True)]
    )
    engine = Engine(connection)
    with patch(ENGINE, return_value=engine):
        reconcile_training_release_eligibility(run_id)
    assert engine.context.committed

    error_connection = Connection([RuntimeError("technical SQL failure")])
    error_engine = Engine(error_connection)
    with patch(ENGINE, return_value=error_engine), pytest.raises(RuntimeError):
        reconcile_training_release_eligibility(run_id)
    assert error_engine.context.rolled_back


def test_missing_nontraining_unknown_and_invalid_input_are_explicit():
    run_id = uuid4()
    with pytest.raises(TrainingRunNotFoundError):
        reconcile_training_release_eligibility(
            run_id, connection=Connection([Result(one=None), Result(scalar=None)])
        )
    with pytest.raises(NotTrainingRunError):
        reconcile_training_release_eligibility(
            run_id,
            connection=Connection([Result(one=None), Result(scalar="evaluation")]),
        )
    with pytest.raises(TrainingReleaseDataIntegrityError):
        reconcile_training_release_eligibility(
            run_id,
            connection=Connection([Result(one=locked_row(run_id, release="unknown"))]),
        )
    with patch(ENGINE) as engine, pytest.raises(ValueError):
        reconcile_training_release_eligibility("not-a-uuid")
    engine.assert_not_called()


def test_service_has_no_global_loop_versions_artifacts_or_temporal_selection():
    source = (
        __import__("pathlib").Path(__file__).parents[1]
        / "src/malaria_dl/governance/services/training_release_eligibility_service.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "model_version_id",
        "model_versions",
        "artifacts",
        "stage2_model_publications",
        "deployed_model_versions",
        "checkpoint_path",
        "ORDER BY",
        "created_at",
        "LIMIT 1",
    ):
        assert forbidden not in source
    assert "for training" not in source.lower()
