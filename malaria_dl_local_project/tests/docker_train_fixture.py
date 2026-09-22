"""Deterministic scientific doubles around the real TRAIN control flow (no TF fit)."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace


def install_science(monkeypatch, *, fit_error=None):
    import tensorflow as tf
    from src import metrics
    from src.malaria_dl.data import loaders
    from src.malaria_dl.models import adapters
    from src.malaria_dl.training import checkpoint_policy

    trace = []
    class Callback:
        def __init__(self, *args, **kwargs):
            self.monitor = kwargs.get('monitor')
    class EarlyStopping(Callback):
        stopped_epoch = 0
        best_epoch = 1
    class Model:
        optimizer = SimpleNamespace(learning_rate=0.1)
        def save(self, path):
            trace.append(('save', str(path)))
            Path(path).write_bytes(b'deterministic synthetic checkpoint')
        def fit(self, data, validation_data, epochs, callbacks):
            trace.append(('fit', data.role, validation_data.role))
            assert data.role == 'train' and validation_data.role == 'val'
            if fit_error is not None:
                raise fit_error
            for epoch in range(2):
                for cb in callbacks:
                    if hasattr(cb, 'on_epoch_end'):
                        cb.on_epoch_end(epoch, {
                            'loss': 0.4 - epoch * 0.1, 'val_loss': 0.3 - epoch * 0.1,
                            'val_f2_parasitized': 0.8 + epoch * 0.1,
                            'val_recall_parasitized': 1.0, 'val_specificity': 1.0,
                            'val_auc': 1.0, 'val_prediction_collapse': False,
                        })
            return SimpleNamespace(epoch=[0, 1])
    model = Model()
    monkeypatch.setattr(tf.keras.callbacks, 'Callback', Callback)
    monkeypatch.setattr(tf.keras.callbacks, 'EarlyStopping', EarlyStopping)
    monkeypatch.setattr(tf.keras.callbacks, 'ReduceLROnPlateau', Callback)
    monkeypatch.setattr(checkpoint_policy, 'ClinicalValidationMetricsCallback', Callback)
    monkeypatch.setattr(tf.keras.models, 'load_model', lambda *a, **k: model)
    monkeypatch.setattr(adapters, 'compile_phase', lambda a, b, r, phase: {'phase': phase, 'synthetic': True})
    def dataset(path, *args):
        role = Path(path).name
        assert role in ('train', 'val')
        trace.append(('dataset', role))
        return SimpleNamespace(role=role, file_paths=[str(path / 'a'), str(path / 'b')])
    monkeypatch.setattr(loaders, 'make_image_dataset_from_directory', dataset)
    monkeypatch.setattr(loaders, 'preprocess_physical_dataset', lambda ds, *a, **k: ds)
    def collect(model, ds, **kwargs):
        assert ds.role == 'val'
        trace.append(('predict', 'val'))
        return [0, 1], [0, 1], [0.1, 0.9]
    monkeypatch.setattr(metrics, 'collect_predictions', collect)
    descriptor = SimpleNamespace(create_adapter=lambda: SimpleNamespace(build=lambda config: SimpleNamespace(model=model)))
    return descriptor, trace


class MemoryRepository:
    def __init__(self, session, trace, fail_kind=None, finish_error=None):
        self.session_data = session
        self.trace = trace
        self.rows = []
        self.fail_kind = fail_kind
        self.finish_error = finish_error
    def put(self, run, owner, kind, phase, key, payload):
        if kind == self.fail_kind:
            raise RuntimeError('LEGACY_WRITE_FAILED')
        self.rows.append(dict(kind=kind, phase=phase, record_key=str(key), payload=deepcopy(payload)))
        self.trace.append(('legacy', kind))
    def records(self, run):
        self.trace.append(('hash_read',))
        return sorted(deepcopy(self.rows), key=lambda r: (r['kind'], r['phase'], r['record_key']))
    def finish(self, run, owner, state, evidence):
        self.trace.append(('finish', state))
        if self.finish_error:
            raise self.finish_error
        self.session_data.update(state=state, completion=deepcopy(evidence))
