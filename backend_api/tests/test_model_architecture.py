from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.model_architecture import ModelArchitecture
from app.services.model_architecture import ModelArchitectureService, family_of, normalize_biomedclip, normalize_keras


def tensor(source, shape):
    return {'class_name': '__keras_tensor__', 'config': {'shape': shape, 'keras_history': [source, 0, 0]}}


def layer(kind, name, inbound=None, **config):
    return {'class_name': kind, 'name': name, 'config': dict(name=name, trainable=config.pop('trainable', True), **config),
            'inbound_nodes': [{'args': inbound}] if inbound else []}


def sequential():
    return {'config': {'layers': [
        {'class_name': 'InputLayer', 'config': {'name': 'input', 'batch_shape': [None, 8, 8, 3]}},
        {'class_name': 'Conv2D', 'config': {'name': 'conv2d', 'filters': 4, 'kernel_size': [3, 3], 'padding': 'same', 'strides': [1, 1], 'use_bias': False, 'trainable': True}},
        {'class_name': 'BatchNormalization', 'config': {'name': 'bn', 'trainable': True}},
        {'class_name': 'MaxPooling2D', 'config': {'name': 'pool', 'pool_size': [2, 2], 'strides': [2, 2], 'padding': 'valid', 'trainable': True}},
        {'class_name': 'GlobalAveragePooling2D', 'config': {'name': 'gap', 'trainable': True}},
        {'class_name': 'Dense', 'config': {'name': 'out', 'units': 1, 'activation': 'sigmoid', 'trainable': True}},
    ]}}


def test_sequential_shapes_and_parameters_are_derived_from_the_record():
    result = normalize_keras([{'phase': 'base', 'payload': {
        'architecture': sequential(), 'input_contract': {'shape': [None, 8, 8, 3]}, 'output_contract': {'shape': [None, 1]}}}], 'custom_cnn')
    layers = {item['name']: item for item in result['layers']}
    assert layers['pool']['output_shape'] == [None, 4, 4, 4]
    assert layers['gap']['output_shape'] == [None, 4]
    assert layers['conv2d']['parameters'] == 108
    assert layers['bn']['parameters'] == 16
    assert layers['out']['parameters'] == 5
    assert result['total_parameters'] == 129
    assert result['phases'] == [{'phase': 'base', 'trainable_parameters': 121}]
    assert [block['id'] for block in result['blocks']] == ['input', 'block1', 'head', 'output']


def functional(trainable):
    inner = {'layers': [
        layer('InputLayer', 'inner_input', batch_shape=[None, 6, 6, 8]),
        layer('Conv2D', 'conv2_block1_2_conv', [tensor('inner_input', [None, 6, 6, 8])], filters=4, kernel_size=[1, 1], trainable=trainable),
        layer('Concatenate', 'conv2_block1_concat', [[tensor('inner_input', [None, 6, 6, 8]), tensor('conv2_block1_2_conv', [None, 6, 6, 4])]], trainable=trainable),
        layer('Activation', 'relu', [tensor('conv2_block1_concat', [None, 6, 6, 12])]),
    ], 'output_layers': ['relu', 0, 0]}
    return {'layers': [
        layer('InputLayer', 'image', batch_shape=[None, 6, 6, 8]),
        {**layer('Functional', 'densenet121', [tensor('image', [None, 6, 6, 8])]), 'config': {**inner, 'name': 'densenet121'}},
        layer('GlobalAveragePooling2D', 'pool', [tensor('densenet121', [None, 6, 6, 12])]),
        layer('Dense', 'binary_output', [tensor('pool', [None, 12])], units=1, activation='sigmoid'),
    ], 'output_layers': ['binary_output', 0, 0]}


def test_nested_model_is_flattened_keeping_connections_and_phases():
    records = [{'phase': phase, 'payload': {'architecture': functional(phase == 'fine_tuning'), 'output_contract': {'shape': [None, 1]}}}
               for phase in ('base', 'fine_tuning')]
    result = normalize_keras(records, 'densenet121')
    layers = {item['name']: item for item in result['layers']}
    assert 'densenet121' not in layers and 'inner_input' not in layers
    assert layers['conv2_block1_2_conv']['inputs'] == ['image']
    assert layers['conv2_block1_concat']['inputs'] == ['image', 'conv2_block1_2_conv']
    assert layers['pool']['inputs'] == ['relu']
    assert layers['binary_output']['output_shape'] == [None, 1]
    assert layers['conv2_block1_2_conv']['trainable_phases'] == ['fine_tuning']
    dense = next(block for block in result['blocks'] if block['id'] == 'dense2')
    assert dense['units'] == 1 and dense['trainable_phases'] == ['fine_tuning']


def test_biomedclip_declares_reference_structure_and_recorded_counts():
    records = [{'phase': 'base', 'payload': {'framework': 'pytorch', 'encoder': 'frozen', 'trainable_parameters': {'count': 2, 'elements': 513}}},
               {'phase': 'fine_tuning', 'payload': {'framework': 'pytorch', 'encoder': 'last_4_blocks', 'trainable_parameters': {'count': 53, 'elements': 28746753}}}]
    configuration = dict(input_height=224, input_width=224, input_channels=3, extension_configuration={
        'recipe': {'head': {'in_features': 512, 'out_features': 1, 'activation': 'sigmoid'}}})
    result = normalize_biomedclip(records, configuration)
    vit = [block for block in result['blocks'] if block['kind'] == 'encoder']
    assert len(vit) == 12 and {block['origin'] for block in vit} == {'reference'}
    assert [block['id'] for block in vit if block['trainable_phases']] == ['vit8', 'vit9', 'vit10', 'vit11']
    assert result['phases'][1] == {'phase': 'fine_tuning', 'encoder': 'last_4_blocks', 'trainable_parameters': 28746753, 'trainable_tensors': 53}
    assert result['blocks'][-1]['parameters'] == 513
    assert result['layers'] == [] and result['total_parameters'] is None


class Repository:
    def __init__(self, source):
        self.source = source

    def read(self, run_id, datasource):
        return self.source


def source(run_type='training', records=()):
    return dict(run={'run_type': run_type, 'model_name': 'custom_cnn'}, configuration={'architecture': 'custom_cnn'},
                records=list(records), checkpoint=None)


def test_absence_is_reported_and_not_replaced_by_a_template():
    result = ModelArchitecture.model_validate(ModelArchitectureService(Repository(source())).read(uuid4(), 'malaria'))
    assert result.state == 'missing' and result.blocks == [] and result.issues


def test_identity_errors_keep_scientific_read_semantics():
    with pytest.raises(HTTPException) as missing:
        ModelArchitectureService(Repository(None)).read(uuid4(), 'malaria')
    assert missing.value.status_code == 404
    with pytest.raises(HTTPException) as derived:
        ModelArchitectureService(Repository(source('evaluation'))).read(uuid4(), 'malaria')
    assert derived.value.status_code == 422


def test_family_keeps_unknown_architectures_generic():
    assert [family_of(name) for name in ('vgg16', 'biomedclip_linear', 'svm', None)] == ['vgg16', 'biomedclip', 'generic', 'generic']
