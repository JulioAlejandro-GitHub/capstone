"""Technical, explicitly non-clinical model availability for Capstone Stage 2."""
from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import text

from src.model_contract_service import ModelContractService
from src.model_governance import repository
from src.model_governance.errors import GovernanceNotFoundError, GovernanceStateError
from src.model_governance.releases import sha256_file
from src.traceable_inference import ModelCache, TraceableInferenceService

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MAPPING = {
    "0": "uninfected", "1": "parasitized",
    "positive_class": 1, "positive_label": "parasitized",
}


class Stage2ModelAvailabilityService:
    def __init__(self, connection_factory, model_loader=None, cache=None, *,
                 environment="stage2", alias="default",
                 deployment_name="malaria-stage2-classifier",
                 production_scope="stage2_experimental", release_channel="stage2"):
        self.connection_factory = connection_factory
        self.model_loader = model_loader or TraceableInferenceService._load
        self.cache = cache or ModelCache(maxsize=4)
        self.contract = ModelContractService(connection_factory, model_loader=self.model_loader)
        self.environment=environment;self.alias=alias;self.deployment_name=deployment_name
        self.production_scope=production_scope;self.release_channel=release_channel

    @property
    def technical_production(self):
        return self.environment=="production" and self.alias=="champion"

    @staticmethod
    def _id(value):
        return str(UUID(str(value)))

    @staticmethod
    def _fixture(row):
        metadata = dict(row.get("metadata") or {})
        name = str(row.get("run_name") or "").lower()
        model = str(row.get("model_name") or "").lower()
        known = {"db_smoke_test_run", "db_smoke_test_model"}
        return bool(metadata.get("is_test_fixture")) or name in known or model in known

    def _training(self, training_run_id):
        with self.connection_factory() as connection:
            row = connection.execute(text("""
              SELECT r.*,COALESCE(m.name,r.execution_parameters->>'model_name',
                r.parameters->>'model_name',r.metadata->>'model_name') model_name
              FROM runs r LEFT JOIN models m ON m.id=r.model_id
              WHERE r.id=CAST(:id AS uuid)"""),{"id":training_run_id}).mappings().one_or_none()
        if not row: raise GovernanceNotFoundError("training run inexistente")
        return dict(row)

    def preview(self, training_run_id):
        training_run_id=self._id(training_run_id);training=self._training(training_run_id)
        blockers=[];warnings=(
          ["Modelo productivo técnico para Etapa 2; no constituye validación clínica ni autorización sanitaria."]
          if self.technical_production else [])
        if training["run_type"]!="training":blockers.append({"code":"INVALID_RUN_TYPE","message":"La ejecución no es TRAIN."})
        if training["status"]!="completed":blockers.append({"code":"TRAINING_NOT_COMPLETED","message":"El entrenamiento no está completed."})
        fixture=self._fixture(training)
        if fixture:blockers.append({"code":"TECHNICAL_FIXTURE","message":"Ejecución técnica sin modelo desplegable."})
        with self.connection_factory() as connection:
            versions=connection.execute(text("SELECT id::text FROM model_versions WHERE training_run_id=:id ORDER BY created_at"),{"id":training_run_id}).scalars().all()
            active=connection.execute(text("""SELECT d.id::text FROM deployed_model_versions d
              JOIN model_versions mv ON mv.id=d.model_version_id
              WHERE mv.training_run_id=:id AND d.environment=:environment AND d.alias=:alias
                AND (:scope='stage2_experimental' OR d.metadata->>'production_scope'=:scope)
                AND d.status='active' ORDER BY d.deployed_at DESC LIMIT 1"""),
              {"id":training_run_id,"environment":self.environment,"alias":self.alias,
               "scope":self.production_scope}).scalar_one_or_none()
        if len(versions)!=1:
            blockers.append({"code":"MODEL_VERSION_REQUIRED","message":"Debe existir exactamente una model_version gobernada para este training."})
            return {"training_run_id":training_run_id,"eligible":False,"available":bool(active),
              "next_action":"unavailable","action_label":"No disponible","blockers":blockers,
              "warnings":warnings,"model_version_id":versions[0] if len(versions)==1 else None,
              "deployment_id":active,"fixture":fixture}
        model_version_id=str(versions[0])
        try: package=self.contract.candidates(model_version_id)
        except Exception as exc:
            blockers.append({"code":"PACKAGE_PREVIEW_FAILED","message":str(exc)})
            package=None
        if package:
            for field in package["fields"][:4]:
                if field["status"] not in {"complete","ready"}:
                    blockers.append({"code":f"MISSING_{field['key'].upper()}","message":f"No se pudo resolver {field['label']}."})
            mapping_field=next(item for item in package["fields"] if item["key"]=="class_mapping")
            mapping=mapping_field.get("current_value") or mapping_field.get("proposed_value") or {}
            if any(mapping.get(key)!=value for key,value in EXPECTED_MAPPING.items()):
                blockers.append({"code":"CLASS_MAPPING_INVALID","message":"La convención de clases es incompatible."})
            if package.get("artifact_inspection_error"):
                blockers.append({"code":"MODEL_NOT_LOADABLE","message":package["artifact_inspection_error"]})
            if not package["production_package"]["evaluation_run_ids"]:
                warnings.append("Sin evaluación clínica formal")
            threshold=next(item for item in package["fields"] if item["key"]=="threshold_profile_id")
            if not threshold["candidates"]:
                warnings.append("Threshold operativo 0.5 no calibrado clínicamente")
        action="view_stage2_model" if active else ("enable_for_stage2" if not blockers else "unavailable")
        enable_label="Publicar como modelo productivo" if self.technical_production else "Habilitar para Etapa 2"
        view_label="Ver modelo productivo" if self.technical_production else "Ver modelo Etapa 2"
        return {"training_run_id":training_run_id,"eligible":not blockers,"available":bool(active),
          "next_action":action,"action_label":view_label if active else (enable_label if not blockers else "No disponible"),
          "blockers":blockers,"warnings":warnings,"model_version_id":model_version_id,
          "deployment_id":str(active) if active else None,"fixture":fixture,"package":package}

    @staticmethod
    def _atomic_copy(source:Path,target:Path,expected_hash:str):
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            if sha256_file(target)!=expected_hash:
                raise GovernanceStateError("la ubicación inmutable contiene bytes diferentes")
            return
        temp=target.with_suffix(f".tmp-{os.getpid()}")
        shutil.copy2(source,temp)
        if sha256_file(temp)!=expected_hash:
            temp.unlink(missing_ok=True);raise GovernanceStateError("SHA-256 incorrecto después de copiar")
        os.replace(temp,target)

    @staticmethod
    def _write_json(path:Path,payload):
        temp=path.with_suffix(f"{path.suffix}.tmp-{os.getpid()}")
        temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
        os.replace(temp,path)

    def _stage2_artifact(self, preview):
        package=preview["package"];model_version_id=preview["model_version_id"]
        row=self.contract._load(model_version_id)
        source=Path(row["artifact_path"])
        if not source.is_absolute():source=PROJECT_ROOT/source
        if not source.is_file() or sha256_file(source)!=package["production_package"]["artifact_sha256"]:
            raise GovernanceStateError("artifact fuente inexistente o con SHA inválido")
        relative=Path("releases")/self.release_channel/package["model_name"]/model_version_id/"model.keras"
        target=PROJECT_ROOT/relative
        self._atomic_copy(source,target,package["production_package"]["artifact_sha256"])
        artifact_uri=f"{self.release_channel}://{package['model_name']}/{model_version_id}/model.keras"
        with self.connection_factory() as connection:
            artifact=connection.execute(text("""SELECT id::text FROM artifacts WHERE run_id=:run
              AND artifact_uri=:uri AND checksum=:sha ORDER BY created_at LIMIT 1"""),
              {"run":preview["training_run_id"],"uri":artifact_uri,
               "sha":package["production_package"]["artifact_sha256"]}).scalar_one_or_none()
            if not artifact:
                artifact=connection.execute(text("""INSERT INTO artifacts(run_id,artifact_type,name,path,mime_type,
              file_size_bytes,checksum,artifact_uri,artifact_status,metadata)
              VALUES(:run,'model_checkpoint','stage2_model.keras',:path,'application/octet-stream',
                :size,:sha,:uri,'available',CAST(:metadata AS jsonb))
              RETURNING id::text"""),{"run":preview["training_run_id"],
                "path":str(relative),"size":target.stat().st_size,"sha":package["production_package"]["artifact_sha256"],
                "uri":artifact_uri,
                "metadata":json.dumps({"source":"stage2_immutable_copy","source_artifact_id":package["production_package"]["artifact_id"]})}).scalar_one_or_none()
            # The governed (model_version, checkpoint_artifact) pair is already
            # referenced by lineage and is intentionally immutable. The Stage 2
            # copy is a package artifact, never a replacement identity.
        return target,relative,str(artifact)

    def enable(self,training_run_id,*,actor,reason,confirm_stage2_enablement,
               preprocessing_candidate_id=None,threshold_candidate_id=None,source_image_id=None):
        if not actor or not reason:raise GovernanceStateError("publicación técnica exige actor y motivo")
        if not confirm_stage2_enablement:raise GovernanceStateError("confirmación explícita requerida")
        preview=self.preview(training_run_id)
        if preview["available"]:
            current=self._result(preview["deployment_id"],idempotent=True)
            if current["available_for_inference"]:
                if self.technical_production and not current["warnings"]:
                    with self.connection_factory() as connection:
                        connection.execute(text("""UPDATE deployed_model_versions SET metadata=jsonb_set(
                          metadata,'{stage2,warnings}',CAST(:warnings AS jsonb),true) WHERE id=:id"""),
                          {"id":preview["deployment_id"],"warnings":json.dumps(preview["warnings"])})
                    current=self._result(preview["deployment_id"],idempotent=True)
                return current
            with self.connection_factory() as connection:
                metadata=connection.execute(text("SELECT metadata FROM deployed_model_versions WHERE id=:id"),
                  {"id":preview["deployment_id"]}).scalar_one()
            smoke=dict(metadata or {}).get("technical_smoke_test") or dict(metadata or {}).get("stage2_smoke_test") or {}
            if smoke.get("status")!="PASS" or not smoke.get("source_image_id"):
                raise GovernanceStateError("deployment activo sin verificación técnica recuperable")
            inference=TraceableInferenceService(connection_factory=self.connection_factory,cache=self.cache).infer(
              deployed_model_version_id=preview["deployment_id"],source_image_id=smoke["source_image_id"])
            with self.connection_factory() as connection:
                connection.execute(text("""UPDATE deployed_model_versions SET metadata=metadata||
                  CAST(:audit AS jsonb) WHERE id=:id"""),{"id":preview["deployment_id"],"audit":json.dumps({
                    "technical_verification":{"status":"PASS","inference_run_id":inference["inference_run_id"],
                      "image_analysis_job_id":inference["image_analysis_job_id"]},
                    "recovered_at":datetime.now(UTC).isoformat()})})
            return self._result(preview["deployment_id"],idempotent=True)
        if not preview["eligible"]:raise GovernanceStateError("; ".join(item["message"] for item in preview["blockers"]))
        target,relative,artifact_id=self._stage2_artifact(preview)
        package=self.contract.candidates(preview["model_version_id"])
        selections={item["key"]:item["proposed_source_id"] for item in package["fields"] if item.get("proposed_source_id")}
        if preprocessing_candidate_id:selections["preprocessing_profile_snapshot"]=preprocessing_candidate_id
        threshold_field=next(item for item in package["fields"] if item["key"]=="threshold_profile_id")
        threshold_value=0.5;threshold_source="stage2_operational_default";threshold_id=None
        if threshold_candidate_id:selections["threshold_profile_id"]=threshold_candidate_id
        if threshold_field["candidates"]:
            selected=next((item for item in threshold_field["candidates"] if item["source_id"]==(threshold_candidate_id or threshold_field.get("proposed_source_id"))),None)
            if selected:
                threshold_id=selected["source_id"];threshold_value=float(selected["value"]["threshold"]);threshold_source=selected["source"]
        if not threshold_id:
            with self.connection_factory() as connection:
                threshold_id=connection.execute(text("""INSERT INTO run_threshold_calibration(
                  run_id,model_name,threshold_policy,threshold_source,threshold_selected,
                  default_threshold,calibration_split,metadata,model_version_id,
                  score_name,positive_label,calibration_status)
                  VALUES(:run,:model,'stage2_operational','stage2_operational_default',0.5,0.5,'val',
                    CAST(:metadata AS jsonb),CAST(:mv AS uuid),'probability_parasitized',
                    'parasitized','recorded') RETURNING run_threshold_calibration_id::text"""),
                  {"run":preview["training_run_id"],"model":package["model_name"],
                   "mv":preview["model_version_id"],"metadata":json.dumps({
                     "usage":"stage2_technical","clinical_calibration":False,
                     "warning":"Threshold operativo por defecto; no es umbral clínico."})}).scalar_one()
            selections["threshold_profile_id"]=threshold_id
        def selected_value(key):
            field=next(item for item in package["fields"] if item["key"]==key)
            return field.get("current_value") or field.get("proposed_value") or {}
        if package["status"]=="discovered":
            completed=self.contract.complete(preview["model_version_id"],selections,actor,reason)
            manifest=completed.get("manifest") or {}
        else:
            manifest={"schema_version":1,"model_version_id":preview["model_version_id"],
              "training_run_id":preview["training_run_id"],"checkpoint_artifact_id":package["production_package"]["artifact_id"],
              "artifact_sha256":package["production_package"]["artifact_sha256"],
              "artifact_size_bytes":package["production_package"]["artifact_size_bytes"],
              "framework":package["production_package"]["framework"],
              "framework_version":package["production_package"]["framework_version"],
              "preprocessing_profile_snapshot":selected_value("preprocessing_profile_snapshot"),
              "class_mapping":selected_value("class_mapping"),"input_signature":selected_value("input_signature"),
              "output_signature":selected_value("output_signature"),"threshold_profile_id":threshold_id,
              "created_at":datetime.now(UTC).isoformat()}
            with self.connection_factory() as connection:
                connection.execute(text("""UPDATE run_threshold_calibration SET model_version_id=:mv
                  WHERE run_threshold_calibration_id=:threshold AND model_version_id IS NULL"""),
                  {"mv":preview["model_version_id"],"threshold":threshold_id})
                connection.execute(text("""UPDATE artifacts SET artifact_status='available',
                  metadata=metadata||CAST(:audit AS jsonb) WHERE id=:artifact"""),
                  {"artifact":package["production_package"]["artifact_id"],"audit":json.dumps({
                    "verified_sha256":package["production_package"]["artifact_sha256"],
                    "technical_production_verified_at":datetime.now(UTC).isoformat()})})
        stage2_manifest={**manifest,"usage":self.production_scope,"clinical_approved":False,
          "production_scope":self.production_scope,
          "threshold":{"value":threshold_value,"source":threshold_source,"clinical_calibration":threshold_source not in {"stage2_operational_default","stage2_default"}},
          "warnings":preview["warnings"]}
        self._write_json(target.parent/"manifest.json",stage2_manifest)
        self._write_json(target.parent/"preprocessing.json",manifest.get("preprocessing_profile_snapshot",{}))
        self._write_json(target.parent/"class_mapping.json",manifest.get("class_mapping",{}))
        self._write_json(target.parent/"signatures.json",{"input":manifest.get("input_signature",{}),"output":manifest.get("output_signature",{})})
        self._write_json(target.parent/"threshold.json",stage2_manifest["threshold"])
        (target.parent/"checksums.sha256").write_text(f"{sha256_file(target)}  model.keras\n",encoding="utf-8")
        with self.connection_factory() as connection:
            existing=connection.execute(text("""SELECT * FROM deployed_model_versions WHERE model_version_id=:mv
              AND deployment_name=:name AND environment=:environment AND alias=:alias
              AND metadata->>'production_scope'=:scope
              AND status IN ('pending','inactive') ORDER BY created_at DESC LIMIT 1"""),
              {"mv":preview["model_version_id"],"name":self.deployment_name,
               "environment":self.environment,"alias":self.alias,"scope":self.production_scope}).mappings().one_or_none()
            if existing:deployment=dict(existing)
            else:
                entity=repository.create_deployed_model_version(model_version_id=preview["model_version_id"],
                  deployment_name=self.deployment_name,environment=self.environment,alias=self.alias,
                  threshold_value=threshold_value,threshold_calibration_id=threshold_id,
                  threshold_profile_snapshot=stage2_manifest["threshold"],
                  preprocessing_profile_snapshot=manifest["preprocessing_profile_snapshot"],
                  label_mapping_snapshot=manifest["class_mapping"],deployed_by=actor,
                  deployment_reason=reason,metadata={"production_scope":self.production_scope,
                    "technical_contract":{"input_signature":manifest["input_signature"],
                      "output_signature":manifest["output_signature"],
                      "preprocessing":manifest["preprocessing_profile_snapshot"],
                      "class_mapping":manifest["class_mapping"]},
                    "stage2":{"eligible":True,"warnings":preview["warnings"],"artifact_id":artifact_id}},
                  connection_or_session=connection)
                deployment={"id":entity.id}
        deployment_id=str(deployment["id"])
        smoke=self._smoke(deployment_id,source_image_id,actor,preview["warnings"])
        if smoke["status"]!="PASS":raise GovernanceStateError("verificación técnica FAIL")
        self._activate(deployment_id,actor,reason)
        inference=TraceableInferenceService(connection_factory=self.connection_factory,cache=self.cache).infer(
          deployed_model_version_id=deployment_id,source_image_id=smoke["source_image_id"])
        with self.connection_factory() as connection:
            connection.execute(text("""UPDATE deployed_model_versions SET metadata=metadata||
              CAST(:audit AS jsonb) WHERE id=:id"""),{"id":deployment_id,"audit":json.dumps({
                "technical_verification":{"status":"PASS","inference_run_id":inference["inference_run_id"],
                  "image_analysis_job_id":inference["image_analysis_job_id"]},"enabled_by":actor,
                "enabled_at":datetime.now(UTC).isoformat()})})
        return self._result(deployment_id)

    def _smoke(self,deployment_id,source_image_id,actor,warnings):
        with self.connection_factory() as connection:
            row=connection.execute(text("""SELECT d.*,a.path artifact_path,mv.input_signature,
              mv.preprocessing_profile_snapshot,mv.class_mapping FROM deployed_model_versions d
              JOIN model_versions mv ON mv.id=d.model_version_id JOIN artifacts a ON a.id=d.checkpoint_artifact_id
              WHERE d.id=:id"""),{"id":deployment_id}).mappings().one()
            if not source_image_id:source_image_id=connection.execute(text("SELECT image_id::text FROM dataset_split_images ORDER BY created_at,image_id LIMIT 1")).scalar_one()
            image=connection.execute(text("""SELECT COALESCE(absolute_path,dataset_dir||'/'||relative_path)
              FROM dataset_split_images WHERE image_id=:id"""),{"id":self._id(source_image_id)}).scalar_one()
        try:
            artifact=Path(row["artifact_path"]);artifact=artifact if artifact.is_absolute() else PROJECT_ROOT/artifact
            image_path=Path(image);image_path=image_path if image_path.is_absolute() else PROJECT_ROOT/image_path
            if sha256_file(artifact)!=row["artifact_sha256"]:raise ValueError("SHA-256 incorrecto")
            technical=dict(row.get("metadata") or {}).get("technical_contract") or {}
            preprocessing=dict(row["preprocessing_profile_snapshot"] or {}) or dict(technical.get("preprocessing") or {})
            input_signature=dict(row["input_signature"] or {}) or dict(technical.get("input_signature") or {})
            model=self.model_loader(artifact)
            probability=float(TraceableInferenceService._predict(model,image_path,preprocessing,input_signature))
            if not 0<=probability<=1:raise ValueError("probabilidad fuera de rango")
            predicted=1 if probability>=float(row["threshold_value"]) else 0
            evidence={"status":"PASS","source_image_id":str(source_image_id),"probability_parasitized":probability,
              "predicted_class":predicted,"threshold":float(row["threshold_value"]),"timestamp":datetime.now(UTC).isoformat(),
              "actor":actor,"warnings":warnings}
        except Exception as exc:
            evidence={"status":"FAIL","source_image_id":str(source_image_id),"error":f"{type(exc).__name__}: {exc}",
              "timestamp":datetime.now(UTC).isoformat(),"actor":actor,"warnings":warnings}
        with self.connection_factory() as connection:
            connection.execute(text("""UPDATE deployed_model_versions SET metadata=jsonb_set(
              jsonb_set(metadata,'{technical_smoke_test}',CAST(:evidence AS jsonb),true),
              '{stage2_smoke_test}',CAST(:evidence AS jsonb),true) WHERE id=:id"""),
              {"id":deployment_id,"evidence":json.dumps(evidence)})
        return evidence

    def _activate(self,deployment_id,actor,reason):
        with self.connection_factory() as connection:
            row=connection.execute(text("SELECT * FROM deployed_model_versions WHERE id=:id FOR UPDATE"),{"id":deployment_id}).mappings().one()
            smoke=dict(row["metadata"] or {}).get("technical_smoke_test") or {}
            if smoke.get("status")!="PASS":raise GovernanceStateError("verificación técnica PASS requerida")
            connection.execute(text("""UPDATE deployed_model_versions SET status='inactive',
              metadata=metadata||CAST(:audit AS jsonb)
              WHERE environment=:environment AND alias=:alias AND status='active' AND id<>:id
                AND (:technical OR deployment_name=:name)"""),
              {"id":deployment_id,"name":self.deployment_name,"environment":self.environment,
               "alias":self.alias,"technical":self.technical_production,
               "audit":json.dumps({"last_audit_event":"technical_production_replaced","at":datetime.now(UTC).isoformat()})})
            connection.execute(text("""UPDATE deployed_model_versions SET status='active',deployed_at=NOW(),
              deployed_by=:actor,deployment_reason=:reason WHERE id=:id"""),
              {"id":deployment_id,"actor":actor,"reason":reason})

    def _result(self,deployment_id,idempotent=False):
        with self.connection_factory() as connection:
            row=dict(connection.execute(text("""SELECT d.*,mv.training_run_id,mv.model_name,mv.version_number
              FROM deployed_model_versions d JOIN model_versions mv ON mv.id=d.model_version_id
              WHERE d.id=:id"""),{"id":deployment_id}).mappings().one())
        metadata=dict(row.get("metadata") or {});smoke=metadata.get("technical_smoke_test") or metadata.get("stage2_smoke_test") or {}
        verification=metadata.get("technical_verification") or metadata.get("stage2_verification") or {}
        with self.connection_factory() as connection:
            rollback_available=bool(connection.execute(text("""SELECT 1 FROM deployed_model_versions
              WHERE environment=:environment AND alias=:alias
                AND (:technical OR deployment_name=:name)
                AND status IN ('inactive','retired') AND id<>:id LIMIT 1"""),
              {"name":row["deployment_name"],"environment":row["environment"],
               "alias":row["alias"],"technical":self.technical_production,
               "id":deployment_id}).scalar_one_or_none())
        return {"training_run_id":str(row["training_run_id"]),"model_version_id":str(row["model_version_id"]),
          "deployment_id":str(row["id"]),"environment":row["environment"],"alias":row["alias"],
          "status":row["status"],"artifact_sha256":row["artifact_sha256"],"smoke_status":smoke.get("status"),
          "production_scope":metadata.get("production_scope",self.production_scope),
          "available_for_stage2":row["status"]=="active" and smoke.get("status")=="PASS" and verification.get("status")=="PASS",
          "available_for_inference":row["status"]=="active" and smoke.get("status")=="PASS" and verification.get("status")=="PASS",
          "technical_verification":smoke.get("status"),
          "verification_inference":verification,"warnings":metadata.get("stage2",{}).get("warnings",[]),
          "rollback_available":rollback_available,"idempotent":idempotent}

    def models(self):
        with self.connection_factory() as connection:
            rows=connection.execute(text("""SELECT d.*,mv.training_run_id,mv.model_name,mv.version_number
              FROM deployed_model_versions d JOIN model_versions mv ON mv.id=d.model_version_id
              WHERE d.environment=:environment AND d.alias=:alias AND d.status='active'
                AND (:scope='stage2_experimental' OR d.metadata->>'production_scope'=:scope)
              ORDER BY d.deployed_at DESC"""),
              {"environment":self.environment,"alias":self.alias,"scope":self.production_scope}).mappings().all()
        return [self._result(str(row["id"])) for row in rows]
