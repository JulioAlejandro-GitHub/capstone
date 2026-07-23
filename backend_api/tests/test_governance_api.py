import sys,unittest
from pathlib import Path
from unittest import mock
from pydantic import ValidationError
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from app.main import app
from app.routes import governance

class GovernanceApiTests(unittest.TestCase):
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
if __name__=="__main__":unittest.main()
