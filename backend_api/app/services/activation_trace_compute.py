"""Forward pass of one governed cell. Runs in its own process: TensorFlow never enters the API."""
import base64
import json
import math
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = 'activation_trace_v2'
CHANNELS = 16
MAP_SIZE = 64
BINS = 24
TOLERANCE = 1e-3
SELECTION = f'{CHANNELS} canales de mayor activación media'
# Head layers worth a step; Dropout is the identity in inference and is skipped.
HEAD_TYPES = ('GlobalAveragePooling2D', 'GlobalMaxPooling2D', 'Flatten', 'Dense')


def block_of(layer: str, output: bool = False) -> str:
    match = re.match(r'(block\d+)_', layer)
    return match[1] if match else 'output' if output or layer == 'binary_output' else 'head'


def traced_layers(layers: list[Any]) -> list[str]:
    """Block poolings, then the head as this TRAIN built it: each run may use GAP, Flatten or other Dense sizes."""
    names = [layer.name for layer in layers if re.fullmatch(r'block\d+_pool', layer.name)]
    last = max((index for index, layer in enumerate(layers) if layer.name in names), default=-1)
    head = [layer.name for layer in layers[last + 1:] if type(layer).__name__ in HEAD_TYPES]
    output = layers[-1].name
    return names + [name for name in head if name != output] + [output]


CONV_BLOCK_TYPES = ('Conv2D', 'BatchNormalization', 'Activation', 'MaxPooling2D')


def custom_cnn_blocks(layers: list[Any]) -> dict[str, str]:
    """Block of each layer with the rule of the architecture service: every Conv2D opens a block that also holds
    its BatchNormalization, Activation and pooling; the rest is the head, and the sigmoid Dense is the output."""
    blocks, count = {}, 0
    for layer in layers:
        kind = type(layer).__name__
        if kind in CONV_BLOCK_TYPES and (kind == 'Conv2D' or count):
            count += kind == 'Conv2D'
            blocks[layer.name] = f'block{count}'
        else:
            blocks[layer.name] = 'head'
    if layers:
        blocks[layers[-1].name] = 'output'
    return blocks


def traced_custom_cnn(layers: list[Any]) -> list[str]:
    """Output of each convolutional block (its last layer: pooling, or the activation of a block without pooling),
    then the head layers that change the tensor and the output."""
    blocks = custom_cnn_blocks(layers)
    ends = {}
    for layer in layers:
        if blocks[layer.name].startswith('block'):
            ends[blocks[layer.name]] = layer.name
    head = [layer.name for layer in layers if blocks[layer.name] == 'head' and type(layer).__name__ in HEAD_TYPES]
    return list(ends.values()) + head + [layers[-1].name]


def densenet_block(layer: Any) -> str:
    """Block of a DenseNet121 layer, with the rule of the architecture service (``_keras_block``)."""
    name, kind = layer.name, type(layer).__name__
    if kind in ('InputLayer', 'Normalization'):
        return 'input'
    if match := re.match(r'conv(\d)_block', name):
        return f'dense{match[1]}'
    if match := re.match(r'pool([234])_', name):
        return f'transition{match[1]}'
    if name.startswith(('conv1', 'zero_padding2d', 'pool1')):
        return 'stem'
    if kind == 'Dense' and getattr(getattr(layer, 'activation', None), '__name__', None) == 'sigmoid':
        return 'output'
    return 'head'


def flattened(tf: Any, model: Any) -> list[Any]:
    """Layers in flow order, with the nested backbone expanded in place (as the architecture service flattens it)."""
    result = []
    for layer in model.layers:
        if isinstance(layer, tf.keras.Model):
            result += [inner for inner in layer.layers if type(inner).__name__ != 'InputLayer']
        else:
            result.append(layer)
    return result


def traced_densenet(layers: list[Any]) -> tuple[list[str], dict[str, str]]:
    """Output of each architecture block (its last layer), then the final activated features, the head and the output."""
    blocks = {layer.name: densenet_block(layer) for layer in layers}
    ends: dict[str, str] = {}
    for layer in layers:
        if blocks[layer.name] not in ('input', 'head', 'output'):
            ends[blocks[layer.name]] = layer.name
    last = max((i for i, layer in enumerate(layers) if layer.name in ends.values()), default=-1)
    head = [layer for layer in layers[last + 1:] if blocks[layer.name] == 'head']
    # The backbone ends in BatchNormalization + ReLU: its ReLU is the activated map the head pools.
    final = [layer.name for layer in head if type(layer).__name__ in ('Activation', 'ReLU')][-1:]
    names = list(ends.values()) + final + [layer.name for layer in head if type(layer).__name__ in HEAD_TYPES]
    names = [name for name in names if blocks[name] != 'output'] + [layers[-1].name]
    return names, {name: blocks[name] for name in names}


def nested_outputs(tf: Any, model: Any, images: Any, names: list[str]) -> list[Any]:
    """Outputs of ``names`` for a linear chain whose backbone is a nested model: Keras cannot expose the backbone's
    inner layers as outputs of the outer graph, so the backbone runs once as its own sub-model and the outer layers
    are applied around it. The result must reproduce the model's own output."""
    import numpy as np

    from src.malaria_dl.assessment.contracts import require

    nested = [layer for layer in model.layers if isinstance(layer, tf.keras.Model)]
    require(len(nested) == 1, 'TRACE_BACKBONE_AMBIGUOUS')
    inner = nested[0]
    own = {layer.name for layer in inner.layers}
    inner_names = [name for name in names if name in own]
    backbone = tf.keras.Model(inputs=inner.inputs, outputs=[inner.get_layer(name).output for name in inner_names] + [inner.outputs[0]])
    values: dict[str, Any] = {}
    x = images
    for layer in model.layers:
        if type(layer).__name__ == 'InputLayer':
            continue
        if layer is inner:
            *read, x = backbone(x, training=False)
            values.update(zip(inner_names, read))
        else:
            x = layer(x, training=False)
            values[layer.name] = x
    expected = np.asarray(model(images, training=False))
    require(np.allclose(np.asarray(x), expected, rtol=1e-4, atol=1e-6), 'TRACE_CHAIN_MISMATCH')
    return [values[name] for name in names]


def traced(layers: list[Any], family: str) -> tuple[list[str], dict[str, str]]:
    """(layers to read, block of each read layer). VGG16 keeps its own naming; custom_cnn uses the block rule."""
    if family == 'densenet121':
        return traced_densenet(layers)
    if family == 'custom_cnn':
        blocks = custom_cnn_blocks(layers)
        names = traced_custom_cnn(layers)
        return names, {name: blocks[name] for name in names}
    names = traced_layers(layers)
    return names, {name: block_of(name, index == len(names) - 1) for index, name in enumerate(names)}


def histogram(np: Any, values: Any) -> dict[str, list[float]]:
    counts, edges = np.histogram(values, bins=BINS)
    return {'counts': [int(count) for count in counts], 'edges': [float(edge) for edge in edges]}


def statistics(values: Any) -> dict[str, float]:
    return {'min': float(values.min()), 'max': float(values.max()), 'mean': float(values.mean()),
            'std': float(values.std()), 'active': float((values > 0).mean())}


def channel_png(tf: Any, channel: Any) -> str:
    low, high = float(channel.min()), float(channel.max())
    scaled = (channel - low) / (high - low) if high > low else channel * 0
    image = tf.convert_to_tensor(scaled[..., None], dtype=tf.float32)
    if max(image.shape[:2]) > MAP_SIZE:
        image = tf.image.resize(image, (MAP_SIZE, MAP_SIZE), method='area')
    pixels = tf.cast(tf.round(image * 255), tf.uint8)
    return base64.b64encode(tf.io.encode_png(pixels).numpy()).decode()


def trace_steps(tf: Any, np: Any, names: list[str], outputs: list[Any], blocks: dict[str, str] | None = None) -> list[dict[str, Any]]:
    steps = []
    for position, (name, output) in enumerate(zip(names, outputs)):
        values, last = np.asarray(output)[0], position == len(names) - 1
        block = blocks[name] if blocks else block_of(name, last)
        step = dict(layer=name, block=block, shape=list(values.shape), stats=statistics(values), maps=[], top=[])
        if values.ndim == 3:
            order = np.argsort(values.mean(axis=(0, 1)))[::-1][:CHANNELS]
            # min and max let the client rebuild raw values from the PNG and redraw them on one layer-wide scale.
            step.update(kind='spatial', maps=[dict(channel=int(index), mean=float(values[..., index].mean()),
                                                   min=float(values[..., index].min()), max=float(values[..., index].max()),
                                                   png=channel_png(tf, values[..., index])) for index in order])
        else:
            order = np.argsort(np.abs(values))[::-1][:CHANNELS]
            step.update(kind='output' if last else 'vector', top=[dict(index=int(index), value=float(values[index])) for index in order])
            if not last:
                step['histogram'] = histogram(np, values)
        steps.append(step)
    return steps


def compute(value: dict[str, Any], sample: dict[str, Any], persisted: dict[str, Any], family: str = 'vgg16') -> dict[str, Any]:
    from src.malaria_dl.assessment.runtime import KerasRuntime, verified_sample_bytes

    runtime = KerasRuntime(value)
    tf, np = runtime.tf, __import__('numpy')
    images = runtime.images([sample])
    if family == 'densenet121':
        names, blocks = traced(flattened(tf, runtime.model), family)
        outputs = nested_outputs(tf, runtime.model, images, names)
    else:
        names, blocks = traced(runtime.model.layers, family)
        model = tf.keras.Model(inputs=runtime.model.inputs, outputs=[runtime.model.get_layer(name).output for name in names])
        outputs = model(images, training=False)
    steps = trace_steps(tf, np, names, outputs, blocks)
    score = steps[-1]['top'][0]['value']
    clipped = min(max(score, 1e-12), 1 - 1e-12)
    rgb = tf.io.decode_image(verified_sample_bytes(value, runtime.dataset_root, sample), channels=3, expand_animations=False)
    expected = persisted.get('raw_score')
    return dict(score=score, logit=math.log(clipped / (1 - clipped)), persisted_score=expected, label=persisted.get('label'),
                predicted=persisted.get('predicted'), threshold=persisted.get('threshold'),
                consistent=expected is not None and abs(score - expected) <= TOLERANCE, selection=SELECTION, steps=steps,
                input_image=base64.b64encode(tf.io.encode_png(rgb).numpy()).decode())


def write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=path.parent, suffix='.tmp', delete=False) as stream:
        json.dump(payload, stream, separators=(',', ':'))
    os.replace(stream.name, path)


def main() -> None:
    job = json.loads(sys.stdin.readline())
    result = compute(job['value'], job['sample'], job['persisted'], job.get('family', 'vgg16'))
    write_atomic(Path(job['path']), {**job['identity'], **result, 'version': VERSION,
                                     'created_at': datetime.now(timezone.utc).isoformat()})


if __name__ == '__main__':
    main()
