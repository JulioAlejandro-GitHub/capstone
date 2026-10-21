"""Isolated synthetic Metal baseline; no database, network, or production edits.

Run from repository root using malaria_dl_local_project/.venv-metal/bin/python.
Each invocation creates a NEW output directory and calls the real TRAIN engine.
"""
import argparse
import hashlib
import importlib.metadata
import json
import platform
import resource
from pathlib import Path
import subprocess
import sys
import time
import traceback
from unittest.mock import patch
from contextlib import ExitStack

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'malaria_dl_local_project'))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--architecture', choices=['custom_cnn', 'vgg16', 'densenet121'], default='custom_cnn')
    parser.add_argument('--deterministic', action='store_true')
    parser.add_argument('--observer', action='store_true')
    parser.add_argument('--reference', action='store_true')
    parser.add_argument('--interrupt', choices=['before', 'during', 'after'])
    parser.add_argument('--two-phases', action='store_true')
    parser.add_argument('--duplicate-bytes', action='store_true')
    parser.add_argument('--unresolved', action='store_true')
    parser.add_argument('--duration-epochs', type=int, default=0)
    parser.add_argument('--no-augment', action='store_true')
    parser.add_argument('--no-shuffle', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    import numpy as np
    import tensorflow as tf
    environment = dict(python=sys.version, executable=sys.executable,
                       platform=platform.platform(), execution_mode='local_python',
                       chip=subprocess.run(['/usr/sbin/sysctl', '-n', 'machdep.cpu.brand_string'], capture_output=True, text=True).stdout.strip(),
                       packages={p: importlib.metadata.version(p) for p in ['tensorflow', 'keras', 'numpy', 'tensorflow-metal']},
                       gpus=[str(d) for d in tf.config.list_physical_devices('GPU')])
    write(out / 'environment.json', environment)
    if not environment['gpus']:
        raise RuntimeError('METAL_UNAVAILABLE: no CPU fallback')
    tf.config.set_soft_device_placement(False)
    with tf.device('/GPU:0'):
        probe = tf.matmul(tf.ones((2, 2)), tf.ones((2, 2)))
        environment['gpu_probe'] = dict(device=probe.device, result=probe.numpy().tolist())
    write(out / 'environment.json', environment)
    from src.malaria_dl.models import registry
    from src.malaria_dl.models.configuration import resolve_config
    from src.malaria_dl.execution.train import train
    from src.config import CLASS_NAMES
    # Only the catalogue lookup is isolated; no SQL or governed clinical dataset.
    with patch.object(registry, 'registered_models', return_value=tuple(registry.MODEL_REGISTRY)):
        config = resolve_config(args.architecture, {'model': {'input_shape': [32, 32, 3], 'weights': 'none'},
            'execution': {'batch_size': 8, 'max_epochs': args.duration_epochs or 3, 'fine_tune_epochs': 3 if args.two_phases else 0,
                          'seed': 42, 'deterministic_ops': args.deterministic,
                          'no_augment': args.no_augment, 'early_stopping': not bool(args.duration_epochs),
                          'early_stopping_patience': 1, 'early_stopping_min_delta': 1.0,
                          'restore_best_weights': True, 'evaluate_best_on_test': False}})
    write(out / 'configuration.json', config)
    fixture = out / 'fixture'
    manifest = []
    rng = np.random.default_rng(20261020)
    for split, count in [('train', 37), ('val', 19)]:
        for index in range(count):
            relative = Path(split) / CLASS_NAMES[index % 2] / f'{index:03d}.png'
            path = fixture / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            pixels = rng.integers(0, 256, (32, 32, 3), dtype=np.uint8)
            encoded = tf.io.encode_png(pixels).numpy()
            if args.duplicate_bytes and split == 'train' and index == 2:
                encoded = (fixture / manifest[0]['path']).read_bytes()
            path.write_bytes(encoded)
            manifest.append(dict(path=relative.as_posix(), label=index % 2, sha256=hashlib.sha256(encoded).hexdigest()))
    if args.unresolved:
        manifest = manifest[1:]
    write(out / 'manifest.json', manifest)

    class AuditRepository:
        def __init__(self):
            self.rows = []
        def put(self, run, owner, kind, phase, key, payload):
            self.rows.append(dict(kind=kind, phase=phase, key=str(key), payload=payload))
            write(out / 'records.json', self.rows)
        def records(self, run):
            return self.rows
        def finish(self, run, owner, state, payload):
            write(out / 'completion.json', dict(state=state, payload=payload))

    session = dict(run_id='00000000-0000-4000-8000-000000000001', owner='synthetic-metal-audit',
                   configuration=config, artifact_root=str(out / 'checkpoints'),
                   dataset={'dataset_root': str(fixture)})
    observer = None
    reference_transport = None
    timings = []
    start = time.perf_counter()
    try:
        with ExitStack() as stack:
            from src.malaria_dl.models import adapters
            original_compile = adapters.compile_phase
            if args.observer or args.reference:
                from observer import Observer
                from src.malaria_dl.data import loaders
                from src.malaria_dl.models import adapters
                observer = Observer(fixture, manifest, out)
                observer.architecture = args.architecture
                observer.patch_loading(stack)
                stack.enter_context(patch.object(loaders, 'preprocess_physical_dataset', observer.preprocess))
                if not args.observer:
                    reference_transport, observer = observer, None
            if args.no_shuffle:
                from src.malaria_dl.data import loaders
                original_loader = loaders.make_image_dataset_from_directory
                def no_shuffle(*a, **kw):
                    kw['shuffle'] = False
                    return original_loader(*a, **kw)
                stack.enter_context(patch.object(loaders, 'make_image_dataset_from_directory', no_shuffle))
            original_hooks = {}
            def compile_measured(*a, **kw):
                runtime = original_compile(*a, **kw)
                model = a[1].model
                if id(model) not in original_hooks:
                    original_hooks[id(model)] = {key: getattr(model, key) for key in ['train_step', 'test_step', '_make_function', 'compute_metrics', 'fit']}
                else:
                    for key,value in original_hooks[id(model)].items(): setattr(model,key,value)
                if args.interrupt == 'during':
                    original_step = model.train_step
                    def interrupted_step(data):
                        result = original_step(data)
                        def fail():
                            raise RuntimeError('INJECTED_DURING_STEP: completion unknown')
                        with tf.control_dependencies(list(result.values()) + [tf.identity(model.optimizer.iterations)]):
                            failure = tf.py_function(fail, [], tf.int64)
                        with tf.control_dependencies([failure]):
                            return {k: tf.identity(v) for k,v in result.items()}
                    model.train_step = interrupted_step
                if observer:
                    observer.phase = a[3]
                    observer.install(model)
                if reference_transport:
                    reference_transport.install(model, record=False)
                if args.reference:
                    from reference import Reference
                    Reference(out, phase=a[3]).install(model)
                make = model._make_function
                def measured_make(step):
                    fn = make(step)
                    purpose = 'weight_optimization' if step == model.train_step else 'keras_validation'
                    def measured(iterator):
                        started = time.perf_counter()
                        if args.interrupt == 'before' and purpose == 'weight_optimization':
                            raise RuntimeError('INJECTED_BEFORE_STEP')
                        result = fn(iterator)
                        if args.interrupt == 'after' and purpose == 'weight_optimization':
                            raise RuntimeError('INJECTED_AFTER_RETURN_BEFORE_CALLBACKS')
                        for value in result.values():
                            if hasattr(value, 'numpy'): value.numpy()
                        timings.append(dict(purpose=purpose, seconds=time.perf_counter()-started,
                                            rss_peak_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
                        return result
                    return measured
                model._make_function = measured_make
                return runtime
            stack.enter_context(patch.object(adapters, 'compile_phase', compile_measured))
            train(AuditRepository(), session, registry.MODEL_REGISTRY[args.architecture])
            if observer: observer.save()
    except BaseException:
        if observer: observer.save()
        write(out / 'outcome.json', dict(status='ERROR', elapsed=time.perf_counter()-start, error=traceback.format_exc()))
        raise
    write(out / 'timings.json', timings)
    write(out / 'outcome.json', dict(status='COMPLETED', elapsed=time.perf_counter()-start, rss_peak_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))


if __name__ == '__main__':
    main()
