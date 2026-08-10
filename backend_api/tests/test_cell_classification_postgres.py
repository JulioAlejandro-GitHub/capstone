from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

import app.audit as audit
import app.routes.cell_classification as classification_routes
import app.security as security
from app.config import Settings
from app.database_safety import assert_capstone_database
from app.db import normalize_sqlalchemy_url
from app.main import app
from app.repositories.cell_classification import CellClassificationRepository
from app.security import Principal
from app.services.cell_crop_storage import CellCropStorage
from app.services.cell_classification import (
    CellClassificationError,
    CellClassificationService,
    freeze_classification_inputs,
)
from app.services.local_storage import LocalStorage
from app.services.productive_model import (
    ProductiveModelResolver,
    ResolvedProductiveModel,
)
from tests.test_cell_detection_postgres import (
    PostgresContext as DetectionPostgresContext,
)


pytestmark = pytest.mark.requires_local_postgres

CLASSIFICATION_TABLES = {
    "cell_classification_runs",
    "cell_classification_inputs",
    "cell_predictions",
    "cell_explanations",
    "smear_analysis_summaries",
    "cell_classification_events",
    "cell_classification_reviews",
}


class TransactionEngine:
    """Expose service transactions as savepoints of one outer test transaction."""

    def __init__(self, connection):
        self.connection = connection

    @contextmanager
    def begin(self):
        with self.connection.begin_nested():
            yield self.connection

    @contextmanager
    def connect(self):
        yield self.connection


def _sqlstate(error: DBAPIError) -> str | None:
    return getattr(error.orig, "sqlstate", None) or getattr(
        error.orig, "pgcode", None
    )


def _request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "path_params": {},
            "headers": [],
            "query_string": b"",
            "server": ("test", 80),
            "client": ("test", 1),
            "scheme": "http",
        }
    )


def _crop_png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (8, 8), (64, 32, 16)).save(output, "PNG")
    return output.getvalue()


class InjectedProductiveResolver:
    """Test-only exact resolver; DB composite lineage remains real."""

    def __init__(self, resolved: ResolvedProductiveModel):
        self.resolved = resolved
        self.load_count = 0

    def resolve(self) -> ResolvedProductiveModel:
        return self.resolved

    def revalidate(
        self, resolved: ResolvedProductiveModel, *, connection
    ) -> ResolvedProductiveModel:
        assert connection.execute(
            text(
                """
                SELECT count(*)
                FROM deployed_model_versions deployment
                JOIN stage2_model_publications publication
                  ON publication.id=:publication_id
                 AND publication.model_version_id=deployment.model_version_id
                WHERE deployment.id=:deployment_id
                  AND deployment.model_version_id=:model_version_id
                """
            ),
            {
                "deployment_id": UUID(resolved.deployment_id),
                "publication_id": UUID(resolved.publication_id),
                "model_version_id": UUID(resolved.model_version_id),
            },
        ).scalar_one() == 1
        return resolved

    def load(self, _resolved: ResolvedProductiveModel):
        self.load_count += 1
        return SimpleNamespace(
            input_shape=(None, 8, 8, 3),
            output_shape=(None, 1),
        )


def _database_counts(connection) -> tuple[int, ...]:
    return tuple(
        connection.execute(
            text(
                """
                SELECT
                  (SELECT count(*) FROM users),
                  (SELECT count(*) FROM models),
                  (SELECT count(*) FROM runs),
                  (SELECT count(*) FROM artifacts),
                  (SELECT count(*) FROM model_versions),
                  (SELECT count(*) FROM run_lineage),
                  (SELECT count(*) FROM stage2_model_publications),
                  (SELECT count(*) FROM deployed_model_versions),
                  (SELECT count(*) FROM research_subjects),
                  (SELECT count(*) FROM microscopy_analysis_runs),
                  (SELECT count(*) FROM cell_detection_runs),
                  (SELECT count(*) FROM image_connected_components),
                  (SELECT count(*) FROM cell_detections),
                  (SELECT count(*) FROM cell_crops),
                  (SELECT count(*) FROM cell_classification_runs),
                  (SELECT count(*) FROM cell_classification_inputs),
                  (SELECT count(*) FROM cell_predictions),
                  (SELECT count(*) FROM cell_explanations),
                  (SELECT count(*) FROM smear_analysis_summaries),
                  (SELECT count(*) FROM cell_classification_events),
                  (SELECT count(*) FROM cell_classification_reviews),
                  (SELECT count(*) FROM audit_events)
                """
            )
        ).one()
    )


@dataclass(frozen=True)
class SeededPrediction:
    classification_run_id: UUID
    classification_input_id: UUID
    prediction_id: UUID
    summary_id: UUID
    event_id: UUID
    detection_run_id: UUID
    analysis_run_id: UUID
    cell_detection_id: UUID
    crop_id: UUID
    deployment_id: UUID
    publication_id: UUID
    model_version_id: UUID
    model_version: str | None
    checkpoint_sha256: str
    manifest_sha256: str


@dataclass
class ClassificationPostgresContext:
    connection: object
    shared_engine: TransactionEngine
    client: TestClient
    headers: dict[str, dict[str, str]]
    principals: dict[str, Principal]
    suffix: str
    settings: Settings
    local_storage: LocalStorage
    analysis_context: DetectionPostgresContext
    detection_runs: dict[int, UUID] = field(default_factory=dict)
    model_fixture: dict | None = None

    def completed_detection(self, count: int = 1) -> dict:
        if count < 1:
            raise ValueError("count debe ser positivo")
        detection_run_id = self.detection_runs.get(count)
        if detection_run_id is None:
            analysis = self.analysis_context.create_analysis()
            detection_run_id = uuid4()
            payload = _crop_png()
            digest = hashlib.sha256(payload).hexdigest()
            self.connection.execute(
                text(
                    """
                    INSERT INTO cell_detection_runs(
                      id,analysis_run_id,detection_run_code,detector_key,
                      detector_version,algorithm_version,profile_snapshot,
                      input_manifest_sha256,status,image_count,
                      processed_image_count,component_count,detection_count,
                      crop_count,warning_count,requested_by,started_at
                    ) VALUES(
                      :id,:analysis_run_id,:code,'postgres_fixture_detector',
                      '1.0.0','postgres-fixture-v1',
                      jsonb_build_object('test_fixture',true),
                      :manifest,'processing',
                      1,0,0,0,0,0,:actor,now()
                    )
                    """
                ),
                {
                    "id": detection_run_id,
                    "analysis_run_id": analysis.analysis_run_id,
                    "code": f"DET-{uuid4().hex[:8].upper()}",
                    "manifest": hashlib.sha256(
                        f"{analysis.analysis_run_id}:{count}".encode()
                    ).hexdigest(),
                    "actor": UUID(
                        self.principals["administrator"].user_id
                    ),
                },
            )
            components: list[dict] = []
            detections: list[dict] = []
            crops: list[dict] = []
            for index in range(1, count + 1):
                component_id = uuid4()
                cell_detection_id = uuid4()
                crop_id = uuid4()
                cell_code = f"CELL-{cell_detection_id.hex[:12].upper()}"
                storage_key = (
                    f"cell-crops/{analysis.analysis_run_id}/"
                    f"{detection_run_id}/{analysis.microscopy_image_id}/"
                    f"{cell_detection_id}/crop.png"
                )
                crop_path = self.local_storage.resolve(storage_key)
                crop_path.parent.mkdir(parents=True, exist_ok=True)
                crop_path.write_bytes(payload)
                components.append(
                    {
                        "id": component_id,
                        "detection_run_id": detection_run_id,
                        "analysis_run_id": analysis.analysis_run_id,
                        "analysis_run_image_id": analysis.analysis_run_image_id,
                        "microscopy_image_id": analysis.microscopy_image_id,
                        "component_index": index,
                    }
                )
                detections.append(
                    {
                        "id": cell_detection_id,
                        "detection_run_id": detection_run_id,
                        "analysis_run_id": analysis.analysis_run_id,
                        "component_id": component_id,
                        "analysis_run_image_id": analysis.analysis_run_image_id,
                        "microscopy_image_id": analysis.microscopy_image_id,
                        "cell_index": index,
                        "cell_code": cell_code,
                    }
                )
                crops.append(
                    {
                        "id": crop_id,
                        "cell_detection_id": cell_detection_id,
                        "storage_key": storage_key,
                        "sha256": digest,
                        "file_size_bytes": len(payload),
                    }
                )
            self.connection.execute(
                text(
                    """
                    INSERT INTO image_connected_components(
                      id,detection_run_id,analysis_run_id,
                      analysis_run_image_id,microscopy_image_id,
                      component_index,bbox_x,bbox_y,bbox_width,bbox_height,
                      centroid_x,centroid_y,area_px,perimeter_px,circularity,
                      solidity,touches_border,component_status,rejection_code,
                      metrics_json
                    ) VALUES(
                      :id,:detection_run_id,:analysis_run_id,
                      :analysis_run_image_id,:microscopy_image_id,
                      :component_index,0,0,8,8,4,4,64,32,0.8,1.0,false,
                      'accepted',NULL,
                      jsonb_build_object('test_fixture',true)
                    )
                    """
                ),
                components,
            )
            self.connection.execute(
                text(
                    """
                    INSERT INTO cell_detections(
                      id,detection_run_id,analysis_run_id,
                      connected_component_id,analysis_run_image_id,
                      microscopy_image_id,cell_index,cell_code,bbox_x,bbox_y,
                      bbox_width,bbox_height,coordinate_space,detector_score,
                      automated_status
                    ) VALUES(
                      :id,:detection_run_id,:analysis_run_id,:component_id,
                      :analysis_run_image_id,:microscopy_image_id,
                      :cell_index,:cell_code,0,0,8,8,
                      'original_image_pixels',0.5,'candidate'
                    )
                    """
                ),
                detections,
            )
            self.connection.execute(
                text(
                    """
                    INSERT INTO cell_crops(
                      id,cell_detection_id,relative_storage_key,sha256,
                      file_size_bytes,width_px,height_px,format,padding_px
                    ) VALUES(
                      :id,:cell_detection_id,:storage_key,:sha256,
                      :file_size_bytes,8,8,'PNG',0
                    )
                    """
                ),
                crops,
            )
            self.connection.execute(
                text(
                    """
                    UPDATE cell_detection_runs
                    SET
                      status='completed',processed_image_count=1,
                      component_count=:count,detection_count=:count,
                      crop_count=:count,completed_at=now(),updated_at=now()
                    WHERE id=:id AND status='processing'
                    """
                ),
                {"id": detection_run_id, "count": count},
            )
            self.detection_runs[count] = detection_run_id

        row = self.connection.execute(
            text(
                """
                SELECT
                  detection_run.id detection_run_id,
                  detection_run.analysis_run_id,
                  detection_run.detector_key,
                  detection_run.detector_version,
                  detection_run.algorithm_version,
                  detection.id cell_detection_id,
                  detection.microscopy_image_id,
                  detection.cell_index,
                  detection.cell_code,
                  run_image.sequence_number image_sequence_number,
                  crop.id crop_id,
                  crop.relative_storage_key crop_storage_key,
                  crop.sha256 crop_sha256,
                  crop.file_size_bytes crop_file_size_bytes,
                  crop.width_px crop_width_px,
                  crop.height_px crop_height_px
                FROM cell_detection_runs detection_run
                JOIN microscopy_analysis_runs analysis
                  ON analysis.id=detection_run.analysis_run_id
                JOIN cell_detections detection
                  ON detection.detection_run_id=detection_run.id
                JOIN microscopy_analysis_run_images run_image
                  ON run_image.id=detection.analysis_run_image_id
                JOIN cell_crops crop
                  ON crop.cell_detection_id=detection.id
                WHERE detection_run.id=:detection_run_id
                  AND analysis.ready_for_analysis=true
                  AND detection_run.status IN (
                    'completed','completed_with_warnings'
                  )
                  AND crop.relative_storage_key IS NOT NULL
                ORDER BY
                  detection_run.completed_at DESC NULLS LAST,
                  run_image.sequence_number,
                  detection.cell_index,
                  detection.id
                LIMIT 1
                """
            ),
            {"detection_run_id": detection_run_id},
        ).mappings().one()
        return dict(row)

    def governed_model(self) -> dict:
        if self.model_fixture is not None:
            return self.model_fixture
        now = datetime.now(UTC)
        model_id = uuid4()
        training_run_id = uuid4()
        evaluation_run_id = uuid4()
        artifact_id = uuid4()
        model_version_id = uuid4()
        publication_id = uuid4()
        deployment_id = uuid4()
        checkpoint_payload = f"checkpoint:{self.suffix}".encode()
        checkpoint_sha256 = hashlib.sha256(checkpoint_payload).hexdigest()
        artifact_path = (
            f"test-artifacts/{training_run_id}/best_model.keras"
        )
        self.connection.execute(
            text(
                """
                INSERT INTO models(id,name,model_type,framework,architecture)
                VALUES(
                  :id,:name,'classifier','keras','postgres-fixture-cnn'
                )
                """
            ),
            {
                "id": model_id,
                "name": f"cell-classification-pg-{self.suffix}",
            },
        )
        self.connection.execute(
            text(
                """
                INSERT INTO runs(
                  id,model_id,run_name,run_type,status,started_at,finished_at,
                  configuration,metadata
                ) VALUES(
                  :training_id,:model_id,:training_name,'training',
                  'completed',:now,:now,'{}'::jsonb,
                  jsonb_build_object('test_fixture',true)
                ),(
                  :evaluation_id,:model_id,:evaluation_name,'evaluation',
                  'completed',:now,:now,'{}'::jsonb,
                  jsonb_build_object('test_fixture',true)
                )
                """
            ),
            {
                "training_id": training_run_id,
                "evaluation_id": evaluation_run_id,
                "model_id": model_id,
                "training_name": f"training-{self.suffix}",
                "evaluation_name": f"evaluation-{self.suffix}",
                "now": now,
            },
        )
        self.connection.execute(
            text(
                """
                INSERT INTO artifacts(
                  id,run_id,artifact_type,name,path,file_size_bytes,checksum,
                  artifact_status,metadata
                ) VALUES(
                  :id,:run_id,'model_checkpoint','best_model.keras',:path,
                  :size,:sha,'available',
                  jsonb_build_object('test_fixture',true)
                )
                """
            ),
            {
                "id": artifact_id,
                "run_id": training_run_id,
                "path": artifact_path,
                "size": len(checkpoint_payload),
                "sha": checkpoint_sha256,
            },
        )
        self.connection.execute(
            text(
                """
                INSERT INTO model_versions(
                  id,model_id,version_name,checkpoint_path,training_run_id,
                  model_name,version_number,checkpoint_artifact_id,
                  artifact_sha256,artifact_size_bytes,framework,
                  framework_version,preprocessing_profile_snapshot,
                  class_mapping,input_signature,output_signature,status,
                  lineage_status,approved_at,metadata
                ) VALUES(
                  :id,:model_id,'1',:path,:training_run_id,:model_name,1,
                  :artifact_id,:sha,:size,'keras','3',
                  jsonb_build_object('mode','rescale_0_1'),
                  jsonb_build_object(
                    '0','uninfected','1','parasitized',
                    'positive_class',1,
                    'positive_label','parasitized'
                  ),
                  jsonb_build_object(
                    'shape',jsonb_build_array(NULL,8,8,3)
                  ),
                  jsonb_build_object(
                    'shape',jsonb_build_array(NULL,1),
                    'activation','sigmoid'
                  ),
                  'approved','resolved',:now,
                  jsonb_build_object('test_fixture',true)
                )
                """
            ),
            {
                "id": model_version_id,
                "model_id": model_id,
                "path": artifact_path,
                "training_run_id": training_run_id,
                "model_name": f"cell-classification-pg-{self.suffix}",
                "artifact_id": artifact_id,
                "sha": checkpoint_sha256,
                "size": len(checkpoint_payload),
                "now": now,
            },
        )
        self.connection.execute(
            text(
                """
                INSERT INTO run_lineage(
                  id,parent_run_id,child_run_id,relationship_type,
                  checkpoint_path,checkpoint_artifact_id,model_version_id,
                  confidence,metadata
                ) VALUES(
                  :id,:training_id,:evaluation_id,
                  'evaluates_checkpoint_from',:path,:artifact_id,
                  :model_version_id,'explicit',
                  jsonb_build_object('test_fixture',true)
                )
                """
            ),
            {
                "id": uuid4(),
                "training_id": training_run_id,
                "evaluation_id": evaluation_run_id,
                "path": artifact_path,
                "artifact_id": artifact_id,
                "model_version_id": model_version_id,
            },
        )
        self.connection.execute(
            text(
                """
                INSERT INTO stage2_model_publications(
                  id,datasource,model_version_id,training_run_id,
                  evaluation_run_id,checkpoint_artifact_id,scope,status,
                  is_active,published_at,published_by,metadata
                ) VALUES(
                  :id,'pytest',:model_version_id,:training_id,:evaluation_id,
                  :artifact_id,'stage2','active',true,:now,'pytest',
                  jsonb_build_object('test_fixture',true)
                )
                """
            ),
            {
                "id": publication_id,
                "model_version_id": model_version_id,
                "training_id": training_run_id,
                "evaluation_id": evaluation_run_id,
                "artifact_id": artifact_id,
                "now": now,
            },
        )
        self.connection.execute(
            text(
                """
                INSERT INTO deployed_model_versions(
                  id,model_version_id,checkpoint_artifact_id,
                  threshold_calibration_id,deployment_name,environment,alias,
                  artifact_sha256,artifact_size_bytes,threshold_value,
                  threshold_profile_snapshot,preprocessing_profile_snapshot,
                  image_quality_policy_snapshot,label_mapping_snapshot,
                  positive_label,score_name,status,deployed_at,deployed_by,
                  deployment_reason,metadata
                ) VALUES(
                  :id,:model_version_id,:artifact_id,NULL,:deployment_name,
                  'test','postgres-fixture',:sha,:size,0.5,
                  jsonb_build_object(
                    'value',0.5,
                    'source','postgres_contract_fixture'
                  ),
                  jsonb_build_object('mode','rescale_0_1'),
                  '{}'::jsonb,
                  jsonb_build_object(
                    '0','uninfected','1','parasitized',
                    'positive_class',1,
                    'positive_label','parasitized'
                  ),
                  'parasitized','probability_parasitized','active',:now,
                  'pytest','transactional PostgreSQL contract fixture',
                  jsonb_build_object('test_fixture',true)
                )
                """
            ),
            {
                "id": deployment_id,
                "model_version_id": model_version_id,
                "artifact_id": artifact_id,
                "deployment_name": (
                    f"cell-classification-pg-{self.suffix}"
                ),
                "sha": checkpoint_sha256,
                "size": len(checkpoint_payload),
                "now": now,
            },
        )
        checkpoint_path = (
            self.local_storage.root
            / "test-artifacts"
            / str(training_run_id)
            / "best_model.keras"
        )
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_bytes(checkpoint_payload)
        self.model_fixture = {
            "publication_id": publication_id,
            "model_version_id": model_version_id,
            "checkpoint_artifact_id": artifact_id,
            "model_name": f"cell-classification-pg-{self.suffix}",
            "model_version": "1",
            "checkpoint_sha256": checkpoint_sha256,
            "checkpoint_size_bytes": len(checkpoint_payload),
            "deployment_id": deployment_id,
            "training_run_id": training_run_id,
            "evaluation_run_id": evaluation_run_id,
            "checkpoint_path": checkpoint_path,
            "published_at": now,
        }
        return self.model_fixture

    def resolved_model(self) -> ResolvedProductiveModel:
        model = self.governed_model()
        return ResolvedProductiveModel(
            deployment_id=str(model["deployment_id"]),
            deployment_name=f"cell-classification-pg-{self.suffix}",
            publication_id=str(model["publication_id"]),
            model_version_id=str(model["model_version_id"]),
            model_name=str(model["model_name"]),
            model_version=str(model["model_version"]),
            source_training_run_id=str(model["training_run_id"]),
            source_evaluation_run_id=str(model["evaluation_run_id"]),
            checkpoint_artifact_id=str(model["checkpoint_artifact_id"]),
            checkpoint_path=Path(model["checkpoint_path"]),
            checkpoint_sha256=str(model["checkpoint_sha256"]),
            checkpoint_size_bytes=int(model["checkpoint_size_bytes"]),
            framework="keras",
            framework_version="3",
            architecture="postgres-fixture-cnn",
            input_width=8,
            input_height=8,
            input_channels=3,
            input_signature={"shape": [None, 8, 8, 3]},
            output_signature={
                "shape": [None, 1],
                "activation": "sigmoid",
            },
            preprocessing={"mode": "rescale_0_1"},
            label_mapping={
                "0": "uninfected",
                "1": "parasitized",
                "positive_class": 1,
                "positive_label": "parasitized",
            },
            positive_label="parasitized",
            positive_class_index=1,
            threshold=0.5,
            threshold_source="postgres_contract_fixture",
            calibration_metadata={"test_fixture": True},
            published_at=model["published_at"],
            production_status="active",
            deployment_metadata={"test_fixture": True},
        )

    def injected_service(self, predictor):
        resolver = InjectedProductiveResolver(self.resolved_model())
        service = CellClassificationService(
            engine=self.shared_engine,
            settings=self.settings,
            model_resolver=resolver,
            local_storage=self.local_storage,
            preprocessor=lambda item, _resolved: int(item["cell_index"]),
            predictor=predictor,
        )
        return service, resolver

    def seed_terminal_prediction(self) -> SeededPrediction:
        source = self.completed_detection()
        model = self.governed_model()
        repository = CellClassificationRepository(self.connection)
        deployment_id = UUID(str(model["deployment_id"]))
        run_id = uuid4()
        input_id = uuid4()
        prediction_id = uuid4()
        summary_id = uuid4()
        event_id = uuid4()
        manifest_sha256 = hashlib.sha256(
            f"{source['cell_detection_id']}:{source['crop_sha256']}".encode()
        ).hexdigest()
        checkpoint_sha256 = str(model["checkpoint_sha256"]).lower()

        snapshot = self.resolved_model().snapshot(
            inference_version="cell-classification-v1",
            review_margin=self.settings.cell_classification_review_margin,
            batch_size=self.settings.cell_classification_batch_size,
        )
        repository.create_run(
            run_id=run_id,
            analysis_run_id=source["analysis_run_id"],
            detection_run_id=source["detection_run_id"],
            classification_run_code=f"CLS-{uuid4().hex[:8].upper()}",
            production_model_id=deployment_id,
            stage2_publication_id=model["publication_id"],
            model_registry_id=model["model_version_id"],
            model_name=model["model_name"] or "stage2-model",
            model_version=model["model_version"],
            model_snapshot=snapshot,
            input_manifest_sha256=manifest_sha256,
            input_count=1,
            eligible_count=1,
            excluded_count=0,
            requested_by=UUID(
                self.principals["administrator"].user_id
            ),
        )
        repository.insert_inputs(
            run_id,
            [
                {
                    "id": input_id,
                    "detection_run_id": source["detection_run_id"],
                    "cell_detection_id": source["cell_detection_id"],
                    "microscopy_image_id": source["microscopy_image_id"],
                    "crop_id": source["crop_id"],
                    "input_order": 1,
                    "image_sequence_number": source["image_sequence_number"],
                    "cell_index": source["cell_index"],
                    "cell_code": source["cell_code"],
                    "detector_key": source["detector_key"],
                    "detector_version": source["detector_version"],
                    "detector_algorithm_version": source["algorithm_version"],
                    "crop_sha256": source["crop_sha256"],
                    "crop_width_px": source["crop_width_px"],
                    "crop_height_px": source["crop_height_px"],
                    "detection_review_status_at_creation": "unreviewed",
                    "eligible": True,
                    "exclusion_reason": None,
                }
            ],
        )
        assert repository.start_run(run_id)["status"] == "processing"
        repository.insert_prediction(
            {
                "id": prediction_id,
                "classification_run_id": run_id,
                "classification_input_id": input_id,
                "cell_detection_id": source["cell_detection_id"],
                "crop_id": source["crop_id"],
                "prediction_status": "completed",
                "raw_output": [0.75],
                "probability_parasitized": 0.75,
                "probability_uninfected": 0.25,
                "predicted_label": "parasitized",
                "predicted_class_index": 1,
                "positive_label": "parasitized",
                "positive_class_index": 1,
                "threshold_used": 0.5,
                "threshold_source": "postgres_contract_fixture",
                "decision_margin": 0.25,
                "near_threshold": False,
                "preprocessing_snapshot": {"mode": "rescale_0_1"},
                "inference_duration_ms": 1.0,
                "error_code": None,
                "error_message": None,
            }
        )
        repository.update_counts(
            run_id,
            processed_count=1,
            parasitized_count=1,
            uninfected_count=0,
            near_threshold_count=0,
            failed_count=0,
        )
        repository.create_summary(
            {
                "id": summary_id,
                "classification_run_id": run_id,
                "analysis_run_id": source["analysis_run_id"],
                "detection_run_id": source["detection_run_id"],
                "outcome": "suspicious_cells_detected",
                "eligible_cell_count": 1,
                "classified_cell_count": 1,
                "parasitized_candidate_count": 1,
                "uninfected_candidate_count": 0,
                "near_threshold_count": 0,
                "failed_prediction_count": 0,
                "parasitized_candidate_fraction": 1.0,
                "maximum_probability_parasitized": 0.75,
                "mean_probability_parasitized": 0.75,
                "median_probability_parasitized": 0.75,
                "per_image_summary": {
                    "images": [
                        {
                            "microscopy_image_id": str(
                                source["microscopy_image_id"]
                            ),
                            "image_sequence_number": (
                                source["image_sequence_number"]
                            ),
                            "eligible_cell_count": 1,
                            "classified_cell_count": 1,
                            "parasitized_candidate_count": 1,
                            "uninfected_candidate_count": 0,
                            "near_threshold_count": 0,
                            "failed_prediction_count": 0,
                        }
                    ]
                },
                "aggregation_policy_snapshot": {
                    "version": "cell-candidate-aggregation-v1",
                    "scope": "candidate_cells",
                    "suspicious_when_any_parasitized": True,
                    "near_threshold_makes_negative_inconclusive": True,
                    "partial_failure_makes_negative_inconclusive": True,
                    "terminology": "experimental_screening_not_diagnosis",
                },
            }
        )
        repository.add_event(
            event_id=event_id,
            classification_run_id=run_id,
            cell_detection_id=source["cell_detection_id"],
            cell_prediction_id=prediction_id,
            event_type="cell_classification.prediction.completed",
            status="completed",
            progress_current=1,
            progress_total=1,
        )
        terminal = repository.complete_run(
            run_id,
            status="completed",
            processed_count=1,
            parasitized_count=1,
            uninfected_count=0,
            near_threshold_count=0,
            failed_count=0,
        )
        assert terminal and terminal["status"] == "completed"
        seeded = SeededPrediction(
            classification_run_id=run_id,
            classification_input_id=input_id,
            prediction_id=prediction_id,
            summary_id=summary_id,
            event_id=event_id,
            detection_run_id=UUID(str(source["detection_run_id"])),
            analysis_run_id=UUID(str(source["analysis_run_id"])),
            cell_detection_id=UUID(str(source["cell_detection_id"])),
            crop_id=UUID(str(source["crop_id"])),
            deployment_id=deployment_id,
            publication_id=UUID(str(model["publication_id"])),
            model_version_id=UUID(str(model["model_version_id"])),
            model_version=(
                str(model["model_version"])
                if model["model_version"] is not None
                else None
            ),
            checkpoint_sha256=checkpoint_sha256,
            manifest_sha256=manifest_sha256,
        )
        return seeded


@pytest.fixture()
def classification_postgres(monkeypatch, tmp_path):
    if os.getenv("TEST_EXECUTION", "").lower() != "true":
        pytest.skip("requiere gate PostgreSQL local explícito")
    settings = Settings.from_env()
    engine = create_engine(normalize_sqlalchemy_url(settings.database_url))
    connection = engine.connect()
    outer = connection.begin()
    assert_capstone_database(
        settings,
        connection.execute(text("SELECT current_database()")).scalar_one(),
    )
    assert connection.execute(
        text("SELECT version_num='20260810_03' FROM alembic_version")
    ).scalar_one(), "la migración 20260810_03 debe estar aplicada"
    baseline = _database_counts(connection)
    suffix = uuid4().hex[:10]
    roles = ("administrator", "operator", "reviewer", "read_only")
    user_ids = {role: uuid4() for role in roles}
    for role in roles:
        username = f"cell_cls_{role}_{suffix}"
        connection.execute(
            text(
                """
                INSERT INTO users(id,username,email,password_hash,status)
                VALUES(:id,:username,:email,'test-not-used','active')
                """
            ),
            {
                "id": user_ids[role],
                "username": username,
                "email": f"{username}@invalid.test",
            },
        )
    shared = TransactionEngine(connection)
    principals = {
        role: Principal(
            user_id=str(user_ids[role]),
            username=f"cell_cls_{role}_{suffix}",
            roles=(role,),
            permissions=frozenset(security.ROLE_PERMISSIONS[role]),
        )
        for role in roles
    }
    test_settings = replace(
        settings,
        storage_root=tmp_path / "storage",
        storage_provider="local",
        cell_classification_batch_size=32,
    )
    local_storage = LocalStorage(test_settings)
    analysis_context = DetectionPostgresContext(
        connection=connection,
        shared_engine=shared,
        local_storage=local_storage,
        crop_storage=CellCropStorage(local_storage),
        actor=principals["administrator"],
        actor_id=user_ids["administrator"],
        suffix=suffix,
    )
    headers = {
        role: {
            "Authorization": (
                "Bearer "
                + security.create_access_token(
                    user_ids[role],
                    principals[role].username,
                    [role],
                )
            )
        }
        for role in roles
    }
    monkeypatch.setattr(security, "get_primary_engine", lambda: shared)
    monkeypatch.setattr(audit, "get_primary_engine", lambda: shared)
    monkeypatch.setattr(classification_routes.service, "engine", shared)
    monkeypatch.setattr(
        classification_routes.service, "settings", test_settings
    )
    monkeypatch.setattr(
        classification_routes.service, "local_storage", local_storage
    )
    monkeypatch.setattr(
        classification_routes.service,
        "model_resolver",
        ProductiveModelResolver(engine=shared),
    )
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield ClassificationPostgresContext(
                connection=connection,
                shared_engine=shared,
                client=client,
                headers=headers,
                principals=principals,
                suffix=suffix,
                settings=test_settings,
                local_storage=local_storage,
                analysis_context=analysis_context,
            )
    finally:
        outer.rollback()
        assert _database_counts(connection) == baseline
        connection.close()
        engine.dispose()


def test_schema_is_specialized_append_only_and_binary_free(
    classification_postgres,
):
    context = classification_postgres
    inspector = inspect(context.connection)
    assert CLASSIFICATION_TABLES <= set(inspector.get_table_names())
    assert "legacy_cell_predictions" in set(inspector.get_view_names())
    assert "cell_predictions" not in set(inspector.get_view_names())

    bytea_columns = context.connection.execute(
        text(
            """
            SELECT table_name,column_name
            FROM information_schema.columns
            WHERE table_schema=current_schema()
              AND table_name=ANY(CAST(:tables AS text[]))
              AND data_type='bytea'
            ORDER BY table_name,column_name
            """
        ),
        {"tables": sorted(CLASSIFICATION_TABLES)},
    ).all()
    assert bytea_columns == []
    assert {"heatmap_storage_key", "heatmap_sha256", "overlay_storage_key"} <= {
        column["name"]
        for column in inspector.get_columns("cell_explanations")
    }

    trigger_names = set(
        context.connection.execute(
            text(
                """
                SELECT trigger_name
                FROM information_schema.triggers
                WHERE event_object_schema=current_schema()
                  AND event_object_table=ANY(CAST(:tables AS text[]))
                """
            ),
            {"tables": sorted(CLASSIFICATION_TABLES)},
        ).scalars()
    )
    assert {
        "trg_cell_classification_inputs_insert_state",
        "trg_cell_classification_inputs_append_only",
        "trg_cell_predictions_insert_state",
        "trg_cell_predictions_append_only",
        "trg_smear_analysis_summaries_insert_state",
        "trg_smear_analysis_summaries_validate",
        "trg_smear_analysis_summaries_append_only",
        "trg_cell_classification_events_append_only",
        "trg_cell_classification_reviews_append_only",
        "trg_cell_classification_reviews_validate",
        "trg_cell_classification_runs_protected",
        "trg_cell_classification_runs_snapshot",
        "trg_cell_classification_inputs_snapshot",
        "trg_cell_predictions_validate_input",
        "trg_cell_explanations_protected",
        "trg_cell_explanations_contract",
    } <= trigger_names

    prediction_indexes = {
        item["name"] for item in inspector.get_indexes("cell_predictions")
    }
    assert {
        "ix_cell_predictions_run_status",
        "ix_cell_predictions_run_label",
        "ix_cell_predictions_run_near_threshold",
        "ix_cell_predictions_detection",
        "ix_cell_predictions_crop",
    } <= prediction_indexes
    absolute_artifact_keys = context.connection.execute(
        text(
            """
            SELECT count(*)
            FROM cell_explanations
            WHERE heatmap_storage_key LIKE '/%'
               OR overlay_storage_key LIKE '/%'
               OR heatmap_storage_key LIKE '%..%'
               OR overlay_storage_key LIKE '%..%'
            """
        )
    ).scalar_one()
    assert absolute_artifact_keys == 0


def test_api_rbac_and_safe_block_without_productive_model(
    classification_postgres,
):
    context = classification_postgres
    source = context.completed_detection()
    # The local gate may legitimately have a real productive model. Isolate
    # the zero-model scenario inside the fixture's outer rollback transaction.
    context.connection.execute(
        text(
            """
            UPDATE stage2_model_publications
            SET status='inactive',is_active=FALSE,
                deactivated_at=NOW(),deactivated_by='postgres-test-rollback'
            WHERE scope='stage2' AND status='active' AND is_active=TRUE
            """
        )
    )
    context.connection.execute(
        text(
            """
            UPDATE deployed_model_versions
            SET status='inactive',retired_at=NOW(),
                retired_by='postgres-test-rollback'
            WHERE environment='stage2' AND alias='default' AND status='active'
            """
        )
    )
    productive_count = context.connection.execute(
        text(
            """
            SELECT count(*)
            FROM deployed_model_versions
            WHERE environment='stage2'
              AND alias='default'
              AND status='active'
            """
        )
    ).scalar_one()
    assert productive_count == 0, (
        "esta prueba demuestra el bloqueo real del entorno sin slot "
        "stage2/default"
    )

    path = (
        "/api/v1/cell-classification/eligible-detection-runs"
        f"?detection_run_id={source['detection_run_id']}"
    )
    assert context.client.get(path).status_code == 401
    eligible = context.client.get(path, headers=context.headers["read_only"])
    assert eligible.status_code == 200, eligible.text
    assert eligible.json()["total"] == 1
    candidate = eligible.json()["items"][0]
    assert candidate["detection_run_id"] == str(source["detection_run_id"])
    assert candidate["eligible"] is False
    assert candidate["reason_code"] == "PRODUCTIVE_MODEL_NOT_FOUND"
    assert candidate["productive_model"] is None

    payload = {"detection_run_id": str(source["detection_run_id"])}
    forbidden = context.client.post(
        "/api/v1/cell-classification/classification-runs",
        headers=context.headers["reviewer"],
        json=payload,
    )
    assert forbidden.status_code == 403
    blocked = context.client.post(
        "/api/v1/cell-classification/classification-runs",
        headers=context.headers["operator"],
        json=payload,
    )
    assert blocked.status_code == 409, blocked.text
    body = blocked.json()
    assert body["error"]["code"] == "CONFLICT"
    assert body["error"]["message"] == "No existe un modelo Productivo Etapa 2."
    assert context.connection.execute(
        text(
            """
            SELECT count(*) FROM cell_classification_runs
            WHERE detection_run_id=:detection_run_id
              AND requested_by=:requested_by
            """
        ),
        {
            "detection_run_id": source["detection_run_id"],
            "requested_by": UUID(context.principals["operator"].user_id),
        },
    ).scalar_one() == 0
    rejection_audit = context.connection.execute(
        text(
            """
            SELECT success,error_code,after_state,metadata
            FROM audit_events
            WHERE actor_user_id=:actor
              AND event_type='scientific.cell_classification.rejected'
            ORDER BY created_at DESC,id DESC
            """
        ),
        {"actor": UUID(context.principals["operator"].user_id)},
    ).mappings().all()
    assert len(rejection_audit) == 1
    assert rejection_audit[0]["success"] is False
    assert rejection_audit[0]["error_code"] == "PRODUCTIVE_MODEL_NOT_FOUND"
    safe_audit = json.dumps(rejection_audit[0], default=str).lower()
    assert "checkpoint_path" not in safe_audit
    assert "artifact_path" not in safe_audit
    assert "storage_key" not in safe_audit
    assert "jwt" not in safe_audit


def test_execution_gate_revalidates_analysis_readiness(
    classification_postgres,
):
    context = classification_postgres
    source = context.completed_detection()
    run = CellClassificationRepository(
        context.connection
    ).detection_run_input(source["detection_run_id"])
    assert run and run["ready_for_analysis"] is True
    run["ready_for_analysis"] = False
    with pytest.raises(CellClassificationError) as rejected:
        CellClassificationService._eligible_detection_run(run)
    assert rejected.value.status_code == 409


def test_service_persists_1_50_500_batches_and_reuses_idempotently(
    classification_postgres,
):
    context = classification_postgres

    def predictor(_model, batch):
        return [[0.75] for _ in range(len(batch))]

    service, resolver = context.injected_service(predictor)
    principal = context.principals["administrator"]
    request = _request(
        "/api/v1/cell-classification/classification-runs"
    )
    for count, expected_batches in (
        (1, [1]),
        (50, [32, 18]),
        (500, [32] * 15 + [20]),
    ):
        detection = context.completed_detection(count)
        first = service.execute_classification(
            str(detection["detection_run_id"]), principal, request
        )
        assert first["idempotent"] is False
        assert first["status"] == "completed"
        assert first["input_count"] == count
        assert first["eligible_count"] == count
        assert first["processed_count"] == count
        assert first["parasitized_count"] == count
        assert context.connection.execute(
            text(
                """
                SELECT count(*) FROM cell_predictions
                WHERE classification_run_id=:run_id
                """
            ),
            {"run_id": UUID(str(first["id"]))},
        ).scalar_one() == count
        batch_sizes = context.connection.execute(
            text(
                """
                SELECT (metadata_json->>'batch_size')::integer
                FROM cell_classification_events
                WHERE classification_run_id=:run_id
                  AND event_type='cell_classification.batch.started'
                ORDER BY (metadata_json->>'batch_number')::integer
                """
            ),
            {"run_id": UUID(str(first["id"]))},
        ).scalars().all()
        assert batch_sizes == expected_batches

        loads_before_reuse = resolver.load_count
        second = service.execute_classification(
            str(detection["detection_run_id"]), principal, request
        )
        assert second["id"] == first["id"]
        assert second["idempotent"] is True
        assert resolver.load_count == loads_before_reuse
        assert context.connection.execute(
            text(
                """
                SELECT count(*)
                FROM cell_classification_runs
                WHERE detection_run_id=:detection_run_id
                  AND production_model_id=:deployment_id
                """
            ),
            {
                "detection_run_id": detection["detection_run_id"],
                "deployment_id": UUID(
                    context.resolved_model().deployment_id
                ),
            },
        ).scalar_one() == 1


def test_failed_run_retries_only_after_a_new_explicit_action(
    classification_postgres,
):
    context = classification_postgres
    detection = context.completed_detection(3)
    principal = context.principals["administrator"]
    request = _request(
        "/api/v1/cell-classification/classification-runs"
    )

    def fail_predictor(_model, _batch):
        raise RuntimeError("synthetic inference failure")

    failed_service, _ = context.injected_service(fail_predictor)
    first = failed_service.execute_classification(
        str(detection["detection_run_id"]), principal, request
    )
    assert first["idempotent"] is False
    assert first["status"] == "failed"
    assert first["failed_count"] == 3
    assert context.connection.execute(
        text(
            """
            SELECT count(*) FROM cell_classification_runs
            WHERE detection_run_id=:detection_run_id
            """
        ),
        {"detection_run_id": detection["detection_run_id"]},
    ).scalar_one() == 1

    success_service, _ = context.injected_service(
        lambda _model, batch: [[0.25] for _ in range(len(batch))]
    )
    retried = success_service.execute_classification(
        str(detection["detection_run_id"]), principal, request
    )
    assert retried["idempotent"] is False
    assert retried["status"] == "completed"
    assert retried["id"] != first["id"]
    assert context.connection.execute(
        text(
            """
            SELECT retry_of_run_id
            FROM cell_classification_runs
            WHERE id=:run_id
            """
        ),
        {"run_id": UUID(str(retried["id"]))},
    ).scalar_one() == UUID(str(first["id"]))
    assert context.connection.execute(
        text(
            """
            SELECT count(*) FROM cell_classification_runs
            WHERE detection_run_id=:detection_run_id
            """
        ),
        {"detection_run_id": detection["detection_run_id"]},
    ).scalar_one() == 2


def test_database_rejects_contradictory_frozen_contracts(
    classification_postgres,
):
    context = classification_postgres
    source = context.completed_detection(2)
    model = context.governed_model()
    resolved = context.resolved_model()
    repository = CellClassificationRepository(context.connection)
    detection = repository.detection_run_input(source["detection_run_id"])
    inputs, manifest_sha256 = freeze_classification_inputs(
        detection["detections"]
    )
    for item in inputs:
        item["detection_run_id"] = detection["id"]
    snapshot = resolved.snapshot(
        inference_version="cell-classification-v1",
        review_margin=context.settings.cell_classification_review_margin,
        batch_size=context.settings.cell_classification_batch_size,
    )
    contradictory_snapshot = json.loads(json.dumps(snapshot))
    contradictory_snapshot["production_model_id"] = str(uuid4())
    with pytest.raises(DBAPIError) as rejected_snapshot:
        with context.connection.begin_nested():
            repository.create_run(
                run_id=uuid4(),
                analysis_run_id=detection["analysis_run_id"],
                detection_run_id=detection["id"],
                classification_run_code=f"CLS-{uuid4().hex[:8].upper()}",
                production_model_id=model["deployment_id"],
                stage2_publication_id=model["publication_id"],
                model_registry_id=model["model_version_id"],
                model_name=model["model_name"],
                model_version=model["model_version"],
                model_snapshot=contradictory_snapshot,
                input_manifest_sha256=manifest_sha256,
                input_count=2,
                eligible_count=2,
                excluded_count=0,
                requested_by=UUID(
                    context.principals["administrator"].user_id
                ),
            )
    assert _sqlstate(rejected_snapshot.value) == "23514"

    run_id = uuid4()
    repository.create_run(
        run_id=run_id,
        analysis_run_id=detection["analysis_run_id"],
        detection_run_id=detection["id"],
        classification_run_code=f"CLS-{uuid4().hex[:8].upper()}",
        production_model_id=model["deployment_id"],
        stage2_publication_id=model["publication_id"],
        model_registry_id=model["model_version_id"],
        model_name=model["model_name"],
        model_version=model["model_version"],
        model_snapshot=snapshot,
        input_manifest_sha256=manifest_sha256,
        input_count=2,
        eligible_count=2,
        excluded_count=0,
        requested_by=UUID(
            context.principals["administrator"].user_id
        ),
    )
    contradictory_input = dict(inputs[0])
    contradictory_input["crop_sha256"] = "0" * 64
    with pytest.raises(DBAPIError) as rejected_input:
        with context.connection.begin_nested():
            repository.insert_inputs(
                run_id,
                [
                    {
                        key: value
                        for key, value in contradictory_input.items()
                        if not key.startswith("_")
                    }
                ],
            )
    assert _sqlstate(rejected_input.value) == "23514"
    repository.insert_inputs(
        run_id,
        [
            {
                key: value
                for key, value in item.items()
                if not key.startswith("_")
            }
            for item in inputs
        ],
    )
    assert repository.start_run(run_id)["status"] == "processing"
    first_input = inputs[0]
    base_prediction = {
        "id": uuid4(),
        "classification_run_id": run_id,
        "classification_input_id": first_input["id"],
        "cell_detection_id": first_input["cell_detection_id"],
        "crop_id": first_input["crop_id"],
        "prediction_status": "completed",
        "raw_output": [0.75],
        "probability_parasitized": 0.75,
        "probability_uninfected": 0.25,
        "predicted_label": "parasitized",
        "predicted_class_index": 1,
        "positive_label": "parasitized",
        "positive_class_index": 1,
        "threshold_used": 0.5,
        "threshold_source": resolved.threshold_source,
        "decision_margin": 0.25,
        "near_threshold": False,
        "preprocessing_snapshot": resolved.preprocessing,
        "inference_duration_ms": 1.0,
        "error_code": None,
        "error_message": None,
    }
    wrong_threshold = {
        **base_prediction,
        "id": uuid4(),
        "threshold_used": 0.6,
        "decision_margin": 0.15,
    }
    with pytest.raises(DBAPIError) as rejected_threshold:
        with context.connection.begin_nested():
            repository.insert_prediction(wrong_threshold)
    assert _sqlstate(rejected_threshold.value) == "23514"
    wrong_preprocessing = {
        **base_prediction,
        "id": uuid4(),
        "preprocessing_snapshot": {"mode": "vgg16_imagenet"},
    }
    with pytest.raises(DBAPIError) as rejected_preprocessing:
        with context.connection.begin_nested():
            repository.insert_prediction(wrong_preprocessing)
    assert _sqlstate(rejected_preprocessing.value) == "23514"

    with pytest.raises(DBAPIError) as rejected_summary:
        with context.connection.begin_nested():
            repository.create_summary(
                {
                    "id": uuid4(),
                    "classification_run_id": run_id,
                    "analysis_run_id": detection["analysis_run_id"],
                    "detection_run_id": detection["id"],
                    "outcome": "suspicious_cells_detected",
                    "eligible_cell_count": 2,
                    "classified_cell_count": 1,
                    "parasitized_candidate_count": 1,
                    "uninfected_candidate_count": 0,
                    "near_threshold_count": 0,
                    "failed_prediction_count": 0,
                    "parasitized_candidate_fraction": 1.0,
                    "maximum_probability_parasitized": 0.75,
                    "mean_probability_parasitized": 0.75,
                    "median_probability_parasitized": 0.75,
                    "per_image_summary": {"images": []},
                    "aggregation_policy_snapshot": {
                        "version": "cell-candidate-aggregation-v1",
                        "scope": "candidate_cells",
                        "suspicious_when_any_parasitized": True,
                        "near_threshold_makes_negative_inconclusive": True,
                        "partial_failure_makes_negative_inconclusive": True,
                        "terminology": (
                            "experimental_screening_not_diagnosis"
                        ),
                    },
                }
            )
    assert _sqlstate(rejected_summary.value) == "23514"


def test_reviews_audit_idempotency_and_append_only_integrity(
    classification_postgres,
):
    context = classification_postgres
    seeded = context.seed_terminal_prediction()
    service = CellClassificationService(engine=context.shared_engine)
    repository = CellClassificationRepository(context.connection)

    equivalent = repository.find_equivalent(
        detection_run_id=seeded.detection_run_id,
        production_model_id=seeded.deployment_id,
        model_version=seeded.model_version,
        checkpoint_sha256=seeded.checkpoint_sha256,
        inference_version="cell-classification-v1",
        input_manifest_sha256=seeded.manifest_sha256,
    )
    assert equivalent
    assert equivalent["id"] == seeded.classification_run_id
    frozen_run = context.connection.execute(
        text(
            """
            SELECT model_name,model_snapshot
            FROM cell_classification_runs
            WHERE id=:run_id
            """
        ),
        {"run_id": seeded.classification_run_id},
    ).mappings().one()
    with pytest.raises(IntegrityError) as duplicate:
        with context.connection.begin_nested():
            repository.create_run(
                run_id=uuid4(),
                analysis_run_id=seeded.analysis_run_id,
                detection_run_id=seeded.detection_run_id,
                classification_run_code=f"CLS-{uuid4().hex[:8].upper()}",
                production_model_id=seeded.deployment_id,
                stage2_publication_id=seeded.publication_id,
                model_registry_id=seeded.model_version_id,
                model_name=frozen_run["model_name"],
                model_version=seeded.model_version,
                model_snapshot=frozen_run["model_snapshot"],
                input_manifest_sha256=seeded.manifest_sha256,
                input_count=1,
                eligible_count=1,
                excluded_count=0,
                requested_by=UUID(
                    context.principals["administrator"].user_id
                ),
            )
    assert _sqlstate(duplicate.value) == "23505"

    automatic_before = repository.get_summary(
        seeded.classification_run_id
    )
    assert automatic_before["outcome"] == "suspicious_cells_detected"
    with pytest.raises(DBAPIError) as rejected_confirmation:
        with context.connection.begin_nested():
            repository.create_review(
                cell_prediction_id=seeded.prediction_id,
                decision="confirmed",
                reviewed_label="uninfected",
                comment="Etiqueta contradictoria de fixture.",
                actor_user_id=UUID(
                    context.principals["reviewer"].user_id
                ),
            )
    assert _sqlstate(rejected_confirmation.value) == "23514"
    operator_forbidden = context.client.post(
        (
            "/api/v1/cell-classification/predictions/"
            f"{seeded.prediction_id}/reviews"
        ),
        headers=context.headers["operator"],
        json={
            "decision": "corrected",
            "reviewed_label": "uninfected",
            "comment": "Corrección de fixture PostgreSQL.",
        },
    )
    assert operator_forbidden.status_code == 403
    review_response = context.client.post(
        (
            "/api/v1/cell-classification/predictions/"
            f"{seeded.prediction_id}/reviews"
        ),
        headers=context.headers["reviewer"],
        json={
            "decision": "corrected",
            "reviewed_label": "uninfected",
            "comment": "Corrección de fixture PostgreSQL.",
        },
    )
    assert review_response.status_code == 201, review_response.text
    review_id = UUID(review_response.json()["id"])

    summary = service.get_summary(str(seeded.classification_run_id))
    assert summary["automatic_summary"]["outcome"] == (
        automatic_before["outcome"]
    )
    assert summary["automatic_summary"]["parasitized_candidate_count"] == 1
    assert summary["reviewed_summary"]["outcome"] == (
        "no_suspicious_cells_detected"
    )
    assert summary["reviewed_summary"]["uninfected_candidate_count"] == 1
    persisted_prediction = repository.get_prediction(seeded.prediction_id)
    assert persisted_prediction["predicted_label"] == "parasitized"
    assert persisted_prediction["probability_parasitized"] == 0.75

    review_history = context.client.get(
        (
            "/api/v1/cell-classification/predictions/"
            f"{seeded.prediction_id}/reviews"
        ),
        headers=context.headers["read_only"],
    )
    assert review_history.status_code == 200
    assert review_history.json()["total"] == 1
    prediction_api = context.client.get(
        f"/api/v1/cell-classification/predictions/{seeded.prediction_id}",
        headers=context.headers["read_only"],
    )
    assert prediction_api.status_code == 200
    serialized = json.dumps(prediction_api.json()).lower()
    assert "crop_storage_key" not in serialized
    assert "relative_storage_key" not in serialized
    assert "checkpoint_path" not in serialized

    audit_row = context.connection.execute(
        text(
            """
            SELECT success,after_state
            FROM audit_events
            WHERE event_type='scientific.cell_classification.reviewed'
              AND resource_id=:prediction_id
            ORDER BY created_at DESC,id DESC
            LIMIT 1
            """
        ),
        {"prediction_id": str(seeded.prediction_id)},
    ).mappings().one()
    assert audit_row["success"] is True
    assert audit_row["after_state"]["review_decision"] == "corrected"
    assert audit_row["after_state"]["comment_present"] is True
    assert audit_row["after_state"]["comment_length"] > 0
    assert "comment" not in audit_row["after_state"]

    explanation = repository.create_explanation(
        cell_prediction_id=seeded.prediction_id,
        method_version="gradcam-v1",
        parameters={
            "method": "gradcam",
            "method_version": "gradcam-v1",
            "target_class_index": 1,
            "positive_class_index": 1,
            "preprocessing": {"mode": "rescale_0_1"},
        },
    )
    repository.start_explanation(explanation["id"], retry=False)
    foreign_analysis_id = uuid4()
    foreign_run_id = uuid4()
    foreign_detection_id = uuid4()
    with pytest.raises(DBAPIError) as rejected_explanation_lineage:
        with context.connection.begin_nested():
            repository.complete_explanation(
                explanation["id"],
                last_conv_layer="fixture_conv",
                heatmap_storage_key=(
                    f"cell-explanations/{foreign_analysis_id}/"
                    f"{foreign_run_id}/{foreign_detection_id}/"
                    "gradcam_heatmap.png"
                ),
                heatmap_sha256="a" * 64,
                heatmap_file_size_bytes=1,
                overlay_storage_key=(
                    f"cell-explanations/{foreign_analysis_id}/"
                    f"{foreign_run_id}/{foreign_detection_id}/"
                    "gradcam_overlay.png"
                ),
                overlay_sha256="b" * 64,
                overlay_file_size_bytes=1,
                width_px=8,
                height_px=8,
            )
    assert _sqlstate(rejected_explanation_lineage.value) == "23514"
    terminal_explanation = repository.fail_explanation(
        explanation["id"],
        error_code="GRADCAM_UNSUPPORTED",
        error_message="Arquitectura no compatible en fixture.",
        unsupported=True,
    )
    assert terminal_explanation["status"] == "unsupported"

    late_inserts = (
        (
            """
            INSERT INTO cell_classification_inputs(
              id,classification_run_id,detection_run_id,cell_detection_id,
              microscopy_image_id,crop_id,input_order,image_sequence_number,
              cell_index,cell_code,detector_key,detector_version,
              detector_algorithm_version,crop_sha256,crop_width_px,
              crop_height_px,detection_review_status_at_creation,eligible,
              exclusion_reason
            )
            SELECT
              :new_id,classification_run_id,detection_run_id,cell_detection_id,
              microscopy_image_id,crop_id,input_order+1,
              image_sequence_number,cell_index,cell_code,detector_key,
              detector_version,detector_algorithm_version,crop_sha256,
              crop_width_px,crop_height_px,
              detection_review_status_at_creation,eligible,exclusion_reason
            FROM cell_classification_inputs WHERE id=:source_id
            """,
            seeded.classification_input_id,
        ),
        (
            """
            INSERT INTO cell_predictions(
              id,classification_run_id,classification_input_id,
              cell_detection_id,crop_id,prediction_status,raw_output,
              probability_parasitized,probability_uninfected,predicted_label,
              predicted_class_index,positive_label,positive_class_index,
              threshold_used,threshold_source,decision_margin,near_threshold,
              preprocessing_snapshot,inference_duration_ms,error_code,
              error_message
            )
            SELECT
              :new_id,classification_run_id,classification_input_id,
              cell_detection_id,crop_id,prediction_status,raw_output,
              probability_parasitized,probability_uninfected,predicted_label,
              predicted_class_index,positive_label,positive_class_index,
              threshold_used,threshold_source,decision_margin,near_threshold,
              preprocessing_snapshot,inference_duration_ms,error_code,
              error_message
            FROM cell_predictions WHERE id=:source_id
            """,
            seeded.prediction_id,
        ),
        (
            """
            INSERT INTO smear_analysis_summaries(
              id,classification_run_id,analysis_run_id,detection_run_id,
              outcome,eligible_cell_count,classified_cell_count,
              parasitized_candidate_count,uninfected_candidate_count,
              near_threshold_count,failed_prediction_count,
              parasitized_candidate_fraction,
              maximum_probability_parasitized,
              mean_probability_parasitized,
              median_probability_parasitized,per_image_summary,
              aggregation_policy_snapshot
            )
            SELECT
              :new_id,classification_run_id,analysis_run_id,detection_run_id,
              outcome,eligible_cell_count,classified_cell_count,
              parasitized_candidate_count,uninfected_candidate_count,
              near_threshold_count,failed_prediction_count,
              parasitized_candidate_fraction,
              maximum_probability_parasitized,
              mean_probability_parasitized,
              median_probability_parasitized,per_image_summary,
              aggregation_policy_snapshot
            FROM smear_analysis_summaries WHERE id=:source_id
            """,
            seeded.summary_id,
        ),
    )
    for statement, source_id in late_inserts:
        with pytest.raises(DBAPIError) as rejected:
            with context.connection.begin_nested():
                context.connection.execute(
                    text(statement),
                    {"new_id": uuid4(), "source_id": source_id},
                )
        assert _sqlstate(rejected.value) == "55000"

    guarded = (
        (
            "UPDATE cell_classification_inputs SET eligible=eligible "
            "WHERE id=:id",
            seeded.classification_input_id,
        ),
        (
            "UPDATE cell_predictions SET near_threshold=near_threshold "
            "WHERE id=:id",
            seeded.prediction_id,
        ),
        (
            "DELETE FROM smear_analysis_summaries WHERE id=:id",
            seeded.summary_id,
        ),
        (
            "UPDATE cell_classification_events SET status=status WHERE id=:id",
            seeded.event_id,
        ),
        (
            "DELETE FROM cell_classification_reviews WHERE id=:id",
            review_id,
        ),
        (
            "UPDATE cell_classification_runs SET updated_at=updated_at "
            "WHERE id=:id",
            seeded.classification_run_id,
        ),
        (
            "UPDATE cell_explanations SET error_message=error_message "
            "WHERE id=:id",
            explanation["id"],
        ),
    )
    for statement, entity_id in guarded:
        with pytest.raises(DBAPIError) as rejected:
            with context.connection.begin_nested():
                context.connection.execute(
                    text(statement), {"id": entity_id}
                )
        assert _sqlstate(rejected.value) == "55000"

    assert context.connection.execute(
        text(
            """
            SELECT
              (SELECT count(*) FROM cell_predictions WHERE id=:prediction_id),
              (SELECT count(*) FROM cell_classification_reviews WHERE id=:review_id),
              (SELECT count(*) FROM smear_analysis_summaries WHERE id=:summary_id),
              (SELECT count(*) FROM cell_explanations WHERE id=:explanation_id)
            """
        ),
        {
            "prediction_id": seeded.prediction_id,
            "review_id": review_id,
            "summary_id": seeded.summary_id,
            "explanation_id": explanation["id"],
        },
    ).one() == (1, 1, 1, 1)
def test_human_classification_is_editable_audited_and_keeps_ai_immutable(
    classification_postgres,
):
    context = classification_postgres
    seeded = context.seed_terminal_prediction()
    endpoint = (
        "/api/v1/cell-classification/predictions/"
        f"{seeded.prediction_id}/human-classification"
    )
    immutable_before = context.connection.execute(text("""
      SELECT prediction.predicted_label,prediction.probability_parasitized,
             prediction.probability_uninfected,prediction.threshold_used,
             prediction.threshold_source,prediction.classification_run_id,
             run.model_version,run.model_snapshot
      FROM cell_predictions prediction
      JOIN cell_classification_runs run ON run.id=prediction.classification_run_id
      WHERE prediction.id=:id
    """), {"id": seeded.prediction_id}).mappings().one()

    initial = context.client.get(endpoint, headers=context.headers["read_only"])
    assert initial.status_code == 200
    assert initial.json()["status"] == "unreviewed"
    assert initial.json()["label"] is None
    assert context.client.put(
        endpoint, headers=context.headers["operator"],
        json={"label": "uninfected"},
    ).status_code == 403

    first = context.client.put(
        endpoint, headers=context.headers["reviewer"],
        json={"label": "uninfected"},
    )
    assert first.status_code == 200, first.text
    assert first.json()["label"] == "uninfected"
    assert first.json()["comment"] is None
    assert first.json()["actor_user_id"] == context.principals["reviewer"].user_id

    second = context.client.put(
        endpoint, headers=context.headers["administrator"],
        json={"label": "parasitized", "comment": "Consenso inicial."},
    )
    assert second.status_code == 200, second.text
    assert second.json()["label"] == "parasitized"

    third = context.client.put(
        endpoint, headers=context.headers["reviewer"],
        json={"label": "uninfected", "comment": "Comentario editado."},
    )
    assert third.status_code == 200, third.text
    assert third.json()["label"] == "uninfected"
    assert third.json()["comment"] == "Comentario editado."

    current = context.client.get(endpoint, headers=context.headers["read_only"])
    assert current.status_code == 200
    assert current.json()["label"] == "uninfected"
    assert current.json()["comment"] == "Comentario editado."
    history = context.client.get(
        f"{endpoint}/history", headers=context.headers["read_only"]
    )
    assert history.status_code == 200
    assert history.json()["total"] == 3
    assert [item["label"] for item in history.json()["items"]] == [
        "uninfected", "parasitized", "uninfected"
    ]
    assert [item["comment"] for item in history.json()["items"]] == [
        None, "Consenso inicial.", "Comentario editado."
    ]

    immutable_after = context.connection.execute(text("""
      SELECT prediction.predicted_label,prediction.probability_parasitized,
             prediction.probability_uninfected,prediction.threshold_used,
             prediction.threshold_source,prediction.classification_run_id,
             run.model_version,run.model_snapshot
      FROM cell_predictions prediction
      JOIN cell_classification_runs run ON run.id=prediction.classification_run_id
      WHERE prediction.id=:id
    """), {"id": seeded.prediction_id}).mappings().one()
    assert dict(immutable_after) == dict(immutable_before)

    audits = context.connection.execute(text("""
      SELECT event_type,actor_user_id,before_state,after_state
      FROM audit_events WHERE resource_type='cell_prediction'
        AND resource_id=:id
        AND action='human-classification'
    """), {"id": str(seeded.prediction_id)}).mappings().all()
    assert len(audits) == 3
    assert sum(row["before_state"] is None for row in audits) == 1
    assert {row["after_state"]["human_label"] for row in audits} == {
        "parasitized", "uninfected"
    }
    assert {row["actor_user_id"] for row in audits} == {
        UUID(context.principals["reviewer"].user_id),
        UUID(context.principals["administrator"].user_id),
    }
