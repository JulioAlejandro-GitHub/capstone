"""SCC-REPORT-SCI.1: synthetic edge cases and SELECT-only operational regression."""
import math
from contextlib import contextmanager
from copy import deepcopy
from uuid import UUID

import httpx
import pytest
from app.main import app
from app.schemas.scientific_report import ScientificReportRequest
from app.services.scientific_report import (
    ScientificReportService,
    checkpoint_evidence,
    consensus,
    population_coverage,
    superiority_answer,
    validate_samples,
)
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError


def sample(name, label, score):
    return {'sample': name, 'label': label, 'score': score}


def valid_population():
    return [sample('a', 0, .1), sample('b', 1, .5), sample('c', 1, .4)]


def expected():
    return {'tn': 1, 'fp': 0, 'fn': 1, 'tp': 1, 'sample_count': 3}


def test_threshold_equality_and_confusion_reconstruction():
    population, counts, issues = validate_samples(valid_population(), .5, expected())
    assert not issues
    assert counts == {'tn': 1, 'fp': 0, 'fn': 1, 'tp': 1}
    assert population['b']['prediction'] == 1


@pytest.mark.parametrize('score', [None, -1, 1.1, math.nan, math.inf, 'invalid', True])
def test_invalid_scores_are_not_silently_discarded(score):
    values = valid_population()
    values[0]['score'] = score
    assert validate_samples(values, .5, expected())[2]


@pytest.mark.parametrize('threshold', [None, -1, 1.1, math.nan, True])
def test_invalid_threshold_is_not_defaulted(threshold):
    assert validate_samples(valid_population(), threshold, expected())[2]


def test_duplicate_and_confusion_mismatch_are_explicit():
    values = valid_population()
    assert 'Predicciones duplicadas.' in validate_samples(values + [values[0]], .5, expected())[2]
    assert validate_samples(values, .5, dict(expected(), tn=2))[2]


def test_alignment_is_by_identity_not_position_and_oracle_is_descriptive():
    a, _, _ = validate_samples(valid_population(), .5, expected())
    b = deepcopy(a)
    b['b'].update(score=.4, prediction=0, correct=False)
    b['c'].update(score=.9, prediction=1, correct=True)
    b = dict(reversed(list(b.items())))
    result = consensus([a, b], [.5, .5])
    assert result['oracle'] == {'numerator': 3, 'denominator': 3, 'ratio': 1}
    assert result['distribution']['CONSENSUS_TN'] == 1
    assert result['distribution']['disagreement'] == 2
    assert result['exclusive_errors'] == [1, 1]
    assert result['exclusive_correct'] == [1, 1]
    assert result['agreement'] == [[3, 1], [1, 3]]
    assert result['all_wrong'] == 0
    assert 'no modelo desplegable' in result['definitions']['oracle']


def test_label_conflicts_outside_intersection_are_detected():
    a, _, _ = validate_samples(valid_population(), .5, expected())
    b, c = deepcopy(a), deepcopy(a)
    b['b']['label'] = 0
    del c['b']
    assert consensus([a, b, c], [.5]*3)['state'] == 'incompatible'


def test_partial_population_pagination_filters_and_missing():
    a, _, _ = validate_samples(valid_population(), .5, expected())
    b = deepcopy(a)
    del b['c']
    result = consensus([a, b], [.5, .5], offset=1, limit=1)
    assert result['common_count'] == 2
    assert result['coverage'][0]['ratio'] == 2/3
    assert result['coverage'][1]['missing'] == 1
    assert len(result['samples']) == 1
    assert consensus([a,b], [.5,.5], category='CONSENSUS_TN')['total'] == 1
    assert consensus([a, {}], [.5,.5])['state'] == 'incompatible'
    assert population_coverage([a, b])['common_count'] == 2


def test_checkpoint_requires_epoch_phase_and_train_agreement_not_bytes():
    record = {'id': 'artifact', 'run_id': 'run', 'checksum': 'registered', 'metadata': {'epoch': 14, 'phase': 'base'},
                  'selection': {'selected_epoch': 14, 'phase': 'base', 'policy': 'policy', 'selected_metric': 'metric'}}
    evidence = checkpoint_evidence(record, 'run')
    assert evidence['logical_lineage']
    assert evidence['physical_checksum'] == evidence['file_availability'] == 'not_checked'
    assert not checkpoint_evidence(record, 'other')['logical_lineage']
    record['metadata']['epoch'] = 26
    assert not checkpoint_evidence(record, 'run')['logical_lineage']


@contextmanager
def broken_transaction(*args, **kwargs):
    raise SQLAlchemyError('private password SQL')
    yield


def test_sql_error_is_not_scientific_absence():
    request = ScientificReportRequest(module='curves', selections=[{'training_run_id': UUID(int=1)}])
    with pytest.raises(HTTPException) as error:
        ScientificReportService(transaction=broken_transaction).read(request, 'malaria')
    assert error.value.status_code == 503
    assert 'password' not in error.value.detail


@pytest.mark.anyio
async def test_report_requires_authentication():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        response = await client.post('/models/comparison/report', json={'module': 'curves', 'selections': [{'training_run_id': str(UUID(int=1))}]})
    assert response.status_code in (401,403)


def test_val_predictions_cannot_be_used_for_test_or_wrong_role():
    service = ScientificReportService()
    selection = ScientificReportRequest(module='consensus', selections=[{'training_run_id': UUID(int=1)}]).selections[0]
    for split, role in [('test','training_validation_final'), ('val','independent_evaluate')]:
        population, issues = service.prediction_population(None, selection, {'state': 'available', 'evaluation': {'split':split, 'evaluation_role':role}})
        assert population == {} and issues


def test_no_implicit_execution_dependencies():
    from pathlib import Path
    source = Path('app/services/scientific_report.py').read_text()
    for forbidden in ('tensorflow', 'subprocess', 'load_model', 'fit(', 'predict(', 'run_evaluate', 'run_explain'):
        assert forbidden not in source


def test_operational_audited_runs_read_only():
    ids = ['565a1dac-9c51-411b-a76c-efeb1d38722c','a1c310c5-1cb0-4b1e-afc4-b087ed13ab24',
           'c96bb5c1-1edb-4ef3-9854-fd715c4025f4','cc925f74-3535-40e0-9060-23a06cea8024']
    service = ScientificReportService()
    selections = [{'training_run_id': i} for i in ids]
    try:
        catalog = service.read(ScientificReportRequest(module='catalog', selections=selections), 'malaria').data
    except HTTPException as error:
        if error.status_code == 404:
            pytest.skip('Audited runs are not present in this database.')
        raise
    for selection, run in zip(selections, catalog):
        evaluation = next(e for e in run['evaluations'] if e['evaluation_role'] == 'training_validation_final')
        selection['evaluation'] = {'source': 'evaluations', 'evaluation_id': evaluation['evaluation_id']}
        assert run['governance']['counts'] == {'train': 22180, 'val': 2693, 'test': 2685}
        assert run['governance']['materialization_dataset_matches']
    curves = service.read(ScientificReportRequest(module='curves', selections=selections), 'malaria').data
    assert [r['executed_epochs'] for r in curves] == [26,16,14,31]
    assert [r['checkpoint']['selected_epoch'] for r in curves] == [14,4,2,19]
    metrics = service.read(ScientificReportRequest(module='metrics', selections=selections), 'malaria').data
    assert [r['clinical']['accuracy'] for r in metrics['runs']] == pytest.approx([.954697,.934645,.949127,.946899], abs=1e-6)
    assert [[r['clinical'][k] for k in ('tn','fp','fn','tp')] for r in metrics['runs']] == [[1340,28,94,1231],[1326,42,134,1191],[1311,57,80,1245],[1336,32,111,1214]]
    result = service.read(ScientificReportRequest(module='consensus', selections=selections, limit=5), 'malaria').data
    assert result['state'] == 'available'
    assert result['common_count'] == 2693 and result['label_conflicts'] == 0
    assert result['oracle']['numerator'] == 2616 and result['all_wrong'] == 77
    assert result['distribution']['disagreement'] == 146
    assert len(result['samples']) == 5
    from app.schemas.scientific_preflight import PreflightRequest
    from app.services.scientific_preflight import ScientificPreflightService
    preflight = ScientificPreflightService().read(PreflightRequest(selections=selections), 'malaria', 'test-report')
    assert not preflight.technical_errors
    assert preflight.populations[0].intersection_unique.value == 2693
    assert all(a.verdict.scientific_state in ('COMPARABLE','COMPARABLE_CON_ADVERTENCIAS') for a in preflight.analyses if a.module_id in ('curves','metrics','consensus'))


def test_cross_run_evaluation_and_split_mismatch_rejected():
    from app.schemas.scientific_preflight import RequestedSelection
    class Repository:
        def evaluation(self, connection, evaluation_id):
            return {'training_run_id': UUID(int=2), 'split': 'val', 'checkpoint_artifact_id': UUID(int=3)}
    service = ScientificReportService(repository=Repository())
    selected = RequestedSelection(training_run_id=UUID(int=1), evaluation={'source':'evaluations','evaluation_id':UUID(int=4)})
    with pytest.raises(HTTPException) as error:
        service.historical(None, selected)
    assert error.value.status_code == 404
    selected.training_run_id = UUID(int=2)
    selected.split = 'test'
    with pytest.raises(HTTPException) as error:
        service.historical(None, selected)
    assert error.value.status_code == 422


def test_predictions_require_one_exact_selected_event():
    from app.schemas.scientific_preflight import RequestedSelection
    class Repository:
        def __init__(self):
            self.events = []
        def preflight_configuration(self, connection, run_id):
            return {'extension_configuration': {'input_contract': {'output': {'meaning':'probability_parasitized'}, 'label_mapping': {'positive_class':1}}}}
        def comparison_predictions(self, connection, run_id, epoch, phase):
            assert (epoch, phase) == (14, 'base')
            return self.events
    repo = Repository()
    service = ScientificReportService(repository=repo)
    selection = RequestedSelection(training_run_id=UUID(int=1))
    metric = {'state':'available', 'evaluation':{'split':'val','evaluation_role':'training_validation_final','threshold_used':.5},
              'checkpoint':{'selected_epoch':14,'phase':'base'}, 'clinical':expected()}
    assert service.prediction_population(None, selection, metric)[1]
    repo.events = [{'samples': valid_population()}]
    assert not service.prediction_population(None, selection, metric)[1]
    repo.events *= 2
    assert service.prediction_population(None, selection, metric)[1]


@pytest.mark.anyio
async def test_report_permission_failure_happens_before_read(monkeypatch):
    from app.routes import scientific_preflight
    from app.security import Permission, Principal, current_principal
    def forbidden(*args):
        raise AssertionError('Must not read without all permissions')
    monkeypatch.setattr(scientific_preflight.ScientificReportService, 'read', forbidden)
    app.dependency_overrides[current_principal] = lambda: Principal('user', 'tester', (), frozenset({Permission.RUNS_READ}), False)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            response = await client.post('/models/comparison/report', json={'module':'metrics','selections':[{'training_run_id':str(UUID(int=1))}]})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(current_principal, None)


def test_superiority_answer_matches_evaluated_split():
    assert 'Las métricas TEST' in superiority_answer({'test'})
    assert 'McNemar' in superiority_answer({'test'})
    assert superiority_answer({'val'}) == 'No se infiere generalización TEST ni superioridad estadística desde VALIDATION.'
    assert 'VALIDATION' in superiority_answer({'val', 'test'})
    assert 'Sin evaluación atribuible común' in superiority_answer(set())


def test_single_run_consensus_is_that_model_errors():
    population = {'a': {'label': 1, 'score': .9, 'prediction': 1, 'correct': True},
                  'b': {'label': 0, 'score': .7, 'prediction': 1, 'correct': False},
                  'c': {'label': 1, 'score': .2, 'prediction': 0, 'correct': False},
                  'd': {'label': 0, 'score': .05, 'prediction': 0, 'correct': True}}
    result = consensus([population], [.5], category='CONSENSUS_FP')
    assert result['state'] == 'available'
    assert result['distribution'] == {'CONSENSUS_TP': 1, 'CONSENSUS_TN': 1, 'CONSENSUS_FP': 1, 'CONSENSUS_FN': 1, 'disagreement': 0}
    assert [s['sample'] for s in result['samples']] == ['b'] and result['total'] == 1
    assert result['oracle']['numerator'] == 2 and result['agreement'] == [[4]]
    assert consensus([], [])['state'] == 'missing'


def test_consensus_sorts_the_whole_filtered_population_before_paging():
    population = {name: {'label': label, 'score': score, 'prediction': int(score >= .5), 'correct': int(score >= .5) == label}
                  for name, label, score in [('a', 1, .9), ('b', 0, .7), ('c', 1, .2), ('d', 0, .05)]}
    page = consensus([population], [.5], offset=0, limit=2, sort_by='run-0', sort_desc=True)
    assert [s['sample'] for s in page['samples']] == ['a', 'b'] and page['total'] == 4
    page = consensus([population], [.5], offset=2, limit=2, sort_by='run-0', sort_desc=True)
    assert [s['sample'] for s in page['samples']] == ['c', 'd']
    assert [s['sample'] for s in consensus([population], [.5], sort_by='label')['samples']] == ['b', 'd', 'a', 'c']
    with pytest.raises(ValueError):
        ScientificReportRequest(module='consensus', selections=[{'training_run_id': UUID(int=1)}], sort_by='score; drop')


def test_consensus_column_filters_apply_to_the_whole_population_before_paging():
    population = {name: {'label': label, 'score': score, 'prediction': int(score >= .5), 'correct': int(score >= .5) == label}
                  for name, label, score in [('img_a', 1, .9), ('img_b', 0, .7), ('cell_c', 1, .2), ('cell_d', 0, .05)]}
    assert [s['sample'] for s in consensus([population], [.5], sample_query='CELL')['samples']] == ['cell_c', 'cell_d']
    assert [s['sample'] for s in consensus([population], [.5], label=0)['samples']] == ['cell_d', 'img_b']
    page = consensus([population], [.5], limit=1, score_ranges={0: (.1, None)}, sort_by='run-0')
    assert [s['sample'] for s in page['samples']] == ['cell_c'] and page['total'] == 3
    assert consensus([population], [.5], label=1, score_ranges={0: (None, .5)})['total'] == 1
    with pytest.raises(ValueError):
        ScientificReportRequest(module='consensus', selections=[{'training_run_id': UUID(int=1)}], score_ranges={10: (0, 1)})
