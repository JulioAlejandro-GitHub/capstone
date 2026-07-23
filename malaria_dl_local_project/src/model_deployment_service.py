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
PROJECT_ROOT=Path(__file__).resolve().parents[1]

def _project_path(value):
    path=Path(value or "")
    return path if path.is_absolute() else PROJECT_ROOT/path

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

    def validate_activation(self,model_version_id,threshold_profile_id=None,allowed_statuses=None):
        with self.connection_factory() as c:
            version=self._version(c,model_version_id)
            threshold=None
            if threshold_profile_id:
                threshold=c.execute(text("""SELECT * FROM run_threshold_calibration
                  WHERE run_threshold_calibration_id=:id AND model_version_id=:mv
                  AND calibration_status IN ('recorded','validated')"""),{"id":str(UUID(str(threshold_profile_id))),"mv":str(UUID(str(model_version_id)))}).mappings().one_or_none()
        errors=[]
        if version.get("lineage_status")!="resolved": errors.append("lineage_status debe ser resolved")
        accepted=set(allowed_statuses or {"approved","validated"})
        if version.get("status") not in accepted: errors.append(f"status debe ser uno de {sorted(accepted)}")
        for field in ("training_run_id","checkpoint_artifact_id","artifact_sha256"):
            if not version.get(field): errors.append(f"falta {field}")
        mapping=dict(version.get("class_mapping") or {})
        if any(mapping.get(k)!=v for k,v in EXPECTED_MAPPING.items()) or mapping.get("positive_label","parasitized")!="parasitized": errors.append("class_mapping clínico inválido")
        if not version.get("preprocessing_profile_snapshot"): errors.append("falta preprocessing")
        if not version.get("input_signature") or not version.get("output_signature"): errors.append("faltan firmas de entrada/salida")
        if not version.get("has_evaluation"): errors.append("falta evaluación formal")
        if not threshold_profile_id: errors.append("falta threshold profile")
        if threshold_profile_id and not threshold: errors.append("threshold profile inválido o de otra versión")
        path=_project_path(version.get("artifact_registered_path") or version.get("checkpoint_path") or "")
        if not path.is_file(): errors.append("artefacto inexistente")
        elif sha256_file(path)!=version.get("artifact_sha256"): errors.append("SHA-256 incorrecto")
        elif str(version.get("framework") or "").lower() not in {"keras","tensorflow","tf.keras","tensorflow/keras"}: errors.append("framework no soportado")
        elif errors: pass
        else:
            try: self.model_loader(path)
            except Exception as exc: errors.append(f"modelo no cargable: {type(exc).__name__}")
        if errors: raise GovernanceStateError("; ".join(errors))
        return version,dict(threshold)

    def readiness(self,deployment_id):
        deployment_id=str(UUID(str(deployment_id)))
        with self.connection_factory() as c:
            row=c.execute(text("""SELECT d.*,mv.training_run_id,mv.model_name,mv.version_number,
              mv.status model_version_status,mv.lineage_status
              FROM deployed_model_versions d JOIN model_versions mv ON mv.id=d.model_version_id
              WHERE d.id=:id"""),{"id":deployment_id}).mappings().one_or_none()
        if not row: raise GovernanceNotFoundError("deployment inexistente")
        validation_errors=[]
        try:
            self.validate_activation(row["model_version_id"],row["threshold_calibration_id"])
        except GovernanceStateError as exc:
            validation_errors=[item.strip() for item in str(exc).split(";") if item.strip()]
        smoke=dict(row.get("metadata") or {}).get("smoke_test") or {}
        requirements=[
          {"key":"approved","label":"Versión aprobada","status":"pass" if row["model_version_status"] in {"approved","deployed"} else "blocked",
           "detail":f"Estado actual: {row['model_version_status']}"},
          {"key":"lineage","label":"Linaje resuelto","status":"pass" if row["lineage_status"]=="resolved" else "blocked",
           "detail":f"Linaje actual: {row['lineage_status']}"},
          {"key":"technical","label":"Artifact y contrato técnico","status":"pass" if not validation_errors else "blocked",
           "detail":"Validación técnica completa." if not validation_errors else " · ".join(validation_errors)},
          {"key":"smoke","label":"Smoke test","status":"pass" if smoke.get("status")=="PASS" else ("blocked" if smoke.get("status")=="FAIL" else "pending"),
           "detail":"PASS" if smoke.get("status")=="PASS" else ("FAIL: "+" · ".join(smoke.get("errors") or []) if smoke.get("status")=="FAIL" else "Pendiente de ejecución.")},
          {"key":"confirmation","label":"Confirmación de producción","status":"pending" if row["environment"]=="production" else "not_applicable",
           "detail":"Debe confirmarse al activar." if row["environment"]=="production" else "No aplica a este ambiente."},
        ]
        can_run_smoke=not validation_errors and row["status"] in {"pending","inactive"}
        can_activate=can_run_smoke and smoke.get("status")=="PASS" and row["model_version_status"] in {"approved","deployed"}
        return {"deployment_id":deployment_id,"model_version_id":str(row["model_version_id"]),
          "training_run_id":str(row["training_run_id"]),"model_name":row["model_name"],
          "version_number":row["version_number"],"environment":row["environment"],"alias":row["alias"],
          "deployment_status":row["status"],"can_run_smoke":can_run_smoke,"can_activate":can_activate,
          "validation_errors":validation_errors,"requirements":requirements,"smoke_test":smoke or None}

    def create(self,*,model_version_id,deployment_name,environment,alias,threshold_profile_id,deployed_by=None,metadata=None,dry_run=False):
        version,threshold=self.validate_activation(model_version_id,threshold_profile_id)
        threshold_value=threshold.get("threshold_selected") or threshold.get("threshold_used")
        threshold_snapshot=json.loads(json.dumps(threshold,default=str))
        plan={"model_version_id":str(model_version_id),"deployment_name":deployment_name,"environment":environment,"alias":alias,"threshold_value":float(threshold_value),"activate":False}
        if dry_run:return plan
        from src.model_governance.repository import create_deployed_model_version
        with self.connection_factory() as c:
            deployment=create_deployed_model_version(model_version_id=model_version_id,deployment_name=deployment_name,environment=environment,alias=alias,
              threshold_value=float(threshold_value),threshold_calibration_id=threshold_profile_id,threshold_profile_snapshot=threshold_snapshot,
              deployed_by=deployed_by,metadata={**(metadata or {}),"explainability_available":bool(version.get("has_explainability")),"audit_event":"deployment_created"},
              connection_or_session=c)
        return deployment

    def smoke_test(self,deployment_id,source_image_id,actor=None,predictor=None):
        deployment_id=str(UUID(str(deployment_id)))
        with self.connection_factory() as c:
            row=c.execute(text("""SELECT d.*,mv.preprocessing_profile_snapshot,mv.input_signature,
              mv.class_mapping,a.path artifact_path FROM deployed_model_versions d
              JOIN model_versions mv ON mv.id=d.model_version_id
              JOIN artifacts a ON a.id=d.checkpoint_artifact_id WHERE d.id=:id"""),
              {"id":deployment_id}).mappings().one_or_none()
            if not row: raise GovernanceNotFoundError("deployment inexistente")
            image=c.execute(text("""SELECT image_id::text id,
              COALESCE(absolute_path,dataset_dir||'/'||relative_path) file_path
              FROM dataset_split_images WHERE image_id=:id"""),
              {"id":str(UUID(str(source_image_id)))}).mappings().one_or_none()
        errors=[]
        try:
            self.validate_activation(row["model_version_id"],row["threshold_calibration_id"])
            mapping=dict(row.get("class_mapping") or {})
            if mapping.get("0")!="uninfected" or mapping.get("1")!="parasitized":
                raise GovernanceStateError("class_mapping clínico inválido")
            image_path=_project_path(image["file_path"]) if image else None
            if not image_path or not image_path.is_file():
                raise GovernanceStateError("imagen controlada inexistente")
            model=self.model_loader(_project_path(row["artifact_path"]))
            if predictor is None:
                from src.traceable_inference import TraceableInferenceService
                predictor=TraceableInferenceService._predict
            probability=float(predictor(model,image_path,dict(row["preprocessing_profile_snapshot"] or {}),dict(row["input_signature"] or {})))
            if not 0<=probability<=1: raise GovernanceStateError("probabilidad fuera de rango")
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            probability=None
        evidence={"status":"PASS" if not errors else "FAIL","timestamp":datetime.now(UTC).isoformat(),
          "deployment_id":deployment_id,"model_version_id":str(row["model_version_id"]),
          "source_image_id":str(source_image_id),"artifact_sha256":row["artifact_sha256"],
          "probability_parasitized":probability,"serializable":True,"actor":actor,"errors":errors}
        with self.connection_factory() as c:
            result=c.execute(text("""UPDATE deployed_model_versions
              SET metadata=jsonb_set(metadata,'{smoke_test}',CAST(:evidence AS jsonb),true)
              WHERE id=:id RETURNING *"""),{"id":deployment_id,"evidence":json.dumps(evidence)}).mappings().one()
        return {"deployment":dict(result),"smoke_test":evidence}

    def activate(self,deployment_id,actor=None,confirm_production=False):
        deployment_id=str(UUID(str(deployment_id)))
        with self.connection_factory() as c:
            candidate=c.execute(text("SELECT model_version_id,threshold_calibration_id,environment,metadata FROM deployed_model_versions WHERE id=:id"),{"id":deployment_id}).mappings().one_or_none()
        if not candidate: raise GovernanceNotFoundError("deployment inexistente")
        self.validate_activation(candidate["model_version_id"],candidate["threshold_calibration_id"])
        if candidate["environment"]=="production" and not confirm_production:
            raise GovernanceStateError("production exige confirmación explícita")
        smoke=dict(candidate.get("metadata") or {}).get("smoke_test") or {}
        if smoke.get("status")!="PASS" or smoke.get("deployment_id")!=deployment_id:
            raise GovernanceStateError("smoke test PASS requerido para activar")
        with self.connection_factory() as c:
            row=c.execute(text("SELECT * FROM deployed_model_versions WHERE id=:id FOR UPDATE"),{"id":deployment_id}).mappings().one_or_none()
            if not row: raise GovernanceNotFoundError("deployment inexistente")
            self._version(c,row["model_version_id"],lock=True)
            if row["status"] not in {"pending","inactive"}: raise GovernanceStateError("sólo pending o inactive puede activarse")
            version_status=c.execute(text("SELECT status FROM model_versions WHERE id=:id"),{"id":row["model_version_id"]}).scalar_one()
            if version_status not in {"approved","deployed"}: raise GovernanceStateError("activación exige model version approved")
            replaced=c.execute(text("""UPDATE deployed_model_versions SET status='inactive',retired_at=NULL,
              metadata=metadata||CAST(:audit AS jsonb) WHERE deployment_name=:name AND environment=:env AND alias=:alias AND status='active' AND id<>:id RETURNING model_version_id"""),
              {"name":row["deployment_name"],"env":row["environment"],"alias":row["alias"],"id":deployment_id,"audit":json.dumps({"last_audit_event":"alias_replaced","at":datetime.now(UTC).isoformat()})}).mappings().all()
            result=c.execute(text("""UPDATE deployed_model_versions SET status='active',deployed_at=NOW(),deployed_by=COALESCE(:actor,deployed_by),
              metadata=metadata||CAST(:audit AS jsonb) WHERE id=:id RETURNING *"""),{"id":deployment_id,"actor":actor,"audit":json.dumps({"last_audit_event":"activated","at":datetime.now(UTC).isoformat()})}).mappings().one()
        if self.model_cache:
            for old in replaced:self.model_cache.invalidate_model_version(old["model_version_id"])
        return dict(result)

    def rollback(self,deployment_id,target_deployment_id,actor=None,reason=None):
        current_id=str(UUID(str(deployment_id)));target_id=str(UUID(str(target_deployment_id)))
        with self.connection_factory() as c:
            current=c.execute(text("SELECT * FROM deployed_model_versions WHERE id=:id"),{"id":current_id}).mappings().one_or_none()
            target=c.execute(text("SELECT * FROM deployed_model_versions WHERE id=:id"),{"id":target_id}).mappings().one_or_none()
            if not current or not target: raise GovernanceNotFoundError("deployment de rollback inexistente")
            if current["status"]!="active": raise GovernanceStateError("rollback exige un deployment actualmente activo")
            for field in ("deployment_name","environment","alias"):
                if current[field]!=target[field]: raise GovernanceStateError("rollback debe conservar deployment_name, environment y alias")
            from src.model_governance.repository import create_deployed_model_version
            revision=create_deployed_model_version(model_version_id=target["model_version_id"],deployment_name=current["deployment_name"],
              environment=current["environment"],alias=current["alias"],threshold_value=float(target["threshold_value"]),
              threshold_calibration_id=target["threshold_calibration_id"],threshold_profile_snapshot=target["threshold_profile_snapshot"],
              preprocessing_profile_snapshot=target["preprocessing_profile_snapshot"],image_quality_policy_snapshot=target["image_quality_policy_snapshot"],
              label_mapping_snapshot=target["label_mapping_snapshot"],supersedes_deployment_id=current_id,rollback_of_deployment_id=current_id,
              deployed_by=actor,deployment_reason=reason or f"Rollback a revisión {target_id}",
              metadata={"audit_event":"rollback_created","rollback_target_deployment_id":target_id},connection_or_session=c)
        return revision

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
