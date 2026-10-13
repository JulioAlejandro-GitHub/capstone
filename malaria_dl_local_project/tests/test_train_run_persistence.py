"""P1: synthetic TRAIN, PostgreSQL savepoints and outer rollback; no real fit."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from src.malaria_dl.execution.repository import ExecutionRepository
from src.malaria_dl.execution.artifacts import verify_session
from src.malaria_dl.execution.contracts import ExecutionContext, ExecutionMode, RunEventType
from src.malaria_dl.execution.emitter import RunEventEmitter
from src.malaria_dl.execution.train import train
from src.malaria_dl.persistence.result_repository import _PostgresScope, _decode
from src.malaria_dl.results.models import AcceptanceState
from src.malaria_dl.results.service import ResultService
from test_campaigns_postgres import isolated  # noqa: F401
from test_result_repository_postgres import apply
from e10_schema_fixture import install_e10
from docker_train_fixture import install_science

pytestmark = pytest.mark.requires_docker_postgres

RUNTIME = dict(host='synthetic-worker', python='3.12.13', tensorflow='2.20.0',
               packages={'keras': '3.11.0'}, git_commit='a' * 40,
               platform='Darwin', machine='arm64', execution_mode='local_python')


@pytest.fixture
def training(isolated, tmp_path):
    x = isolated
    for revision in ('20260912_01_train_execution', '20260912_02_assessments',
                     '20260914_01_controlled_train', '20260914_02_global_execution',
                     '20260915_01_local_execution'):
        apply(x.c, revision)
    install_e10(x.c)
    from test_campaigns_e4 import request, protocol
    requested = request()
    requested['models'] = ['vgg16']
    requested['variants'][0]['selected'] = {'execution': {'fine_tune_epochs': 2}}
    campaign = x.service.create(name='P1 rollback', purpose='synthetic persistence test',
        dataset_version_id=x.dataset['dataset_version_id'], request=requested,
        protocol=protocol(), actor='synthetic-test')
    campaign = x.service.freeze(str(campaign['id']))
    token = uuid4()
    x.c.execute(text("""INSERT INTO local_execution_jobs
        (id,principal,agent_id,owner,request_hash,campaign_id,state)
        VALUES(:id,'p1-fixture',:agent,:owner,:hash,:campaign,'held')"""),
        dict(id=uuid4(), agent=uuid4(), owner=token, hash='a'*64, campaign=campaign['id']))
    x.c.execute(text('UPDATE experiment_execution_gate SET owner=:owner'), dict(owner=token))
    x.c.execute(text("SELECT set_config('capstone.execution_token',:token,true)"), dict(token=str(token)))
    dataset_id = uuid4()
    x.c.execute(text("INSERT INTO dataset_version_sources VALUES (:version,:dataset,'PRIMARY')"),
                dict(version=x.dataset['dataset_version_id'], dataset=dataset_id))
    repo = ExecutionRepository(x.repo.scope)
    session = repo.claim(str(campaign['id']), str(uuid4()), 'coordinator', 1, tmp_path,
                         observed_runtime=RUNTIME)
    return SimpleNamespace(x=x, repo=repo, session=session, dataset_id=dataset_id)


def run_row(t):
    return dict(t.x.c.execute(text('SELECT * FROM runs WHERE id=:id'),
                             dict(id=t.session['run_id'])).mappings().one())


def test_creation_preserves_scientific_configuration_and_worker_environment(training):
    t = training
    row = run_row(t)
    config = t.session['configuration']
    ex = config['resolved']['execution']
    selection = config['resolved']['selection']
    assert row['id'] == t.session['run_id']
    assert row['dataset_id'] == t.dataset_id
    assert str(row['dataset_version_id']) == t.session['dataset']['dataset_version_id']
    assert str(row['model_id']) == t.x.models[config['model_id']]
    assert row['campaign_id'] is not None
    assert row['experiment_id'] is None
    assert row['run_type'] == 'training' and row['status'] == 'running'
    assert row['random_seed'] == ex['seed']
    assert row['max_epochs'] == ex['max_epochs']
    assert row['total_epochs'] == ex['max_epochs'] + ex['fine_tune_epochs']
    assert row['checkpoint_monitor'] == selection['monitor']
    assert row['checkpoint_mode'] == selection['mode']
    assert row['early_stopping_enabled'] == ex['early_stopping']
    assert row['early_stopping_patience'] == ex['early_stopping_patience']
    assert row['early_stopping_min_delta'] == ex['early_stopping_min_delta']
    assert row['restore_best_weights'] == ex['restore_best_weights']
    assert row['execution_parameters']['model_configuration_e2']['configuration'] == config
    assert row['execution_parameters']['runtime_environment'] == RUNTIME
    assert row['python_version'] == RUNTIME['python'] != t.session['environment']['python']
    assert row['host_name'] == RUNTIME['host']
    assert row['tensorflow_version'] == RUNTIME['tensorflow']
    assert row['keras_version'] == RUNTIME['packages']['keras']
    assert row['execution_type'] == 'local_python'
    assert row['git_commit'] == RUNTIME['git_commit']
    assert row['platform'] == 'Darwin' and row['machine'] == 'arm64'


def test_completion_and_two_verifications_preserve_results(training, monkeypatch):
    t = training
    descriptor, trace = install_science(monkeypatch, first_epoch_best=True)
    monkeypatch.setattr('src.malaria_dl.execution.campaign.runtime_environment', lambda: RUNTIME)
    # The actual TRAIN orchestration emits two completed epochs per phase, with
    # deterministic science doubles. No TensorFlow training or TEST/EXPLAIN runs.
    train(t.repo, t.session, descriptor)
    before = run_row(t)
    records = t.repo.records(t.session['run_id'])
    epochs = [r for r in records if r['kind'] == 'epoch']
    current = t.repo.session(t.session['run_id'])
    selection = current['completion']['selection']
    assert before['completed_epochs'] == len(epochs)
    assert before['best_epoch'] == selection['selected_epoch']
    assert before['best_epoch'] < before['completed_epochs'] == 4
    assert before['best_validation_value'] == selection['selected_metric_value']
    fine = [r['payload']['epoch'] for r in epochs if r['phase'] == 'fine_tuning']
    assert before['fine_tuning_start_epoch'] == (min(fine)-1 if fine else None)
    assert before['stopped_epoch'] == (len(epochs) if before['early_stopping_enabled'] else None)
    assert before['finished_at'] == datetime.fromisoformat(current['completion']['finished_at'])
    elapsed = before['finished_at'] - before['started_at']
    assert before['duration_seconds'] == Decimal(elapsed.days * 86400 + elapsed.seconds) + Decimal(elapsed.microseconds)/1000000
    assert before['status'] == 'completed' and before['error_message'] is None
    attempt_before = t.x.c.execute(text('SELECT finished_at FROM campaign_attempts WHERE id=:id'),
                                  dict(id=t.session['attempt_id'])).scalar_one()
    for _ in range(2):
        current = t.repo.session(t.session['run_id'])
        proof = verify_session(t.repo, current, lambda *args: None)
        t.repo.finish(current['run_id'], current['owner'], 'verified', proof)
        assert run_row(t) == before
        assert t.x.c.execute(text('SELECT finished_at FROM campaign_attempts WHERE id=:id'),
                            dict(id=t.session['attempt_id'])).scalar_one() == attempt_before
    assert t.repo.session(current['run_id'])['state'] == 'verified'


def test_late_runtime_event_and_duplicate_are_atomic(training):
    t = training
    started = datetime.now(timezone.utc) - timedelta(seconds=5, microseconds=123456)
    context = ExecutionContext(run_id=t.session['run_id'], owner=t.session['owner'],
        attempt_id=t.session['attempt_id'], execution_mode=ExecutionMode.LOCAL_PYTHON,
        dataset_version_id=UUID(t.session['dataset']['dataset_version_id']),
        model_id=t.session['configuration']['model_id'],
        adapter_version=t.session['configuration']['adapter_version'])

    class RollbackRepository:
        @contextmanager
        def acceptance_scope(self, ctx, event):
            with t.x.repo.scope() as c:
                t.repo.authorize(c, ctx.owner)
                old = c.execute(text('SELECT * FROM train_execution_records WHERE event_id=:id'),
                                dict(id=event.event_id)).mappings().one_or_none()
                last = c.execute(text('SELECT coalesce(max(event_sequence),0) FROM train_execution_records WHERE run_id=:id'),
                                 dict(id=ctx.run_id)).scalar_one()
                scope = _PostgresScope(c, event, AcceptanceState(existing_event=_decode(old),
                    sequence_event=None, last_sequence=int(last)))
                scope.revision = '20260922_01'
                yield scope
                scope.active = False

    service = ResultService(RollbackRepository())
    reporter = SimpleNamespace(report=lambda event: service.accept_event(context, event))
    emitter = RunEventEmitter(reporter, run_id=context.run_id, attempt_id=context.attempt_id)
    event = emitter.emit(RunEventType.PHASE_STARTED, {'result': dict(phase='base', callbacks=[],
        runtime_environment=dict(RUNTIME, host='actual-child'), started_at=started.isoformat())})
    before = run_row(t)
    reporter.report(event)
    assert run_row(t) == before
    assert before['started_at'] == started and before['host_name'] == 'actual-child'
    assert len(t.repo.result_events(context.run_id)) == 1
    assert t.repo.records(context.run_id) == []


def test_v2_creation_uses_real_constraints_and_rolls_back(training):
    """Only new UUIDs in public, all writes rolled back; existing rows are read only."""
    from src.malaria_dl.persistence.database import get_engine
    from copy import deepcopy
    engine = get_engine()
    run, dataset, version, experiment = (uuid4() for _ in range(4))
    try:
        with engine.connect() as c:
            transaction = c.begin()
            try:
                c.execute(text("INSERT INTO datasets(id,name) VALUES(:id,'P1 rollback fixture')"), dict(id=dataset))
                c.execute(text("""INSERT INTO dataset_versions
                    (id,name,semantic_version,grouping_strategy,grouping_field,stratification_strategy,
                     split_algorithm,split_algorithm_version,random_seed,target_train_ratio,target_val_ratio,
                     target_test_ratio,positive_class)
                    VALUES(:id,'P1 rollback fixture','test','patient','patient','class','synthetic','test',11,.7,.15,.15,'parasitized')"""), dict(id=version))
                c.execute(text("INSERT INTO dataset_version_sources VALUES(:version,:dataset,'PRIMARY',now())"),
                          dict(version=version, dataset=dataset))
                c.execute(text("INSERT INTO experiments(id,name) VALUES(:id,'P1 rollback fixture')"), dict(id=experiment))
                config = deepcopy(training.session['configuration'])
                snapshot = dict(training.session['dataset'], dataset_version_id=str(version))
                ExecutionRepository._create_run(c, str(run), config, snapshot,
                    training.session['environment'], experiment=experiment, runtime=RUNTIME)
                c.execute(text('SET CONSTRAINTS ALL IMMEDIATE'))
                row = c.execute(text('SELECT * FROM runs WHERE id=:id'), dict(id=run)).mappings().one()
                typed = c.execute(text('SELECT * FROM run_configurations WHERE run_id=:id'), dict(id=run)).mappings().one()
                assert row['experiment_id'] == experiment and row['dataset_id'] == dataset
                assert row['configuration'] is None
                assert row['gpu_available'] is None and row['gpu_devices'] == []
                assert row['peak_cpu_memory_bytes'] is None and row['peak_gpu_memory_bytes'] is None
                assert row['random_seed'] == typed['random_seed']
                assert row['max_epochs'] == typed['max_epochs']
                assert row['checkpoint_monitor'] == typed['checkpoint_monitor']
                assert typed['provenance_snapshot'] == config
            finally:
                transaction.rollback()
        with engine.connect() as c:
            assert c.execute(text('SELECT count(*) FROM runs WHERE id=:id'), dict(id=run)).scalar_one() == 0
            assert c.execute(text('SELECT count(*) FROM datasets WHERE id=:id'), dict(id=dataset)).scalar_one() == 0
    finally:
        engine.dispose()


def test_selected_artifact_retains_run_attempt_and_selection(training, monkeypatch):
    from src.malaria_dl.execution import schema
    from src.malaria_dl.execution.artifacts import file_identity
    t = training
    t.x.c.execute(text('CREATE TABLE artifacts (LIKE public.artifacts INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES)'))
    descriptor, _ = install_science(monkeypatch, first_epoch_best=True)
    original_finish = t.repo.finish

    def finish(run, owner, state, evidence=None, cause=None):
        # Exercise the v2 writer with synthetic campaign/session parents in this
        # rollback schema. The real v2 catalog gate is exercised separately above.
        with monkeypatch.context() as patch:
            patch.setattr(schema, 'require_e10_schema', lambda c: {'revision': schema.V2_REVISION})
            t.repo.bind_evaluation_context(run, owner, evidence['selection']['selected_epoch'])
        original_finish(run, owner, state, evidence, cause)

    monkeypatch.setattr(t.repo, 'finish', finish)
    train(t.repo, t.session, descriptor)
    row = t.x.c.execute(text('SELECT * FROM artifacts WHERE run_id=:id'),
                        dict(id=t.session['run_id'])).mappings().one()
    selection = t.repo.session(t.session['run_id'])['completion']['selection']
    assert row['metadata']['epoch'] == selection['selected_epoch'] < 4
    assert row['metadata']['attempt_id'] == str(t.session['attempt_id'])
    assert row['metadata']['selection'] == selection
    assert file_identity(row['path']) == dict(sha256=row['checksum'], bytes=row['file_size_bytes'])
    context = run_row(t)['execution_parameters']['e10_v2_evaluation_context_v1']
    assert context['checkpoint_artifact_id'] == str(row['id'])
