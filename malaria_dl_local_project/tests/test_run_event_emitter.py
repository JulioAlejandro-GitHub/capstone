"""Scientific stream state machine; infrastructure appears only in adapter tests."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timezone
import json
from threading import Event
from uuid import uuid4

import pytest

from src.malaria_dl.execution.contracts import RunEvent, RunEventType as Kind, RunReporter
from src.malaria_dl.execution.emitter import (
    RunEventEmitter, PendingEventExists, NoPendingEvent, EventStreamClosed,
    EventEmissionInProgress, OperationalHeartbeatExcluded,
)


class Reporter(RunReporter):
    def __init__(self):
        self.events = []
        self.error = None

    def report(self, event):
        self.events.append(event)
        if self.error is not None:
            raise self.error


def emitter(reporter):
    return RunEventEmitter(reporter, run_id=uuid4(), attempt_id=uuid4())


def test_new_identity_contiguous_sequence_and_aware_clock():
    reporter = Reporter()
    stream = emitter(reporter)
    assert (stream.next_sequence, stream.pending, stream.closed) == (1, None, False)
    first = stream.emit(Kind.PHASE_STARTED, {'phase': 'base'})
    second = stream.emit(Kind.EPOCH_COMPLETED, {'epoch': 1})
    assert [first.sequence, second.sequence, stream.next_sequence] == [1, 2, 3]
    assert first.event_id != second.event_id
    assert first.run_id == second.run_id and first.attempt_id == second.attempt_id
    assert first.occurred_at.tzinfo is timezone.utc
    assert first.schema_version == 'run_event_v1'
    assert reporter.events == [first, second] and stream.pending is None


@pytest.mark.parametrize('error', [OSError('network'), RuntimeError('rejection'), KeyboardInterrupt()])
def test_failure_blocks_new_event_and_retry_retains_exact_object_and_bytes(error, monkeypatch):
    reporter = Reporter()
    reporter.error = error
    stream = emitter(reporter)
    payload = {'values': [1, 1.0, True, -0.0, '\x00', '\ud800']}
    with pytest.raises(type(error)) as caught:
        stream.emit(Kind.EPOCH_COMPLETED, payload)
    assert caught.value is error
    pending = stream.pending
    before = json.dumps(pending.to_dict())
    payload['values'].append('caller mutation')
    assert stream.next_sequence == 1 and not stream.closed
    def forbidden(): raise AssertionError('retry must not generate identity/time')
    monkeypatch.setattr('src.malaria_dl.execution.emitter.uuid4', forbidden)
    with pytest.raises(PendingEventExists):
        stream.emit(Kind.TRAINING_FAILED, {'cause': 'different event'})
    with pytest.raises(type(error)):
        stream.retry_pending()
    assert stream.pending is pending and stream.next_sequence == 1
    reporter.error = None
    assert stream.retry_pending() is pending
    assert all(event is pending for event in reporter.events)
    assert json.dumps(pending.to_dict()) == before
    assert stream.pending is None and stream.next_sequence == 2
    monkeypatch.undo()
    assert stream.emit(Kind.PHASE_COMPLETED, {}).sequence == 2


@pytest.mark.parametrize('terminal', [Kind.TRAINING_COMPLETED, Kind.TRAINING_FAILED])
def test_terminal_closes_only_after_confirmation(terminal):
    reporter = Reporter()
    reporter.error = OSError('lost terminal ACK')
    stream = emitter(reporter)
    with pytest.raises(OSError): stream.emit(terminal, {})
    assert not stream.closed and stream.next_sequence == 1 and stream.pending.event_type is terminal
    reporter.error = None
    stream.retry_pending()
    assert stream.closed and stream.next_sequence == 2 and stream.pending is None
    with pytest.raises(EventStreamClosed): stream.emit(Kind.EPOCH_COMPLETED, {})
    with pytest.raises(EventStreamClosed): stream.retry_pending()
    assert len(reporter.events) == 2


def test_evaluation_is_not_terminal_and_standalone_has_no_attempt():
    stream = RunEventEmitter(Reporter(), run_id=uuid4())
    assert stream.emit(Kind.EVALUATION_COMPLETED, {}).attempt_id is None
    assert not stream.closed
    assert stream.emit(Kind.TRAINING_COMPLETED, {}).sequence == 2


def test_heartbeat_is_excluded_without_consuming_identity_or_sequence(monkeypatch):
    def forbidden(): raise AssertionError('must reject before construction')
    monkeypatch.setattr('src.malaria_dl.execution.emitter.uuid4', forbidden)
    stream = emitter(Reporter())
    with pytest.raises(OperationalHeartbeatExcluded): stream.emit(Kind.HEARTBEAT, {})
    assert stream.pending is None and stream.next_sequence == 1


def test_retry_without_pending_is_explicit_error():
    with pytest.raises(NoPendingEvent): emitter(Reporter()).retry_pending()


@pytest.mark.parametrize('kind,payload', [('epoch_completed', {}), (Kind.EPOCH_COMPLETED, {'x': float('nan')}),
    (Kind.EPOCH_COMPLETED, {'x': object()}), (Kind.EPOCH_COMPLETED, [])])
def test_invalid_input_does_not_occupy_a_sequence(kind, payload):
    reporter = Reporter()
    stream = emitter(reporter)
    with pytest.raises((TypeError, ValueError)): stream.emit(kind, payload)
    assert not reporter.events and stream.next_sequence == 1 and stream.pending is None
    assert stream.emit(Kind.EPOCH_COMPLETED, {}).sequence == 1


@pytest.mark.parametrize('identity', [{'run_id': 'invalid'}, {'run_id': uuid4(), 'attempt_id': 'invalid'}])
def test_bad_stream_identity(identity):
    with pytest.raises(TypeError): RunEventEmitter(Reporter(), **identity)


def test_state_properties_cannot_be_reassigned():
    stream = emitter(Reporter())
    for key, value in [('next_sequence', 5), ('pending', None), ('closed', True)]:
        with pytest.raises(AttributeError): setattr(stream, key, value)


def test_overlapping_emit_or_retry_does_not_deliver_twice():
    entered, release = Event(), Event()
    class Slow(Reporter):
        def report(self, event):
            super().report(event)
            entered.set()
            assert release.wait(5)
    reporter = Slow()
    stream = emitter(reporter)
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(stream.emit, Kind.EPOCH_COMPLETED, {})
        assert entered.wait(5)
        try:
            with pytest.raises(EventEmissionInProgress): stream.emit(Kind.PHASE_COMPLETED, {})
            with pytest.raises(EventEmissionInProgress): stream.retry_pending()
            assert stream.next_sequence == 1 and stream.pending is reporter.events[0]
        finally: release.set()
        assert future.result(5).sequence == 1
    assert len(reporter.events) == 1 and stream.next_sequence == 2


@pytest.mark.parametrize('adapter', ['docker', 'http'])
def test_reporters_accept_duplicate_after_lost_ack_without_new_identity(adapter):
    from result_repository_fake import FakeResultRepository
    from test_result_service import context
    from src.malaria_dl.execution.reporters.docker import DockerRunReporter
    from src.malaria_dl.execution.reporters.http import HttpRunReporter
    from src.malaria_dl.local_execution.event_transport import EventRequest, RemoteExecutionIdentity
    from src.malaria_dl.results import ResultService
    from src.malaria_dl.results.errors import ResultPersistenceError
    ctx = context()
    repo = FakeResultRepository()
    repo.authorize(ctx)
    service = ResultService(repo)
    class Transport:
        def call_event(self, payload):
            request = EventRequest.from_dict(json.loads(json.dumps(payload)))
            receipt = service.accept_event(ctx, request.event)
            return dict(status=receipt.status.value, run_id=str(receipt.run_id),
                        event_id=str(receipt.event_id), sequence=receipt.sequence)
    reporter = DockerRunReporter(ctx, service) if adapter == 'docker' else HttpRunReporter(
        Transport(), RemoteExecutionIdentity(job_id=uuid4(), agent_id=uuid4()))
    stream = RunEventEmitter(reporter, run_id=ctx.run_id, attempt_id=ctx.attempt_id)
    repo.failure = 'ack'
    with pytest.raises(ResultPersistenceError): stream.emit(Kind.EPOCH_COMPLETED, {'n': 1.0})
    pending = stream.pending
    assert len(repo.events) == 1 and stream.next_sequence == 1
    repo.failure = None
    assert stream.retry_pending() is pending
    assert len(repo.events) == 1 and repo.append_count == 1
    assert stream.emit(Kind.TRAINING_COMPLETED, {}).sequence == 2
    assert stream.closed and len(repo.events) == 2


def test_new_instance_does_not_claim_to_recover_previous_state():
    reporter = Reporter()
    run = uuid4()
    old = RunEventEmitter(reporter, run_id=run)
    old.emit(Kind.EPOCH_COMPLETED, {})
    fresh = RunEventEmitter(reporter, run_id=run)
    assert fresh.next_sequence == 1  # Not safe to attach to this existing stream.
    assert fresh.pending is None and old.next_sequence == 2
