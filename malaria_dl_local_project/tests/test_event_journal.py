"""Real SQLite, process death, exclusive writers and fail-closed state recovery."""
from dataclasses import replace
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from uuid import uuid4

import pytest
from src.malaria_dl.execution.contracts import RunEventType as E
from src.malaria_dl.execution.emitter import RunEventEmitter, EventStreamClosed, PendingEventExists
from src.malaria_dl.execution.journal import EventState, JournalError
from src.malaria_dl.local_execution.event_journal import SQLiteEventJournal, StreamIdentity, encoded


@pytest.fixture
def journal_identity():
    return StreamIdentity(uuid4(),uuid4(),uuid4(),uuid4())


class Reporter:
    def __init__(self, failure=None): self.events=[]; self.failure=failure
    def report(self,event):
        self.events.append(event)
        if self.failure: raise self.failure


def emitter(journal, reporter=None):
    return RunEventEmitter(reporter or Reporter(), run_id=journal.identity.run_id,
                           attempt_id=journal.identity.attempt_id, journal=journal)


def test_pending_exact_roundtrip_confirm_closed_and_new_run(tmp_path,journal_identity):
    path=tmp_path/'stream.sqlite3'; ident=journal_identity
    with SQLiteEventJournal(path,ident,create=True) as journal:
        assert journal.created and journal.load(ident.run_id,ident.attempt_id)==EventState()
        writer=emitter(journal,Reporter(OSError('lost')))
        with pytest.raises(OSError):writer.emit(E.EPOCH_COMPLETED, {'types':[1,1.0,-0.0,True,None,'á\x00\ud800']})
        pending=writer.pending
        with pytest.raises(PendingEventExists):writer.emit(E.TRAINING_FAILED,{})
    with SQLiteEventJournal(path,ident) as journal:
        reporter=Reporter();writer=emitter(journal,reporter)
        assert writer.pending.to_dict()==pending.to_dict()
        assert writer.retry_pending().to_dict()==pending.to_dict()
        assert writer.next_sequence==2 and writer.pending is None
        writer.emit(E.TRAINING_COMPLETED, {'records_hash':'a'*64})
        assert writer.closed
    with SQLiteEventJournal(path,ident) as journal:
        writer=emitter(journal)
        assert writer.closed and writer.next_sequence==3
        assert journal.load(ident.run_id,ident.attempt_id).terminal_type is E.TRAINING_COMPLETED
        with pytest.raises(EventStreamClosed):writer.emit(E.EPOCH_COMPLETED,{})
    with SQLiteEventJournal(tmp_path/'other.sqlite3',replace(ident,run_id=uuid4(),attempt_id=uuid4()),create=True) as journal:
        assert emitter(journal).next_sequence==1
    assert os.stat(path).st_mode & 0o777 == 0o600


@pytest.mark.parametrize('field',['job_id','agent_id','run_id','attempt_id'])
def test_identity_mismatch(tmp_path,journal_identity,field):
    path=tmp_path/'j'
    with SQLiteEventJournal(path,journal_identity,create=True):pass
    with pytest.raises(JournalError,match='IDENTITY_MISMATCH'):
        SQLiteEventJournal(path,replace(journal_identity,**{field:uuid4()}))


@pytest.mark.parametrize('corruption',['bytes','empty','version','table','payload','state','checksum'])
def test_corruption_is_never_reinitialized(tmp_path,journal_identity,corruption):
    path=tmp_path/'j'
    with SQLiteEventJournal(path,journal_identity,create=True):pass
    if corruption=='bytes':path.write_bytes(b'not sqlite')
    elif corruption=='empty':path.write_bytes(b'')
    else:
        with sqlite3.connect(path) as db:
            if corruption=='version':db.execute('PRAGMA user_version=99')
            elif corruption=='table':db.execute('CREATE TABLE surprise (x)')
            else:
                value=json.loads(db.execute('SELECT body FROM stream').fetchone()[0])
                if corruption=='payload':value['state']['pending']={'broken':True}
                elif corruption=='state':value['state']['next_sequence']=False
                body=encoded(value)
                checksum=SQLiteEventJournal._hash(body) if corruption!='checksum' else 'bad'
                db.execute('UPDATE stream SET body=?,sha256=?',(body,checksum))
    before=path.read_bytes()
    with pytest.raises(JournalError):SQLiteEventJournal(path,journal_identity,create=True)
    assert path.read_bytes()==before


@pytest.mark.parametrize('when',['save','confirm','confirm_after_commit'])
def test_journal_failure_stops_http_or_retains_pending(tmp_path,journal_identity,monkeypatch,when):
    path=tmp_path/'j';reporter=Reporter()
    with SQLiteEventJournal(path,journal_identity,create=True) as journal:
        transition=journal.transition
        def fail(expected,updated):
            if (when=='save' and updated.pending) or (when.startswith('confirm') and not updated.pending):
                if when=='confirm_after_commit':transition(expected,updated)
                raise JournalError('disk failure')
            transition(expected,updated)
        monkeypatch.setattr(journal,'transition',fail)
        writer=emitter(journal,reporter)
        with pytest.raises(JournalError):writer.emit(E.EPOCH_COMPLETED,{})
        assert writer.pending is not None and writer.next_sequence==1
        assert len(reporter.events)==(0 if when=='save' else 1)
        with pytest.raises(JournalError,match='REOPEN_REQUIRED'):writer.retry_pending()
    with SQLiteEventJournal(path,journal_identity) as journal:
        recovered=emitter(journal)
        if when=='save':assert recovered.pending is None and recovered.next_sequence==1
        elif when=='confirm':assert recovered.pending.to_dict()==reporter.events[0].to_dict()
        else:assert recovered.pending is None and recovered.next_sequence==2


def test_sql_transaction_rollback_and_state_cas(tmp_path,journal_identity):
    with SQLiteEventJournal(tmp_path/'j',journal_identity,create=True) as journal:
        with pytest.raises(RuntimeError):
            with journal._transaction():
                journal.connection.execute("UPDATE stream SET sha256='bad'")
                raise RuntimeError('rollback')
        assert emitter(journal).next_sequence==1
        with pytest.raises(JournalError,match='STATE_CONFLICT'):
            journal.transition(EventState(2),EventState(3))
        assert emitter(journal).next_sequence==1


@pytest.mark.parametrize('point',['A','C','D'])
def test_real_process_crash_and_restart(tmp_path,journal_identity,point):
    path=tmp_path/'j'
    script='''
import json,os,sys
from uuid import UUID
from src.malaria_dl.local_execution.event_journal import SQLiteEventJournal,StreamIdentity
from src.malaria_dl.execution.emitter import RunEventEmitter
from src.malaria_dl.execution.contracts import RunEventType as E
identity=StreamIdentity(*(UUID(v) for v in json.loads(sys.argv[2])))
with SQLiteEventJournal(sys.argv[1],identity,create=True) as journal:
 class Reporter:
  def report(self,event):
   # At both crash boundaries a separate connection sees committed pending.
   import sqlite3
   with sqlite3.connect(sys.argv[1]) as c:
    assert json.loads(c.execute('SELECT body FROM stream').fetchone()[0])['state']['pending']==event.to_dict()
   if sys.argv[3]=='A':os._exit(71)
 reporter=Reporter()
 if sys.argv[3]=='C':
  original=journal.transition
  def transition(before,after):
   if after.pending is None:os._exit(72)
   original(before,after)
  journal.transition=transition
 writer=RunEventEmitter(reporter,run_id=identity.run_id,attempt_id=identity.attempt_id,journal=journal)
 writer.emit(E.EPOCH_COMPLETED,{'metric':0.75})
 os._exit(73)
'''
    result=subprocess.run([sys.executable,'-B','-c',script,str(path),json.dumps(list(journal_identity.wire().values())),point],timeout=15)
    assert result.returncode=={'A':71,'C':72,'D':73}[point]
    with SQLiteEventJournal(path,journal_identity) as journal:
        writer=emitter(journal)
        if point!='D':
            event=writer.pending;assert event.sequence==1
            assert writer.retry_pending() is event
        assert writer.next_sequence==2
        assert writer.emit(E.EPOCH_COMPLETED,{}).sequence==2


def test_other_process_cannot_open_active_writer(tmp_path,journal_identity):
    path=tmp_path/'j'
    with SQLiteEventJournal(path,journal_identity,create=True):
        script='''
import json,sys
from uuid import UUID
from src.malaria_dl.local_execution.event_journal import SQLiteEventJournal,StreamIdentity
from src.malaria_dl.execution.journal import JournalError
try:SQLiteEventJournal(sys.argv[1],StreamIdentity(*(UUID(v) for v in json.loads(sys.argv[2]))))
except JournalError as exc:
 assert str(exc)=='EVENT_JOURNAL_ALREADY_OPEN'
else:raise AssertionError('concurrent writer')
'''
        p=subprocess.run([sys.executable,'-B','-c',script,str(path),json.dumps(list(journal_identity.wire().values()))],timeout=15)
        assert p.returncode==0
