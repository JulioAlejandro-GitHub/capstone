"""Structure of the registered BiomedCLIP base: parameters and output shape of each block.

Runs in its own process (PyTorch never enters the API). The base is resolved and verified by
SHA-256 with ``base_files`` and built exactly as TRAIN builds it; one forward pass of a zero image
records the shapes. No trained weight is read: the structure is the same for every TRAIN of the base.
For every ``fine_tune_layers`` value it also records the trainable set TRAIN would declare
(names hash, tensor count, elements), so each TRAIN's recorded set can be checked against it.
"""
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = 'vit_structure_v1'
EMBEDDING = ('visual.trunk.patch_embed.', 'visual.trunk.cls_token', 'visual.trunk.pos_embed', 'visual.trunk.reg_token')
PROJECTION = ('visual.trunk.norm.', 'visual.trunk.fc_norm.', 'visual.head.')


def group_of(name: str) -> str:
    if name.startswith('head.'):
        return 'output'
    if name.startswith('visual.trunk.blocks.'):
        return f"vit{name.split('.')[3]}"
    if name.startswith(EMBEDDING):
        return 'embedding'
    if name.startswith(PROJECTION):
        return 'projection'
    return 'other'


def compute(base: dict[str, Any], input_size: int) -> dict[str, Any]:
    import torch

    from src.malaria_dl.campaigns.contracts import digest
    from src.malaria_dl.models.biomedclip_training import VIT_BLOCKS, base_files, build, trainable_names

    files = base_files(base)
    model, _ = build(files)
    model.eval()
    blocks: dict[str, dict[str, Any]] = {}
    for name, parameter in model.named_parameters():
        entry = blocks.setdefault(group_of(name), {'parameters': 0, 'tensors': 0, 'output_shape': None})
        entry['parameters'] += parameter.numel()
        entry['tensors'] += 1
    trunk = model.visual.trunk
    shapes: dict[str, list[int]] = {}
    hooks = [trunk.patch_embed.register_forward_hook(lambda _m, _i, out: shapes.__setitem__('patches', list(out.shape)))]
    hooks += [block.register_forward_hook(lambda _m, _i, out, i=i: shapes.__setitem__(f'vit{i}', list(out.shape)))
              for i, block in enumerate(trunk.blocks)]
    with torch.inference_mode():
        image = torch.zeros(1, 3, input_size, input_size)
        embedded = model.embed(image)
        logits = model.head(embedded)
    for hook in hooks:
        hook.remove()
    for index in range(len(trunk.blocks)):
        blocks.setdefault(f'vit{index}', {'parameters': 0, 'tensors': 0})['output_shape'] = shapes.get(f'vit{index}')
    # Tokens that enter the encoder: patches plus the class (and register) tokens.
    blocks.setdefault('embedding', {'parameters': 0, 'tensors': 0})['output_shape'] = shapes.get('vit0')
    blocks['embedding']['patches'] = shapes.get('patches')
    blocks.setdefault('projection', {'parameters': 0, 'tensors': 0})['output_shape'] = list(embedded.shape)
    blocks.setdefault('output', {'parameters': 0, 'tensors': 0})['output_shape'] = list(logits.shape)
    trainable = {}
    for layers in range(VIT_BLOCKS + 1):
        names = trainable_names(model, layers)
        parameters = dict(model.named_parameters())
        trainable[str(layers)] = {'names_sha256': digest(names), 'count': len(names), 'elements': sum(parameters[n].numel() for n in names)}
    patch = getattr(trunk.patch_embed, 'patch_size', None)
    return dict(version=VERSION, base={'sha256': files['checkpoint']['sha256'], 'bytes': files['checkpoint']['bytes']},
                input_size=input_size, vit_blocks=len(trunk.blocks), patch_size=list(patch) if patch else None,
                width=int(trunk.embed_dim), total_parameters=sum(p.numel() for p in model.parameters()),
                blocks=blocks, trainable=trainable, created_at=datetime.now(timezone.utc).isoformat())


def write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=path.parent, suffix='.tmp', delete=False) as stream:
        json.dump(payload, stream, separators=(',', ':'))
    os.replace(stream.name, path)


def main() -> None:
    job = json.loads(sys.stdin.readline())
    write_atomic(Path(job['path']), compute(job['base'], int(job['input_size'])))


if __name__ == '__main__':
    main()
