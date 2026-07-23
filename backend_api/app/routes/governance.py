from __future__ import annotations
import sys
from pathlib import Path
from uuid import UUID
from contextlib import contextmanager
from fastapi import APIRouter,Header,HTTPException,Query
from pydantic import BaseModel,ConfigDict
from app.db import fetch_all,fetch_one,get_engine,resolve_datasource
from app.services.serialization import row_to_dict,rows_to_list

CAPSTONE_ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(CAPSTONE_ROOT/"malaria_dl_local_project"))
from src.model_deployment_service import ModelDeploymentService
from src.model_contract_service import ModelContractService
from src.model_release_lifecycle_service import ModelReleaseLifecycleService
from src.prepare_model_release_service import PrepareModelReleaseService
from src.stage2_model_availability_service import Stage2ModelAvailabilityService
from src.traceable_inference import ModelCache,TraceableInferenceService

MODEL_CACHE=ModelCache(maxsize=4)
DEPLOYMENT_SERVICE=ModelDeploymentService(model_cache=MODEL_CACHE)
INFERENCE_SERVICE=TraceableInferenceService(cache=MODEL_CACHE)

router=APIRouter(prefix="/api",tags=["model-governance"])
def uid(value):
    try:return str(UUID(str(value)))
    except ValueError as exc:raise HTTPException(422,"UUID inválido") from exc
def safe(call):
    try:return call()
    except HTTPException:raise
    except Exception as exc:raise HTTPException(409,f"Operación rechazada: {exc}") from exc

class DeploymentCreate(BaseModel):
    model_config=ConfigDict(extra="forbid")
    model_version_id:str;deployment_name:str;environment:str;alias:str;threshold_profile_id:str;deployed_by:str|None=None;metadata:dict={};activate:bool=False;dry_run:bool=False
class Transition(BaseModel):
    model_config=ConfigDict(extra="forbid")
    actor:str|None=None;reason:str|None=None;confirm_production:bool=False
class ModelVersionTransition(BaseModel):
    model_config=ConfigDict(extra="forbid")
    actor:str|None=None;reason:str|None=None;threshold_profile_id:str|None=None
class SmokeTestRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    source_image_id:str;actor:str|None=None
class RollbackRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    target_deployment_id:str;actor:str|None=None;reason:str|None=None
class ImageJobCreate(BaseModel):
    model_config=ConfigDict(extra="forbid")
    deployed_model_version_id:str|None=None;deployment_name:str|None=None;environment:str|None=None;alias:str|None=None;source_image_id:str
class PrepareReleaseRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    target_environment:str|None=None
class CompleteContractRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    selections:dict[str,str]={};actor:str;reason:str
class PublishProductionRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    deployment_name:str="malaria-classifier";alias:str="champion"
    actor:str;reason:str;confirm_production:bool=False;source_image_id:str|None=None
class Stage2EnableRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    actor:str;reason:str;confirm_stage2_enablement:bool=False
    preprocessing_candidate_id:str|None=None
    threshold_candidate_id:str|None=None
    source_image_id:str|None=None
class TechnicalProductionRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    actor:str;reason:str;confirm_publication:bool=False
    preprocessing_profile:str|None=None
    threshold:float|None=None
    source_image_id:str|None=None

def prepare_release_service(datasource:str|None):
    key=resolve_datasource(datasource)
    @contextmanager
    def connection_factory():
        with get_engine(key).begin() as connection:
            yield connection
    return PrepareModelReleaseService(connection_factory=connection_factory)

def governance_services(datasource:str|None):
    key=resolve_datasource(datasource)
    @contextmanager
    def connection_factory():
        with get_engine(key).begin() as connection:
            yield connection
    deployment=ModelDeploymentService(connection_factory=connection_factory,model_cache=MODEL_CACHE)
    return deployment,ModelReleaseLifecycleService(connection_factory),TraceableInferenceService(connection_factory=connection_factory,cache=MODEL_CACHE)

def contract_service(datasource:str|None):
    key=resolve_datasource(datasource)
    @contextmanager
    def connection_factory():
        with get_engine(key).begin() as connection:
            yield connection
    return ModelContractService(connection_factory)

def stage2_service(datasource:str|None):
    key=resolve_datasource(datasource)
    @contextmanager
    def connection_factory():
        with get_engine(key).begin() as connection:
            yield connection
    return Stage2ModelAvailabilityService(connection_factory,cache=MODEL_CACHE)

def technical_production_service(datasource:str|None):
    key=resolve_datasource(datasource)
    @contextmanager
    def connection_factory():
        with get_engine(key).begin() as connection:
            yield connection
    return Stage2ModelAvailabilityService(
      connection_factory,cache=MODEL_CACHE,environment="production",alias="champion",
      deployment_name="malaria-classifier",production_scope="stage2_technical",
      release_channel="production",
    )

@router.get("/training-runs/{training_run_id}/promotion-status")
def promotion_status(training_run_id:str,datasource:str|None=Query("malaria")):
    try:
        return prepare_release_service(datasource).promotion_status(uid(training_run_id))
    except HTTPException:raise
    except Exception as exc:raise HTTPException(409,{"code":"PROMOTION_STATUS_FAILED","message":type(exc).__name__}) from exc

@router.post("/training-runs/{training_run_id}/prepare-release")
def prepare_release(
    training_run_id:str,
    body:PrepareReleaseRequest|None=None,
    datasource:str|None=Query("malaria"),
    requester:str|None=Header(None,alias="X-Requester"),
    request_id:str|None=Header(None,alias="X-Request-ID"),
):
    try:
        request_body=body or PrepareReleaseRequest()
        return prepare_release_service(datasource).prepare_release(
            uid(training_run_id),requester=requester,
            target_environment=request_body.target_environment,request_id=request_id,
        )
    except HTTPException:raise
    except Exception as exc:raise HTTPException(409,{"code":"PREPARE_RELEASE_FAILED","message":type(exc).__name__}) from exc

@router.get("/training-runs/{training_run_id}/stage2-availability")
def stage2_availability(training_run_id:str,datasource:str|None=Query("malaria")):
    return safe(lambda:stage2_service(datasource).preview(uid(training_run_id)))

@router.get("/training-runs/{training_run_id}/stage2-package-preview")
def stage2_package_preview(training_run_id:str,datasource:str|None=Query("malaria")):
    return safe(lambda:stage2_service(datasource).preview(uid(training_run_id)))

@router.post("/training-runs/{training_run_id}/enable-stage2")
def enable_stage2(training_run_id:str,body:Stage2EnableRequest,datasource:str|None=Query("malaria")):
    return safe(lambda:stage2_service(datasource).enable(
      uid(training_run_id),actor=body.actor,reason=body.reason,
      confirm_stage2_enablement=body.confirm_stage2_enablement,
      preprocessing_candidate_id=body.preprocessing_candidate_id,
      threshold_candidate_id=body.threshold_candidate_id,
      source_image_id=uid(body.source_image_id) if body.source_image_id else None,
    ))

@router.get("/stage2/models")
def stage2_models(datasource:str|None=Query("malaria")):
    return {"items":stage2_service(datasource).models()}

@router.get("/model-versions/{model_version_id}/technical-production-preview")
def technical_production_preview(model_version_id:str,datasource:str|None=Query("malaria")):
    row=fetch_one(datasource,"SELECT training_run_id::text FROM model_versions WHERE id=CAST(:id AS uuid)",
      {"id":uid(model_version_id)})
    if not row:raise HTTPException(404,"Model version no encontrada")
    return safe(lambda:technical_production_service(datasource).preview(str(row["training_run_id"])))

@router.post("/model-versions/{model_version_id}/publish-technical-production")
def publish_model_technical_production(model_version_id:str,body:TechnicalProductionRequest,datasource:str|None=Query("malaria")):
    row=fetch_one(datasource,"SELECT training_run_id::text FROM model_versions WHERE id=CAST(:id AS uuid)",
      {"id":uid(model_version_id)})
    if not row:raise HTTPException(404,"Model version no encontrada")
    return safe(lambda:technical_production_service(datasource).enable(
      str(row["training_run_id"]),actor=body.actor,reason=body.reason,
      confirm_stage2_enablement=body.confirm_publication,
      preprocessing_candidate_id=body.preprocessing_profile,
      source_image_id=uid(body.source_image_id) if body.source_image_id else None,
    ))

@router.post("/training-runs/{training_run_id}/publish-technical-production")
def publish_training_technical_production(training_run_id:str,body:TechnicalProductionRequest,datasource:str|None=Query("malaria")):
    return safe(lambda:technical_production_service(datasource).enable(
      uid(training_run_id),actor=body.actor,reason=body.reason,
      confirm_stage2_enablement=body.confirm_publication,
      preprocessing_candidate_id=body.preprocessing_profile,
      source_image_id=uid(body.source_image_id) if body.source_image_id else None,
    ))

@router.post("/training-runs/{training_run_id}/build-production-model-version")
def build_production_model_version(
    training_run_id:str,body:PrepareReleaseRequest|None=None,
    datasource:str|None=Query("malaria"),
    requester:str|None=Header(None,alias="X-Requester"),
    request_id:str|None=Header(None,alias="X-Request-ID"),
):
    request_body=body or PrepareReleaseRequest()
    return safe(lambda:prepare_release_service(datasource).prepare_release(
      uid(training_run_id),requester=requester,
      target_environment=request_body.target_environment,request_id=request_id,
    ))

@router.get("/model-versions")
def model_versions(datasource:str|None=Query("malaria")):
    return {"items":rows_to_list(fetch_all(datasource,"""SELECT mv.id,mv.training_run_id,mv.model_name,mv.version_number,mv.status,mv.lineage_status,
      mv.artifact_sha256,mv.artifact_size_bytes,mv.framework,mv.framework_version,mv.class_mapping,mv.input_signature,mv.output_signature,mv.created_at,mv.validated_at,
      evaluation.evaluation_run_id,evaluation.recall_parasitized,evaluation.specificity,evaluation.f2_parasitized,
      threshold.threshold_used,COALESCE(explanation.available,FALSE) explainability_available,
      threshold.threshold_profile_id,
      deployment.id active_deployment_id,deployment.alias deployment_alias,deployment.environment deployment_environment
      FROM model_versions mv
      LEFT JOIN LATERAL(SELECT r.id evaluation_run_id,metric.recall_parasitized,metric.specificity,metric.f2_parasitized
        FROM run_lineage rl JOIN runs r ON r.id=rl.child_run_id LEFT JOIN run_clinical_metrics metric ON metric.run_id=r.id
        WHERE rl.model_version_id=mv.id AND r.run_type='evaluation' ORDER BY r.finished_at DESC NULLS LAST LIMIT 1)evaluation ON TRUE
      LEFT JOIN LATERAL(SELECT calibration.threshold_selected threshold_used,calibration.run_threshold_calibration_id threshold_profile_id FROM run_threshold_calibration calibration
        WHERE calibration.model_version_id=mv.id ORDER BY calibration.created_at DESC LIMIT 1)threshold ON TRUE
      LEFT JOIN LATERAL(SELECT TRUE available FROM run_lineage rl JOIN runs r ON r.id=rl.child_run_id
        WHERE rl.model_version_id=mv.id AND r.run_type='explainability' AND r.status='completed' LIMIT 1)explanation ON TRUE
      LEFT JOIN LATERAL(SELECT d.id,d.alias,d.environment FROM deployed_model_versions d WHERE d.model_version_id=mv.id AND d.status='active' ORDER BY d.deployed_at DESC LIMIT 1)deployment ON TRUE
      ORDER BY mv.created_at DESC"""))}
@router.get("/model-versions/{model_version_id}")
def model_version(model_version_id:str,datasource:str|None=Query("malaria")):
    row=fetch_one(datasource,"""SELECT id,training_run_id,model_name,version_number,status,lineage_status,artifact_sha256,
      artifact_size_bytes,framework,framework_version,preprocessing_profile_snapshot,class_mapping,input_signature,output_signature,created_at,metadata
      FROM model_versions WHERE id=CAST(:id AS uuid)""",{"id":uid(model_version_id)})
    if not row:raise HTTPException(404,"Model version no encontrada")
    return row_to_dict(row)
@router.get("/model-versions/{model_version_id}/lineage")
def model_version_lineage(model_version_id:str,datasource:str|None=Query("malaria")):
    return {"items":rows_to_list(fetch_all(datasource,"""SELECT rl.id,rl.parent_run_id,rl.child_run_id,rl.relationship_type,
      rl.model_version_id,rl.checkpoint_artifact_id,rl.confidence,rl.created_at FROM run_lineage rl WHERE rl.model_version_id=CAST(:id AS uuid) ORDER BY rl.created_at""",{"id":uid(model_version_id)}))}
@router.get("/model-versions/{model_version_id}/contract-candidates")
def model_version_contract_candidates(model_version_id:str,datasource:str|None=Query("malaria")):
    return safe(lambda:contract_service(datasource).candidates(uid(model_version_id)))
@router.get("/model-versions/{model_version_id}/production-package-preview")
def production_package_preview(model_version_id:str,datasource:str|None=Query("malaria")):
    return safe(lambda:contract_service(datasource).candidates(uid(model_version_id)))
@router.post("/model-versions/{model_version_id}/complete-contract")
def complete_model_version_contract(model_version_id:str,body:CompleteContractRequest,datasource:str|None=Query("malaria")):
    return safe(lambda:contract_service(datasource).complete(uid(model_version_id),body.selections,body.actor,body.reason))
@router.post("/model-versions/{model_version_id}/build-production-package")
def build_production_package(model_version_id:str,body:CompleteContractRequest,datasource:str|None=Query("malaria")):
    return safe(lambda:contract_service(datasource).complete(uid(model_version_id),body.selections,body.actor,body.reason))
@router.get("/model-versions/{model_version_id}/production-readiness")
def model_version_production_readiness(model_version_id:str,datasource:str|None=Query("malaria")):
    return safe(lambda:contract_service(datasource).readiness(uid(model_version_id)))
@router.post("/model-versions/{model_version_id}/publish-to-production")
def publish_to_production(model_version_id:str,body:PublishProductionRequest,datasource:str|None=Query("malaria")):
    return safe(lambda:governance_services(datasource)[0].publish_to_production(
      model_version_id=uid(model_version_id),deployment_name=body.deployment_name,
      alias=body.alias,actor=body.actor,reason=body.reason,
      confirm_production=body.confirm_production,
      source_image_id=uid(body.source_image_id) if body.source_image_id else None,
    ))
@router.get("/deployments")
def deployments(datasource:str|None=Query("malaria")):
    return {"items":rows_to_list(fetch_all(datasource,"""SELECT d.*,mv.training_run_id,mv.model_name,mv.version_number,
      mv.status model_version_status FROM deployed_model_versions d JOIN model_versions mv ON mv.id=d.model_version_id
      ORDER BY d.created_at DESC"""))}
@router.get("/deployments/active")
def active_deployments(datasource:str|None=Query("malaria")):
    return {"items":rows_to_list(fetch_all(datasource,"""SELECT d.*,mv.training_run_id,mv.model_name,mv.version_number,
      mv.status model_version_status FROM deployed_model_versions d JOIN model_versions mv ON mv.id=d.model_version_id
      WHERE d.status='active' ORDER BY d.deployment_name,d.environment,d.alias"""))}
@router.get("/models/available")
def available_models(datasource:str|None=Query("malaria"),environment:str|None=None):
    filters=" AND d.environment=:environment" if environment else ""
    return {"items":rows_to_list(fetch_all(datasource,"""SELECT d.*,mv.training_run_id,mv.model_name,mv.version_number,
      mv.status model_version_status FROM deployed_model_versions d JOIN model_versions mv ON mv.id=d.model_version_id
      WHERE d.status='active' AND mv.status IN ('approved','deployed')"""+filters+
      " ORDER BY d.environment,d.deployment_name,d.alias",{"environment":environment} if environment else {}))}
@router.get("/deployments/{deployment_id}")
def deployment(deployment_id:str,datasource:str|None=Query("malaria")):
    row=fetch_one(datasource,"SELECT * FROM deployed_model_versions WHERE id=CAST(:id AS uuid)",{"id":uid(deployment_id)})
    if not row:raise HTTPException(404,"Deployment no encontrado")
    return row_to_dict(row)
@router.get("/deployments/{deployment_id}/readiness")
def deployment_readiness(deployment_id:str,datasource:str|None=Query("malaria")):
    return safe(lambda:governance_services(datasource)[0].readiness(uid(deployment_id)))
@router.post("/model-versions/{model_version_id}/validate")
def validate_model_version(model_version_id:str,body:ModelVersionTransition,datasource:str|None=Query("malaria")):
    if not body.threshold_profile_id:raise HTTPException(422,"threshold_profile_id requerido")
    return safe(lambda:governance_services(datasource)[1].validate(uid(model_version_id),uid(body.threshold_profile_id),body.actor,body.reason))
@router.post("/model-versions/{model_version_id}/approve")
def approve_model_version(model_version_id:str,body:ModelVersionTransition,datasource:str|None=Query("malaria")):
    return safe(lambda:governance_services(datasource)[1].approve(uid(model_version_id),body.actor,body.reason))
@router.post("/model-versions/{model_version_id}/reject")
def reject_model_version(model_version_id:str,body:ModelVersionTransition,datasource:str|None=Query("malaria")):
    return safe(lambda:governance_services(datasource)[1].reject(uid(model_version_id),body.actor,body.reason))
@router.post("/deployments")
def create_deployment(body:DeploymentCreate,datasource:str|None=Query("malaria")):
    def op():
        service=governance_services(datasource)[0];result=service.create(model_version_id=body.model_version_id,deployment_name=body.deployment_name,environment=body.environment,alias=body.alias,threshold_profile_id=body.threshold_profile_id,deployed_by=body.deployed_by,metadata=body.metadata,dry_run=body.dry_run)
        if body.activate and not body.dry_run:result=service.activate(result.id,actor=body.deployed_by)
        return result
    return safe(op)
@router.post("/deployments/{deployment_id}/activate")
def activate(deployment_id:str,body:Transition,datasource:str|None=Query("malaria")):return safe(lambda:governance_services(datasource)[0].activate(uid(deployment_id),actor=body.actor,confirm_production=body.confirm_production))
@router.post("/deployments/{deployment_id}/smoke-test")
def smoke_test(deployment_id:str,body:SmokeTestRequest,datasource:str|None=Query("malaria")):return safe(lambda:governance_services(datasource)[0].smoke_test(uid(deployment_id),uid(body.source_image_id),body.actor))
@router.post("/deployments/{deployment_id}/rollback")
def rollback(deployment_id:str,body:RollbackRequest,datasource:str|None=Query("malaria")):return safe(lambda:governance_services(datasource)[0].rollback(uid(deployment_id),uid(body.target_deployment_id),body.actor,body.reason))
@router.post("/deployments/{deployment_id}/deactivate")
def deactivate(deployment_id:str,body:Transition,datasource:str|None=Query("malaria")):return safe(lambda:governance_services(datasource)[0].transition(uid(deployment_id),"inactive",body.actor,body.reason))
@router.post("/deployments/{deployment_id}/retire")
def retire(deployment_id:str,body:Transition,datasource:str|None=Query("malaria")):return safe(lambda:governance_services(datasource)[0].transition(uid(deployment_id),"retired",body.actor,body.reason))
@router.post("/image-analysis-jobs")
def create_image_job(body:ImageJobCreate,datasource:str|None=None):
    if not body.deployed_model_version_id and not all((body.deployment_name,body.environment,body.alias)):raise HTTPException(422,"deployment id o alias requerido")
    service=governance_services(datasource)[2] if datasource else INFERENCE_SERVICE
    return safe(lambda:service.infer(**body.model_dump()))
@router.get("/image-analysis-jobs/{job_id}")
def image_job(job_id:str,datasource:str|None=Query("malaria")):
    row=fetch_one(datasource,"SELECT * FROM image_analysis_jobs WHERE id=CAST(:id AS uuid)",{"id":uid(job_id)})
    if not row:raise HTTPException(404,"Job no encontrado")
    return row_to_dict(row)
@router.get("/image-analysis-jobs/{job_id}/predictions")
def job_predictions(job_id:str,datasource:str|None=Query("malaria")):
    return {"items":rows_to_list(fetch_all(datasource,"""SELECT id,image_analysis_job_id,model_version_id,deployed_model_version_id,
      prediction_scope,probability_parasitized,probability_uninfected,threshold_used,predicted_class,predicted_label,quality_status,created_at
      FROM predictions WHERE image_analysis_job_id=CAST(:id AS uuid)""",{"id":uid(job_id)}))}
@router.get("/inference-runs/{run_id}")
def inference_run(run_id:str,datasource:str|None=Query("malaria")):
    row=fetch_one(datasource,"""SELECT r.id,r.run_type,r.status,r.backend_version,r.pipeline_version,r.started_at,r.finished_at,
      r.configuration,r.error_message,r.metadata,b.deployed_model_version_id,b.model_version_id FROM runs r
      JOIN run_model_deployments b ON b.run_id=r.id AND b.role='primary' WHERE r.id=CAST(:id AS uuid) AND r.run_type='inference'""",{"id":uid(run_id)})
    if not row:raise HTTPException(404,"Inference run no encontrado")
    return row_to_dict(row)
