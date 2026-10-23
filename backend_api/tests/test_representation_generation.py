"""REPRESENT contracts: identity, status, queue dispatch and CKA. These doubles do not certify the model runtime."""
from uuid import uuid4
from unittest.mock import Mock
import numpy as np
import pytest
from app.schemas.explain_generation import ExplainRequest
from app.schemas.representation_generation import RepresentRequest
from app.services import explain_agent
from app.services.representation_generation import RepresentService, request_key
from app.services.scientific_representations import cka_matrix, representation_evidence
from src.malaria_dl.assessment.contracts import identity
from src.malaria_dl.assessment.representation import linear_cka, representation_spec


def source_identity(kind='evaluate'):
    sample = {'sample_id': str(uuid4()), 'patient_id': str(uuid4()), 'label': 1, 'split': 'val', 'sha256': 'a' * 64,
              'relative_path': 'val/x.png'}
    value = {'kind': kind, 'model': {'training_run_id': str(uuid4()), 'checkpoint_artifact_id': str(uuid4())},
             'dataset': {'dataset_version_id': str(uuid4())}, 'samples': [sample], 'split': 'val',
             'purpose': 'development', 'protocol': {'version': 'x'}, 'decision': {'requested': 'auto', 'effective': 0.5},
             'seed': 42, 'batch_size': 8}
    if kind == 'represent':
        value['representation'] = representation_spec()
    return value


@pytest.fixture
def service():
    repository = Mock()
    source = source_identity()
    repository.source.return_value = {'state': 'verified', 'identity': source}
    repository.represent_candidates.return_value = []
    repository.represent_requests.return_value = []
    return RepresentService(repository), RepresentRequest(source_attempt_id=uuid4()), source


def binding():
    return {'training_run_id': str(uuid4()), 'input_contract': {
        'schema_version': 1, 'architecture': 'custom_cnn', 'shape': [None, 64, 64, 3], 'dtype': 'float32',
        'color_mode': 'rgb', 'external': {'mode': 'scale_0_1'}, 'internal_preprocessing': None,
        'output': {'shape': [None, 1], 'activation': 'sigmoid', 'meaning': 'probability_parasitized'},
        'label_mapping': {'uninfected': 0, 'parasitized': 1, 'positive_class': 1}}}


def test_only_represent_identity_carries_the_specification(monkeypatch):
    monkeypatch.setattr('src.malaria_dl.assessment.contracts.validate_input_contract', lambda contract: None)
    arguments = dict(split='val', purpose='development', protocol={'version': 'x', 'splits': ['val'], 'purposes': ['development']},
                     decision={'effective': 0.5}, code={}, seed=1, batch_size=4)
    samples = source_identity()['samples']
    evaluate = identity(binding(), {}, samples, **arguments)
    represent = identity(binding(), {}, samples, representation=representation_spec(), **arguments)
    # Historical EVALUATE/EXPLAIN identities (and their hashes) must not gain a key.
    assert evaluate['kind'] == 'evaluate' and 'representation' not in evaluate
    assert represent['kind'] == 'represent' and represent['representation'] == representation_spec()
    with pytest.raises(ValueError):
        identity(binding(), {}, samples, explanation={'method': 'gradcam'}, representation=representation_spec(), **arguments)


def test_source_must_be_a_verified_evaluate(service):
    represent, request, source = service
    represent.repository.source.return_value = {'state': 'verified', 'identity': {**source, 'kind': 'explain'}}
    with pytest.raises(ValueError, match='REPRESENT_SOURCE_NOT_EVALUATE'):
        represent.state(request, True)


def test_state_reports_queue_then_attempt(service):
    represent, request, source = service
    assert represent.state(request, False)['state'] == 'not_executed'
    represent.repository.represent_requests.return_value = [{'id': uuid4(), 'state': 'queued', 'cause': None}]
    assert represent.state(request, False)['state'] == 'pending'
    row = {'id': uuid4(), 'state': 'verified', 'identity': {**source_identity('represent'), **{k: source[k] for k in source if k != 'kind'}}}
    represent.repository.represent_candidates.return_value = [row]
    state = represent.state(request, True)
    assert state['state'] == 'completed' and state['attempt_id'] == str(row['id'])


def test_attempt_of_another_population_is_not_reused(service):
    represent, request, source = service
    other = {**source_identity('represent'), **{k: source[k] for k in source if k not in ('kind', 'samples')}}
    represent.repository.represent_candidates.return_value = [{'id': uuid4(), 'state': 'verified', 'identity': other}]
    assert represent.state(request, True)['state'] == 'not_executed'


def test_queue_key_is_stable_and_distinct_from_explain():
    source = uuid4()
    assert request_key(RepresentRequest(source_attempt_id=source)) == request_key(RepresentRequest(source_attempt_id=source))
    with pytest.raises(ValueError):
        ExplainRequest.model_validate({'source_attempt_id': str(source), 'sample_id': str(uuid4()), 'operation': 'represent'})


def test_agent_dispatches_represent_rows():
    queue, seen = Mock(), []
    job = {'id': uuid4(), 'actor': 'a', 'request': RepresentRequest(source_attempt_id=uuid4()).model_dump(mode='json')}
    assert explain_agent.serve_one(queue, job, lambda request, actor, ack: seen.append(type(request)), str) == 'completed'
    assert seen == [RepresentRequest]


def test_linear_cka_is_invariant_to_rotation_and_scale():
    x = np.random.default_rng(0).normal(size=(120, 16))
    rotation, _ = np.linalg.qr(np.random.default_rng(1).normal(size=(16, 16)))
    assert linear_cka(x, 4 * x @ rotation) == pytest.approx(1.0)
    assert linear_cka(x, np.random.default_rng(2).normal(size=(120, 8))) < 0.5


def test_cka_uses_only_common_samples_in_the_same_order():
    x = np.random.default_rng(3).normal(size=(50, 6))
    ids = [str(k).zfill(3) for k in range(50)]
    left = {'samples': ids, 'embeddings': x}
    # Same vectors, reversed order and one extra sample: CKA must realign them by sample id.
    right = {'samples': ids[::-1] + ['extra'], 'embeddings': np.vstack([x[::-1], np.ones((1, 6))])}
    result = cka_matrix([left, right, None])
    assert result['values'][0][1] == pytest.approx(1.0)
    assert result['common'][0][1] == 50 and result['values'][0][2] is None


def test_historical_evaluation_has_no_representation():
    selection = Mock(training_run_id=uuid4(), evaluation=Mock(source='evaluations'))
    dto, matrix = representation_evidence(Mock(), None, selection)
    assert dto['state'] == 'missing' and matrix is None and dto['issues']
