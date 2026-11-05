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
        'architecture': sequential(), 'input_contract': {'shape': [None, 8, 8, 3]}, 'output_contract': {'shape': [None, 1], 'activation': 'sigmoid', 'meaning': 'probability_parasitized'},
        'loss': {'name': 'binary_crossentropy', 'from_logits': False}}}], 'custom_cnn')
    layers = {item['name']: item for item in result['layers']}
    assert layers['pool']['output_shape'] == [None, 4, 4, 4]
    assert layers['gap']['output_shape'] == [None, 4]
    assert layers['conv2d']['parameters'] == 108
    assert layers['bn']['parameters'] == 16
    assert layers['out']['parameters'] == 5
    assert result['total_parameters'] == 129
    assert result['phases'] == [{'phase': 'base', 'trainable_parameters': 121, 'learning_rates': []}]
    assert [block['id'] for block in result['blocks']] == ['input', 'block1', 'head', 'output']
    assert result['blocks'][-1]['label'] == 'Capa de salida'
    assert result['output'] == {'neurons': 1, 'activation': 'sigmoid', 'loss': 'binary_crossentropy', 'from_logits': False, 'meaning': 'probability_parasitized'}


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
        'recipe': {'head': {'in_features': 512, 'out_features': 1, 'activation': 'sigmoid', 'loss': 'bce_with_logits'}},
        'input_contract': {'output': {'meaning': 'probability_parasitized'}}})
    result = normalize_biomedclip(records, configuration)
    vit = [block for block in result['blocks'] if block['kind'] == 'encoder']
    assert len(vit) == 12 and {block['origin'] for block in vit} == {'reference'}
    assert [block['id'] for block in vit if block['trainable_phases']] == ['vit8', 'vit9', 'vit10', 'vit11']
    assert result['phases'][1] == {'phase': 'fine_tuning', 'encoder': 'last_4_blocks', 'trainable_parameters': 28746753, 'trainable_tensors': 53,
                                   'structure_check': None, 'learning_rates': []}
    assert result['blocks'][-1]['parameters'] == 513 and result['blocks'][-1]['kind'] == 'output'
    assert result['output'] == {'neurons': 1, 'activation': 'sigmoid', 'loss': 'bce_with_logits', 'from_logits': True,
                                'meaning': 'probability_parasitized', 'embedding_features': 512}
    assert result['layers'] == [] and result['total_parameters'] is None


VIT_BLOCK = 7087872


def vit_structure(sha='a' * 64):
    blocks = {f'vit{i}': {'parameters': VIT_BLOCK, 'tensors': 12, 'output_shape': [1, 197, 768]} for i in range(12)}
    blocks.update(embedding={'parameters': 742656, 'tensors': 4, 'output_shape': [1, 197, 768], 'patches': [1, 196, 768]},
                  projection={'parameters': 394752, 'tensors': 3, 'output_shape': [1, 512]},
                  output={'parameters': 513, 'tensors': 2, 'output_shape': [1, 1]})
    trainable = {'0': {'names_sha256': 'h0', 'count': 2, 'elements': 513},
                 '4': {'names_sha256': 'h4', 'count': 53, 'elements': 4 * VIT_BLOCK + 394752 + 513}}
    return dict(version='vit_structure_v1', base={'sha256': sha, 'bytes': 1}, vit_blocks=12, patch_size=[16, 16], width=768,
                total_parameters=sum(b['parameters'] for b in blocks.values()), blocks=blocks, trainable=trainable)


def vit_records(sha='a' * 64, fine_sha='h4'):
    base = {'checkpoint': {'sha256': sha, 'bytes': 1}}
    groups = lambda *items: {'name': 'adamw', 'groups': [{'name': n, 'lr': lr, 'parameters': p} for n, lr, p in items]}
    return [{'phase': 'base', 'payload': {'framework': 'pytorch', 'encoder': 'frozen', 'base_model': base, 'optimizer': groups(('head', 1e-3, 513)),
                                         'trainable_parameters': {'names_sha256': 'h0', 'count': 2, 'elements': 513}}},
            {'phase': 'fine_tuning', 'payload': {'framework': 'pytorch', 'encoder': 'last_4_blocks', 'base_model': base,
                                                'optimizer': groups(('head', 1e-3, 513), ('encoder', 1e-5, 28746240)),
                                                'trainable_parameters': {'names_sha256': fine_sha, 'count': 53, 'elements': 28746753}}}]


def vit_configuration(sha='a' * 64):
    return dict(architecture='biomedclip_fine_tuning', input_height=224, input_width=224, input_channels=3, extension_configuration={
        'recipe': {'head': {'in_features': 512, 'out_features': 1, 'activation': 'sigmoid', 'loss': 'bce_with_logits'},
                   'base_model': {'checkpoint': {'sha256': sha, 'bytes': 1}}},
        'input_contract': {'output': {'meaning': 'probability_parasitized'}}})


def test_vit_blocks_take_shapes_and_parameters_from_the_registered_base():
    result = normalize_biomedclip(vit_records(), vit_configuration(), vit_structure())
    ids = [block['id'] for block in result['blocks']]
    assert ids[:2] == ['input', 'embedding'] and ids[-2:] == ['projection', 'output'] and len(ids) == 16
    vit = [block for block in result['blocks'] if block['kind'] == 'encoder']
    assert {block['origin'] for block in vit} == {'derived'} and {block['parameters'] for block in vit} == {VIT_BLOCK}
    assert vit[0]['output_shape'] == [None, 197, 768]
    projection = next(block for block in result['blocks'] if block['id'] == 'projection')
    assert projection['output_shape'] == [None, 512] and projection['trainable_phases'] == ['fine_tuning']
    assert next(block for block in result['blocks'] if block['id'] == 'embedding')['trainable_phases'] == []
    assert result['total_parameters'] == 12 * VIT_BLOCK + 742656 + 394752 + 513
    assert result['structure'] == {'origin': 'derived', 'base_sha256': 'a' * 64, 'vit_blocks': 12, 'patch_size': [16, 16],
                                   'width': 768, 'patches': 196, 'tokens': 197}
    assert [phase['structure_check'] for phase in result['phases']] == ['match', 'match'] and not result['issues']
    assert result['phases'][1]['learning_rates'] == [{'group': 'head', 'learning_rate': 1e-3, 'parameters': 513},
                                                     {'group': 'encoder', 'learning_rate': 1e-5, 'parameters': 28746240}]


def test_a_recorded_trainable_set_that_differs_from_the_base_is_reported():
    result = normalize_biomedclip(vit_records(fine_sha='otro'), vit_configuration(), vit_structure())
    assert [phase['structure_check'] for phase in result['phases']] == ['match', 'mismatch']
    assert len(result['issues']) == 1 and 'fine_tuning' in result['issues'][0]


class Structures:
    def __init__(self, structure=None, error=None):
        self.structure, self.error, self.calls = structure, error, []

    def read(self, base, input_size):
        self.calls.append((base['checkpoint']['sha256'], input_size))
        if self.error:
            raise self.error
        return self.structure


def vit_source(records):
    return dict(run={'run_type': 'training', 'model_name': 'biomedclip_fine_tuning'}, configuration=vit_configuration(),
                records=records, checkpoint=None)


def test_the_service_derives_the_structure_from_the_base_every_phase_recorded():
    structures = Structures(vit_structure())
    result = ModelArchitecture.model_validate(ModelArchitectureService(Repository(vit_source(vit_records())), structures).read(uuid4(), 'malaria'))
    assert structures.calls == [('a' * 64, 224)] and result.structure.tokens == 197 and not result.issues
    assert result.phases[1].learning_rates[1].group == 'encoder'


def test_without_the_structure_the_vit_keeps_its_reference_blocks_and_says_why():
    from app.services.vit_structure import StructureUnavailable
    service = ModelArchitectureService(Repository(vit_source(vit_records())), Structures(error=StructureUnavailable('Sin base.')))
    result = ModelArchitecture.model_validate(service.read(uuid4(), 'malaria'))
    assert result.structure is None and {b.origin for b in result.blocks if b.kind == 'encoder'} == {'reference'}
    assert result.issues == ['Sin base. Los bloques ViT quedan como estructura de referencia.']
    other = ModelArchitectureService(Repository(vit_source(vit_records(sha='b' * 64))), Structures(vit_structure()))
    assert 'no coincide' in other.read(uuid4(), 'malaria')['issues'][0]


def test_keras_phases_expose_the_learning_rate_compiled_for_the_phase():
    from app.services.model_architecture import learning_rates
    assert learning_rates({'optimizer': {'name': 'SGD', 'learning_rate': 1.25e-05}}) == [{'group': 'model', 'learning_rate': 1.25e-05, 'parameters': None}]
    assert learning_rates({}) == []


def test_saved_structures_are_reused_and_identities_are_validated(tmp_path):
    import json
    from app.services.vit_structure import StructureUnavailable, VitStructureService
    from app.services.vit_structure_compute import VERSION, group_of
    service = VitStructureService(tmp_path)
    (tmp_path / f"{'c' * 64}.json").write_text(json.dumps({'version': VERSION, 'base': {'sha256': 'c' * 64}, 'blocks': {}}))
    assert service.read({'checkpoint': {'sha256': 'c' * 64}}, 224)['base']['sha256'] == 'c' * 64
    with pytest.raises(StructureUnavailable):
        service.read({'checkpoint': {'sha256': '../x'}}, 224)
    assert [group_of(n) for n in ('head.weight', 'visual.trunk.blocks.11.mlp.fc1.weight', 'visual.trunk.pos_embed',
                                  'visual.head.proj.weight', 'visual.trunk.norm.bias')] == ['output', 'vit11', 'embedding', 'projection', 'projection']


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


ZERO_SHOT_SHA = '5' * 64


def zero_shot_source():
    version = dict(model_version_id=uuid4(), training_run_id=uuid4(), sha256=ZERO_SHOT_SHA, bytes=783705670,
                   profile={'prompts': ['a photo of an uninfected red blood cell', 'a photo of a parasitized red blood cell'],
                            'class_order': ['uninfected', 'parasitized'],
                            'dependencies': [{'role': 'model_config', 'sha256': 'b' * 64, 'bytes': 707, 'path': '/x'}]},
                   output_signature={'meaning': 'relative softmax score_parasitized; not clinically calibrated'})
    return dict(run={'run_type': 'training', 'model_name': 'biomedclip_zero_shot'}, configuration=None, records=[],
                logical_version=version, checkpoint=None)


def zero_shot_structure():
    structure = vit_structure(ZERO_SHOT_SHA)
    structure.update(input_size=224, text={'parameters': 109479168, 'tensors': 200, 'logit_scale': 1})
    return structure


def test_zero_shot_is_read_from_its_registered_version_and_nothing_is_trained():
    structures = Structures(zero_shot_structure())
    result = ModelArchitecture.model_validate(ModelArchitectureService(Repository(zero_shot_source()), structures).read(uuid4(), 'malaria'))
    assert result.state == 'available' and result.family == 'biomedclip' and not result.issues
    assert structures.calls == [(ZERO_SHOT_SHA, 224)]
    assert result.phases == [] and all(block.trainable_phases == [] for block in result.blocks)
    vit = [block for block in result.blocks if block.kind == 'encoder']
    assert len(vit) == 12 and {block.origin for block in vit} == {'derived'}
    output = result.blocks[-1]
    assert output.label == 'Similitud con 2 prompts' and output.output_shape == [None, 2] and output.parameters == 109479169
    assert result.output.activation == 'softmax' and result.output.neurons == 2 and result.output.embedding_features == 512
    assert result.zero_shot.prompts[1] == 'a photo of a parasitized red blood cell' and result.zero_shot.training_performed is False
    assert result.total_parameters == 742656 + 12 * VIT_BLOCK + 394752 + 109479169
    assert result.input_shape == [None, 224, 224, 3]


def test_zero_shot_base_is_its_own_version_with_dependency_identities_only():
    from app.services.model_architecture import logical_base
    version = zero_shot_source()['logical_version']
    base = logical_base(version)
    assert base['checkpoint'] == {'sha256': ZERO_SHOT_SHA, 'bytes': 783705670}
    assert base['dependencies'] == [{'role': 'model_config', 'sha256': 'b' * 64, 'bytes': 707}]
    assert base['model_version_id'] == str(version['model_version_id'])


def test_zero_shot_without_its_structure_keeps_reference_blocks():
    from app.services.vit_structure import StructureUnavailable
    service = ModelArchitectureService(Repository(zero_shot_source()), Structures(error=StructureUnavailable('Sin base.')))
    result = ModelArchitecture.model_validate(service.read(uuid4(), 'malaria'))
    assert {b.origin for b in result.blocks if b.kind == 'encoder'} == {'reference'} and result.total_parameters is None
    assert result.issues == ['Sin base. Los bloques ViT quedan como estructura de referencia.']
