import hashlib, sys, tempfile, unittest, warnings
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4
PROJECT_ROOT=Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0,str(PROJECT_ROOT))
from src.model_version_resolver import ModelVersionIntegrityError, ModelVersionNotFoundError, ModelVersionResolutionError, ModelVersionResolver

class Result:
    def __init__(self,row): self.row=row
    def mappings(self): return self
    def one_or_none(self): return self.row
    def all(self): return self.row
class Conn:
    def __init__(self,*rows): self.rows=list(rows)
    def execute(self,*_): return Result(self.rows.pop(0))
def factory(conn):
    @contextmanager
    def open_conn(): yield conn
    return open_conn

class ResolverTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.path=Path(self.tmp.name)/"m.keras"; self.path.write_bytes(b"model")
        self.mv=str(uuid4()); self.run=str(uuid4()); self.artifact=str(uuid4())
    def tearDown(self): self.tmp.cleanup()
    def row(self,**changes):
        row={"model_version_id":self.mv,"source_training_run_id":self.run,"checkpoint_artifact_id":self.artifact,
          "checkpoint_path":str(self.path),"artifact_sha256":hashlib.sha256(b"model").hexdigest(),"model_name":"custom_cnn",
          "status":"candidate","lineage_status":"resolved","preprocessing_profile_snapshot":{"mode":"rescale_0_1"},
          "class_mapping":{"0":"uninfected","1":"parasitized","positive_class":1,"positive_label":"parasitized"},
          "input_signature":{},"output_signature":{},"run_type":"training"}
        row.update(changes); return row
    def test_resolves_model_version(self):
        resolved=ModelVersionResolver(factory(Conn(self.row()))).resolve(model_version_id=self.mv,require_lineage=True)
        self.assertEqual(resolved.checkpoint_artifact_id,self.artifact)
    def test_wrong_hash(self):
        with self.assertRaisesRegex(ModelVersionIntegrityError,"SHA-256"):
            ModelVersionResolver(factory(Conn(self.row(artifact_sha256="0"*64)))).resolve(model_version_id=self.mv)
    def test_missing_version(self):
        with self.assertRaises(ModelVersionNotFoundError): ModelVersionResolver(factory(Conn(None))).resolve(model_version_id=self.mv)
    def test_training_inconsistent(self):
        with self.assertRaisesRegex(ModelVersionIntegrityError,"training"):
            ModelVersionResolver(factory(Conn(self.row()))).resolve(model_version_id=self.mv,source_training_run_id=str(uuid4()))
    def test_invalid_mapping(self):
        with self.assertRaisesRegex(ModelVersionIntegrityError,"class_mapping"):
            ModelVersionResolver(factory(Conn(self.row(class_mapping={"0":"parasitized"})))).resolve(model_version_id=self.mv)
    def test_other_model_evaluation(self):
        resolver=ModelVersionResolver(factory(Conn({"model_version_id":str(uuid4())})))
        with self.assertRaisesRegex(ModelVersionIntegrityError,"otra model version"): resolver.validate_evaluation(str(uuid4()),self.mv)
    def test_legacy_warns(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always"); self.assertIsNone(ModelVersionResolver(factory(Conn([]))).resolve(checkpoint=self.path))
        self.assertIn("legacy",str(caught[0].message))
    def test_strict_requires_version(self):
        with self.assertRaises(ModelVersionResolutionError): ModelVersionResolver(factory(Conn())).resolve(checkpoint=self.path,require_lineage=True)
    def test_source_training_run_resolves_unique_version(self):
        resolved=ModelVersionResolver(factory(Conn([{"id":self.mv}],self.row()))).resolve(source_training_run_id=self.run)
        self.assertEqual(resolved.model_version_id,self.mv)

if __name__=="__main__": unittest.main()
