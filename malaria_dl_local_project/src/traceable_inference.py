"""Traceable image-level inference. No object detection or synthetic cells."""
from __future__ import annotations
import time
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID
from sqlalchemy import text
from src.model_governance.releases import sha256_file
from src.model_governance import repository
from src.model_deployment_service import ModelDeploymentService

PROJECT_ROOT=Path(__file__).resolve().parents[1]
def _project_path(value):
    path=Path(value)
    return path if path.is_absolute() else PROJECT_ROOT/path

class ModelCache:
    def __init__(self,maxsize=4): self.maxsize=maxsize;self._items=OrderedDict()
    def get_or_load(self,model_version_id,sha256,path,loader):
        key=(str(model_version_id),sha256)
        if key in self._items:self._items.move_to_end(key);return self._items[key]
        value=loader(path);self._items[key]=value
        while len(self._items)>self.maxsize:self._items.popitem(last=False)
        return value
    def invalidate_model_version(self,model_version_id):
        for key in list(self._items):
            if key[0]==str(model_version_id):self._items.pop(key)

class TraceableInferenceService:
    def __init__(self,connection_factory=None,loader=None,predictor=None,cache=None):
        if connection_factory is None:
            from src.db import get_connection
            connection_factory=get_connection
        self.connection_factory=connection_factory;self.loader=loader or self._load;self.predictor=predictor or self._predict;self.cache=cache or ModelCache()
    @staticmethod
    def _load(path):
        import tensorflow as tf
        return tf.keras.models.load_model(path,compile=False)
    @staticmethod
    def _predict(model,image_path,preprocessing,input_signature):
        import numpy as np
        from PIL import Image
        shape=input_signature.get("shape") or input_signature.get("input_shape") or [None,200,200,3]
        height,width=int(shape[-3]),int(shape[-2])
        image=np.asarray(Image.open(image_path).convert("RGB").resize((width,height)),dtype="float32")
        mode=preprocessing.get("mode") or preprocessing.get("preprocessing")
        if mode in {"rescale_0_1","rescale"}:image=image/255.0
        elif mode=="vgg16_imagenet":
            from tensorflow.keras.applications.vgg16 import preprocess_input
            image=preprocess_input(image)
        score=float(model.predict(image[None,...],verbose=0).reshape(-1)[0])
        return score
    def _deployment(self,c,deployment_id):
        row=c.execute(text("""SELECT d.*,mv.model_name,mv.version_number,mv.status model_version_status,mv.lineage_status,
          mv.training_run_id,mv.checkpoint_path,mv.artifact_sha256 model_sha256,mv.framework,mv.input_signature,mv.output_signature,
          mv.preprocessing_profile_snapshot,mv.class_mapping,a.path artifact_path
          FROM deployed_model_versions d JOIN model_versions mv ON mv.id=d.model_version_id
          JOIN artifacts a ON a.id=d.checkpoint_artifact_id WHERE d.id=:id"""),{"id":str(UUID(str(deployment_id)))}).mappings().one_or_none()
        if not row:raise ValueError("deployment inexistente")
        if row["status"]!="active":raise ValueError("deployment no activo")
        return dict(row)
    def infer(self,*,source_image_id,deployed_model_version_id=None,deployment_name=None,environment=None,alias=None):
        if not deployed_model_version_id:
            if not all((deployment_name,environment,alias)):raise ValueError("deployment id o alias controlado requerido")
            deployed_model_version_id=ModelDeploymentService(self.connection_factory).resolve_alias(deployment_name,environment,alias)["id"]
        started=time.perf_counter();run=None;job=None;failure=None
        with self.connection_factory() as c:
            deployment=self._deployment(c,deployed_model_version_id)
            image=c.execute(text("SELECT image_id::text id,COALESCE(absolute_path,dataset_dir||'/'||relative_path) file_path FROM dataset_split_images WHERE image_id=:id"),{"id":str(UUID(str(source_image_id)))}).mappings().one_or_none()
            if not image:raise ValueError("source_image_id inexistente")
            path=_project_path(deployment["artifact_path"]).resolve();image_path=_project_path(image["file_path"]).resolve()
            allowed=(Path(__file__).resolve().parents[1]/"outputs").resolve(),(Path(__file__).resolve().parents[1]/"releases").resolve()
            if not any(path==root or root in path.parents for root in allowed):raise ValueError("artefacto fuera del store autorizado")
            if not path.is_file() or sha256_file(path)!=deployment["model_sha256"]:raise ValueError("integridad del modelo inválida")
            stage2_metadata=dict(deployment.get("metadata") or {}).get("stage2") or {}
            stage2_candidate=(
                (
                  (deployment["environment"]=="stage2" and deployment["alias"]=="default")
                  or (
                    deployment["environment"]=="production" and deployment["alias"]=="champion"
                    and dict(deployment.get("metadata") or {}).get("production_scope")=="stage2_technical"
                  )
                )
                and deployment["model_version_status"] in {"discovered","candidate","validated","approved","deployed"}
                and stage2_metadata.get("eligible") is True
            )
            formally_released=deployment["model_version_status"] in {"approved","validated","deployed"}
            if not (formally_released or stage2_candidate) or deployment["lineage_status"]!="resolved":
                raise ValueError("model version no apta")
            technical=dict(deployment.get("metadata") or {}).get("technical_contract") or {}
            mapping=(dict(deployment["class_mapping"] or {})
              or dict(deployment.get("label_mapping_snapshot") or {})
              or dict(technical.get("class_mapping") or {}))
            if mapping.get("0")!="uninfected" or mapping.get("1")!="parasitized":raise ValueError("class_mapping inválido")
            run=repository.create_inference_run(deployed_model_version_id=deployed_model_version_id,backend_version="backend-api-0.2",pipeline_version="traceable-image-v1",configuration={"model_version_id":str(deployment["model_version_id"]),"sha256":deployment["model_sha256"]},connection_or_session=c)
            job=repository.create_image_analysis_job(inference_run_id=run.id,deployed_model_version_id=deployed_model_version_id,source_image_id=source_image_id,status="running",quality_status="not_assessed",threshold_used=float(deployment["threshold_value"]),threshold_source="deployment_snapshot",started_at=run.started_at or datetime.now(UTC),connection_or_session=c)
            try:
                with c.begin_nested():
                    model=self.cache.get_or_load(deployment["model_version_id"],deployment["model_sha256"],path,self.loader)
                    technical=dict(deployment.get("metadata") or {}).get("technical_contract") or {}
                    preprocessing=dict(deployment["preprocessing_profile_snapshot"] or {}) or dict(technical.get("preprocessing") or {})
                    input_signature=dict(deployment["input_signature"] or {}) or dict(technical.get("input_signature") or {})
                    probability=float(self.predictor(model,image_path,preprocessing,input_signature))
                    if not 0<=probability<=1:raise ValueError("probabilidad fuera de rango")
                    threshold=float(deployment["threshold_value"]);predicted=1 if probability>=threshold else 0;label="parasitized" if predicted else "uninfected"
                    prediction=c.execute(text("""INSERT INTO predictions(run_id,image_id,predicted_label,score,score_positive_label,threshold,
                      image_analysis_job_id,model_version_id,deployed_model_version_id,inference_run_id,classifier_model_version_id,
                      prediction_scope,source_image_id,probability_parasitized,probability_uninfected,threshold_used,predicted_class,
                      quality_status,review_status,metadata) VALUES(:run,:legacy_image,:label,:p,:p,:t,:job,:mv,:dep,:run,:mv,'image',:source_image,:p,:u,:t,:class,'not_assessed','unreviewed',CAST(:metadata AS jsonb)) RETURNING id"""),
                      {"run":run.id,"legacy_image":str(source_image_id),"source_image":str(source_image_id),"label":label,"p":probability,"u":1-probability,"t":threshold,"job":job.id,"mv":str(deployment["model_version_id"]),"dep":str(deployed_model_version_id),"class":predicted,"metadata":'{"stage":"image_classification","object_detection":false}'}).scalar_one()
                elapsed=time.perf_counter()-started
                c.execute(text("UPDATE image_analysis_jobs SET status='completed',completed_at=clock_timestamp(),summary=CAST(:summary AS jsonb),updated_at=clock_timestamp() WHERE id=:id"),{"id":job.id,"summary":f'{{"prediction_id":"{prediction}","processing_time":{elapsed}}}'})
                c.execute(text("UPDATE runs SET status='completed',finished_at=clock_timestamp() WHERE id=:id"),{"id":run.id})
            except Exception as exc:
                if job:c.execute(text("UPDATE image_analysis_jobs SET status='failed',completed_at=clock_timestamp(),error_message=:error WHERE id=:id"),{"id":job.id,"error":type(exc).__name__})
                if run:c.execute(text("UPDATE runs SET status='failed',finished_at=clock_timestamp(),error_message=:error WHERE id=:id"),{"id":run.id,"error":type(exc).__name__})
                failure=exc
        if failure is not None:
            raise RuntimeError(f"inference failed: {type(failure).__name__}: {failure}") from failure
        return {"inference_run_id":str(run.id),"image_analysis_job_id":str(job.id),"deployed_model_version_id":str(deployed_model_version_id),"model_version_id":str(deployment["model_version_id"]),"model_name":deployment["model_name"],"model_version":deployment["version_number"],"probability_parasitized":probability,"probability_uninfected":1-probability,"predicted_class":predicted,"predicted_label":label,"threshold_used":threshold,"threshold_source":"deployment_snapshot","quality_status":"not_assessed","processing_time":elapsed,"warnings":[]}
