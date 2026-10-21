"""Symmetric diagnostic capture from the existing forward/backward, no extra call."""
import numpy as np


class Reference:
    def __init__(self, output, phase):
        self.output = output
        self.phase = phase
        self.batch = 0

    def install(self, model):
        captured = {}
        metrics = model.compute_metrics
        apply = model.optimizer.apply_gradients
        def compute_metrics(x, y, y_pred, sample_weight=None):
            captured['scores'] = y_pred
            return metrics(x,y,y_pred,sample_weight=sample_weight)
        def apply_gradients(grads_and_vars):
            pairs = list(grads_and_vars)
            captured['gradients'] = [g for g,v in pairs if g is not None]
            return apply(pairs)
        model.compute_metrics = compute_metrics
        model.optimizer.apply_gradients = apply_gradients
        for method in ['train_step','test_step']:
            original = getattr(model,method)
            def step(data, original=original, method=method):
                result = original(data)
                result['_reference_x'] = data[0]['image'] if isinstance(data[0], dict) else data[0]
                if isinstance(data[0], dict): result['_reference_tokens'] = data[0]['token']
                result['_reference_y'] = data[1]
                result['_reference_scores'] = captured['scores']
                if method == 'train_step':
                    for i,g in enumerate(captured['gradients']): result[f'_reference_gradient_{i}'] = g
                return result
            setattr(model,method,step)
        make = model._make_function
        def make_reference(step):
            fn = make(step)
            purpose = 'train' if step == model.train_step else 'val'
            def execute(iterator):
                result = fn(iterator)
                arrays = {k.removeprefix('_reference_'): result.pop(k).numpy()
                          for k in list(result) if k.startswith('_reference_')}
                if arrays:
                    np.savez_compressed(self.output/f'reference_{self.phase}_{self.batch:04d}_{purpose}.npz', **arrays)
                    self.batch += 1
                return result
            return execute
        model._make_function = make_reference
