"""Reporter delegation, preserving the approved None-returning port."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.malaria_dl.execution.contracts import RunReporter
from src.malaria_dl.execution.reporters.docker import DockerRunReporter
from src.malaria_dl.results import EventAcceptance, EventAcceptanceStatus, ResultService
from src.malaria_dl.results.errors import (
    EventIdConflict, SequenceConflict, SequenceGap, WriterNotAuthorized, ResultPersistenceError,
)
from test_result_service import context, event


@pytest.mark.parametrize('status', list(EventAcceptanceStatus))
def test_exact_delegation_and_none_result(status):
    ctx, item = context(), event()
    service = Mock(spec=ResultService)
    service.accept_event.return_value = EventAcceptance(
        status=status, run_id=item.run_id, event_id=item.event_id, sequence=item.sequence)
    reporter = DockerRunReporter(ctx, service)
    assert isinstance(reporter, RunReporter)
    before = item.to_dict()
    assert reporter.report(item) is None
    service.accept_event.assert_called_once_with(ctx, item)
    args = service.accept_event.call_args.args
    assert args[0] is ctx and args[1] is item
    assert item.to_dict() == before


def test_retry_is_delegated_each_time_without_local_transformation():
    ctx, item = context(), event()
    service = Mock(spec=ResultService)
    service.accept_event.side_effect = [EventAcceptance(
        status=status, run_id=item.run_id, event_id=item.event_id, sequence=item.sequence)
        for status in EventAcceptanceStatus]
    reporter = DockerRunReporter(ctx, service)
    assert reporter.report(item) is None
    assert reporter.report(item) is None
    assert service.accept_event.call_count == 2
    assert all(call.args[0] is ctx and call.args[1] is item for call in service.accept_event.call_args_list)


@pytest.mark.parametrize('error', [EventIdConflict(), SequenceConflict(), SequenceGap(),
                                 WriterNotAuthorized(), ResultPersistenceError(), OSError('synthetic')])
def test_errors_propagate_unchanged_without_retries(error):
    service = Mock(spec=ResultService)
    service.accept_event.side_effect = error
    with pytest.raises(type(error)) as caught:
        DockerRunReporter(context(), service).report(event())
    assert caught.value is error
    assert service.accept_event.call_count == 1


@pytest.mark.parametrize('receipt', [None, False, SimpleNamespace(status='accepted')])
def test_invalid_acceptance_is_not_success(receipt):
    service = Mock(spec=ResultService)
    service.accept_event.return_value = receipt
    with pytest.raises(RuntimeError, match='UNEXPECTED_EVENT_ACCEPTANCE'):
        DockerRunReporter(context(), service).report(event())


def test_composition_is_lazy_and_builds_real_classes():
    from src.malaria_dl.execution.composition import build_docker_run_reporter
    from src.malaria_dl.persistence.result_repository import PostgresResultRepository
    factory = Mock(side_effect=AssertionError('must not connect during construction'))
    reporter = build_docker_run_reporter(context(), execution_token=context().owner, engine_factory=factory)
    assert isinstance(reporter, DockerRunReporter)
    assert isinstance(reporter._result_service, ResultService)
    assert isinstance(reporter._result_service._repository, PostgresResultRepository)
    factory.assert_not_called()
