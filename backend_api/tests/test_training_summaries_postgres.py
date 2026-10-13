"""Summary regression with current-schema fixtures, independent of old 35-TRAIN data."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from test_e6_lineage_read_only import TRAIN, LEGACY, STAMP, fixtures, explain_fixture, install_fixtures, scientific_fingerprint

pytestmark = pytest.mark.requires_docker_postgres


def test_training_summaries_http_is_exact_read_only_and_preserves_database(monkeypatch):
    values = fixtures(("verified",), False, False, False)
    values['runs'][0].update(release_status='available_to_publish', release_updated_at=STAMP,
                             release_changed_by='synthetic', release_reason='fixture')
    values['runs'].append({**values['runs'][0], 'id': LEGACY, 'release_status': 'productive_stage2'})
    explain_fixture(values, 0)
    explain_fixture(values, 1)
    before = scientific_fingerprint()
    install_fixtures(monkeypatch, values)
    with TestClient(app) as client:
        response = client.get('/runs/training-summaries?limit=100')
    assert response.status_code == 200
    payload = response.json()
    assert payload['count'] == len(payload['items']) == 2
    rows = {x['run_id']: x for x in payload['items']}
    assert rows[TRAIN]['evaluation_count'] == 1
    assert rows[TRAIN]['explainability_count'] == 2
    assert rows[LEGACY]['evaluation_count'] == rows[LEGACY]['explainability_count'] == 0
    assert rows[TRAIN]['release_status'] == 'available_to_publish'
    assert rows[LEGACY]['release_status'] == 'productive_stage2'
    for row in rows.values():
        assert row['release_changed_by'] == 'synthetic'
        assert row['release_reason'] == 'fixture'
        assert row['release_updated_at']
        assert 'evaluations' not in row and 'artifact' not in row
    assert scientific_fingerprint() == before
