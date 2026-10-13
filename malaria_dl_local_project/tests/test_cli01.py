"""CLI-01 certification: mocked SQL, synthetic evidence; no operational database."""
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from src.malaria_dl.assessment import cli, service
from src.malaria_dl.assessment.contracts import AssessmentError
from src.malaria_dl.execution import operations, selection
from test_assessment_e6 import MemoryRepository, Runtime, value

COMMON = {'--campaign-id', '--source-training-run-id', '--inspect'}
INFERENCE = {'--threshold', '--seed', '--batch-size'}
EXPLAIN = {'--method', '--layer', '--class-id', '--num-samples', '--max-images',
           '--sample-id', '--background-sample-id'}


@pytest.mark.parametrize('kind', ['train', 'evaluate', 'explain', 'test'])
def test_exact_public_matrix(kind):
    parser = operations.parser() if kind == 'train' else cli.parser(kind)
    actual = {option for action in parser._actions for option in action.option_strings} - {'-h', '--help'}
    expected = COMMON | ({'--plan', '--dry-run'} if kind == 'train' else INFERENCE)
    if kind == 'explain':
        expected |= EXPLAIN
    assert actual == expected
    for removed in ('--model-version-id', '--dataset-version-id', '--model', '--dataset-dir',
                    '--artifact-root', '--evaluation-id'):
        with pytest.raises(SystemExit):
            parser.parse_args([removed, 'unused'])
    with pytest.raises(SystemExit):
        parser.parse_args(['--campaign', str(uuid4())])


@pytest.mark.parametrize('method', ['lime', 'shap'])
@pytest.mark.parametrize('number', [None, 1000, 5000])
def test_internal_sample_defaults_bounds(method, number):
    spec = service.explanation_spec(method, None, 1, number, ['reference'] if method == 'shap' else [])
    assert spec['num_samples'] == (number or 1000)


@pytest.mark.parametrize('method', ['lime', 'shap'])
@pytest.mark.parametrize('number', [1, 999, 5001, 1000.0, True, '1000'])
def test_reject_internal_samples_before_preparation(method, number):
    with pytest.raises(AssessmentError, match='EXPLANATION_PARAMETERS_INVALID'):
        service.explanation_spec(method, None, 1, number, ['reference'] if method == 'shap' else [])


@pytest.mark.parametrize('options', [
    ['--method', 'lime', '--num-samples', '999'],
    ['--method', 'shap', '--num-samples', '5001'],
    ['--num-samples', '1000'],
    ['--method', 'lime', '--layer', 'conv'],
    ['--method', 'shap'],
    ['--background-sample-id', str(uuid4())],
    ['--sample-id', str(uuid4()), '--max-images', 'all'],
    ['--max-images', '0'], ['--max-images', '-1'], ['--max-images', '1.5'],
    ['--num-samples', '1000.5'], ['--batch-size', '0'],
])
def test_invalid_cli_never_bootstraps_or_reserves(options, monkeypatch):
    from src.malaria_dl.execution import local_launch
    monkeypatch.setattr(local_launch, 'bootstrap', lambda: pytest.fail('must reject before DB/bootstrap'))
    with pytest.raises(SystemExit):
        cli.main('explain', argv=['--source-training-run-id', str(uuid4()), *options])


def test_gradcam_defaults_and_explicit_class_layer():
    args = cli.parser('explain').parse_args([])
    assert (args.method, args.class_id, args.seed, args.threshold, args.max_images) == ('gradcam', 1, 'auto', 'auto', 'all')
    assert service.explanation_spec(args.method, args.layer, args.class_id, args.num_samples, [])['layer'] is None
    assert service.explanation_spec('gradcam', 'last', 0, None, [])['class'] == 0


@pytest.mark.parametrize('operation', ['evaluate', 'explain', 'test'])
@pytest.mark.parametrize('profile,expected', [({}, 23), ({'inference': {'batch_size': 7}}, 7),
                                           ({'inference': {'batch_size': 7}, 'operation': {'batch_size': 3}}, 3)])
def test_persisted_defaults_and_explicit_priority(operation, profile, expected, monkeypatch):
    profile = deepcopy(profile)
    if 'operation' in profile:
        profile[operation] = profile.pop('operation')
    config = {'resolved': {'execution': {'seed': 91, 'batch_size': 23}, **profile}}
    queries = []
    def execute(connection, sql, **params):
        queries.append(sql)
        return SimpleNamespace(scalar_one_or_none=lambda: config)
    monkeypatch.setattr(service, 'execute', execute)
    repo = SimpleNamespace(transaction=lambda **kw: nullcontext(None))
    train = str(uuid4())
    assert service.inference_options(repo, train, 'auto', None, operation) == (91, expected)
    assert service.inference_options(repo, train, 0, 5, operation) == (0, 5)
    assert len(queries) == 1
    assert "execution_parameters->'model_configuration_e2'->'configuration'" in queries[0]


def test_missing_auto_seed_never_falls_back(monkeypatch):
    monkeypatch.setattr(service, 'execute', lambda *a, **kw: SimpleNamespace(scalar_one_or_none=lambda: {'resolved': {}}))
    with pytest.raises(AssessmentError, match='INFERENCE_OPTIONS_INVALID'):
        service.inference_options(SimpleNamespace(transaction=lambda **kw: nullcontext(None)), str(uuid4()), 'auto', 4, 'test')


class SelectionRepository:
    def __init__(self, samples, dataset):
        self.samples = samples
        self.dataset = dataset
        self.queries = []

    def transaction(self, readonly=False):
        assert readonly
        return nullcontext(self)

    def execute(self, sql, params):
        sql = str(sql)
        self.queries.append((sql, params))
        assert 'ORDER BY source_record_id LIMIT :limit' in sql
        assert 'dataset_version_id=CAST(:dataset AS uuid) AND split_name=:split' in sql
        ids = sorted(s['sample_id'] for s in self.samples if s['split'] == params['split']
                     and self.dataset == params['dataset']
                     and (params['sample'] is None or s['sample_id'] == params['sample']))
        if params['limit'] is not None:
            ids = ids[:params['limit']]
        return SimpleNamespace(scalars=lambda: ids)


@pytest.mark.parametrize('method', ['gradcam', 'lime', 'shap'])
@pytest.mark.parametrize('requested', ['all', 1, 5, 100, 'individual'])
def test_selection_identity_persistence_and_repetition(tmp_path, monkeypatch, method, requested):
    template = value(tmp_path)
    samples = [dict(template['samples'][i % 2], sample_id=str(UUID(int=i + 1))) for i in range(7)]
    repo = SelectionRepository(samples, template['dataset']['dataset_version_id'])
    monkeypatch.setattr(service, 'resolve', lambda *a: (template['model'], template['dataset'], None))
    monkeypatch.setattr(service, 'dataset_samples', lambda *a, **kw: deepcopy(samples))
    monkeypatch.setattr(service, 'inference_environment', lambda *a: {})
    background = [samples[-1]['sample_id']] if method == 'shap' else []
    maximum = 'all' if requested == 'individual' else requested
    sample_id = samples[3]['sample_id'] if requested == 'individual' else None
    prepared = service.prepare(repo, training_run_id=template['model']['training_run_id'], split='val',
        purpose='development', protocol=template['protocol'], requested_threshold='.5', seed=42, batch_size=2,
        explanation=service.explanation_spec(method, None, 1, None, background),
        max_images=maximum, sample_id=sample_id)
    expected = [samples[3]] if sample_id else samples[:maximum] if isinstance(maximum, int) else samples
    assert prepared['samples'] == expected
    selected = prepared['explanation']['selection']
    assert selected == dict(eligible_count=7, requested_max_images=maximum, requested_sample_id=sample_id,
                           selected_count=len(expected), sample_ids=[s['sample_id'] for s in expected])
    if method == 'shap':
        assert prepared['explanation']['background'] == [samples[-1]]
    memory = MemoryRepository()
    first = service.run(memory, prepared, tmp_path, Runtime)
    before = deepcopy(memory.__dict__)
    second = service.run(memory, prepared, tmp_path, Runtime)
    assert first['id'] != second['id']
    assert memory.attempt(first['id']) == before['attempts'][first['id']]
    assert first['verification']['count'] == len(expected)
    assert len(memory.artifacts(first['id'])) == 2 * len(expected)
    assert {r['sample_id'] for r in memory.results(first['id'])} == set(selected['sample_ids'])
    assert memory.identity(first['identity_id'])['explanation'] == prepared['explanation']


@pytest.mark.parametrize('fault', ['missing', 'other_split', 'other_dataset'])
def test_target_selection_rejects_foreign_sample(tmp_path, fault):
    template = value(tmp_path)
    samples = template['samples']
    repository = SelectionRepository(samples, template['dataset']['dataset_version_id'])
    target = str(uuid4()) if fault == 'missing' else samples[0]['sample_id']
    if fault == 'other_split':
        repository.samples = [dict(s, split='train') for s in samples]
    if fault == 'other_dataset':
        repository.dataset = str(uuid4())
    with pytest.raises(AssessmentError, match='EXPLANATION_SAMPLE_SELECTION_EMPTY'):
        service.select_explanation_samples(repository, template['dataset'], 'val', samples, 'all', target)


@pytest.mark.parametrize('kind', ['evaluate', 'explain', 'test'])
def test_inspect_multiple_trainings_no_runtime_or_writes(kind, monkeypatch, capsys):
    import json
    from src.malaria_dl.execution import global_gate, local_launch
    campaign = str(uuid4())
    trainings = [dict(id=str(uuid4()), campaign_id=campaign, status='completed') for _ in range(3)]
    monkeypatch.setattr(local_launch, 'bootstrap', lambda: None)
    monkeypatch.setattr(global_gate, 'GlobalGate', lambda *a: pytest.fail('no gate writes'))
    monkeypatch.setattr(cli, 'AssessmentRepository', object)
    monkeypatch.setattr(cli, 'select_trainings', lambda *a: trainings)
    monkeypatch.setattr(cli, 'run', lambda *a: pytest.fail('no scientific execution'))
    calls = []
    def prepare(repository, **kwargs):
        calls.append(kwargs)
        return {'seed': 91, 'batch_size': 7}
    monkeypatch.setattr(cli, 'prepare', prepare)
    assert cli.main(kind, argv=['--campaign-id', campaign, '--inspect']) == 0
    output = json.loads(capsys.readouterr().out)
    assert [x['source_training_run_id'] for x in output] == [x['id'] for x in trainings]
    assert all(x['inspection']['seed'] == 91 for x in output)
    assert all(x['inspection'] for x in calls)
    assert {x['split'] for x in calls} == ({'test'} if kind == 'test' else {'val'})


@pytest.mark.parametrize('mode', ['--inspect', '--plan', '--dry-run'])
def test_train_inspect_modes_no_execution(mode, monkeypatch, capsys):
    import json
    from src.malaria_dl.execution import local_launch, train
    monkeypatch.setattr(local_launch, 'bootstrap', lambda: None)
    monkeypatch.setattr(operations, 'ExecutionRepository', object)
    plan = [dict(configuration={'resolved': {'execution': {'seed': s}}}) for s in (11, 19)]
    monkeypatch.setattr(operations, 'training_plan', lambda *a: plan)
    monkeypatch.setattr(train, 'standalone', lambda *a: pytest.fail('no TRAIN'))
    assert operations.main(['--campaign-id', str(uuid4()), mode]) == 0
    assert json.loads(capsys.readouterr().out) == plan


@pytest.mark.parametrize('case', ['none', 'campaign', 'train', 'both', 'mismatch', 'missing_campaign', 'missing_train'])
def test_common_identifier_sql_contract(case, monkeypatch):
    campaign, train = str(uuid4()), str(uuid4())
    rows = [dict(id=train, campaign_id=campaign), dict(id=str(uuid4()), campaign_id=campaign)]
    def execute(connection, sql, **params):
        if 'SELECT EXISTS' in sql:
            return SimpleNamespace(scalar_one=lambda: case != 'missing_campaign')
        assert "r.run_type='training'" in sql and 'ORDER BY r.started_at,r.id' in sql
        assert '(CAST(:train AS uuid) IS NULL OR r.id=CAST(:train AS uuid))' in sql
        assert '(CAST(:campaign AS uuid) IS NULL OR r.campaign_id=CAST(:campaign AS uuid)' in sql
        assert 'campaign_attempts a JOIN campaign_members m' in sql
        selected = [] if case in ('mismatch', 'missing_train') else rows[:1] if params['train'] else rows
        return SimpleNamespace(mappings=lambda: selected)
    monkeypatch.setattr(selection, 'execute', execute)
    repo = SimpleNamespace(transaction=lambda **kw: nullcontext(None))
    cid = campaign if case in ('campaign', 'both', 'mismatch', 'missing_campaign') else None
    tid = train if case not in ('none', 'campaign', 'missing_campaign') else None
    if case in ('none', 'mismatch', 'missing_campaign', 'missing_train'):
        with pytest.raises(AssessmentError):
            selection.select_trainings(repo, cid, tid)
    else:
        assert selection.select_trainings(repo, cid, tid) == (rows if case == 'campaign' else rows[:1])


def test_legacy_executors_absent():
    root = Path(__file__).resolve().parents[1]
    for name in ('run_train_all_models.py', 'run_evaluate_all_trainings.py',
                 'run_explain_all_trainings.py', 'run_test_all_models.py'):
        assert not (root / name).exists()


@pytest.mark.parametrize('architecture', ['custom_cnn', 'vgg16', 'densenet121'])
def test_gradcam_auto_layer_graph_compatibility(architecture, monkeypatch):
    """Build synthetic graphs with random weights; no dataset, prediction or training."""
    import tensorflow as tf
    from src.malaria_dl.models import registry
    from src.malaria_dl.models.configuration import resolve_config
    from src.malaria_dl.explainability.pipeline import find_last_conv_layer, build_gradcam_model
    monkeypatch.setattr(registry, 'registered_models', lambda: tuple(registry.MODEL_REGISTRY))
    config = resolve_config(architecture, {'model': {'weights': 'none', 'input_shape': [32, 32, 3]}})['resolved']
    model = registry.resolve_descriptor(architecture).create_adapter().build(config).model
    layer = find_last_conv_layer(model)
    # Nested DenseNet exposes its connected rank-4 convolutional backbone;
    # preserve the existing resolver's fallback instead of changing Grad-CAM math.
    assert isinstance(layer, tf.keras.layers.Conv2D) or (
        architecture == 'densenet121' and isinstance(layer, tf.keras.Model))
    graph = build_gradcam_model(model, layer, tf)
    assert len(graph.outputs) == 2 and len(graph.outputs[0].shape) == 4
    tf.keras.backend.clear_session()


def test_test_inspection_reads_metadata_only(tmp_path, monkeypatch):
    template = value(tmp_path)
    monkeypatch.setattr(service, 'resolve', lambda *a: (template['model'], template['dataset'], None))
    monkeypatch.setattr(service, 'inference_environment', lambda *a: {})
    def samples(repository, dataset, split, override, **kwargs):
        assert split == 'test' and kwargs['inspection'] and kwargs['metadata_only']
        return [dict(s, split='test') for s in template['samples']]
    monkeypatch.setattr(service, 'dataset_samples', samples)
    prepared = service.prepare(object(), training_run_id=template['model']['training_run_id'], split='test',
        purpose='final', protocol={'version': 'synthetic', 'splits': ['test'], 'purposes': ['final'],
                                  'allowed_numeric_thresholds': [.5]},
        requested_threshold='.5', seed=42, batch_size=2, inspection=True)
    assert prepared['split'] == 'test' and prepared['evaluation'] is None


def test_new_train_identity_never_reuses_source(tmp_path, monkeypatch):
    from src.malaria_dl.execution import repository as module
    source = str(uuid4())
    created = []
    sessions = []
    repository = module.ExecutionRepository(lambda **kw: nullcontext(None))
    monkeypatch.setattr(repository, '_create_run', lambda c, run, *a, **kw: created.append((run, kw)))
    def execute(connection, sql, **params):
        assert 'INSERT INTO train_execution_sessions' in sql
        sessions.append(params)
    monkeypatch.setattr(module, 'execute', execute)
    monkeypatch.setattr(repository, 'session', lambda run: {'run_id': run})
    first = repository.standalone({}, {}, {}, tmp_path, 'fixture', 1, None, source_training_run_id=source)
    second = repository.standalone({}, {}, {}, tmp_path, 'fixture', 1, None, source_training_run_id=source)
    assert len({source, first['run_id'], second['run_id']}) == 3
    assert all(options['source_training_run_id'] == source for _, options in created)
    assert sessions[0]['root'] != sessions[1]['root']


@pytest.mark.parametrize('kind', ['train', 'evaluate', 'explain', 'test'])
@pytest.mark.parametrize('flag', ['--inspect', '--help', '--plan', '--dry-run'])
def test_process_gate_recognizes_official_modules(kind, flag):
    from src.malaria_dl.execution.global_gate import managed_execution
    command = ['python', '-m', 'src.' + kind]
    assert managed_execution(command)
    assert not managed_execution([*command, flag])


@pytest.mark.parametrize('calibration', [None, {}, {'result': None}, {'result': {}}, {'result': {'enabled': False, 'threshold': .5}}])
def test_clinical_missing_calibration_is_explicit(calibration):
    from src.malaria_dl.assessment.contracts import threshold
    with pytest.raises(AssessmentError, match='CLINICAL_THRESHOLD_EVIDENCE_REQUIRED'):
        threshold('clinical', {}, calibration)


@pytest.mark.parametrize('released', [False, True])
def test_gate_accepts_current_local_absence_after_interruption(monkeypatch, released):
    from src.malaria_dl.execution import global_gate as gate
    host = {'host': 'fixture-mac', 'boot_id': 'boot-1'}
    monkeypatch.setattr(gate, 'host_identity', lambda: host)
    monkeypatch.setattr(gate, 'process_table', lambda: {})
    gate.verify_retained_processes({'identities': [{**host, 'pid': 123, 'start_ticks': '1'}],
                                   'sessions': [123], 'release_confirmed': released})


@pytest.mark.parametrize('case,error', [
    ('live', 'PREVIOUS_EXPERIMENT_PROCESS_STILL_ALIVE'),
    ('unknown_start', 'PREVIOUS_EXPERIMENT_PROCESS_STILL_ALIVE'),
    ('descendant', 'PREVIOUS_EXPERIMENT_DESCENDANTS_STILL_ALIVE'),
    ('remote', 'REMOTE_PROCESS_ABSENCE_UNPROVEN'),
    ('empty', 'PROCESS_TREE_RELEASE_UNPROVEN'),
])
def test_gate_does_not_bypass_unproven_or_live_processes(monkeypatch, case, error):
    from src.malaria_dl.execution import global_gate as gate
    from src.malaria_dl.campaigns.contracts import CampaignError
    host = {'host': 'fixture-mac', 'boot_id': 'boot-1'}
    identity = {**host, 'pid': 123, 'start_ticks': '1'}
    evidence = {'identities': [identity], 'sessions': [123], 'release_confirmed': False}
    table = {}
    if case in ('live', 'unknown_start'):
        table[123] = {'session': 123, 'start_ticks': '1' if case == 'live' else None}
    elif case == 'descendant':
        table[456] = {'session': 123, 'start_ticks': '2'}
    elif case == 'remote':
        identity['host'] = 'other-host'
    else:
        evidence['identities'] = []
    monkeypatch.setattr(gate, 'host_identity', lambda: host)
    monkeypatch.setattr(gate, 'process_table', lambda: table)
    with pytest.raises(CampaignError, match=error):
        gate.verify_retained_processes(evidence)


def test_gate_accepts_reused_pid_with_proven_different_identity(monkeypatch):
    from src.malaria_dl.execution import global_gate as gate
    host = {'host': 'fixture-mac', 'boot_id': 'boot-1'}
    monkeypatch.setattr(gate, 'host_identity', lambda: host)
    monkeypatch.setattr(gate, 'process_table', lambda: {123: {'session': 999, 'start_ticks': '2'}})
    gate.verify_retained_processes({'identities': [{**host, 'pid': 123, 'start_ticks': '1'}],
                                   'sessions': [], 'release_confirmed': False})


def test_assessment_gate_error_has_no_traceback_or_execution(monkeypatch, capsys):
    from src.malaria_dl.execution import global_gate, local_launch
    from src.malaria_dl.campaigns.contracts import CampaignError
    class BlockedGate:
        def __init__(self, kind):
            pass
        def __enter__(self):
            raise CampaignError('PREVIOUS_EXPERIMENT_PROCESS_STILL_ALIVE')
        def __exit__(self, *args):
            pass
    monkeypatch.setattr(local_launch, 'bootstrap', lambda: None)
    monkeypatch.setattr(global_gate, 'GlobalGate', BlockedGate)
    monkeypatch.setattr(cli, '_execute', lambda *args: pytest.fail('no preparation or inference'))
    assert cli.main('explain', argv=['--source-training-run-id', str(uuid4()), '--max-images', '1', '--method', 'lime']) == 2
    output = capsys.readouterr()
    assert output.out == 'STOP PREVIOUS_EXPERIMENT_PROCESS_STILL_ALIVE\n'
    assert not output.err
