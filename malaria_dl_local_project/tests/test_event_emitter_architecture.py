"""Pure producer and separate evidence integrity mechanisms."""
import ast
from pathlib import Path
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / 'src/malaria_dl'


def test_emitter_import_allowlist_and_no_dynamic_imports():
    for node in ast.walk(ast.parse((SOURCE / 'execution/emitter.py').read_text())):
        assert not isinstance(node, ast.Import)
        if isinstance(node, ast.ImportFrom):
            assert (node.level, node.module) in {
                (0, 'dataclasses'), (0, 'datetime'), (0, 'threading'), (0, 'uuid'), (1, 'contracts'), (1, 'journal')}
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {'__import__', 'exec', 'eval', 'open'}


def test_emitter_works_without_infrastructure_installed():
    script = '''
import sys
sys.path.insert(0, sys.argv[1])
import importlib.abc
parents = {'src', 'src.malaria_dl', 'src.malaria_dl.execution'}
allowed = ('src.malaria_dl.execution.journal', 'src.malaria_dl.execution.emitter', 'src.malaria_dl.execution.contracts')
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in parents or any(fullname == p or fullname.startswith(p+'.') for p in allowed): return None
        if fullname.split('.')[0] in sys.stdlib_module_names: return None
        raise AssertionError('Infrastructure: ' + fullname)
sys.meta_path.insert(0, Guard())
from uuid import uuid4
from src.malaria_dl.execution.emitter import RunEventEmitter
from src.malaria_dl.execution.contracts import RunReporter, RunEventType
class Reporter(RunReporter):
    def report(self, event): pass
stream = RunEventEmitter(Reporter(), run_id=uuid4())
assert stream.emit(RunEventType.TRAINING_COMPLETED, {}).sequence == 1
assert stream.closed
'''
    result = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', script, str(PROJECT)],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr


def test_hash_service_and_reporters_keep_separate_responsibilities():
    for path in [*(SOURCE / 'execution/reporters').glob('*.py'), *(SOURCE / 'results').glob('*.py')]:
        assert 'records_hash' not in path.read_text()
    for path in [SOURCE / 'campaigns/contracts.py', SOURCE / 'execution/artifacts.py']:
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                assert 'reporter' not in (node.module or '') and 'emitter' not in (node.module or '')
    for name in ('local_execution/worker.py',
                 'local_execution/agent.py', 'local_execution/transport.py'):
        for node in ast.walk(ast.parse((SOURCE / name).read_text())):
            if isinstance(node, ast.ImportFrom): assert 'emitter' not in (node.module or '')
