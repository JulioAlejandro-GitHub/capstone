"""E10 HTTP wire contract and failures; no server or storage dependencies."""
from dataclasses import dataclass
from uuid import UUID

from ..execution.contracts import RunEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class RemoteExecutionIdentity:
    job_id: UUID
    agent_id: UUID

    def __post_init__(self):
        if not isinstance(self.job_id, UUID) or not isinstance(self.agent_id, UUID):
            raise TypeError('job_id and agent_id must be UUID')


@dataclass(frozen=True, slots=True, kw_only=True)
class EventRequest:
    identity: RemoteExecutionIdentity
    event: RunEvent

    def to_dict(self):
        return {'job_id': str(self.identity.job_id), 'agent_id': str(self.identity.agent_id),
                'event': self.event.to_dict()}

    @classmethod
    def from_dict(cls, value):
        if type(value) is not dict or value.keys() != {'job_id', 'agent_id', 'event'}:
            raise ValueError('exact E10 request fields required')
        if type(value['job_id']) is not str or type(value['agent_id']) is not str:
            raise TypeError('UUID strings required')
        return cls(identity=RemoteExecutionIdentity(job_id=UUID(value['job_id']),
                   agent_id=UUID(value['agent_id'])), event=RunEvent.from_dict(value['event']))


class EventDeliveryError(RuntimeError):
    """Delivery did not confirm acceptance; retain the original event."""


class EventRejected(EventDeliveryError):
    def __init__(self, status: int):
        self.status = status
        super().__init__('EVENT_REJECTED_' + str(status))


class EventServerFailure(EventDeliveryError):
    def __init__(self, status: int):
        self.status = status
        super().__init__('EVENT_SERVER_FAILURE_' + str(status))


class EventTransportFailure(EventDeliveryError):
    pass


class EventProtocolError(EventDeliveryError):
    pass
