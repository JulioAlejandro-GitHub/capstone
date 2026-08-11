from __future__ import annotations

import json
import secrets
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection


def _dict(row) -> dict | None:
    return dict(row) if row else None


def _values(item) -> dict:
    if is_dataclass(item):
        return asdict(item)
    if isinstance(item, Mapping):
        return dict(item)
    raise TypeError("El registro debe ser un mapping o dataclass.")


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)


RUN_LIST_FROM = """
FROM cell_classification_runs cr
JOIN cell_detection_runs dr ON dr.id=cr.detection_run_id
JOIN microscopy_analysis_runs ar ON ar.id=cr.analysis_run_id
JOIN deployed_model_versions deployment ON deployment.id=cr.production_model_id
JOIN stage2_model_publications publication
  ON publication.id=cr.stage2_publication_id
LEFT JOIN smear_analysis_summaries summary
  ON summary.classification_run_id=cr.id
LEFT JOIN LATERAL (
  SELECT
    count(*) completed_prediction_count,
    count(*) FILTER (WHERE effective.decision IS NOT NULL) reviewed_count,
    count(*) FILTER (WHERE effective.decision='confirmed') confirmed_count,
    count(*) FILTER (WHERE effective.decision='corrected') corrected_count,
    count(*) FILTER (
      WHERE effective.decision='needs_attention'
    ) needs_attention_count
  FROM cell_predictions prediction
  LEFT JOIN LATERAL (
    SELECT review.decision
    FROM cell_classification_reviews review
    WHERE review.cell_prediction_id=prediction.id
      AND review.decision<>'comment_only'
    ORDER BY review.created_at DESC,review.id DESC
    LIMIT 1
  ) effective ON true
  WHERE prediction.classification_run_id=cr.id
    AND prediction.prediction_status='completed'
) review_totals ON true
"""


RUN_LIST_SELECT = """
SELECT
  cr.*,
  dr.detection_run_code,
  dr.detector_key,
  dr.detector_version,
  dr.algorithm_version detector_algorithm_version,
  ar.run_code analysis_run_code,
  deployment.environment production_environment,
  deployment.alias production_alias,
  deployment.deployment_name production_deployment_name,
  publication.status publication_status,
  publication.is_active publication_is_active,
  summary.id summary_id,
  summary.outcome,
  COALESCE(review_totals.reviewed_count,0)::integer reviewed_count,
  GREATEST(
    COALESCE(review_totals.completed_prediction_count,0)
      -COALESCE(review_totals.reviewed_count,0),
    0
  )::integer unreviewed_count,
  COALESCE(review_totals.confirmed_count,0)::integer confirmed_count,
  COALESCE(review_totals.corrected_count,0)::integer corrected_count,
  COALESCE(review_totals.needs_attention_count,0)::integer
    needs_attention_review_count
"""


PREDICTION_FROM = """
FROM cell_predictions prediction
JOIN cell_classification_inputs input
  ON input.id=prediction.classification_input_id
JOIN cell_detections detection ON detection.id=prediction.cell_detection_id
JOIN cell_crops crop ON crop.id=prediction.crop_id
JOIN cell_classification_runs classification
  ON classification.id=prediction.classification_run_id
LEFT JOIN cell_explanations explanation
  ON explanation.cell_prediction_id=prediction.id
LEFT JOIN LATERAL (
  SELECT
    review.id,
    review.decision,
    review.reviewed_label,
    review.comment,
    review.actor_user_id,
    actor.username actor_username,
    review.created_at
  FROM cell_classification_reviews review
  JOIN users actor ON actor.id=review.actor_user_id
  WHERE review.cell_prediction_id=prediction.id
    AND review.decision<>'comment_only'
  ORDER BY review.created_at DESC,review.id DESC
  LIMIT 1
) latest_review ON true
"""


PREDICTION_SELECT = """
SELECT
  prediction.*,
  input.detection_run_id,
  input.microscopy_image_id,
  input.input_order,
  input.image_sequence_number,
  input.cell_index,
  input.cell_code,
  input.detector_key,
  input.detector_version,
  input.detector_algorithm_version,
  input.detection_review_status_at_creation,
  detection.bbox_x,
  detection.bbox_y,
  detection.bbox_width,
  detection.bbox_height,
  detection.coordinate_space,
  detection.detector_score,
  crop.relative_storage_key crop_storage_key,
  crop.sha256 crop_persisted_sha256,
  crop.file_size_bytes crop_file_size_bytes,
  crop.width_px crop_width_px,
  crop.height_px crop_height_px,
  classification.analysis_run_id,
  classification.classification_run_code,
  classification.production_model_id,
  classification.stage2_publication_id,
  classification.model_registry_id,
  classification.model_name,
  classification.model_version,
  classification.model_snapshot,
  explanation.id explanation_id,
  explanation.status explanation_status,
  explanation.method explanation_method,
  explanation.method_version explanation_method_version,
  explanation.last_conv_layer explanation_last_conv_layer,
  latest_review.id latest_review_id,
  COALESCE(latest_review.decision,'unreviewed') review_status,
  latest_review.reviewed_label latest_reviewed_label,
  latest_review.comment latest_review_comment,
  latest_review.actor_user_id latest_review_actor_user_id,
  latest_review.actor_username latest_review_actor_username,
  latest_review.created_at latest_review_created_at
"""


class CellClassificationRepository:
    """SQL persistence for immutable cell-classification scientific records."""

    def __init__(self, connection: Connection):
        self.connection = connection

    def stage2_default_candidates(
        self,
        *,
        deployment_name: str = "malaria-stage2-classifier",
        environment: str = "stage2",
        alias: str = "default",
        for_share: bool = False,
    ) -> list[dict]:
        lock = " FOR SHARE OF deployment,version,publication,artifact" if for_share else ""
        rows = self.connection.execute(
            text(
                f"""
                SELECT
                  deployment.*,
                  version.id model_registry_id,
                  version.model_name,
                  version.version_number,
                  version.status model_registry_status,
                  version.lineage_status,
                  version.framework,
                  version.framework_version,
                  version.preprocessing_profile_snapshot,
                  version.class_mapping,
                  version.input_signature,
                  version.output_signature,
                  version.training_run_id source_training_run_id,
                  model.architecture,
                  model.input_shape model_input_shape,
                  artifact.path checkpoint_path,
                  artifact.checksum checkpoint_artifact_sha256,
                  artifact.file_size_bytes checkpoint_artifact_size_bytes,
                  artifact.artifact_status,
                  publication.id stage2_publication_id,
                  publication.evaluation_run_id source_evaluation_run_id,
                  publication.published_at,
                  publication.status publication_status,
                  publication.is_active publication_is_active,
                  training.status training_status,
                  evaluation.status evaluation_status,
                  threshold.threshold_source calibration_threshold_source,
                  threshold.threshold_selected calibration_threshold,
                  threshold.calibration_status,
                  threshold.score_name calibration_score_name,
                  threshold.positive_label calibration_positive_label
                FROM deployed_model_versions deployment
                JOIN model_versions version
                  ON version.id=deployment.model_version_id
                JOIN models model ON model.id=version.model_id
                JOIN artifacts artifact
                  ON artifact.id=deployment.checkpoint_artifact_id
                JOIN stage2_model_publications publication
                  ON publication.model_version_id=version.id
                  AND publication.scope='stage2'
                  AND publication.status='active'
                  AND publication.is_active=true
                JOIN runs training ON training.id=version.training_run_id
                JOIN runs evaluation
                  ON evaluation.id=publication.evaluation_run_id
                LEFT JOIN run_threshold_calibration threshold
                  ON threshold.run_threshold_calibration_id=
                    deployment.threshold_calibration_id
                  AND threshold.model_version_id=version.id
                WHERE deployment.deployment_name=:deployment_name
                  AND deployment.environment=:environment
                  AND deployment.alias=:alias
                  AND deployment.status='active'
                ORDER BY deployment.deployed_at DESC,deployment.id{lock}
                """
            ),
            {
                "deployment_name": deployment_name,
                "environment": environment,
                "alias": alias,
            },
        ).mappings().all()
        return [dict(row) for row in rows]

    def eligible_detection_runs(
        self,
        *,
        detection_run_id: str | UUID | None = None,
        limit: int,
        offset: int,
    ) -> dict:
        params = {
            "detection_run_id": (
                str(detection_run_id) if detection_run_id is not None else None
            ),
            "limit": limit,
            "offset": offset,
        }
        base = """
          FROM cell_detection_runs detection
          JOIN microscopy_analysis_runs analysis
            ON analysis.id=detection.analysis_run_id
          JOIN research_subjects subject ON subject.id=analysis.subject_id
          JOIN blood_samples sample ON sample.id=analysis.sample_id
          JOIN smear_slides slide ON slide.id=analysis.slide_id
          LEFT JOIN LATERAL (
            SELECT
              classification.id classification_run_id,
              classification.status classification_status,
              classification.classification_run_code
            FROM cell_classification_runs classification
            WHERE classification.detection_run_id=detection.id
            ORDER BY classification.created_at DESC,classification.id DESC
            LIMIT 1
          ) latest_classification ON true
          WHERE (
              (
                CAST(:detection_run_id AS uuid) IS NULL
                AND analysis.ready_for_analysis=true
                AND detection.status IN (
                  'completed','completed_with_warnings'
                )
                AND detection.detection_count > 0
              )
              OR (
                CAST(:detection_run_id AS uuid) IS NOT NULL
                AND detection.id=CAST(:detection_run_id AS uuid)
              )
            )
        """
        rows = self.connection.execute(
            text(
                f"""
                SELECT
                  detection.id,
                  detection.analysis_run_id,
                  detection.detection_run_code,
                  detection.detector_key,
                  detection.detector_version,
                  detection.algorithm_version,
                  detection.status,
                  detection.detection_count,
                  detection.crop_count,
                  detection.warning_count,
                  detection.completed_at,
                  subject.subject_code,
                  sample.sample_code,
                  slide.slide_code,
                  latest_classification.classification_run_id,
                  latest_classification.classification_status,
                  latest_classification.classification_run_code
                {base}
                ORDER BY detection.created_at DESC,detection.id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
        total = self.connection.execute(
            text(f"SELECT count(*) {base}"), params
        ).scalar_one()
        return {
            "items": [dict(row) for row in rows],
            "total": int(total),
            "limit": limit,
            "offset": offset,
        }

    def detection_run_input(
        self, detection_run_id: str | UUID, *, for_update: bool = False
    ) -> dict | None:
        lock = " FOR UPDATE OF detection" if for_update else ""
        run = _dict(
            self.connection.execute(
                text(
                    f"""
                    SELECT
                      detection.*,
                      analysis.ready_for_analysis,
                      analysis.quality_gate_status,
                      analysis.run_status analysis_run_status,
                      analysis.input_manifest_sha256 analysis_manifest_sha256
                    FROM cell_detection_runs detection
                    JOIN microscopy_analysis_runs analysis
                      ON analysis.id=detection.analysis_run_id
                    WHERE detection.id=CAST(:id AS uuid){lock}
                    """
                ),
                {"id": str(detection_run_id)},
            ).mappings().first()
        )
        if not run:
            return None
        rows = self.connection.execute(
            text(
                """
                SELECT
                  detection.id cell_detection_id,
                  detection.detection_run_id,
                  detection.analysis_run_id,
                  detection.microscopy_image_id,
                  detection.cell_index,
                  detection.cell_code,
                  detection.created_at detection_created_at,
                  image.sequence_number image_sequence_number,
                  run.detector_key,
                  run.detector_version,
                  run.algorithm_version detector_algorithm_version,
                  crop.id crop_id,
                  crop.relative_storage_key crop_storage_key,
                  crop.sha256 crop_sha256,
                  crop.file_size_bytes crop_file_size_bytes,
                  crop.width_px crop_width_px,
                  crop.height_px crop_height_px,
                  crop.format crop_format,
                  COALESCE(latest_review.decision,'unreviewed')
                    detection_review_status
                FROM cell_detections detection
                JOIN cell_detection_runs run
                  ON run.id=detection.detection_run_id
                JOIN microscopy_analysis_run_images image
                  ON image.id=detection.analysis_run_image_id
                LEFT JOIN cell_crops crop
                  ON crop.cell_detection_id=detection.id
                LEFT JOIN LATERAL (
                  SELECT review.decision
                  FROM scientific_reviews review
                  WHERE review.entity_type='cell_detection'
                    AND review.entity_id=detection.id
                    AND review.decision<>'comment_only'
                  ORDER BY review.created_at DESC,review.id DESC
                  LIMIT 1
                ) latest_review ON true
                WHERE detection.detection_run_id=CAST(:id AS uuid)
                ORDER BY
                  image.sequence_number,
                  detection.cell_index,
                  detection.id
                """
            ),
            {"id": str(detection_run_id)},
        ).mappings().all()
        run["detections"] = [dict(row) for row in rows]
        return run

    def find_equivalent(
        self,
        *,
        detection_run_id: str | UUID,
        production_model_id: str | UUID,
        checkpoint_sha256: str,
        model_version: str | None,
        inference_version: str,
        input_manifest_sha256: str,
    ) -> dict | None:
        return _dict(
            self.connection.execute(
                text(
                    """
                    SELECT *
                    FROM cell_classification_runs
                    WHERE detection_run_id=CAST(:detection_run_id AS uuid)
                      AND production_model_id=
                        CAST(:production_model_id AS uuid)
                      AND model_version IS NOT DISTINCT FROM :model_version
                      AND model_snapshot->>'checkpoint_sha256'=
                        :checkpoint_sha256
                      AND model_snapshot->>'inference_version'=
                        :inference_version
                      AND input_manifest_sha256=:input_manifest_sha256
                      AND status IN (
                        'created','processing','completed',
                        'completed_with_warnings'
                      )
                    ORDER BY created_at DESC,id DESC
                    LIMIT 1
                    """
                ),
                {
                    "detection_run_id": str(detection_run_id),
                    "production_model_id": str(production_model_id),
                    "checkpoint_sha256": checkpoint_sha256,
                    "model_version": model_version,
                    "inference_version": inference_version,
                    "input_manifest_sha256": input_manifest_sha256,
                },
            ).mappings().first()
        )

    def find_failed_equivalent(
        self,
        *,
        detection_run_id: str | UUID,
        production_model_id: str | UUID,
        checkpoint_sha256: str,
        model_version: str | None,
        inference_version: str,
        input_manifest_sha256: str,
    ) -> dict | None:
        return _dict(
            self.connection.execute(
                text(
                    """
                    SELECT *
                    FROM cell_classification_runs
                    WHERE detection_run_id=CAST(:detection_run_id AS uuid)
                      AND production_model_id=
                        CAST(:production_model_id AS uuid)
                      AND model_version IS NOT DISTINCT FROM :model_version
                      AND model_snapshot->>'checkpoint_sha256'=
                        :checkpoint_sha256
                      AND model_snapshot->>'inference_version'=
                        :inference_version
                      AND input_manifest_sha256=:input_manifest_sha256
                      AND status='failed'
                    ORDER BY failed_at DESC,created_at DESC,id DESC
                    LIMIT 1
                    """
                ),
                {
                    "detection_run_id": str(detection_run_id),
                    "production_model_id": str(production_model_id),
                    "checkpoint_sha256": checkpoint_sha256,
                    "model_version": model_version,
                    "inference_version": inference_version,
                    "input_manifest_sha256": input_manifest_sha256,
                },
            ).mappings().first()
        )

    def create_run(
        self,
        *,
        analysis_run_id: str | UUID,
        detection_run_id: str | UUID,
        production_model_id: str | UUID,
        stage2_publication_id: str | UUID,
        model_registry_id: str | UUID,
        model_name: str,
        model_version: str | None,
        model_snapshot: dict,
        input_manifest_sha256: str,
        input_count: int,
        eligible_count: int,
        excluded_count: int,
        requested_by: str | UUID,
        run_id: UUID | None = None,
        retry_of_run_id: str | UUID | None = None,
        classification_run_code: str | None = None,
    ) -> dict:
        run_id = run_id or uuid4()
        classification_run_code = (
            classification_run_code
            or f"CLS-{secrets.token_hex(4).upper()}"
        )
        row = self.connection.execute(
            text(
                """
                INSERT INTO cell_classification_runs(
                  id,analysis_run_id,detection_run_id,
                  classification_run_code,production_model_id,
                  stage2_publication_id,model_registry_id,model_name,
                  model_version,model_snapshot,input_manifest_sha256,status,
                  input_count,eligible_count,excluded_count,requested_by,
                  retry_of_run_id
                ) VALUES(
                  :id,CAST(:analysis_run_id AS uuid),
                  CAST(:detection_run_id AS uuid),:classification_run_code,
                  CAST(:production_model_id AS uuid),
                  CAST(:stage2_publication_id AS uuid),
                  CAST(:model_registry_id AS uuid),:model_name,:model_version,
                  CAST(:model_snapshot AS jsonb),:input_manifest_sha256,
                  'created',:input_count,:eligible_count,:excluded_count,
                  CAST(:requested_by AS uuid),CAST(:retry_of_run_id AS uuid)
                )
                RETURNING *
                """
            ),
            {
                "id": run_id,
                "analysis_run_id": str(analysis_run_id),
                "detection_run_id": str(detection_run_id),
                "classification_run_code": classification_run_code,
                "production_model_id": str(production_model_id),
                "stage2_publication_id": str(stage2_publication_id),
                "model_registry_id": str(model_registry_id),
                "model_name": model_name,
                "model_version": model_version,
                "model_snapshot": _json(model_snapshot),
                "input_manifest_sha256": input_manifest_sha256,
                "input_count": input_count,
                "eligible_count": eligible_count,
                "excluded_count": excluded_count,
                "requested_by": str(requested_by),
                "retry_of_run_id": (
                    str(retry_of_run_id) if retry_of_run_id else None
                ),
            },
        ).mappings().one()
        return dict(row)

    def insert_inputs(
        self,
        classification_run_id: str | UUID,
        items: Sequence[Mapping | object],
    ) -> list[dict]:
        inserted: list[dict] = []
        statement = text(
            """
            INSERT INTO cell_classification_inputs(
              id,classification_run_id,detection_run_id,cell_detection_id,
              microscopy_image_id,crop_id,input_order,image_sequence_number,
              cell_index,cell_code,detector_key,detector_version,
              detector_algorithm_version,crop_sha256,crop_width_px,
              crop_height_px,detection_review_status_at_creation,eligible,
              exclusion_reason
            ) VALUES(
              :id,CAST(:classification_run_id AS uuid),
              CAST(:detection_run_id AS uuid),
              CAST(:cell_detection_id AS uuid),
              CAST(:microscopy_image_id AS uuid),CAST(:crop_id AS uuid),
              :input_order,:image_sequence_number,:cell_index,:cell_code,
              :detector_key,:detector_version,:detector_algorithm_version,
              :crop_sha256,:crop_width_px,:crop_height_px,
              :detection_review_status_at_creation,:eligible,
              :exclusion_reason
            )
            RETURNING *
            """
        )
        for original in items:
            item = _values(original)
            params = {
                **item,
                "id": item.get("id") or uuid4(),
                "classification_run_id": str(classification_run_id),
                "detection_run_id": str(item["detection_run_id"]),
                "cell_detection_id": str(item["cell_detection_id"]),
                "microscopy_image_id": str(item["microscopy_image_id"]),
                "crop_id": str(item["crop_id"]) if item.get("crop_id") else None,
            }
            inserted.append(
                dict(self.connection.execute(statement, params).mappings().one())
            )
        return inserted

    def start_run(self, classification_run_id: str | UUID) -> dict | None:
        return _dict(
            self.connection.execute(
                text(
                    """
                    UPDATE cell_classification_runs
                    SET status='processing',started_at=now(),updated_at=now()
                    WHERE id=CAST(:id AS uuid) AND status='created'
                    RETURNING *
                    """
                ),
                {"id": str(classification_run_id)},
            ).mappings().first()
        )

    def add_event(
        self,
        *,
        classification_run_id: str | UUID,
        event_type: str,
        status: str,
        cell_detection_id: str | UUID | None = None,
        cell_prediction_id: str | UUID | None = None,
        message_code: str | None = None,
        message: str | None = None,
        progress_current: int | None = None,
        progress_total: int | None = None,
        metadata: dict | None = None,
        event_id: UUID | None = None,
    ) -> dict:
        row = self.connection.execute(
            text(
                """
                INSERT INTO cell_classification_events(
                  id,classification_run_id,cell_detection_id,
                  cell_prediction_id,event_type,status,message_code,message,
                  progress_current,progress_total,metadata_json
                ) VALUES(
                  :id,CAST(:classification_run_id AS uuid),
                  CAST(:cell_detection_id AS uuid),
                  CAST(:cell_prediction_id AS uuid),:event_type,:status,
                  :message_code,:message,:progress_current,:progress_total,
                  CAST(:metadata AS jsonb)
                )
                RETURNING *
                """
            ),
            {
                "id": event_id or uuid4(),
                "classification_run_id": str(classification_run_id),
                "cell_detection_id": (
                    str(cell_detection_id) if cell_detection_id else None
                ),
                "cell_prediction_id": (
                    str(cell_prediction_id) if cell_prediction_id else None
                ),
                "event_type": event_type,
                "status": status,
                "message_code": message_code,
                "message": message,
                "progress_current": progress_current,
                "progress_total": progress_total,
                "metadata": _json(metadata or {}),
            },
        ).mappings().one()
        return dict(row)

    def insert_prediction(self, values: Mapping) -> dict:
        item = dict(values)
        row = self.connection.execute(
            text(
                """
                INSERT INTO cell_predictions(
                  id,classification_run_id,classification_input_id,
                  cell_detection_id,crop_id,prediction_status,raw_output,
                  probability_parasitized,probability_uninfected,
                  predicted_label,predicted_class_index,positive_label,
                  positive_class_index,threshold_used,threshold_source,
                  decision_margin,near_threshold,preprocessing_snapshot,
                  inference_duration_ms,error_code,error_message
                ) VALUES(
                  :id,CAST(:classification_run_id AS uuid),
                  CAST(:classification_input_id AS uuid),
                  CAST(:cell_detection_id AS uuid),CAST(:crop_id AS uuid),
                  :prediction_status,CAST(:raw_output AS jsonb),
                  :probability_parasitized,:probability_uninfected,
                  :predicted_label,:predicted_class_index,:positive_label,
                  :positive_class_index,:threshold_used,:threshold_source,
                  :decision_margin,:near_threshold,
                  CAST(:preprocessing_snapshot AS jsonb),
                  :inference_duration_ms,:error_code,:error_message
                )
                RETURNING *
                """
            ),
            {
                **item,
                "id": item.get("id") or uuid4(),
                "classification_run_id": str(item["classification_run_id"]),
                "classification_input_id": str(
                    item["classification_input_id"]
                ),
                "cell_detection_id": str(item["cell_detection_id"]),
                "crop_id": str(item["crop_id"]),
                "raw_output": _json(item["raw_output"]),
                "preprocessing_snapshot": _json(
                    item["preprocessing_snapshot"]
                ),
            },
        ).mappings().one()
        return dict(row)

    def update_counts(
        self,
        classification_run_id: str | UUID,
        *,
        processed_count: int,
        parasitized_count: int,
        uninfected_count: int,
        near_threshold_count: int,
        failed_count: int,
    ) -> dict | None:
        return _dict(
            self.connection.execute(
                text(
                    """
                    UPDATE cell_classification_runs
                    SET
                      processed_count=:processed_count,
                      parasitized_count=:parasitized_count,
                      uninfected_count=:uninfected_count,
                      near_threshold_count=:near_threshold_count,
                      failed_count=:failed_count,
                      updated_at=now()
                    WHERE id=CAST(:id AS uuid) AND status='processing'
                    RETURNING *
                    """
                ),
                {
                    "id": str(classification_run_id),
                    "processed_count": processed_count,
                    "parasitized_count": parasitized_count,
                    "uninfected_count": uninfected_count,
                    "near_threshold_count": near_threshold_count,
                    "failed_count": failed_count,
                },
            ).mappings().first()
        )

    def complete_run(
        self,
        classification_run_id: str | UUID,
        *,
        status: str,
        processed_count: int,
        parasitized_count: int,
        uninfected_count: int,
        near_threshold_count: int,
        failed_count: int,
    ) -> dict | None:
        if status not in {"completed", "completed_with_warnings"}:
            raise ValueError("Estado terminal de clasificación inválido.")
        return _dict(
            self.connection.execute(
                text(
                    """
                    UPDATE cell_classification_runs
                    SET
                      status=:status,
                      processed_count=:processed_count,
                      parasitized_count=:parasitized_count,
                      uninfected_count=:uninfected_count,
                      near_threshold_count=:near_threshold_count,
                      failed_count=:failed_count,
                      completed_at=now(),
                      updated_at=now()
                    WHERE id=CAST(:id AS uuid) AND status='processing'
                    RETURNING *
                    """
                ),
                {
                    "id": str(classification_run_id),
                    "status": status,
                    "processed_count": processed_count,
                    "parasitized_count": parasitized_count,
                    "uninfected_count": uninfected_count,
                    "near_threshold_count": near_threshold_count,
                    "failed_count": failed_count,
                },
            ).mappings().first()
        )

    def fail_run(
        self,
        classification_run_id: str | UUID,
        *,
        error_code: str,
        error_message: str,
    ) -> dict | None:
        return _dict(
            self.connection.execute(
                text(
                    """
                    UPDATE cell_classification_runs
                    SET
                      status='failed',
                      started_at=COALESCE(started_at,now()),
                      failed_at=now(),
                      completed_at=NULL,
                      error_code=:error_code,
                      error_message=:error_message,
                      updated_at=now()
                    WHERE id=CAST(:id AS uuid)
                      AND status IN ('created','processing')
                    RETURNING *
                    """
                ),
                {
                    "id": str(classification_run_id),
                    "error_code": error_code,
                    "error_message": error_message,
                },
            ).mappings().first()
        )

    def create_summary(self, values: Mapping) -> dict:
        item = dict(values)
        row = self.connection.execute(
            text(
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
                ) VALUES(
                  :id,CAST(:classification_run_id AS uuid),
                  CAST(:analysis_run_id AS uuid),
                  CAST(:detection_run_id AS uuid),:outcome,
                  :eligible_cell_count,:classified_cell_count,
                  :parasitized_candidate_count,
                  :uninfected_candidate_count,:near_threshold_count,
                  :failed_prediction_count,:parasitized_candidate_fraction,
                  :maximum_probability_parasitized,
                  :mean_probability_parasitized,
                  :median_probability_parasitized,
                  CAST(:per_image_summary AS jsonb),
                  CAST(:aggregation_policy_snapshot AS jsonb)
                )
                RETURNING *
                """
            ),
            {
                **item,
                "id": item.get("id") or uuid4(),
                "classification_run_id": str(item["classification_run_id"]),
                "analysis_run_id": str(item["analysis_run_id"]),
                "detection_run_id": str(item["detection_run_id"]),
                "per_image_summary": _json(item["per_image_summary"]),
                "aggregation_policy_snapshot": _json(
                    item["aggregation_policy_snapshot"]
                ),
            },
        ).mappings().one()
        return dict(row)

    def list_runs(
        self,
        *,
        status: str | None,
        analysis_run_id: str | UUID | None,
        detection_run_id: str | UUID | None,
        limit: int,
        offset: int,
    ) -> dict:
        clauses: list[str] = []
        params: dict = {"limit": limit, "offset": offset}
        if status:
            clauses.append("cr.status=:status")
            params["status"] = status
        if analysis_run_id:
            clauses.append("cr.analysis_run_id=CAST(:analysis_run_id AS uuid)")
            params["analysis_run_id"] = str(analysis_run_id)
        if detection_run_id:
            clauses.append(
                "cr.detection_run_id=CAST(:detection_run_id AS uuid)"
            )
            params["detection_run_id"] = str(detection_run_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(
            text(
                f"""
                {RUN_LIST_SELECT}
                {RUN_LIST_FROM}
                {where}
                ORDER BY cr.created_at DESC,cr.id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
        total = self.connection.execute(
            text(f"SELECT count(*) {RUN_LIST_FROM} {where}"), params
        ).scalar_one()
        return {
            "items": [dict(row) for row in rows],
            "total": int(total),
            "limit": limit,
            "offset": offset,
        }

    def get_run(self, classification_run_id: str | UUID) -> dict | None:
        run = _dict(
            self.connection.execute(
                text(
                    f"""
                    {RUN_LIST_SELECT}
                    {RUN_LIST_FROM}
                    WHERE cr.id=CAST(:id AS uuid)
                    """
                ),
                {"id": str(classification_run_id)},
            ).mappings().first()
        )
        if not run:
            return None
        run["events"] = self.events(classification_run_id)
        return run

    def list_predictions(
        self,
        *,
        classification_run_id: str | UUID,
        microscopy_image_id: str | UUID | None = None,
        predicted_label: str | None = None,
        near_threshold: bool | None = None,
        prediction_status: str | None = None,
        review_status: str | None = None,
        cell_code: str | None = None,
        limit: int,
        offset: int,
    ) -> dict | None:
        exists = self.connection.execute(
            text(
                """
                SELECT 1 FROM cell_classification_runs
                WHERE id=CAST(:id AS uuid)
                """
            ),
            {"id": str(classification_run_id)},
        ).scalar()
        if not exists:
            return None
        clauses = ["prediction.classification_run_id=CAST(:run_id AS uuid)"]
        params: dict = {
            "run_id": str(classification_run_id),
            "limit": limit,
            "offset": offset,
        }
        filters = {
            "microscopy_image_id": (
                microscopy_image_id,
                "input.microscopy_image_id=CAST(:microscopy_image_id AS uuid)",
            ),
            "predicted_label": (
                predicted_label,
                "prediction.predicted_label=:predicted_label",
            ),
            "near_threshold": (
                near_threshold,
                "prediction.near_threshold=:near_threshold",
            ),
            "prediction_status": (
                prediction_status,
                "prediction.prediction_status=:prediction_status",
            ),
            "review_status": (
                review_status,
                "COALESCE(latest_review.decision,'unreviewed')=:review_status",
            ),
            "cell_code": (
                cell_code,
                "upper(input.cell_code)=upper(:cell_code)",
            ),
        }
        for key, (value, clause) in filters.items():
            if value is None or value == "":
                continue
            clauses.append(clause)
            params[key] = str(value) if isinstance(value, UUID) else value
        where = f"WHERE {' AND '.join(clauses)}"
        rows = self.connection.execute(
            text(
                f"""
                {PREDICTION_SELECT}
                {PREDICTION_FROM}
                {where}
                ORDER BY
                  input.image_sequence_number,
                  input.cell_index,
                  prediction.id
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
        total = self.connection.execute(
            text(f"SELECT count(*) {PREDICTION_FROM} {where}"), params
        ).scalar_one()
        return {
            "items": [dict(row) for row in rows],
            "total": int(total),
            "limit": limit,
            "offset": offset,
        }

    def get_prediction(self, prediction_id: str | UUID) -> dict | None:
        return _dict(
            self.connection.execute(
                text(
                    f"""
                    {PREDICTION_SELECT}
                    {PREDICTION_FROM}
                    WHERE prediction.id=CAST(:id AS uuid)
                    """
                ),
                {"id": str(prediction_id)},
            ).mappings().first()
        )

    def get_summary(
        self, classification_run_id: str | UUID
    ) -> dict | None:
        return _dict(
            self.connection.execute(
                text(
                    """
                    SELECT *
                    FROM smear_analysis_summaries
                    WHERE classification_run_id=CAST(:id AS uuid)
                    """
                ),
                {"id": str(classification_run_id)},
            ).mappings().first()
        )

    def prediction_for_explanation(
        self, prediction_id: str | UUID, *, for_update: bool = False
    ) -> dict | None:
        lock = " FOR UPDATE OF prediction" if for_update else ""
        return _dict(
            self.connection.execute(
                text(
                    f"""
                    SELECT
                      prediction.*,
                      input.microscopy_image_id,
                      input.detection_run_id,
                      input.image_sequence_number,
                      input.cell_index,
                      input.cell_code,
                      crop.relative_storage_key crop_storage_key,
                      crop.sha256 crop_sha256,
                      crop.file_size_bytes crop_file_size_bytes,
                      crop.width_px crop_width_px,
                      crop.height_px crop_height_px,
                      classification.analysis_run_id,
                      classification.production_model_id,
                      classification.stage2_publication_id,
                      classification.model_registry_id,
                      classification.model_snapshot,
                      classification.model_name,
                      classification.model_version
                    FROM cell_predictions prediction
                    JOIN cell_classification_inputs input
                      ON input.id=prediction.classification_input_id
                    JOIN cell_crops crop ON crop.id=prediction.crop_id
                    JOIN cell_classification_runs classification
                      ON classification.id=prediction.classification_run_id
                    WHERE prediction.id=CAST(:id AS uuid)
                      AND prediction.prediction_status='completed'{lock}
                    """
                ),
                {"id": str(prediction_id)},
            ).mappings().first()
        )

    def find_explanation(
        self, cell_prediction_id: str | UUID
    ) -> dict | None:
        return _dict(
            self.connection.execute(
                text(
                    """
                    SELECT *
                    FROM cell_explanations
                    WHERE cell_prediction_id=CAST(:id AS uuid)
                    """
                ),
                {"id": str(cell_prediction_id)},
            ).mappings().first()
        )

    def get_explanation(
        self, explanation_id: str | UUID
    ) -> dict | None:
        return _dict(
            self.connection.execute(
                text(
                    """
                    SELECT explanation.*,prediction.classification_run_id,
                      prediction.cell_detection_id
                    FROM cell_explanations explanation
                    JOIN cell_predictions prediction
                      ON prediction.id=explanation.cell_prediction_id
                    WHERE explanation.id=CAST(:id AS uuid)
                    """
                ),
                {"id": str(explanation_id)},
            ).mappings().first()
        )

    def create_explanation(
        self,
        *,
        cell_prediction_id: str | UUID,
        method_version: str,
        parameters: dict,
        status: str = "not_requested",
        explanation_id: UUID | None = None,
    ) -> dict:
        if status not in {"not_requested", "pending"}:
            raise ValueError("Estado inicial de explicación inválido.")
        row = self.connection.execute(
            text(
                """
                INSERT INTO cell_explanations(
                  id,cell_prediction_id,method,method_version,status,
                  parameters_json,started_at
                ) VALUES(
                  :id,CAST(:cell_prediction_id AS uuid),'gradcam',
                  :method_version,CAST(:status AS varchar(20)),
                  CAST(:parameters AS jsonb),
                  CASE
                    WHEN CAST(:status AS varchar(20))='pending'
                    THEN now()
                    ELSE NULL
                  END
                )
                RETURNING *
                """
            ),
            {
                "id": explanation_id or uuid4(),
                "cell_prediction_id": str(cell_prediction_id),
                "method_version": method_version,
                "status": status,
                "parameters": _json(parameters),
            },
        ).mappings().one()
        return dict(row)

    def start_explanation(
        self, explanation_id: str | UUID, *, retry: bool
    ) -> dict | None:
        allowed = (
            "('not_requested','failed')"
            if retry
            else "('not_requested')"
        )
        return _dict(
            self.connection.execute(
                text(
                    f"""
                    UPDATE cell_explanations
                    SET
                      status='pending',
                      last_conv_layer=NULL,
                      heatmap_storage_key=NULL,
                      heatmap_sha256=NULL,
                      heatmap_file_size_bytes=NULL,
                      overlay_storage_key=NULL,
                      overlay_sha256=NULL,
                      overlay_file_size_bytes=NULL,
                      width_px=NULL,
                      height_px=NULL,
                      started_at=now(),
                      completed_at=NULL,
                      error_code=NULL,
                      error_message=NULL
                    WHERE id=CAST(:id AS uuid)
                      AND status IN {allowed}
                    RETURNING *
                    """
                ),
                {"id": str(explanation_id)},
            ).mappings().first()
        )

    def mark_explanation_artifact_missing(
        self, explanation_id: str | UUID
    ) -> dict | None:
        return _dict(
            self.connection.execute(
                text(
                    """
                    UPDATE cell_explanations SET
                      status='failed', last_conv_layer=NULL,
                      heatmap_storage_key=NULL, heatmap_sha256=NULL,
                      heatmap_file_size_bytes=NULL, overlay_storage_key=NULL,
                      overlay_sha256=NULL, overlay_file_size_bytes=NULL,
                      width_px=NULL, height_px=NULL, completed_at=now(),
                      error_code='ARTIFACT_MISSING',
                      error_message='El artefacto Grad-CAM ya no está disponible.'
                    WHERE id=CAST(:id AS uuid) AND status='generated'
                    RETURNING *
                    """
                ),
                {"id": str(explanation_id)},
            ).mappings().first()
        )

    def complete_explanation(
        self,
        explanation_id: str | UUID,
        *,
        last_conv_layer: str,
        heatmap_storage_key: str,
        heatmap_sha256: str,
        heatmap_file_size_bytes: int,
        overlay_storage_key: str,
        overlay_sha256: str,
        overlay_file_size_bytes: int,
        width_px: int,
        height_px: int,
    ) -> dict | None:
        return _dict(
            self.connection.execute(
                text(
                    """
                    UPDATE cell_explanations
                    SET
                      status='generated',
                      last_conv_layer=:last_conv_layer,
                      heatmap_storage_key=:heatmap_storage_key,
                      heatmap_sha256=:heatmap_sha256,
                      heatmap_file_size_bytes=:heatmap_file_size_bytes,
                      overlay_storage_key=:overlay_storage_key,
                      overlay_sha256=:overlay_sha256,
                      overlay_file_size_bytes=:overlay_file_size_bytes,
                      width_px=:width_px,
                      height_px=:height_px,
                      completed_at=now(),
                      error_code=NULL,
                      error_message=NULL
                    WHERE id=CAST(:id AS uuid) AND status='pending'
                    RETURNING *
                    """
                ),
                {
                    "id": str(explanation_id),
                    "last_conv_layer": last_conv_layer,
                    "heatmap_storage_key": heatmap_storage_key,
                    "heatmap_sha256": heatmap_sha256,
                    "heatmap_file_size_bytes": heatmap_file_size_bytes,
                    "overlay_storage_key": overlay_storage_key,
                    "overlay_sha256": overlay_sha256,
                    "overlay_file_size_bytes": overlay_file_size_bytes,
                    "width_px": width_px,
                    "height_px": height_px,
                },
            ).mappings().first()
        )

    def fail_explanation(
        self,
        explanation_id: str | UUID,
        *,
        error_code: str,
        error_message: str,
        unsupported: bool = False,
    ) -> dict | None:
        status = "unsupported" if unsupported else "failed"
        return _dict(
            self.connection.execute(
                text(
                    """
                    UPDATE cell_explanations
                    SET
                      status=:status,
                      completed_at=now(),
                      error_code=:error_code,
                      error_message=:error_message
                    WHERE id=CAST(:id AS uuid) AND status='pending'
                    RETURNING *
                    """
                ),
                {
                    "id": str(explanation_id),
                    "status": status,
                    "error_code": error_code,
                    "error_message": error_message,
                },
            ).mappings().first()
        )

    def explanation_artifact(
        self, explanation_id: str | UUID, *, kind: str
    ) -> dict | None:
        if kind not in {"heatmap", "overlay"}:
            raise ValueError("Artefacto de explicación inválido.")
        return _dict(
            self.connection.execute(
                text(
                    f"""
                    SELECT
                      explanation.id,
                      explanation.cell_prediction_id,
                      explanation.{kind}_storage_key storage_key,
                      explanation.{kind}_sha256 sha256,
                      explanation.{kind}_file_size_bytes file_size_bytes,
                      explanation.width_px,
                      explanation.height_px
                    FROM cell_explanations explanation
                    WHERE explanation.id=CAST(:id AS uuid)
                      AND explanation.status='generated'
                    """
                ),
                {"id": str(explanation_id)},
            ).mappings().first()
        )

    def prediction_for_review(
        self,
        cell_prediction_id: str | UUID,
    ) -> dict | None:
        return _dict(
            self.connection.execute(
                text(
                    """
                    SELECT
                      id,predicted_label,prediction_status,
                      classification_run_id,cell_detection_id
                    FROM cell_predictions
                    WHERE id=CAST(:id AS uuid)
                    FOR SHARE
                    """
                ),
                {"id": str(cell_prediction_id)},
            ).mappings().first()
        )

    def create_review(
        self,
        *,
        cell_prediction_id: str | UUID,
        decision: str,
        reviewed_label: str | None,
        comment: str | None,
        actor_user_id: str | UUID,
        review_id: UUID | None = None,
    ) -> dict | None:
        exists = self.connection.execute(
            text(
                """
                SELECT 1 FROM cell_predictions
                WHERE id=CAST(:id AS uuid)
                FOR SHARE
                """
            ),
            {"id": str(cell_prediction_id)},
        ).scalar()
        if not exists:
            return None
        row = self.connection.execute(
            text(
                """
                WITH inserted AS (
                  INSERT INTO cell_classification_reviews(
                    id,cell_prediction_id,decision,reviewed_label,comment,
                    actor_user_id
                  ) VALUES(
                    :id,CAST(:cell_prediction_id AS uuid),:decision,
                    :reviewed_label,:comment,CAST(:actor_user_id AS uuid)
                  )
                  RETURNING *
                )
                SELECT
                  inserted.*,
                  prediction.classification_run_id,
                  prediction.cell_detection_id
                FROM inserted
                JOIN cell_predictions prediction
                  ON prediction.id=inserted.cell_prediction_id
                """
            ),
            {
                "id": review_id or uuid4(),
                "cell_prediction_id": str(cell_prediction_id),
                "decision": decision,
                "reviewed_label": reviewed_label,
                "comment": comment,
                "actor_user_id": str(actor_user_id),
            },
        ).mappings().one()
        return dict(row)

    def latest_human_classification(
        self, cell_prediction_id: str | UUID
    ) -> dict | None:
        return _dict(self.connection.execute(text("""
          SELECT review.*,actor.username actor_username,
                 prediction.predicted_label automatic_label
          FROM cell_predictions prediction
          LEFT JOIN LATERAL (
            SELECT item.* FROM cell_classification_reviews item
            WHERE item.cell_prediction_id=prediction.id
              AND item.decision IN ('confirmed','corrected')
            ORDER BY item.created_at DESC,item.id DESC LIMIT 1
          ) review ON true
          LEFT JOIN users actor ON actor.id=review.actor_user_id
          WHERE prediction.id=CAST(:id AS uuid)
        """), {"id": str(cell_prediction_id)}).mappings().first())

    def human_classification_history(
        self, cell_prediction_id: str | UUID, *, limit: int, offset: int
    ) -> dict | None:
        if not self.connection.execute(
            text("SELECT 1 FROM cell_predictions WHERE id=CAST(:id AS uuid)"),
            {"id": str(cell_prediction_id)},
        ).scalar():
            return None
        params = {"id": str(cell_prediction_id), "limit": limit, "offset": offset}
        rows = self.connection.execute(text("""
          SELECT review.*,actor.username actor_username,
                 prediction.predicted_label automatic_label
          FROM cell_classification_reviews review
          JOIN users actor ON actor.id=review.actor_user_id
          JOIN cell_predictions prediction ON prediction.id=review.cell_prediction_id
          WHERE review.cell_prediction_id=CAST(:id AS uuid)
            AND review.decision IN ('confirmed','corrected')
          ORDER BY review.created_at,review.id LIMIT :limit OFFSET :offset
        """), params).mappings().all()
        total = self.connection.execute(text("""
          SELECT count(*) FROM cell_classification_reviews
          WHERE cell_prediction_id=CAST(:id AS uuid)
            AND decision IN ('confirmed','corrected')
        """), params).scalar_one()
        return {"items": [dict(row) for row in rows], "total": int(total),
                "limit": limit, "offset": offset}

    def reviews(
        self,
        cell_prediction_id: str | UUID,
        *,
        limit: int,
        offset: int,
    ) -> dict | None:
        exists = self.connection.execute(
            text(
                """
                SELECT 1 FROM cell_predictions
                WHERE id=CAST(:id AS uuid)
                """
            ),
            {"id": str(cell_prediction_id)},
        ).scalar()
        if not exists:
            return None
        params = {
            "id": str(cell_prediction_id),
            "limit": limit,
            "offset": offset,
        }
        rows = self.connection.execute(
            text(
                """
                SELECT review.*,actor.username actor_username
                FROM cell_classification_reviews review
                JOIN users actor ON actor.id=review.actor_user_id
                WHERE review.cell_prediction_id=CAST(:id AS uuid)
                ORDER BY review.created_at,review.id
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
        total = self.connection.execute(
            text(
                """
                SELECT count(*) FROM cell_classification_reviews
                WHERE cell_prediction_id=CAST(:id AS uuid)
                """
            ),
            params,
        ).scalar_one()
        return {
            "items": [dict(row) for row in rows],
            "total": int(total),
            "limit": limit,
            "offset": offset,
        }

    def latest_reviews_for_summary(
        self, classification_run_id: str | UUID
    ) -> list[dict]:
        rows = self.connection.execute(
            text(
                """
                SELECT
                  prediction.id cell_prediction_id,
                  prediction.cell_detection_id,
                  input.microscopy_image_id,
                  input.image_sequence_number,
                  input.cell_index,
                  prediction.prediction_status,
                  prediction.predicted_label automatic_label,
                  prediction.probability_parasitized,
                  prediction.near_threshold,
                  detection_review.decision detection_review_status,
                  classification_review.id classification_review_id,
                  classification_review.decision classification_review_status,
                  classification_review.reviewed_label,
                  CASE
                    WHEN detection_review.decision='rejected' THEN NULL
                    WHEN classification_review.decision='corrected'
                      THEN classification_review.reviewed_label
                    WHEN classification_review.decision='confirmed'
                      THEN prediction.predicted_label
                    ELSE prediction.predicted_label
                  END effective_reviewed_label
                FROM cell_predictions prediction
                JOIN cell_classification_inputs input
                  ON input.id=prediction.classification_input_id
                LEFT JOIN LATERAL (
                  SELECT review.decision
                  FROM scientific_reviews review
                  WHERE review.entity_type='cell_detection'
                    AND review.entity_id=prediction.cell_detection_id
                    AND review.decision<>'comment_only'
                  ORDER BY review.created_at DESC,review.id DESC
                  LIMIT 1
                ) detection_review ON true
                LEFT JOIN LATERAL (
                  SELECT review.*
                  FROM cell_classification_reviews review
                  WHERE review.cell_prediction_id=prediction.id
                    AND review.decision<>'comment_only'
                  ORDER BY review.created_at DESC,review.id DESC
                  LIMIT 1
                ) classification_review ON true
                WHERE prediction.classification_run_id=CAST(:id AS uuid)
                ORDER BY
                  input.image_sequence_number,
                  input.cell_index,
                  prediction.id
                """
            ),
            {"id": str(classification_run_id)},
        ).mappings().all()
        return [dict(row) for row in rows]

    def events(self, classification_run_id: str | UUID) -> list[dict]:
        rows = self.connection.execute(
            text(
                """
                SELECT *
                FROM cell_classification_events
                WHERE classification_run_id=CAST(:id AS uuid)
                ORDER BY created_at,id
                """
            ),
            {"id": str(classification_run_id)},
        ).mappings().all()
        return [dict(row) for row in rows]
