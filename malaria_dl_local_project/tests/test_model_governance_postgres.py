"""Opt-in PostgreSQL 17 integration tests for governed model lineage.

This module never uses DATABASE_URL implicitly.  It only mutates a database
whose explicit name looks disposable and when the separate write opt-in is set.
"""

from __future__ import annotations

import os
import re
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import init_db  # noqa: E402
from src.db import normalize_database_url  # noqa: E402
from src.model_governance import repository  # noqa: E402
from src.model_governance.errors import (  # noqa: E402
    GovernanceConflictError,
    GovernanceValidationError,
)


TEST_DATABASE_URL = os.getenv("MODEL_GOVERNANCE_TEST_DATABASE_URL", "").strip()
WRITE_OPT_IN = os.getenv("MODEL_GOVERNANCE_TEST_ALLOW_SCHEMA_CHANGES") == "1"
DISPOSABLE_DATABASE_PATTERN = re.compile(
    r"(?:^test(?:_|$)|(?:^|_)test(?:_|$)|^codex(?:_|$)|(?:^|_)codex(?:_|$))",
    re.IGNORECASE,
)


@unittest.skipUnless(
    TEST_DATABASE_URL and WRITE_OPT_IN,
    "Requiere MODEL_GOVERNANCE_TEST_DATABASE_URL y "
    "MODEL_GOVERNANCE_TEST_ALLOW_SCHEMA_CHANGES=1.",
)
class ModelGovernancePostgres17IntegrationTests(unittest.TestCase):
    """Exercise migrations and the complete lineage in a disposable database."""

    @classmethod
    def setUpClass(cls):
        normalized_url = normalize_database_url(TEST_DATABASE_URL)
        parsed_url = make_url(normalized_url)
        database_name = parsed_url.database or ""
        if database_name in {
            "postgres",
            "template0",
            "template1",
            "malaria_experiments",
        } or not DISPOSABLE_DATABASE_PATTERN.search(database_name):
            raise RuntimeError(
                "La prueba solo puede modificar una base desechable cuyo nombre "
                "contenga 'test' o 'codex'; nunca malaria_experiments."
            )

        cls.engine = create_engine(normalized_url, future=True, pool_pre_ping=True)
        cls.addClassCleanup(cls.engine.dispose)
        with cls.engine.connect() as connection:
            actual_database = connection.execute(
                text("SELECT current_database()")
            ).scalar_one()
            server_version = int(
                connection.execute(
                    text("SELECT current_setting('server_version_num')")
                ).scalar_one()
            )
        if actual_database != database_name:
            cls.engine.dispose()
            raise RuntimeError(
                "La conexión no abrió la base desechable indicada en la URL."
            )
        if not 170000 <= server_version < 180000:
            cls.engine.dispose()
            raise unittest.SkipTest(
                f"Esta integración exige PostgreSQL 17; recibió {server_version}."
            )

        # Apply every numbered migration once, then prove the checksum ledger
        # makes a second runner pass a no-op.
        with cls.engine.begin() as connection:
            init_db.ensure_migration_ledger(connection)
            init_db.baseline_legacy_migrations(connection)
            for sql_path in init_db.SQL_FILES:
                init_db.execute_pending_sql_file(connection, sql_path)

        with cls.engine.begin() as connection:
            second_pass = [
                init_db.execute_pending_sql_file(connection, sql_path)
                for sql_path in init_db.SQL_FILES
            ]
            recorded = connection.execute(
                text("SELECT COUNT(*) FROM schema_migrations")
            ).scalar_one()
        if any(second_pass) or recorded != len(init_db.SQL_FILES):
            cls.engine.dispose()
            raise AssertionError(
                "La reejecución no fue idempotente o el ledger quedó incompleto."
            )

    def test_full_lineage_constraints_and_delete_restriction(self):
        checksum = "a" * 64
        now = datetime.now(UTC)

        with self.engine.connect() as connection:
            transaction = connection.begin()
            try:
                model_id = connection.execute(
                    text(
                        """
                        INSERT INTO models (name, model_type, framework)
                        VALUES ('governance_integration_model', 'classifier', 'keras')
                        RETURNING id
                        """
                    )
                ).scalar_one()
                training_run_id = connection.execute(
                    text(
                        """
                        INSERT INTO runs (
                            model_id, run_name, run_type, status, started_at
                        )
                        VALUES (
                            :model_id, 'governance-integration-training',
                            'training', 'completed', :started_at
                        )
                        RETURNING id
                        """
                    ),
                    {"model_id": model_id, "started_at": now},
                ).scalar_one()
                artifact_path = (
                    f"test-artifacts/{training_run_id}/best_model.keras"
                )
                checkpoint_artifact_id = connection.execute(
                    text(
                        """
                        INSERT INTO artifacts (
                            run_id, artifact_type, name, path,
                            file_size_bytes, checksum, artifact_status
                        )
                        VALUES (
                            :run_id, 'model_checkpoint', 'best_model.keras',
                            :path, 4096, :checksum, 'available'
                        )
                        RETURNING id
                        """
                    ),
                    {
                        "run_id": training_run_id,
                        "path": artifact_path,
                        "checksum": checksum,
                    },
                ).scalar_one()

                model_version = repository.create_model_version(
                    training_run_id=training_run_id,
                    model_name="governance_integration_model",
                    version_number=1,
                    checkpoint_artifact_id=checkpoint_artifact_id,
                    artifact_path=artifact_path,
                    artifact_sha256=checksum,
                    artifact_size_bytes=4096,
                    framework="keras",
                    framework_version="3",
                    status="approved",
                    lineage_status="resolved",
                    approved_at=now,
                    connection_or_session=connection,
                )

                pending_deployment = repository.create_deployed_model_version(
                    model_version_id=model_version.id,
                    deployment_name="malaria-cell-classifier",
                    environment="integration-test",
                    alias="candidate",
                    threshold_value=0.42,
                    connection_or_session=connection,
                )
                self.assertEqual(pending_deployment.status, "pending")
                self.assertIsNone(pending_deployment.deployed_at)

                active_deployment = repository.create_deployed_model_version(
                    model_version_id=model_version.id,
                    deployment_name="malaria-cell-classifier",
                    environment="integration-test",
                    alias="champion",
                    threshold_value=0.42,
                    status="active",
                    deployed_at=now,
                    deployed_by="postgres-integration-test",
                    connection_or_session=connection,
                )

                with self.assertRaises(GovernanceConflictError):
                    with connection.begin_nested():
                        repository.create_deployed_model_version(
                            model_version_id=model_version.id,
                            deployment_name="malaria-cell-classifier",
                            environment="integration-test",
                            alias="champion",
                            threshold_value=0.42,
                            status="active",
                            deployed_at=now,
                            deployed_by="duplicate-integration-test",
                            connection_or_session=connection,
                        )

                inference_run = repository.create_inference_run(
                    deployed_model_version_id=active_deployment.id,
                    backend_version="integration-api-1",
                    pipeline_version="integration-pipeline-1",
                    connection_or_session=connection,
                )
                image_job = repository.create_image_analysis_job(
                    inference_run_id=inference_run.id,
                    deployed_model_version_id=active_deployment.id,
                    input_artifact_id=checkpoint_artifact_id,
                    idempotency_key="governance-integration-image-1",
                    connection_or_session=connection,
                )
                prediction = repository.create_cell_prediction(
                    image_analysis_job_id=image_job.id,
                    classifier_model_version_id=model_version.id,
                    cell_index=0,
                    bbox_x=10,
                    bbox_y=20,
                    bbox_width=30,
                    bbox_height=40,
                    probability_parasitized=0.91,
                    probability_uninfected=0.09,
                    threshold_used=0.42,
                    predicted_class=1,
                    predicted_label="parasitized",
                    confidence_level="high",
                    quality_status="passed",
                    connection_or_session=connection,
                )

                lineage = repository.get_lineage(
                    prediction_id=prediction.id,
                    connection_or_session=connection,
                )
                self.assertEqual(len(lineage), 1)
                self.assertEqual(lineage[0].training_run_id, str(training_run_id))
                self.assertEqual(lineage[0].model_version_id, model_version.id)
                self.assertEqual(
                    lineage[0].deployed_model_version_id,
                    active_deployment.id,
                )
                self.assertEqual(lineage[0].inference_run_id, inference_run.id)
                self.assertEqual(lineage[0].image_analysis_job_id, image_job.id)
                self.assertEqual(lineage[0].prediction_id, prediction.id)

                relation_counts = connection.execute(
                    text(
                        """
                        SELECT
                            (SELECT COUNT(*) FROM model_versions
                             WHERE id = :model_version_id) AS versions,
                            (SELECT COUNT(*) FROM run_model_deployments
                             WHERE run_id = :inference_run_id) AS bindings,
                            (SELECT COUNT(*) FROM image_analysis_jobs
                             WHERE id = :image_job_id) AS jobs,
                            (SELECT COUNT(*) FROM cell_predictions
                             WHERE id = :prediction_id) AS cells
                        """
                    ),
                    {
                        "model_version_id": model_version.id,
                        "inference_run_id": inference_run.id,
                        "image_job_id": image_job.id,
                        "prediction_id": prediction.id,
                    },
                ).mappings().one()
                self.assertEqual(dict(relation_counts), {
                    "versions": 1,
                    "bindings": 1,
                    "jobs": 1,
                    "cells": 1,
                })

                invalid_prediction = {
                    "image_analysis_job_id": image_job.id,
                    "classifier_model_version_id": model_version.id,
                    "cell_index": 1,
                    "bbox_x": 0,
                    "bbox_y": 0,
                    "bbox_width": 1,
                    "bbox_height": 1,
                    "probability_parasitized": 1.01,
                    "probability_uninfected": 0,
                    "threshold_used": 0.42,
                    "predicted_class": 1,
                    "predicted_label": "parasitized",
                    "connection_or_session": connection,
                }
                with self.assertRaises(GovernanceValidationError):
                    repository.create_cell_prediction(**invalid_prediction)
                invalid_prediction.update(
                    probability_parasitized=0.5,
                    probability_uninfected=0.5,
                    predicted_class=2,
                )
                with self.assertRaises(GovernanceValidationError):
                    repository.create_cell_prediction(**invalid_prediction)

                # Exercise PostgreSQL checks independently from Python validation.
                with self.assertRaises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(
                            text(
                                """
                                UPDATE predictions
                                SET probability_parasitized = 1.01
                                WHERE id = :prediction_id
                                """
                            ),
                            {"prediction_id": prediction.id},
                        )
                with self.assertRaises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(
                            text(
                                """
                                UPDATE predictions
                                SET predicted_class = 2
                                WHERE id = :prediction_id
                                """
                            ),
                            {"prediction_id": prediction.id},
                        )

                with self.assertRaises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(
                            text("DELETE FROM runs WHERE id = :training_run_id"),
                            {"training_run_id": training_run_id},
                        )
                remaining = connection.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM model_versions
                        WHERE id = :model_version_id
                          AND training_run_id = :training_run_id
                        """
                    ),
                    {
                        "model_version_id": model_version.id,
                        "training_run_id": training_run_id,
                    },
                ).scalar_one()
                self.assertEqual(remaining, 1)
            finally:
                transaction.rollback()


if __name__ == "__main__":
    unittest.main()
