"""Offline OpenCLIP zero-shot adapter; scores are relative similarities, not calibration."""
from __future__ import annotations

import copy
import hashlib
import io
import json
import tempfile
from pathlib import Path
from threading import RLock

from ..pretrained.registration import verified_file

_LOCK = RLock()


def _dependencies(profile):
    items = profile['dependencies']
    files = {item['role']: verified_file(item) for item in items}
    if len(files) != len(items):
        raise ValueError('Duplicate OpenCLIP dependency roles')
    required = {'model_config', 'text_config', 'tokenizer_config', 'vocabulary'}
    if not required <= files.keys():
        raise ValueError('Missing OpenCLIP dependencies')
    text_paths = [Path(files[role]['path']).parent for role in required - {'model_config'}]
    if len(set(text_paths)) != 1:
        raise ValueError('Text dependencies must form one registered tokenizer directory')
    registered = {Path(files[role]['path']).name for role in required - {'model_config'}}
    if {path.name for path in text_paths[0].iterdir() if path.is_file()} != registered:
        raise ValueError('Unregistered text dependency in tokenizer directory')
    return files


def image_transform(profile):
    from open_clip.transform import image_transform_v2, PreprocessCfg
    files = _dependencies(profile)
    config = json.loads(Path(files['model_config']['path']).read_text())
    return image_transform_v2(PreprocessCfg(**{'size': config['model_cfg']['vision_cfg']['image_size'], **config['preprocess_cfg']}), is_train=False)


def transform_bytes(payload, profile):
    from PIL import Image
    with Image.open(io.BytesIO(payload)) as image:
        return image_transform(profile)(image.convert('RGB')).numpy()


class OpenCLIPClassifier:
    """Capstone predict interface over the original image/text encoders."""
    def __init__(self, checkpoint, profile, expected_sha256):
        import open_clip
        import torch
        files = _dependencies(profile)
        config = json.loads(Path(files['model_config']['path']).read_text())
        cfg = copy.deepcopy(config['model_cfg'])
        if cfg['vision_cfg'].get('timm_model_pretrained', False):
            raise ValueError('External image weight download is forbidden during checkpoint load')
        text_dir = str(Path(files['text_config']['path']).parent)
        cfg['text_cfg'].update(hf_model_name=text_dir, hf_tokenizer_name=text_dir, hf_model_pretrained=False)
        if profile['class_order'] != ['uninfected', 'parasitized'] or len(profile['prompts']) != 2:
            raise ValueError('OpenCLIP requires the canonical two-class prompt order')
        name = 'capstone_' + hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:16]
        with Path(checkpoint).open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected_sha256:
                raise ValueError('Checkpoint SHA mismatch before load')
        with _LOCK, tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / (name + '.json')
            path.write_text(json.dumps(cfg))
            open_clip.add_model_config(path)
            self.model, _, self.transform = open_clip.create_model_and_transforms(
                name, pretrained=str(checkpoint), pretrained_text=False, device='cpu', precision='fp32',
                **{('force_image_size' if key == 'size' else 'image_' + key): value
                   for key, value in config['preprocess_cfg'].items()})
            tokenizer = open_clip.get_tokenizer(name)
        with Path(checkpoint).open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected_sha256:
                raise ValueError('Checkpoint changed during load')
        self.model.eval()
        with torch.inference_mode():
            self.text_features = self.model.encode_text(tokenizer(profile['prompts']), normalize=True)
        size = config['preprocess_cfg'].get('size', cfg['vision_cfg']['image_size'])
        height, width = (size, size) if isinstance(size, int) else size
        self.input_shape = (None, height, width, 3)
        self.device = 'cpu'

    def predict(self, batch, verbose=0):
        import numpy as np
        import torch
        values = np.asarray(batch, dtype=np.float32)
        # The cellular preprocessor supplies original-transform NCHW. The technical
        # smoke test supplies NHWC zeros and is transformed by this same adapter.
        if values.ndim != 4:
            raise ValueError('Expected a batch of cell images')
        if values.shape[-1] == 3:
            from PIL import Image
            tensors = torch.stack([self.transform(Image.fromarray(np.uint8(value))) for value in values])
        else:
            tensors = torch.from_numpy(values)
        with torch.inference_mode():
            features = self.model.encode_image(tensors, normalize=True)
            scores = (self.model.logit_scale.exp() * features @ self.text_features.T).softmax(dim=-1)
        result = scores.cpu().numpy()
        if result.shape != (len(values), 2) or not np.isfinite(result).all():
            raise ValueError('Invalid OpenCLIP similarities')
        return result
