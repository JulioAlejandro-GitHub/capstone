from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import bindparam, text

from src.malaria_dl.evaluation.evaluation_finalization_service import (
    EvaluationFinalizationConflictError,
    InvalidEvaluationTransitionError,
    NotEvaluationRunError,
    finalize_evaluation_run,
)
from src.malaria_dl.persistence.database import get_engine


pytestmark = pytest.mark.requires_docker_postgres


TABLES = (
    "runs",
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
                WHERE run_type = 'training'
                GROUP BY release_status
                """
            )
        ).all()
    )


def _evaluation_statuses(connection):
    return dict(
        connection.execute(
            text(
                """
                SELECT status, COUNT(*)
                FROM runs
                WHERE run_type = 'evaluation'
                GROUP BY status
                """
            )
        ).all()
    )


def _insert_run(connection, run_id, *, run_type, status):
    connection.execute(
        text(
            """
            INSERT INTO runs (
                id,
                run_name,
                run_type,
                status,
                started_at,
                finished_at,
                metadata
            )
            VALUES (
                :run_id,
                :run_name,
                :run_type,
                :status,
                CURRENT_TIMESTAMP - INTERVAL '1 minute',
                CASE WHEN :status = 'failed' THEN CURRENT_TIMESTAMP END,
                '{}'::jsonb
            )
            """
        ),
        {
            "run_id": run_id,
            "run_name": f"rollback-only:{run_type}:{run_id}",
            "run_type": run_type,
            "status": status,
        },
    )


class ConflictConnection:
    """Change the locked row immediately before the service CAS."""

    def __init__(self, connection):
        self.connection = connection
        self.injected = False

    def execute(self, statement, params=None):
        sql = str(statement)
        if (
            not self.injected
            and "SET status = 'completed'" in sql
            and "AND status = 'started'" in sql
        ):
            self.connection.execute(
                text(
                    """
                    UPDATE runs
                    SET status = 'failed',
                        finished_at = CURRENT_TIMESTAMP
                    WHERE id = :evaluation_run_id
                      AND run_type = 'evaluation'
                      AND status = 'started'
                    """
                ),
                {"evaluation_run_id": params["evaluation_run_id"]},
            )
            self.injected = True
        return self.connection.execute(statement, params or {})


def test_evaluation_finalization_rolls_back_every_postgres_write():
    engine = get_engine()
    with engine.connect() as connection:
        outer_transaction = connection.begin()
        initial_alembic = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
        initial_fingerprints = {
            table: _fingerprint(connection, table) for table in TABLES
        }
        initial_release = _release_distribution(connection)
        initial_evaluation_statuses = _evaluation_statuses(connection)
        initial_productive = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM runs
                WHERE run_type='training'
                  AND release_status='productive_stage2'
                """
            )
        ).scalar_one()

        started_id = uuid4()
        training_id = connection.execute(
            text(
                """
                SELECT id FROM runs
                WHERE run_type='training'
                ORDER BY id
                LIMIT 1
                """
            )
        ).scalar_one()
        failed_id = uuid4()
        conflict_id = uuid4()
        try:
            _insert_run(
                connection, started_id, run_type="evaluation", status="started"
            )
            _insert_run(
                connection, failed_id, run_type="evaluation", status="failed"
            )
            _insert_run(
                connection, conflict_id, run_type="evaluation", status="started"
            )

            requested_at = datetime.now(UTC)
            changed = finalize_evaluation_run(
                started_id,
                completed_at=requested_at,
                summary={"test_scope": "rollback-only"},
                connection=connection,
            )
            assert changed.changed
            assert changed.completed_at == requested_at

            persisted_before_retry = connection.execute(
                text(
                    """
                    SELECT finished_at, duration_seconds, metadata
                    FROM runs WHERE id=:run_id
                    """
                ),
                {"run_id": started_id},
            ).mappings().one()
            retried = finalize_evaluation_run(
                started_id,
                completed_at=datetime.now(UTC),
                duration_seconds=999,
                summary={"must_not_be_written": True},
                connection=connection,
            )
            persisted_after_retry = connection.execute(
                text(
                    """
                    SELECT finished_at, duration_seconds, metadata
                    FROM runs WHERE id=:run_id
                    """
                ),
                {"run_id": started_id},
            ).mappings().one()
            assert not retried.changed
            assert dict(persisted_after_retry) == dict(persisted_before_retry)
            assert "must_not_be_written" not in persisted_after_retry["metadata"]

            with pytest.raises(NotEvaluationRunError):
                finalize_evaluation_run(training_id, connection=connection)
            with pytest.raises(InvalidEvaluationTransitionError):
                finalize_evaluation_run(failed_id, connection=connection)

            conflict_connection = ConflictConnection(connection)
            with pytest.raises(EvaluationFinalizationConflictError):
                finalize_evaluation_run(
                    conflict_id, connection=conflict_connection
                )
            assert conflict_connection.injected
            assert connection.in_transaction()
            assert outer_transaction.is_active
            assert connection.execute(
                text("SELECT status FROM runs WHERE id=:run_id"),
                {"run_id": started_id},
            ).scalar_one() == "completed"
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == "20260829_01"
            assert _release_distribution(connection) == initial_release
            assert connection.execute(
                text(
                    """
                    SELECT COUNT(*) FROM runs
                    WHERE run_type='training'
                      AND release_status='productive_stage2'
                    """
                )
            ).scalar_one() == initial_productive
        finally:
            if outer_transaction.is_active:
                outer_transaction.rollback()

    with engine.connect() as independent:
        assert independent.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == initial_alembic == "20260829_01"
        assert {
            table: _fingerprint(independent, table) for table in TABLES
        } == initial_fingerprints
        assert _release_distribution(independent) == initial_release
        assert _evaluation_statuses(independent) == initial_evaluation_statuses
        assert independent.execute(
            text(
                """
                SELECT COUNT(*) FROM runs
                WHERE run_type='training'
                  AND release_status='productive_stage2'
                """
            )
        ).scalar_one() == initial_productive
        assert independent.execute(
            text(
                """
                SELECT COUNT(*) FROM runs
                WHERE id IN :run_ids
                """
            ).bindparams(bindparam("run_ids", expanding=True)),
            {
                "run_ids": (
                    started_id,
                    failed_id,
                    conflict_id,
                )
            },
        ).scalar_one() == 0
