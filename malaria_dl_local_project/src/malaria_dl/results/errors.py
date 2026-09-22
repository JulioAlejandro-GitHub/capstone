"""Stable application errors, independent of persistence and transport."""


class ResultError(RuntimeError):
    code = "RESULT_ERROR"

    def __init__(self) -> None:
        super().__init__(self.code)


class RunIdentityMismatch(ResultError):
    code = "RUN_ID_MISMATCH"


class AttemptIdentityMismatch(ResultError):
    code = "ATTEMPT_ID_MISMATCH"


class UnsupportedEventSchema(ResultError):
    code = "UNSUPPORTED_EVENT_SCHEMA"


class InvalidEventType(ResultError):
    code = "INVALID_EVENT_TYPE"


class WriterNotAuthorized(ResultError):
    code = "WRITER_NOT_AUTHORIZED"


class EventIdConflict(ResultError):
    code = "EVENT_ID_CONFLICT"


class SequenceConflict(ResultError):
    code = "SEQUENCE_CONFLICT"


class SequenceGap(ResultError):
    code = "SEQUENCE_GAP"


class StaleSequence(ResultError):
    code = "STALE_SEQUENCE"


class ResultPersistenceError(ResultError):
    """Write/commit unconfirmed; never implies that a retry needs a new identity."""

    code = "RESULT_PERSISTENCE_ERROR"


class InvalidScientificResult(ResultError):
    code = "INVALID_SCIENTIFIC_RESULT"


class FinalEvaluationConflict(ResultError):
    code = "FINAL_EVALUATION_CONFLICT"
