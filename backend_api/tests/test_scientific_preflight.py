"""Contract tests with synthetic evidence; PostgreSQL tests below use SELECT-only CTEs."""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from uuid import UUID

import httpx
import pytest
from app.config import get_settings
from app.main import app
from app.schemas.scientific_preflight import PreflightRequest
from app.security import Permission, Principal, current_principal
from app.services.scientific_preflight import CONFIG_FIELDS, ScientificPreflightService
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError


def uid(n):
    return UUID(int=n)

class Connection:
    @contextmanager
    def begin_nested(self):
        yield

@contextmanager
def transaction(*args, **kwargs):
    assert kwargs == {'repeatable_read': True}
    yield Connection()

class Evidence:
    def __init__(self):
        self.trains = {uid(n): {'id': uid(n), 'run_type': 'training', 'dataset_version_id': uid(10),
                                   'dataset_registered': True} for n in (1, 2)}
        self.config = {k: 'persisted' for k in CONFIG_FIELDS}
        self.config.update(random_seed=1, learning_rate=.01, batch_size=32,
                           extension_configuration={'execution': {'no_augment': False}})
        self.attempts = {uid(n+20): {'attempt_id': uid(n+20), 'identity_id': uid(n+30),
            'training_run_id': uid(n), 'kind': 'evaluate', 'identity_hash': 'a'*64, 'state': 'verified',
            'verification': {'count': 2, 'metrics': {'accuracy': 1}},
            'identity': {'split': 'val', 'dataset': {'dataset_version_id': str(uid(10))},
                'model': {'checkpoint_artifact_id': str(uid(n+40)), 'input_contract': {'normalization': 'x'}},
                'protocol': {'version': 'v1'}, 'decision': {'effective': .5, 'score_domain': 'raw', 'positive_class': 1, 'comparison': '>=', 'calibrator': None}, 'batch_size': 32,
                'metrics_definition': 'binary_counts_rates_v1'}} for n in (1, 2)}
        self.coverage = [{'attempt_id': uid(n+20), 'expected_rows': 2, 'expected_unique': 2,
            'retrieved_rows': 2, 'retrieved_unique': 2, 'intersection_unique': 2, 'label_conflicts': 0,
            'missing_labels': 0, 'missing_count': 0, 'unexpected_count': 0, 'declared_label_conflicts': 0,
            'ungoverned_count': 0, 'state': 'verified', 'verified_count': '2'} for n in (1, 2)]
        self.fail = set()
        self.candidates = {'attempts': 0, 'evaluations': 0}
        self.calls = []
    def check(self, name):
        self.calls.append(name)
        if name in self.fail:
            raise SQLAlchemyError('private SQL password /private/secret')
    def preflight_training(self, c, run):
        self.check('train')
        return self.trains.get(run)
    def preflight_configuration(self, c, run):
        self.check('config')
        return self.config
    def preflight_history(self, c, run):
        self.check('history')
        return {'rows': 10, 'unique_epochs': 10, 'unknown_axes': 0}
    def preflight_detail(self, c, attempt):
        self.check('attempt')
        return self.attempts.get(attempt)
    def preflight_candidates(self, c, run):
        self.check('candidates')
        return self.candidates
    def preflight_population(self, c, attempts):
        self.check('population')
        return self.coverage
    def get(self, datasource, artifact_id, source, *, connection):
        self.check('artifact')
        return {'training_run_id': uid(int(UUID(artifact_id))-40), 'path': '/private/model.keras', 'checksum': 'a'*64}

def request(evaluation=True):
    return PreflightRequest.model_validate({'selections': [
        dict(training_run_id=uid(n), **({'evaluation': {'source': 'assessment',
             'identity_id': uid(n+30), 'attempt_id': uid(n+20)}} if evaluation else {})) for n in (1, 2)]})

def run(e=None, body=None):
    e = e or Evidence()
    return ScientificPreflightService(e, e, e, transaction).read(body or request(), 'malaria', 'test')

def states(result, module):
    return {a.verdict.scientific_state for a in result.analyses if a.module_id == module}

def codes(result):
    return {f.code for d in result.dimensions for f in d.findings}

def test_two_comparable_trains_and_independent_modules():
    result = run()
    assert states(result, 'metrics') == {'COMPARABLE'}
    assert states(result, 'consensus') == {'COMPARABLE'}
    assert states(result, 'xai') == {'EVIDENCIA_INSUFICIENTE'}
    assert result.summary.analysis_count == sum(result.summary.by_state.values()) + result.summary.not_evaluated
    assert all(c.availability == c.integrity == 'not_checked' and c.checked_at is None for c in result.checkpoints)
    assert '/private/' not in result.model_dump_json()
    assert result.populations[0].per_selection[0].ratio.value == 1

def test_different_datasets_are_context_not_automatic_rejection():
    e = Evidence()
    e.trains[uid(2)]['dataset_version_id'] = uid(11)
    result = run(e)
    assert states(result, 'metrics') == {'COMPARABLE_CON_ADVERTENCIAS'}
    assert 'TRAIN_DATASET_DIFFERENCE' in codes(result)

def test_splits_and_missing_configuration_preserve_both_conditions():
    e = Evidence()
    e.attempts[uid(22)]['identity']['split'] = 'test'
    e.attempts[uid(22)]['identity'].pop('protocol')
    result = run(e)
    assert states(result, 'metrics') == {'NO_COMPARABLE', 'EVIDENCIA_INSUFICIENTE'}
    assert 'SPLIT_DIFFERENCE' in codes(result)
    assert 'PROTOCOL_INCOMPLETE' in codes(result)

@pytest.mark.parametrize('candidate_count', [0, 1, 3])
def test_no_automatic_selection(candidate_count):
    e = Evidence()
    e.candidates['attempts'] = candidate_count
    result = run(e, request(False))
    assert all(s.evaluation.state == 'unknown' for s in result.selections)
    assert 'attempt' not in e.calls
    assert states(result, 'curves') == {'COMPARABLE'}
    assert states(result, 'metrics') == {'EVIDENCIA_INSUFICIENTE'}
    if candidate_count > 1:
        assert 'AMBIGUOUS_EVALUATION' in codes(result)

def test_old_attempt_is_selected_exactly():
    e = Evidence()
    e.attempts[uid(99)] = deepcopy(e.attempts[uid(21)])
    e.attempts[uid(99)]['state'] = 'active'
    result = run(e)
    assert str(result.selections[0].evaluation.value['attempt_id']) == str(uid(21))
    assert states(result, 'metrics') == {'COMPARABLE'}

@pytest.mark.parametrize('change,code', [
    ('incomplete', 'COVERAGE_NOT_VERIFIED'), ('duplicate', 'DUPLICATE_SAMPLES'),
    ('label', 'LABEL_CONFLICT'), ('empty', 'EMPTY_INTERSECTION'),
    ('ungoverned', 'COVERAGE_NOT_VERIFIED'),
])
def test_population_problems(change, code):
    e = Evidence()
    if change == 'incomplete':
        e.coverage[0].update(missing_count=1, retrieved_rows=1, retrieved_unique=1)
    elif change == 'duplicate':
        e.coverage[0]['expected_rows'] = 3
    elif change == 'label':
        e.coverage[0]['label_conflicts'] = 1
    elif change == 'ungoverned':
        e.coverage[0]['ungoverned_count'] = 1
    else:
        for c in e.coverage:
            c['intersection_unique'] = 0
    result = run(e)
    assert code in codes(result)
    assert 'COMPARABLE' not in states(result, 'consensus')
    if change in ('incomplete', 'duplicate', 'ungoverned'):
        assert result.populations[0].intersection_unique.state == 'unknown'

def test_partial_intersection_does_not_relabel_original_metrics():
    e = Evidence()
    for c in e.coverage:
        c['intersection_unique'] = 1
    result = run(e)
    assert states(result, 'metrics') == {'NO_COMPARABLE'}
    assert states(result, 'consensus') == {'COMPARABLE_CON_ADVERTENCIAS'}
    assert result.populations[0].per_selection[0].ratio.value == .5

def test_configuration_is_not_completed_with_defaults_or_secrets():
    e = Evidence()
    e.config = {'architecture': 'a', 'canonical_configuration': {'token': 'SECRET'}}
    result = run(e)
    assert 'CONFIGURATION_INCOMPLETE' in codes(result)
    assert 'SECRET' not in result.model_dump_json()

@pytest.mark.parametrize('domain', ['population', 'attempt', 'artifact', 'config', 'history', 'train'])
def test_sql_errors_are_separate_and_sanitized(domain):
    e = Evidence()
    e.fail.add(domain)
    result = run(e)
    assert result.technical_errors
    assert 'private SQL' not in result.model_dump_json()
    assert result.summary.not_evaluated > 0
    if domain in ('population', 'attempt', 'artifact'):
        assert states(result, 'curves') == {'COMPARABLE'}

def test_missing_train_and_wrong_identity_are_http_errors():
    e = Evidence()
    del e.trains[uid(1)]
    with pytest.raises(HTTPException) as err:
        run(e)
    assert err.value.status_code == 404
    e = Evidence()
    e.attempts[uid(21)]['identity_id'] = uid(90)
    with pytest.raises(HTTPException) as err:
        run(e)
    assert err.value.status_code == 422

def test_cross_train_attempt_not_exposed():
    e = Evidence()
    e.attempts[uid(21)]['training_run_id'] = uid(999)
    with pytest.raises(HTTPException) as err:
        run(e)
    assert err.value.status_code == 404

def test_limit_uses_settings(monkeypatch):
    from app.schemas import scientific_preflight
    monkeypatch.setattr(scientific_preflight, 'get_settings', lambda: replace(get_settings(), scc_max_comparison_runs=1))
    with pytest.raises(ValidationError, match='SCC_MAX_COMPARISON_RUNS'):
        request()

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.anyio
@pytest.mark.parametrize('permissions,insecure,expected', [
    (frozenset(), False, 403),
    (frozenset(Permission), True, 401),
    (frozenset(Permission) - {Permission.ARTIFACTS_READ}, False, 403),
    (frozenset(Permission), False, 200),
])
async def test_http_permissions(monkeypatch, permissions, insecure, expected):
    from app.routes import scientific_preflight
    app.dependency_overrides[current_principal] = lambda: Principal('user', 'tester', (), permissions, insecure)
    called = []
    def read(*args):
        called.append(True)
        return run()
    monkeypatch.setattr(scientific_preflight, 'ScientificPreflightService', lambda: type('Service', (), {'read': read})())
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            response = await client.post('/models/comparison/preflight', json=request().model_dump(mode='json'))
        assert response.status_code == expected
        assert bool(called) == (expected == 200)
        if expected == 200:
            assert response.headers['cache-control'] == 'private, no-store'
    finally:
        app.dependency_overrides.clear()

@pytest.mark.anyio
async def test_http_requires_authentication(monkeypatch):
    from app import security
    monkeypatch.setattr(security, 'get_settings', lambda: replace(get_settings(), auth_mode='local_jwt'))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post('/models/comparison/preflight', json=request().model_dump(mode='json'))
    assert response.status_code == 401

def test_no_execution_imports():
    import ast
    from pathlib import Path
    path = Path(__file__).parents[1] / 'app/services/scientific_preflight.py'
    tree = ast.parse(path.read_text())
    imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert not any(x and any(s in x for s in ('runtime', 'execution', 'tensorflow', 'science.comparison')) for x in imports)

@pytest.mark.requires_docker_postgres
def test_postgres_complete_population_aggregates_and_conflicts():
    import json

    from app.db import read_only_transaction
    from app.repositories.assessments import AssessmentReadRepository
    from sqlalchemy import text
    tables = ('assessment_identities', 'assessment_attempts', 'assessment_results',
              'dataset_split_assignments', 'dataset_source_records')
    fixtures = {t: [] for t in tables}
    # More than the historical default page (100); the SQL must examine all 105.
    for sample in range(1000, 1105):
        fixtures['dataset_source_records'].append({'id': str(uid(sample))})
        fixtures['dataset_split_assignments'].append({'source_record_id': str(uid(sample)),
            'dataset_version_id': str(uid(10)), 'split_name': 'val', 'class_index': 0})
    for n in (1, 2):
        samples = [{'sample_id': str(uid(i)), 'label': 0} for i in range(1000, 1105)]
        fixtures['assessment_identities'].append({'id': str(uid(n+30)), 'training_run_id': str(uid(n)),
            'identity': {'samples': samples, 'split': 'val', 'dataset': {'dataset_version_id': str(uid(10))}}})
        fixtures['assessment_attempts'].append({'id': str(uid(n+20)), 'identity_id': str(uid(n+30)),
            'state': 'verified', 'verification': {'count': 105}})
        fixtures['assessment_results'] += [{'attempt_id': str(uid(n+20)), 'sample_id': s['sample_id'],
            'payload': {'label': 0}} for s in samples]
    with read_only_transaction('malaria', repeatable_read=True) as connection:
        class FixtureConnection:
            def execute(self, statement, params):
                sql = str(statement)
                ctes = ','.join(f'{t} AS (SELECT * FROM jsonb_populate_recordset(NULL::public.{t}, CAST(:{t} AS jsonb)))' for t in tables)
                return connection.execute(text(sql.replace('WITH selected AS', 'WITH ' + ctes + ', selected AS', 1)),
                    {**params, **{t: json.dumps(fixtures[t]) for t in tables}})
        repository = AssessmentReadRepository()
        rows = repository.preflight_population(FixtureConnection(), [uid(21), uid(22)])
        assert len(rows) == 2
        assert all(r['retrieved_rows'] == r['expected_unique'] == r['intersection_unique'] == 105 for r in rows)
        assert all(r['ungoverned_count'] == r['missing_count'] == r['label_conflicts'] == 0 for r in rows)
        fixtures['assessment_results'][-1]['payload']['label'] = 1
        rows = repository.preflight_population(FixtureConnection(), [uid(21), uid(22)])
        assert all(r['label_conflicts'] == 1 for r in rows)
        assert rows[1]['declared_label_conflicts'] == rows[1]['ungoverned_count'] == 1
        fixtures['assessment_results'].pop()
        rows = repository.preflight_population(FixtureConnection(), [uid(21), uid(22)])
        assert rows[1]['missing_count'] == 1
        assert rows[0]['intersection_unique'] == 104

@pytest.mark.requires_docker_postgres
def test_postgres_readonly_snapshot_and_savepoint_recovery():
    from app.db import read_only_transaction
    from sqlalchemy import text
    with read_only_transaction('malaria', repeatable_read=True) as c:
        assert c.execute(text('SHOW transaction_read_only')).scalar_one() == 'on'
        assert c.execute(text('SHOW transaction_isolation')).scalar_one() == 'repeatable read'
        snapshot = c.execute(text('SELECT pg_current_snapshot()::text')).scalar_one()
        with pytest.raises(SQLAlchemyError), c.begin_nested():
            c.execute(text('SELECT 1/0'))
        assert c.execute(text('SELECT 42')).scalar_one() == 42
        assert c.execute(text('SELECT pg_current_snapshot()::text')).scalar_one() == snapshot
        # No row can be affected, even if the READ ONLY guard regresses.
        with pytest.raises(SQLAlchemyError, match='read-only'), c.begin_nested():
            c.execute(text('DELETE FROM runs WHERE false'))
        assert c.execute(text('SELECT 42')).scalar_one() == 42

@pytest.mark.requires_docker_postgres
def test_postgres_repository_queries_existing_evidence():
    from app.db import read_only_transaction
    from app.repositories.artifacts import ArtifactReadRepository
    from app.repositories.assessments import AssessmentReadRepository
    from app.repositories.scientific_results import ScientificReadRepository
    from sqlalchemy import text
    with read_only_transaction('malaria', repeatable_read=True) as c:
        repo = ScientificReadRepository()
        run_id = c.execute(text("SELECT id FROM runs WHERE run_type='training' ORDER BY id LIMIT 1")).scalar_one_or_none()
        if run_id is None:
            pytest.skip('No TRAIN persisted; operational evidence unavailable.')
        assert repo.preflight_training(c, run_id)['id'] == run_id
        repo.preflight_configuration(c, run_id)
        repo.preflight_history(c, run_id)
        AssessmentReadRepository().preflight_candidates(c, run_id)
        evaluation_id = c.execute(text('SELECT id FROM evaluations ORDER BY id LIMIT 1')).scalar_one_or_none()
        if evaluation_id:
            assert repo.evaluation(c, evaluation_id)['id'] == evaluation_id
        assert ArtifactReadRepository().get('malaria', str(uid(0)), 'artifacts', connection=c) is None

def test_requested_split_and_checkpoint_conflicts():
    body = request().model_copy(deep=True)
    body.selections[0].split = 'test'
    body.selections[0].checkpoint_artifact_id = uid(42)
    result = run(body=body)
    assert {'REQUESTED_SPLIT_MISMATCH', 'CHECKPOINT_SELECTION_CONFLICT'} <= codes(result)
    assert states(result, 'metrics') == {'NO_COMPARABLE'}

def test_decision_semantics_are_not_inferred_from_equal_metrics():
    e = Evidence()
    e.attempts[uid(22)]['identity']['decision']['positive_class'] = 0
    result = run(e)
    assert states(result, 'metrics') == {'NO_COMPARABLE'}

def test_historical_exact_link_is_checked():
    e = Evidence()
    e.evaluation = lambda c, eid: {'id': eid, 'training_run_id': uid(1), 'run_id': uid(90),
        'source_assessment_attempt_id': uid(21), 'split': 'test', 'checkpoint_artifact_id': uid(41),
        'dataset_version_id': uid(10), 'metric_definition': 'binary_counts_rates_v1'}
    body = request().model_dump()
    body['selections'][0]['evaluation'] = {'source': 'evaluations', 'evaluation_id': uid(80)}
    result = run(e, PreflightRequest.model_validate(body))
    assert result.selections[0].evaluation.value['source'] == 'evaluations'
    assert 'HISTORICAL_LINK_CONFLICT_SPLIT' in codes(result)

def test_historical_without_metrics_is_not_aligned():
    e = Evidence()
    e.comparison_metrics = lambda c, eid: []
    e.comparison_checkpoint = lambda c, rid: None
    e.evaluation = lambda c, eid: {'id': eid, 'training_run_id': uid(1), 'run_id': uid(90),
        'source_assessment_attempt_id': None, 'split': 'val', 'checkpoint_artifact_id': uid(41),
        'dataset_version_id': uid(10), 'metric_definition': 'binary_counts_rates_v1'}
    body = request().model_dump()
    body['selections'][0]['evaluation'] = {'source': 'evaluations', 'evaluation_id': uid(80)}
    result = run(e, PreflightRequest.model_validate(body))
    assert states(result, 'metrics') == {'EVIDENCIA_INSUFICIENTE'}
    assert 'HISTORICAL_RESULTS_UNATTRIBUTED' in codes(result)

def test_checkpoint_metadata_does_not_verify_files_or_hashes():
    e = Evidence()
    result = run(e)
    assert states(result, 'metrics') == {'COMPARABLE'}
    assert all(c.lineage.value and c.registered.value for c in result.checkpoints)
    assert all(c.availability == c.integrity == 'not_checked' for c in result.checkpoints)
    assert '/private/model.keras' not in result.model_dump_json()

def test_missing_and_wrong_train_checkpoint():
    e = Evidence()
    e.get = lambda *args, **kwargs: None
    assert 'CHECKPOINT_UNREGISTERED' in codes(run(e))
    e.get = lambda *args, **kwargs: {'training_run_id': uid(999)}
    assert states(run(e), 'metrics') == {'NO_COMPARABLE'}

def test_invalid_uuid_and_duplicate_training_selections():
    with pytest.raises(ValidationError):
        PreflightRequest.model_validate({'selections': [{'training_run_id': 'not-a-uuid'}]})
    body = request().model_dump()
    body['selections'][1] = body['selections'][0]
    with pytest.raises(ValidationError, match='una sola vez'):
        PreflightRequest.model_validate(body)

def test_proven_split_conflict_survives_auxiliary_sql_error():
    e = Evidence()
    e.attempts[uid(22)]['identity']['split'] = 'test'
    e.fail.add('population')
    result = run(e)
    assert 'NO_COMPARABLE' in states(result, 'metrics')
    assert result.technical_errors
    assert all(err.scope_ids for err in result.technical_errors)
    assert len(result.technical_errors[0].selection_ids) == 2
