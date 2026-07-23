import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4


PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from src.prepare_model_release_service import (  # noqa: E402
    EXPECTED_CLASS_MAPPING,
    PrepareModelReleaseService,
    PromotionContext,
)


class DeploymentValidator:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def validate_activation(self, model_version_id, threshold_id):
        self.calls.append((model_version_id, threshold_id))
        if self.error:
            raise self.error
        return {}, {}


class FixtureService(PrepareModelReleaseService):
    def __init__(self, contexts, deployment_service=None):
        self.contexts = list(contexts)
        self.created = 0
        self.audits = []
        self.deployment_service = deployment_service or DeploymentValidator()

    def _load_context(self, training_run_id, *, validate_model):
        context = self.contexts.pop(0) if len(self.contexts) > 1 else self.contexts[0]
        context.model_loadable = context.model_loadable and True
        return context

    def _create_model_version(self, context):
        self.created += 1
        return str(uuid4())

    def _audit(self, **kwargs):
        self.audits.append(kwargs)


class PrepareModelReleaseServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.run_id = str(uuid4())
        self.artifact_id = str(uuid4())
        self.model_version_id = str(uuid4())
        self.evaluation_id = str(uuid4())
        self.checkpoint_path = (
            Path(self.temp.name) / "outputs" / "custom_cnn" / "runs"
            / self.run_id / "best_model.keras"
        )
        self.checkpoint_path.parent.mkdir(parents=True)
        self.checkpoint_path.write_bytes(b"governed-model")
        self.checksum = hashlib.sha256(b"governed-model").hexdigest()

    def tearDown(self):
        self.temp.cleanup()

    def context(self, **changes):
        value = PromotionContext(
            training_run_id=self.run_id,
            training_status="completed",
            run_type="training",
            model_name="custom_cnn",
            checkpoint={
                "checkpoint_artifact_id": self.artifact_id,
                "path": str(self.checkpoint_path),
                "artifact_sha256": self.checksum,
                "artifact_size_bytes": self.checkpoint_path.stat().st_size,
                "artifact_status": "available",
            },
            preprocessing={"mode": "rescale_0_1"},
            class_mapping=dict(EXPECTED_CLASS_MAPPING),
            input_signature={"shape": [None, 200, 200, 3]},
            output_signature={"shape": [None, 1]},
            framework="keras",
        )
        for key, item in changes.items():
            setattr(value, key, item)
        return value

    def version(self, status="candidate", **changes):
        value = {
            "id": self.model_version_id,
            "training_run_id": self.run_id,
            "checkpoint_artifact_id": self.artifact_id,
            "artifact_sha256": self.checksum,
            "status": status,
            "lineage_status": "resolved",
        }
        value.update(changes)
        return value

    @staticmethod
    def codes(response):
        return {item["code"] for item in response["blocking_reasons"]}

    def test_missing_run(self):
        response = FixtureService(
            [PromotionContext(training_run_id=self.run_id, exists=False)]
        ).promotion_status(self.run_id)
        self.assertIn("TRAINING_RUN_NOT_FOUND", self.codes(response))

    def test_evaluation_run_is_not_training(self):
        response = FixtureService(
            [self.context(run_type="evaluation")]
        ).promotion_status(self.run_id)
        self.assertIn("INVALID_RUN_TYPE", self.codes(response))

    def test_training_must_be_completed(self):
        response = FixtureService(
            [self.context(training_status="running")]
        ).promotion_status(self.run_id)
        self.assertIn("TRAINING_NOT_COMPLETED", self.codes(response))

    def test_checkpoint_is_required(self):
        response = FixtureService(
            [self.context(checkpoint=None)]
        ).promotion_status(self.run_id)
        self.assertIn("CHECKPOINT_NOT_FOUND", self.codes(response))

    def test_generic_legacy_checkpoint_is_rejected(self):
        generic = Path(self.temp.name) / "outputs" / "custom_cnn" / "best_model.keras"
        generic.parent.mkdir(parents=True, exist_ok=True)
        generic.write_bytes(b"governed-model")
        checkpoint = dict(self.context().checkpoint)
        checkpoint["path"] = str(generic)
        response = FixtureService(
            [self.context(checkpoint=checkpoint)]
        ).promotion_status(self.run_id)
        self.assertIn("UNRESOLVED_LINEAGE", self.codes(response))

    def test_wrong_sha256_is_rejected(self):
        checkpoint = dict(self.context().checkpoint)
        checkpoint["artifact_sha256"] = "0" * 64
        response = FixtureService(
            [self.context(checkpoint=checkpoint)]
        ).promotion_status(self.run_id)
        self.assertIn("CHECKPOINT_HASH_MISMATCH", self.codes(response))

    def test_unloadable_model_is_rejected(self):
        response = FixtureService(
            [self.context(model_loadable=False)]
        ).promotion_status(self.run_id)
        self.assertIn("MODEL_NOT_LOADABLE", self.codes(response))

    def test_preprocessing_is_required(self):
        response = FixtureService(
            [self.context(preprocessing={})]
        ).promotion_status(self.run_id)
        self.assertIn("PREPROCESSING_REQUIRED", self.codes(response))

    def test_resolved_lineage_can_release(self):
        response = FixtureService([self.context()]).promotion_status(self.run_id)
        self.assertTrue(response["can_release"])
        self.assertEqual(response["next_action"], "prepare_release")

    def test_existing_candidate_is_reused(self):
        context = self.context(model_version=self.version(), versions_count=1)
        service = FixtureService([context])
        response = service.prepare_release(self.run_id, requester="tester")
        self.assertEqual(response["model_version_id"], self.model_version_id)
        self.assertEqual(service.created, 0)
        self.assertEqual(response["next_action"], "review_model_version")

    def test_inconsistent_source_training_run_is_rejected(self):
        other_training = str(uuid4())
        context = self.context(
            model_version=self.version(training_run_id=other_training),
            versions_count=1,
        )
        response = FixtureService([context]).promotion_status(self.run_id)
        self.assertIn("UNRESOLVED_LINEAGE", self.codes(response))

    def test_creation_is_idempotent_at_service_boundary(self):
        initial = self.context()
        created = self.context(
            model_version=self.version(), versions_count=1
        )
        service = FixtureService([initial, created])
        first = service.prepare_release(self.run_id, requester="tester")
        service.contexts = [created]
        second = service.prepare_release(self.run_id, requester="tester")
        self.assertEqual(service.created, 1)
        self.assertEqual(first["model_version_id"], second["model_version_id"])

    def test_evaluation_and_explainability_are_returned(self):
        evaluation = {
            "evaluation_run_id": self.evaluation_id,
            "status": "completed",
            "split_name": "test",
            "threshold_used": 0.42,
            "prediction_collapse": {"collapsed": False},
        }
        explain_id = str(uuid4())
        response = FixtureService(
            [
                self.context(
                    model_version=self.version("approved"),
                    versions_count=1,
                    evaluation=evaluation,
                    explainability_run_ids=[explain_id],
                    threshold={
                        "id": str(uuid4()),
                        "value": 0.42,
                        "source": "clinical",
                        "evaluated_on_test": True,
                    },
                )
            ]
        ).promotion_status(self.run_id)
        self.assertEqual(response["evaluation_run_id"], self.evaluation_id)
        self.assertEqual(response["explainability_run_ids"], [explain_id])

    def test_threshold_must_be_evaluated_on_test(self):
        response = FixtureService(
            [
                self.context(
                    model_version=self.version("approved"),
                    versions_count=1,
                    evaluation={
                        "evaluation_run_id": self.evaluation_id,
                        "status": "completed",
                        "split_name": "test",
                        "threshold_used": None,
                        "prediction_collapse": {"collapsed": False},
                    },
                    threshold={
                        "id": str(uuid4()),
                        "value": 0.42,
                        "source": "clinical",
                        "evaluated_on_test": False,
                    },
                )
            ]
        ).promotion_status(self.run_id)
        self.assertIn("CLINICAL_THRESHOLD_REQUIRED", self.codes(response))

    def test_invalid_class_mapping_is_rejected(self):
        response = FixtureService(
            [self.context(class_mapping={"0": "parasitized", "1": "uninfected"})]
        ).promotion_status(self.run_id)
        self.assertIn("CLASS_MAPPING_INVALID", self.codes(response))

    def test_approved_complete_version_can_deploy(self):
        validator = DeploymentValidator()
        context = self.context(
            model_version=self.version("approved"),
            versions_count=1,
            evaluation={
                "evaluation_run_id": self.evaluation_id,
                "status": "completed",
                "split_name": "test",
                "threshold_used": 0.42,
                "prediction_collapse": {"collapsed": False},
            },
            threshold={
                "id": str(uuid4()),
                "value": 0.42,
                "source": "clinical",
                "evaluated_on_test": True,
            },
        )
        response = FixtureService([context], validator).promotion_status(self.run_id)
        self.assertTrue(response["can_deploy"])
        self.assertEqual(response["next_action"], "create_deployment")
        self.assertEqual(
            response["target_url"],
            f"/modelo-ia/modelos-liberados/{self.model_version_id}",
        )

    def test_prediction_collapse_blocks_deployment(self):
        context = self.context(
            model_version=self.version("approved"),
            versions_count=1,
            evaluation={
                "evaluation_run_id": self.evaluation_id,
                "status": "completed",
                "split_name": "test",
                "threshold_used": 0.42,
                "prediction_collapse": {"collapsed": True},
            },
            threshold={
                "id": str(uuid4()),
                "value": 0.42,
                "source": "clinical",
                "evaluated_on_test": True,
            },
        )
        response = FixtureService([context]).promotion_status(self.run_id)
        self.assertFalse(response["can_deploy"])
        self.assertIn("DEPLOYMENT_NOT_ALLOWED", self.codes(response))

    def test_deployment_validator_can_block_deployment(self):
        context = self.context(
            model_version=self.version("approved"),
            versions_count=1,
            evaluation={
                "evaluation_run_id": self.evaluation_id,
                "status": "completed",
                "split_name": "test",
                "threshold_used": 0.42,
                "prediction_collapse": {"collapsed": False},
            },
            threshold={
                "id": str(uuid4()),
                "value": 0.42,
                "source": "clinical",
                "evaluated_on_test": True,
            },
        )
        response = FixtureService(
            [context], DeploymentValidator(RuntimeError("blocked"))
        ).promotion_status(self.run_id)
        self.assertFalse(response["can_deploy"])
        self.assertIn("DEPLOYMENT_NOT_ALLOWED", self.codes(response))

    def test_conflicting_versions_are_blocked(self):
        response = FixtureService(
            [self.context(versions_count=2)]
        ).promotion_status(self.run_id)
        self.assertIn("MODEL_VERSION_CONFLICT", self.codes(response))

    def test_active_deployment_is_the_next_target(self):
        deployment_id = str(uuid4())
        context = self.context(
            model_version=self.version("approved"),
            versions_count=1,
            deployment={
                "id": deployment_id,
                "status": "active",
                "environment": "production",
                "alias": "champion",
            },
        )
        response = FixtureService([context]).promotion_status(self.run_id)
        self.assertEqual(response["next_action"], "view_active_deployment")
        self.assertEqual(response["button_label"], "Ver despliegue")
        self.assertEqual(
            response["target_url"], f"/modelo-ia/despliegues/{deployment_id}"
        )

    def test_pending_deployment_is_the_next_target(self):
        deployment_id = str(uuid4())
        context = self.context(
            model_version=self.version("approved"),
            versions_count=1,
            deployment={
                "id": deployment_id,
                "status": "pending",
                "environment": "experimental",
                "alias": "candidate",
            },
        )
        response = FixtureService([context]).promotion_status(self.run_id)
        self.assertEqual(response["next_action"], "review_pending_deployment")
        self.assertEqual(response["button_label"], "Ver despliegue pendiente")

    def test_get_status_has_no_creation_or_audit_side_effect(self):
        service = FixtureService([self.context()])
        service.promotion_status(self.run_id)
        self.assertEqual(service.created, 0)
        self.assertEqual(service.audits, [])

    def test_prepare_is_audited(self):
        context = self.context(
            model_version=self.version(), versions_count=1
        )
        service = FixtureService([context])
        service.prepare_release(
            self.run_id, requester="tester", request_id="request-1"
        )
        self.assertEqual(len(service.audits), 1)
        self.assertEqual(service.audits[0]["requester"], "tester")
        self.assertEqual(service.audits[0]["request_id"], "request-1")


if __name__ == "__main__":
    unittest.main()
