"""Controlled deployment lifecycle with auditable validation and alias cutover."""
from __future__ import annotations
import json
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID
from sqlalchemy import text
from src.model_governance.errors import GovernanceConflictError, GovernanceNotFoundError, GovernanceStateError
from src.model_governance.releases import sha256_file

EXPECTED_MAPPING={"0":"uninfected","1":"parasitized"}

class ModelDeploymentService:
    def __init__(self, connection_factory=None, model_loader=None, model_cache=None):
        if connection_factory is None:
            from src.db import get_connection
            connection_factory=get_connection
        self.connection_factory=connection_factory
        self.model_loader=model_loader or self._keras_loader
        self.model_cache=model_cache

    @staticmethod
    def _keras_loader(path):
        import tensorflow as tf
        return tf.keras.models.load_model(path,compile=False)

    def _version(self,c,model_version_id,lock=False):
        suffix=" FOR SHARE" if lock else ""
        row=c.execute(text("""SELECT mv.*,a.path artifact_registered_path,
          EXISTS(SELECT 1 FROM run_lineage rl JOIN runs er ON er.id=rl.child_run_id
            WHERE rl.model_version_id=mv.id AND er.run_type='evaluation' AND er.status='completed') has_evaluation,
          EXISTS(SELECT 1 FROM run_lineage rl JOIN runs xr ON xr.id=rl.child_run_id
            WHERE rl.model_version_id=mv.id AND xr.run_type='explainability' AND xr.status='completed') has_explainability
          FROM model_versions mv JOIN artifacts a ON a.id=mv.checkpoint_artifact_id
          WHERE mv.id=:id"""+suffix),{"id":str(UUID(str(model_version_id)))}).mappings().one_or_none()
        if not row: raise GovernanceNotFoundError("model version inexistente")
        return dict(row)

    def validate_activation(self,model_version_id,threshold_profile_id=None):
        with self.connection_factory() as c:
            version=self._version(c,model_version_id)
            threshold=None
            if threshold_profile_id:
                threshold=c.execute(text("""SELECT * FROM run_threshold_calibration
                  WHERE run_threshold_calibration_id=:id AND model_version_id=:mv
                  AND calibration_status IN ('recorded','validated')"""),{"id":str(UUID(str(threshold_profile_id))),"mv":str(UUID(str(model_version_id)))}).mappings().one_or_none()
        errors=[]
        if version.get("lineage_status")!="resolved": errors.append("lineage_status debe ser resolved")
        if version.get("status") not in {"approved","validated"}: errors.append("status debe ser approved o validated")
        for field in ("training_run_id","checkpoint_artifact_id","artifact_sha256"):
            if not version.get(field): errors.append(f"falta {field}")
        mapping=dict(version.get("class_mapping") or {})
        if any(mapping.get(k)!=v for k,v in EXPECTED_MAPPING.items()) or mapping.get("positive_label","parasitized")!="parasitized": errors.append("class_mapping clínico inválido")
        if not version.get("preprocessing_profile_snapshot"): errors.append("falta preprocessing")
        if not version.get("input_signature") or not version.get("output_signature"): errors.append("faltan firmas de entrada/salida")
        if not version.get("has_evaluation"): errors.append("falta evaluación formal")
        if not threshold_profile_id: errors.append("falta threshold profile")
        if threshold_profile_id and not threshold: errors.append("threshold profile inválido o de otra versión")
        path=Path(version.get("artifact_registered_path") or version.get("checkpoint_path") or "")
        if not path.is_file(): errors.append("artefacto inexistente")
        elif sha256_file(path)!=version.get("artifact_sha256"): errors.append("SHA-256 incorrecto")
        elif str(version.get("framework") or "").lower() not in {"keras","tensorflow","tf.keras"}: errors.append("framework no soportado")
        else:
            try: self.model_loader(path)
            except Exception as exc: errors.append(f"modelo no cargable: {type(exc).__name__}")
        if errors: raise GovernanceStateError("; ".join(errors))
        return version,dict(threshold)

    def create(self,*,model_version_id,deployment_name,environment,alias,threshold_profile_id,deployed_by=None,metadata=None,dry_run=False):
        version,threshold=self.validate_activation(model_version_id,threshold_profile_id)
        threshold_value=threshold.get("threshold_selected") or threshold.get("threshold_used")
        plan={"model_version_id":str(model_version_id),"deployment_name":deployment_name,"environment":environment,"alias":alias,"threshold_value":float(threshold_value),"activate":False}
        if dry_run:return plan
        from src.model_governance.repository import create_deployed_model_version
        deployment=create_deployed_model_version(model_version_id=model_version_id,deployment_name=deployment_name,environment=environment,alias=alias,
          threshold_value=float(threshold_value),threshold_calibration_id=threshold_profile_id,threshold_profile_snapshot=threshold,
          deployed_by=deployed_by,metadata={**(metadata or {}),"explainability_available":bool(version.get("has_explainability")),"audit_event":"deployment_created"})
        return deployment

    def activate(self,deployment_id,actor=None):
        deployment_id=str(UUID(str(deployment_id)))
        with self.connection_factory() as c:
            candidate=c.execute(text("SELECT model_version_id,threshold_calibration_id FROM deployed_model_versions WHERE id=:id"),{"id":deployment_id}).mappings().one_or_none()
        if not candidate: raise GovernanceNotFoundError("deployment inexistente")
        self.validate_activation(candidate["model_version_id"],candidate["threshold_calibration_id"])
        with self.connection_factory() as c:
            row=c.execute(text("SELECT * FROM deployed_model_versions WHERE id=:id FOR UPDATE"),{"id":deployment_id}).mappings().one_or_none()
            if not row: raise GovernanceNotFoundError("deployment inexistente")
            self._version(c,row["model_version_id"],lock=True)
            if row["status"] not in {"pending","inactive"}: raise GovernanceStateError("sólo pending o inactive puede activarse")
            replaced=c.execute(text("""UPDATE deployed_model_versions SET status='inactive',retired_at=NULL,
              metadata=metadata||CAST(:audit AS jsonb) WHERE deployment_name=:name AND environment=:env AND alias=:alias AND status='active' AND id<>:id RETURNING model_version_id"""),
              {"name":row["deployment_name"],"env":row["environment"],"alias":row["alias"],"id":deployment_id,"audit":json.dumps({"last_audit_event":"alias_replaced","at":datetime.now(UTC).isoformat()})}).mappings().all()
            result=c.execute(text("""UPDATE deployed_model_versions SET status='active',deployed_at=NOW(),deployed_by=COALESCE(:actor,deployed_by),
              metadata=metadata||CAST(:audit AS jsonb) WHERE id=:id RETURNING *"""),{"id":deployment_id,"actor":actor,"audit":json.dumps({"last_audit_event":"activated","at":datetime.now(UTC).isoformat()})}).mappings().one()
        if self.model_cache:
            for old in replaced:self.model_cache.invalidate_model_version(old["model_version_id"])
        return dict(result)

    def transition(self,deployment_id,status,actor=None,reason=None):
        if status not in {"inactive","retired"}: raise ValueError("transición inválida")
        with self.connection_factory() as c:
            row=c.execute(text("""UPDATE deployed_model_versions SET status=:status,
              retired_at=CASE WHEN :status='retired' THEN NOW() ELSE retired_at END,
              retired_by=CASE WHEN :status='retired' THEN :actor ELSE retired_by END,
              retirement_reason=CASE WHEN :status='retired' THEN :reason ELSE retirement_reason END,
              metadata=metadata||CAST(:audit AS jsonb) WHERE id=:id AND status<>'retired' RETURNING *"""),
              {"id":str(UUID(str(deployment_id))),"status":status,"actor":actor,"reason":reason,"audit":json.dumps({"last_audit_event":status,"at":datetime.now(UTC).isoformat()})}).mappings().one_or_none()
        if not row: raise GovernanceStateError("deployment inexistente o retirado")
        return dict(row)

    def resolve_alias(self,deployment_name,environment,alias):
        with self.connection_factory() as c:
            rows=c.execute(text("SELECT * FROM deployed_model_versions WHERE deployment_name=:n AND environment=:e AND alias=:a AND status='active'"),{"n":deployment_name,"e":environment,"a":alias}).mappings().all()
        if len(rows)!=1: raise GovernanceConflictError("alias no resuelve exactamente un deployment activo")
        return dict(rows[0])
