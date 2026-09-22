"""AST and isolated imports enforce the results application boundary."""
import ast
from pathlib import Path
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]
RESULTS = PROJECT / "src/malaria_dl/results"


def test_results_import_only_stdlib_siblings_and_approved_contracts():
    allowed = {"abc", "contextlib", "dataclasses", "enum", "json", "uuid"}
    siblings = {path.stem for path in RESULTS.glob("*.py")}
    for path in RESULTS.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
            if isinstance(node, ast.Import):
                assert all(alias.name in allowed for alias in node.names), (path, node.lineno)
            elif isinstance(node, ast.ImportFrom):
                assert (
                    (node.level == 0 and node.module in allowed)
                    or (node.level == 1 and node.module in siblings)
                    or (node.level == 2 and node.module == "execution.contracts")
                ), (path, node.lineno)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"__import__", "exec", "eval"}, (path, node.lineno)


def test_service_has_no_runtime_authorization_branch():
    tree = ast.parse((RESULTS / "service.py").read_text())
    assert not any(isinstance(node, ast.Attribute) and node.attr == "execution_mode"
                   for node in ast.walk(tree))


def test_results_import_without_site_packages_or_infrastructure():
    script = r'''
import sys
sys.path.insert(0, sys.argv[1])
import importlib.abc
parents = {"src", "src.malaria_dl", "src.malaria_dl.execution"}
prefixes = ("src.malaria_dl.results", "src.malaria_dl.execution.contracts")
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in parents or any(fullname == p or fullname.startswith(p + ".") for p in prefixes):
            return None
        if fullname.split(".")[0] in sys.stdlib_module_names:
            return None
        raise AssertionError("Infrastructure import: " + fullname)
sys.meta_path.insert(0, Guard())
from src.malaria_dl.results import ResultService, ResultRepository, EventAcceptance, EventAcceptanceStatus
from src.malaria_dl.results.errors import RunIdentityMismatch
from src.malaria_dl.execution.contracts import ExecutionContext, ExecutionMode, RunEvent, RunEventType
from datetime import datetime, timezone
from uuid import UUID
context = ExecutionContext(run_id=UUID(int=1), owner=UUID(int=2),
    dataset_version_id=UUID(int=3), execution_mode=ExecutionMode.DOCKER,
    model_id="custom_cnn", adapter_version="1")
event = RunEvent(event_id=UUID(int=4), run_id=UUID(int=5), sequence=1,
    event_type=RunEventType.HEARTBEAT, occurred_at=datetime.now(timezone.utc), payload={})
class NeverRepository(ResultRepository):
    def acceptance_scope(self, context, event):
        raise AssertionError("identity rejection must precede persistence")
try:
    ResultService(NeverRepository()).accept_event(context, event)
except RunIdentityMismatch:
    pass
else:
    raise AssertionError("run mismatch accepted")
'''
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", script, str(PROJECT)],
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
