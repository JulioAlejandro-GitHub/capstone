"""The authorized Docker boundary expands; Local and scientific policy stay separate."""
import ast
import hashlib
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'src/malaria_dl'


def imports(path):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom):
            yield (node.module or '') + '.' + '.'.join(a.name for a in node.names)
        elif isinstance(node, ast.Import):
            yield from (a.name for a in node.names)


def test_train_only_knows_emitter_and_contracts_at_new_boundary():
    dependencies = list(imports(SOURCE/'execution/train.py'))
    assert any('emitter.RunEventEmitter' in d for d in dependencies)
    for d in dependencies:
        assert not any(name in d for name in ('PostgresResultRepository', 'ResultService',
                                             'DockerRunReporter', 'HttpRunReporter', 'fastapi', 'composition'))
    tree = ast.parse((SOURCE/'execution/train.py').read_text())
    train = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'train')
    assert [a.arg for a in train.args.kwonlyargs] == ['event_emitter']
    assert isinstance(train.args.kw_defaults[0], ast.Constant) and train.args.kw_defaults[0].value is None
    assert not any(isinstance(n, ast.Global) for n in ast.walk(train))


def test_local_keeps_reports_with_shared_emitter():
    for name in ('worker', 'agent', 'transport'):
        for dependency in imports(SOURCE/f'local_execution/{name}.py'):
            assert not any(s in dependency for s in ('RunEventEmitter', 'HttpRunReporter', 'DockerRunReporter', 'composition'))
    tree = ast.parse((SOURCE/'local_execution/worker.py').read_text())
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'train']
    assert len(calls) == 1 and len(calls[0].args) == 3 and [k.arg for k in calls[0].keywords] == ['event_emitter']
    assert isinstance(calls[0].args[0], ast.Call) and calls[0].args[0].func.id == 'Reports'


def test_frozen_baseline_integrity():
    # Exact committed E10.6 source through TRAIN; no standalone CLI copied.
    path = Path(__file__).parent/'fixtures/e10_6_train.py'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == '12e1ddb68653beaf1c4dc335271ac5cb0a8f51c675051d21c2b98db1830bab0b'
