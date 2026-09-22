"""E10.6 reader/hash/emitter proof on real PostgreSQL, temporary schemas only."""
from dataclasses import replace
import json
import os
from pathlib import Path
import re
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from src.malaria_dl.campaigns.contracts import CampaignError, canonical, digest
from src.malaria_dl.execution.artifacts import verify_session
from src.malaria_dl.execution.contracts import RunEventType as Kind
from src.malaria_dl.execution.emitter import RunEventEmitter, PendingEventExists
from src.malaria_dl.persistence.execution_record_readers import read_result_events
from src.malaria_dl.results.errors import EventIdConflict, ResultPersistenceError, WriterNotAuthorized
from src.malaria_dl.results.identity import canonical_event
from test_campaigns_postgres import isolated  # noqa: F401
from test_result_repository_postgres import pg, item, apply, REVISION  # noqa: F401
from test_docker_reporter_postgres import legacy_repository, reporter, snapshot
from test_execution_record_readers import golden_rows, GOLDEN_BYTES, GOLDEN_HASH

pytestmark = [pytest.mark.requires_docker_postgres, pytest.mark.skipif(
    os.getenv('RUN_E10_EMITTER_POSTGRES_TESTS') != '1', reason='Explicit disposable-schema opt-in required')]


def historical_unfiltered_records(pg):
    """Exact pre-fix query; intentionally diagnostic, never used by completion."""
    with pg.sql() as c:
        return [dict(r) for r in c.execute(text('''SELECT kind,phase,record_key,payload
            FROM train_execution_records WHERE run_id=:id ORDER BY kind,phase,record_key'''),
            {'id': pg.ctx.run_id}).mappings()]


def install_golden(pg):
    repo = legacy_repository(pg)
    for row in golden_rows():
        repo.put(pg.ctx.run_id, pg.ctx.owner, row['kind'], row['phase'], row['record_key'], row['payload'])
    return repo


def test_golden_hash_unaffected_by_one_many_events_and_exact_retries(pg):
    repo = install_golden(pg)
    old = historical_unfiltered_records(pg)
    assert canonical(old).encode('utf-8') == GOLDEN_BYTES
    assert canonical(repo.legacy_records(pg.ctx.run_id)).encode('utf-8') == GOLDEN_BYTES
    assert digest(repo.records(pg.ctx.run_id)) == GOLDEN_HASH
    before = snapshot(pg)
    stream = RunEventEmitter(reporter(pg), run_id=pg.ctx.run_id, attempt_id=pg.ctx.attempt_id)
    emitted = []
    for n in range(1, 13):
        event = stream.emit(Kind.TRAINING_COMPLETED if n == 12 else Kind.EPOCH_COMPLETED,
                            {'number': n, 'types': [1, 1.0, True, -0.0], 'text': '\x00\ud800á'})
        emitted.append(event)
        reporter(pg).report(event)  # exact accepted duplicate, no extra evidence
        assert canonical(repo.records(pg.ctx.run_id)).encode('utf-8') == GOLDEN_BYTES
        assert digest(repo.records(pg.ctx.run_id)) == GOLDEN_HASH
        # Reproduce the previous defect with the ORIGINAL unfiltered query.
        assert digest(historical_unfiltered_records(pg)) != GOLDEN_HASH
    assert stream.closed
    restored = repo.result_events(pg.ctx.run_id)
    assert [e.sequence for e in restored] == list(range(1, 13))  # numeric, not 1,10,11,2
    assert [canonical_event(e) for e in restored] == [canonical_event(e) for e in emitted]
    assert len(pg.records()) == len(old) + 12
    assert snapshot(pg) == before  # full run JSON includes all three parameter/config columns


def test_family_uses_column_not_kind_or_payload_and_run_is_scoped(pg):
    repo = legacy_repository(pg)
    before = digest(repo.records(pg.ctx.run_id))
    payload = {'event_id': str(uuid4()), 'canonical_event': 'not an event'}
    repo.put(pg.ctx.run_id, pg.ctx.owner, 'epoch_completed', 'legacy', '10', payload)
    repo.put(pg.ctx.run_id, pg.ctx.owner, 'epoch_completed', 'legacy', '2', payload)
    event = item(pg.ctx, event_type=Kind.EPOCH_COMPLETED, payload=payload)
    reporter(pg).report(event)
    legacy = repo.legacy_records(pg.ctx.run_id)
    assert [r['record_key'] for r in legacy if r['kind'] == 'epoch_completed'] == ['10', '2']
    assert len(legacy) == 3 and len(repo.result_events(pg.ctx.run_id)) == 1
    assert repo.records(uuid4()) == [] and repo.result_events(uuid4()) == []
    assert digest(legacy) != before  # unfamiliar legacy kinds still belong to the historical hash


def test_pre_e10_schema_remains_readable_without_migration_or_backfill(pg):
    repo = install_golden(pg)
    with pg.sql() as c:
        apply(c, REVISION, 'downgrade')  # Own temporary schema only; no E10 rows exist.
    assert canonical(repo.records(pg.ctx.run_id)).encode('utf-8') == GOLDEN_BYTES
    assert repo.result_events(pg.ctx.run_id) == []
    # Names alone cannot turn a pre-E10 historical row into an event.
    repo.put(pg.ctx.run_id, pg.ctx.owner, 'e10_event', 'old', 'old', {'historical': True})
    assert any(r['kind'] == 'e10_event' for r in repo.records(pg.ctx.run_id))
    assert repo.result_events(pg.ctx.run_id) == []


def valid_legacy_session(pg):
    from test_campaign_executor_e5 import evidence
    repo = legacy_repository(pg)
    actual = repo.session(pg.ctx.run_id)
    root = Path(actual['artifact_root'])
    root.mkdir(parents=True, exist_ok=True)
    synthetic, rows = evidence(root)
    for row in rows:
        if row['kind'] == 'runtime': continue
        if row['kind'] == 'artifact':
            row['payload'].update(run_id=str(pg.ctx.run_id), version_id=str(uuid4()))
        if row['kind'] == 'calibration': row['payload']['checkpoint_epoch'] = 1
        repo.put(pg.ctx.run_id, pg.ctx.owner, row['kind'], row['phase'], row['record_key'], row['payload'])
    actual['completion'] = {**synthetic['completion'], 'records_hash': digest(repo.records(pg.ctx.run_id))}
    return repo, actual


def test_mixed_verification_and_future_terminal_before_finish_order(pg):
    from src.malaria_dl.assessment.lineage import resolve
    repo, session = valid_legacy_session(pg)
    completion = dict(session['completion'])
    expected = verify_session(repo, session, lambda *_: None)
    before = snapshot(pg)
    stream = RunEventEmitter(reporter(pg), run_id=pg.ctx.run_id, attempt_id=pg.ctx.attempt_id)
    stream.emit(Kind.EVALUATION_COMPLETED, {'scope': 'synthetic'})
    terminal = stream.emit(Kind.TRAINING_COMPLETED, {'records_hash': completion['records_hash']})
    assert snapshot(pg) == before
    assert verify_session(repo, session, lambda *_: None) == expected
    assert session['completion'] == completion
    # Explicit existing lifecycle operations, not side effects of any event.
    repo.finish(pg.ctx.run_id, pg.ctx.owner, 'completed', completion)
    verification = verify_session(repo, repo.session(pg.ctx.run_id), lambda *_: None)
    repo.finish(pg.ctx.run_id, pg.ctx.owner, 'verified', verification)
    binding, _, calibration = resolve(repo, training_run_id=pg.ctx.run_id)
    assert binding['source']['records_hash'] == completion['records_hash']
    assert calibration['checkpoint_epoch'] == 1
    assert repo.result_events(pg.ctx.run_id)[-1] == terminal  # reading remains allowed
    with pytest.raises(WriterNotAuthorized): reporter(pg).report(terminal)


def test_e10_tampering_is_rejected_independently_of_legacy_hash(pg):
    repo = install_golden(pg)
    event = item(pg.ctx)
    reporter(pg).report(event)
    with pytest.raises(EventIdConflict): reporter(pg).report(replace(event, payload={'changed': True}))
    for statement in ("UPDATE train_execution_records SET payload='{}' WHERE event_id=:id",
                      'DELETE FROM train_execution_records WHERE event_id=:id'):
        with pytest.raises(DBAPIError):
            with pg.sql() as c: c.execute(text(statement), {'id': event.event_id})
    assert digest(repo.records(pg.ctx.run_id)) == GOLDEN_HASH
    assert repo.result_events(pg.ctx.run_id) == [event]


def test_legacy_idempotency_lookup_cannot_acknowledge_an_e10_row(pg):
    repo = legacy_repository(pg)
    event = item(pg.ctx)
    reporter(pg).report(event)
    with pytest.raises(CampaignError):
        repo.put(pg.ctx.run_id, pg.ctx.owner, 'e10_event', 'run_event_v1',
                 str(event.event_id), {'canonical_event': canonical_event(event)})
    assert len(pg.records()) == 2 and repo.result_events(pg.ctx.run_id) == [event]


def test_corrupt_e10_does_not_poison_legacy_hash_but_event_reader_fails_closed(pg):
    repo = install_golden(pg)
    event = item(pg.ctx)
    # Authorized SQL fixture inserts opaque but inconsistent canonical text.
    # No UPDATE/DELETE or disabled trigger is used to manufacture corruption.
    with pg.sql() as c:
        c.execute(text('''INSERT INTO train_execution_records
            (run_id,kind,phase,record_key,payload,event_id,event_sequence)
            VALUES(:run,'e10_event','run_event_v1',:key,CAST(:payload AS jsonb),:id,1)'''),
            dict(run=pg.ctx.run_id, key=str(event.event_id), id=event.event_id,
                 payload=json.dumps({'canonical_event': canonical_event(replace(event, run_id=uuid4()))})))
    assert digest(repo.records(pg.ctx.run_id)) == GOLDEN_HASH
    with pytest.raises(ResultPersistenceError):
        with pg.sql() as c: read_result_events(c, pg.ctx.run_id)
    with pytest.raises(CampaignError, match='CAMPAIGN_DATABASE_OPERATION_FAILED'):
        repo.result_events(pg.ctx.run_id)


def test_pending_survives_real_commit_lost_ack_without_hash_change(pg):
    repo = install_golden(pg)
    durable = reporter(pg)
    class LostAck:
        lost = True
        def report(self, event):
            durable.report(event)
            if self.lost: raise ConnectionError('synthetic after commit')
    delivery = LostAck()
    stream = RunEventEmitter(delivery, run_id=pg.ctx.run_id, attempt_id=pg.ctx.attempt_id)
    with pytest.raises(ConnectionError): stream.emit(Kind.EPOCH_COMPLETED, {'value': 1.0})
    pending = stream.pending
    assert len(repo.result_events(pg.ctx.run_id)) == 1 and stream.next_sequence == 1
    with pytest.raises(PendingEventExists): stream.emit(Kind.TRAINING_COMPLETED, {})
    delivery.lost = False
    assert stream.retry_pending() is pending
    assert stream.next_sequence == 2 and len(repo.result_events(pg.ctx.run_id)) == 1
    assert digest(repo.records(pg.ctx.run_id)) == GOLDEN_HASH


def test_summary_calibration_reader_selects_legacy_explicitly(pg):
    from app.services.training_summaries import TRAINING_SUMMARIES_SQL
    repo = legacy_repository(pg)
    repo.put(pg.ctx.run_id, pg.ctx.owner, 'calibration', 'val', 'selected', {'legacy': True})
    reporter(pg).report(item(pg.ctx, event_type=Kind.CALIBRATION_COMPLETED, payload={'legacy': False}))
    # Execute the actual lateral subquery from the UI reader against the synthetic run.
    sql = re.search(r'LEFT JOIN LATERAL \((\s*SELECT record.payload.*?)\) AS campaign_calibration',
                    TRAINING_SUMMARIES_SQL, re.S).group(1)
    with pg.sql() as c:
        value = c.execute(text('SELECT calibration.payload FROM (SELECT CAST(:id AS uuid) AS id) selected '
            'LEFT JOIN LATERAL (' + sql + ') calibration ON TRUE'), {'id': pg.ctx.run_id}).scalar_one()
    assert value == {'legacy': True}
