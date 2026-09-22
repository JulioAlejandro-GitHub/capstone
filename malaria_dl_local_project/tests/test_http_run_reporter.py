"""HTTP-only event delivery; failures never manufacture event identity."""
from datetime import datetime, timezone
from io import BytesIO
from http.client import IncompleteRead
import json
from urllib.error import HTTPError, URLError
from uuid import uuid4

import pytest

from src.malaria_dl.execution.contracts import RunEvent, RunEventType, RunReporter
from src.malaria_dl.execution.reporters.http import HttpRunReporter
from src.malaria_dl.local_execution.event_transport import (
    EventRequest, RemoteExecutionIdentity, EventRejected, EventServerFailure,
    EventTransportFailure, EventProtocolError,
)
from src.malaria_dl.local_execution.event_client import build_http_run_reporter
from src.malaria_dl.local_execution import transport


@pytest.fixture
def event():
    return RunEvent(event_id=uuid4(), run_id=uuid4(), attempt_id=uuid4(), sequence=7,
                    occurred_at=datetime.now(timezone.utc), event_type=RunEventType.EVALUATION_COMPLETED,
                    payload={'values': [1, 1.0, True, -0.0, None, '\x00', '\ud800', 'á']})


@pytest.mark.parametrize('status', ['accepted', 'duplicate_accepted'])
def test_exact_http_envelope_and_receipt(monkeypatch, event, status):
    identity = RemoteExecutionIdentity(job_id=uuid4(), agent_id=uuid4())
    requests = []
    def send(req, timeout):
        requests.append(req)
        reply = dict(status=status, run_id=str(event.run_id), event_id=str(event.event_id), sequence=7)
        return BytesIO(json.dumps(reply).encode())
    monkeypatch.setattr(transport, 'urlopen', send)
    reporter = build_http_run_reporter('http://127.0.0.1:9000', 'synthetic', identity)
    assert isinstance(reporter, RunReporter)
    assert reporter.report(event) is None
    assert reporter.report(event) is None
    assert requests[0].data == requests[1].data
    request = json.loads(requests[0].data)
    assert request.keys() == {'job_id', 'agent_id', 'event'}
    assert EventRequest.from_dict(request).identity == identity
    # Compare JSON strings to preserve 1 vs 1.0, bool vs int and signed zero.
    assert json.dumps(EventRequest.from_dict(request).event.to_dict()) == json.dumps(event.to_dict())
    assert requests[0].full_url == 'http://127.0.0.1:9000/execution/local/events'
    assert requests[0].get_header('Authorization') == 'Bearer synthetic'


@pytest.mark.parametrize('error,expected', [
    (HTTPError('secret', 409, 'secret', {}, None), EventRejected),
    (HTTPError('secret', 403, 'secret', {}, None), EventRejected),
    (HTTPError('secret', 503, 'secret', {}, None), EventServerFailure),
    (URLError('secret'), EventTransportFailure), (TimeoutError('secret'), EventTransportFailure),
    (ConnectionResetError('secret'), EventTransportFailure),
    (IncompleteRead(b'partial'), EventTransportFailure),
])
def test_typed_failures_preserve_identity_for_explicit_retry(monkeypatch, event, error, expected):
    requests = []
    def fail(req, timeout):
        requests.append(req.data)
        raise error
    monkeypatch.setattr(transport, 'urlopen', fail)
    reporter = build_http_run_reporter('http://localhost:9000', 'synthetic',
        RemoteExecutionIdentity(job_id=uuid4(), agent_id=uuid4()))
    for _ in range(2):
        with pytest.raises(expected) as caught:
            reporter.report(event)
        assert 'secret' not in str(caught.value)
    assert len(requests) == 2 and requests[0] == requests[1]


@pytest.mark.parametrize('reply', [None, {}, {'status': 'accepted'},
    {'status': 'accepted', 'run_id': 'wrong', 'event_id': 'wrong', 'sequence': 7}])
def test_malformed_success_is_not_acceptance(event, reply):
    class Client:
        def call_event(self, payload): return reply
    with pytest.raises(EventProtocolError):
        HttpRunReporter(Client(), RemoteExecutionIdentity(job_id=uuid4(), agent_id=uuid4())).report(event)


@pytest.mark.parametrize('extra', ['owner', 'principal', 'campaign_id', 'member_id', 'context'])
def test_dto_rejects_client_authority(event, extra):
    value = EventRequest(identity=RemoteExecutionIdentity(job_id=uuid4(), agent_id=uuid4()), event=event).to_dict()
    with pytest.raises(ValueError):
        EventRequest.from_dict({**value, extra: str(uuid4())})


def test_invalid_json_response(monkeypatch, event):
    monkeypatch.setattr(transport, 'urlopen', lambda *a, **k: BytesIO(b'not json'))
    reporter = build_http_run_reporter('http://localhost:9000', 'synthetic',
        RemoteExecutionIdentity(job_id=uuid4(), agent_id=uuid4()))
    with pytest.raises(EventProtocolError):
        reporter.report(event)
