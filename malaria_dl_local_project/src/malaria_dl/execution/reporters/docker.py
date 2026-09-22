"""Deliver prebuilt events to the results application boundary."""
from ..contracts import ExecutionContext, RunEvent, RunReporter
from ...results import EventAcceptance, EventAcceptanceStatus, ResultService


class DockerRunReporter(RunReporter):
    def __init__(self, context: ExecutionContext, result_service: ResultService) -> None:
        self._context = context
        self._result_service = result_service

    def report(self, event: RunEvent) -> None:
        acceptance = self._result_service.accept_event(self._context, event)
        if not isinstance(acceptance, EventAcceptance) or acceptance.status not in (
            EventAcceptanceStatus.ACCEPTED, EventAcceptanceStatus.DUPLICATE_ACCEPTED,
        ):
            raise RuntimeError("UNEXPECTED_EVENT_ACCEPTANCE")
