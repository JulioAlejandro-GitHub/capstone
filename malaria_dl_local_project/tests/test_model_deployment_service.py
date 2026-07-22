import hashlib,sys,tempfile,unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4
PROJECT=Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:sys.path.insert(0,str(PROJECT))
from src.model_deployment_service import ModelDeploymentService
from src.model_governance.errors import GovernanceConflictError,GovernanceStateError
from src.traceable_inference import ModelCache

class Result:
    def __init__(self,row=None,rows=None):self.row=row;self.rows=rows
    def mappings(self):return self
    def one_or_none(self):return self.row
    def all(self):return self.rows if self.rows is not None else ([] if self.row is None else [self.row])
class Conn:
    def __init__(self,*results):self.results=list(results)
    def execute(self,*_):
        value=self.results.pop(0);return value if isinstance(value,Result) else Result(row=value)
def factory(conn):
    @contextmanager
    def open_conn():yield conn
    return open_conn

class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/"model.keras";self.path.write_bytes(b"model")
        self.mv=str(uuid4());self.threshold=str(uuid4())
    def tearDown(self):self.temp.cleanup()
    def version(self,**changes):
        row={"id":self.mv,"training_run_id":str(uuid4()),"checkpoint_artifact_id":str(uuid4()),"artifact_sha256":hashlib.sha256(b"model").hexdigest(),
          "artifact_registered_path":str(self.path),"status":"validated","lineage_status":"resolved","class_mapping":{"0":"uninfected","1":"parasitized","positive_label":"parasitized"},
          "preprocessing_profile_snapshot":{"mode":"rescale_0_1"},"input_signature":{"shape":[None,200,200,3]},"output_signature":{"shape":[None,1]},
          "framework":"keras","has_evaluation":True,"has_explainability":False}
        row.update(changes);return row
    def calibration(self):return {"threshold_selected":0.42,"calibration_status":"validated"}
    def test_valid_deployment_plan(self):
        service=ModelDeploymentService(factory(Conn(self.version(),self.calibration())),model_loader=lambda _:object())
        plan=service.create(model_version_id=self.mv,deployment_name="malaria",environment="experimental",alias="champion",threshold_profile_id=self.threshold,dry_run=True)
        self.assertEqual(plan["threshold_value"],0.42)
    def test_deployment_without_evaluation(self):
        service=ModelDeploymentService(factory(Conn(self.version(has_evaluation=False),self.calibration())),model_loader=lambda _:object())
        with self.assertRaisesRegex(GovernanceStateError,"evaluación"):service.validate_activation(self.mv,self.threshold)
    def test_deployment_wrong_hash(self):
        service=ModelDeploymentService(factory(Conn(self.version(artifact_sha256="0"*64),self.calibration())),model_loader=lambda _:object())
        with self.assertRaisesRegex(GovernanceStateError,"SHA-256"):service.validate_activation(self.mv,self.threshold)
    def test_load_error_blocks_activation(self):
        def broken(_):raise ValueError("bad")
        service=ModelDeploymentService(factory(Conn(self.version(),self.calibration())),model_loader=broken)
        with self.assertRaisesRegex(GovernanceStateError,"no cargable"):service.validate_activation(self.mv,self.threshold)
    def test_alias_requires_exactly_one_active(self):
        service=ModelDeploymentService(factory(Conn(Result(rows=[]))))
        with self.assertRaises(GovernanceConflictError):service.resolve_alias("m","e","champion")
    def test_cache_key_includes_model_version_and_hash(self):
        cache=ModelCache();calls=[]
        loader=lambda path:calls.append(path) or object()
        first=cache.get_or_load("v1","a",self.path,loader);self.assertIs(first,cache.get_or_load("v1","a",self.path,loader))
        cache.get_or_load("v2","a",self.path,loader);cache.get_or_load("v1","b",self.path,loader)
        self.assertEqual(len(calls),3)
    def test_cache_invalidation(self):
        cache=ModelCache();calls=[];loader=lambda _:calls.append(1) or object()
        cache.get_or_load("v1","a",self.path,loader);cache.invalidate_model_version("v1");cache.get_or_load("v1","a",self.path,loader)
        self.assertEqual(len(calls),2)
if __name__=="__main__":unittest.main()
