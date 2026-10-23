"""One cell can be read across EXPLAIN attempts without paging the whole population."""
from uuid import UUID

import httpx
import pytest
from app.main import app
from app.repositories.assessments import AssessmentReadRepository


class Recorder(AssessmentReadRepository):
    def __init__(self):
        self.calls = []

    def payloads(self, attempt_id, kind, limit, offset, sample_ids=None):
        self.calls.append((kind, limit, offset, sample_ids))
        return []


def test_service_forwards_sample_filter_only_when_given():
    from app.services.assessments import AssessmentReadService
    repository = Recorder()
    service = AssessmentReadService(repository)
    sample = UUID(int=7)
    service.payloads(UUID(int=1), 'artifacts', 100, 0, False, [sample])
    service.payloads(UUID(int=1), 'artifacts', 100, 0)
    assert repository.calls == [('artifacts', 100, 0, [sample]), ('artifacts', 100, 0, None)]


@pytest.mark.requires_docker_postgres
@pytest.mark.anyio
async def test_real_artifacts_filtered_by_sample():
    attempts = AssessmentReadRepository().payloads(UUID('120f477a-d95d-47ab-b68d-1dff464614bf'), 'artifacts', 2, 0)
    if not attempts:
        pytest.skip('Audited EXPLAIN attempt is not present in this database.')
    sample = attempts[0]['sample_id']
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        r = await client.get('/assessments/120f477a-d95d-47ab-b68d-1dff464614bf/artifacts',
                             params={'view': 'traceability', 'sample_id': sample})
    assert r.status_code == 200, r.text
    items = r.json()['items']
    assert items and {item['sample_id'] for item in items} == {sample}
    assert {item['role'] for item in items} == {'map', 'overlay'}


@pytest.mark.requires_docker_postgres
@pytest.mark.anyio
async def test_real_results_filtered_by_sample():
    rows = AssessmentReadRepository().payloads(UUID('d1ce1424-c7c3-4ee8-816d-3b91090b42cf'), 'results', 1, 0)
    if not rows:
        pytest.skip('Audited EVALUATE attempt is not present in this database.')
    sample = rows[0]['sample_id']
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        r = await client.get('/assessments/d1ce1424-c7c3-4ee8-816d-3b91090b42cf/results', params={'sample_id': sample})
    assert r.status_code == 200, r.text
    items = r.json()['items']
    assert len(items) == 1 and items[0]['sample_id'] == sample and {'label', 'predicted', 'raw_score', 'threshold'} <= set(items[0])
