"""Current-schema PostgreSQL regressions with isolated SELECT fixtures.

Replaces the historical 24-TRAIN snapshot: E6 children have no separate run_id.
"""
from uuid import UUID
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.lineage_children import get_training_lineage_children
from test_e6_lineage_read_only import TRAIN, fixtures, explain_fixture, install_fixtures, scientific_fingerprint

pytestmark = pytest.mark.requires_docker_postgres


def test_all_training_children_counts_scope_order_limits_and_integrity(monkeypatch):
    values = fixtures(("verified",), True, True, False)
    explain_fixture(values, 0, ("verified", "failed"))
    before = scientific_fingerprint()
    install_fixtures(monkeypatch, values)
    result = get_training_lineage_children(UUID(TRAIN), "malaria", 100)
    assert result.evaluation_count == len(result.evaluations) == 2
    assert result.explainability_count == len(result.explainabilities) == 2
    assert {x.source_kind for x in result.explainabilities} == {"run", "assessment_explain_e6"}
    assert result.total_count == 4 and not result.truncated
    with TestClient(app) as client:
        ids = set()
        for offset in range(4):
            response = client.get(f"/runs/{TRAIN}/lineage-children", params=dict(limit=1, offset=offset))
            assert response.status_code == 200
            payload = response.json()
            assert payload['total_count'] == 4
            assert payload['offset'] == offset
            assert payload['truncated'] == (offset < 3)
            child = (payload['evaluations'] + payload['explainabilities'])[0]
            ids.add(child.get('run_id') or child['attempt_id'])
        assert len(ids) == 4
        assert client.get(f"/runs/{TRAIN}/lineage-children?offset=-1").status_code == 422
    assert scientific_fingerprint() == before
