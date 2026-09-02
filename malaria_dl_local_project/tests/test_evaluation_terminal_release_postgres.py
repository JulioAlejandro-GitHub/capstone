from __future__ import annotations

from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import bindparam, text

from src.malaria_dl.evaluation import evaluation_terminal_service as terminal_service
from src.malaria_dl.governance.services.training_release_eligibility_service import (
    ELIGIBILITY_ACTOR,
    ELIGIBLE_REASON,
)
from src.malaria_dl.persistence.database import get_engine
from src.malaria_dl.persistence.training_release import TrainingReleaseStatus


pytestmark = pytest.mark.requires_docker_postgres

TABLES = (
    "runs",
    "artifacts",
    "run_lineage",
    "model_versions",
    "stage2_model_publications",
    "deployed_model_versions",
)


def _fingerprint(connection, table):
    if table not in TABLES:
        raise AssertionError(f"unexpected table: {table}")
    return connection.execute(
        text(
            f"""
            SELECT COUNT(*),
                   md5(COALESCE(
                       string_agg(md5(row_to_json(item)::text), '' ORDER BY item.id),
                       ''
                   ))
            FROM {table} AS item
            """
        )
    ).one()


def _release_distribution(connection):
    return dict(
        connection.execute(
            text(
                """
                SELECT release_status, COUNT(*)
                FROM runs
                WHERE run_type='training'
                GROUP BY release_status
                """
            )
        ).all()
    )


def _release_row(connection, training_run_id):
    return dict(
        connection.execute(
            text(
                """
                SELECT release_status, release_updated_at,
                       release_changed_by, release_reason
                FROM runs
                WHERE id=:training_run_id
                """
            ),
            {"training_run_id": training_run_id},
        ).mappings().one()
    )


def _insert_run(
    connection,
    run_id,
    *,
    run_type,
    status,
    release_status=None,
):
    connection.execute(
        text(
            """
            INSERT INTO runs (
                id, run_name, run_type, status, started_at, finished_at,
                release_status, release_updated_at,
                release_changed_by, release_reason, metadata
            )
            VALUES (
                :id, :name, :run_type, :status,
                CURRENT_TIMESTAMP - INTERVAL '2 minutes',
                CASE WHEN :status='completed'
                     THEN CURRENT_TIMESTAMP - INTERVAL '1 minute' END,
                CAST(:release_status AS text),
                CASE WHEN CAST(:release_status AS text) IS NOT NULL
                     THEN CURRENT_TIMESTAMP - INTERVAL '1 day' END,
                CASE WHEN CAST(:release_status AS text) IS NOT NULL
                     THEN 'rollback-only' END,
                CASE WHEN CAST(:release_status AS text) IS NOT NULL
                     THEN 'rollback-only' END,
                '{}'::jsonb
            )
            """
        ),
        {
            "id": run_id,
            "name": f"rollback-only:{run_type}:{run_id}",
            "run_type": run_type,
            "status": status,
            "release_status": release_status,
        },
    )


def _insert_version(connection, training_run_id):
    artifact_id, version_id = uuid4(), uuid4()
    path = f"rollback-only/{training_run_id}/{artifact_id}.keras"
    connection.execute(
        text(
            """
            INSERT INTO artifacts (id, run_id, artifact_type, path, metadata)
            VALUES (:id, :run_id, 'checkpoint', :path, '{}'::jsonb)
            """
        ),
        {"id": artifact_id, "run_id": training_run_id, "path": path},
    )
    connection.execute(
        text(
            """
            INSERT INTO model_versions (
                id, training_run_id, checkpoint_artifact_id,
                checkpoint_path, status, lineage_status
            )
            VALUES (
                :id, :training_run_id, :artifact_id,
                :path, 'discovered', 'resolved'
            )
            """
        ),
        {
            "id": version_id,
            "training_run_id": training_run_id,
            "artifact_id": artifact_id,
            "path": path,
        },
    )
    return version_id, artifact_id, path


def _terminal(
    connection,
    *,
    training_run_id,
    evaluation_run_id,
    version_id,
    artifact_id,
    checkpoint_path,
):
    return terminal_service.finalize_evaluation_with_lineage(
        training_run_id=training_run_id,
        evaluation_run_id=evaluation_run_id,
        model_version_id=version_id,
        checkpoint_artifact_id=artifact_id,
        checkpoint_path=checkpoint_path,
        confidence="explicit",
        lineage_metadata={"test_scope": "rollback-only"},
        summary={"test_scope": "rollback-only"},
        connection=connection,
    )


def test_terminal_release_reconciliation_is_atomic_and_rolls_back_every_write():
    engine = get_engine()
    created_ids: set[UUID] = set()
    with engine.connect() as connection:
        outer = connection.begin()
        initial_alembic = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
        initial_fingerprints = {
            table: _fingerprint(connection, table) for table in TABLES
        }
        initial_release = _release_distribution(connection)
        initial_idle_transactions = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM pg_stat_activity
                WHERE datname=current_database()
                  AND pid<>pg_backend_pid()
                  AND state LIKE 'idle in transaction%'
                """
            )
        ).scalar_one()
        try:
            training_id, evaluation_id, failed_evaluation_id = (
                uuid4(),
                uuid4(),
                uuid4(),
            )
            created_ids.update(
                {training_id, evaluation_id, failed_evaluation_id}
            )
            _insert_run(
                connection,
                training_id,
                run_type="training",
                status="completed",
                release_status="not_available",
            )
            _insert_run(
                connection,
                evaluation_id,
                run_type="evaluation",
                status="started",
            )
            _insert_run(
                connection,
                failed_evaluation_id,
                run_type="evaluation",
                status="started",
            )
            version_id, artifact_id, checkpoint_path = _insert_version(
                connection, training_id
            )
            created_ids.update({version_id, artifact_id})
            release_before = _release_row(connection, training_id)

            result = _terminal(
                connection,
                training_run_id=training_id,
                evaluation_run_id=evaluation_id,
                version_id=version_id,
                artifact_id=artifact_id,
                checkpoint_path=checkpoint_path,
            )
            assert result.lineage.created
            assert result.finalization.changed
            assert result.release_decision.changed
            assert result.lineage.training_run_id == training_id
            assert result.release_decision.training_run_id == training_id
            assert result.release_decision.previous_status is (
                TrainingReleaseStatus.NOT_AVAILABLE
            )
            assert result.release_decision.target_status is (
                TrainingReleaseStatus.AVAILABLE_TO_PUBLISH
            )
            assert connection.execute(
                text("SELECT status FROM runs WHERE id=:id"),
                {"id": evaluation_id},
            ).scalar_one() == "completed"
            release_after = _release_row(connection, training_id)
            assert release_after["release_status"] == "available_to_publish"
            assert release_after["release_updated_at"] > (
                release_before["release_updated_at"]
            )
            assert release_after["release_changed_by"] == ELIGIBILITY_ACTOR
            assert release_after["release_reason"] == ELIGIBLE_REASON

            retried = _terminal(
                connection,
                training_run_id=training_id,
                evaluation_run_id=evaluation_id,
                version_id=version_id,
                artifact_id=artifact_id,
                checkpoint_path="must/not/replace.keras",
            )
            assert not retried.lineage.created
            assert not retried.finalization.changed
            assert not retried.release_decision.changed
            assert _release_row(connection, training_id) == release_after

            productive_identity = connection.execute(
                text(
                    """
                    SELECT l.parent_run_id, l.child_run_id,
                           l.model_version_id, l.checkpoint_artifact_id,
                           l.checkpoint_path
                    FROM run_lineage AS l
                    JOIN runs AS training
                      ON training.id=l.parent_run_id
                     AND training.run_type='training'
                     AND training.release_status='productive_stage2'
                    JOIN runs AS evaluation
                      ON evaluation.id=l.child_run_id
                     AND evaluation.run_type='evaluation'
                     AND evaluation.status='completed'
                    WHERE l.relationship_type='evaluates_checkpoint_from'
                    """
                )
            ).mappings().one()
            productive_before = _release_row(
                connection, productive_identity["parent_run_id"]
            )
            protected = _terminal(
                connection,
                training_run_id=productive_identity["parent_run_id"],
                evaluation_run_id=productive_identity["child_run_id"],
                version_id=productive_identity["model_version_id"],
                artifact_id=productive_identity["checkpoint_artifact_id"],
                checkpoint_path=productive_identity["checkpoint_path"],
            )
            assert protected.release_decision.productive_protected
            assert not protected.release_decision.changed
            assert protected.release_decision.target_status is (
                TrainingReleaseStatus.PRODUCTIVE_STAGE2
            )
            assert _release_row(
                connection, productive_identity["parent_run_id"]
            ) == productive_before

            nested = connection.begin_nested()
            try:
                with patch.object(
                    terminal_service,
                    "reconcile_training_release_eligibility",
                    side_effect=RuntimeError("induced release failure"),
                ), pytest.raises(RuntimeError, match="induced release failure"):
                    _terminal(
                        connection,
                        training_run_id=training_id,
                        evaluation_run_id=failed_evaluation_id,
                        version_id=version_id,
                        artifact_id=artifact_id,
                        checkpoint_path=checkpoint_path,
                    )
                assert connection.execute(
                    text("SELECT status FROM runs WHERE id=:id"),
                    {"id": failed_evaluation_id},
                ).scalar_one() == "completed"
                assert connection.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM run_lineage
                        WHERE child_run_id=:evaluation_run_id
                          AND relationship_type='evaluates_checkpoint_from'
                        """
                    ),
                    {"evaluation_run_id": failed_evaluation_id},
                ).scalar_one() == 1
            finally:
                if nested.is_active:
                    nested.rollback()
            assert connection.execute(
                text("SELECT status FROM runs WHERE id=:id"),
                {"id": failed_evaluation_id},
            ).scalar_one() == "started"
            assert connection.execute(
                text(
                    """
                    SELECT COUNT(*) FROM run_lineage
                    WHERE child_run_id=:evaluation_run_id
                      AND relationship_type='evaluates_checkpoint_from'
                    """
                ),
                {"evaluation_run_id": failed_evaluation_id},
            ).scalar_one() == 0
            assert _release_row(connection, training_id) == release_after

            assert connection.in_transaction()
            assert outer.is_active
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == "20260901_01"
        finally:
            if outer.is_active:
                outer.rollback()

    with engine.connect() as independent:
        assert independent.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == initial_alembic == "20260901_01"
        assert {
            table: _fingerprint(independent, table) for table in TABLES
        } == initial_fingerprints
        assert _release_distribution(independent) == initial_release
        for table in ("runs", "artifacts", "model_versions", "run_lineage"):
            assert independent.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE id IN :ids").bindparams(
                    bindparam("ids", expanding=True)
                ),
                {"ids": tuple(created_ids)},
            ).scalar_one() == 0
        assert independent.execute(
            text(
                """
                SELECT COUNT(*) FROM run_lineage
                WHERE child_run_id IN :ids OR parent_run_id IN :ids
                """
            ).bindparams(bindparam("ids", expanding=True)),
            {"ids": tuple(created_ids)},
        ).scalar_one() == 0
        assert independent.execute(
            text(
                """
                SELECT COUNT(*)
                FROM pg_stat_activity
                WHERE datname=current_database()
                  AND pid<>pg_backend_pid()
                  AND state LIKE 'idle in transaction%'
                """
            )
        ).scalar_one() == initial_idle_transactions
