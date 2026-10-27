"""Current PostgreSQL contracts: atomic ingestion, technical activation and identity."""
import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID, uuid4

import numpy as np
import pytest
from sqlalchemy import create_engine, text

from src.malaria_dl.pretrained.registration import register_external_model
from src.malaria_dl.persistence.database import transaction_scope
from src.malaria_dl.execution.selection import select_trainings
from src.malaria_dl.campaigns.repository import CampaignRepository


@pytest.fixture
def db():
    url = os.getenv('CONTRACT_TEST_DATABASE_URL')
    if not url:
        pytest.skip('Requires a disposable database copied from the current schema')
    engine = create_engine(url)
    with engine.connect() as c, c.begin() as tx, transaction_scope(c):
        assert c.execute(text('SELECT current_database()')).scalar_one() == 'contract01b_test'
        yield c
        tx.rollback()
    engine.dispose()


@pytest.fixture
def spec(tmp_path):
    checkpoint = tmp_path/'model.keras';checkpoint.write_bytes(b'technical-test-checkpoint')
    return dict(name='external_'+uuid4().hex, model_type='zero_shot', framework='keras', architecture='test',
        metadata={'training_mode':'logical','scientific_origin':{'kind':'pretrained_external','repo_id':'test/external'}},
        files=[{'role':'checkpoint','path':str(checkpoint),'sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),'bytes':checkpoint.stat().st_size}],
        preprocessing={'mode':'rescale_0_1'},class_mapping={'0':'uninfected','1':'parasitized','positive_class':1,'positive_label':'parasitized'},
        input_signature={'shape':[None,8,8,3]},output_signature={'shape':[None,1],'activation':'sigmoid'})


def test_ingestion_idempotent_zero_epochs_and_common_training_lineage(db,spec):
    first=register_external_model(spec);second=register_external_model(spec)
    assert second == {**first,'idempotent':True}
    row=db.execute(text('SELECT * FROM runs WHERE id=:id'),{'id':first['run_id']}).mappings().one()
    assert row['run_type']=='training' and row['status']=='completed'
    assert row['total_epochs']==row['completed_epochs']==0
    assert row['metadata']['training_performed'] is False
    assert row['execution_parameters']['runtime_environment']['python_version']
    assert db.execute(text('SELECT count(*) FROM run_configurations WHERE run_id=:id'),{'id':first['run_id']}).scalar_one()==0
    assert not db.execute(text("SELECT 1 FROM pg_trigger WHERE tgrelid='public.runs'::regclass AND tgname='v2_run_configuration_required'")).first()
    @contextmanager
    def scope(readonly=False): yield db
    selected=select_trainings(CampaignRepository(scope),None,first['run_id'])
    assert selected[0]['model_metadata']['training_mode']=='logical'
    assert selected[0]['configuration'] is None
    assert db.execute(text('SELECT checkpoint_artifact_id::text FROM model_versions WHERE id=:id'),{'id':first['version_id']}).scalar_one()==first['artifact_id']


def test_invalid_bytes_do_not_register(db,spec):
    spec['files'][0]['sha256']='0'*64
    with pytest.raises(ValueError,match='identity mismatch'): register_external_model(spec)
    assert db.execute(text('SELECT count(*) FROM models WHERE name=:name'),spec).scalar_one()==0


def test_logical_mode_is_metadata_only(db,spec):
    spec['metadata'].pop('training_mode')
    with pytest.raises(ValueError,match='training_mode'): register_external_model(spec)


def test_conflicting_existing_metadata_is_not_overwritten(db,spec):
    first=register_external_model(spec)
    spec['metadata']['scientific_origin']['revision']='other'
    with pytest.raises(ValueError,match='conflicting metadata'): register_external_model(spec)
    assert 'revision' not in db.execute(text('SELECT metadata FROM models WHERE id=:id'),{'id':first['model_id']}).scalar_one()['scientific_origin']


def test_version_failure_rolls_back_entire_ingestion(db,spec,monkeypatch):
    from src.malaria_dl.pretrained import registration
    def fail(**kwargs): raise RuntimeError('synthetic version failure')
    monkeypatch.setattr(registration,'create_model_version',fail)
    with pytest.raises(RuntimeError,match='synthetic'), db.begin_nested(): register_external_model(spec)
    assert db.execute(text('SELECT count(*) FROM models WHERE name=:name'),spec).scalar_one()==0


class TransactionEngine:
    def __init__(self,c): self.c=c
    @contextmanager
    def begin(self):
        with self.c.begin_nested(): yield self.c
    @contextmanager
    def connect(self): yield self.c


class TechnicalModel:
    input_shape=(None,8,8,3)
    def predict(self,batch,verbose=0): return np.full((len(batch),1),.25,dtype=np.float32)


def activation_service(db,spec):
    from app.services.productive_model import ProductiveModelResolver
    from app.services.cell_activation import CellActivationService
    engine=TransactionEngine(db)
    resolver=ProductiveModelResolver(engine=engine,allowed_roots=[Path(spec['files'][0]['path']).parent],model_loader=lambda p:TechnicalModel())
    return CellActivationService(engine,resolver=resolver),resolver


def test_activation_without_evaluate_and_repeat(db,spec):
    result=register_external_model(spec)
    service,resolver=activation_service(db,spec)
    activated=service.activate(UUID(result['run_id']),actor='test')
    assert activated['available_for_inference']
    assert service.activate(UUID(result['run_id']),actor='test')['idempotent']
    assert service.enable(result['run_id'],actor='test',reason='test',confirm_stage2_enablement=True)['threshold_source']=='configured_decision'
    resolved=resolver.resolve()
    assert resolver.revalidate(resolved,connection=db).cache_key == resolved.cache_key
    assert resolved.source_evaluation_run_id is None
    assert resolved.threshold_source=='configured_decision'
    assert resolved.checkpoint_artifact_id==result['artifact_id']
    assert db.execute(text('SELECT count(*) FROM run_configurations')).scalar_one()==0


def test_activation_rejects_inaccessible_bytes_and_rolls_back(db,spec):
    result=register_external_model(spec)
    Path(spec['files'][0]['path']).unlink()
    service,_=activation_service(db,spec)
    from src.model_governance.errors import GovernanceStateError
    with pytest.raises(GovernanceStateError): service.activate(UUID(result['run_id']),actor='test')
    assert db.execute(text('SELECT count(*) FROM stage2_model_publications')).scalar_one()==0
    assert db.execute(text('SELECT count(*) FROM deployed_model_versions')).scalar_one()==0


def test_activation_rejects_unsupported_adapter(db,spec):
    spec['framework']='unsupported'
    result=register_external_model(spec)
    service,_=activation_service(db,spec)
    from src.model_governance.errors import GovernanceStateError
    with pytest.raises(GovernanceStateError): service.activate(UUID(result['run_id']),actor='test')
    assert db.execute(text('SELECT count(*) FROM deployed_model_versions')).scalar_one()==0


def test_activation_does_not_require_completed_training(db,spec):
    result=register_external_model(spec)
    db.execute(text("UPDATE runs SET status='running' WHERE id=:id"),{'id':result['run_id']})
    service,resolver=activation_service(db,spec)
    assert service.activate(UUID(result['run_id']),actor='test')['available_for_inference']
    assert resolver.revalidate(resolver.resolve(),connection=db).source_training_run_id==result['run_id']
