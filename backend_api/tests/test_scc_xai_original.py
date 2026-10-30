"""Original-image HTTP contract; synthetic files and read-only repository doubles."""
from collections import Counter
from dataclasses import replace
from hashlib import sha256
from unittest.mock import Mock
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.repositories.dataset_samples import DatasetSampleReadRepository
from app.routes.artifacts import router
from app.security import current_principal, Principal, Permission
from src.malaria_dl.data.governed_dataset import GovernedDatasetSnapshot

PNG = b'\x89PNG\r\n\x1a\n' + b'\0' * 16
SAMPLE = '000f6007-9330-5085-972a-247631c541c6'
TRAIN = 'd3d42cf3-0800-468c-b3ed-995860967da1'
DATASET = 'd8c0cab5-09dd-597f-9de7-7ca01aee2ec2'
ATTEMPT = '93966b5d-5548-4b29-96f9-0b67e5c98f9f'
FILENAME = 'C168P129ThinF_IMG_20151118_155802_cell_44.png'


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def scenario(tmp_path):
    snapshot = GovernedDatasetSnapshot(UUID(DATASET), uuid4(), tmp_path,
        *(['a' * 64] * 4), {'train': 1, 'val': 1, 'test': 1})
    path = tmp_path / 'val' / 'uninfected' / FILENAME
    path.parent.mkdir(parents=True)
    path.write_bytes(PNG)
    row = dict(source_record_id=SAMPLE, clinical_identity_id=str(uuid4()), split_name='val',
               class_name='uninfected', source_filename=FILENAME, source_file_sha256=sha256(PNG).hexdigest())
    context = dict(identity_id=str(uuid4()), training_run_id=TRAIN,
                   identity={'dataset': snapshot.metadata(), 'split': 'val'})
    repo = Mock(spec=DatasetSampleReadRepository)
    repo.explanation_context.return_value = context
    repo.training_dataset.return_value = snapshot
    repo.sample_reference.return_value = (row, Counter({('val', 'uninfected', FILENAME): 1}))
    app = FastAPI()
    app.include_router(router)
    @app.exception_handler(HTTPException)
    async def error(request, exc):
        return JSONResponse({'error': exc.detail}, status_code=exc.status_code)
    app.dependency_overrides[DatasetSampleReadRepository] = lambda: repo
    app.dependency_overrides[current_principal] = lambda: Principal('user', 'user', (), frozenset({Permission.ARTIFACTS_READ}))
    return app, repo, row, context, path


async def get(scenario, **overrides):
    app = scenario[0]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        return await client.get('/artifacts/file', params={**dict(source='dataset_sample',
            training_run_id=TRAIN, sample_id=SAMPLE, attempt_id=ATTEMPT, dataset_version_id=DATASET), **overrides})


@pytest.mark.anyio
async def test_original_uses_sample_identity_and_verified_content(scenario):
    response = await get(scenario)
    assert response.status_code == 200, response.text
    assert response.content == PNG
    assert response.headers['content-type'] == 'image/png'
    assert response.headers['x-content-sha256'] == sha256(PNG).hexdigest()
    assert response.headers['x-sample-id'] == SAMPLE
    assert response.headers['x-dataset-version-id'] == DATASET
    assert SAMPLE in response.headers['content-disposition']
    assert response.headers['cache-control'] == 'private, no-store'
    assert str(scenario[4]) not in str(response.headers)
    scenario[1].sample_reference.assert_called_once_with('malaria', DATASET, 'val', SAMPLE)


@pytest.mark.anyio
@pytest.mark.parametrize('fault,status,code', [
    ('foreign_attempt', 404, 'ARTIFACT_RELATION_MISMATCH'),
    ('foreign_sample', 404, 'ARTIFACT_RELATION_MISMATCH'),
    ('foreign_dataset', 404, 'ARTIFACT_RELATION_MISMATCH'),
    ('split', 404, 'ARTIFACT_RELATION_MISMATCH'),
    ('snapshot', 409, 'ARTIFACT_DATASET_EVIDENCE_INVALID'),
    ('missing', 410, 'ARTIFACT_CONTENT_MISSING'),
    ('changed', 409, 'ARTIFACT_INTEGRITY_FAILED'),
    ('traversal', 409, 'ARTIFACT_DATASET_EVIDENCE_INVALID'),
    ('absolute', 409, 'ARTIFACT_DATASET_EVIDENCE_INVALID'),
    ('symlink', 409, 'ARTIFACT_LOCATION_INVALID'),
    ('mime', 415, None),
])
async def test_original_rejects_invalid_evidence_without_fallback(scenario, fault, status, code):
    app, repo, row, context, path = scenario
    if fault == 'foreign_attempt': repo.explanation_context.return_value = None
    if fault == 'foreign_sample': repo.sample_reference.return_value = None
    if fault == 'foreign_dataset': repo.training_dataset.return_value = replace(repo.training_dataset.return_value, dataset_version_id=uuid4())
    if fault == 'split': context['identity']['split'] = '../../test'
    if fault == 'snapshot': context['identity']['dataset']['patient_assignment_fingerprint'] = 'different'
    if fault == 'missing': path.unlink()
    if fault == 'changed': path.write_bytes(PNG + b'changed')
    if fault == 'traversal': row['source_filename'] = '../secret.png'
    if fault == 'absolute': row['source_filename'] = '/tmp/secret.png'
    if fault == 'symlink':
        outside = path.parents[2] / 'other.png'
        outside.write_bytes(PNG)
        path.unlink()
        path.symlink_to(outside)
    if fault == 'mime':
        path.write_bytes(b'not PNG')
        row['source_file_sha256'] = sha256(b'not PNG').hexdigest()
    response = await get(scenario)
    assert response.status_code == status, response.text
    if code: assert response.json()['error']['code'] == code
    assert str(path.parent) not in response.text


@pytest.mark.anyio
async def test_collision_uses_shared_source_record_prefix(scenario):
    app, repo, row, context, path = scenario
    repo.sample_reference.return_value[1][('val', 'uninfected', FILENAME)] = 2
    path.rename(path.with_name(f'{SAMPLE}__{FILENAME}'))
    response = await get(scenario)
    assert response.status_code == 200
    assert response.content == PNG


@pytest.mark.anyio
@pytest.mark.parametrize('status', [401, 403])
async def test_original_requires_authentication_and_permission(scenario, status):
    app, repo, *_ = scenario
    if status == 401:
        def anonymous():
            raise HTTPException(401, 'Authentication required')
        app.dependency_overrides[current_principal] = anonymous
    else:
        app.dependency_overrides[current_principal] = lambda: Principal('user', 'user', (), frozenset())
    response = await get(scenario)
    assert response.status_code == status
    repo.explanation_context.assert_not_called()


@pytest.mark.anyio
@pytest.mark.parametrize('field', ['sample_id', 'training_run_id', 'attempt_id', 'dataset_version_id'])
async def test_original_rejects_path_instead_of_uuid(scenario, field):
    response = await get(scenario, **{field: '../secret.png'})
    assert response.status_code == 400
    assert response.json()['error']['code'] == 'ARTIFACT_ID_INVALID'
    assert '../secret' not in response.text
    scenario[1].explanation_context.assert_not_called()


@pytest.mark.anyio
async def test_requested_dataset_must_match_attempt_and_train(scenario):
    response = await get(scenario, dataset_version_id=str(uuid4()))
    assert response.status_code == 404
    scenario[1].training_dataset.assert_not_called()


def test_inspection_uses_the_persisted_train_snapshot_without_reverifying_the_population(monkeypatch, tmp_path):
    from app.repositories import dataset_samples
    persisted = {'dataset_version_id': DATASET, 'dataset_materialization_id': str(uuid4()), 'dataset_root': str(tmp_path),
                 'patient_assignment_fingerprint': 'p', 'record_assignment_fingerprint': 'r',
                 'source_population_fingerprint': 's', 'clinical_identity_fingerprint': 'c', 'counts': {'val': 1}}
    metadata = Mock(return_value=persisted)
    monkeypatch.setattr(dataset_samples, 'training_dataset_metadata', metadata)
    monkeypatch.setattr(dataset_samples, 'resolve_datasource', lambda source: source)
    snapshot = DatasetSampleReadRepository().training_dataset('malaria', TRAIN)
    metadata.assert_called_once_with(TRAIN)
    assert not hasattr(dataset_samples, 'resolve_training_run_dataset')
    assert snapshot.metadata()['patient_assignment_fingerprint'] == 'p' and str(snapshot.dataset_version_id) == DATASET
