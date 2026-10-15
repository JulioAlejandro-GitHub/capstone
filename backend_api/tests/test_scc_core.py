"""SCC read contracts: synthetic PostgreSQL CTEs and real SELECT-only evidence."""
import json
from contextlib import contextmanager
from dataclasses import replace
from uuid import UUID

import httpx
import pytest
from sqlalchemy import text

from app.config import Settings, get_settings
from app.db import read_only_transaction
from app.main import app
from app.repositories import catalog
from app.repositories.assessments import AssessmentReadRepository
from app.repositories.catalog import CatalogRepository
from app.repositories.scientific_results import ScientificReadRepository
from app.services.assessments import AssessmentReadService
from app.services.catalog import CatalogService
from app.services.scientific_public import public_evidence
from app.services.scientific_results import ScientificReadService
from test_e6_lineage_read_only import fixtures, install_fixtures, TRAIN, REAL_TRAIN


@pytest.fixture
def anyio_backend():
    return 'asyncio'


def test_configuration(monkeypatch):
    monkeypatch.delenv('SCC_MAX_COMPARISON_RUNS', raising=False)
    assert Settings.from_env().scc_max_comparison_runs == 4
    monkeypatch.setenv('SCC_MAX_COMPARISON_RUNS', '7')
    assert Settings.from_env().scc_max_comparison_runs == 7
    for invalid in ('0', '-1', 'invalid'):
        monkeypatch.setenv('SCC_MAX_COMPARISON_RUNS', invalid)
        with pytest.raises(ValueError):
            Settings.from_env()


def test_public_storage_projection():
    value = {'artifact_id': 'id', 'sample_id': 'sample', 'path': '/private/test.png',
             'identity': {'artifact_root': '/tmp', 'extensions': {'location': '/tmp/foo',
             'checkpoint_path': 'relative/a.h5', 'score': 0}}, 'command': 'python /private/x.py'}
    result = public_evidence(value)
    assert result == {'artifact_id': 'id', 'sample_id': 'sample',
                      'identity': {'extensions': {'location': None, 'score': 0}}}


@pytest.mark.requires_docker_postgres
def test_dynamic_catalog_multiple_training_and_untrained(monkeypatch):
    models = [dict(id=str(UUID(int=i)), name=f'future_{i}', architecture=f'Transformer {i}',
                   model_type='classification') for i in (1, 2)]
    runs = [dict(id=str(UUID(int=i)), model_id=models[0]['id'], run_type=kind, status=state)
            for i, kind, state in [(10, 'training', 'completed'), (11, 'training', 'failed'), (12, 'evaluation', 'completed')]]

    @contextmanager
    def connection(_datasource):
        with read_only_transaction('malaria') as c:
            assert c.execute(text('SHOW transaction_read_only')).scalar_one() == 'on'
            class FixtureConnection:
                def execute(self, statement):
                    prefix = '''WITH models AS (
                      SELECT * FROM jsonb_populate_recordset(NULL::public.models, CAST(:models AS jsonb))),
                      runs AS (SELECT * FROM jsonb_populate_recordset(NULL::public.runs, CAST(:runs AS jsonb))),
                      vw_model_run_summary AS (
                        SELECT id AS model_id,name AS model_name,model_type,0 AS total_runs FROM models)
                    '''
                    return c.execute(text(prefix + str(statement)), {'models': json.dumps(models), 'runs': json.dumps(runs)})
            yield FixtureConnection()
    monkeypatch.setattr(catalog, 'read_only_transaction', connection)
    result = CatalogService(CatalogRepository(), replace(get_settings(), scc_max_comparison_runs=9)).models('malaria')
    assert result['comparison']['scc_max_comparison_runs'] == 9
    trained, untrained = result['items']
    assert len(trained['training_runs']) == 2
    assert trained['has_completed_training'] is True
    assert untrained['training_runs'] == []
    assert untrained['has_completed_training'] is False
    assert {m['architecture'] for m in result['items']} == {'Transformer 1', 'Transformer 2'}


@pytest.mark.requires_docker_postgres
def test_all_attempts_and_test_split_preserved(monkeypatch):
    values = fixtures(('verified', 'failed', 'interrupted', 'active'), False, False, False)
    base_identity = values['assessment_identities'][0]
    for i, kind, split in [(50, 'evaluate', 'test'), (51, 'explain', 'val')]:
        identity_id = str(UUID(int=i))
        values['assessment_identities'].append({**base_identity, 'id': identity_id, 'kind': kind,
                                                'identity': {'split': split}})
        values['assessment_attempts'].append({**values['assessment_attempts'][0],
                                              'id': str(UUID(int=i+100)), 'identity_id': identity_id})
    install_fixtures(monkeypatch, values)
    service = AssessmentReadService(AssessmentReadRepository())
    items = service.list(UUID(TRAIN), None, 100, 0, True)['items']
    assert len(items) == 6
    assert len({i['attempt_id'] for i in items}) == 6
    assert {i['assessment_type'] for i in items} == {'EVALUATE', 'EXPLAIN', 'TEST'}
    assert all(i['split'] == 'test' for i in items if i['assessment_type'] == 'TEST')
    assert all(i['identity_id'] != i['attempt_id'] for i in items)
    for item in items:
        detail = service.detail(item['attempt_id'], True)
        assert detail['training_run_id'] == UUID(TRAIN)
        assert detail['identity_id'] == item['identity_id']


@pytest.mark.requires_docker_postgres
@pytest.mark.anyio
async def test_real_http_contracts_and_missing_ids():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/models')
        assert response.status_code == 200, response.text
        assert response.json()['comparison']['scc_max_comparison_runs'] == get_settings().scc_max_comparison_runs
        response = await client.get(f'/runs/{REAL_TRAIN}/scientific-results?view=traceability')
        assert response.status_code == 200, response.text
        result = response.json()
        assert result['contract_version'] == 'scc_core_1'
        assert result['training_run_id'] == REAL_TRAIN
        assert result['model']['id'] == result['training']['model_id']
        assert result['evidence']['dataset_version']['id'] == result['training']['dataset_version_id']
        assert result['evidence']['run_configurations']
        assert result['assessments']
        assert 'checkpoint_path' not in json.dumps(result)
        assert 'artifact_root' not in json.dumps(result)
        for attempt in result['assessments']:
            for suffix in ('', '/results', '/artifacts'):
                r = await client.get(f"/assessments/{attempt['attempt_id']}{suffix}?view=traceability&limit=1")
                assert r.status_code == 200, r.text
                assert '"path"' not in r.text
                if suffix == '/artifacts' and r.json()['items']:
                    assert r.json()['items'][0]['artifact_id']
        missing = str(UUID(int=0))
        for path in [f'/runs/{missing}/scientific-results', f'/assessments/{missing}', f'/assessments/{missing}/results']:
            r = await client.get(path, params={'view': 'traceability'})
            assert r.status_code == 404, r.text
        old = await client.get(f'/runs/{REAL_TRAIN}/scientific-results')
        assert old.status_code == 200
        assert old.json()['contract_version'] == 'scientific_results_v2'


def test_database_failure_is_not_empty_evidence():
    class BrokenRepository:
        def read(self, *args):
            raise RuntimeError('database unavailable')
    service = ScientificReadService(BrokenRepository(), AssessmentReadRepository())
    with pytest.raises(RuntimeError, match='database unavailable'):
        service.read(UUID(TRAIN), 'malaria', True)


def test_scientific_catalog_excludes_other_tasks_and_redacts_metadata():
    class Repository:
        def models(self, datasource):
            return [dict(model_type=kind, training_runs=[], metadata={'path': '/private/data'})
                    for kind in ('classification', 'segmentation', 'detection')]
    result = CatalogService(Repository(), get_settings()).models('malaria', True)
    assert len(result['items']) == 1
    assert result['items'][0]['metadata'] == {}
    assert result['items'][0]['training_evidence_status'] == 'not_generated'


def test_non_training_and_unregistered_model():
    class Repository:
        def read(self, *args):
            return {'training': {'run_type': 'evaluation'}, 'model': None}
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        ScientificReadService(Repository(), AssessmentReadRepository()).read(UUID(TRAIN), 'malaria', True)
    assert exc.value.status_code == 422
