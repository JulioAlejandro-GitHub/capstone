"""One transactional registration in the existing scientific persistence plane."""
import os
import platform
import shutil
import socket
from pathlib import Path
from uuid import uuid4

from ..campaigns.contracts import CampaignError, canonical, digest
from ..campaigns.repository import execute, identifier
from ..data.governed_dataset import GovernedDatasetError, _resolve, normalize_dataset_version_id
from ..execution.repository import ExecutionRepository
from ..execution.storage_paths import PROJECT_ROOT, local_scientific_path
from .contracts import (ARCHITECTURE, COMPONENTS, ORIGIN, PROTOCOL,
                        PretrainedCompletionContractV1, configuration, require,
                        validate_configuration, verify_components)


def governed_snapshot(connection, dataset_version_id):
    try:
        return _resolve(connection, normalize_dataset_version_id(dataset_version_id), ()).metadata()
    except GovernedDatasetError as exc:
        raise CampaignError(str(exc)) from None


class PretrainedRepository(ExecutionRepository):
    def resolve_dataset(self, dataset_version_id):
        with self.transaction(readonly=True) as c:
            return governed_snapshot(c, dataset_version_id)

    def find(self, configuration_hash):
        with self.transaction(readonly=True) as c:
            return execute(c, "SELECT id FROM runs WHERE execution_parameters ? 'scientific_origin' "
                           "AND execution_parameters->>'configuration_hash'=:hash", hash=configuration_hash).scalar_one_or_none()

    def recover(self, run_id):
        """Revalidate relational ownership, complete protocol and every physical component."""
        with self.transaction(readonly=True) as c:
            s = dict(execute(c, "SELECT s.*,r.status AS run_status,r.model_id,r.dataset_version_id "
                            "FROM train_execution_sessions s JOIN runs r ON r.id=s.run_id "
                            "WHERE s.run_id=CAST(:id AS uuid)", id=identifier(run_id)).mappings().one())
            require(s["state"] == "verified" and s["run_status"] == "completed", "PRETRAINED_ORIGIN_NOT_VERIFIED")
            validate_configuration(s["configuration"])
            completion = PretrainedCompletionContractV1.from_dict(s["completion"])
            require(execute(c, "SELECT pretrained_completion_valid(CAST(:id AS uuid),CAST(:completion AS jsonb))",
                            id=identifier(run_id), completion=canonical(completion.to_dict())).scalar_one(),
                    "PRETRAINED_BINDING_INVALID")
            require(s["verification"] == {"status": "verified", "completion": completion.to_dict(), "components": COMPONENTS},
                    "PRETRAINED_VERIFICATION_INCOMPLETE")
            root = local_scientific_path(Path(s["artifact_root"]) / PROTOCOL["checkpoint"]).parent
            verify_components(root)
            return {"run_id": str(run_id), "model_id": str(s["model_id"]), "artifact_id": completion.artifact_id,
                    "model_version_id": completion.model_version_id, "state": "verified",
                    "configuration_hash": completion.configuration_hash, "artifact_root": str(root),
                    "configuration": s["configuration"]}

    def register(self, *, config, biomedclip_directory, text_directory, owner):
        validate_configuration(config)
        run_id, version_id = str(uuid4()), str(uuid4())
        owner = identifier(owner)
        root = PROJECT_ROOT / "outputs" / "train_runs" / run_id
        require(not any(p.is_symlink() for p in (root, *root.parents)), "PRETRAINED_SYMLINK_FORBIDDEN")
        # Unique owned directory; a failed transaction may leave unreferenced bytes,
        # never an apparently successful RUN. No historical file is overwritten/deleted.
        with self.transaction() as c:
            self.authorize(c, owner)
            dataset = governed_snapshot(c, config["target_dataset"]["dataset_version_id"])
            require(dataset == config["target_dataset"], "PRETRAINED_DATASET_CHANGED")
            model = execute(c, "SELECT id,metadata FROM models WHERE name=:name FOR SHARE", name=ARCHITECTURE).mappings().one()
            require(model["metadata"].get("trainable") is False, "PRETRAINED_MODEL_NOT_REGISTERED")
            params = {"scientific_origin": ORIGIN, "pretrained_configuration": config, "configuration_hash": digest(config)}
            execute(c, "INSERT INTO runs(id,model_id,run_name,run_type,status,started_at,dataset_version_id,execution_parameters) "
                    "VALUES(CAST(:id AS uuid),CAST(:model AS uuid),:name,'training','running',clock_timestamp(),"
                    "CAST(:dataset AS uuid),CAST(:parameters AS jsonb))", id=run_id, model=str(model["id"]),
                    name=ARCHITECTURE + ":pretrained_registration", dataset=dataset["dataset_version_id"], parameters=canonical(params))
            environment = {"python": platform.python_version(), "platform": platform.platform(),
                           "packages": config["framework_versions"], "operation": "register_pretrained"}
            execute(c, "INSERT INTO train_execution_sessions(run_id,owner,host,parent_pid,configuration,dataset,environment,artifact_root) "
                    "VALUES(CAST(:id AS uuid),CAST(:owner AS uuid),:host,:pid,CAST(:config AS jsonb),CAST(:dataset AS jsonb),"
                    "CAST(:environment AS jsonb),:root)", id=run_id, owner=owner, host=socket.gethostname(), pid=os.getpid(),
                    config=canonical(config), dataset=canonical(dataset), environment=canonical(environment), root=str(root))
            root.mkdir(parents=True, exist_ok=False)
            artifacts = {}
            for name, identity in COMPONENTS.items():
                source = Path(text_directory) / name[5:] if name.startswith("text/") else Path(biomedclip_directory) / name
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                # Exclusive create, copy bytes (not symlinks/hardlinks to mutable cache).
                with source.open("rb") as src, target.open("xb") as dst:
                    shutil.copyfileobj(src, dst, 1024 * 1024)
                    dst.flush()
                    os.fsync(dst.fileno())
                target.chmod(0o444)
                artifacts[name] = str(uuid4())
                execute(c, "INSERT INTO artifacts(id,run_id,artifact_type,name,path,artifact_uri,file_size_bytes,checksum,metadata) "
                        "VALUES(CAST(:id AS uuid),CAST(:run AS uuid),:type,:name,:path,:path,:bytes,:sha,CAST(:metadata AS jsonb))",
                        id=artifacts[name], run=run_id, type="model_checkpoint" if name == PROTOCOL["checkpoint"] else "model_component",
                        name=name, path=str(target), bytes=identity["bytes"], sha=identity["sha256"],
                        metadata=canonical({"scientific_origin": ORIGIN, "configuration_hash": digest(config), "component": name}))
            verify_components(root)
            checkpoint_id = artifacts[PROTOCOL["checkpoint"]]
            checkpoint = COMPONENTS[PROTOCOL["checkpoint"]]
            execute(c, "INSERT INTO model_versions(id,model_id,model_name,version_name,training_run_id,checkpoint_artifact_id,"
                    "checkpoint_path,artifact_uri,artifact_sha256,artifact_size_bytes,artifact_hash_reuse_justification,framework,framework_version,"
                    "preprocessing_profile_snapshot,class_mapping,input_signature,output_signature,status,lineage_status,metadata) "
                    "VALUES(CAST(:id AS uuid),CAST(:model AS uuid),:name,:version,CAST(:run AS uuid),CAST(:artifact AS uuid),:path,:path,"
                    ":sha,:bytes,:reuse,'pytorch/open_clip',:framework_version,CAST(:transform AS jsonb),CAST(:classes AS jsonb),"
                    "CAST(:input AS jsonb),CAST(:output AS jsonb),'candidate','resolved',CAST(:metadata AS jsonb))",
                    id=version_id, model=str(model["id"]), name=ARCHITECTURE, version=digest(config), run=run_id,
                    artifact=checkpoint_id, path=str(root / PROTOCOL["checkpoint"]), sha=checkpoint["sha256"], bytes=checkpoint["bytes"],
                    reuse="Same immutable external checkpoint; target dataset and inference protocol bound by configuration_hash",
                    framework_version=config["framework_versions"]["torch"], transform=canonical(PROTOCOL["transform"]),
                    classes=canonical({"uninfected": 0, "parasitized": 1}),
                    input=canonical({"shape": [None, 3, 224, 224], "dtype": "float32", "layout": "NCHW"}),
                    output=canonical({"shape": [None, 2], "positive_class": 1, "semantics": "relative_to_two_prompts"}),
                    metadata=canonical({"scientific_origin": ORIGIN, "configuration_hash": digest(config)}))
            completion = PretrainedCompletionContractV1.create(run_id=run_id, owner=owner, model_id=str(model["id"]),
                artifact_id=checkpoint_id, model_version_id=version_id, config=config).to_dict()
            execute(c, "UPDATE train_execution_sessions SET state='completed',completion=CAST(:value AS jsonb),updated_at=clock_timestamp() "
                    "WHERE run_id=CAST(:run AS uuid)", run=run_id, value=canonical(completion))
            verify_components(root)
            execute(c, "UPDATE train_execution_sessions SET state='verified',verification=CAST(:value AS jsonb),updated_at=clock_timestamp() "
                    "WHERE run_id=CAST(:run AS uuid)", run=run_id,
                    value=canonical({"status": "verified", "completion": completion, "components": COMPONENTS}))
            execute(c, "UPDATE runs SET status='completed',finished_at=clock_timestamp(),"
                    "duration_seconds=extract(epoch FROM clock_timestamp()-started_at),updated_at=clock_timestamp() "
                    "WHERE id=CAST(:run AS uuid)", run=run_id)
            # Check deferred constraints before leaving the transaction, not after reporting success.
            execute(c, "SET CONSTRAINTS ALL IMMEDIATE")
        return self.recover(run_id)
