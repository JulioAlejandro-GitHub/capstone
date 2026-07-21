import sys
import unittest
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.model_governance.entities import (  # noqa: E402
    CellPrediction,
    DeployedModelVersion,
    DeploymentStatus,
    ModelVersion,
)
from src.model_governance.errors import GovernanceValidationError  # noqa: E402


TRAINING_RUN_ID = "11111111-1111-4111-8111-111111111111"
MODEL_VERSION_ID = "22222222-2222-4222-8222-222222222222"
ARTIFACT_ID = "33333333-3333-4333-8333-333333333333"
DEPLOYMENT_ID = "44444444-4444-4444-8444-444444444444"
INFERENCE_RUN_ID = "55555555-5555-4555-8555-555555555555"
JOB_ID = "66666666-6666-4666-8666-666666666666"


def valid_model_version(**overrides):
    values = {
        "id": MODEL_VERSION_ID,
        "training_run_id": TRAINING_RUN_ID,
        "model_name": "custom_cnn",
        "version_number": 1,
        "checkpoint_artifact_id": ARTIFACT_ID,
        "artifact_path": "outputs/custom_cnn/runs/training/best_model.keras",
        "artifact_sha256": "A" * 64,
        "artifact_size_bytes": 1024,
        "framework": "keras",
        "framework_version": "3.0",
        "class_mapping": {0: "uninfected", 1: "parasitized"},
        "status": "candidate",
        "lineage_status": "resolved",
    }
    values.update(overrides)
    return ModelVersion(**values)


def valid_cell_prediction(**overrides):
    values = {
        "image_analysis_job_id": JOB_ID,
        "inference_run_id": INFERENCE_RUN_ID,
        "deployed_model_version_id": DEPLOYMENT_ID,
        "classifier_model_version_id": MODEL_VERSION_ID,
        "cell_index": 0,
        "bbox_x": 10,
        "bbox_y": 20,
        "bbox_width": 30,
        "bbox_height": 40,
        "probability_parasitized": 0.91,
        "probability_uninfected": 0.09,
        "threshold_used": 0.42,
        "predicted_class": 1,
        "predicted_label": "parasitized",
    }
    values.update(overrides)
    return CellPrediction(**values)


class ModelGovernanceEntityTests(unittest.TestCase):
    def test_creates_valid_immutable_model_version(self):
        version = valid_model_version()

        self.assertEqual(version.version_number, 1)
        self.assertEqual(version.artifact_sha256, "a" * 64)
        self.assertEqual(version.class_mapping["0"], "uninfected")
        self.assertEqual(version.class_mapping["1"], "parasitized")
        with self.assertRaises(FrozenInstanceError):
            version.status = "approved"

    def test_rejects_invalid_model_hash_or_class_mapping(self):
        with self.assertRaisesRegex(GovernanceValidationError, "64 caracteres"):
            valid_model_version(artifact_sha256="not-a-sha")
        with self.assertRaisesRegex(GovernanceValidationError, "0=uninfected"):
            valid_model_version(
                class_mapping={"0": "parasitized", "1": "uninfected"}
            )

    def test_new_deployment_is_pending_and_never_activates_implicitly(self):
        deployment = DeployedModelVersion(
            model_version_id=MODEL_VERSION_ID,
            deployment_name="malaria-cell-classifier",
            environment="test",
            alias="candidate",
            threshold_value=0.42,
        )

        self.assertEqual(deployment.status, DeploymentStatus.PENDING.value)
        self.assertIsNone(deployment.deployed_at)

    def test_active_deployment_requires_explicit_authorization_timestamp(self):
        with self.assertRaisesRegex(GovernanceValidationError, "deployed_at"):
            DeployedModelVersion(
                model_version_id=MODEL_VERSION_ID,
                deployment_name="malaria-cell-classifier",
                environment="test",
                alias="champion",
                threshold_value=0.42,
                label_mapping_snapshot={"0": "uninfected", "1": "parasitized"},
                status="active",
                deployed_by="unit-test",
            )

        deployed_at = datetime.now(UTC)
        with self.assertRaisesRegex(GovernanceValidationError, "deployed_by"):
            DeployedModelVersion(
                model_version_id=MODEL_VERSION_ID,
                deployment_name="malaria-cell-classifier",
                environment="test",
                alias="champion",
                threshold_value=0.42,
                status="active",
                deployed_at=deployed_at,
            )

        deployment = DeployedModelVersion(
            model_version_id=MODEL_VERSION_ID,
            deployment_name="malaria-cell-classifier",
            environment="test",
            alias="champion",
            threshold_value=0.42,
            label_mapping_snapshot={"0": "uninfected", "1": "parasitized"},
            status="active",
            deployed_at=deployed_at,
            deployed_by="unit-test",
        )
        self.assertEqual(deployment.deployed_at, deployed_at)

    def test_rejects_probabilities_outside_zero_one(self):
        for field_name, invalid_value in (
            ("probability_parasitized", -0.01),
            ("probability_parasitized", 1.01),
            ("probability_uninfected", -0.01),
            ("probability_uninfected", 1.01),
            ("threshold_used", -0.01),
            ("threshold_used", 1.01),
        ):
            with self.subTest(field_name=field_name, invalid_value=invalid_value):
                with self.assertRaisesRegex(GovernanceValidationError, "entre 0 y 1"):
                    valid_cell_prediction(**{field_name: invalid_value})

    def test_rejects_unknown_predicted_class(self):
        for invalid_class in (2, -1, True, "1"):
            with self.subTest(predicted_class=invalid_class):
                with self.assertRaisesRegex(
                    GovernanceValidationError,
                    "solo puede ser 0 o 1",
                ):
                    valid_cell_prediction(predicted_class=invalid_class)

    def test_rejects_class_label_mismatch(self):
        with self.assertRaisesRegex(GovernanceValidationError, "debe coincidir"):
            valid_cell_prediction(predicted_class=0, predicted_label="parasitized")

    def test_creates_valid_cell_prediction_with_required_relationships(self):
        prediction = valid_cell_prediction()

        self.assertEqual(prediction.model_version_id, MODEL_VERSION_ID)
        self.assertEqual(prediction.deployed_model_version_id, DEPLOYMENT_ID)
        self.assertEqual(prediction.inference_run_id, INFERENCE_RUN_ID)
        self.assertEqual(prediction.image_analysis_job_id, JOB_ID)
        self.assertEqual(prediction.predicted_label, "parasitized")


if __name__ == "__main__":
    unittest.main()
