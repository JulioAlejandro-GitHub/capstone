"""Committed synthetic evidence in the isolated EXEC.1 PostgreSQL, never production."""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
import importlib.util
import os

import pytest
from sqlalchemy import create_engine, text
from src.malaria_dl.assessment.repository import AssessmentRepository
from src.malaria_dl.assessment.service import run
from src.malaria_dl.campaigns.contracts import CampaignError
from src.malaria_dl.execution.repository import ExecutionRepository
from src.malaria_dl.execution.selection import select_trainings
from src.malaria_dl.models.configuration import resolve_config
from test_assessment_e6 import value, Runtime

pytestmark = pytest.mark.requires_docker_postgres


@pytest.fixture
def postgres(tmp_path):
    # Fixed test-only endpoint: no fallback to operational DATABASE_URL.
    engine = create_engine('postgresql+psycopg://exec1_fixture:exec1_fixture_only@exec1-postgres:5432/exec1_fixture')
    migration_path = Path('/scripts/../alembic_v2/versions/20261012_01_exec1.py')
    if not migration_path.exists():
        migration_path = Path('/tmp/exec1_migration.py')
    spec = importlib.util.spec_from_file_location('exec1_migration', migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.begin() as c:
        assert c.execute(text('SELECT current_database()')).scalar_one() == 'exec1_fixture'
        c.execute(text(migration.SQL))
    gate = engine.connect()
    gate.execute(text('SELECT pg_advisory_lock(120994,1)'))
    gate.commit()
    owner = str(uuid4())
    with engine.begin() as c:
        c.execute(text("INSERT INTO experiment_execution_gate(singleton,owner,db_pid) VALUES(true,:owner,:pid) "
                       "ON CONFLICT(singleton) DO UPDATE SET owner=excluded.owner,db_pid=excluded.db_pid"),
                  dict(owner=owner,pid=gate.execute(text('SELECT pg_backend_pid()')).scalar_one()))
    @contextmanager
    def scope(readonly=False):
        with engine.begin() as c:
            if readonly: c.execute(text('SET TRANSACTION READ ONLY'))
            c.execute(text("SELECT set_config('capstone.execution_token',:owner,true)"),dict(owner=owner))
            yield c
    repo = AssessmentRepository(scope)
    # Recover only unfinished fixtures in this isolated database after failed test runs.
    with engine.connect() as c:
        unfinished = list(c.execute(text("SELECT run_id,owner FROM train_execution_sessions WHERE state='active'")).mappings())
    for session in unfinished:
        ExecutionRepository(scope).finish(session['run_id'],session['owner'],'failed',cause='SYNTHETIC_FIXTURE_INTERRUPTED')
    v = value(tmp_path)
    dataset = v['dataset']['dataset_version_id']
    with engine.begin() as c:
        c.execute(text("""INSERT INTO dataset_versions
            (id,name,semantic_version,grouping_strategy,grouping_field,stratification_strategy,
             split_algorithm,split_algorithm_version,random_seed,target_train_ratio,target_val_ratio,target_test_ratio,positive_class)
            VALUES(:id,:name,'1','patient','patient_id','label','synthetic','1',11,.6,.2,.2,'parasitized')"""),dict(id=dataset,name="EXEC1 synthetic fixture "+dataset))
        config = resolve_config('custom_cnn')
        ExecutionRepository._create_run(c,v['model']['training_run_id'],config,v['dataset'],{},evidence_id=None)
        c.execute(text("UPDATE runs SET status='completed',finished_at=clock_timestamp() WHERE id=:id"),dict(id=v['model']['training_run_id']))
    v.update(split='test',purpose='final',seed=11,batch_size=64)
    v['protocol'].update(splits=['test'],purposes=['final'])
    samples = []
    for label,score in [(0,.2),(0,.8),(1,.2),(1,.8)]:
        sample = deepcopy(v['samples'][label])
        sample.update(sample_id=str(uuid4()),label=label,split='test',score=score)
        samples.append(sample)
    v['samples'] = samples
    yield engine,repo,v
    gate.execute(text("SELECT pg_advisory_unlock(120994,1)"))
    gate.close()
    engine.dispose()


class Scores(Runtime):
    def predict(self,samples):
        return [s['score'] for s in samples]


def test_test_roundtrip_independent_connection_and_immutable_history(postgres,tmp_path):
    engine,repo,v = postgres
    first = run(repo,v,tmp_path,Scores)
    # All repository operations commit; a different physical connection reads the result.
    with engine.connect() as writer, engine.connect() as reader:
        assert writer.execute(text('SELECT pg_backend_pid()')).scalar_one() != reader.execute(text('SELECT pg_backend_pid()')).scalar_one()
        row = reader.execute(text('SELECT * FROM assessment_attempts WHERE id=:id'),dict(id=first['id'])).mappings().one()
        assert row['state'] == 'verified' and row['started_at'] and row['finished_at']
        before = dict(row)
        rows = reader.execute(text('SELECT payload FROM assessment_results WHERE attempt_id=:id'),dict(id=first['id'])).scalars().all()
        assert len(rows) == row['verification']['count'] == 4
        counts = {k:0 for k in ('tn','fp','fn','tp')}
        for r in rows: counts[('tn','fp','fn','tp')[2*r['label']+r['predicted']]] += 1
        assert counts == dict(tn=1,fp=1,fn=1,tp=1)
        assert all(row['verification']['metrics'][k] == val for k,val in counts.items())
        assert row['verification']['metrics']['accuracy'] == .5
        assert row['verification']['metrics']['f1'] == .5
        assert row['verification']['metrics']['f2'] == .5
        assert row['verification']['metrics']['roc_auc'] == .5
        assert row['verification']['metrics']['pr_auc'] == .5
        assert reader.execute(text('SELECT count(*) FROM assessment_final_locks')).scalar_one() == 0
    stored = repo.identity(first['identity_id'])
    assert stored['model'] == v['model'] and stored['dataset'] == v['dataset']
    assert stored['split'] == 'test' and stored['purpose'] == 'final'
    assert stored['seed'] == 11 and stored['batch_size'] == 64
    second = run(repo,v,tmp_path,Scores)
    assert second['id'] != first['id']
    assert repo.attempt(first['id']) == before
    assert repo.results(first['id']) == sorted(rows,key=lambda r:r['sample_id'])
    # A real constraint error must fail; it cannot become a successful execution.
    with pytest.raises(CampaignError):
        repo.write_batch(first['id'],first['owner'],rows)
    with pytest.raises(CampaignError):
        with repo.transaction() as c:
            c.execute(text("UPDATE assessment_results SET payload=payload WHERE attempt_id=:id"),dict(id=first['id']))


def test_selection_and_fresh_training(postgres,tmp_path):
    engine,repo,v = postgres
    source = select_trainings(repo,None,v['model']['training_run_id'])[0]
    assert str(source['dataset_version_id']) == v['dataset']['dataset_version_id']
    assert source['configuration']['model_id'] == 'custom_cnn'
    with pytest.raises(CampaignError,match='NOT_FOUND'):
        select_trainings(repo,None,str(uuid4()))

    original = deepcopy(source)
    train_repo = ExecutionRepository(repo.scope)
    first = train_repo.standalone(source['configuration'],v['dataset'],{},tmp_path,'synthetic',1,None,
                                 source_training_run_id=str(source['id']))
    train_repo.finish(first['run_id'],first['owner'],'failed',cause='SYNTHETIC_RESERVATION_ONLY')
    second = train_repo.standalone(source['configuration'],v['dataset'],{},tmp_path,'synthetic',1,None,
                                  source_training_run_id=str(source['id']))
    train_repo.finish(second['run_id'],second['owner'],'failed',cause='SYNTHETIC_RESERVATION_ONLY')
    assert first['run_id'] != second['run_id'] != source['id']
    assert first['artifact_root'] != second['artifact_root']
    assert first['configuration'] == second['configuration'] == source['configuration']
    assert select_trainings(repo,None,str(source['id']))[0] == original
    with engine.connect() as c:
        assert c.execute(text("SELECT execution_parameters->>'source_training_run_id' FROM runs WHERE id=:id"),
                         dict(id=first['run_id'])).scalar_one() == str(source['id'])


def test_campaign_membership_and_all_runs_without_freezing(postgres):
    import json
    engine,repo,v = postgres
    campaign,other,evidence = map(str,(uuid4(),uuid4(),uuid4()))
    trains = [str(uuid4()),str(uuid4())]
    config = resolve_config('custom_cnn')
    with engine.begin() as c:
        c.execute(text("""INSERT INTO audit_events
            (id,event_type,action,resource_type,request_method,request_path,correlation_id,after_state,success)
            VALUES(CAST(:id AS uuid),'ml.dataset_verification','synthetic','dataset_version','TEST','exec1',CAST(:id AS text),CAST(:state AS jsonb),true)"""),
            dict(id=evidence,state=json.dumps(dict(integrity_status='verified',snapshot=v['dataset'],dataset_version_id=v['dataset']['dataset_version_id']))))
        for cid in (campaign,other):
            c.execute(text("""INSERT INTO experimental_campaigns
                (id,name,purpose,dataset_version_id,dataset_snapshot,dataset_evidence_id,requested,protocol,environment,actor)
                VALUES(:id,'EXEC1 fixture','synthetic',:dataset,CAST(:snapshot AS jsonb),:evidence,'{}','{}','{}','fixture')"""),
                dict(id=cid,dataset=v['dataset']['dataset_version_id'],snapshot=json.dumps(v['dataset']),evidence=evidence))
        for train in trains:
            ExecutionRepository._create_run(c,train,config,v['dataset'],{},campaign_id=campaign)
    assert {str(r['id']) for r in select_trainings(repo,campaign,None)} == set(trains)
    assert [str(r['id']) for r in select_trainings(repo,campaign,trains[0])] == [trains[0]]
    with pytest.raises(CampaignError,match='CAMPAIGN_MISMATCH'):
        select_trainings(repo,other,trains[0])
    with pytest.raises(CampaignError,match='REQUIRED'):
        select_trainings(repo,None,None)
