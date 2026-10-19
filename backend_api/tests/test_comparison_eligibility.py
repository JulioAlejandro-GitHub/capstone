"""Admission tests use synthetic evidence; audited RUN checks perform SELECT only."""
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
from uuid import UUID, uuid5

import pytest
from fastapi import HTTPException, Response
from sqlalchemy.exc import SQLAlchemyError

from app.services.comparison_eligibility import ComparisonEligibilityService, decision, query_error

RUN = str(UUID(int=101))
VERSION = str(UUID(int=102))


def fixture():
    artifact = dict(run_id=RUN, version_id=VERSION, path='/checkpoint.keras', sha256='a'*64,
                    bytes=100, epoch=2, phase='base')
    training = dict(run_type='training', status='completed', session_state='verified',
                    verification=dict(artifact=artifact, records_hash='b'*64), input_contract={'shape': [None, 1]})
    checkpoint = dict(id=UUID(int=103), run_id=RUN, path=artifact['path'], checksum=artifact['sha256'],
                      file_size_bytes=100, metadata=dict(epoch=2, phase='base'),
                      selection=dict(selected_epoch=2, phase='base'))
    model = dict(training_run_id=RUN, model_version_id=VERSION,
                 checkpoint_artifact_id=str(uuid5(UUID(VERSION), 'e5-selected-checkpoint')),
                 path=artifact['path'], sha256=artifact['sha256'], bytes=100,
                 input_contract=training['input_contract'],
                 source=dict(kind='e5_selected_record', epoch=2, records_hash='b'*64))
    attempts = [dict(kind=kind, identity_id=UUID(int=i), attempt_id=UUID(int=i+10),
                     state='verified', finished_at='2026-10-19', result_count=1, expected_count=1,
                     artifact_count=2 if kind == 'explain' else 0,
                     identity=dict(model=deepcopy(model), split='val', decision={'effective': .4}),
                     verification=dict(count=1, sha256='c'*64, artifacts_hash='d'*64))
                for i, kind in enumerate(('evaluate', 'explain'), 1)]
    return training, checkpoint, attempts


def test_complete_val_and_partial_explain_coverage():
    assert decision(RUN, *fixture())['eligible']


@pytest.mark.parametrize('stage', ['evaluate', 'explain'])
def test_no_independent_assessment_including_training_validation_final(stage):
    train, checkpoint, attempts = fixture()
    # training_validation_final belongs to evaluations, never an assessment substitute.
    result = decision(RUN, train, checkpoint, [a for a in attempts if a['kind'] != stage])
    assert not result['eligible']
    assert result['reasons'][0]['code'] == f'{stage.upper()}_NOT_EXECUTED'


@pytest.mark.parametrize('stage', [0, 1])
@pytest.mark.parametrize('field,value', [('state', None), ('state', 'failed'), ('state', 'active'),
    ('result_count', 0), ('finished_at', None), ('verification', None), ('expected_count', 2)])
def test_invalid_attempts(stage, field, value):
    train, checkpoint, attempts = fixture()
    attempts[stage][field] = value
    assert not decision(RUN, train, checkpoint, attempts)['eligible']


@pytest.mark.parametrize('count', [0, 1, 3])
def test_explain_artifacts_required(count):
    train, checkpoint, attempts = fixture()
    attempts[1]['artifact_count'] = count
    assert not decision(RUN, train, checkpoint, attempts)['eligible']


@pytest.mark.parametrize('field,value', [('sha256', 'x'*64), ('bytes', 999), ('training_run_id', str(UUID(int=999))),
                                       ('checkpoint_artifact_id', str(UUID(int=999)))])
def test_checkpoint_conflicts(field, value):
    train, checkpoint, attempts = fixture()
    attempts[1]['identity']['model'][field] = value
    result = decision(RUN, train, checkpoint, attempts)
    assert not result['eligible']
    assert result['reasons'][0]['code'] == 'INCOMPATIBLE_LINEAGE'


def test_failed_training_and_unregistered_checkpoint():
    train, checkpoint, attempts = fixture()
    train['status'] = 'failed'
    assert not decision(RUN, train, checkpoint, attempts)['eligible']
    assert not decision(RUN, fixture()[0], None, attempts)['eligible']


def test_attempts_never_combine_and_valid_alternative_wins():
    train, checkpoint, attempts = fixture()
    other = deepcopy(attempts[1])
    attempts[1]['artifact_count'] = 0
    other['result_count'] = 0
    assert not decision(RUN, train, checkpoint, attempts + [other])['eligible']
    assert decision(RUN, train, checkpoint, attempts + [other, fixture()[2][1]])['eligible']


def test_test_optional_threshold_and_software_do_not_gate():
    train, checkpoint, attempts = fixture()
    test = deepcopy(attempts[0])
    test['identity']['split'] = 'test'
    attempts[1]['identity']['software'] = {'commit': 'different'}
    attempts[0]['identity']['decision']['effective'] = .5
    assert decision(RUN, train, checkpoint, attempts)['eligible']
    assert decision(RUN, train, checkpoint, attempts + [test])['eligible']


def test_query_error_is_not_absence():
    @contextmanager
    def unavailable(*args, **kwargs):
        raise SQLAlchemyError('private database detail')
        yield
    service = ComparisonEligibilityService(transaction=unavailable)
    result = service.read([RUN], 'malaria')[RUN]
    assert result == query_error(RUN)
    with pytest.raises(HTTPException) as error:
        service.require([SimpleNamespace(training_run_id=RUN)], 'malaria')
    assert error.value.status_code == 503
    assert 'private' not in str(error.value.detail)


@pytest.mark.parametrize('route', ['scientific_preflight', 'scientific_report'])
def test_http_boundary_rejects_bypassed_selector(monkeypatch, route):
    from app.routes import scientific_preflight as routes
    service = ComparisonEligibilityService()
    monkeypatch.setattr(service, 'read', lambda *args: {RUN: decision(RUN, None, None, [])})
    monkeypatch.setattr(routes, 'ComparisonEligibilityService', lambda: service)
    with pytest.raises(HTTPException) as error:
        getattr(routes, route)(SimpleNamespace(selections=[SimpleNamespace(training_run_id=RUN)]),
                              Response(), None, 'malaria')
    assert error.value.status_code == 422
    assert error.value.detail['code'] == 'RUN_NOT_ELIGIBLE'


@pytest.mark.requires_docker_postgres
def test_audited_runs_are_eligible_read_only():
    ids = ['338136db-a207-47fc-bbf3-d17ce85c0dc2', 'bbbd5b60-afaa-4034-a504-a60ed642aafe']
    results = ComparisonEligibilityService().read(ids, 'malaria')
    assert all(r['eligible'] for r in results.values()), results
    assert len(results[ids[0]]['evidence']['evaluate']) == 2
    assert len(results[ids[1]]['evidence']['evaluate']) == 1

@pytest.mark.requires_docker_postgres
def test_audited_val_population_and_threshold_warning():
    from sqlalchemy import text
    from app.db import read_only_transaction
    from app.schemas.scientific_preflight import PreflightRequest
    from app.services.scientific_preflight import ScientificPreflightService
    identities = ['08b0b61e-8733-4c5c-9924-49ccc1e10a2f', '9aa0bef7-a699-4ca2-9f45-a50a562ea205']
    with read_only_transaction('malaria') as c:
        assert c.execute(text('SHOW transaction_read_only')).scalar_one() == 'on'
        rows = list(c.execute(text('''
            SELECT i.id,i.training_run_id,a.id AS attempt_id,i.identity
            FROM assessment_identities i JOIN assessment_attempts a ON a.identity_id=i.id
            WHERE i.id=ANY(CAST(:ids AS uuid[])) AND a.state='verified' ORDER BY i.id
        '''), {'ids': identities}).mappings())
    populations = [{s['sample_id']: (s['label'], s['sha256']) for s in r['identity']['samples']} for r in rows]
    assert len(rows) == 2
    assert len(populations[0]) == len(populations[1]) == 2693
    assert populations[0] == populations[1]
    assert {r['identity']['decision']['effective'] for r in rows} == {.4, .5}
    request = PreflightRequest(selections=[dict(training_run_id=r['training_run_id'], split='val',
        evaluation=dict(source='assessment', identity_id=r['id'], attempt_id=r['attempt_id'])) for r in rows])
    result = ScientificPreflightService().read(request, 'malaria', 'scc-eligibility-audit')
    payload = result.model_dump(mode='json')
    import json
    serialized = json.dumps(payload, ensure_ascii=False)
    assert 'PROTOCOL_DIFFERENCE_DECISION' in serialized
    assert 'Umbrales efectivos diferentes' in serialized
    assert not payload['technical_errors']
    assert 'CHECKPOINT_UNREGISTERED' not in serialized
    assert next(d for d in payload['dimensions'] if d['dimension'] == 'A5')['verdict']['scientific_state'] == 'COMPARABLE'

@pytest.mark.requires_docker_postgres
def test_sql_failure_keeps_other_runs_and_read_only_transaction():
    from sqlalchemy import text
    from app.repositories.assessments import AssessmentReadRepository
    ids = ['338136db-a207-47fc-bbf3-d17ce85c0dc2', 'bbbd5b60-afaa-4034-a504-a60ed642aafe']

    class FailingRead(AssessmentReadRepository):
        def eligibility_training(self, connection, run_id):
            assert connection.execute(text('SHOW transaction_read_only')).scalar_one() == 'on'
            if run_id == ids[0]:
                connection.execute(text('SELECT 1/0'))
            return super().eligibility_training(connection, run_id)

    result = ComparisonEligibilityService(assessments=FailingRead()).read(ids, 'malaria')
    assert result[ids[0]] == query_error(ids[0])
    assert result[ids[1]]['eligible']
