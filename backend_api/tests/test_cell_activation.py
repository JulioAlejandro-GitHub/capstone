"""Real PostgreSQL constraints and rollback in a disposable Docker DB, never the active DB."""
import hashlib
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.services.cell_activation import CellActivationService
from app.services.productive_model import ProductiveModelResolver
from app.repositories import cell_activation as repository
from src.model_governance.errors import GovernanceStateError


@pytest.fixture(scope='module')
def database():
    url = os.getenv('CELL_ACTIVATION_TEST_URL', '')
    if not url:
        pytest.skip('Requires make test-cell-activation-backend disposable database')
    assert url == 'postgresql+psycopg://postgres@cell-activation-db:5432/cell_activation_test'
    engine = create_engine(url)
    scripts = ScriptDirectory.from_config(Config('/app/alembic_v2.ini'))
    with engine.begin() as c:
        assert c.execute(text('SELECT current_database()')).scalar_one() == 'cell_activation_test'
        c.execute(text('CREATE ROLE capstone_v2_migrator; CREATE ROLE capstone_v2_runtime;'))
        c.info['pg_v2_verified_target'] = 'disposable-cell-activation-test'
        migration_context = MigrationContext.configure(c)
        migration_context._ensure_version_table()
        with Operations.context(migration_context):
            scripts.get_revision('pg_v2_baseline').module.upgrade()
        c.execute(text("INSERT INTO alembic_version(version_num) VALUES('pg_v2_baseline')"))
    migrate = [sys.executable, '-m', 'alembic', '-c', '/app/alembic_v2.ini', '-x',
               'activation_migration=true', '-x', 'activation_database=cell_activation_test', 'upgrade', 'head']
    for _ in range(2):
        result = subprocess.run(migrate, env={**os.environ, 'PGV2_DATABASE_URL': url}, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    yield engine
    engine.dispose()


class TransactionEngine:
    def __init__(self, connection):
        self.connection = connection

    @contextmanager
    def begin(self):
        with self.connection.begin_nested():
            yield self.connection

    @contextmanager
    def connect(self):
        yield self.connection


@pytest.fixture
def ctx(database, tmp_path):
    with database.connect() as c:
        transaction = c.begin()
        token = str(uuid4())
        c.execute(text('SELECT pg_advisory_xact_lock(120994,1)'))
        c.execute(text("SELECT set_config('capstone.execution_token',:token,true)"), {'token':token})
        c.execute(text('UPDATE experiment_execution_gate SET owner=:token,db_pid=pg_backend_pid()'), {'token':token})
        engine = TransactionEngine(c)
        class Model:
            input_shape = (None, 2, 2, 3)
            def predict(self, batch, verbose=0):
                return np.full((len(batch), 1), .7)
        resolver = ProductiveModelResolver(engine=engine, model_loader=lambda _: Model(), allowed_roots=[tmp_path])
        service = CellActivationService(engine, resolver=resolver)
        yield c, service, resolver, tmp_path
        transaction.rollback()


def candidate(ctx, *, train='completed', state='verified'):
    c, _, _, root = ctx
    training, attempt, identity, version, artifact = [uuid4() for _ in range(5)]
    path = root / f'{version}.keras'
    path.write_bytes(str(version).encode())
    mapping={'0':'uninfected','1':'parasitized','positive_class':1,'positive_label':'parasitized'}
    model={'model_version_id':str(version),'checkpoint_artifact_id':str(artifact),
           'training_run_id':str(training),'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
           'bytes':path.stat().st_size,'input_contract':{'architecture':'custom_cnn','shape':[None,2,2,3],
             'external':{'mode':'rescale_0_1'},'output':{'shape':[None,1],'meaning':'probability_parasitized'},'label_mapping':mapping}}
    sample,owner=uuid4(),uuid4()
    payload={'schema':'assessment_identity_v1','dataset':{},'samples':[{'sample_id':str(sample),'patient_id':'synthetic-patient','label':1,'split':'val','sha256':'a'*64}],
             'protocol':{'version':'fixture','splits':['val'],'purposes':['development']},'kind':'evaluate','model':model,'split':'val','purpose':'development',
             'decision':{'effective':.5,'comparison':'>=','score_domain':'raw'}}
    c.execute(text("INSERT INTO runs(id,run_type,status) VALUES(:id,'training',:state)"),{'id':training,'state':train})
    canonical=json.dumps(payload,sort_keys=True,separators=(',',':'))
    c.execute(text("""INSERT INTO assessment_identities(id,identity_hash,training_run_id,kind,identity,canonical_identity)
      VALUES(:id,:hash,:train,'evaluate',CAST(:payload AS jsonb),:canonical)"""),
      {'id':identity,'hash':hashlib.sha256(canonical.encode()).hexdigest(),'train':training,'payload':canonical,'canonical':canonical})
    c.execute(text("""INSERT INTO assessment_attempts(id,identity_id,owner,host,pid,ordinal,artifact_root)
      VALUES(:id,:identity,:owner,'fixture',1,1,:root)"""),
      {'id':attempt,'identity':identity,'owner':owner,'root':str(attempt)})
    c.execute(text("SELECT set_config('capstone.assessment_owner',:owner,true)"),{'owner':str(owner)})
    if state=='verified':
        c.execute(text("INSERT INTO assessment_results(attempt_id,sample_id,payload) VALUES(:id,:sample,CAST(:payload AS jsonb))"),
          {'id':attempt,'sample':sample,'payload':json.dumps({'sample_id':str(sample),'patient_id':'synthetic-patient','label':1,'raw_score':.7,'calibrated_score':None,'threshold':.5,'predicted':1})})
    if state!='active':
        c.execute(text("UPDATE assessment_attempts SET state=:state,verification=CAST(:verification AS jsonb),finished_at=NOW() WHERE id=:id"),
          {'id':attempt,'state':state,'verification':json.dumps({'count':1,'sha256':'a'*64,'metrics':{'recall':.01}}) if state=='verified' else None})
    return training, attempt, model


def count(c, table):
    return c.execute(text(f'SELECT count(*) FROM {table}')).scalar_one()


def test_verified_activation_materializes_identity_and_selects_checkpoint_for_new_crops(ctx):
    c, service, resolver, _ = ctx
    training, attempt, model = candidate(ctx)
    assert count(c,'model_versions') == 0
    result=service.activate(training,actor='test')
    resolved=resolver.resolve()
    assert resolved.model_version_id == model['model_version_id']
    assert resolved.source_evaluation_attempt_id == str(attempt)
    assert resolved.source_evaluation_run_id is None
    assert resolver.revalidate(resolved, connection=c).deployment_id == resolved.deployment_id
    assert resolved.threshold == .5
    assert resolved.checkpoint_sha256 == model['sha256']
    assert count(c,'runs') == 1  # no fabricated evaluation/inference RUN
    assert count(c,'model_versions') == count(c,'artifacts') == 1
    assert resolver.load(resolved).predict(np.zeros((1,2,2,3)))[0,0] == .7
    before=count(c,'stage2_model_publication_events')
    assert service.activate(training,actor='test')['idempotent']
    assert count(c,'stage2_model_publication_events') == before
    assert result['available_for_inference']


@pytest.mark.parametrize('train,state',[('running','verified'),('completed','failed'),('completed','active')])
def test_only_completed_training_and_verified_evaluation_can_activate(ctx,train,state):
    c, service, _, _ = ctx
    training, _, _ = candidate(ctx,train=train,state=state)
    with pytest.raises(GovernanceStateError): service.activate(training,actor='test')
    assert count(c,'model_versions') == count(c,'stage2_model_publications') == 0


def test_missing_evaluation(ctx):
    c,service,_,_=ctx
    training=uuid4()
    c.execute(text("INSERT INTO runs(id,run_type,status) VALUES(:id,'training','completed')"),{'id':training})
    with pytest.raises(GovernanceStateError): service.activate(training,actor='test')


def test_replacement_is_atomic_preserves_historical_snapshot_and_uses_new_cache_key(ctx,monkeypatch):
    c, service, resolver, _ = ctx
    first,_,_=candidate(ctx)
    service.activate(first,actor='test')
    old=resolver.resolve()
    snapshot=old.snapshot(inference_version='test',review_margin=.1,batch_size=1)
    second,_,model=candidate(ctx)
    with pytest.raises(GovernanceStateError,match='STAGE2_SELECTION_EXISTS'):
        service.activate(second,actor='test')
    assert resolver.resolve().deployment_id == old.deployment_id
    activate=repository.activate_deployment
    def fail(*args):
        activate(*args)
        raise RuntimeError('injected persistence failure')
    monkeypatch.setattr(repository,'activate_deployment',fail)
    with pytest.raises(RuntimeError,match='persistence'):
        service.activate(second,actor='test',replace_existing=True)
    assert resolver.resolve().deployment_id == old.deployment_id
    assert count(c,'model_versions') == 1
    monkeypatch.setattr(repository,'activate_deployment',activate)
    service.activate(second,actor='test',replace_existing=True)
    new=resolver.resolve()
    assert new.model_version_id == model['model_version_id']
    assert new.cache_key != old.cache_key
    assert resolver.resolve_snapshot(snapshot).deployment_id == old.deployment_id
    assert c.execute(text("SELECT count(*) FROM stage2_model_publications WHERE is_active")).scalar_one()==1


def test_load_failure_rolls_back_all_registration_and_publication(ctx):
    c,service,resolver,_=ctx
    training,_,_=candidate(ctx)
    def fail(_): raise ValueError('checkpoint cannot load')
    resolver.model_loader=fail
    with pytest.raises(ValueError,match='cannot load'): service.activate(training,actor='test')
    for table in ('artifacts','model_versions','stage2_model_publications','deployed_model_versions'):
        assert count(c,table)==0


def test_fk_xor_and_exact_assessment_lineage_are_enforced(ctx):
    c,service,_,_=ctx
    training,attempt,_=candidate(ctx)
    service.activate(training,actor='test')
    for sql in ("UPDATE stage2_model_publications SET evaluation_run_id=training_run_id",
                "UPDATE stage2_model_publications SET evaluation_attempt_id=NULL",
                "UPDATE deployed_model_versions SET threshold_assessment_attempt_id=NULL"):
        with pytest.raises(IntegrityError), c.begin_nested(): c.execute(text(sql))


def test_existing_physical_checkpoint_is_reused_without_duplicate_artifact(ctx):
    c,service,resolver,_=ctx
    training,_,model=candidate(ctx)
    registered=uuid4()
    c.execute(text("""INSERT INTO artifacts(id,run_id,artifact_type,path,checksum,file_size_bytes)
      VALUES(:id,:train,'model_checkpoint',:path,:sha,:size)"""),
      {'id':registered,'train':training,'path':model['path'],'sha':model['sha256'],'size':model['bytes']})
    service.activate(training,actor='test')
    assert count(c,'artifacts')==1
    assert resolver.resolve().checkpoint_artifact_id==str(registered)
    assert str(registered)!=model['checkpoint_artifact_id']
    assert c.execute(text("SELECT metadata->>'assessment_checkpoint_identity_id' FROM model_versions")).scalar_one()==model['checkpoint_artifact_id']


def test_wrong_verified_assessment_cannot_be_attached_to_another_model(ctx):
    c,service,_,_=ctx
    training,_,model=candidate(ctx)
    service.activate(training,actor='test')
    _,other_attempt,_=candidate(ctx)
    with pytest.raises(IntegrityError), c.begin_nested():
        c.execute(text("""INSERT INTO stage2_model_publications(datasource,model_version_id,training_run_id,
          checkpoint_artifact_id,evaluation_attempt_id,status,is_active,deactivated_at)
          VALUES('malaria',:version,:train,:artifact,:attempt,'inactive',false,NOW())"""),
          {'version':model['model_version_id'],'train':training,'artifact':model['checkpoint_artifact_id'],'attempt':other_attempt})


def test_new_crop_snapshot_accepts_assessment_source_and_rejects_false_lineage(ctx):
    c,service,resolver,_=ctx
    training,_,_=candidate(ctx)
    service.activate(training,actor='test')
    resolved=resolver.resolve()
    snapshot=resolved.snapshot(inference_version='test',review_margin=.1,batch_size=1)
    c.execute(text('CREATE TEMP TABLE cell_snapshot_probe AS SELECT * FROM cell_classification_runs WITH NO DATA'))
    c.execute(text('CREATE TRIGGER probe BEFORE INSERT ON cell_snapshot_probe FOR EACH ROW EXECUTE FUNCTION validate_cell_classification_run_snapshot()'))
    sql=text("""INSERT INTO cell_snapshot_probe(production_model_id,stage2_publication_id,model_registry_id,
      model_name,model_version,model_snapshot) VALUES(:deployment,:publication,:version,:name,:number,CAST(:snapshot AS jsonb))""")
    params={'deployment':resolved.deployment_id,'publication':resolved.publication_id,'version':resolved.model_version_id,
            'name':resolved.model_name,'number':resolved.model_version,'snapshot':json.dumps(snapshot)}
    c.execute(sql,params)
    snapshot['source_evaluation_attempt_id']=str(uuid4())
    with pytest.raises(IntegrityError), c.begin_nested():
        c.execute(sql,{**params,'snapshot':json.dumps(snapshot)})


def test_legacy_publication_retains_run_fk_and_can_replace_assessment_publication(ctx):
    from src.malaria_dl.governance.services.stage2_publication_service import Stage2PublicationService
    c,service,_,_=ctx
    training,_,model=candidate(ctx)
    service.activate(training,actor='test')
    training,_,model=candidate(ctx)
    repository.register_evidence(c,{'training_run_id':training},model,model['input_contract'],model['path'])
    evaluation=uuid4()
    c.execute(text("INSERT INTO runs(id,run_type,status) VALUES(:id,'evaluation','completed')"),{'id':evaluation})
    c.execute(text("""INSERT INTO run_lineage(parent_run_id,child_run_id,relationship_type,model_version_id,checkpoint_artifact_id)
      VALUES(:train,:evaluation,'evaluates_checkpoint_from',:version,:artifact)"""),
      {'train':training,'evaluation':evaluation,'version':model['model_version_id'],'artifact':model['checkpoint_artifact_id']})
    @contextmanager
    def shared(): yield c
    result=Stage2PublicationService(shared).publish(model['model_version_id'],'test','legacy fixture',replace_existing=True)
    assert result['eligible']
    row=c.execute(text('SELECT evaluation_run_id,evaluation_attempt_id FROM stage2_model_publications WHERE is_active')).one()
    assert row==(evaluation,None)


def test_route_forwards_only_explicit_activation_and_replacement_request():
    from unittest.mock import Mock
    from types import SimpleNamespace
    from app.routes.governance import activate_cell_model
    from app.schemas.cell_activation import CellActivationRequest
    training=uuid4()
    service=Mock()
    service.activate.return_value={'training_run_id':training,'model_version_id':uuid4(),'deployment_id':uuid4(),
                                  'available_for_inference':True,'idempotent':False}
    result=activate_cell_model(training,CellActivationRequest(replace_existing=True),service,SimpleNamespace(username='test'))
    service.activate.assert_called_once_with(training,actor='test',replace_existing=True,reason='Activación para clasificación celular')
    assert result.available_for_inference


def test_activation_works_with_existing_runtime_role_privileges(ctx):
    c,service,resolver,_=ctx
    training,_,_=candidate(ctx)
    c.execute(text('SET LOCAL ROLE capstone_v2_runtime'))
    service.activate(training,actor='test')
    assert resolver.resolve().source_training_run_id==str(training)
