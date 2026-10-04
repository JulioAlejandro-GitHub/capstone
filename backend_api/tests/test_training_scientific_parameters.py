"""Scientific listing contract, including read-only checks of persisted provenance."""
from fastapi.testclient import TestClient
from sqlalchemy import text
import pytest

from app.db import read_only_transaction
from app.main import app
from app.schemas.training_summaries import ScientificParameters


@pytest.mark.parametrize('value', [False, True, None])
def test_calibration_preserves_native_boolean(value: bool | None) -> None:
    assert ScientificParameters(calibrate_threshold=value).model_dump()['calibrate_threshold'] is value


def test_zero_and_missing_are_not_defaults() -> None:
    values = ScientificParameters(target_recall=0, early_stopping_patience=0).model_dump()
    assert values['target_recall'] == 0
    assert values['early_stopping_patience'] == 0
    assert values['threshold'] is None
    assert all(value is None for value in ScientificParameters().model_dump().values())


@pytest.mark.requires_docker_postgres
def test_listing_matches_each_run_snapshot_and_final_validation_read_only() -> None:
    with read_only_transaction('malaria') as connection:
        assert connection.execute(text('SHOW transaction_read_only')).scalar_one() == 'on'
        expected = connection.execute(text("""
            SELECT r.id, r.execution_parameters #>
                '{model_configuration_e2,configuration,resolved,execution}' AS execution,
                e.threshold_used, m.f2_parasitized,
                e.checkpoint_artifact_id::text AS checkpoint,
                r.execution_parameters #>>
                '{e10_v2_evaluation_context_v1,checkpoint_artifact_id}' AS snapshot_checkpoint
            FROM runs r
            LEFT JOIN LATERAL (
                SELECT * FROM evaluations e
                WHERE e.training_run_id = r.id AND e.split = 'val'
                  AND e.evaluation_role = 'training_validation_final'
                ORDER BY e.created_at DESC, e.id DESC LIMIT 1
            ) e ON TRUE
            LEFT JOIN run_clinical_metrics m ON m.evaluation_id = e.id
            WHERE r.run_type = 'training'
            ORDER BY r.started_at DESC NULLS LAST, r.created_at DESC, r.id
            LIMIT 500
        """)).mappings().all()
    with TestClient(app) as client:
        response = client.get('/runs/training-summaries?datasource=malaria&limit=500')
    assert response.status_code == 200, response.text
    items = response.json()['items']
    assert len(items) == len({item['run_id'] for item in items}) == len(expected)
    for item, source in zip(items, expected, strict=True):
        assert item['run_id'] == str(source['id'])
        actual = item['scientific_parameters']
        assert len(actual) == 9
        for key in actual.keys() - {'threshold', 'val_f2_parasitized'}:
            assert actual[key] == source['execution'].get(key)
        assert actual['threshold'] == source['threshold_used']
        assert actual['val_f2_parasitized'] == (
            float(source['f2_parasitized']) if source['f2_parasitized'] is not None else None
        )
        if source['snapshot_checkpoint']:
            assert source['checkpoint'] == source['snapshot_checkpoint']
