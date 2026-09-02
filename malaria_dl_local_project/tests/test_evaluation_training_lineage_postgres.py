from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import bindparam, text

from src.malaria_dl.evaluation.evaluation_finalization_service import (
    InvalidEvaluationTransitionError,
)
from src.malaria_dl.evaluation.evaluation_terminal_service import (
    finalize_evaluation_with_lineage,
)
from src.malaria_dl.evaluation.evaluation_training_lineage_service import (
    CheckpointArtifactOwnershipError,
    EvaluationTrainingLineageConflictError,
    create_or_confirm_evaluation_training_lineage,
)
from src.malaria_dl.persistence.database import get_engine


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
                  AND COALESCE(run_name, '') NOT LIKE 'rollback-only:%'
                GROUP BY release_status
                """
            )
        ).all()
    )


def _insert_run(connection, run_id, *, run_type, status="started"):
    connection.execute(
        text(
            """
            INSERT INTO runs (
                id, run_name, run_type, status, started_at, finished_at, metadata
            )
            VALUES (
                :id, :name, :run_type, :status,
                CURRENT_TIMESTAMP - INTERVAL '1 minute',
                CASE WHEN :status = 'failed' THEN CURRENT_TIMESTAMP END,
                '{}'::jsonb
            )
            """
        ),
        {
            "id": run_id,
            "name": f"rollback-only:{run_type}:{run_id}",
            "run_type": run_type,
            "status": status,
        },
    )


def _insert_version(connection, training_run_id):
    artifact_id = uuid4()
    version_id = uuid4()
    path = f"rollback-only/{training_run_id}/{artifact_id}.keras"
    connection.execute(
        text(
            """
            INSERT INTO artifacts (id, run_id, artifact_type, name, path, metadata)
            VALUES (:id, :run_id, 'checkpoint', 'rollback-only', :path, '{}'::jsonb)
            """
        ),
        {"id": artifact_id, "run_id": training_run_id, "path": path},
    )
    connection.execute(
        text(
            """
            INSERT INTO model_versions (
                id, version_name, checkpoint_path, training_run_id,
                checkpoint_artifact_id, status, lineage_status
            )
            VALUES (
                :id, :name, :path, :training_run_id,
                :artifact_id, 'discovered', 'resolved'
            )
            """
        ),
        {
            "id": version_id,
            "name": f"rollback-only:{version_id}",
            "path": path,
            "training_run_id": training_run_id,
            "artifact_id": artifact_id,
        },
    )
    return version_id, artifact_id, path


def _lineage_row(connection, evaluation_run_id):
    row = connection.execute(
        text(
            """
            SELECT * FROM run_lineage
            WHERE child_run_id=:evaluation_run_id
              AND relationship_type='evaluates_checkpoint_from'
            """
        ),
        {"evaluation_run_id": evaluation_run_id},
    ).mappings().one_or_none()
    return None if row is None else dict(row)


def test_strict_evaluation_training_lineage_rolls_back_all_postgres_writes():
    engine = get_engine()
    created_ids = set()
    with engine.connect() as connection:
        outer = connection.begin()
        initial_alembic = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
        initial_fingerprints = {
            table: _fingerprint(connection, table) for table in TABLES
        }
        initial_release = _release_distribution(connection)
        try:
            train_one, train_two = uuid4(), uuid4()
            evaluation, failed_new, failed_existing = uuid4(), uuid4(), uuid4()
            for value in (
                train_one,
                train_two,
                evaluation,
                failed_new,
                failed_existing,
            ):
                created_ids.add(value)
            _insert_run(connection, train_one, run_type="training", status="completed")
            _insert_run(connection, train_two, run_type="training", status="completed")
            _insert_run(connection, evaluation, run_type="evaluation")
            _insert_run(connection, failed_new, run_type="evaluation", status="failed")
            _insert_run(
                connection, failed_existing, run_type="evaluation", status="failed"
            )
            version_one, artifact_one, path_one = _insert_version(
                connection, train_one
            )
            version_one_b, artifact_one_b, path_one_b = _insert_version(
                connection, train_one
            )
            version_two, artifact_two, path_two = _insert_version(
                connection, train_two
            )
            created_ids.update(
                {
                    version_one,
                    artifact_one,
                    version_one_b,
                    artifact_one_b,
                    version_two,
                    artifact_two,
                }
            )

            terminal = finalize_evaluation_with_lineage(
                training_run_id=train_one,
                evaluation_run_id=evaluation,
                model_version_id=version_one,
                checkpoint_artifact_id=artifact_one,
                checkpoint_path=path_one,
                confidence="explicit",
                lineage_metadata={"original": True},
                summary={"postgres_contract": True},
                connection=connection,
            )
            assert terminal.lineage.created
            assert terminal.finalization.changed
            original = _lineage_row(connection, evaluation)
            created_ids.add(original["id"])
            retried = finalize_evaluation_with_lineage(
                training_run_id=train_one,
                evaluation_run_id=evaluation,
                model_version_id=version_one,
                checkpoint_artifact_id=artifact_one,
                checkpoint_path="must/not/replace.keras",
                confidence="unknown",
                lineage_metadata={"must_not_replace": True},
                summary={"must_not_replace": True},
                connection=connection,
            )
            assert not retried.lineage.created
            assert not retried.finalization.changed
            assert _lineage_row(connection, evaluation) == original

            with pytest.raises(EvaluationTrainingLineageConflictError):
                create_or_confirm_evaluation_training_lineage(
                    training_run_id=train_one,
                    evaluation_run_id=evaluation,
                    model_version_id=version_one_b,
                    checkpoint_artifact_id=artifact_one_b,
                    checkpoint_path=path_one_b,
                    connection=connection,
                )
            with pytest.raises(CheckpointArtifactOwnershipError):
                create_or_confirm_evaluation_training_lineage(
                    training_run_id=train_one,
                    evaluation_run_id=evaluation,
                    model_version_id=version_one,
                    checkpoint_artifact_id=artifact_one_b,
                    checkpoint_path=path_one_b,
                    connection=connection,
                )
            with pytest.raises(EvaluationTrainingLineageConflictError):
                create_or_confirm_evaluation_training_lineage(
                    training_run_id=train_two,
                    evaluation_run_id=evaluation,
                    model_version_id=version_two,
                    checkpoint_artifact_id=artifact_two,
                    checkpoint_path=path_two,
                    connection=connection,
                )

            nested = connection.begin_nested()
            try:
                with pytest.raises(InvalidEvaluationTransitionError):
                    finalize_evaluation_with_lineage(
                        training_run_id=train_one,
                        evaluation_run_id=failed_new,
                        model_version_id=version_one,
                        checkpoint_artifact_id=artifact_one,
                        checkpoint_path=path_one,
                        connection=connection,
                    )
                assert _lineage_row(connection, failed_new) is not None
            finally:
                if nested.is_active:
                    nested.rollback()
            assert _lineage_row(connection, failed_new) is None

            existing = create_or_confirm_evaluation_training_lineage(
                training_run_id=train_one,
                evaluation_run_id=failed_existing,
                model_version_id=version_one,
                checkpoint_artifact_id=artifact_one,
                checkpoint_path=path_one,
                metadata={"existing": True},
                connection=connection,
            )
            created_ids.add(existing.lineage_id)
            before_failed_retry = _lineage_row(connection, failed_existing)
            nested = connection.begin_nested()
            try:
                with pytest.raises(InvalidEvaluationTransitionError):
                    finalize_evaluation_with_lineage(
                        training_run_id=train_one,
                        evaluation_run_id=failed_existing,
                        model_version_id=version_one,
                        checkpoint_artifact_id=artifact_one,
                        checkpoint_path="must/not/replace-existing.keras",
                        lineage_metadata={"must_not_replace": True},
                        connection=connection,
                    )
            finally:
                if nested.is_active:
                    nested.rollback()
            assert _lineage_row(connection, failed_existing) == before_failed_retry

            assert connection.in_transaction()
            assert outer.is_active
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == "20260901_01"
            assert _release_distribution(connection) == initial_release
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
        assert independent.execute(
            text("SELECT COUNT(*) FROM runs WHERE id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            ),
            {"ids": tuple(created_ids)},
        ).scalar_one() == 0
        assert independent.execute(
            text("SELECT COUNT(*) FROM artifacts WHERE id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            ),
            {"ids": tuple(created_ids)},
        ).scalar_one() == 0
        assert independent.execute(
            text("SELECT COUNT(*) FROM model_versions WHERE id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            ),
            {"ids": tuple(created_ids)},
        ).scalar_one() == 0
        assert independent.execute(
            text("SELECT COUNT(*) FROM run_lineage WHERE id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            ),
            {"ids": tuple(created_ids)},
        ).scalar_one() == 0
