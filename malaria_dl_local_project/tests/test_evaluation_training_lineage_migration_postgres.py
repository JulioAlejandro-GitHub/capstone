from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.malaria_dl.persistence.database import get_engine


pytestmark = pytest.mark.requires_docker_postgres

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
INDEX_NAME = "uq_run_lineage_single_evaluation_training_parent"


def _config(connection):
    config = Config(str(REPOSITORY_ROOT / "alembic.ini"))
    config.set_main_option(
        "script_location", str(REPOSITORY_ROOT / "alembic")
    )
    config.attributes["connection"] = connection
    return config


def _fingerprint(connection, table):
    if table not in {"runs", "artifacts", "model_versions", "run_lineage"}:
        raise AssertionError(f"unexpected table: {table}")
    return connection.execute(
        text(
            f"""
            SELECT COUNT(*), md5(COALESCE(
                string_agg(md5(row_to_json(item)::text), '' ORDER BY item.id), ''
            ))
            FROM {table} AS item
            """
        )
    ).one()


def _index_count(connection):
    return connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM pg_indexes
            WHERE schemaname='public' AND indexname=:index_name
            """
        ),
        {"index_name": INDEX_NAME},
    ).scalar_one()


def _coherent_parent(connection):
    training_id, artifact_id, version_id = uuid4(), uuid4(), uuid4()
    path = f"rollback-only/{artifact_id}.keras"
    connection.execute(
        text(
            """
            INSERT INTO runs (id, run_name, run_type, status, started_at, metadata)
            VALUES (:id, :name, 'training', 'completed', CURRENT_TIMESTAMP, '{}'::jsonb)
            """
        ),
        {"id": training_id, "name": f"rollback-only:training:{training_id}"},
    )
    connection.execute(
        text(
            """
            INSERT INTO artifacts (id, run_id, artifact_type, path, metadata)
            VALUES (:id, :run_id, 'checkpoint', :path, '{}'::jsonb)
            """
        ),
        {"id": artifact_id, "run_id": training_id, "path": path},
    )
    connection.execute(
        text(
            """
            INSERT INTO model_versions (
                id, training_run_id, checkpoint_artifact_id, checkpoint_path,
                status, lineage_status
            )
            VALUES (
                :id, :training_run_id, :artifact_id, :path,
                'discovered', 'resolved'
            )
            """
        ),
        {
            "id": version_id,
            "training_run_id": training_id,
            "artifact_id": artifact_id,
            "path": path,
        },
    )
    return training_id, version_id, artifact_id, path


def _evaluation(connection):
    evaluation_id = uuid4()
    connection.execute(
        text(
            """
            INSERT INTO runs (id, run_name, run_type, status, started_at, metadata)
            VALUES (:id, :name, 'evaluation', 'started', CURRENT_TIMESTAMP, '{}'::jsonb)
            """
        ),
        {"id": evaluation_id, "name": f"rollback-only:evaluation:{evaluation_id}"},
    )
    return evaluation_id


def _insert_lineage(connection, parent, child, version, artifact, path):
    return connection.execute(
        text(
            """
            INSERT INTO run_lineage (
                parent_run_id, child_run_id, relationship_type,
                model_version_id, checkpoint_artifact_id, checkpoint_path,
                confidence, metadata
            )
            VALUES (
                :parent, :child, 'evaluates_checkpoint_from',
                :version, :artifact, :path, 'explicit', '{}'::jsonb
            )
            RETURNING id
            """
        ),
        {
            "parent": parent,
            "child": child,
            "version": version,
            "artifact": artifact,
            "path": path,
        },
    ).scalar_one()


def test_migration_precheck_rejects_existing_duplicate_children_and_rolls_back():
    engine = get_engine()
    tables = ("runs", "artifacts", "model_versions", "run_lineage")
    with engine.connect() as connection:
        outer = connection.begin()
        initial = {table: _fingerprint(connection, table) for table in tables}
        try:
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == "20260829_01"
            assert _index_count(connection) == 0
            evaluation_id = _evaluation(connection)
            first = _coherent_parent(connection)
            second = _coherent_parent(connection)
            _insert_lineage(connection, first[0], evaluation_id, *first[1:])
            _insert_lineage(connection, second[0], evaluation_id, *second[1:])

            with pytest.raises(RuntimeError, match="duplicate direct lineages"):
                command.upgrade(_config(connection), "head")

            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == "20260829_01"
            assert _index_count(connection) == 0
            assert outer.is_active
        finally:
            if outer.is_active:
                outer.rollback()

    with engine.connect() as independent:
        assert independent.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == "20260829_01"
        assert _index_count(independent) == 0
        assert {
            table: _fingerprint(independent, table) for table in tables
        } == initial


def test_migration_applies_in_outer_transaction_and_index_blocks_second_parent():
    engine = get_engine()
    tables = ("runs", "artifacts", "model_versions", "run_lineage")
    with engine.connect() as connection:
        outer = connection.begin()
        initial = {table: _fingerprint(connection, table) for table in tables}
        try:
            command.upgrade(_config(connection), "head")
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == "20260901_01"
            definition = connection.execute(
                text(
                    """
                    SELECT indexdef FROM pg_indexes
                    WHERE schemaname='public' AND indexname=:index_name
                    """
                ),
                {"index_name": INDEX_NAME},
            ).scalar_one()
            assert "UNIQUE INDEX" in definition
            assert "child_run_id" in definition
            assert "evaluates_checkpoint_from" in definition

            evaluation_id = _evaluation(connection)
            first = _coherent_parent(connection)
            second = _coherent_parent(connection)
            _insert_lineage(connection, first[0], evaluation_id, *first[1:])
            nested = connection.begin_nested()
            try:
                with pytest.raises(IntegrityError) as caught:
                    _insert_lineage(
                        connection, second[0], evaluation_id, *second[1:]
                    )
                assert caught.value.orig.diag.constraint_name == INDEX_NAME
            finally:
                if nested.is_active:
                    nested.rollback()

            assert connection.execute(
                text(
                    """
                    SELECT COUNT(*) FROM run_lineage
                    WHERE child_run_id=:evaluation_id
                      AND relationship_type='evaluates_checkpoint_from'
                    """
                ),
                {"evaluation_id": evaluation_id},
            ).scalar_one() == 1
            assert outer.is_active
        finally:
            if outer.is_active:
                outer.rollback()

    with engine.connect() as independent:
        assert independent.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == "20260829_01"
        assert _index_count(independent) == 0
        assert {
            table: _fingerprint(independent, table) for table in tables
        } == initial
