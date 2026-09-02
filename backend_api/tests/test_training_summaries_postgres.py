"""Read-only contract proof against the existing Docker PostgreSQL service."""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import read_only_transaction
from app.main import app
from app.schemas.training_summaries import TrainingSummaryCollection


pytestmark = pytest.mark.requires_docker_postgres

PRODUCTIVE_TRAINING_ID = "623ad00c-0b03-4cf0-8f2c-bb9496efb496"

FINGERPRINTS_SQL = """
SELECT 'runs' AS table_name,
       md5(string_agg(md5(row_to_json(row_data)::text), '' ORDER BY id)) AS value
FROM runs AS row_data
UNION ALL
SELECT 'run_lineage',
       md5(string_agg(md5(row_to_json(row_data)::text), '' ORDER BY id))
FROM run_lineage AS row_data
UNION ALL
SELECT 'model_versions',
       md5(string_agg(md5(row_to_json(row_data)::text), '' ORDER BY id))
FROM model_versions AS row_data
UNION ALL
SELECT 'stage2_model_publications',
       md5(string_agg(md5(row_to_json(row_data)::text), '' ORDER BY id))
FROM stage2_model_publications AS row_data
UNION ALL
SELECT 'deployed_model_versions',
       md5(string_agg(md5(row_to_json(row_data)::text), '' ORDER BY id))
FROM deployed_model_versions AS row_data
ORDER BY table_name
"""

EXPECTED_SQL = """
SELECT
    training.id::text AS run_id,
    training.release_status,
    training.release_updated_at,
    training.release_changed_by,
    training.release_reason,
    COUNT(DISTINCT lineage.child_run_id) FILTER (
        WHERE lineage.relationship_type = 'evaluates_checkpoint_from'
          AND child.run_type = 'evaluation'
    ) AS evaluation_count,
    COUNT(DISTINCT lineage.child_run_id) FILTER (
        WHERE lineage.relationship_type = 'explains_checkpoint_from'
          AND child.run_type = 'explainability'
    ) AS explainability_count,
    training.started_at,
    training.created_at
FROM runs AS training
LEFT JOIN run_lineage AS lineage ON lineage.parent_run_id = training.id
LEFT JOIN runs AS child ON child.id = lineage.child_run_id
WHERE training.run_type = 'training'
GROUP BY training.id
ORDER BY
    training.started_at DESC NULLS LAST,
    training.created_at DESC,
    training.id
"""


def _read_database_snapshot():
    with read_only_transaction("malaria") as connection:
        assert connection.execute(
            text("SHOW transaction_read_only")
        ).scalar_one() == "on"
        fingerprints = dict(
            connection.execute(text(FINGERPRINTS_SQL)).all()
        )
        expected = [
            dict(row)
            for row in connection.execute(text(EXPECTED_SQL)).mappings().all()
        ]
        counts = dict(
            connection.execute(
                text(
                    """
                    SELECT
                        (SELECT count(*) FROM runs) AS runs,
                        (SELECT count(*) FROM runs WHERE run_type = 'evaluation')
                            AS evaluations,
                        (SELECT count(*) FROM runs
                         WHERE run_type = 'evaluation' AND status = 'completed')
                            AS completed_evaluations,
                        (SELECT count(*) FROM run_lineage) AS lineage,
                        (SELECT count(*) FROM model_versions) AS model_versions
                    """
                )
            ).mappings().one()
        )
    return fingerprints, expected, counts


def _parse_timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def test_training_summaries_http_is_exact_read_only_and_preserves_database():
    fingerprints_before, expected, counts_before = _read_database_snapshot()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/runs/training-summaries",
            params={"datasource": "malaria", "limit": 100},
        )

    assert response.status_code == 200, response.text
    payload = TrainingSummaryCollection.model_validate(response.json())
    raw_items = response.json()["items"]
    assert payload.count == len(payload.items) == len(expected) == 24
    assert payload.limit == 100
    assert all(item.run_type == "training" for item in payload.items)
    assert len({str(item.run_id) for item in payload.items}) == 24
    assert [str(item.run_id) for item in payload.items] == [
        row["run_id"] for row in expected
    ]

    release_counts = {
        value: sum(
            item.release_status is not None and item.release_status.value == value
            for item in payload.items
        )
        for value in (
            "available_to_publish",
            "productive_stage2",
            "not_available",
        )
    }
    assert release_counts == {
        "available_to_publish": 23,
        "productive_stage2": 1,
        "not_available": 0,
    }
    productive = [
        item for item in payload.items
        if item.release_status and item.release_status.value == "productive_stage2"
    ]
    assert [str(item.run_id) for item in productive] == [PRODUCTIVE_TRAINING_ID]

    expected_by_id = {row["run_id"]: row for row in expected}
    for item, raw in zip(payload.items, raw_items, strict=True):
        source = expected_by_id[str(item.run_id)]
        assert (item.release_status.value if item.release_status else None) == source[
            "release_status"
        ]
        assert _parse_timestamp(raw["release_updated_at"]) == source[
            "release_updated_at"
        ]
        assert item.release_changed_by == source["release_changed_by"]
        assert item.release_reason == source["release_reason"]
        assert item.evaluation_count == source["evaluation_count"]
        assert item.explainability_count == source["explainability_count"]
        for absent in ("evaluations", "explainability", "model_version_id", "artifact"):
            assert absent not in raw

    fingerprints_after, _, counts_after = _read_database_snapshot()
    assert fingerprints_after == fingerprints_before
    assert counts_after == counts_before == {
        "runs": 88,
        "evaluations": 36,
        "completed_evaluations": 36,
        "lineage": 61,
        "model_versions": 36,
    }
