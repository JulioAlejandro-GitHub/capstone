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
if __name__=="__main__":unittest.main()
