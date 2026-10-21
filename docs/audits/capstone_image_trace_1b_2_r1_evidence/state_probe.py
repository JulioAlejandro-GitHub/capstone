"""Separate initial/final state capture, including post-EarlyStopping restoration."""
import json
from pathlib import Path
import runpy
import sys
from unittest.mock import patch
import numpy as np
from reference import Reference

ROOT = Path(__file__).resolve().parent
arch, arm = sys.argv[1:]
OUT = ROOT/f'{arch}_state_{arm}'
install = Reference.install


def instrument(self, model):
    make = model._make_function
    def device_make(step):
        function = make(step)
        def execute(iterator):
            result = function(iterator)
            devices = {key: value.device for key,value in result.items()
                       if key == '_reference_scores' or key.startswith('_reference_gradient_')}
            if devices:
                with (OUT/'step_devices.jsonl').open('a') as stream:
                    stream.write(json.dumps(dict(phase=self.phase, devices=devices))+'\n')
            return result
        return execute
    model._make_function = device_make
    install(self, model)
    def save(stage):
        arrays = {f'weight_{i:04d}': v.numpy() for i, v in enumerate(model.weights)}
        arrays.update({f'optimizer_{i:04d}': v.numpy() for i, v in enumerate(model.optimizer.variables)})
        np.savez_compressed(OUT/f'state_{self.phase}_{stage}.npz', **arrays)
    save('initial')
    fit = model.fit
    def capture(*args, **kwargs):
        result = fit(*args, **kwargs)
        save('after_fit_and_restore')
        for callback in kwargs.get('callbacks', []):
            if getattr(callback, 'best_weights', None) is not None:
                np.savez_compressed(OUT/f'state_{self.phase}_early_stopping_best.npz',
                    **{f'weight_{i:04d}': v for i,v in enumerate(callback.best_weights)})
                (OUT/f'restore_{self.phase}.json').write_text(json.dumps(dict(
                    best_epoch=int(callback.best_epoch), stopped_epoch=int(callback.stopped_epoch),
                    restore_best_weights=callback.restore_best_weights), indent=2))
        return result
    model.fit = capture


sys.argv = ['experiment.py', str(OUT), '--deterministic', '--reference', '--architecture', arch]
if arm == 'b':
    sys.argv += ['--observer']
if arch != 'custom_cnn':
    sys.argv += ['--two-phases']
with patch.object(Reference, 'install', instrument):
    runpy.run_path(str(ROOT/'experiment.py'), run_name='__main__')
