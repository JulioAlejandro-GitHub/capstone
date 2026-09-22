"""Application decisions made inside an authorized atomic repository scope."""
from ..execution.contracts import (
    RUN_EVENT_SCHEMA_VERSION, ExecutionContext, RunEvent, RunEventType,
)
from .errors import (
    AttemptIdentityMismatch, EventIdConflict, InvalidEventType, RunIdentityMismatch,
    SequenceConflict, SequenceGap, StaleSequence, UnsupportedEventSchema,
)
from .identity import canonical_event
from .models import EventAcceptance, EventAcceptanceStatus
from .repository import ResultRepository


class ResultService:
    def __init__(self, repository: ResultRepository) -> None:
        self._repository = repository

    def accept_event(self, context: ExecutionContext, event: RunEvent) -> EventAcceptance:
        if not isinstance(context, ExecutionContext) or not isinstance(event, RunEvent):
            raise TypeError("ExecutionContext and RunEvent are required")
        if context.run_id != event.run_id:
            raise RunIdentityMismatch()
        # None is valid only on both sides: standalone never invents an attempt.
        if context.attempt_id != event.attempt_id:
            raise AttemptIdentityMismatch()
        if event.schema_version != RUN_EVENT_SCHEMA_VERSION:
            raise UnsupportedEventSchema()
        if not isinstance(event.event_type, RunEventType):
            raise InvalidEventType()

        with self._repository.acceptance_scope(context, event) as scope:
            state = scope.state
            if state.existing_event is not None:
                if canonical_event(state.existing_event) != canonical_event(event):
                    raise EventIdConflict()
                status = EventAcceptanceStatus.DUPLICATE_ACCEPTED
            else:
                if state.sequence_event is not None:
                    raise SequenceConflict()
                expected = state.last_sequence + 1
                if event.sequence > expected:
                    raise SequenceGap()
                if event.sequence < expected:
                    raise StaleSequence()
                scope.append()
                status = EventAcceptanceStatus.ACCEPTED
            acceptance = EventAcceptance(
                status=status, run_id=event.run_id,
                event_id=event.event_id, sequence=event.sequence,
            )
        # In particular, a failing __exit__/commit cannot return ACCEPTED.
        return acceptance
