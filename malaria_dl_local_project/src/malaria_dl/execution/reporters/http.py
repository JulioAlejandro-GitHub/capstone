"""Send an already constructed event through the Local HTTP client."""
from ..contracts import RunEvent, RunReporter
from ...local_execution.event_transport import EventProtocolError, EventRequest, RemoteExecutionIdentity


class HttpRunReporter(RunReporter):
    def __init__(self, api_client, remote_execution_identity: RemoteExecutionIdentity):
        self._api = api_client
        self._identity = remote_execution_identity

    def report(self, event: RunEvent) -> None:
        reply = self._api.call_event(EventRequest(identity=self._identity, event=event).to_dict())
        if (type(reply) is not dict
                or reply.keys() != {'status', 'run_id', 'event_id', 'sequence'}
                or reply['status'] not in ('accepted', 'duplicate_accepted')
                or reply['run_id'] != str(event.run_id)
                or reply['event_id'] != str(event.event_id)
                or type(reply['sequence']) is not int or reply['sequence'] != event.sequence):
            raise EventProtocolError('EVENT_ACCEPTANCE_UNCONFIRMED')
