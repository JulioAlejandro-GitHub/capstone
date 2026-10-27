"""Registration contracts. Real database tests opt in to a disposable current-schema clone."""
from contextlib import contextmanager
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from src.malaria_dl.campaigns.contracts import CampaignError, canonical, digest
from src.malaria_dl.pretrained.contracts import (
    ARCHITECTURE, COMPONENTS, ORIGIN, PROTOCOL, PretrainedCompletionContractV1,
    configuration, framework_versions, validate_configuration, verify_components,
)
from src.malaria_dl.pretrained.repository import PretrainedRepository

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(os.getenv('BIOMEDCLIP_ORIGINAL_ROOT', str(Path.home() / '.cache/capstone-biomedclip-01b/original')))
CLIP = ASSETS / 'biomedclip' / ORIGIN['revision']
TEXT = ASSETS / 'text' / PROTOCOL['text_revision']
DATASET = 'd8c0cab5-09dd-597f-9de7-7ca01aee2ec2'


@pytest.fixture(scope='module')
def database():
    url = os.getenv('BIOMEDCLIP_TEST_DATABASE_URL')
    if not url:
        pytest.skip('Explicit disposable current-schema database required')
    parsed = make_url(url)
    assert parsed.database.startswith('biomedclip_01c1') and parsed.host == '127.0.0.1' and parsed.port == 55439
    engine = create_engine(url)
    @contextmanager
    def scope(readonly=False):
        with engine.begin() as c:
            if readonly:
                c.execute(text('SET TRANSACTION READ ONLY'))
            yield c
    repo = PretrainedRepository(scope)
    yield engine, repo
    engine.dispose()


def command(dataset=DATASET):
    return [sys.executable, '-m', 'src.register_pretrained', '--database-url-env', 'BIOMEDCLIP_TEST_DATABASE_URL',
            '--dataset-version-id', dataset, '--biomedclip-directory', str(CLIP), '--text-directory', str(TEXT)]


@pytest.fixture(scope='module')
def registered(database):
    result = subprocess.run(command(), cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    value = json.loads(result.stdout.splitlines()[-1])
    assert value['state'] == 'verified'
    return value


@pytest.fixture
def cfg(registered):
    return deepcopy(registered['configuration'])


@contextmanager
def writing(database):
    """Real global advisory ownership; all scientific mutations rolled back."""
    engine, _ = database
    owner = str(uuid4())
    with engine.connect() as c:
        tx = c.begin()
        c.execute(text('SELECT pg_advisory_xact_lock(120994,1)'))
        c.execute(text("UPDATE experiment_execution_gate SET owner=CAST(:owner AS uuid),db_pid=pg_backend_pid() WHERE singleton"), {'owner': owner})
        c.execute(text("SELECT set_config('capstone.execution_token',:o,true),set_config('capstone.train_owner',:o,true)"), {'o': owner})
        try:
            yield c, owner
        finally:
            tx.rollback()


def insert_run(c, cfg, model_id=None):
    cfg = deepcopy(cfg)
    cfg['framework_versions']['torch'] += '-negative-test-' + str(uuid4())
    run = str(uuid4())
    model = model_id or c.execute(text("SELECT id FROM models WHERE name='biomedclip_zero_shot'")).scalar_one()
    params = {'scientific_origin': cfg['scientific_origin'], 'pretrained_configuration': cfg, 'configuration_hash': digest(cfg)}
    c.execute(text("INSERT INTO runs(id,model_id,run_type,status,dataset_version_id,execution_parameters) "
                   "VALUES(:run,:model,'training','running',:dataset,CAST(:p AS jsonb))"),
              {'run': run, 'model': model, 'dataset': cfg['target_dataset']['dataset_version_id'], 'p': canonical(params)})
    return run, cfg


def insert_session(c, owner, run, cfg):
    c.execute(text("INSERT INTO train_execution_sessions(run_id,owner,host,parent_pid,configuration,dataset,environment,artifact_root) "
                   "VALUES(:run,:owner,'isolated-negative',1,CAST(:cfg AS jsonb),CAST(:dataset AS jsonb),'{}',:root)"),
              {'run': run, 'owner': owner, 'cfg': canonical(cfg), 'dataset': canonical(cfg['target_dataset']),
               'root': str(ROOT / 'outputs/train_runs' / run)})


def test_catalog_visible_disabled_and_presets(database, monkeypatch):
    from src.malaria_dl.models import registry
    from src.malaria_dl.campaigns import configuration as cc
    with database[0].connect() as c:
        rows = tuple(dict(r) for r in c.execute(text('SELECT name,architecture,model_type,framework FROM models ORDER BY name')).mappings())
    monkeypatch.setattr(registry, 'model_catalog', lambda: rows)
    cat = cc.catalog()
    model = next(m for m in cat['models'] if m['id'] == ARCHITECTURE)
    assert model['trainable'] is False and model['disabled_reason'] == 'No requiere entrenamiento local'
    assert model['optimizers'] == [] and model['parameters'] == []
    assert {m['id'] for m in cat['models'] if m['trainable']} == {'custom_cnn','vgg16','densenet121'}
    for preset in cat['presets']:
        assert ARCHITECTURE not in preset['configuration']['models']
        assert cc.normalize(preset['configuration'])[1] == []
    bad = deepcopy(cat['presets'][0]['configuration'])
    bad['models'].append(ARCHITECTURE)
    assert any(e['code'] == 'MODEL_NOT_TRAINABLE:' + ARCHITECTURE for e in cc.normalize(bad)[1])
    with pytest.raises(ValueError, match='MODEL_NOT_EXECUTABLE'):
        registry.resolve_descriptor(ARCHITECTURE)


def test_train_skips_and_continues_without_registration(monkeypatch, capsys):
    from src.malaria_dl.execution import operations
    base = dict(id=str(uuid4()), dataset_version_id=DATASET, campaign_id=None)
    zero = dict(base, model_name=ARCHITECTURE, configuration=None)
    config = {'model_id':'custom_cnn','schema_version':'test','adapter_version':'test',
              'resolved':dict.fromkeys(('model','optimizer','execution','selection','input_contract','recipe'), {})}
    trained = dict(base, id=str(uuid4()), model_name='custom_cnn', configuration=config)
    monkeypatch.setattr(operations, 'select_trainings', lambda *a: [zero,trained])
    plan = operations.training_plan(object(), None, base['id'])
    assert len(plan) == 1 and plan[0]['source_training_run_id'] == trained['id']
    assert 'No requiere entrenamiento local' in capsys.readouterr().out
    monkeypatch.setattr(operations, 'select_trainings', lambda *a: [zero])
    assert operations.training_plan(object(), None, base['id']) == []
    from src.malaria_dl.execution.train import standalone
    from types import SimpleNamespace
    assert standalone(SimpleNamespace(model=ARCHITECTURE)) == {'state':'omitted'}


def test_real_lineage_completion_recovery_no_learning(database, registered):
    engine, repo = database
    run = registered['run_id']
    recovered = repo.recover(run)
    assert recovered['configuration'] == registered['configuration']
    assert recovered['configuration']['scientific_origin'] == ORIGIN
    with engine.connect() as c:
        r = c.execute(text('SELECT * FROM runs WHERE id=:r'), {'r':run}).mappings().one()
        assert r['run_type'] == 'training' and r['status'] == 'completed'
        assert all(r[k] is None for k in ('max_epochs','total_epochs','best_epoch','checkpoint_monitor','early_stopping_enabled'))
        for table in ('train_execution_records','training_history','run_configurations','assessment_identities'):
            column = 'training_run_id' if table == 'assessment_identities' else 'run_id'
            assert c.execute(text(f'SELECT count(*) FROM {table} WHERE {column}=:r'), {'r':run}).scalar_one() == 0
        artifacts = c.execute(text('SELECT * FROM artifacts WHERE run_id=:r'), {'r':run}).mappings().all()
        assert len(artifacts) == 5 and {a['metadata']['component'] for a in artifacts} == set(COMPONENTS)
        v = c.execute(text('SELECT * FROM model_versions WHERE id=:v'), {'v':registered['model_version_id']}).mappings().one()
        assert str(v['training_run_id']) == run and str(v['checkpoint_artifact_id']) == registered['artifact_id']
        assert str(v['model_id']) == registered['model_id'] and v['status'] == 'candidate'
        s = c.execute(text('SELECT * FROM train_execution_sessions WHERE run_id=:r'), {'r':run}).mappings().one()
        assert s['state'] == 'verified' and s['completion']['schema'] == 'pretrained_completion_v1'
        assert 'epochs' not in s['completion'] and 'selection' not in s['completion']
        assert c.execute(text('SELECT pretrained_completion_valid(:r,CAST(:v AS jsonb))'),
                         {'r':run,'v':canonical(s['completion'])}).scalar_one()
    assert verify_components(recovered['artifact_root']) == COMPONENTS


def test_idempotent_and_concurrent_real_registration(database, registered):
    # A fresh target version exercises simultaneous first creation, not just two reads.
    env = dict(os.environ)
    env['BIOMEDCLIP_TEST_DATABASE_URL'] = os.environ['BIOMEDCLIP_CONCURRENT_DATABASE_URL']
    parallel_engine = create_engine(env['BIOMEDCLIP_TEST_DATABASE_URL'])
    assert make_url(env['BIOMEDCLIP_TEST_DATABASE_URL']).database.startswith('biomedclip_01c1')
    with parallel_engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM runs WHERE execution_parameters ? 'scientific_origin'")).scalar_one() == 0
    a = subprocess.Popen(command(), cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    b = subprocess.Popen(command(), cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    outputs = []
    for p in (a,b):
        out, err = p.communicate(timeout=120)
        assert p.returncode == 0, out + err
        outputs.append(json.loads(out.splitlines()[-1]))
    assert outputs[0]['run_id'] == outputs[1]['run_id']
    assert {v['reused'] for v in outputs} == {False, True}
    with parallel_engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM runs WHERE execution_parameters->>'configuration_hash'=:h"),
                         {'h':outputs[0]['configuration_hash']}).scalar_one() == 1
    parallel_engine.dispose()
    repeated = subprocess.run(command(), cwd=ROOT, capture_output=True, text=True)
    assert repeated.returncode == 0, repeated.stdout + repeated.stderr
    value = json.loads(repeated.stdout.splitlines()[-1])
    assert value['run_id'] == registered['run_id'] and value['reused'] is True


@pytest.mark.parametrize('path,value', [
    (('scientific_origin','revision'),'main'),
    (('scientific_origin','architecture'),'custom_cnn'),
    (('inference','prompts'),['only one prompt']),
    (('inference','positive_class'),0),
    (('inference','tokenizer','revision'),'main'),
    (('inference','components','open_clip_pytorch_model.bin','sha256'),'0'*64),
    (('inference','threshold','value'),0.7),
    (('inference','embedding','dimension'),768),
])
def test_reject_protocol_mutation_python_and_sql(database, cfg, path, value):
    node = cfg
    for key in path[:-1]: node = node[key]
    node[path[-1]] = value
    with pytest.raises(CampaignError): validate_configuration(cfg)
    with writing(database) as (c, _):
        with pytest.raises(DBAPIError, match='PRETRAINED_CONFIGURATION_INVALID'):
            insert_run(c,cfg)


def test_missing_configuration_and_invalid_dataset(database, cfg):
    cfg.pop('inference')
    with pytest.raises(CampaignError, match='INCOMPLETE'): validate_configuration(cfg)
    with writing(database) as (c, _):
        with pytest.raises(DBAPIError): insert_run(c,cfg)
    with pytest.raises(Exception, match='DATASET_VERSION_NOT_FOUND'):
        database[1].resolve_dataset(str(uuid4()))


def test_trainable_cannot_spoof_zero_shot(database, cfg):
    with writing(database) as (c, _):
        model = c.execute(text("SELECT id FROM models WHERE name='custom_cnn'")).scalar_one()
        with pytest.raises(DBAPIError, match='PRETRAINED_CONFIGURATION_INVALID'):
            insert_run(c,cfg,model)


@pytest.mark.parametrize('completion', [{'epochs':1,'records_hash':'a'*64}, {}, {'schema':'pretrained_completion_v1'}])
def test_reject_fake_completion(database, cfg, completion):
    with pytest.raises(CampaignError): PretrainedCompletionContractV1.from_dict(completion)
    with writing(database) as (c, owner):
        run, config = insert_run(c,cfg)
        insert_session(c,owner,run,config)
        with pytest.raises(DBAPIError):
            c.execute(text("UPDATE train_execution_sessions SET state='completed',completion=CAST(:v AS jsonb) WHERE run_id=:r"),
                      {'v':canonical(completion),'r':run})


def test_owner_fencing_and_verified_without_evidence(database, cfg):
    with writing(database) as (c, owner):
        run, config = insert_run(c,cfg)
        insert_session(c,owner,run,config)
        c.execute(text("SELECT set_config('capstone.train_owner',:o,true)"), {'o':str(uuid4())})
        with pytest.raises(DBAPIError, match='TRAIN_OWNER_FENCED'):
            c.execute(text("UPDATE train_execution_sessions SET state='verified',completion='{}',verification='{}' WHERE run_id=:r"), {'r':run})
    with writing(database) as (c, owner):
        run, config = insert_run(c,cfg)
        insert_session(c,owner,run,config)
        with pytest.raises(DBAPIError, match='TRAIN_TRANSITION_INVALID'):
            c.execute(text("UPDATE train_execution_sessions SET state='verified',completion='{}',verification='{}' WHERE run_id=:r"), {'r':run})


def test_commit_requires_complete_registration_and_conventional_config(database, cfg):
    with writing(database) as (c, _):
        insert_run(c,cfg)
        with pytest.raises(DBAPIError, match='PRETRAINED_REGISTRATION_INCOMPLETE'):
            c.execute(text('SET CONSTRAINTS ALL IMMEDIATE'))
    with writing(database) as (c, _):
        c.execute(text("INSERT INTO runs(run_type,status) VALUES('training','running')"))
        with pytest.raises(DBAPIError, match='TRAIN_CONFIGURATION_REQUIRED'):
            c.execute(text('SET CONSTRAINTS ALL IMMEDIATE'))


@pytest.mark.parametrize('operation', [
    "UPDATE runs SET execution_parameters=execution_parameters-'scientific_origin' WHERE id=:r",
    "UPDATE artifacts SET metadata='{}' WHERE run_id=:r",
    "UPDATE model_versions SET metadata='{}' WHERE training_run_id=:r",
    "UPDATE model_versions SET model_id=(SELECT id FROM models WHERE name='custom_cnn') WHERE training_run_id=:r",
    "UPDATE artifacts SET run_id=(SELECT id FROM runs WHERE id<>:r LIMIT 1) WHERE run_id=:r",
    "DELETE FROM train_execution_sessions WHERE run_id=:r",
    "DELETE FROM artifacts WHERE run_id=:r",
    "DELETE FROM model_versions WHERE training_run_id=:r",
])
def test_registered_origin_immutable(database, registered, operation):
    with writing(database) as (c, _):
        with pytest.raises(DBAPIError):
            c.execute(text(operation), {'r':registered['run_id']})


def test_version_wrong_model_and_artifact_wrong_owner(database, cfg, registered):
    with writing(database) as (c, owner):
        run, config = insert_run(c,cfg)
        insert_session(c,owner,run,config)
        with pytest.raises(DBAPIError, match='PRETRAINED_VERSION_BINDING_INVALID'):
            c.execute(text("INSERT INTO model_versions(model_id,training_run_id,checkpoint_artifact_id,status,artifact_sha256) "
                           "VALUES((SELECT id FROM models WHERE name='custom_cnn'),:r,:a,'candidate',:h)"),
                      {'r':run,'a':registered['artifact_id'],'h':COMPONENTS[PROTOCOL['checkpoint']]['sha256']})
    with writing(database) as (c, _):
        conventional = c.execute(text("SELECT id FROM runs WHERE execution_parameters ? 'scientific_origin'=false LIMIT 1")).scalar_one()
        with pytest.raises(DBAPIError, match='PRETRAINED_ARTIFACT_OWNER_INVALID'):
            c.execute(text("INSERT INTO artifacts(run_id,artifact_type,path,metadata) VALUES(:r,'model_checkpoint','bad',CAST(:m AS jsonb))"),
                      {'r':conventional,'m':canonical({'scientific_origin':ORIGIN})})


def test_missing_and_changed_binary(tmp_path):
    with pytest.raises(CampaignError, match='CHECKPOINT_NOT_FINALIZED'): verify_components(tmp_path)
    (tmp_path / PROTOCOL['checkpoint']).write_bytes(b'not the original checkpoint')
    with pytest.raises(CampaignError, match='IDENTITY_MISMATCH'): verify_components(tmp_path)


def test_wrong_tokenizer_rejected_real_checkpoint(tmp_path, registered):
    # APFS clone (independent inode/data on write); never mutate the registered original.
    copy = tmp_path / 'copy'
    subprocess.run(['cp','-cR',registered['artifact_root'],str(copy)],check=True)
    vocab = copy / 'text/vocab.txt'
    vocab.chmod(0o644)
    vocab.write_text('wrong tokenizer')
    with pytest.raises(CampaignError, match='text/vocab.txt'): verify_components(copy)


def test_sql_failure_rolls_back_whole_registration(database, cfg, monkeypatch):
    from src.malaria_dl.pretrained import repository as module
    engine, repo = database
    original = module.execute
    failed_run = []
    def fail(c, statement, **params):
        if statement.startswith('INSERT INTO runs'): failed_run.append(params['id'])
        if statement.startswith('INSERT INTO model_versions'):
            return c.execute(text('SELECT * FROM deliberately_nonexistent_registration_table'))
        return original(c,statement,**params)
    # The outer transaction owns the real gate; repo's scope reuses it so rollback is exercised.
    with writing(database) as (c, owner):
        @contextmanager
        def scope(readonly=False):
            with c.begin_nested(): yield c
        local = PretrainedRepository(scope)
        monkeypatch.setattr(module,'execute',fail)
        cfg['framework_versions']['torch'] += '-rollback-test'
        with pytest.raises(Exception):
            local.register(config=cfg,biomedclip_directory=CLIP,text_directory=TEXT,owner=owner)
        assert failed_run
        for table,column in [('runs','id'),('train_execution_sessions','run_id'),('artifacts','run_id'),('model_versions','training_run_id')]:
            assert c.execute(text(f'SELECT count(*) FROM {table} WHERE {column}=:r'), {'r':failed_run[0]}).scalar_one() == 0


def test_no_implicit_assessment_support(database, registered):
    from src.malaria_dl.execution.artifacts import verify_session
    session = database[1].session(registered['run_id'])
    with pytest.raises(CampaignError, match='PRETRAINED_ASSESSMENT_NOT_IMPLEMENTED'):
        verify_session(database[1], session, lambda *a: pytest.fail('Keras loader must not run'))


def test_train_entry_only_zero_leaves_database_unchanged(database, registered, monkeypatch, capsys):
    from src.malaria_dl.execution import operations, local_launch
    monkeypatch.setattr(local_launch, 'bootstrap', lambda: None)
    monkeypatch.setattr(operations, 'ExecutionRepository', lambda: database[1])
    with database[0].connect() as c:
        before = c.execute(text('SELECT count(*) FROM runs')).scalar_one()
    assert operations.main(['--source-training-run-id', registered['run_id']]) == 0
    assert 'No requiere entrenamiento local' in capsys.readouterr().out
    with database[0].connect() as c:
        assert c.execute(text('SELECT count(*) FROM runs')).scalar_one() == before


def test_legacy_train_arguments_allow_omission(database, monkeypatch):
    from src.malaria_dl.models import registry
    from src.malaria_dl.training.cli import parse_args
    with database[0].connect() as c:
        rows = tuple(dict(r) for r in c.execute(text('SELECT name,architecture,model_type,framework FROM models')).mappings())
    monkeypatch.setattr(registry,'model_catalog',lambda:rows)
    args = parse_args(['--model',ARCHITECTURE,'--dataset-version-id',DATASET])
    assert args.model == ARCHITECTURE and args.model_configuration is None


@pytest.mark.parametrize('kind', ['missing_checkpoint','changed_checkpoint','changed_tokenizer'])
def test_invalid_source_cli_no_partial_success(database, registered, tmp_path, kind):
    args = command()
    if kind == 'changed_tokenizer':
        target = tmp_path / 'text'
        target.mkdir()
        for p in TEXT.iterdir():
            if p.is_file(): (target / p.name).write_bytes(p.read_bytes())
        (target / 'vocab.txt').write_text('invalid vocabulary')
        args[args.index('--text-directory')+1] = str(target)
    else:
        args[args.index('--biomedclip-directory')+1] = str(tmp_path)
        if kind == 'changed_checkpoint':
            (tmp_path / PROTOCOL['checkpoint']).write_bytes(b'corrupted')
    with database[0].connect() as c:
        before = c.execute(text('SELECT count(*) FROM runs')).scalar_one()
    result = subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
    assert result.returncode == 2
    assert json.loads(result.stdout.splitlines()[-1])['state'] == 'failed'
    with database[0].connect() as c:
        assert c.execute(text('SELECT count(*) FROM runs')).scalar_one() == before


def test_zero_cannot_insert_learning_evidence(database, registered):
    with writing(database) as (c,_):
        with pytest.raises(DBAPIError,match='PRETRAINED_LEARNING_EVIDENCE_FORBIDDEN'):
            c.execute(text("INSERT INTO training_history(run_id,epoch,loss) VALUES(:r,1,.1)"),{'r':registered['run_id']})


def test_session_insertion_requires_owner(database, cfg):
    with writing(database) as (c, owner):
        run, config = insert_run(c,cfg)
        with pytest.raises(DBAPIError,match='PRETRAINED_SESSION_INVALID'):
            insert_session(c,str(uuid4()),run,config)


def test_python_sql_protocols_are_exact(database):
    with database[0].connect() as c:
        assert c.execute(text('SELECT pretrained_protocol_v1()')).scalar_one() == PROTOCOL
        assert c.execute(text('SELECT pretrained_origin_v1()')).scalar_one() == ORIGIN
    original = json.loads((CLIP / 'open_clip_config.json').read_text())
    assert PROTOCOL['text_pooling'] == original['model_cfg']['text_cfg']['hf_pooler_type']
    assert PROTOCOL['visual_encoder'] == original['model_cfg']['vision_cfg']['timm_model_name']
    assert PROTOCOL['embedding']['dimension'] == original['model_cfg']['embed_dim']


def test_conventional_session_still_requires_epochs(database):
    with writing(database) as (c, owner):
        run = str(uuid4())
        c.execute(text("INSERT INTO runs(id,run_type,status) VALUES(:r,'training','running')"), {'r':run})
        c.execute(text("INSERT INTO train_execution_sessions(run_id,owner,host,parent_pid,configuration,dataset,environment,artifact_root) "
                       "VALUES(:r,:o,'conventional-test',1,'{}','{}','{}',:root)"),
                  {'r':run,'o':owner,'root':'/synthetic/' + run})
        completion = {'epochs':0,'records_hash':digest([])}
        c.execute(text("UPDATE train_execution_sessions SET state='completed',completion=CAST(:v AS jsonb) WHERE run_id=:r"),
                  {'r':run,'v':canonical(completion)})
        with pytest.raises(DBAPIError,match='TRAIN_VERIFICATION_INCOMPLETE'):
            c.execute(text("UPDATE train_execution_sessions SET state='verified',verification=CAST(:v AS jsonb) WHERE run_id=:r"),
                      {'r':run,'v':canonical({'status':'verified','records_hash':digest([])})})


def test_conventional_session_guard_accepts_matching_epoch_evidence(database):
    # Synthetic rollback-only guard probe; no real learning is claimed.
    with writing(database) as (c, owner):
        run = str(uuid4())
        c.execute(text("INSERT INTO runs(id,run_type,status) VALUES(:r,'training','running')"), {'r':run})
        c.execute(text("INSERT INTO train_execution_sessions(run_id,owner,host,parent_pid,configuration,dataset,environment,artifact_root) "
                       "VALUES(:r,:o,'conventional-test',1,'{}','{}','{}',:root)"),
                  {'r':run,'o':owner,'root':'/synthetic/' + run})
        for kind in ('epoch','artifact'):
            c.execute(text("INSERT INTO train_execution_records(run_id,kind,phase,record_key,payload) VALUES(:r,:k,'base','1','{}')"),
                      {'r':run,'k':kind})
        c.execute(text("UPDATE train_execution_sessions SET state='completed',completion=CAST(:v AS jsonb) WHERE run_id=:r"),
                  {'r':run,'v':canonical({'epochs':1,'records_hash':'a'*64})})
        c.execute(text("UPDATE train_execution_sessions SET state='verified',verification=CAST(:v AS jsonb) WHERE run_id=:r"),
                  {'r':run,'v':canonical({'status':'verified','records_hash':'a'*64})})
        assert c.execute(text('SELECT state FROM train_execution_sessions WHERE run_id=:r'),{'r':run}).scalar_one() == 'verified'


def test_train_main_continues_trainable_sources(monkeypatch, capsys):
    from src.malaria_dl.execution import operations, local_launch, train
    source = str(uuid4())
    config = {'model_id':'custom_cnn','schema_version':'test','adapter_version':'test',
              'resolved':dict.fromkeys(('model','optimizer','execution','selection','input_contract','recipe'), {})}
    rows = [dict(id=str(uuid4()),model_name=ARCHITECTURE,configuration=None),
            dict(id=source,model_name='custom_cnn',configuration=config,campaign_id=None,dataset_version_id=DATASET)]
    monkeypatch.setattr(local_launch,'bootstrap',lambda:None)
    monkeypatch.setattr(operations,'select_trainings',lambda *a:rows)
    called=[]
    def execute_train(args):
        called.append(args.model)
        return {'run_id':str(uuid4()),'state':'verified'}
    monkeypatch.setattr(train,'standalone',execute_train)
    monkeypatch.setattr(PretrainedRepository,'register',lambda *a,**k:pytest.fail('TRAIN must never register an origin'))
    assert operations.main(['--source-training-run-id',source]) == 0
    assert called == ['custom_cnn'] and 'No requiere entrenamiento local' in capsys.readouterr().out
