import sys
import unittest
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.model_governance import repository  # noqa: E402


TRAINING_RUN_ID = "11111111-1111-4111-8111-111111111111"
MODEL_VERSION_ID = "22222222-2222-4222-8222-222222222222"
ARTIFACT_ID = "33333333-3333-4333-8333-333333333333"
DEPLOYMENT_ID = "44444444-4444-4444-8444-444444444444"
INFERENCE_RUN_ID = "55555555-5555-4555-8555-555555555555"
JOB_ID = "66666666-6666-4666-8666-666666666666"
PREDICTION_ID = "77777777-7777-4777-8777-777777777777"
SOURCE_IMAGE_ID = "88888888-8888-4888-8888-888888888888"


class FakeResult:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows

    def mappings(self):
        return self

    def one_or_none(self):
        return self.row

    def all(self):
        if self.rows is not None:
            return self.rows
        return [] if self.row is None else [self.row]


class QueueConnection:
    def __init__(self, *results):
        self.results = list(results)
        self.calls = []

    def execute(self, statement, params):
        self.calls.append((str(statement), params))
        if not self.results:
            raise AssertionError("La prueba no configuró un resultado SQL.")
        result = self.results.pop(0)
        return result if isinstance(result, FakeResult) else FakeResult(row=result)


class ModelGovernanceRepositoryTests(unittest.TestCase):
    def test_create_model_version_uses_registered_artifact_identity(self):
        artifact_path = "outputs/custom_cnn/runs/training/best_model.keras"
        checksum = "a" * 64
        connection = QueueConnection(
            {
                "training_run_id": TRAINING_RUN_ID,
                "run_type": "training",
                "model_id": None,
                "checkpoint_artifact_id": ARTIFACT_ID,
                "artifact_run_id": TRAINING_RUN_ID,
                "artifact_path": artifact_path,
                "artifact_uri": "artifact://custom-cnn/1",
                "artifact_sha256": checksum,
                "artifact_size_bytes": 1024,
            },
            None,
            {
                "id": MODEL_VERSION_ID,
                "training_run_id": TRAINING_RUN_ID,
                "model_name": "custom_cnn",
                "version_number": 1,
                "checkpoint_artifact_id": ARTIFACT_ID,
                "checkpoint_path": artifact_path,
                "artifact_uri": "artifact://custom-cnn/1",
                "artifact_sha256": checksum,
                "artifact_size_bytes": 1024,
                "artifact_hash_reuse_justification": None,
                "framework": "keras",
                "framework_version": "3.0",
                "preprocessing_profile_snapshot": {},
                "class_mapping": {"0": "uninfected", "1": "parasitized"},
                "input_signature": {},
                "output_signature": {},
                "status": "candidate",
                "lineage_status": "resolved",
                "created_at": datetime.now(UTC),
                "validated_at": None,
                "approved_at": None,
                "retired_at": None,
                "metadata": {},
            },
        )

        version = repository.create_model_version(
            training_run_id=TRAINING_RUN_ID,
            model_name="custom_cnn",
            version_number=1,
            checkpoint_artifact_id=ARTIFACT_ID,
            artifact_path=artifact_path,
            artifact_uri="artifact://custom-cnn/1",
            artifact_sha256=checksum,
            artifact_size_bytes=1024,
            framework="keras",
            framework_version="3.0",
            status="candidate",
            connection_or_session=connection,
        )

        self.assertEqual(version.id, MODEL_VERSION_ID)
        self.assertEqual(len(connection.calls), 3)
        insert_sql, insert_params = connection.calls[2]
        self.assertIn("INSERT INTO model_versions", insert_sql)
        self.assertEqual(insert_params["checkpoint_path"], artifact_path)
        self.assertEqual(insert_params["checkpoint_artifact_id"], ARTIFACT_ID)

    def test_create_deployment_defaults_to_pending(self):
        now = datetime.now(UTC)
        checksum = "a" * 64
        connection = QueueConnection(
            {
                "id": MODEL_VERSION_ID,
                "training_run_id": TRAINING_RUN_ID,
                "checkpoint_artifact_id": ARTIFACT_ID,
                "artifact_sha256": checksum,
                "artifact_size_bytes": 1024,
                "preprocessing_profile_snapshot": {"image_size": [128, 128]},
                "class_mapping": {"0": "uninfected", "1": "parasitized"},
                "status": "approved",
                "lineage_status": "resolved",
            },
            {
                "id": DEPLOYMENT_ID,
                "model_version_id": MODEL_VERSION_ID,
                "checkpoint_artifact_id": ARTIFACT_ID,
                "threshold_calibration_id": None,
                "deployment_name": "malaria-cell-classifier",
                "environment": "test",
                "alias": "candidate",
                "artifact_sha256": checksum,
                "artifact_size_bytes": 1024,
                "threshold_value": Decimal("0.42"),
                "threshold_profile_snapshot": {},
                "preprocessing_profile_snapshot": {"image_size": [128, 128]},
                "image_quality_policy_snapshot": {},
                "label_mapping_snapshot": {
                    "0": "uninfected",
                    "1": "parasitized",
                },
                "positive_label": "parasitized",
                "score_name": "probability_parasitized",
                "status": "pending",
                "supersedes_deployment_id": None,
                "rollback_of_deployment_id": None,
                "deployed_at": None,
                "retired_at": None,
                "deployed_by": None,
                "retired_by": None,
                "deployment_reason": None,
                "retirement_reason": None,
                "created_at": now,
                "metadata": {},
            },
        )

        deployment = repository.create_deployed_model_version(
            model_version_id=MODEL_VERSION_ID,
            deployment_name="malaria-cell-classifier",
            environment="test",
            alias="candidate",
            threshold_value=0.42,
            connection_or_session=connection,
        )

        self.assertEqual(deployment.status, "pending")
        self.assertIsNone(deployment.deployed_at)
        self.assertEqual(connection.calls[1][1]["status"], "pending")

    def test_create_inference_run_inserts_run_and_bridge_on_one_connection(self):
        now = datetime.now(UTC)
        connection = QueueConnection(
            {
                "deployed_model_version_id": DEPLOYMENT_ID,
                "model_version_id": MODEL_VERSION_ID,
                "deployment_status": "active",
                "threshold_value": Decimal("0.42"),
                "model_id": None,
            },
            {
                "id": INFERENCE_RUN_ID,
                "backend_version": "api-1",
                "pipeline_version": "pipeline-1",
                "started_at": now,
                "finished_at": None,
                "status": "started",
                "configuration": {"batch_size": 1},
                "metadata": {},
                "error_message": None,
            },
            {"id": "99999999-9999-4999-8999-999999999999"},
        )

        inference = repository.create_inference_run(
            deployed_model_version_id=DEPLOYMENT_ID,
            backend_version="api-1",
            pipeline_version="pipeline-1",
            configuration={"batch_size": 1},
            connection_or_session=connection,
        )

        self.assertEqual(inference.id, INFERENCE_RUN_ID)
        self.assertEqual(inference.model_version_id, MODEL_VERSION_ID)
        self.assertEqual(len(connection.calls), 3)
        self.assertIn("INSERT INTO runs", connection.calls[1][0])
        self.assertIn("INSERT INTO run_model_deployments", connection.calls[2][0])
        self.assertEqual(connection.calls[2][1]["run_id"], INFERENCE_RUN_ID)

    def test_create_image_job_returns_existing_idempotent_row(self):
        now = datetime.now(UTC)
        existing_job = {
            "id": JOB_ID,
            "inference_run_id": INFERENCE_RUN_ID,
            "deployed_model_version_id": DEPLOYMENT_ID,
            "model_version_id": MODEL_VERSION_ID,
            "input_artifact_id": ARTIFACT_ID,
            "source_image_id": None,
            "idempotency_key": "request-1",
            "sample_id": None,
            "patient_id": None,
            "slide_id": None,
            "status": "pending",
            "quality_status": "not_assessed",
            "quality_metrics": {},
            "threshold_used": Decimal("0.42"),
            "threshold_source": "deployment_snapshot",
            "summary": {},
            "total_cells": None,
            "positive_cells": None,
            "started_at": None,
            "completed_at": None,
            "error_message": None,
            "created_at": now,
            "updated_at": now,
            "metadata": {},
        }
        connection = QueueConnection(
            {
                "inference_run_id": INFERENCE_RUN_ID,
                "run_type": "inference",
                "inference_status": "started",
                "deployed_model_version_id": DEPLOYMENT_ID,
                "model_version_id": MODEL_VERSION_ID,
                "deployment_status": "active",
                "threshold_value": Decimal("0.42"),
            },
            None,
            existing_job,
        )

        job = repository.create_image_analysis_job(
            inference_run_id=INFERENCE_RUN_ID,
            deployed_model_version_id=DEPLOYMENT_ID,
            input_artifact_id=ARTIFACT_ID,
            idempotency_key="request-1",
            connection_or_session=connection,
        )

        self.assertEqual(job.id, JOB_ID)
        self.assertEqual(len(connection.calls), 3)
        self.assertIn("ON CONFLICT", connection.calls[1][0])

    def test_create_cell_prediction_writes_canonical_predictions_table(self):
        now = datetime.now(UTC)
        connection = QueueConnection(
            {
                "image_analysis_job_id": JOB_ID,
                "inference_run_id": INFERENCE_RUN_ID,
                "deployed_model_version_id": DEPLOYMENT_ID,
                "model_version_id": MODEL_VERSION_ID,
                "source_image_id": SOURCE_IMAGE_ID,
                "threshold_used": Decimal("0.42"),
                "job_status": "running",
                "inference_status": "started",
                "run_type": "inference",
                "source_dataset_id": None,
            },
            {
                "id": PREDICTION_ID,
                "image_analysis_job_id": JOB_ID,
                "inference_run_id": INFERENCE_RUN_ID,
                "deployed_model_version_id": DEPLOYMENT_ID,
                "model_version_id": MODEL_VERSION_ID,
                "classifier_model_version_id": MODEL_VERSION_ID,
                "detector_model_version_id": None,
                "cell_index": 0,
                "source_image_id": SOURCE_IMAGE_ID,
                "bbox_x": 10,
                "bbox_y": 20,
                "bbox_width": 30,
                "bbox_height": 40,
                "crop_artifact_id": None,
                "probability_parasitized": Decimal("0.91"),
                "probability_uninfected": Decimal("0.09"),
                "threshold_used": Decimal("0.42"),
                "predicted_class": 1,
                "predicted_label": "parasitized",
                "confidence_level": "high",
                "quality_status": "passed",
                "explanation_artifact_id": None,
                "review_status": "unreviewed",
                "reviewed_label": None,
                "reviewed_by": None,
                "reviewed_at": None,
                "created_at": now,
                "metadata": {},
            },
        )

        prediction = repository.create_cell_prediction(
            image_analysis_job_id=JOB_ID,
            classifier_model_version_id=MODEL_VERSION_ID,
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

        self.assertEqual(prediction.id, PREDICTION_ID)
        insert_sql, insert_params = connection.calls[1]
        self.assertIn("INSERT INTO predictions", insert_sql)
        self.assertIn("'cell'", insert_sql)
        self.assertEqual(insert_params["model_version_id"], MODEL_VERSION_ID)
        self.assertEqual(
            insert_params["model_version_id"],
            insert_params["classifier_model_version_id"],
        )

    def test_get_lineage_returns_the_complete_governed_path(self):
        connection = QueueConnection(
            FakeResult(
                rows=[
                    {
                        "training_run_id": TRAINING_RUN_ID,
                        "model_version_id": MODEL_VERSION_ID,
                        "checkpoint_artifact_id": ARTIFACT_ID,
                        "model_name": "custom_cnn",
                        "version_number": 1,
                        "artifact_path": "outputs/custom_cnn/best_model.keras",
                        "artifact_sha256": "a" * 64,
                        "model_version_status": "approved",
                        "deployed_model_version_id": DEPLOYMENT_ID,
                        "deployment_name": "malaria-cell-classifier",
                        "environment": "test",
                        "alias": "champion",
                        "deployment_status": "active",
                        "inference_run_id": INFERENCE_RUN_ID,
                        "inference_status": "started",
                        "image_analysis_job_id": JOB_ID,
                        "image_job_status": "running",
                        "prediction_id": PREDICTION_ID,
                        "derived_run_id": None,
                        "derived_run_type": None,
                        "relationship_type": None,
                    }
                ]
            )
        )

        paths = repository.get_lineage(
            prediction_id=PREDICTION_ID,
            connection_or_session=connection,
        )

        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].training_run_id, TRAINING_RUN_ID)
        self.assertEqual(paths[0].model_version_id, MODEL_VERSION_ID)
        self.assertEqual(paths[0].deployed_model_version_id, DEPLOYMENT_ID)
        self.assertEqual(paths[0].inference_run_id, INFERENCE_RUN_ID)
        self.assertEqual(paths[0].image_analysis_job_id, JOB_ID)
        self.assertEqual(paths[0].prediction_id, PREDICTION_ID)
        lineage_sql, params = connection.calls[0]
        self.assertIn("LEFT JOIN run_lineage", lineage_sql)
        self.assertIn("prediction.id = :anchor_id", lineage_sql)
        self.assertEqual(params["anchor_id"], PREDICTION_ID)


if __name__ == "__main__":
    unittest.main()
