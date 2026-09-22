from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from src.malaria_dl.execution.contracts import RunEventType as E
from src.malaria_dl.execution.emitter import RunEventEmitter
from src.malaria_dl.execution.journal import EventState, JournalError
from src.malaria_dl.local_execution.event_journal import SQLiteEventJournal
from src.malaria_dl.local_execution.event_runtime import check_remote, compose, journal_path, stream_identity, prepare_payload
from test_event_journal import Reporter


@pytest.fixture
def assignment(tmp_path):
    run,attempt=str(uuid4()),str(uuid4())
    job=dict(job_id=str(uuid4()),agent_id=str(uuid4()),run_id=run,artifact_root_id='artifacts',
             session=dict(run_id=run,attempt_id=attempt))
    remote=dict(run_id=run,attempt_id=attempt,last_sequence=0,last_event_id=None,terminal_type=None,legacy_exists=False)
    return job, remote


def api(remote):
    return SimpleNamespace(call=lambda *a:deepcopy(remote),url='http://127.0.0.1:1234/execution/local',bearer='test',timeout=1)


def test_new_composition_and_absent_history_guard(tmp_path,assignment):
    job,remote=assignment
    path=journal_path(tmp_path/'agent.json',job)
    assert path.parent==tmp_path/'e10_journals'
    with compose(api(remote),job,path,tmp_path)[0] as journal:
        assert journal.created
    other=tmp_path/'lost.sqlite3'
    remote.update(last_sequence=1,last_event_id=str(uuid4()),legacy_exists=True)
    with pytest.raises(JournalError,match='JOURNAL_REQUIRED_FOR_RECOVERY'):
        compose(api(remote),job,other,tmp_path)
    assert not other.exists()


@pytest.mark.parametrize('remote_changes', [dict(last_sequence=2,last_event_id=str(uuid4())),dict(terminal_type='training_completed'),dict(run_id=str(uuid4()))])
def test_remote_divergence_closed(tmp_path,assignment,remote_changes):
    job,remote=assignment;remote.update(remote_changes)
    with pytest.raises(JournalError):check_remote(api(remote),stream_identity(job),EventState())


def test_exact_pending_may_be_committed_or_not(tmp_path,assignment):
    job,remote=assignment;ident=stream_identity(job)
    with SQLiteEventJournal(tmp_path/'j',ident,create=True) as journal:
        writer=RunEventEmitter(Reporter(OSError()),run_id=ident.run_id,attempt_id=ident.attempt_id,journal=journal)
        with pytest.raises(OSError):writer.emit(E.EPOCH_COMPLETED,{})
        state=journal.load(ident.run_id,ident.attempt_id)
        check_remote(api(remote),ident,state)
        remote.update(last_sequence=1,last_event_id=str(writer.pending.event_id))
        check_remote(api(remote),ident,state)
        remote['last_event_id']=str(uuid4())
        with pytest.raises(JournalError,match='DIVERGED'):check_remote(api(remote),ident,state)


def test_payload_paths_are_references_before_pending(tmp_path,assignment):
    job,_=assignment;path=tmp_path/job['run_id']/'epoch_1.keras'
    payload={'result':{'path':str(path),'sha256':'a'*64},'legacy_record':{'kind':'artifact'}}
    transformed=prepare_payload(job,tmp_path)(payload)
    assert transformed['result']['path']=={'root_id':'artifacts','relative_path':job['run_id']+'/epoch_1.keras'}
    assert payload['result']['path']==str(path)


def test_worker_restart_recovers_transport_without_restarting_train(tmp_path,assignment,monkeypatch):
    import io,json,os
    from src.malaria_dl.local_execution import worker,event_runtime
    from src.malaria_dl.execution import train
    job,_=assignment
    job['session'].update(dataset={'dataset_root':{'root_id':'data'}},artifact_root={'relative_path':job['run_id']})
    job['dataset_manifest']=[]
    ident=stream_identity(job);path=tmp_path/'j'
    with SQLiteEventJournal(path,ident,create=True) as journal:
        writer=RunEventEmitter(Reporter(OSError()),run_id=ident.run_id,attempt_id=ident.attempt_id,journal=journal)
        with pytest.raises(OSError):writer.emit(E.EPOCH_COMPLETED,{})
        expected=writer.pending.to_dict()
    reporter=Reporter()
    def composition(*args):
        journal=SQLiteEventJournal(path,ident)
        return journal,RunEventEmitter(reporter,run_id=ident.run_id,attempt_id=ident.attempt_id,journal=journal)
    monkeypatch.setattr(event_runtime,'compose',composition)
    monkeypatch.setattr(worker,'verify_samples',lambda *a:None)
    monkeypatch.setattr(train,'train',lambda *a,**k:pytest.fail('scientific restart'))
    monkeypatch.setenv('CAPSTONE_AGENT_BEARER','synthetic')
    monkeypatch.setattr(worker.sys,'stdin',io.StringIO(json.dumps(dict(job=job,roots={'data':str(tmp_path),'artifacts':str(tmp_path)},url='http://127.0.0.1:1234',event_journal=str(path)))))
    with pytest.raises(JournalError,match='SCIENTIFIC_RESUME_UNSUPPORTED'):worker.main()
    assert reporter.events[0].to_dict()==expected
    with SQLiteEventJournal(path,ident) as journal:
        assert journal.load(ident.run_id,ident.attempt_id).next_sequence==2
