"""E10.2 behavior with a test-only atomic repository; no runtime or storage IO."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import UUID

import pytest

from src.malaria_dl.execution.contracts import ExecutionContext, ExecutionMode, RunEvent, RunEventType
from src.malaria_dl.results import EventAcceptance, EventAcceptanceStatus, ResultRepository, ResultService
from src.malaria_dl.results.errors import (
    AttemptIdentityMismatch, EventIdConflict, InvalidEventType, ResultPersistenceError,
    RunIdentityMismatch, SequenceConflict, SequenceGap, StaleSequence,
    UnsupportedEventSchema, WriterNotAuthorized,
)
from src.malaria_dl.results.identity import canonical_event
from result_repository_fake import FakeResultRepository


def context(**changes):
    fields = dict(run_id=UUID(int=1), owner=UUID(int=2), dataset_version_id=UUID(int=3),
                  execution_mode=ExecutionMode.DOCKER, model_id="custom_cnn", adapter_version="1")
    return ExecutionContext(**(fields | changes))


def event(**changes):
    fields = dict(event_id=UUID(int=4), run_id=UUID(int=1), sequence=1,
                  event_type=RunEventType.EPOCH_COMPLETED,
                  occurred_at=datetime(2026, 9, 22, 13, tzinfo=timezone.utc),
                  payload={"metrics": {"loss": 0.25}, "labels": [1, False, None, "α"]})
    return RunEvent(**(fields | changes))


@pytest.fixture
def setup():
    repo = FakeResultRepository()
    ctx = context()
    repo.authorize(ctx)
    return ctx, repo, ResultService(repo)


@pytest.mark.parametrize("mode", list(ExecutionMode))
@pytest.mark.parametrize("kind", [kind for kind in RunEventType if kind is not RunEventType.EVALUATION_COMPLETED])
def test_new_event_accepted_once_without_interpreting_payload(mode, kind):
    ctx = context(execution_mode=mode)
    repo = FakeResultRepository()
    repo.authorize(ctx)
    item = event(event_type=kind, payload={"opaque": ["no scientific schema"]})
    result = ResultService(repo).accept_event(ctx, item)
    assert result == EventAcceptance(status=EventAcceptanceStatus.ACCEPTED,
                                    run_id=ctx.run_id, event_id=item.event_id, sequence=1)
    assert repo.events == (item,)
    assert repo.events[0] is item
    assert repo.append_count == 1


def test_run_mismatch_precedes_repository(setup):
    ctx, repo, service = setup
    with pytest.raises(RunIdentityMismatch, match="RUN_ID_MISMATCH"):
        service.accept_event(ctx, event(run_id=UUID(int=99)))
    assert repo.scope_calls == 0 and repo.events == ()


@pytest.mark.parametrize("ctx_attempt,event_attempt", [
    (UUID(int=8), None), (None, UUID(int=8)), (UUID(int=8), UUID(int=9)),
])
def test_attempt_mismatch_including_one_sided_none(setup, ctx_attempt, event_attempt):
    ctx, repo, service = setup
    with pytest.raises(AttemptIdentityMismatch, match="ATTEMPT_ID_MISMATCH"):
        service.accept_event(replace(ctx, attempt_id=ctx_attempt), event(attempt_id=event_attempt))
    assert repo.scope_calls == 0


@pytest.mark.parametrize("attempt", [None, UUID(int=8)])
def test_matching_attempt_or_standalone(attempt):
    ctx = context(attempt_id=attempt)
    repo = FakeResultRepository()
    repo.authorize(ctx)
    assert ResultService(repo).accept_event(ctx, event(attempt_id=attempt)).status is EventAcceptanceStatus.ACCEPTED


@pytest.mark.parametrize("field,value,error", [
    ("schema_version", "run_event_v2", UnsupportedEventSchema),
    ("event_type", "epoch_completed", InvalidEventType),
    ("event_type", "unknown", InvalidEventType),
])
def test_defensive_version_and_enum_validation(setup, field, value, error):
    ctx, repo, service = setup
    item = event()
    # E10.1 normally rejects these during construction. Fault injection tests
    # the application boundary without changing the approved contract.
    object.__setattr__(item, field, value)
    with pytest.raises(error) as caught:
        service.accept_event(ctx, item)
    assert str(caught.value) == caught.value.code
    assert repo.scope_calls == 0


@pytest.mark.parametrize("ctx,item", [(None, event()), (context(), {}), ({}, event())])
def test_requires_typed_contracts(setup, ctx, item):
    _, repo, service = setup
    with pytest.raises(TypeError):
        service.accept_event(ctx, item)
    assert repo.scope_calls == 0


@pytest.mark.parametrize("changes", [
    {"owner": UUID(int=90)}, {"dataset_version_id": UUID(int=90)},
    {"model_id": "different"}, {"adapter_version": "different"},
    {"campaign_id": UUID(int=90)}, {"member_id": UUID(int=90)},
    {"configuration_hash": "a" * 64}, {"contract_hash": "b" * 64},
])
def test_authorization_uses_authoritative_context(setup, changes):
    ctx, repo, service = setup
    with pytest.raises(WriterNotAuthorized):
        service.accept_event(replace(ctx, **changes), event())
    assert repo.events == ()


def test_revoked_writer_cannot_append_or_get_duplicate_ack(setup):
    ctx, repo, service = setup
    service.accept_event(ctx, event())
    repo.revoke(ctx.run_id)
    for item in (event(), event(event_id=UUID(int=5), sequence=2)):
        with pytest.raises(WriterNotAuthorized, match="WRITER_NOT_AUTHORIZED"):
            service.accept_event(ctx, item)
    assert repo.append_count == 1


def test_retry_exact_and_older_retry_do_not_write_again(setup):
    ctx, repo, service = setup
    first = event()
    service.accept_event(ctx, first)
    service.accept_event(ctx, event(event_id=UUID(int=5), sequence=2))
    receipt = service.accept_event(ctx, RunEvent.from_dict(first.to_dict()))
    assert receipt.status is EventAcceptanceStatus.DUPLICATE_ACCEPTED
    assert receipt == service.accept_event(ctx, first)
    assert receipt.sequence == 1 and receipt.event_id == first.event_id
    assert repo.append_count == 2 and len(repo.events) == 2


def test_authorized_owner_rotation_does_not_change_event_identity(setup):
    ctx, repo, service = setup
    service.accept_event(ctx, event())
    rotated = replace(ctx, owner=UUID(int=91))
    repo.authorize(rotated)
    assert service.accept_event(rotated, event()).status is EventAcceptanceStatus.DUPLICATE_ACCEPTED
    with pytest.raises(WriterNotAuthorized):
        service.accept_event(ctx, event())
    assert repo.append_count == 1


def test_canonical_retry_ignores_nested_key_order_and_original_timezone(setup):
    ctx, repo, service = setup
    first = event(payload={"b": {"β": 1, "a": 2}, "a": [1, 2]})
    retry = event(payload={"a": [1, 2], "b": {"a": 2, "β": 1}},
                  occurred_at=datetime(2026, 9, 22, 10, tzinfo=timezone(timedelta(hours=-3))))
    assert canonical_event(first) == canonical_event(retry)
    service.accept_event(ctx, first)
    assert service.accept_event(ctx, retry).status is EventAcceptanceStatus.DUPLICATE_ACCEPTED
    assert repo.append_count == 1


@pytest.mark.parametrize("changes", [
    {"payload": {"different": True}}, {"sequence": 2},
    {"occurred_at": datetime(2026, 9, 22, 13, 0, 1, tzinfo=timezone.utc)},
    {"event_type": RunEventType.PHASE_COMPLETED},
])
def test_same_id_changed_content_conflicts_before_sequence(setup, changes):
    ctx, repo, service = setup
    service.accept_event(ctx, event())
    with pytest.raises(EventIdConflict, match="EVENT_ID_CONFLICT"):
        service.accept_event(ctx, event(**changes))
    assert repo.append_count == 1


@pytest.mark.parametrize("left,right", [(1, 1.0), (1, True), (0.0, -0.0), ([1, 2], [2, 1]), ("é", "e\u0301")])
def test_exact_identity_preserves_json_types_sign_order_and_unicode(setup, left, right):
    ctx, repo, service = setup
    service.accept_event(ctx, event(payload={"value": left}))
    with pytest.raises(EventIdConflict):
        service.accept_event(ctx, event(payload={"value": right}))
    assert repo.append_count == 1


@pytest.mark.parametrize("changes", [{"run_id": UUID(int=99)}, {"attempt_id": UUID(int=99)}])
def test_global_event_id_cannot_be_rebound_to_run_or_attempt(setup, changes):
    ctx, repo, service = setup
    service.accept_event(ctx, event())
    other = replace(ctx, **changes)
    repo.authorize(other)
    with pytest.raises(EventIdConflict):
        service.accept_event(other, event(**changes))
    assert repo.append_count == 1


def test_sequence_collision_has_precedence_over_stale(setup):
    ctx, repo, service = setup
    service.accept_event(ctx, event())
    with pytest.raises(SequenceConflict, match="SEQUENCE_CONFLICT"):
        service.accept_event(ctx, event(event_id=UUID(int=5)))
    assert repo.append_count == 1


def test_gap_is_rejected_then_safe_retry_after_missing_event(setup):
    ctx, repo, service = setup
    second = event(event_id=UUID(int=5), sequence=2)
    with pytest.raises(SequenceGap, match="SEQUENCE_GAP"):
        service.accept_event(ctx, second)
    assert repo.append_count == 0
    service.accept_event(ctx, event())
    service.accept_event(ctx, second)
    assert [item.sequence for item in repo.events] == [1, 2]


def test_stale_unknown_event_fails_closed_on_incomplete_history(setup):
    ctx, repo, service = setup
    repo.set_watermark(ctx.run_id, 3)
    with pytest.raises(StaleSequence, match="STALE_SEQUENCE"):
        service.accept_event(ctx, event(sequence=2))
    assert repo.append_count == 0


def test_independent_runs_start_at_one(setup):
    ctx, repo, service = setup
    other = replace(ctx, run_id=UUID(int=99))
    repo.authorize(other)
    service.accept_event(ctx, event())
    service.accept_event(other, event(run_id=other.run_id, event_id=UUID(int=5)))
    assert [item.sequence for item in repo.events] == [1, 1]


@pytest.mark.parametrize("point", ["enter", "read", "append", "commit"])
def test_repository_failure_never_returns_acceptance_or_leaves_partial_write(setup, point):
    ctx, repo, service = setup
    repo.failure = point
    with pytest.raises(ResultPersistenceError):
        service.accept_event(ctx, event())
    assert repo.events == () and repo.append_count == 0
    repo.failure = None
    assert service.accept_event(ctx, event()).status is EventAcceptanceStatus.ACCEPTED


def test_unknown_repository_exception_is_not_converted_to_success(setup, monkeypatch):
    ctx, repo, service = setup
    def fail(*args):
        raise OSError("synthetic storage failure")
    monkeypatch.setattr(repo, "acceptance_scope", fail)
    with pytest.raises(OSError):
        service.accept_event(ctx, event())
    assert repo.events == ()


def test_lost_commit_ack_retry_resolves_without_second_write(setup):
    ctx, repo, service = setup
    repo.failure = "ack"
    with pytest.raises(ResultPersistenceError):
        service.accept_event(ctx, event())
    assert repo.append_count == 1
    repo.failure = None
    assert service.accept_event(ctx, event()).status is EventAcceptanceStatus.DUPLICATE_ACCEPTED
    assert repo.append_count == 1


def test_duplicate_scope_exit_failure_is_not_reported_successfully(setup):
    ctx, repo, service = setup
    service.accept_event(ctx, event())
    repo.failure = "commit"
    with pytest.raises(ResultPersistenceError):
        service.accept_event(ctx, event())
    assert repo.append_count == 1


@pytest.mark.parametrize("case", ["retry", "sequence_collision", "id_collision", "cross_run_id"])
def test_concurrent_acceptance_is_serialized(setup, case):
    ctx, repo, service = setup
    first = event()
    second_context = ctx
    second = first
    error = None
    if case == "sequence_collision":
        second = replace(first, event_id=UUID(int=5))
        error = SequenceConflict
    elif case == "id_collision":
        second = replace(first, payload={"changed": True})
        error = EventIdConflict
    elif case == "cross_run_id":
        second_context = replace(ctx, run_id=UUID(int=99))
        repo.authorize(second_context)
        second = replace(first, run_id=second_context.run_id)
        error = EventIdConflict
    barrier = Barrier(2)
    def submit(pair):
        barrier.wait(timeout=5)
        try:
            return service.accept_event(*pair).status
        except (SequenceConflict, EventIdConflict) as caught:
            return type(caught)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, [(ctx, first), (second_context, second)], timeout=10))
    assert results.count(EventAcceptanceStatus.ACCEPTED) == 1
    assert results.count(error or EventAcceptanceStatus.DUPLICATE_ACCEPTED) == 1
    assert repo.append_count == 1 and len(repo.events) == 1


def test_existing_event_simulation_and_deterministic_immutable_receipt(setup):
    ctx, repo, service = setup
    repo.seed(event())
    receipt = service.accept_event(ctx, event())
    assert receipt == service.accept_event(ctx, event())
    assert receipt.status is EventAcceptanceStatus.DUPLICATE_ACCEPTED
    with pytest.raises(FrozenInstanceError):
        receipt.sequence = 2
    assert not hasattr(receipt, "__dict__")
    assert repo.append_count == 0


def test_repository_is_abstract():
    with pytest.raises(TypeError):
        ResultRepository()
