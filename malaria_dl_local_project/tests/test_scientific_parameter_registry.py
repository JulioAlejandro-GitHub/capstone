"""C2: synthetic contracts and exact scientific equivalence; no datasets or DB."""
from copy import deepcopy
import ast
from pathlib import Path

import pytest

from src.malaria_dl.models import registry
from src.malaria_dl.models.configuration import resolve_config
from src.malaria_dl.models.scientific_parameters import (
    PARAMETERS, OPTIMIZER_DEFAULTS, compare_runs, defaults_by_model,
    effective_values, flatten,
)
from src.malaria_dl.evaluation.calibration_controller import CalibrationController
from src.malaria_dl.evaluation.threshold_calibration import find_threshold_for_target_recall
from src.malaria_dl.evaluation.validation import evaluate_validation_predictions
from src.malaria_dl.results.training import ThresholdResult


@pytest.fixture(autouse=True)
def synthetic_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(registry, 'registered_models', lambda: tuple(registry.MODEL_REGISTRY))


def snapshot(enabled: bool = False, **options: object) -> dict:
    return resolve_config('custom_cnn', overrides={'execution': {
        'calibrate_threshold': enabled, 'evaluate_best_on_test': False, **options,
    }})


def test_dictionary_covers_contract_leaves_and_dependencies() -> None:
    for model, cfg in defaults_by_model().items():
        for section in ('model', 'execution', 'recipe'):
            assert set(flatten({section: cfg[section]})) <= PARAMETERS.keys()
        resolved = resolve_config(model)['resolved']
        governed = {k: v for k, v in resolved.items() if k != 'input_contract'}
        assert set(flatten(governed)) <= PARAMETERS.keys()
    for values in OPTIMIZER_DEFAULTS.values():
        assert {'optimizer.parameters.' + key for key in values} <= PARAMETERS.keys()
    for parameter in PARAMETERS.values():
        assert set(parameter.related) <= PARAMETERS.keys()
        assert parameter.restriction and parameter.condition and parameter.effect
        assert set(parameter.relations) <= {'Configuración', 'Dependencia', 'Cálculo', 'Selección', 'Persistencia'}


def test_code_references_resolve_to_actual_symbols() -> None:
    root = Path(__file__).resolve().parents[1] / 'src/malaria_dl'
    for parameter in PARAMETERS.values():
        for reference in (parameter.contract, *parameter.consumers):
            file, symbol = reference.split(':')
            tree = ast.parse((root / file).read_text())
            for name in symbol.split('.'):
                tree = next(node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name)


def test_persisted_comparison_never_backfills_or_mutates() -> None:
    historical = {'execution': {'target_recall': .91, 'min_specificity': None}, 'legacy': {'flag': 7}}
    current = snapshot(True)['resolved']
    before = deepcopy(historical)
    result = compare_runs({'old-run': historical, 'new-run': current})
    assert result['execution.target_recall']['old-run']['value'] == .91
    assert result['execution.target_recall']['new-run']['value'] == .98
    assert result['execution.min_specificity']['old-run']['present']
    assert not result['execution.beta']['old-run']['present']
    assert result['legacy.flag']['old-run'] == {'present': True, 'value': 7, 'governed': False}
    assert historical == before
    assert effective_values({})['execution.target_recall']['present'] is False


@pytest.mark.parametrize('labels,scores,options', [
    ([0,0,1,1], [.1,.8,.6,.9], {}),
    ([0,1], [.8,.2], {'min_specificity': 1.0}),
    ([0,0], [.2,.8], {}),
    ([0,1], [.0,.01], {}),
    ([0,1,1], [.5,.5,1.0], {'target_recall': 1.0}),
    ([0]+[1]*50, [.2]+[.9]*49+[.1], {'target_recall': .98}),
])
def test_controller_exactly_preserves_science(labels: list, scores: list, options: dict) -> None:
    config = snapshot(True, **options)
    before = deepcopy(config)
    e = config['resolved']['execution']
    direct = find_threshold_for_target_recall(labels, scores, target_recall=e['target_recall'],
                                             min_specificity=e['min_specificity'], beta=e['beta'])
    controller = CalibrationController(config)
    result = controller.calibrate(labels, scores)
    # Timestamp is observational metadata; every scientific field is compared.
    direct.pop('created_at')
    result.pop('created_at')
    assert result == direct
    assert controller.threshold(result) == ThresholdResult(direct['threshold_used'], direct['threshold_source'])
    assert evaluate_validation_predictions(labels, scores, controller.threshold(result)) == evaluate_validation_predictions(
        labels, scores, ThresholdResult(direct['threshold_used'], direct['threshold_source']))
    assert config == before


def test_disabled_does_not_call_calibrator(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError('Calibration must stay disabled')
    monkeypatch.setattr('src.malaria_dl.evaluation.calibration_controller.find_threshold_for_target_recall', forbidden)
    controller = CalibrationController(snapshot())
    result = controller.calibrate([0, 1], [.1, .8])
    assert result == {'enabled': False, 'threshold': .5}
    assert controller.threshold(result) == ThresholdResult(.5, 'default')


@pytest.mark.parametrize('enabled', [False, True])
def test_controller_rejects_test_without_loading_data(enabled: bool) -> None:
    with pytest.raises(ValueError):
        CalibrationController(snapshot(enabled)).calibrate([], [], split='test')


@pytest.mark.parametrize('options', [
    {'beta': 1}, {'target_recall': 1.1}, {'min_specificity': -1},
    {'min_class_fraction': .6}, {'calibrate_threshold': 'true'},
    {'checkpoint_policy': 'new_policy'},
])
def test_new_request_reuses_existing_validation(options: dict) -> None:
    with pytest.raises(ValueError) as expected:
        resolve_config('custom_cnn', overrides={'execution': options})
    with pytest.raises(ValueError) as actual:
        CalibrationController.from_request('custom_cnn', overrides={'execution': options})
    assert str(actual.value) == str(expected.value)


def test_persistence_snapshot_is_exact_and_queryable() -> None:
    from src.malaria_dl.persistence import v2_projection
    from unittest.mock import patch
    config = snapshot(True, target_recall=.93)
    with patch.object(v2_projection, '_insert') as insert:
        v2_projection.project_configuration(object(), 'synthetic-run', config)
    row = insert.call_args.args[2]
    assert row['provenance_snapshot'] == config
    assert row['extension_configuration'] == config['resolved']
    assert effective_values(row['extension_configuration'])['execution.target_recall']['value'] == .93


@pytest.mark.parametrize('enabled', [False, True])
@pytest.mark.parametrize('emitting', [False, True])
def test_train_integration_with_scientific_doubles(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, enabled: bool, emitting: bool,
) -> None:
    from uuid import UUID, uuid4
    from docker_train_fixture import install_science, MemoryRepository
    from src.malaria_dl.execution.train import train
    from src.malaria_dl.execution.contracts import RunEventType
    from src.malaria_dl.execution.emitter import RunEventEmitter
    from test_docker_train_integration import Recorder

    descriptor, trace = install_science(monkeypatch)
    config = snapshot(enabled, max_epochs=2)
    session = {'run_id': str(uuid4()), 'owner': str(uuid4()),
               'configuration': config, 'artifact_root': str(tmp_path / 'artifacts'),
               'dataset': {'dataset_root': str(tmp_path / 'synthetic')}}
    repo = MemoryRepository(session, trace)
    recorder = Recorder(trace)
    emitter = RunEventEmitter(recorder, run_id=UUID(session['run_id']), attempt_id=uuid4()) if emitting else None
    train(repo, session, descriptor, event_emitter=emitter)
    evidence = next(row['payload'] for row in repo.rows if row['kind'] == 'calibration')
    assert evidence['checkpoint_epoch'] == session['completion']['selection']['selected_epoch']
    assert all(sample['sample'].startswith('val/') for sample in evidence['samples'])
    result = deepcopy(evidence['result'])
    if enabled:
        expected = find_threshold_for_target_recall([0, 1], [.1, .9], target_recall=.98, min_specificity=None, beta=2)
        expected.pop('created_at')
        result.pop('created_at')
        assert result == expected
        decision = ThresholdResult(expected['threshold_used'], expected['threshold_source'])
    else:
        assert result == {'enabled': False, 'threshold': .5}
        decision = ThresholdResult(.5, 'default')
    if emitting:
        final = next(event for event in recorder.events if event.event_type == RunEventType.EVALUATION_COMPLETED)
        assert final.to_dict()['payload'] == evaluate_validation_predictions([0, 1], [.1, .9], decision).to_dict()
        assert sum(event.event_type == RunEventType.CALIBRATION_COMPLETED for event in recorder.events) == int(enabled)
    assert session['state'] == 'completed'
    assert [item for item in trace if item[0] == 'dataset'] == [('dataset', 'train'), ('dataset', 'val')]
