"""Read-only API evidence pagination through the shared repository/service."""
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4


def test_paginated_structured_results_are_read_only(monkeypatch):
    from app.repositories import assessments
    from app.services.assessments import AssessmentReadService
    calls = []

    class Result:
        def scalars(self):
            return iter([{"sample_id": "synthetic", "raw_score": 0.4}])

    def execute(query, params):
        calls.append((str(query), params))
        return Result()

    @contextmanager
    def scope(datasource):
        assert datasource == "malaria"
        yield SimpleNamespace(execute=execute)

    monkeypatch.setattr(assessments, 'read_only_transaction', scope)
    aid = uuid4()
    service = AssessmentReadService(assessments.AssessmentReadRepository())
    result = service.payloads(aid,'results',10,0)
    assert result['items'][0]['raw_score'] == .4
    assert calls[0][1] == {'id':str(aid),'limit':10,'offset':0}
    assert 'assessment_results' in calls[0][0] and 'ORDER BY sample_id' in calls[0][0]
