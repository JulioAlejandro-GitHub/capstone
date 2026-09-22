"""Keep the reporter light and concrete persistence at the composition edge."""
import ast
from pathlib import Path
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / 'src/malaria_dl'


def test_reporter_imports_only_contracts_and_application():
    for path in (SOURCE / 'execution/reporters/docker.py', SOURCE / 'execution/reporters/__init__.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            assert not isinstance(node, ast.Import)
            if isinstance(node, ast.ImportFrom):
                assert (node.level, node.module) in {(2, 'contracts'), (3, 'results')}
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {'__import__', 'eval', 'exec', 'RunEvent', 'uuid4'}
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert not any(name in node.value.lower() for name in ('train_execution_records', 'runs.parameters', 'select ', 'insert '))


def test_concrete_adapter_is_composed_only_at_external_edge():
    for directory in ('results', 'execution/contracts'):
        for path in (SOURCE / directory).rglob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom):
                    assert all(alias.name not in {'DockerRunReporter', 'PostgresResultRepository'} for alias in node.names)
                    assert not any(word in (node.module or '') for word in ('reporters', 'composition', 'persistence'))
    for name in ('train.py', 'campaign.py'):
        tree = ast.parse((SOURCE / 'execution' / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not any(word in (node.module or '') for word in ('composition', 'reporters'))


def test_reporter_import_without_infrastructure_installed():
    script = r'''
import sys
sys.path.insert(0, sys.argv[1])
import importlib.abc
parents = {'src', 'src.malaria_dl', 'src.malaria_dl.execution', 'src.malaria_dl.evaluation'}
prefixes = ('src.malaria_dl.execution.contracts', 'src.malaria_dl.execution.reporters', 'src.malaria_dl.results', 'src.malaria_dl.evaluation.binary_counts')
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in parents or any(fullname == p or fullname.startswith(p + '.') for p in prefixes):
            return None
        if fullname.split('.')[0] in sys.stdlib_module_names:
            return None
        raise AssertionError('Infrastructure import: ' + fullname)
sys.meta_path.insert(0, Guard())
from src.malaria_dl.execution.reporters.docker import DockerRunReporter
from src.malaria_dl.execution.contracts import RunReporter
assert issubclass(DockerRunReporter, RunReporter)
'''
    result = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', script, str(PROJECT)],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
