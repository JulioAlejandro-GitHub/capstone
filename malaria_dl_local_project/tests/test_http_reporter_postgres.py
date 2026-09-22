"""Real loopback HTTP, real JWT auth, real E10 transactions in disposable schemas.

No dependency override bypasses authentication or permission checks. Synthetic
users live only in the same temporary schema as the synthetic job and results.
"""
from contextlib import contextmanager
from dataclasses import fields, replace
import json
import os
import socket
from threading import Thread
import time
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest
from sqlalchemy import text

from src.malaria_dl.execution.contracts import RunEvent, RunEventType
from src.malaria_dl.local_execution.event_transport import (
    EventRequest, RemoteExecutionIdentity, EventRejected, EventTransportFailure, EventServerFailure,
)
from src.malaria_dl.local_execution.event_client import build_http_run_reporter
from src.malaria_dl.local_execution.event_context import LocalExecutionContextResolver
from src.malaria_dl.local_execution import event_backend, transport
from src.malaria_dl.results.identity import canonical_event
from test_campaigns_postgres import isolated  # noqa: F401
from test_result_repository_postgres import pg, item  # noqa: F401
from test_docker_reporter_postgres import snapshot, legacy_repository

pytestmark = [pytest.mark.requires_docker_postgres, pytest.mark.skipif(
    os.getenv('RUN_E10_HTTP_POSTGRES_TESTS') != '1', reason='Explicit disposable-schema opt-in required')]


@contextmanager
def serve(app):
    import uvicorn
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    server = uvicorn.Server(uvicorn.Config(app, log_level='critical', access_log=False))
    thread = Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(.01)
        assert server.started
        yield 'http://127.0.0.1:' + str(sock.getsockname()[1])
    finally:
        server.should_exit = True
        thread.join(10)
        sock.close()
        assert not thread.is_alive()


@pytest.fixture
def remote(pg, monkeypatch):
    from fastapi import FastAPI
    from app import security, config
    from app.routes import local_execution as route
    principal, other = uuid4(), uuid4()
    with pg.sql() as c:
        c.execute(text('CREATE TABLE users(id uuid PRIMARY KEY, username text, status text)'))
        for user in (principal, other):
            c.execute(text("INSERT INTO users VALUES(:id,'synthetic','active')"), {'id': user})
        c.execute(text('''UPDATE local_execution_jobs SET principal=:principal,run_id=:run,
            session=(SELECT to_jsonb(s) FROM train_execution_sessions s WHERE s.run_id=:run)'''),
            {'principal': str(principal), 'run': pg.ctx.run_id})
        job = c.execute(text('SELECT * FROM local_execution_jobs')).mappings().one()
    identity = RemoteExecutionIdentity(job_id=job['id'], agent_id=job['agent_id'])
    base = config.Settings.from_env()
    settings = SimpleNamespace(**{field.name: getattr(base, field.name) for field in fields(base)})
    settings.auth_mode = 'local_jwt'
    settings.jwt_secret = uuid4().hex + uuid4().hex
    settings.jwt_algorithm = 'HS256'
    settings.jwt_access_token_expire_minutes = 5
    monkeypatch.setattr(security, 'get_settings', lambda: settings)
    monkeypatch.setattr(config, 'get_settings', lambda: settings)
    auth_engine = pg.factory()
    monkeypatch.setattr(security, 'get_primary_engine', lambda: auth_engine)
    monkeypatch.setenv('CAPSTONE_LOCAL_EXECUTION_ENABLED', '1')
    build = event_backend.build_local_event_backend
    monkeypatch.setattr(event_backend, 'build_local_event_backend', lambda: build(engine_factory=pg.factory))
    def token(user=principal, role='administrator'):
        return security.create_access_token(user, 'synthetic', [role])
    def app():
        application = FastAPI()
        application.include_router(route.router)
        return application
    try:
        with serve(app()) as url:
            def reporter(identity_override=None, bearer=None):
                return build_http_run_reporter(url, bearer or token(), identity_override or identity)
            def post(payload, bearer=None):
                req = Request(url + '/execution/local/events', data=json.dumps(payload).encode(),
                    headers={'Content-Type': 'application/json', **(
                        {'Authorization': 'Bearer ' + bearer} if bearer is not None else {})})
                try:
                    with urlopen(req, timeout=10) as response:
                        return response.status, json.load(response)
                except HTTPError as exc:
                    with exc:
                        return exc.code, json.load(exc)
            yield SimpleNamespace(identity=identity, principal=principal, other=other, token=token,
                url=url, app=app, reporter=reporter, post=post, settings=settings)
    finally:
        auth_engine.dispose()


def wire(remote, event):
    return EventRequest(identity=remote.identity, event=event).to_dict()


@pytest.mark.parametrize('kind', [RunEventType.PHASE_COMPLETED, RunEventType.TRAINING_COMPLETED])
def test_real_http_sequences_recreation_and_no_side_effects(pg, remote, kind):
    before = snapshot(pg)
    with pg.sql() as c:
        job_before = c.execute(text('SELECT to_jsonb(j) FROM local_execution_jobs j')).scalar_one()
    first = item(pg.ctx, event_type=kind, payload={'unicode': '\x00\ud800á', 'numbers': [1, 1.0, -0.0, True]})
    second = item(pg.ctx, sequence=2, event_type=kind)
    assert remote.reporter().report(first) is None
    assert remote.reporter().report(second) is None
    rows = pg.records()
    assert len(rows) == 3
    assert rows[1]['payload']['canonical_event'] == canonical_event(first)
    assert RunEvent.from_dict(json.loads(rows[1]['payload']['canonical_event'])).to_dict() == first.to_dict()
    # Recreate FastAPI app/server AND the complete client and backend composition.
    with serve(remote.app()) as url:
        assert build_http_run_reporter(url, remote.token(), remote.identity).report(first) is None
    status, receipt = remote.post(wire(remote, first), remote.token())
    assert status == 200 and receipt['status'] == 'duplicate_accepted'
    assert pg.records() == rows and snapshot(pg) == before
    with pg.sql() as c:
        assert c.execute(text('SELECT to_jsonb(j) FROM local_execution_jobs j')).scalar_one() == job_before


def test_lost_response_after_real_commit_then_retry(pg, remote, monkeypatch):
    first = item(pg.ctx)
    real_open = transport.urlopen
    def lose(req, timeout):
        with real_open(req, timeout=timeout) as response:
            assert json.load(response)['status'] == 'accepted'
        raise ConnectionResetError('synthetic lost ACK after committed acceptance')
    monkeypatch.setattr(transport, 'urlopen', lose)
    with pytest.raises(EventTransportFailure):
        remote.reporter().report(first)
    assert len(pg.records()) == 2
    monkeypatch.setattr(transport, 'urlopen', real_open)
    assert remote.reporter().report(first) is None
    assert len(pg.records()) == 2


@pytest.mark.parametrize('case,code', [('payload','EVENT_ID_CONFLICT'),
    ('sequence','SEQUENCE_CONFLICT'), ('gap','SEQUENCE_GAP')])
def test_http_conflicts(pg, remote, case, code):
    first = item(pg.ctx)
    remote.reporter().report(first)
    altered = {'payload': replace(first, payload={'tampered': True}),
        'sequence': replace(first, event_id=uuid4()),
        'gap': replace(first, event_id=uuid4(), sequence=4)}[case]
    assert remote.post(wire(remote, altered), remote.token()) == (409, {'detail': code})
    with pytest.raises(EventRejected) as caught:
        remote.reporter().report(altered)
    assert caught.value.status == 409 and len(pg.records()) == 2


@pytest.mark.parametrize('case,status', [('absent',401), ('invalid_jwt',401), ('wrong_principal',403),
    ('permission',403), ('agent',403), ('job',403), ('run',409), ('attempt',409),
    ('owner',422), ('context',422), ('schema',422), ('sequence_bool',422)])
def test_auth_and_tampering(pg, remote, case, status):
    payload = wire(remote, item(pg.ctx))
    bearer = remote.token()
    if case == 'absent': bearer = None
    elif case == 'invalid_jwt': bearer = 'invalid'
    elif case == 'wrong_principal': bearer = remote.token(remote.other)
    elif case == 'permission': bearer = remote.token(role='read_only')
    elif case in ('agent','job'): payload[case + '_id'] = str(uuid4())
    elif case in ('run','attempt'): payload['event'][case + '_id'] = str(uuid4())
    elif case in ('owner','context'): payload[case] = str(pg.ctx.owner)
    elif case == 'schema': payload['event']['schema_version'] = 'run_event_v999'
    elif case == 'sequence_bool': payload['event']['sequence'] = True
    before = snapshot(pg)
    assert remote.post(payload, bearer)[0] == status
    assert len(pg.records()) == 1 and snapshot(pg) == before


@pytest.mark.parametrize('state', ['released', 'failed'])
def test_closed_jobs_reject_even_duplicate(pg, remote, state):
    first = item(pg.ctx)
    remote.reporter().report(first)
    with pg.sql() as c:
        c.execute(text('UPDATE local_execution_jobs SET state=:state'), {'state': state})
    assert remote.post(wire(remote, first), remote.token())[0] == 403
    assert len(pg.records()) == 2


def test_calculation_reported_is_still_held(pg, remote):
    with pg.sql() as c:
        c.execute(text("UPDATE local_execution_jobs SET state='calculation_reported'"))
    assert remote.reporter().report(item(pg.ctx)) is None


@pytest.mark.parametrize('case', ['inactive', 'owner_snapshot', 'gate', 'disabled_user'])
def test_persisted_fencing(pg, remote, case):
    first = item(pg.ctx)
    if case == 'inactive':
        legacy_repository(pg).finish(pg.ctx.run_id, pg.ctx.owner, 'failed', cause='SYNTHETIC')
    else:
        with pg.sql() as c:
            if case == 'owner_snapshot':
                c.execute(text("UPDATE local_execution_jobs SET session=jsonb_set(session,'{owner}',to_jsonb(CAST(:owner AS text)))"), {'owner': str(uuid4())})
            elif case == 'gate': c.execute(text('UPDATE experiment_execution_gate SET owner=NULL'))
            else: c.execute(text("UPDATE users SET status='disabled'"))
    before = snapshot(pg)
    status, _ = remote.post(wire(remote, first), remote.token())
    assert status == (401 if case == 'disabled_user' else 403)
    assert len(pg.records()) == 1 and snapshot(pg) == before


@pytest.mark.parametrize('field', ['principal', 'agent_id', 'state', 'session'])
def test_identity_revalidated_inside_acceptance_transaction(pg, remote, monkeypatch, field):
    original = LocalExecutionContextResolver.resolve
    def race(resolver, identity, principal):
        resolved = original(resolver, identity, principal)
        with pg.sql() as c:
            statements = {
                'principal': "UPDATE local_execution_jobs SET principal='changed-after-resolution'",
                'agent_id': "UPDATE local_execution_jobs SET agent_id=CAST(:value AS uuid)",
                'state': "UPDATE local_execution_jobs SET state='released'",
                'session': "UPDATE local_execution_jobs SET session=jsonb_set(session,'{owner}',to_jsonb(CAST(:value AS text)))",
            }
            c.execute(text(statements[field]), {'value': str(uuid4())})
        return resolved
    monkeypatch.setattr(LocalExecutionContextResolver, 'resolve', race)
    assert remote.post(wire(remote, item(pg.ctx)), remote.token())[0] == 403
    assert len(pg.records()) == 1


def test_internal_owner_is_resolved_without_remote_token(pg, remote):
    resolved = LocalExecutionContextResolver(pg.factory).resolve(remote.identity, str(remote.principal))
    assert resolved.context.owner == pg.ctx.owner
    assert resolved.execution_token == pg.token != resolved.context.owner
    assert resolved.context.attempt_id == pg.ctx.attempt_id
    assert resolved.context.campaign_id == pg.ctx.campaign_id
    assert resolved.context.member_id == pg.ctx.member_id
    assert set(wire(remote, item(pg.ctx))) == {'job_id', 'agent_id', 'event'}
    assert remote.reporter().report(item(pg.ctx)) is None


@pytest.mark.parametrize('case,status,detail', [
    ('storage',503,'RESULT_PERSISTENCE_ERROR'), ('unexpected',500,'LOCAL_EVENT_INTERNAL_ERROR')])
def test_server_failures_are_sanitized(pg, remote, monkeypatch, case, status, detail):
    from src.malaria_dl.results.errors import ResultPersistenceError
    def fail(*a):
        if case == 'storage': raise ResultPersistenceError()
        raise RuntimeError('secret database URL and SQL')
    monkeypatch.setattr(LocalExecutionContextResolver, 'resolve', fail)
    assert remote.post(wire(remote, item(pg.ctx)), remote.token()) == (status, {'detail': detail})
    with pytest.raises(EventServerFailure) as caught:
        remote.reporter().report(item(pg.ctx))
    assert caught.value.status == status and len(pg.records()) == 1


def test_local_jwt_and_opt_in_required(pg, remote, monkeypatch):
    remote.settings.auth_mode = 'disabled'
    assert remote.post(wire(remote, item(pg.ctx)), remote.token()) == (503, {'detail': 'LOCAL_EVENTS_REQUIRE_LOCAL_JWT'})
    remote.settings.auth_mode = 'local_jwt'
    monkeypatch.setenv('CAPSTONE_LOCAL_EXECUTION_ENABLED', '0')
    assert remote.post(wire(remote, item(pg.ctx)), remote.token()) == (503, {'detail': 'LOCAL_EXECUTION_DISABLED'})
    assert len(pg.records()) == 1


def test_http_commit_failure_rolls_back_and_exact_retry_succeeds(pg, remote, monkeypatch):
    from sqlalchemy import event as sa_event
    from sqlalchemy.exc import OperationalError
    from src.malaria_dl.persistence.result_repository import PostgresResultRepository
    original = PostgresResultRepository._authorize
    def fail_on_commit(repository, connection, context, event):
        original(connection, context, event)
        def fail(connection):
            raise OperationalError('synthetic SQL containing private details', {}, RuntimeError('secret'))
        sa_event.listen(connection, 'commit', fail)
    monkeypatch.setattr(PostgresResultRepository, '_authorize', fail_on_commit)
    first = item(pg.ctx)
    before = snapshot(pg)
    assert remote.post(wire(remote, first), remote.token()) == (503, {'detail': 'RESULT_PERSISTENCE_ERROR'})
    assert len(pg.records()) == 1 and snapshot(pg) == before
    monkeypatch.setattr(PostgresResultRepository, '_authorize', staticmethod(original))
    assert remote.reporter().report(first) is None
    assert len(pg.records()) == 2


def test_http_records_preserve_legacy_digest_without_consolidation(pg, remote):
    from src.malaria_dl.campaigns.contracts import digest
    repo = legacy_repository(pg)
    before = repo.records(pg.ctx.run_id)
    state = snapshot(pg)
    remote.reporter().report(item(pg.ctx, event_type=RunEventType.TRAINING_COMPLETED))
    after = repo.records(pg.ctx.run_id)
    assert digest(before) == digest(after)
    assert after == before
    assert len(repo.result_events(pg.ctx.run_id)) == 1
    assert snapshot(pg) == state


def test_production_error_envelope_preserves_status_and_sanitized_message(pg, remote):
    from fastapi import HTTPException
    from app.main import http_error
    app = remote.app()
    app.add_exception_handler(HTTPException, http_error)
    with serve(app) as url:
        first = item(pg.ctx)
        reporter = build_http_run_reporter(url, remote.token(), remote.identity)
        assert reporter.report(first) is None
        req = Request(url + '/execution/local/events',
            data=json.dumps(wire(remote, replace(first, payload={'tampered': True}))).encode(),
            headers={'Authorization': 'Bearer ' + remote.token(), 'Content-Type': 'application/json'})
        with pytest.raises(HTTPError) as caught:
            urlopen(req, timeout=10)
        with caught.value as response:
            assert response.code == 409
            body = json.load(response)
            assert body['error']['code'] == 'CONFLICT'
            assert body['error']['message'] == 'EVENT_ID_CONFLICT'
            assert body['error']['retryable'] is False
    assert len(pg.records()) == 2
