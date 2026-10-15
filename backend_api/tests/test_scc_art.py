"""SCC-ART HTTP contract; repositories mocked, no scientific DB writes."""
import hashlib
from pathlib import Path
from uuid import uuid4
from unittest.mock import Mock

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from app.routes.artifacts import router
from app.repositories.artifacts import ArtifactReadRepository
from app.security import current_principal, Principal, Permission
from app.services import artifacts

PNG = b'\x89PNG\r\n\x1a\n' + b'\0' * 16


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def scenario(tmp_path, monkeypatch):
    aid, attempt, train, sample = [str(uuid4()) for _ in range(4)]
    root = tmp_path / 'artifacts' / 'assessments' / attempt
    root.mkdir(parents=True)
    path = root / f'{aid}.png'
    path.write_bytes(PNG)
    old = Path('/historical/malaria_dl_local_project/artifacts/assessments') / attempt
    row = dict(artifact_id=aid, attempt_id=attempt, training_run_id=train, sample_id=sample,
               artifact_root=str(old), payload=dict(artifact_id=aid, sample_id=sample,
               path=str(old / path.name), bytes=len(PNG), sha256=hashlib.sha256(PNG).hexdigest()))
    repo = Mock(spec=ArtifactReadRepository)
    repo.get.return_value = row
    monkeypatch.setattr(artifacts, 'MALARIA_PROJECT_ROOT', tmp_path)
    app = FastAPI()
    app.include_router(router)
    @app.exception_handler(HTTPException)
    async def errors(request, exc):
        return JSONResponse({'error': exc.detail}, status_code=exc.status_code)
    app.dependency_overrides[ArtifactReadRepository] = lambda: repo
    app.dependency_overrides[current_principal] = lambda: Principal('user','user',(),frozenset({Permission.ARTIFACTS_READ}))
    return app, repo, row, path


async def get(scenario, **params):
    app, repo, row, path = scenario
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        return await client.get('/artifacts/file', params={'artifact_id': row['artifact_id'], 'source': 'assessment', **params})


@pytest.mark.anyio
async def test_png_bytes_identity_and_headers(scenario):
    app, repo, row, path = scenario
    response = await get(scenario, attempt_id=row['attempt_id'], training_run_id=row['training_run_id'])
    assert response.status_code == 200, response.text
    assert response.content == PNG
    assert response.headers['content-type'] == 'image/png'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert '/historical' not in str(response.headers)
    repo.get.assert_called_once_with('malaria', row['artifact_id'], 'assessment')


@pytest.mark.anyio
@pytest.mark.parametrize('change,status,code', [
    ('missing_record',404,'ARTIFACT_NOT_REGISTERED'),('missing_file',410,'ARTIFACT_CONTENT_MISSING'),
    ('hash',409,'ARTIFACT_INTEGRITY_FAILED'),('size',409,'ARTIFACT_INTEGRITY_FAILED'),
    ('traversal',409,'ARTIFACT_LOCATION_INVALID'),('absolute',409,'ARTIFACT_LOCATION_INVALID'),
    ('symlink',409,'ARTIFACT_LOCATION_INVALID'),('wrong_attempt',404,'ARTIFACT_RELATION_MISMATCH'),
    ('wrong_train',404,'ARTIFACT_RELATION_MISMATCH'),('payload_id',409,'ARTIFACT_RELATION_MISMATCH'),
    ('sample',409,'ARTIFACT_RELATION_MISMATCH'),('uuid',400,'ARTIFACT_ID_INVALID'),
    ('source',400,'ARTIFACT_SOURCE_INVALID'),
])
async def test_controlled_failures(scenario, change, status, code):
    app, repo, row, path = scenario
    params = {}
    if change == 'missing_record': repo.get.return_value = None
    if change == 'missing_file': path.unlink()
    if change == 'hash': row['payload']['sha256'] = '0'*64
    if change == 'size': row['payload']['bytes'] = 1
    if change == 'traversal': row['payload']['path'] = row['artifact_root']+'/../secret.png'
    if change == 'absolute': row['payload']['path'] = '/etc/secret.png'
    if change == 'payload_id': row['payload']['artifact_id'] = str(uuid4())
    if change == 'sample': row['payload']['sample_id'] = str(uuid4())
    if change == 'wrong_attempt': params['attempt_id'] = str(uuid4())
    if change == 'wrong_train': params['training_run_id'] = str(uuid4())
    if change == 'uuid': params['artifact_id'] = 'invalid'
    if change == 'source': params['source'] = 'guess'
    if change == 'symlink':
        outside = path.parents[3]/'secret.png'; outside.write_bytes(PNG)
        path.unlink(); path.symlink_to(outside)
    response = await get(scenario, **params)
    assert response.status_code == status, response.text
    assert response.json()['error']['code'] == code
    assert '/historical' not in response.text and str(path) not in response.text


@pytest.mark.anyio
@pytest.mark.parametrize('suffix,payload,mime', [('.npy',b'\x93NUMPYdata','application/octet-stream'),('.json',b'{}','application/json'),('.csv',b'a,b\n1,2','text/csv')])
async def test_download(scenario, suffix, payload, mime):
    app, repo, row, path = scenario
    target = path.with_suffix(suffix); target.write_bytes(payload)
    row['payload'].update(path=str(Path(row['artifact_root'])/target.name),bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
    response = await get(scenario)
    assert response.status_code == 200
    assert response.content == payload
    assert response.headers['content-type'].startswith(mime)
    assert response.headers['content-disposition'].startswith('attachment')


@pytest.mark.anyio
async def test_training_default_and_collision_are_deterministic(scenario, monkeypatch):
    app, repo, row, path = scenario
    training = dict(artifact_id=row['artifact_id'], path=str(path), training_run_id=row['training_run_id'],
                    checksum=hashlib.sha256(PNG).hexdigest(), file_size_bytes=len(PNG))
    repo.get.side_effect = lambda ds, aid, source: training if source == 'training' else row
    monkeypatch.setattr(artifacts, 'ALLOWED_ARTIFACT_ROOTS', (path.parent,))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/artifacts/file',params={'artifact_id':row['artifact_id']})
    assert response.status_code == 200
    assert repo.get.call_args.args[2] == 'training'
    assert (await get(scenario)).status_code == 200
    assert repo.get.call_args.args[2] == 'assessment'


@pytest.mark.anyio
@pytest.mark.parametrize('status', [401,403])
async def test_authorization_before_resolution(scenario, status):
    app, repo, row, path = scenario
    def principal():
        if status == 401: raise HTTPException(401,'Authentication required')
        return Principal('user','user',(),frozenset())
    if status == 401:
        app.dependency_overrides.pop(current_principal)
    else:
        app.dependency_overrides[current_principal] = principal
    response = await get(scenario)
    assert response.status_code == status
    repo.get.assert_not_called()


@pytest.mark.anyio
async def test_no_hash_uses_existing_unverified_policy(scenario):
    scenario[2]['payload'].pop('sha256')
    assert (await get(scenario)).status_code == 200


@pytest.mark.anyio
async def test_relative_registered_location(scenario):
    row = scenario[2]
    row['artifact_root'] = f"artifacts/assessments/{row['attempt_id']}"
    row['payload']['path'] = row['artifact_root']+'/'+scenario[3].name
    assert (await get(scenario)).status_code == 200


@pytest.mark.anyio
@pytest.mark.parametrize('kind', ['checksum','missing','escape'])
async def test_training_integrity_and_confinement(scenario, monkeypatch, kind):
    app, repo, row, path = scenario
    training = dict(artifact_id=row['artifact_id'],path=str(path),training_run_id=row['training_run_id'],
                    checksum=hashlib.sha256(PNG).hexdigest(),file_size_bytes=len(PNG))
    repo.get.return_value = training
    monkeypatch.setattr(artifacts,'ALLOWED_ARTIFACT_ROOTS',(path.parent,))
    if kind == 'checksum': training['checksum'] = '0'*64
    if kind == 'missing': path.unlink()
    if kind == 'escape': training['path'] = '/etc/passwd'
    response = await get(scenario,source='training')
    assert response.status_code == (410 if kind == 'missing' else 409)


@pytest.mark.anyio
@pytest.mark.parametrize('kind', ['png','npy','extension'])
async def test_reject_untrusted_media(scenario, kind):
    app, repo, row, path = scenario
    target = path.with_suffix('.npy' if kind == 'npy' else '.html' if kind == 'extension' else '.png')
    target.write_bytes(b'not-an-image')
    row['payload'].update(path=str(Path(row['artifact_root'])/target.name),bytes=12,sha256=None)
    response = await get(scenario)
    assert response.status_code in (403,415)
