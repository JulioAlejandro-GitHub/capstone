"""API query contract with a mock read-only connection, not PostgreSQL."""

import importlib.util
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace
from uuid import uuid4


def test_paginated_structured_results_are_read_only(monkeypatch):
    calls = []

    class Result:
        def scalars(self):
            return self

        def all(self):
            return [{"sample_id": "synthetic", "raw_score": 0.4}]

    def execute(query, params):
        calls.append((str(query), params))
        return Result()

    @contextmanager
    def scope(datasource):
        assert datasource == "malaria"
        yield SimpleNamespace(execute=execute)

    fake_db = ModuleType("app.db")
    fake_db.read_only_transaction = scope
    import sys

    monkeypatch.setitem(sys.modules, "app.db", fake_db)
    path = Path(__file__).resolve().parents[2] / "backend_api/app/routes/assessments.py"
    spec = importlib.util.spec_from_file_location("assessment_api_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    aid = uuid4()
    result = module.results(aid, limit=10, offset=0)
    assert result["items"][0]["raw_score"] == 0.4
    assert calls[0][1] == {"id": str(aid), "limit": 10, "offset": 0}
    assert "assessment_results" in calls[0][0] and "ORDER BY sample_id" in calls[0][0]
