import json, sys, tempfile, unittest, zipfile
from pathlib import Path
from uuid import uuid4
PROJECT_ROOT=Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0,str(PROJECT_ROOT))
from src.model_governance.releases import (CLASS_MAPPING, create_release, inventory_artifacts, resolve_lineage, sha256_file, validate_model_artifact)

def keras(path, payload=b"weights"):
    path.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path,"w") as z:
        z.writestr("config.json","{}")
        z.writestr("metadata.json","{}")
        z.writestr("model.weights.h5",payload)

class ModelReleaseTests(unittest.TestCase):
    def test_hash_is_reproducible(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x"; p.write_bytes(b"abc")
            self.assertEqual(sha256_file(p),sha256_file(p))
            self.assertEqual(sha256_file(p),"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
    def test_unique_hash_resolves_generic_copy(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); run=str(uuid4()); specific=root/"outputs"/"custom_cnn"/"runs"/run/"best_model.keras"; generic=root/"outputs"/"custom_cnn"/"best_model.keras"
            keras(specific); generic.parent.mkdir(parents=True,exist_ok=True); generic.write_bytes(specific.read_bytes())
            resolved=resolve_lineage(inventory_artifacts(root),[run])
            generic_item=next(x for x in resolved if x["generic_path"])
            self.assertEqual(generic_item["training_run_id"],run); self.assertEqual(generic_item["lineage_evidence"],"unique_sha256_match")
    def test_ambiguity_is_not_associated(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); runs=[str(uuid4()),str(uuid4())]
            for run in runs: keras(root/"outputs"/"m"/"runs"/run/"best_model.keras")
            generic=root/"outputs"/"m"/"best_model.keras"; generic.parent.mkdir(parents=True,exist_ok=True); generic.write_bytes((root/"outputs"/"m"/"runs"/runs[0]/"best_model.keras").read_bytes())
            # Zip timestamps can differ; force identical bytes for the second run.
            (root/"outputs"/"m"/"runs"/runs[1]/"best_model.keras").write_bytes(generic.read_bytes())
            item=next(x for x in resolve_lineage(inventory_artifacts(root),runs) if x["generic_path"])
            self.assertEqual(item["lineage_status"],"unresolved"); self.assertIsNone(item["training_run_id"])
    def test_missing_artifact_rejected(self):
        with self.assertRaises(FileNotFoundError): validate_model_artifact(Path("does-not-exist.keras"))
    def test_corrupt_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bad.keras"; p.write_bytes(b"bad")
            with self.assertRaises(ValueError): validate_model_artifact(p)
    def test_release_manifest_mapping_no_deployment_and_source_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source=root/"source.keras"; keras(source); before=source.read_bytes(); run=str(uuid4())
            manifest=create_release(project_root=root,artifact_path=source,training_run_id=run,model_name="custom_cnn",output_dir=root/"releases")
            loaded=json.loads((Path(manifest["immutable_artifact_path"]).parent/"manifest.json").read_text())
            self.assertEqual(loaded["class_mapping"],CLASS_MAPPING); self.assertFalse(loaded["deployment_created"])
            self.assertEqual(source.read_bytes(),before); self.assertEqual(sha256_file(source),loaded["sha256"])
    def test_release_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source=root/"source.keras"; keras(source); version=str(uuid4()); kwargs=dict(project_root=root,artifact_path=source,training_run_id=str(uuid4()),model_name="m",output_dir=root/"releases",model_version_id=version)
            create_release(**kwargs)
            with self.assertRaises(FileExistsError): create_release(**kwargs)

if __name__=="__main__": unittest.main()
