import sys,unittest
from pathlib import Path
from unittest import mock
from pydantic import ValidationError
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from app.routes import governance

class GovernanceApiTests(unittest.TestCase):
    def test_removed_technical_stage2_routes_are_not_registered(self):
        paths={route.path for route in governance.router.routes}
        self.assertNotIn("/api/training-runs/{training_run_id}/stage2-availability",paths)
        self.assertNotIn("/api/training-runs/{training_run_id}/stage2-package-preview",paths)
        self.assertNotIn("/api/training-runs/{training_run_id}/enable-stage2",paths)
        self.assertNotIn(
            "/api/model-versions/{model_version_id}/technical-production-preview",
            paths,
        )
        self.assertNotIn(
            "/api/model-versions/{model_version_id}/publish-technical-production",
            paths,
        )

    def test_stage2_release_status_is_publication_only(self):
        run_id="084604a0-cb23-43c0-be0f-eab5b0ba1a31"
        service=mock.Mock()
        service.status_for_training.return_value={"training_run_id":run_id,"eligible":True}
        with mock.patch.object(
            governance,"stage2_publication_service",return_value=service
        ):
            response=governance.stage2_release_status(run_id,"malaria")
        service.status_for_training.assert_called_once_with(run_id)
        service.publish.assert_not_called()
        self.assertTrue(response["eligible"])

    def test_publish_stage2_only_creates_publication(self):
        model_id="8f5277bd-e2bb-4dff-a4d6-821f9f5a60e7"
        service=mock.Mock()
        service.publish.return_value={
            "model_version_id":model_id,
            "publication_id":"084604a0-cb23-43c0-be0f-eab5b0ba1a31",
            "publication_status":"active",
            "eligible":True,
        }
        principal=governance.Principal(
            "user-id","tester",("administrator",),frozenset()
        )
        body=governance.Stage2PublicationRequest(reason="TRAIN y EVALUATE completos")
        with mock.patch.object(
            governance,"stage2_publication_service",return_value=service
        ):
            response=governance.publish_stage2_model(
                model_id,body,"malaria","request-1",principal
            )
        service.publish.assert_called_once_with(
            model_id,"tester","TRAIN y EVALUATE completos","request-1"
        )
        self.assertEqual(response["publication_status"],"active")
    def test_arbitrary_checkpoint_is_rejected(self):
        with self.assertRaises(ValidationError):governance.ImageJobCreate.model_validate({"deployed_model_version_id":"11111111-1111-4111-8111-111111111111","source_image_id":"22222222-2222-4222-8222-222222222222","checkpoint":"../../evil.pkl"})
    def test_inference_response_serialization(self):
        payload={"inference_run_id":"r","image_analysis_job_id":"j","deployed_model_version_id":"d","model_version_id":"m","predicted_class":1,"predicted_label":"parasitized"}
        with mock.patch.object(governance.INFERENCE_SERVICE,"infer",return_value=payload):
            response=governance.create_image_job(governance.ImageJobCreate(deployed_model_version_id="11111111-1111-4111-8111-111111111111",source_image_id="22222222-2222-4222-8222-222222222222"))
        self.assertEqual(response["predicted_label"],"parasitized")
    def test_legacy_physical_path_not_in_schema(self):
        schema=governance.ImageJobCreate.model_json_schema()
        self.assertNotIn("checkpoint",schema["properties"]);self.assertNotIn("model_path",schema["properties"])
    def test_promotion_status_is_read_only_service_call(self):
        run_id="11111111-1111-4111-8111-111111111111"
        service=mock.Mock()
        service.promotion_status.return_value={"training_run_id":run_id,"next_action":"prepare_release"}
        with mock.patch.object(governance,"prepare_release_service",return_value=service):
            response=governance.promotion_status(run_id,"malaria")
        service.promotion_status.assert_called_once_with(run_id)
        service.prepare_release.assert_not_called()
        self.assertEqual(response["next_action"],"prepare_release")
    def test_prepare_release_forwards_audit_context(self):
        run_id="11111111-1111-4111-8111-111111111111"
        service=mock.Mock()
        service.prepare_release.return_value={"training_run_id":run_id,"model_version_id":"model","deployment_id":None}
        with mock.patch.object(governance,"prepare_release_service",return_value=service):
            response=governance.prepare_release(
                run_id,governance.PrepareReleaseRequest(target_environment="experimental"),
                "malaria","tester","request-1",
            )
        service.prepare_release.assert_called_once_with(
            run_id,requester="tester",target_environment="experimental",request_id="request-1",
        )
        self.assertIsNone(response["deployment_id"])
    def test_contract_candidates_is_read_only_service_call(self):
        model_id="11111111-1111-4111-8111-111111111111"
        service=mock.Mock();service.candidates.return_value={"model_version_id":model_id,"fields":[]}
        with mock.patch.object(governance,"contract_service",return_value=service):
            response=governance.model_version_contract_candidates(model_id,"malaria")
        service.candidates.assert_called_once_with(model_id);service.complete.assert_not_called()
        self.assertEqual(response["model_version_id"],model_id)
    def test_complete_contract_forwards_explicit_evidence_and_audit(self):
        model_id="11111111-1111-4111-8111-111111111111";service=mock.Mock()
        service.complete.return_value={"threshold_profile_id":"threshold"}
        body=governance.CompleteContractRequest(
            selections={"threshold_profile_id":"22222222-2222-4222-8222-222222222222"},
            actor="tester",reason="evidencia revisada",
        )
        with mock.patch.object(governance,"contract_service",return_value=service):
            response=governance.complete_model_version_contract(model_id,body,"malaria")
        service.complete.assert_called_once_with(model_id,body.selections,"tester","evidencia revisada")
        self.assertEqual(response["threshold_profile_id"],"threshold")
    def test_publish_forwards_confirmation_to_existing_deployment_service(self):
        model_id="11111111-1111-4111-8111-111111111111";image_id="22222222-2222-4222-8222-222222222222"
        deployment=mock.Mock();deployment.publish_to_production.return_value={"status":"active","smoke_status":"PASS"}
        body=governance.PublishProductionRequest(
            deployment_name="malaria-classifier",alias="champion",actor="tester",
            reason="publicación aprobada",confirm_production=True,source_image_id=image_id,
        )
        with mock.patch.object(governance,"governance_services",return_value=(deployment,mock.Mock(),mock.Mock())):
            response=governance.publish_to_production(model_id,body,"malaria")
        deployment.publish_to_production.assert_called_once_with(
            model_version_id=model_id,deployment_name="malaria-classifier",alias="champion",
            actor="tester",reason="publicación aprobada",confirm_production=True,
            source_image_id=image_id,
        )
        self.assertEqual(response["status"],"active")
if __name__=="__main__":unittest.main()
