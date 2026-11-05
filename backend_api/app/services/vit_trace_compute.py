"""Forward pass of one governed cell through a BiomedCLIP (ViT) model. Runs in its own process: PyTorch never enters
the API. Same step contract as the Keras trace, so the same panel draws it:

- each token tensor (patch embedding and the 12 Transformer blocks) is drawn as its 14×14 patch grid, one map per
  token dimension (the 16 with largest mean magnitude), plus the attention of the class token over the patches;
- the projection is the L2-normalized embedding (vector); the output is the parasitized score.

The model is the one the EVALUATE ran (``runtime_for``): zero-shot compares the embedding with the prompts and applies
softmax; linear probing and fine-tuning apply their sigmoid head. Attention weights are read with timm's explicit
attention path for this pass only; the score must still match the EVALUATE's persisted score.
"""
import base64
import io
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.activation_trace_compute import CHANNELS, TOLERANCE, histogram, statistics, write_atomic

VERSION = 'activation_trace_vit_v1'
SELECTION = f'{CHANNELS} dimensiones de mayor magnitud media sobre los parches'


def png(np: Any, values: Any) -> tuple[str, float, float]:
    """Grayscale PNG of a 2D map scaled to its own range, with that range to rebuild raw values."""
    from PIL import Image

    low, high = float(values.min()), float(values.max())
    scaled = (values - low) / (high - low) if high > low else values * 0
    stream = io.BytesIO()
    Image.fromarray(np.round(scaled * 255).astype('uint8'), mode='L').save(stream, format='PNG')
    return base64.b64encode(stream.getvalue()).decode(), low, high


def token_step(np: Any, layer: str, block: str, tokens: Any, prefix: int, attention: Any | None, final_cls: Any) -> dict[str, Any]:
    """Step of a token tensor (tokens × width): patch grid maps, class-token attention and class-token similarity."""
    patches = tokens[prefix:]
    side = int(round(math.sqrt(len(patches))))
    grid = patches.reshape(side, side, -1)
    order = np.argsort(np.abs(grid).mean(axis=(0, 1)))[::-1][:CHANNELS]
    maps = []
    for index in order:
        encoded, low, high = png(np, grid[..., index])
        maps.append(dict(channel=int(index), mean=float(grid[..., index].mean()), min=low, max=high, png=encoded))
    cls = tokens[0]
    similarity = float(np.dot(cls, final_cls) / (np.linalg.norm(cls) * np.linalg.norm(final_cls) + 1e-12))
    step = dict(layer=layer, block=block, kind='spatial', shape=[side, side, int(grid.shape[-1])], tokens=int(tokens.shape[0]),
                stats=statistics(tokens), maps=maps, top=[], cls_similarity=similarity)
    if attention is not None:
        encoded, low, high = png(np, attention.reshape(side, side))
        step['attention'] = dict(png=encoded, min=low, max=high)
    return step


def vector_step(np: Any, layer: str, block: str, values: Any, output: bool = False) -> dict[str, Any]:
    order = np.argsort(np.abs(values))[::-1][:CHANNELS]
    step = dict(layer=layer, block=block, kind='output' if output else 'vector', shape=list(values.shape), stats=statistics(values),
                maps=[], top=[dict(index=int(i), value=float(values[i])) for i in order])
    if not output:
        step['histogram'] = histogram(np, values)
    return step


def forward(runtime: Any, sample: dict[str, Any]) -> tuple[list[dict[str, Any]], float]:
    """(steps, parasitized score) of one cell, with the EVALUATE's own model and transform."""
    import numpy as np
    import torch

    zero_shot = hasattr(runtime, 'classifier')
    visual = runtime.classifier.model.visual if zero_shot else runtime.net.visual
    trunk = visual.trunk
    blocks = list(trunk.blocks)
    prefix = int(getattr(trunk, 'num_prefix_tokens', 1))
    captured: dict[str, Any] = {}
    hooks = [blocks[0].register_forward_pre_hook(lambda _m, args: captured.__setitem__('embedding', args[0].detach()))]
    fused = []
    for index, block in enumerate(blocks):
        hooks.append(block.register_forward_hook(lambda _m, _i, out, i=index: captured.__setitem__(f'vit{i}', out.detach())))
        attention = block.attn
        fused.append(getattr(attention, 'fused_attn', False))
        attention.fused_attn = False  # explicit softmax(QKᵀ) so the weights exist; same math, read once
        hooks.append(attention.attn_drop.register_forward_hook(lambda _m, _i, out, i=index: captured.__setitem__(f'attn{i}', out.detach())))
    try:
        images = torch.from_numpy(runtime.images([sample])).to(runtime.device)
        with torch.inference_mode():
            if zero_shot:
                model = runtime.classifier.model
                embedded = model.encode_image(images, normalize=True)
                probabilities = (model.logit_scale.exp() * embedded @ runtime.classifier.text_features.T).softmax(dim=-1)[0]
            else:
                embedded = runtime.net.embed(images)
                score = torch.sigmoid(runtime.net.head(embedded)).reshape(-1)[0]
                probabilities = torch.stack([1 - score, score])
    finally:
        for hook in hooks:
            hook.remove()
        for block, value in zip(blocks, fused):
            block.attn.fused_attn = value
    as_array = lambda tensor: tensor.float().cpu().numpy()
    last = as_array(captured[f'vit{len(blocks) - 1}'])[0]
    final_cls = last[0]
    steps = [token_step(np, 'patch_embed', 'embedding', as_array(captured['embedding'])[0], prefix, None, final_cls)]
    for index in range(len(blocks)):
        weights = as_array(captured[f'attn{index}'])[0]  # heads × tokens × tokens
        cls_attention = weights[:, 0, prefix:].mean(axis=0)
        steps.append(token_step(np, f'blocks.{index}', f'vit{index}', as_array(captured[f'vit{index}'])[0], prefix, cls_attention, final_cls))
    steps.append(vector_step(np, 'projection', 'projection', as_array(embedded)[0]))
    values = as_array(probabilities)
    score = float(values[1])
    output = dict(layer='output', block='output', kind='output', shape=[len(values)], stats=statistics(values), maps=[],
                  top=[dict(index=1, value=score), dict(index=0, value=float(values[0]))])
    steps.append(output)
    return steps, score


def compute(value: dict[str, Any], sample: dict[str, Any], persisted: dict[str, Any]) -> dict[str, Any]:
    import numpy as np  # noqa: F401 -- loaded with the runtime's environment
    from PIL import Image

    from src.malaria_dl.assessment.runtime import runtime_for, verified_sample_bytes

    runtime = runtime_for(value)
    steps, score = forward(runtime, sample)
    clipped = min(max(score, 1e-12), 1 - 1e-12)
    with Image.open(io.BytesIO(verified_sample_bytes(value, runtime.dataset_root, sample))) as image:
        stream = io.BytesIO()
        image.convert('RGB').save(stream, format='PNG')
    expected = persisted.get('raw_score')
    return dict(score=score, logit=math.log(clipped / (1 - clipped)), persisted_score=expected, label=persisted.get('label'),
                predicted=persisted.get('predicted'), threshold=persisted.get('threshold'),
                consistent=expected is not None and abs(score - expected) <= TOLERANCE, selection=SELECTION, steps=steps,
                input_image=base64.b64encode(stream.getvalue()).decode())


def main() -> None:
    job = json.loads(sys.stdin.readline())
    result = compute(job['value'], job['sample'], job['persisted'])
    write_atomic(Path(job['path']), {**job['identity'], **result, 'version': VERSION,
                                     'created_at': datetime.now(timezone.utc).isoformat()})


if __name__ == '__main__':
    main()
