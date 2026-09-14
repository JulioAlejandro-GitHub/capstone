"""Runtime provenance stays content-addressed when the image omits git."""
from types import SimpleNamespace

from src.malaria_dl.campaigns import service


def test_missing_git_keeps_same_source_identity(monkeypatch):
    monkeypatch.setattr(service.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0, stdout='a' * 40))
    available = service.planning_environment()
    def missing(*args, **kwargs):
        raise FileNotFoundError('git')
    monkeypatch.setattr(service.subprocess, 'run', missing)
    absent = service.planning_environment()
    assert available.pop('git_commit') == 'a' * 40
    assert absent.pop('git_commit') is None
    assert absent == available
    assert len(absent['source_sha256']) == 64


def test_integral_jsonb_learning_rate_builds_without_mutating_config():
    from copy import deepcopy
    from src.malaria_dl.models.optimizers import build_optimizer, optimizer_config
    config = optimizer_config('adadelta', {'learning_rate': 1})
    original = deepcopy(config)
    optimizer = build_optimizer('adadelta', config=config)
    assert float(optimizer.learning_rate.numpy()) == 1.0
    assert config == original
    assert type(config['learning_rate']) is int
