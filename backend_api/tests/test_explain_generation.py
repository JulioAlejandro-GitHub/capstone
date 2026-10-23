"""HTTP/orchestration contracts. These doubles do not certify scientific generation."""
from copy import deepcopy
from contextlib import nullcontext
from io import StringIO
from uuid import uuid4
from unittest.mock import Mock
import httpx
import pytest
from fastapi import FastAPI
from app.routes.explain_generation import router, get_service
from app.schemas.explain_generation import ExplainRequest
from app.security import Principal, Permission, current_principal
from app.services.explain_generation import ExplainService
from app.services.explain_launcher import ExplainLauncher
from app.services import explain_worker


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def setup():
    source_id, sample, dataset, training = [str(uuid4()) for _ in range(4)]
    value = {'model': {'training_run_id': training, 'checkpoint_artifact_id': str(uuid4())},
             'dataset': {'dataset_version_id': dataset}, 'samples': [{'sample_id': sample, 'sha256': 'a'*64}],
             'split': 'val', 'purpose': 'development', 'protocol': {'version': 'x'},
             'decision': {'requested': 'auto'}, 'seed': 42, 'batch_size': 1}
    repository = Mock()
    repository.source.return_value = {'identity': value}
    repository.samples.side_effect = lambda dataset, sample=None, limit=None, split='val': [sample or str(uuid4())]
    repository.candidates.return_value = []
    repository.requests_for.return_value = []
    service = ExplainService(repository)
    request = ExplainRequest(source_attempt_id=source_id, sample_id=sample, methods=['gradcam', 'lime', 'shap'])
    return service, request, value


@pytest.mark.parametrize('method', ['gradcam', 'lime', 'shap'])
def test_preparation_calls_canonical_single_cell_service(setup, monkeypatch, method):
    service, request, source = setup
    prepare = Mock(return_value=source)
    monkeypatch.setattr('app.services.explain_generation.prepare', prepare)
    service.prepare(request, source, method)
    kwargs = prepare.call_args.kwargs
    assert kwargs['sample_id'] == str(request.sample_id)
    assert kwargs['training_run_id'] == source['model']['training_run_id']
    assert 'max_images' not in kwargs
    assert kwargs['explanation']['method'] == method
    assert kwargs['explanation']['num_samples'] == (None if method == 'gradcam' else 1000)


def test_background_uses_canonical_first_val_without_target_filter(setup):
    service, request, source = setup
    background = str(uuid4())
    service.repository.samples.side_effect = lambda dataset, sample=None, limit=None, split='val': [sample or background]
    spec = service.specification(request, source, 'shap')
    assert spec['background'] == [background]
    assert background != str(request.sample_id)
    service.repository.samples.assert_any_call(source['dataset']['dataset_version_id'], limit=1, split='val')


def test_invalid_explicit_background_never_falls_back(setup):
    service, request, source = setup
    request.background_sample_id = uuid4()
    service.repository.samples.return_value = []
    service.repository.samples.side_effect = None
    with pytest.raises(ValueError, match='BACKGROUND_NOT_ACCREDITED'):
        service.specification(request, source, 'shap')
    assert service.repository.samples.call_count == 1


@pytest.mark.parametrize('key', ['model', 'dataset', 'split', 'purpose', 'protocol', 'decision'])
def test_context_mismatch_never_reuses(setup, key):
    service, request, source = setup
    spec = service.specification(request, source, 'gradcam')
    candidate = deepcopy(source)
    candidate['explanation'] = spec
    assert service.compatible({'identity': candidate}, source, request, spec)
    candidate[key] = 'foreign'
    assert not service.compatible({'identity': candidate}, source, request, spec)


def test_active_duplicate_returns_existing_without_start(setup):
    service, request, source = setup
    request.methods = ['gradcam']
    candidate = deepcopy(source)
    candidate['explanation'] = service.specification(request, source, 'gradcam')
    attempt = str(uuid4())
    service.repository.candidates.return_value = [{'id': attempt, 'state': 'active', 'identity': candidate}]
    launcher = Mock()
    for _ in range(2):
        assert service.submit(request, launcher, 'actor')['operations'][0]['attempt_id'] == attempt
    launcher.launch.assert_not_called()


def test_failed_attempt_is_retryable_and_historical_row_untouched(setup):
    service, request, source = setup
    request.methods = ['lime']
    candidate = deepcopy(source)
    candidate['explanation'] = service.specification(request, source, 'lime')
    row = {'id': str(uuid4()), 'state': 'failed', 'identity': candidate}
    service.repository.candidates.return_value = [row]
    launcher = Mock()
    service.submit(request, launcher, 'actor')
    launcher.launch.assert_called_once_with(request, 'actor')
    assert row['state'] == 'failed'


def test_whole_action_reserves_before_ack_and_keeps_partial_results(setup, monkeypatch):
    service, request, source = setup
    service.reusable = Mock(return_value=None)
    service.matching = Mock(return_value=[])
    service.prepare = Mock(side_effect=lambda request, source, method: {'method': method})
    gate = Mock()
    monkeypatch.setattr(explain_worker, 'GlobalGate', lambda _: nullcontext(gate))
    events = []
    def reserve(repo, value, root):
        events.append(('reserve', value['method']))
        return value, {'id': value['method'], 'owner': 'owner'}, True
    def execute(repo, value, attempt):
        events.append(('execute', value['method']))
        if value['method'] == 'lime':
            raise ValueError('method failed')
    monkeypatch.setattr(explain_worker, 'reserve_execution', reserve)
    monkeypatch.setattr(explain_worker, 'execute_reserved', execute)
    monkeypatch.setattr(explain_worker.sys, 'stdin', StringIO('START\n'))
    service.repository.attempt.return_value = {'state': 'verified'}
    output = StringIO()
    explain_worker.execute(request, service, output, 'actor')
    assert events == [event for method in request.methods for event in [('reserve', method), ('execute', method)]]
    assert all(m in output.getvalue() for m in request.methods)
    gate.event.assert_any_call('http_explain_failed', method='lime', code='EXPLAIN_EXECUTOR_FAILED')


@pytest.mark.anyio
@pytest.mark.parametrize('allowed,status', [(True, 202), (False, 403)])
async def test_generation_http_authorization(setup, allowed, status, monkeypatch):
    service, request, _ = setup
    engine = Mock()
    engine.begin.return_value = nullcontext(Mock())
    monkeypatch.setattr('app.audit.get_primary_engine', lambda: engine)
    service.submit = Mock(return_value={'operations': [{'method': 'gradcam', 'attempt_id': str(uuid4())}]})
    app = FastAPI(); app.include_router(router)
    permissions = {Permission.RUNS_READ, Permission.DATASETS_READ, Permission.ARTIFACTS_READ}
    if allowed: permissions.add(Permission.SCIENTIFIC_CELL_CLASSIFICATION_EXPLAIN)
    app.dependency_overrides[current_principal] = lambda: Principal('actor', 'actor', (), frozenset(permissions))
    app.dependency_overrides[get_service] = lambda: service
    app.dependency_overrides[ExplainLauncher] = lambda: Mock()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post('/explain-generations', json=request.model_dump(mode='json'))
    assert response.status_code == status, response.text
    assert service.submit.called == allowed


@pytest.mark.parametrize('field,value', [('command','rm'), ('sample_id','filename.png'), ('methods',['unknown']), ('num_samples',999)])
def test_closed_request_contract(setup, field, value):
    _, request, _ = setup
    data = {**request.model_dump(mode='json'), field: value}
    with pytest.raises(ValueError): ExplainRequest.model_validate(data)

@pytest.mark.requires_docker_postgres
def test_default_background_sql_equivalence_on_governed_dataset():
    from app.db import read_only_transaction
    from sqlalchemy import text
    from src.malaria_dl.data.sample_repository import select_dataset_sample_ids
    with read_only_transaction('malaria') as connection:
        row = connection.execute(text('''SELECT t.id AS training, t.dataset_version_id AS dataset,
            r.id AS sample FROM runs t
            JOIN dataset_split_assignments a ON a.dataset_version_id=t.dataset_version_id
            JOIN dataset_source_records r ON r.id=a.source_record_id
            WHERE t.run_type='training' AND a.split_name='val'
            ORDER BY t.id,r.id LIMIT 1''')).mappings().one_or_none()
        if row is None:
            pytest.skip('No governed TRAIN/VAL fixture')
        assert select_dataset_sample_ids(connection, row['dataset'], 'val', limit=1) == [row['sample']]
        assert select_dataset_sample_ids(connection, row['dataset'], 'val', row['sample']) == [row['sample']]
        assert select_dataset_sample_ids(connection, row['dataset'], 'val', uuid4()) == []


def test_interrupted_reservation_is_failed_and_not_reused(setup, monkeypatch):
    service, request, source = setup
    request.methods = ['gradcam']
    candidate = deepcopy(source);candidate['explanation'] = service.specification(request, source, 'gradcam')
    row = {'id': str(uuid4()), 'identity_id': str(uuid4()), 'state': 'active', 'identity': candidate}
    service.repository.candidates.return_value = [row]
    monkeypatch.setattr('app.services.explain_generation.owner_absent', lambda _: True)
    assert service.reusable(request, source, 'gradcam') is None
    state=service.state(request, True)
    assert state['methods'][0]['state']=='failed'
    assert state['methods'][0]['error']=='ASSESSMENT_OWNER_PROCESS_ABSENT'


@pytest.mark.anyio
async def test_unauthenticated_generation_is_rejected(setup):
    from fastapi import HTTPException
    _, request, _ = setup
    app=FastAPI();app.include_router(router)
    def unauthenticated():
        raise HTTPException(401, 'Authentication required')
    app.dependency_overrides[current_principal]=unauthenticated
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        response=await client.post('/explain-generations',json=request.model_dump(mode='json'))
    assert response.status_code==401


def test_bad_shap_reference_does_not_prevent_other_methods_submission(setup):
    service, request, source = setup
    service.reusable = Mock(side_effect=[None, None, ValueError('BACKGROUND_NOT_ACCREDITED')])
    launcher = Mock()
    service.submit(request, launcher, 'actor')
    launcher.launch.assert_called_once_with(request, 'actor')


def test_host_and_docker_locations_are_the_same_context(setup):
    """The GPU agent runs on the host checkout; only the storage prefix differs from Docker."""
    service, request, source = setup
    spec = service.specification(request, source, 'gradcam')
    candidate = deepcopy(source)
    candidate['explanation'] = spec
    candidate['dataset'] = {**candidate['dataset'], 'dataset_root': '/Users/someone/capstone/malaria_dl_local_project/data/malaria_dataset_versions/v1'}
    source['dataset'] = {**source['dataset'], 'dataset_root': '/app/malaria_dl_local_project/data/malaria_dataset_versions/v1'}
    candidate['model'] = {**candidate['model'], 'path': '/Users/someone/capstone/malaria_dl_local_project/outputs/campaign_runs/x/epoch_2.keras'}
    assert service.compatible({'identity': candidate}, source, request, spec)
    candidate['dataset'] = {**candidate['dataset'], 'dataset_root': '/Users/someone/capstone/malaria_dl_local_project/data/malaria_dataset_versions/v2'}
    assert not service.compatible({'identity': candidate}, source, request, spec)


def test_queued_host_request_is_pending_and_failed_one_reports_its_cause(setup):
    service, request, source = setup
    queued = {'id': uuid4(), 'state': 'queued', 'cause': None,
              'request': {'methods': ['lime'], 'class_id': 1, 'num_samples': 1000, 'background_sample_id': None}}
    failed = {'id': uuid4(), 'state': 'failed', 'cause': 'LOCAL_GPU_REQUIRED',
              'request': {'methods': ['shap'], 'class_id': 1, 'num_samples': 1000, 'background_sample_id': None}}
    other_class = {'id': uuid4(), 'state': 'queued', 'cause': None,
                   'request': {'methods': ['gradcam'], 'class_id': 0, 'num_samples': 1000, 'background_sample_id': None}}
    service.repository.requests_for.return_value = [queued, failed, other_class]
    states = {item['method']: item for item in service.state(request, True)['methods']}
    assert states['lime']['state'] == 'pending' and states['lime']['operation_id'] == str(queued['id'])
    assert states['shap']['state'] == 'failed' and states['shap']['error'] == 'LOCAL_GPU_REQUIRED'
    assert states['gradcam']['state'] == 'not_executed'


@pytest.mark.parametrize('split,purpose', [('test', 'final'), ('train', 'development')])
def test_any_governed_split_of_the_train_can_be_explained(setup, split, purpose):
    service, request, source = setup
    source.update(split=split, purpose=purpose)
    asked = []
    service.repository.samples.side_effect = lambda dataset, sample=None, limit=None, split='val': asked.append(split) or [sample or str(uuid4())]
    assert service.context(request) is source
    service.specification(request, source, 'shap')
    assert set(asked) == {split}
