"""Single authoritative resolver for evaluation, explanation and inference inputs."""
from __future__ import annotations
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from uuid import UUID
from sqlalchemy import text
from src.config import LABEL_MAPPING_VERSION
from src.model_governance.releases import sha256_file

EXPECTED_MAPPING={"0":"uninfected","1":"parasitized","positive_class":1,"positive_label":"parasitized"}

class ModelVersionResolutionError(RuntimeError): pass
class ModelVersionNotFoundError(ModelVersionResolutionError): pass
class ModelVersionIntegrityError(ModelVersionResolutionError): pass

@dataclass(frozen=True)
class ResolvedModelVersion:
    model_version_id: str
    source_training_run_id: str
    checkpoint_artifact_id: str
    checkpoint_path: Path
    checkpoint_sha256: str
    model_name: str
    status: str
    preprocessing: dict
    class_mapping: dict
    input_signature: dict
    output_signature: dict

    def lineage_metadata(self) -> dict[str, Any]:
        return {"model_version_id":self.model_version_id,"source_training_run_id":self.source_training_run_id,
                "checkpoint_artifact_id":self.checkpoint_artifact_id,"checkpoint_path":str(self.checkpoint_path),
                "checkpoint_sha256":self.checkpoint_sha256,"preprocessing_profile":self.preprocessing,
                "class_mapping":self.class_mapping,"input_signature":self.input_signature,"output_signature":self.output_signature}

class ModelVersionResolver:
    def __init__(self, connection_factory: Callable|None=None):
        if connection_factory is None:
            from src.db import get_connection
            connection_factory=get_connection
        self.connection_factory=connection_factory

    def resolve(self, *, model_version_id=None, checkpoint=None, source_training_run_id=None,
                require_lineage=False) -> ResolvedModelVersion|None:
        if require_lineage and not model_version_id:
            raise ModelVersionResolutionError("--require-lineage exige --model-version-id.")
        if not model_version_id and source_training_run_id and not checkpoint:
            with self.connection_factory() as c:
                rows=c.execute(text("SELECT id::text id FROM model_versions WHERE training_run_id=:run AND status NOT IN ('rejected','retired') ORDER BY version_number DESC NULLS LAST"),{"run":source_training_run_id}).mappings().all()
            if len(rows)!=1:
                raise ModelVersionResolutionError("--source-training-run-id debe resolver exactamente una model version utilizable")
            model_version_id=rows[0]["id"]
        if not model_version_id:
            warnings.warn("--checkpoint/--model-path es legacy; resuelva o cree una model_version antes de persistir resultados.",FutureWarning,stacklevel=2)
            path=Path(checkpoint).expanduser().resolve()
            if path.is_file():
                checksum=sha256_file(path)
                with self.connection_factory() as c:
                    rows=c.execute(text("""SELECT id::text id FROM model_versions
                      WHERE (checkpoint_path=:path OR artifact_sha256=:sha)
                        AND (:run IS NULL OR training_run_id=:run)
                        AND status NOT IN ('rejected','retired')"""),
                        {"path":str(path),"sha":checksum,"run":source_training_run_id}).mappings().all()
                if len(rows)==1:
                    return self.resolve(model_version_id=rows[0]["id"],source_training_run_id=source_training_run_id)
            return None
        try: normalized=str(UUID(str(model_version_id)))
        except ValueError as exc: raise ModelVersionNotFoundError("model_version_id inválido") from exc
        with self.connection_factory() as c:
            row=c.execute(text("""SELECT mv.id::text model_version_id,mv.training_run_id::text source_training_run_id,
                mv.checkpoint_artifact_id::text checkpoint_artifact_id,mv.checkpoint_path,mv.artifact_sha256,
                mv.model_name,mv.status,mv.lineage_status,mv.preprocessing_profile_snapshot,mv.class_mapping,
                mv.input_signature,mv.output_signature,r.run_type
              FROM model_versions mv JOIN runs r ON r.id=mv.training_run_id WHERE mv.id=:id"""),{"id":normalized}).mappings().one_or_none()
        if not row: raise ModelVersionNotFoundError(f"No existe la model version {normalized}.")
        if row["run_type"]!="training" or (source_training_run_id and str(row["source_training_run_id"])!=str(source_training_run_id)):
            raise ModelVersionIntegrityError("training run inconsistente con la model version")
        if row["lineage_status"]!="resolved" or row["status"] in {"rejected","retired"}:
            raise ModelVersionIntegrityError("model version no utilizable por estado o linaje")
        path=Path(row["checkpoint_path"]).expanduser().resolve()
        if not path.is_file(): raise ModelVersionIntegrityError(f"checkpoint inexistente: {path}")
        actual=sha256_file(path)
        if actual!=row["artifact_sha256"]: raise ModelVersionIntegrityError("SHA-256 del checkpoint no coincide")
        mapping=dict(row["class_mapping"] or {})
        for key,value in EXPECTED_MAPPING.items():
            if mapping.get(key)!=value: raise ModelVersionIntegrityError("class_mapping clínico inválido")
        preprocessing=dict(row["preprocessing_profile_snapshot"] or {})
        if require_lineage and not preprocessing: raise ModelVersionIntegrityError("preprocessing obligatorio en modo estricto")
        return ResolvedModelVersion(normalized,str(row["source_training_run_id"]),str(row["checkpoint_artifact_id"]),path,actual,row["model_name"],row["status"],preprocessing,mapping,dict(row["input_signature"] or {}),dict(row["output_signature"] or {}))

    def validate_evaluation(self, evaluation_run_id: str, model_version_id: str) -> None:
        with self.connection_factory() as c:
            row=c.execute(text("""SELECT rl.model_version_id::text model_version_id FROM runs r
              JOIN run_lineage rl ON rl.child_run_id=r.id WHERE r.id=:id AND r.run_type='evaluation'
              AND rl.relationship_type='evaluates_checkpoint_from'"""),{"id":evaluation_run_id}).mappings().one_or_none()
        if not row: raise ModelVersionIntegrityError("evaluation_run_id inexistente o sin linaje gobernado")
        if row["model_version_id"]!=model_version_id: raise ModelVersionIntegrityError("evaluation run pertenece a otra model version")
