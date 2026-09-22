"""Same TRAIN, same science path and event types with both approved reporters."""
from copy import deepcopy
from uuid import UUID,uuid4

import pytest
from src.malaria_dl.execution.train import train
from src.malaria_dl.execution.emitter import RunEventEmitter
from src.malaria_dl.execution.artifacts import verify_session
from src.malaria_dl.execution.reporters.docker import DockerRunReporter
from src.malaria_dl.execution.reporters.http import HttpRunReporter
from src.malaria_dl.local_execution.event_transport import EventRequest,RemoteExecutionIdentity
from src.malaria_dl.local_execution.event_journal import SQLiteEventJournal,StreamIdentity
from src.malaria_dl.local_execution.event_runtime import prepare_payload
from src.malaria_dl.results import ResultService
from result_repository_fake import FakeResultRepository
from test_result_service import context
from test_docker_train_integration import setup  # noqa: F401
from docker_train_fixture import MemoryRepository


@pytest.mark.parametrize('calibration',[False,True])
def test_shared_scientific_path_has_identical_ordered_event_types(setup,tmp_path,calibration,monkeypatch):
    from datetime import datetime
    from src.malaria_dl.evaluation import threshold_calibration
    class Clock:
        @staticmethod
        def now(): return datetime(2026,9,22,12)
    monkeypatch.setattr(threshold_calibration,'datetime',Clock)
    original,descriptor,_,_,_,_=setup
    original['configuration']['resolved']['execution']['calibrate_threshold']=calibration
    streams=[];legacy=[];outputs=[]
    for mode in ('docker','local'):
        session=deepcopy(original);session['artifact_root']=str(tmp_path/mode)
        repo=MemoryRepository(session,[])
        storage=FakeResultRepository()
        ctx=context(run_id=UUID(session['run_id']),attempt_id=UUID(session['attempt_id']))
        storage.authorize(ctx);service=ResultService(storage)
        journal=None
        if mode=='docker':reporter=DockerRunReporter(ctx,service)
        else:
            identity=RemoteExecutionIdentity(job_id=uuid4(),agent_id=uuid4())
            class Api:
                def call_event(self,payload):
                    request=EventRequest.from_dict(payload)
                    receipt=service.accept_event(ctx,request.event)
                    return dict(status=receipt.status.value,run_id=str(receipt.run_id),event_id=str(receipt.event_id),sequence=receipt.sequence)
            reporter=HttpRunReporter(Api(),identity)
            journal=SQLiteEventJournal(tmp_path/'journal',StreamIdentity(identity.job_id,identity.agent_id,ctx.run_id,ctx.attempt_id),create=True)
        try:
            stream=RunEventEmitter(reporter,run_id=ctx.run_id,attempt_id=ctx.attempt_id,journal=journal,
                prepare_payload=prepare_payload({'artifact_root_id':'shared'},tmp_path) if journal else None)
            train(repo,session,descriptor,event_emitter=stream)
            assert stream.closed
            assert verify_session(repo,session,lambda *a:None)['records_hash']==session['completion']['records_hash']
            streams.append(storage.events)
            outputs.append(storage.parameters[ctx.run_id])
            legacy.append([r for r in repo.records(session['run_id']) if r['kind'] not in ('artifact','artifact_prepared')])
        finally:
            if journal:journal.close()
    assert [e.event_type for e in streams[0]]==[e.event_type for e in streams[1]]
    assert [e.sequence for e in streams[0]]==[e.sequence for e in streams[1]]==list(range(1,len(streams[0])+1))
    assert legacy[0]==legacy[1]
    assert outputs[0]==outputs[1]
    assert streams[0][-2].to_dict()['payload']==streams[1][-2].to_dict()['payload']
    assert outputs[0]['training_results']['validation']==streams[0][-2].to_dict()['payload']
