"""EXEC.1 uses synthetic predictions and mocks; never opens the official dataset."""
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4
import subprocess
import sys
from pathlib import Path

import pytest
from src.malaria_dl.assessment import cli, service
from src.malaria_dl.assessment.contracts import AssessmentError, verify_rows, prediction
from src.malaria_dl.execution.operations import training_plan
from test_assessment_e6 import value, MemoryRepository, Runtime

ROOT = Path(__file__).resolve().parents[1]
ENTRIES = [
    ['-m', 'src.' + kind] for kind in ('train', 'evaluate', 'explain', 'test')
]


@pytest.mark.parametrize('entry', ENTRIES)
def test_help_and_missing_selection(entry):
    result = subprocess.run([sys.executable, *entry, '--help'], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert '--campaign-id' in result.stdout and '--source-training-run-id' in result.stdout
    missing = subprocess.run([sys.executable, *entry], cwd=ROOT, capture_output=True, text=True)
    assert missing.returncode != 0


@pytest.mark.parametrize('kind,split,purpose', [('evaluate','val','development'),('explain','val','development'),('test','test','final')])
@pytest.mark.parametrize('selectors', ['campaign','training','both'])
def test_same_orchestrator_fixed_split(kind, split, purpose, selectors, monkeypatch):
    campaign, train = str(uuid4()), str(uuid4())
    args = []
    if selectors != 'training': args += ['--campaign-id', campaign]
    if selectors != 'campaign': args += ['--source-training-run-id', train]
    args += ['--threshold', '.4', '--seed', '11', '--batch-size', '64']
    if kind == 'explain': args += ['--method','gradcam','--layer','last']
    repository = object()
    monkeypatch.setattr(cli, 'AssessmentRepository', lambda: repository)
    monkeypatch.setattr(cli, 'select_trainings', lambda *a: [dict(id=train, campaign_id=campaign, status='completed')])
    calls = []
    def prepare(repo, **kwargs):
        assert repo is repository
        calls.append(kwargs)
        return {}
    monkeypatch.setattr(cli, 'prepare', prepare)
    monkeypatch.setattr(cli, 'run', lambda *a: dict(id=uuid4(), state='verified', verification={}))
    assert cli._execute(kind, cli.parser(kind).parse_args(args)) == 0
    assert len(calls) == 1
    assert calls[0]['split'] == split and calls[0]['purpose'] == purpose
    assert calls[0]['seed'] == 11 and calls[0]['requested_threshold'] == '.4'
    with pytest.raises(SystemExit):
        cli.parser(kind).parse_args(args + ['--split','train'])


def test_test_repeat_metrics_history(tmp_path):
    repo = MemoryRepository()
    v = value(tmp_path)
    v.update(split='test', purpose='final')
    for sample in v['samples']: sample['split'] = 'test'
    v['protocol'].update(splits=['test'], purposes=['final'])
    a = service.run(repo, v, tmp_path, Runtime)
    before = deepcopy(repo.attempt(a['id']))
    b = service.run(repo, v, tmp_path, Runtime)
    assert a['id'] != b['id']
    assert repo.attempt(a['id']) == before
    assert a['verification']['metrics']['roc_auc'] == 1
    assert a['verification']['metrics']['pr_auc'] == 1
    assert a['verification']['metrics']['f1'] == 1
    assert a['verification']['metrics']['balanced_accuracy'] == 1
    assert repo.identity(a['identity_id'])['model'] == v['model']


def test_test_undefined_metrics(tmp_path):
    v = value(tmp_path)
    v['split'] = 'test'
    v['samples'] = [next(s for s in v['samples'] if s['label'] == 0)]
    rows = [prediction(v['samples'][0], .1, v['decision'])]
    m = verify_rows(v, rows)['metrics']
    assert m['recall'] is None and m['precision'] is None
    assert m['f1'] is None and m['roc_auc'] is None and m['pr_auc'] is None


def test_train_reference_keeps_configuration(monkeypatch):
    from src.malaria_dl.execution import operations
    train, campaign, dataset = map(str, (uuid4(),uuid4(),uuid4()))
    from src.malaria_dl.models.configuration import resolve_config
    config = resolve_config('custom_cnn')
    source = dict(id=train,campaign_id=campaign,dataset_version_id=dataset,configuration=config)
    monkeypatch.setattr(operations,'select_trainings',lambda *a:[source])
    plan = training_plan(object(), campaign, train)
    assert plan == [dict(configuration=config, campaign_id=campaign, dataset_version_id=dataset, source_training_run_id=train)]
    source['configuration'] = None
    with pytest.raises(AssessmentError, match='CONFIGURATION_UNAVAILABLE'):
        training_plan(object(), campaign, train)


def test_campaign_members_are_not_expanded_by_the_standalone_plan():
    # Campaign members are reserved by the coordinator claim, which applies each member's seed.
    with pytest.raises(AssessmentError, match='SOURCE_TRAINING_RUN_REQUIRED'):
        training_plan(object(), str(uuid4()), None)


@pytest.mark.parametrize('stored', [0.0, 0.4, 0.5, 1.0])
def test_auto_threshold_uses_recorded_fixed_value(stored):
    from src.malaria_dl.assessment.contracts import threshold
    calibration = {'result': {'enabled': False, 'threshold': stored}, 'checkpoint_epoch': 4}
    decision = threshold('auto', {}, calibration)
    assert decision['effective'] == stored
    assert decision['requested'] == 'auto'
    assert decision['source']['version'] == 'training_fixed_threshold_v1'
    with pytest.raises(AssessmentError, match='CLINICAL_THRESHOLD_EVIDENCE_REQUIRED'):
        threshold('clinical', {}, calibration)
    assert threshold('.7', {'allowed_numeric_thresholds': [.7]}, calibration)['effective'] == .7


def test_auto_threshold_uses_validated_calibration():
    from src.malaria_dl.assessment.contracts import threshold
    calibration = {'result': {'enabled': True, 'schema_version': 1,
        'calibration_split': 'val', 'positive_class_index': 1,
        'threshold_source': 'validation_calibration', 'threshold_selected': .63, 'threshold_used': .63}}
    assert threshold('auto', {}, calibration) == {**threshold('clinical', {}, calibration), 'requested': 'auto'}
    calibration['result']['calibration_split'] = 'test'
    with pytest.raises(AssessmentError):
        threshold('auto', {}, calibration)


@pytest.mark.parametrize('evidence', [None, {}, {'result': {}}, {'result': {'enabled': False}},
    {'result': {'enabled': False, 'threshold': None}}, {'result': {'enabled': False, 'threshold': float('nan')}},
    {'result': {'enabled': False, 'threshold': -1}}, {'result': {'enabled': False, 'threshold': 2}}])
def test_auto_threshold_never_invents_missing_or_invalid_value(evidence):
    from src.malaria_dl.assessment.contracts import threshold
    with pytest.raises(AssessmentError):
        threshold('auto', {}, evidence)


def test_test_campaign_without_threshold_uses_training_evidence(monkeypatch):
    from src.malaria_dl.assessment.contracts import threshold
    train, campaign = str(uuid4()), str(uuid4())
    monkeypatch.setattr(cli, 'AssessmentRepository', object)
    monkeypatch.setattr(cli, 'select_trainings', lambda *a: [dict(id=train,campaign_id=campaign,status='completed')])
    observed = []
    def prepare(repository, **options):
        assert options['split'] == 'test' and options['purpose'] == 'final'
        decision = threshold(options['requested_threshold'], options['protocol'],
                             {'result': {'enabled': False, 'threshold': .5}, 'checkpoint_epoch': 4})
        observed.append(decision)
        return {'decision': decision}
    monkeypatch.setattr(cli, 'prepare', prepare)
    monkeypatch.setattr(cli, 'run', lambda *a: dict(id=str(uuid4()),state='verified',verification={}))
    args = cli.parser('test').parse_args(['--campaign-id',campaign])
    assert cli._execute('test',args) == 0
    assert len(observed) == 1 and all(d['effective'] == .5 for d in observed)


@pytest.fixture(autouse=True)
def synthetic_catalog(monkeypatch):
    from src.malaria_dl.models import registry
    monkeypatch.setattr(registry, "model_catalog", lambda: tuple(
        {"name": name, "architecture": name, "model_type": "classification", "framework": "tensorflow/keras"}
        for name in registry.MODEL_REGISTRY))
