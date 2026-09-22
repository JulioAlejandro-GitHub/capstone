"""Keep every contract import independent of installed infrastructure."""
import ast
from pathlib import Path
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]
CONTRACTS = PROJECT / "src/malaria_dl/execution/contracts"


def test_contract_ast_allows_only_stdlib_and_contract_siblings():
    allowed = {"__future__", "abc", "collections.abc", "dataclasses", "datetime", "enum",
               "math", "re", "types", "typing", "uuid"}
    siblings = {path.stem for path in CONTRACTS.glob("*.py")}
    for path in CONTRACTS.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name in allowed for alias in node.names), (path, node.lineno)
            elif isinstance(node, ast.ImportFrom):
                assert ((node.level == 1 and node.module in siblings)
                        or (node.level == 0 and node.module in allowed)), (path, node.lineno)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"__import__", "eval", "exec"}, (path, node.lineno)


def test_import_and_round_trip_in_isolated_stdlib_process():
    script = r'''
import sys
sys.path.insert(0, sys.argv[1])
import importlib.abc
import json
from datetime import datetime, timezone
from uuid import UUID
allowed = {"src", "src.malaria_dl", "src.malaria_dl.execution"}
prefix = "src.malaria_dl.execution.contracts"
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split(".")[0]
        if fullname in allowed or fullname == prefix or fullname.startswith(prefix + "."):
            return None
        if root in sys.stdlib_module_names:
            return None
        raise AssertionError("Infrastructure import: " + fullname)
sys.meta_path.insert(0, Guard())
from src.malaria_dl.execution.contracts import RunEvent, RunEventType, ExecutionContext, ExecutionMode, RunReporter
context = ExecutionContext(run_id=UUID(int=1), owner=UUID(int=2),
    dataset_version_id=UUID(int=3), execution_mode=ExecutionMode.DOCKER,
    model_id="custom_cnn", adapter_version="1")
event = RunEvent(event_id=UUID(int=4), run_id=context.run_id, sequence=1,
    event_type=RunEventType.HEARTBEAT, occurred_at=datetime.now(timezone.utc), payload={})
assert RunEvent.from_dict(json.loads(json.dumps(event.to_dict()))) == event
'''
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", script, str(PROJECT)],
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
