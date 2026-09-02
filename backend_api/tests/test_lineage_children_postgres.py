"""Read-only PostgreSQL proof for the lazy direct-children endpoint."""

from __future__ import annotations

from collections import defaultdict

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import read_only_transaction
from app.main import app
from app.schemas.lineage_children import TrainingLineageChildren
from app.services.lineage_children import get_training_lineage_children


pytestmark = pytest.mark.requires_docker_postgres

FINGERPRINTS_SQL = """
SELECT 'runs', md5(string_agg(md5(row_to_json(row_data)::text), '' ORDER BY id))
FROM runs AS row_data
UNION ALL
SELECT 'run_lineage', md5(string_agg(md5(row_to_json(row_data)::text), '' ORDER BY id))
FROM run_lineage AS row_data
UNION ALL
SELECT 'model_versions', md5(string_agg(md5(row_to_json(row_data)::text), '' ORDER BY id))
FROM model_versions AS row_data
UNION ALL
SELECT 'stage2_model_publications', md5(string_agg(md5(row_to_json(row_data)::text), '' ORDER BY id))
FROM stage2_model_publications AS row_data
UNION ALL
SELECT 'deployed_model_versions', md5(string_agg(md5(row_to_json(row_data)::text), '' ORDER BY id))
FROM deployed_model_versions AS row_data
"""

DIRECT_CHILDREN_SQL = """
WITH eligible AS (
    SELECT
        lineage.parent_run_id,
        child.id AS child_run_id,
        child.run_type,
        lineage.relationship_type,
        child.started_at,
        child.created_at
    FROM run_lineage AS lineage
    JOIN runs AS child ON child.id = lineage.child_run_id
    WHERE (
        lineage.relationship_type = 'evaluates_checkpoint_from'
        AND child.run_type = 'evaluation'
    ) OR (
        lineage.relationship_type = 'explains_checkpoint_from'
        AND child.run_type = 'explainability'
    )
)
SELECT
    training.id::text AS training_run_id,
    eligible.child_run_id::text,
    eligible.run_type,
    eligible.relationship_type,
    eligible.started_at,
    eligible.created_at
FROM runs AS training
LEFT JOIN eligible ON eligible.parent_run_id = training.id
WHERE training.run_type = 'training'
ORDER BY
    training.id,
    eligible.started_at ASC NULLS LAST,
    eligible.created_at ASC,
    eligible.child_run_id ASC
"""


def database_snapshot():
    with read_only_transaction("malaria") as connection:
        assert connection.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
        fingerprints = dict(connection.execute(text(FINGERPRINTS_SQL)).all())
        rows = [
            dict(row)
            for row in connection.execute(text(DIRECT_CHILDREN_SQL)).mappings().all()
        ]
        duplicated_evaluations = connection.execute(
            text(
                """
                SELECT count(*)
                FROM (
                    SELECT lineage.child_run_id
                    FROM run_lineage AS lineage
                    JOIN runs AS child ON child.id = lineage.child_run_id
                    WHERE lineage.relationship_type = 'evaluates_checkpoint_from'
                      AND child.run_type = 'evaluation'
                    GROUP BY lineage.child_run_id
                    HAVING count(DISTINCT lineage.parent_run_id) > 1
                ) AS duplicated
                """
            )
        ).scalar_one()
    return fingerprints, rows, duplicated_evaluations


def expected_by_training(rows):
    expected = defaultdict(lambda: {"evaluation": [], "explainability": []})
    for row in rows:
        if row["child_run_id"] is not None:
            expected[row["training_run_id"]][row["run_type"]].append(
                row["child_run_id"]
            )
        else:
            expected[row["training_run_id"]]
    return expected


def test_all_training_children_counts_scope_order_limits_and_integrity():
    fingerprints_before, rows, duplicated_evaluations = database_snapshot()
    expected = expected_by_training(rows)

    assert len(expected) == 24
    assert duplicated_evaluations == 0

    results = {}
    for training_run_id, direct in expected.items():
        result = get_training_lineage_children(
            training_run_id=training_run_id,
            datasource="malaria",
            limit=500,
        )
        results[training_run_id] = result
        assert result.evaluation_count == len(set(direct["evaluation"]))
        assert result.explainability_count == len(set(direct["explainability"]))
        assert result.total_count == (
            result.evaluation_count + result.explainability_count
        )
        assert [str(item.run_id) for item in result.evaluations] == direct["evaluation"]
        assert [str(item.run_id) for item in result.explainabilities] == direct[
            "explainability"
        ]
        assert all(
            str(item.parent_run_id) == training_run_id
            and item.relationship_type == "evaluates_checkpoint_from"
            for item in result.evaluations
        )
        assert all(
            str(item.parent_run_id) == training_run_id
            and item.relationship_type == "explains_checkpoint_from"
            for item in result.explainabilities
        )
        assert result.truncated is False
        TrainingLineageChildren.model_validate(result.model_dump(mode="json"))

    # Select real max/min/both cases dynamically from the current database.
    maximum_id = max(results, key=lambda item: results[item].total_count)
    minimum_id = min(results, key=lambda item: results[item].total_count)
    assert results[maximum_id].total_count >= results[minimum_id].total_count
    both_id = next(
        (
            item
            for item, result in results.items()
            if result.evaluation_count and result.explainability_count
        ),
        None,
    )
    assert both_id is not None

    limited = get_training_lineage_children(maximum_id, "malaria", 1)
    assert len(limited.evaluations) + len(limited.explainabilities) == 1
    assert limited.total_count == results[maximum_id].total_count
    assert limited.truncated is (limited.total_count > 1)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            f"/runs/{maximum_id}/lineage-children",
            params={"datasource": "malaria", "limit": 1},
        )
    assert response.status_code == 200, response.text
    http_payload = TrainingLineageChildren.model_validate(response.json())
    assert http_payload.training_run_id == limited.training_run_id
    assert http_payload.total_count == limited.total_count
    assert http_payload.truncated == limited.truncated

    fingerprints_after, _, duplicated_after = database_snapshot()
    assert fingerprints_after == fingerprints_before
    assert duplicated_after == duplicated_evaluations == 0
