"""Normalize the architecture recorded by TRAIN from persisted evidence. Keras records its layers; for a ViT the
block structure is derived once from the registered base (``vit_structure``), never from trained weights."""
import re
from typing import Annotated, Any
from uuid import UUID
from fastapi import Depends, HTTPException
from app.repositories.model_architecture import ModelArchitectureRepository
from app.services.scientific_report import checkpoint_evidence
from app.services.vit_structure import StructureUnavailable, VitStructureService
from src.malaria_dl.models.biomedclip_training import VIT_BLOCKS

SETTINGS = ('filters', 'kernel_size', 'strides', 'pool_size', 'padding', 'activation', 'units', 'rate', 'use_bias',
            'center', 'scale', 'epsilon', 'mean', 'variance')
NESTED = ('Functional', 'Sequential')


def family_of(architecture: str | None) -> str:
    name = architecture or ''
    if name.startswith('biomedclip'):
        return 'biomedclip'
    return name if name in ('custom_cnn', 'vgg16', 'densenet121') else 'generic'


def _tensors(value: Any):
    if isinstance(value, dict):
        if value.get('class_name') == '__keras_tensor__':
            yield value['config']
        else:
            for item in value.values():
                yield from _tensors(item)
    elif isinstance(value, list):
        for item in value:
            yield from _tensors(item)


def _output_shape(layer: dict[str, Any], incoming: list[int | None] | None) -> list[int | None] | None:
    """Keras shape rule, used where the record keeps no consumer tensor (Sequential)."""
    config, kind = layer['config'], layer['class_name']
    if kind == 'InputLayer':
        return config.get('batch_shape')
    if incoming is None:
        return None
    if kind == 'GlobalAveragePooling2D':
        return [incoming[0], incoming[-1]]
    if kind == 'Dense':
        return [*incoming[:-1], config['units']]
    if kind == 'Conv2D' or kind == 'MaxPooling2D':
        size = config.get('kernel_size') or config.get('pool_size')
        strides = config.get('strides') or size
        same = config.get('padding') == 'same'
        spatial = [(value + stride - 1) // stride if same else (value - window) // stride + 1
                   for value, window, stride in zip(incoming[1:3], size, strides)]
        return [incoming[0], *spatial, config['filters'] if kind == 'Conv2D' else incoming[-1]]
    return incoming


def _weights(layer: dict[str, Any], incoming: Any) -> tuple[int, int]:
    """(total, trainable) weights implied by the recorded layer configuration."""
    config, kind = layer['config'], layer['class_name']
    channels = incoming[-1] if incoming else None
    if kind == 'Conv2D' and channels:
        kernel = config['kernel_size'][0] * config['kernel_size'][1] * channels * config['filters']
        total = kernel + (config['filters'] if config.get('use_bias', True) else 0)
        return total, total
    if kind == 'Dense' and channels:
        total = (channels + (1 if config.get('use_bias', True) else 0)) * config['units']
        return total, total
    if kind == 'BatchNormalization' and channels:
        trainable = channels * (int(config.get('center', True)) + int(config.get('scale', True)))
        return trainable + 2 * channels, trainable
    return 0, 0


def _flatten(model: dict[str, Any], phase_name: str, target: dict[str, dict], parent_input: str | None = None) -> str | None:
    """Flatten a Keras config into `target` (execution order). Returns the name of the model's output."""
    layers = model['layers']
    sequential = not any(layer.get('inbound_nodes') for layer in layers)
    shapes: dict[str, Any] = {}
    for layer in layers:
        for tensor in _tensors(layer.get('inbound_nodes')):
            shapes[tensor['keras_history'][0]] = tensor.get('shape')
    aliases: dict[str, str] = {}
    previous: str | None = None
    previous_shape: list[int | None] | None = None
    for layer in layers:
        config = layer['config']
        name = layer.get('name') or config['name']
        sources = [tensor['keras_history'][0] for tensor in _tensors(layer.get('inbound_nodes'))]
        if sequential and previous:
            sources = [previous]
        inputs = [aliases.get(source, source) for source in sources]
        if layer['class_name'] in NESTED:
            aliases[name] = _flatten(config, phase_name, target, inputs[0] if inputs else None)
            previous = name
            continue
        if layer['class_name'] == 'InputLayer' and parent_input:
            aliases[name] = parent_input
            previous = name
            continue
        incoming = [tensor.get('shape') for tensor in _tensors(layer.get('inbound_nodes'))]
        received = (incoming if len(incoming) > 1 else incoming[0]) if incoming else previous_shape
        output = _output_shape(layer, previous_shape) if sequential else shapes.get(name)
        if not sequential and output is None and layer['class_name'] == 'InputLayer':
            output = config.get('batch_shape')
        channels = received[0] if received and isinstance(received[0], list) else received
        total, trainable = _weights(layer, channels)
        entry = target.setdefault(name, dict(
            name=name, type=layer['class_name'], block='', output_shape=output, inputs=inputs, parameters=total,
            trainable_phases=[], weights=trainable,
            settings={key: config[key] for key in SETTINGS if key in config}))
        if config.get('trainable', True):
            entry['trainable_phases'].append(phase_name)
        previous, previous_shape = name, output
    outputs = model.get('output_layers')
    return aliases.get(outputs[0], outputs[0]) if outputs else previous


def _last_shape(layers: list[dict[str, Any]], output: dict[str, Any] | None) -> None:
    if layers and layers[-1]['output_shape'] is None and output:
        layers[-1]['output_shape'] = output.get('shape')


def _keras_block(family: str, layer: dict[str, Any], state: dict[str, int]) -> tuple[str, str, str]:
    name, kind = layer['name'], layer['type']
    if kind in ('InputLayer', 'Normalization'):
        return 'input', 'Entrada', 'input'
    if family == 'vgg16' and (match := re.match(r'block(\d+)_', name)):
        return f'block{match[1]}', f'Bloque {match[1]}', 'convolution'
    if family == 'densenet121':
        if match := re.match(r'conv(\d)_block', name):
            return f'dense{match[1]}', f'Bloque denso {int(match[1]) - 1}', 'dense'
        if match := re.match(r'pool([234])_', name):
            return f'transition{match[1]}', f'Transición {int(match[1]) - 1}', 'transition'
        if name.startswith(('conv1', 'zero_padding2d', 'pool1')):
            return 'stem', 'Convolución inicial', 'convolution'
    if family == 'custom_cnn' and kind in ('Conv2D', 'BatchNormalization', 'Activation', 'MaxPooling2D'):
        state['convolutions'] += kind == 'Conv2D'
        return f"block{state['convolutions']}", f"Bloque {state['convolutions']}", 'convolution'
    if kind == 'Dense' and layer['settings'].get('activation') == 'sigmoid':
        return 'output', 'Capa de salida', 'output'
    return 'head', 'Cabeza de clasificación', 'head'


def _summarize(layers: list[dict[str, Any]], family: str, origin: str) -> list[dict[str, Any]]:
    blocks: dict[str, dict[str, Any]] = {}
    state = {'convolutions': 0}
    for layer in layers:
        block, label, kind = _keras_block(family, layer, state)
        layer['block'] = block
        entry = blocks.setdefault(block, dict(id=block, label=label, kind=kind, layers=0, units=None, output_shape=None,
                                              parameters=0, trainable_phases=[], origin=origin))
        entry['layers'] += 1
        entry['parameters'] += layer['parameters'] or 0
        if layer['output_shape'] is not None:
            entry['output_shape'] = layer['output_shape']
        if layer['type'] == 'Concatenate':
            entry['units'] = (entry['units'] or 0) + 1
        if layer['type'] != 'InputLayer' and (layer['parameters'] or layer['type'] == 'Concatenate'):
            entry['trainable_phases'] = sorted({*entry['trainable_phases'], *layer['trainable_phases']})
    return list(blocks.values())


def normalize_keras(records: list[dict[str, Any]], family: str) -> dict[str, Any]:
    layers: dict[str, dict] = {}
    phases = []
    for record in records:
        architecture = record['payload']['architecture']
        _flatten(architecture.get('config', architecture), record['phase'], layers)
        trained = sum(layer['weights'] for layer in layers.values() if record['phase'] in layer['trainable_phases'])
        phases.append(dict(phase=record['phase'], trainable_parameters=trained, learning_rates=learning_rates(record['payload'])))
    ordered = list(layers.values())
    contract_output = records[-1]['payload'].get('output_contract') or {}
    _last_shape(ordered, contract_output)
    blocks = _summarize(ordered, family, 'recorded')
    for layer in ordered:
        layer.pop('weights')
    contract = records[-1]['payload'].get('input_contract') or {}
    loss = records[-1]['payload'].get('loss') or {}
    output = dict(neurons=(contract_output.get('shape') or [None])[-1], activation=contract_output.get('activation'),
                  loss=loss.get('name'), from_logits=loss.get('from_logits'), meaning=contract_output.get('meaning'))
    return dict(framework='keras', input_shape=contract.get('shape'), output=output, phases=phases, blocks=blocks,
                layers=ordered, total_parameters=sum(layer['parameters'] for layer in ordered))


def _vit_trained(encoder: str | None) -> set[int]:
    if encoder == 'full':
        return set(range(VIT_BLOCKS))
    match = re.fullmatch(r'last_(\d+)_blocks', encoder or '')
    return set(range(VIT_BLOCKS - int(match[1]), VIT_BLOCKS)) if match else set()


def _fine_tune_layers(encoder: str | None) -> int | None:
    if encoder == 'frozen':
        return 0
    if encoder == 'full':
        return VIT_BLOCKS
    match = re.fullmatch(r'last_(\d+)_blocks', encoder or '')
    return int(match[1]) if match else None


def learning_rates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Initial learning rate of each optimizer group in a phase, as recorded at the phase start."""
    optimizer = payload.get('optimizer') or {}
    groups = optimizer.get('groups')
    if isinstance(groups, list):
        return [dict(group=g.get('name'), learning_rate=g.get('lr'), parameters=g.get('parameters')) for g in groups if isinstance(g, dict)]
    rate = optimizer.get('learning_rate')
    return [dict(group='model', learning_rate=rate, parameters=None)] if isinstance(rate, (int, float)) else []


def normalize_biomedclip(records: list[dict[str, Any]], configuration: dict[str, Any] | None,
                         structure: dict[str, Any] | None = None) -> dict[str, Any]:
    """The TRAIN records tensor counts, not layers. Block shapes and parameters come from the registered base
    (``structure``, derived once per base SHA-256); without it the ViT blocks stay a reference structure."""
    extension = (configuration or {}).get('extension_configuration') or {}
    head = (extension.get('recipe') or {}).get('head') or {}
    side = (configuration or {}).get('input_height')
    channels = (configuration or {}).get('input_channels')
    width = (configuration or {}).get('input_width')
    shape = [None, side, width, channels] if side else None
    encoded = [(record['phase'], record['payload'].get('encoder')) for record in records]
    derived = (structure or {}).get('blocks') or {}
    trained_in = lambda test: [phase for phase, encoder in encoded if (layers := _fine_tune_layers(encoder)) is not None and test(layers)]

    def block(id_, label, kind, output, phases, origin, parameters=None):
        part = derived.get(id_) if structure else None
        if part:
            output, parameters, origin = [None, *part['output_shape'][1:]], part['parameters'], 'derived' if origin == 'reference' else origin
        return dict(id=id_, label=label, kind=kind, layers=1, units=None, output_shape=output, parameters=parameters,
                    trainable_phases=phases, origin=origin)

    embedding = head.get('in_features')
    # With the base structure every block has a known count; the input carries no weights.
    blocks = [block('input', 'Entrada', 'input', shape, [], 'recorded', 0 if structure else None)]
    if structure:
        blocks.append(block('embedding', 'Parches y posición', 'transition', None, trained_in(lambda n: n == VIT_BLOCKS), 'reference'))
    blocks += [block(f'vit{index}', f'Bloque ViT {index + 1}', 'encoder', None,
                     [phase for phase, encoder in encoded if index in _vit_trained(encoder)], 'reference')
               for index in range(VIT_BLOCKS)]
    if structure:
        blocks.append(block('projection', 'Norma y proyección', 'head', None, trained_in(lambda n: n > 0), 'reference'))
    blocks.append(block('output', 'Capa de salida', 'output', [None, head.get('out_features')],
                        [phase for phase, _ in encoded], 'recorded', (embedding + 1) if embedding else None))
    issues, phases = [], []
    for record in records:
        payload = record['payload']
        recorded = payload.get('trainable_parameters') or {}
        layers = _fine_tune_layers(payload.get('encoder'))
        expected = ((structure or {}).get('trainable') or {}).get(str(layers)) if layers is not None else None
        check = None
        if expected:
            check = 'match' if all(recorded.get(key) == expected[key] for key in ('names_sha256', 'count', 'elements')) else 'mismatch'
            if check == 'mismatch':
                issues.append(f"Fase {record['phase']}: el conjunto entrenable registrado no coincide con el que declara la base para "
                              f"{payload.get('encoder')} ({recorded.get('elements')} vs {expected['elements']} parámetros).")
        phases.append(dict(phase=record['phase'], encoder=payload.get('encoder'),
                           trainable_parameters=recorded.get('elements'), trainable_tensors=recorded.get('count'),
                           structure_check=check, learning_rates=learning_rates(payload)))
    contract = (extension.get('input_contract') or {}).get('output') or {}
    result = dict(framework=records[-1]['payload'].get('framework'), input_shape=shape,
                  output=dict(neurons=head.get('out_features'), activation=head.get('activation'), loss=head.get('loss'),
                              from_logits=head.get('loss') == 'bce_with_logits', meaning=contract.get('meaning'),
                              embedding_features=embedding),
                  phases=phases, blocks=blocks, layers=[], total_parameters=(structure or {}).get('total_parameters'),
                  structure=None)
    if structure:
        patches = derived.get('embedding', {}).get('patches')
        result['structure'] = dict(origin='derived', base_sha256=structure['base']['sha256'], vit_blocks=structure.get('vit_blocks'),
                                   patch_size=structure.get('patch_size'), width=structure.get('width'),
                                   patches=patches[1] if patches and len(patches) == 3 else None,
                                   tokens=(derived.get('vit0', {}).get('output_shape') or [None, None])[1])
        if derived.get('other', {}).get('parameters'):
            issues.append('La base tiene parámetros fuera de los bloques conocidos; se cuentan en el total, no en un bloque.')
    return dict(result, issues=issues)


def recorded_base(records: list[dict[str, Any]], configuration: dict[str, Any] | None) -> tuple[dict[str, Any] | None, str | None]:
    """The registered base of the recipe, only if every phase of the TRAIN recorded that same checkpoint."""
    base = (((configuration or {}).get('extension_configuration') or {}).get('recipe') or {}).get('base_model')
    sha256 = ((base or {}).get('checkpoint') or {}).get('sha256')
    if not sha256:
        return None, 'La receta no identifica la base registrada: los bloques ViT quedan como estructura de referencia.'
    used = {((record['payload'].get('base_model') or {}).get('checkpoint') or {}).get('sha256') for record in records}
    if used != {sha256}:
        return None, 'La base registrada por TRAIN no coincide con la de la receta: los bloques ViT quedan como estructura de referencia.'
    return base, None


class ModelArchitectureService:
    def __init__(self, repository: ModelArchitectureRepository, structures: VitStructureService | None = None) -> None:
        self.repository = repository
        self.structures = structures or VitStructureService()

    def vit_structure(self, records, configuration) -> tuple[dict[str, Any] | None, list[str]]:
        base, issue = recorded_base(records, configuration)
        if base is None:
            return None, [issue]
        try:
            return self.structures.read(base, int((configuration or {}).get('input_height') or 224)), []
        except StructureUnavailable as error:
            return None, [f'{error} Los bloques ViT quedan como estructura de referencia.']

    def read(self, run_id: UUID, datasource: str | None) -> dict[str, Any]:
        source = self.repository.read(run_id, datasource)
        if source is None:
            raise HTTPException(404, 'Run no encontrado')
        if source['run']['run_type'] != 'training':
            raise HTTPException(422, 'run_id debe identificar un TRAIN')
        configuration = source['configuration']
        name = (configuration or {}).get('architecture')
        family = family_of(name)
        checkpoint = checkpoint_evidence(source['checkpoint'], run_id) if source['checkpoint'] else {}
        result = dict(training_run_id=run_id, state='available', issues=[], model_name=source['run']['model_name'],
                      architecture=name, family=family, framework=None, input_shape=None, output=None,
                      total_parameters=None, phases=[], blocks=[], layers=[], checkpoint=dict(
                          artifact_id=str(checkpoint['artifact_id']) if checkpoint.get('artifact_id') else None, selected_epoch=checkpoint.get('selected_epoch'),
                          phase=checkpoint.get('phase')))
        records = source['records']
        if not records:
            return dict(result, state='missing', issues=['Este TRAIN no registró su configuración de ejecución.'])
        if family == 'biomedclip':
            structure, issues = self.vit_structure(records, configuration)
            normalized = normalize_biomedclip(records, configuration, structure)
            return {**result, **normalized, 'issues': issues + normalized['issues']}
        if any('architecture' not in record['payload'] for record in records):
            return dict(result, state='missing', issues=['El registro de ejecución no incluye la arquitectura.'])
        return dict(result, **normalize_keras(records, family))


def get_model_architecture_service(
    repository: Annotated[ModelArchitectureRepository, Depends()],
) -> ModelArchitectureService:
    return ModelArchitectureService(repository)
