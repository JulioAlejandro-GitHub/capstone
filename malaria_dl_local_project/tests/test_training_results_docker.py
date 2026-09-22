"""One real Keras epoch in Docker, real selected checkpoint and atomic PG results."""
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from src.malaria_dl.execution.train import train
from src.malaria_dl.execution.worker import docker_context
from src.malaria_dl.execution.composition import build_docker_run_reporter
from src.malaria_dl.execution.emitter import RunEventEmitter
from src.malaria_dl.execution.contracts import RunEventType as E
from src.malaria_dl.execution.artifacts import verify_session, keras_loader
from src.malaria_dl.models.registry import resolve_descriptor
from src.malaria_dl.results.training import TrainingResultsV1, ThresholdResult
from src.malaria_dl.evaluation.validation import evaluate_validation_predictions
from src.malaria_dl.campaigns.contracts import digest
from test_campaigns_postgres import isolated  # noqa: F401
from test_result_repository_postgres import pg  # noqa: F401
from test_docker_reporter_postgres import legacy_repository
from test_local_execution_postgres import synthetic_images

pytestmark=pytest.mark.skipif(os.getenv('RUN_E10_POSTGRES_TESTS')!='1',reason='Explicit temporary-schema opt-in')


@pytest.fixture(params=[False,True])
def real_docker(request,monkeypatch,tmp_path):
    if not Path('/.dockerenv').exists():pytest.skip('Requires actual Docker scientific runtime')
    import test_campaigns_postgres as fixtures
    original_dataset,original_request,original_protocol=fixtures.dataset,fixtures.matrix_request,fixtures.protocol
    root=tmp_path/'synthetic-data';synthetic_images(root,{'train':2,'val':2})
    def dataset():return original_dataset()|{'dataset_root':str(root)}
    def matrix(seeds=None):
        value=original_request(seeds);value['models']=['custom_cnn'];value['optimizers']=['adam']
        value['variants'][0]['selected']={'model':{'input_shape':[32,32,3]},
            'execution':{'max_epochs':1,'fine_tune_epochs':0,'batch_size':2,'no_augment':True,'calibrate_threshold':request.param}}
        return value
    def protocol():
        value=original_protocol()
        if not request.param:value['calibration']['algorithm']='none'
        return value
    monkeypatch.setattr(fixtures,'protocol',protocol)
    monkeypatch.setattr(fixtures,'dataset',dataset);monkeypatch.setattr(fixtures,'matrix_request',matrix)
    pg=request.getfixturevalue('pg');repo=legacy_repository(pg)
    repo.finish(pg.ctx.run_id,pg.ctx.owner,'failed',cause='SYNTHETIC_FIXTURE_SETUP')
    session=repo.claim(pg.ctx.campaign_id,str(uuid4()),'synthetic-docker',os.getpid(),tmp_path/'train')
    row=repo.get(pg.ctx.campaign_id)
    attempt=next(a for a in row['attempts'] if a['id']==session['attempt_id'])
    member=next(m for m in row['members'] if m['id']==attempt['member_id'])
    return pg,repo,session,docker_context(session,row,attempt,member),request.param


def test_real_epoch_final_result_and_verification(real_docker):
    pg,repo,session,ctx,calibrated=real_docker
    reporter=build_docker_run_reporter(ctx,execution_token=pg.token,engine_factory=pg.factory)
    emitter=RunEventEmitter(reporter,run_id=ctx.run_id,attempt_id=ctx.attempt_id)
    train(repo,session,resolve_descriptor('custom_cnn'),event_emitter=emitter)
    events=repo.result_events(ctx.run_id)
    assert [e.event_type for e in events][-2:]==[E.EVALUATION_COMPLETED,E.TRAINING_COMPLETED]
    assert [e.sequence for e in events]==list(range(1,len(events)+1))
    with pg.sql() as c:
        output=c.execute(text('SELECT parameters FROM runs WHERE id=:id'),{'id':ctx.run_id}).scalar_one()
    result=TrainingResultsV1.from_dict(output['training_results']).validation
    evidence=next(row['payload'] for row in repo.records(ctx.run_id) if row['kind']=='calibration')
    samples=evidence['samples']
    threshold=ThresholdResult(evidence['result']['threshold_used'],'validation_calibration') if calibrated else ThresholdResult(.5,'default')
    assert result==evaluate_validation_predictions([s['label'] for s in samples],[s['score'] for s in samples],threshold)
    assert result.n_samples==2 and result.to_dict()==events[-2].to_dict()['payload']
    assert all(s['sample'].startswith('val/') for s in samples)
    current=repo.session(ctx.run_id)
    proof=verify_session(repo,current,keras_loader)
    assert proof['records_hash']==events[-1].payload['records_hash']==digest(repo.records(ctx.run_id))
    repo.finish(ctx.run_id,ctx.owner,'verified',proof)
    assert repo.session(ctx.run_id)['state']=='verified'
