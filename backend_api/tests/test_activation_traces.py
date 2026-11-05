import json
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from fastapi import HTTPException

from app.schemas.activation_traces import ActivationTraceCatalog
from app.services import activation_traces
from app.services.activation_trace_compute import VERSION, block_of, histogram, statistics, trace_steps, traced, traced_layers, write_atomic
from app.services.activation_traces import ActivationTraceService


class Architecture:
    def __init__(self, architecture='vgg16', run_type='training'):
        self.source = dict(run={'run_type': run_type}, configuration={'architecture': architecture})

    def read(self, run_id, datasource):
        return self.source


class Evaluations:
    def evaluation(self, run_id, datasource):
        return {'id': uuid4(), 'split': 'val'}

    def result(self, attempt, sample, datasource):
        return {'raw_score': 0.5}


def saved(root, run, sample, **values):
    write_atomic(root / str(run) / f'{sample}.json', dict(created_at='2026-11-01T10:00:00', label=1, predicted=0, score=0.03, persisted_score=0.03,
                                                         consistent=True, split='val', checkpoint_sha256='abc', version=VERSION, **values))


def test_saved_traces_are_listed_when_the_run_is_reopened(tmp_path):
    run, sample = uuid4(), uuid4()
    saved(tmp_path, run, sample)
    result = ActivationTraceCatalog.model_validate(ActivationTraceService(Evaluations(), Architecture(), tmp_path).catalog(run, 'malaria'))
    assert result.available and [item.sample_id for item in result.items] == [sample]
    assert result.used_bytes == result.items[0].bytes > 0


def test_only_traceable_cnns_are_supported_and_other_models_say_why(tmp_path):
    assert ActivationTraceService(Evaluations(), Architecture('custom_cnn'), tmp_path).catalog(uuid4(), 'malaria')['available']
    assert ActivationTraceService(Evaluations(), Architecture('densenet121'), tmp_path).catalog(uuid4(), 'malaria')['available']
    result = ActivationTraceService(Evaluations(), Architecture('biomedclip_linear'), tmp_path).catalog(uuid4(), 'malaria')
    assert not result['available'] and result['reason'] == 'El recorrido por capas está disponible para VGG16, CNN propia, DenseNet121 y BiomedCLIP zero-shot.'
    with pytest.raises(HTTPException) as error:
        ActivationTraceService(Evaluations(), Architecture('biomedclip_fine_tuning'), tmp_path).create(uuid4(), uuid4(), 'malaria')
    assert error.value.status_code == 409


def representing(monkeypatch, sha='abc'):
    class Repository:
        def source(self, attempt):
            return {'identity': {'model': {'sha256': sha}, 'samples': []}}
    monkeypatch.setattr(activation_traces, 'RepresentRepository', Repository)


def test_existing_trace_is_reused_without_running_the_model(tmp_path, monkeypatch):
    run, sample = uuid4(), uuid4()
    saved(tmp_path, run, sample)
    representing(monkeypatch)
    monkeypatch.setattr(activation_traces.subprocess, 'run', lambda *args, **kwargs: pytest.fail('no debe recalcular'))
    assert ActivationTraceService(Evaluations(), Architecture(), tmp_path).create(run, sample, 'malaria')['sample_id'] == str(sample)


def test_limit_blocks_new_traces_and_never_deletes_saved_ones(tmp_path, monkeypatch):
    run, sample = uuid4(), uuid4()
    saved(tmp_path, run, sample)
    representing(monkeypatch)
    monkeypatch.setattr(activation_traces, 'MAX_BYTES', 1)
    with pytest.raises(HTTPException) as error:
        ActivationTraceService(Evaluations(), Architecture(), tmp_path).create(run, uuid4(), 'malaria')
    assert error.value.status_code == 409 and '500 MB' in error.value.detail
    assert (tmp_path / str(run) / f'{sample}.json').is_file()


def test_delete_removes_only_the_requested_trace(tmp_path):
    run, first, second = uuid4(), uuid4(), uuid4()
    saved(tmp_path, run, first), saved(tmp_path, run, second)
    service = ActivationTraceService(Evaluations(), Architecture(), tmp_path)
    service.delete(run, first)
    assert [Path(item).stem for item in map(str, (tmp_path / str(run)).glob('*.json'))] == [str(second)]
    with pytest.raises(HTTPException) as error:
        service.read(run, first)
    assert error.value.status_code == 404


def test_step_blocks_and_statistics_follow_the_architecture():
    assert [block_of(name) for name in ('block3_pool', 'global_avg_pool', 'binary_output')] == ['block3', 'head', 'output']
    assert statistics(np.array([0.0, 2.0])) == {'min': 0.0, 'max': 2.0, 'mean': 1.0, 'std': 1.0, 'active': 0.5}


def test_atomic_write_leaves_no_partial_file(tmp_path):
    write_atomic(tmp_path / 'run' / 'cell.json', {'score': 1})
    assert [path.name for path in (tmp_path / 'run').iterdir()] == ['cell.json']
    assert json.loads((tmp_path / 'run' / 'cell.json').read_text()) == {'score': 1}


def test_routes_are_registered_in_the_application():
    from app.main import app
    assert {'/runs/{run_id}/activation-traces', '/runs/{run_id}/activation-traces/candidates',
            '/runs/{run_id}/activation-traces/{sample_id}'} <= set(app.openapi()['paths'])


class Layer:
    def __init__(self, name, kind):
        self.name = name
        # The Keras type is read from the class name, as traced_layers does with real layers.
        self.__class__ = type(kind, (Layer,), {})


def layers(*items):
    return [Layer(name, kind) for name, kind in items]


def test_head_follows_each_train_configuration():
    gap = layers(('input_1', 'InputLayer'), ('block1_conv1', 'Conv2D'), ('block1_pool', 'MaxPooling2D'), ('block2_pool', 'MaxPooling2D'),
                 ('global_avg_pool', 'GlobalAveragePooling2D'), ('feature_dense_1024', 'Dense'), ('dropout_50', 'Dropout'), ('binary_output', 'Dense'))
    flatten = layers(('block5_pool', 'MaxPooling2D'), ('flatten', 'Flatten'), ('dense', 'Dense'), ('dense_1', 'Dense'))
    assert traced_layers(gap) == ['block1_pool', 'block2_pool', 'global_avg_pool', 'feature_dense_1024', 'binary_output']
    assert traced_layers(flatten) == ['block5_pool', 'flatten', 'dense', 'dense_1']
    assert block_of('dense_1', output=True) == 'output' and block_of('dense') == 'head'


def test_steps_carry_scale_and_distribution_and_name_the_last_layer_output(monkeypatch):
    from app.services import activation_trace_compute
    monkeypatch.setattr(activation_trace_compute, 'channel_png', lambda tf, channel: 'png')
    spatial = np.zeros((1, 4, 4, 2)); spatial[0, ..., 1] = 3.0
    steps = trace_steps(None, np, ['block1_pool', 'flatten', 'dense_1'], [spatial, np.array([[0.0, 2.0, 1.0]]), np.array([[0.2]])])
    assert steps[0]['maps'][0] == {'channel': 1, 'mean': 3.0, 'min': 3.0, 'max': 3.0, 'png': 'png'}
    assert steps[1]['kind'] == 'vector' and sum(steps[1]['histogram']['counts']) == 3
    assert steps[2]['kind'] == 'output' and steps[2]['block'] == 'output' and 'histogram' not in steps[2]
    assert len(histogram(np, np.arange(10.0))['edges']) == 25


# Layers of the custom_cnn TRAIN 33348978 and of the VGG16 TRAIN 0bbdd732, as their epoch checkpoints record them.
CUSTOM_CNN = [('input_layer_1', 'InputLayer')] + [item for i, suffix in enumerate(('', '_1', '_2', '_3')) for item in (
    (f'conv2d{suffix}', 'Conv2D'), (f'batch_normalization{suffix}', 'BatchNormalization'), (f'activation{suffix}', 'Activation'),
    *([(f'max_pooling2d{suffix}', 'MaxPooling2D')] if i < 3 else []))] + [
    ('global_average_pooling2d', 'GlobalAveragePooling2D'), ('dense', 'Dense'), ('dropout', 'Dropout'), ('dense_1', 'Dense')]
VGG16 = [('input_layer_1', 'InputLayer')] + [(f'block{b}_conv{c}', 'Conv2D') for b, n in ((1, 2), (2, 2)) for c in range(1, n + 1)] + [
    ('block1_pool', 'MaxPooling2D'), ('block2_pool', 'MaxPooling2D'), ('global_avg_pool', 'GlobalAveragePooling2D'),
    ('feature_dense_1024', 'Dense'), ('dropout_50', 'Dropout'), ('binary_output', 'Dense')]


def test_custom_cnn_reads_the_output_of_each_architecture_block_then_the_head():
    names, blocks = traced(layers(*CUSTOM_CNN), 'custom_cnn')
    assert names == ['max_pooling2d', 'max_pooling2d_1', 'max_pooling2d_2', 'activation_3', 'global_average_pooling2d', 'dense', 'dense_1']
    # Same block ids as GET /runs/{id}/architecture builds for custom_cnn, so each step lands on its drawn block.
    assert [blocks[name] for name in names] == ['block1', 'block2', 'block3', 'block4', 'head', 'head', 'output']


def test_vgg16_keeps_exactly_the_steps_it_had():
    vgg = layers(*VGG16)
    names, blocks = traced(vgg, 'vgg16')
    assert names == traced_layers(vgg)
    assert [blocks[name] for name in names] == [block_of(name, index == len(names) - 1) for index, name in enumerate(names)]


def test_custom_cnn_trace_is_computed_with_its_family(tmp_path, monkeypatch):
    run, sample = uuid4(), uuid4()
    representing(monkeypatch)
    jobs = []

    def fake_run(command, input, **kwargs):
        job = json.loads(input)
        jobs.append(job)
        write_atomic(Path(job['path']), dict(job['identity'], created_at='2026-11-05T10:00:00', label=1, predicted=1, score=0.9,
                                             persisted_score=0.9, consistent=True, version=VERSION))
    monkeypatch.setattr(activation_traces.subprocess, 'run', fake_run)

    class Repository(Evaluations):
        def result(self, attempt, sample_id, datasource):
            return {'raw_score': 0.9}
    service = ActivationTraceService(Repository(), Architecture('custom_cnn'), tmp_path)
    monkeypatch.setattr(activation_traces, 'RepresentRepository', lambda: type('R', (), {'source': lambda self, a: {
        'identity': {'model': {'sha256': 'abc'}, 'samples': [{'sample_id': str(sample)}]}}})())
    service.create(run, sample, 'malaria')
    assert jobs[0]['family'] == 'custom_cnn'
    service.delete(run, sample)
    assert service.catalog(run, 'malaria')['used_bytes'] == 0


class Dense(Layer):
    def __init__(self, name, activation):
        super().__init__(name, 'Dense')
        self.activation = type('Activation', (), {'__name__': activation})() if activation else None


def densenet_layers():
    """The flattened layers of DenseNet121 TRAIN 03c7b1a1 (431, nested backbone expanded), from its epoch checkpoint."""
    items = json.loads((Path(__file__).parent / 'fixtures' / 'densenet121_layers.json').read_text())
    return [Dense(name, activation) if kind == 'Dense' else Layer(name, kind) for name, kind, activation in items], items


def test_densenet121_reads_each_block_output_the_final_features_the_head_and_the_output():
    from app.services.activation_trace_compute import traced_densenet
    names, blocks = traced_densenet(densenet_layers()[0])
    assert names == ['pool1', 'conv2_block6_concat', 'pool2_pool', 'conv3_block12_concat', 'pool3_pool', 'conv4_block24_concat',
                     'pool4_pool', 'conv5_block16_concat', 'relu', 'global_avg_pool', 'binary_output']
    assert [blocks[name] for name in names] == ['stem', 'dense2', 'transition2', 'dense3', 'transition3', 'dense4', 'transition4',
                                                'dense5', 'head', 'head', 'output']


def test_densenet121_trace_blocks_are_the_blocks_the_architecture_draws():
    from app.services.activation_trace_compute import densenet_block
    from app.services.model_architecture import _keras_block
    layers, items = densenet_layers()
    state = {'convolutions': 0}
    for layer, (name, kind, activation) in zip(layers, items):
        assert densenet_block(layer) == _keras_block('densenet121', {'name': name, 'type': kind, 'settings': {'activation': activation}}, state)[0], name



def test_a_zero_shot_train_is_traced_with_the_vit_engine_and_its_own_version(tmp_path, monkeypatch):
    from app.services.vit_trace_compute import VERSION as VIT_VERSION
    run, sample = uuid4(), uuid4()
    commands = []

    def fake_run(command, input, **kwargs):
        commands.append(command)
        job = json.loads(input)
        write_atomic(Path(job['path']), dict(job['identity'], created_at='2026-11-05T18:00:00', label=1, predicted=1, score=0.7,
                                             persisted_score=0.7, consistent=True, version=VIT_VERSION))
    monkeypatch.setattr(activation_traces.subprocess, 'run', fake_run)
    monkeypatch.setattr(activation_traces, 'RepresentRepository', lambda: type('R', (), {'source': lambda self, a: {
        'identity': {'model': {'sha256': 'zs'}, 'samples': [{'sample_id': str(sample)}]}}})())

    class ZeroShot:
        # A logical TRAIN has no run configuration: the model name is its architecture.
        def read(self, run_id, datasource):
            return dict(run={'run_type': 'training', 'model_name': 'biomedclip_zero_shot'}, configuration=None)
    service = ActivationTraceService(Evaluations(), ZeroShot(), tmp_path)
    assert service.catalog(run, 'malaria')['available']
    first = service.create(run, sample, 'malaria')
    assert commands[0][-1] == 'app.services.vit_trace_compute' and first['version'] == VIT_VERSION
    service.create(run, sample, 'malaria')
    assert len(commands) == 1, 'a saved ViT trace of the same checkpoint and version is reused'


def test_vit_token_step_draws_the_patch_grid_and_the_class_token_attention():
    from app.services.vit_trace_compute import CHANNELS, token_step
    tokens = np.random.default_rng(0).standard_normal((197, 768)).astype('float32')
    step = token_step(np, 'blocks.3', 'vit3', tokens, 1, np.full(196, 1 / 196), tokens[0])
    assert step['shape'] == [14, 14, 768] and step['tokens'] == 197 and len(step['maps']) == CHANNELS
    assert step['attention']['png'] and abs(step['cls_similarity'] - 1) < 1e-6
    means = [abs(np.abs(tokens[1:].reshape(14, 14, 768))[..., m['channel']].mean()) for m in step['maps']]
    assert means == sorted(means, reverse=True), 'dimensions ranked by mean magnitude over the patches'
