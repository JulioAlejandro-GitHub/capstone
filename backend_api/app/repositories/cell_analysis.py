from __future__ import annotations

import json
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection


def _dict(row) -> dict | None:
    return dict(row) if row else None


RUN_SUMMARY_FROM = """
FROM cell_detection_runs dr
JOIN microscopy_analysis_runs ar ON ar.id=dr.analysis_run_id
JOIN research_subjects rs ON rs.id=ar.subject_id
JOIN blood_samples bs ON bs.id=ar.sample_id
JOIN smear_slides ss ON ss.id=ar.slide_id
LEFT JOIN LATERAL (
  SELECT
    count(*) FILTER (WHERE effective.decision IS NOT NULL) reviewed_count,
    count(*) FILTER (WHERE effective.decision='accepted') accepted_count,
    count(*) FILTER (WHERE effective.decision='rejected') rejected_count,
    count(*) FILTER (WHERE effective.decision='needs_attention') needs_attention_count
  FROM cell_detections cd
  LEFT JOIN LATERAL (
    SELECT sr.decision
    FROM scientific_reviews sr
    WHERE sr.entity_type='cell_detection'
      AND sr.entity_id=cd.id
      AND sr.decision<>'comment_only'
    ORDER BY sr.created_at DESC,sr.id DESC
    LIMIT 1
  ) effective ON true
  WHERE cd.detection_run_id=dr.id
) review_totals ON true
"""


RUN_SUMMARY_SELECT = """
SELECT
  dr.*, ar.run_code analysis_run_code, rs.subject_code, bs.sample_code,
  ss.slide_code, COALESCE(review_totals.reviewed_count,0) reviewed_count,
  GREATEST(dr.detection_count-COALESCE(review_totals.reviewed_count,0),0)
    pending_review_count,
  COALESCE(review_totals.accepted_count,0) accepted_count,
  COALESCE(review_totals.rejected_count,0) rejected_count,
  COALESCE(review_totals.needs_attention_count,0) needs_attention_count
"""


class CellAnalysisRepository:
    def __init__(self, connection: Connection):
        self.connection = connection

    def eligible_analysis_runs(
        self,
        *,
        detector_key: str,
        detector_version: str,
        algorithm_version: str,
        limit: int,
        offset: int,
    ) -> dict:
        params = {
            "detector_key": detector_key,
            "detector_version": detector_version,
            "algorithm_version": algorithm_version,
            "limit": limit,
            "offset": offset,
        }
        eligibility = """
          ar.ready_for_analysis=true
          AND ar.quality_gate_status IN ('pass','warning')
          AND ar.input_image_count > 0
          AND (
            ar.quality_gate_status='pass'
            OR EXISTS (
              SELECT 1 FROM quality_gate_decisions qgd
              WHERE qgd.analysis_run_id=ar.id
                AND qgd.decision='approve_with_warnings'
            )
          )
          AND (
            SELECT count(*) FROM microscopy_analysis_run_images ari
            WHERE ari.analysis_run_id=ar.id
          )=ar.input_image_count
          AND NOT EXISTS (
            SELECT 1
            FROM microscopy_analysis_run_images ari
            JOIN microscopy_images mi ON mi.id=ari.microscopy_image_id
            WHERE ari.analysis_run_id=ar.id
              AND (
                mi.status<>'available'
                OR mi.sha256<>ari.input_sha256
                OR mi.file_size_bytes<>ari.input_file_size_bytes
                OR mi.width_px<>ari.input_width_px
                OR mi.height_px<>ari.input_height_px
              )
          )
          AND NOT EXISTS (
            SELECT 1 FROM cell_detection_runs existing
            WHERE existing.analysis_run_id=ar.id
              AND existing.detector_key=:detector_key
              AND existing.detector_version=:detector_version
              AND existing.algorithm_version=:algorithm_version
              AND existing.input_manifest_sha256=ar.input_manifest_sha256
              AND existing.status IN (
                'created','processing','completed','completed_with_warnings'
              )
          )
        """
        base = f"""
          FROM microscopy_analysis_runs ar
          JOIN research_subjects rs ON rs.id=ar.subject_id
          JOIN blood_samples bs ON bs.id=ar.sample_id
          JOIN smear_slides ss ON ss.id=ar.slide_id
          WHERE {eligibility}
        """
        rows = self.connection.execute(
            text(
                f"""
                SELECT ar.id,ar.run_code,rs.subject_code,bs.sample_code,ss.slide_code,
                  ar.input_image_count,ar.quality_gate_status,ar.ready_for_analysis,
                  ar.input_manifest_sha256,ar.created_at
                {base}
                ORDER BY ar.created_at DESC,ar.id DESC
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
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def analysis_input(self, analysis_run_id: str, *, for_update: bool = False) -> dict | None:
        lock = " FOR UPDATE OF ar" if for_update else ""
        run = _dict(
            self.connection.execute(
                text(
                    f"""
                    SELECT ar.*,rs.subject_code,bs.sample_code,ss.slide_code,
                      EXISTS(
                        SELECT 1 FROM quality_gate_decisions qgd
                        WHERE qgd.analysis_run_id=ar.id
                          AND qgd.decision='approve_with_warnings'
                      ) warning_approved
                    FROM microscopy_analysis_runs ar
                    JOIN research_subjects rs ON rs.id=ar.subject_id
                    JOIN blood_samples bs ON bs.id=ar.sample_id
                    JOIN smear_slides ss ON ss.id=ar.slide_id
                    WHERE ar.id=CAST(:id AS uuid){lock}
                    """
                ),
                {"id": analysis_run_id},
            ).mappings().first()
        )
        if not run:
            return None
        images = self.connection.execute(
            text(
                """
                SELECT
                  ari.id analysis_run_image_id,ari.analysis_run_id,
                  ari.microscopy_image_id,ari.sequence_number,
                  ari.input_sha256,ari.input_file_size_bytes,
                  ari.input_width_px,ari.input_height_px,
                  ari.image_status_at_creation,
                  mi.storage_key,mi.storage_provider,mi.status current_image_status,
                  mi.sha256 current_sha256,mi.file_size_bytes current_file_size_bytes,
                  mi.width_px current_width_px,mi.height_px current_height_px,
                  mi.mime_type
                FROM microscopy_analysis_run_images ari
                JOIN microscopy_images mi ON mi.id=ari.microscopy_image_id
                WHERE ari.analysis_run_id=CAST(:id AS uuid)
                ORDER BY ari.sequence_number,ari.id
                """
            ),
            {"id": analysis_run_id},
        ).mappings().all()
        run["images"] = [dict(row) for row in images]
        return run

    def find_equivalent(
        self,
        *,
        analysis_run_id: UUID,
        detector_key: str,
        detector_version: str,
        algorithm_version: str,
        input_manifest_sha256: str,
    ) -> dict | None:
        return _dict(
            self.connection.execute(
                text(
                    """
                    SELECT * FROM cell_detection_runs
                    WHERE analysis_run_id=:analysis_run_id
                      AND detector_key=:detector_key
                      AND detector_version=:detector_version
                      AND algorithm_version=:algorithm_version
                      AND input_manifest_sha256=:input_manifest_sha256
                      AND status IN (
                        'created','processing','completed','completed_with_warnings'
                      )
                    ORDER BY created_at DESC,id DESC LIMIT 1
                    """
                ),
                {
                    "analysis_run_id": analysis_run_id,
                    "detector_key": detector_key,
                    "detector_version": detector_version,
                    "algorithm_version": algorithm_version,
                    "input_manifest_sha256": input_manifest_sha256,
                },
            ).mappings().first()
        )

    def create_run(
        self,
        *,
        run_id: UUID,
        analysis_run_id: UUID,
        detection_run_code: str,
        detector_key: str,
        detector_version: str,
        algorithm_version: str,
        profile_snapshot: dict,
        input_manifest_sha256: str,
        image_count: int,
        requested_by: str,
    ) -> dict:
        return dict(
            self.connection.execute(
                text(
                    """
                    INSERT INTO cell_detection_runs(
                      id,analysis_run_id,detection_run_code,detector_key,
                      detector_version,algorithm_version,profile_snapshot,
                      input_manifest_sha256,status,image_count,requested_by
                    ) VALUES(
                      :id,:analysis_run_id,:detection_run_code,:detector_key,
                      :detector_version,:algorithm_version,
                      CAST(:profile_snapshot AS jsonb),:input_manifest_sha256,
                      'created',:image_count,CAST(:requested_by AS uuid)
                    )
                    RETURNING *
                    """
                ),
                {
                    "id": run_id,
                    "analysis_run_id": analysis_run_id,
                    "detection_run_code": detection_run_code,
                    "detector_key": detector_key,
                    "detector_version": detector_version,
                    "algorithm_version": algorithm_version,
                    "profile_snapshot": json.dumps(profile_snapshot),
                    "input_manifest_sha256": input_manifest_sha256,
                    "image_count": image_count,
                    "requested_by": requested_by,
                },
            ).mappings().one()
        )

    def start_run(self, detection_run_id: UUID) -> None:
        self.connection.execute(
            text(
                """
                UPDATE cell_detection_runs
                SET status='processing',started_at=now(),updated_at=now()
                WHERE id=:id AND status='created'
                """
            ),
            {"id": detection_run_id},
        )

    def add_event(
        self,
        *,
        detection_run_id: UUID,
        event_type: str,
        stage: str,
        status: str,
        microscopy_image_id: UUID | None = None,
        message_code: str | None = None,
        message: str | None = None,
        progress_current: int | None = None,
        progress_total: int | None = None,
        metadata: dict | None = None,
    ) -> dict:
        return dict(
            self.connection.execute(
                text(
                    """
                    INSERT INTO cell_detection_events(
                      id,detection_run_id,microscopy_image_id,event_type,stage,
                      status,message_code,message,progress_current,progress_total,
                      metadata_json
                    ) VALUES(
                      :id,:detection_run_id,:microscopy_image_id,:event_type,:stage,
                      :status,:message_code,:message,:progress_current,:progress_total,
                      CAST(:metadata AS jsonb)
                    ) RETURNING *
                    """
                ),
                {
                    "id": uuid4(),
                    "detection_run_id": detection_run_id,
                    "microscopy_image_id": microscopy_image_id,
                    "event_type": event_type,
                    "stage": stage,
                    "status": status,
                    "message_code": message_code,
                    "message": message,
                    "progress_current": progress_current,
                    "progress_total": progress_total,
                    "metadata": json.dumps(metadata or {}),
                },
            ).mappings().one()
        )

    def insert_component(self, values: dict) -> None:
        self.connection.execute(
            text(
                """
                INSERT INTO image_connected_components(
                  id,detection_run_id,analysis_run_id,analysis_run_image_id,
                  microscopy_image_id,component_index,bbox_x,bbox_y,bbox_width,
                  bbox_height,centroid_x,centroid_y,area_px,perimeter_px,
                  circularity,solidity,touches_border,component_status,
                  rejection_code,metrics_json
                ) VALUES(
                  :id,:detection_run_id,:analysis_run_id,:analysis_run_image_id,
                  :microscopy_image_id,:component_index,:bbox_x,:bbox_y,:bbox_width,
                  :bbox_height,:centroid_x,:centroid_y,:area_px,:perimeter_px,
                  :circularity,:solidity,:touches_border,:component_status,
                  :rejection_code,CAST(:metrics_json AS jsonb)
                )
                """
            ),
            {**values, "metrics_json": json.dumps(values["metrics_json"])},
        )

    def insert_detection(self, values: dict) -> None:
        self.connection.execute(
            text(
                """
                INSERT INTO cell_detections(
                  id,detection_run_id,analysis_run_id,connected_component_id,
                  analysis_run_image_id,microscopy_image_id,cell_index,cell_code,
                  bbox_x,bbox_y,bbox_width,bbox_height,coordinate_space,
                  detector_score,automated_status
                ) VALUES(
                  :id,:detection_run_id,:analysis_run_id,:connected_component_id,
                  :analysis_run_image_id,:microscopy_image_id,:cell_index,:cell_code,
                  :bbox_x,:bbox_y,:bbox_width,:bbox_height,:coordinate_space,
                  :detector_score,:automated_status
                )
                """
            ),
            values,
        )

    def insert_crop(self, values: dict) -> None:
        self.connection.execute(
            text(
                """
                INSERT INTO cell_crops(
                  id,cell_detection_id,relative_storage_key,sha256,file_size_bytes,
                  width_px,height_px,format,padding_px
                ) VALUES(
                  :id,:cell_detection_id,:relative_storage_key,:sha256,
                  :file_size_bytes,:width_px,:height_px,:format,:padding_px
                )
                """
            ),
            values,
        )

    def complete_run(
        self,
        detection_run_id: UUID,
        *,
        status: str,
        image_count: int,
        component_count: int,
        detection_count: int,
        crop_count: int,
        warning_count: int,
    ) -> None:
        self.connection.execute(
            text(
                """
                UPDATE cell_detection_runs
                SET status=:status,processed_image_count=:image_count,
                  component_count=:component_count,detection_count=:detection_count,
                  crop_count=:crop_count,warning_count=:warning_count,
                  completed_at=now(),updated_at=now()
                WHERE id=:id AND status='processing'
                """
            ),
            {
                "id": detection_run_id,
                "status": status,
                "image_count": image_count,
                "component_count": component_count,
                "detection_count": detection_count,
                "crop_count": crop_count,
                "warning_count": warning_count,
            },
        )

    def fail_run(self, detection_run_id: UUID, *, error_code: str, error_message: str) -> None:
        self.connection.execute(
            text(
                """
                UPDATE cell_detection_runs
                SET status='failed',started_at=COALESCE(started_at,now()),
                  failed_at=now(),updated_at=now(),
                  error_code=:error_code,error_message=:error_message
                WHERE id=:id AND status IN ('created','processing')
                """
            ),
            {
                "id": detection_run_id,
                "error_code": error_code,
                "error_message": error_message,
            },
        )

    def list_runs(
        self,
        *,
        status: str | None,
        analysis_run_id: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        clauses: list[str] = []
        params: dict = {"limit": limit, "offset": offset}
        if status:
            clauses.append("dr.status=:status")
            params["status"] = status
        if analysis_run_id:
            clauses.append("dr.analysis_run_id=CAST(:analysis_run_id AS uuid)")
            params["analysis_run_id"] = analysis_run_id
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(
            text(
                f"""
                {RUN_SUMMARY_SELECT}
                {RUN_SUMMARY_FROM}
                {where}
                ORDER BY dr.created_at DESC,dr.id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
        total = self.connection.execute(
            text(f"SELECT count(*) {RUN_SUMMARY_FROM} {where}"), params
        ).scalar_one()
        return {
            "items": [dict(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_run(self, detection_run_id: str) -> dict | None:
        return _dict(
            self.connection.execute(
                text(
                    f"""
                    {RUN_SUMMARY_SELECT}
                    {RUN_SUMMARY_FROM}
                    WHERE dr.id=CAST(:id AS uuid)
                    """
                ),
                {"id": detection_run_id},
            ).mappings().first()
        )

    def list_images(self, detection_run_id: str) -> list[dict] | None:
        if not self.connection.execute(
            text("SELECT 1 FROM cell_detection_runs WHERE id=CAST(:id AS uuid)"),
            {"id": detection_run_id},
        ).scalar():
            return None
        rows = self.connection.execute(
            text(
                """
                WITH effective_reviews AS (
                  SELECT DISTINCT ON (sr.entity_id)
                    sr.entity_id,sr.decision
                  FROM scientific_reviews sr
                  JOIN cell_detections reviewed ON reviewed.id=sr.entity_id
                  WHERE sr.entity_type='cell_detection'
                    AND sr.decision<>'comment_only'
                    AND reviewed.detection_run_id=CAST(:run_id AS uuid)
                  ORDER BY sr.entity_id,sr.created_at DESC,sr.id DESC
                ),
                detection_counts AS (
                  SELECT
                    cd.analysis_run_image_id,
                    count(*) detection_count,
                    count(er.entity_id) reviewed_count
                  FROM cell_detections cd
                  LEFT JOIN effective_reviews er ON er.entity_id=cd.id
                  WHERE cd.detection_run_id=CAST(:run_id AS uuid)
                  GROUP BY cd.analysis_run_image_id
                ),
                component_counts AS (
                  SELECT
                    cc.analysis_run_image_id,
                    count(*) FILTER (
                      WHERE cc.component_status='rejected_by_filter'
                    ) warning_count
                  FROM image_connected_components cc
                  WHERE cc.detection_run_id=CAST(:run_id AS uuid)
                  GROUP BY cc.analysis_run_image_id
                )
                SELECT
                  ari.id analysis_run_image_id,ari.microscopy_image_id,
                  ari.sequence_number,
                  concat('Imagen ',lpad(ari.sequence_number::text,3,'0')) safe_name,
                  mi.mime_type,
                  COALESCE(
                    (image_event.metadata_json->>'oriented_width_px')::integer,
                    ari.input_width_px
                  ) width_px,
                  COALESCE(
                    (image_event.metadata_json->>'oriented_height_px')::integer,
                    ari.input_height_px
                  ) height_px,
                  COALESCE(dc.detection_count,0) detection_count,
                  COALESCE(dc.reviewed_count,0) reviewed_count,
                  COALESCE(cc.warning_count,0) warning_count
                FROM cell_detection_runs dr
                JOIN microscopy_analysis_run_images ari
                  ON ari.analysis_run_id=dr.analysis_run_id
                JOIN microscopy_images mi ON mi.id=ari.microscopy_image_id
                LEFT JOIN detection_counts dc ON dc.analysis_run_image_id=ari.id
                LEFT JOIN component_counts cc ON cc.analysis_run_image_id=ari.id
                LEFT JOIN LATERAL (
                  SELECT event.metadata_json
                  FROM cell_detection_events event
                  WHERE event.detection_run_id=dr.id
                    AND event.microscopy_image_id=ari.microscopy_image_id
                    AND event.event_type='cell_detection.image.completed'
                  ORDER BY event.created_at DESC,event.id DESC
                  LIMIT 1
                ) image_event ON true
                WHERE dr.id=CAST(:run_id AS uuid)
                ORDER BY ari.sequence_number,ari.id
                """
            ),
            {"run_id": detection_run_id},
        ).mappings().all()
        return [dict(row) for row in rows]

    @staticmethod
    def _detection_base() -> str:
        return """
          FROM cell_detections cd
          JOIN cell_detection_runs dr ON dr.id=cd.detection_run_id
          JOIN microscopy_analysis_run_images ari ON ari.id=cd.analysis_run_image_id
          JOIN microscopy_images mi ON mi.id=cd.microscopy_image_id
          JOIN image_connected_components cc ON cc.id=cd.connected_component_id
          JOIN cell_crops crop ON crop.cell_detection_id=cd.id
          LEFT JOIN LATERAL (
            SELECT sr.id,sr.decision,sr.comment,sr.actor_user_id,sr.created_at,
              u.username actor_username
            FROM scientific_reviews sr
            JOIN users u ON u.id=sr.actor_user_id
            WHERE sr.entity_type='cell_detection'
              AND sr.entity_id=cd.id
              AND sr.decision<>'comment_only'
            ORDER BY sr.created_at DESC,sr.id DESC
            LIMIT 1
          ) latest ON true
        """

    @staticmethod
    def _detection_select() -> str:
        return """
          SELECT
            cd.*,dr.detection_run_code,dr.detector_key,dr.detector_version,
            dr.algorithm_version,
            COALESCE(latest.decision,'unreviewed') review_status,
            latest.id latest_review_id,latest.comment latest_review_comment,
            latest.actor_user_id latest_review_actor_user_id,
            latest.actor_username latest_review_actor_username,
            latest.created_at latest_review_created_at,
            crop.id crop_id,crop.sha256 crop_sha256,
            crop.file_size_bytes crop_file_size_bytes,
            crop.width_px crop_width_px,crop.height_px crop_height_px,
            crop.format crop_format,crop.padding_px crop_padding_px,
            cc.area_px,cc.perimeter_px,cc.circularity,cc.solidity,
            cc.touches_border,cc.metrics_json component_metrics_json,
            ari.sequence_number source_sequence_number,
            concat('Imagen ',lpad(ari.sequence_number::text,3,'0')) source_safe_name,
            mi.mime_type source_mime_type,
            COALESCE(
              (image_event.metadata_json->>'oriented_width_px')::integer,
              ari.input_width_px
            ) source_width_px,
            COALESCE(
              (image_event.metadata_json->>'oriented_height_px')::integer,
              ari.input_height_px
            ) source_height_px
        """

    @staticmethod
    def _detection_image_event_join() -> str:
        return """
          LEFT JOIN LATERAL (
            SELECT event.metadata_json
            FROM cell_detection_events event
            WHERE event.detection_run_id=dr.id
              AND event.microscopy_image_id=cd.microscopy_image_id
              AND event.event_type='cell_detection.image.completed'
            ORDER BY event.created_at DESC,event.id DESC
            LIMIT 1
          ) image_event ON true
        """

    def list_detections(
        self,
        *,
        detection_run_id: str,
        microscopy_image_id: str,
        review_status: str | None,
        limit: int,
        offset: int,
    ) -> dict | None:
        exists = self.connection.execute(
            text(
                """
                SELECT 1 FROM cell_detection_runs dr
                JOIN microscopy_analysis_run_images ari
                  ON ari.analysis_run_id=dr.analysis_run_id
                WHERE dr.id=CAST(:run_id AS uuid)
                  AND ari.microscopy_image_id=CAST(:image_id AS uuid)
                """
            ),
            {"run_id": detection_run_id, "image_id": microscopy_image_id},
        ).scalar()
        if not exists:
            return None
        params = {
            "run_id": detection_run_id,
            "image_id": microscopy_image_id,
            "limit": limit,
            "offset": offset,
        }
        filter_sql = ""
        if review_status:
            params["review_status"] = review_status
            filter_sql = " AND COALESCE(latest.decision,'unreviewed')=:review_status"
        base = (
            self._detection_base()
            + self._detection_image_event_join()
            + """
              WHERE cd.detection_run_id=CAST(:run_id AS uuid)
                AND cd.microscopy_image_id=CAST(:image_id AS uuid)
            """
            + filter_sql
        )
        rows = self.connection.execute(
            text(
                f"""
                {self._detection_select()}
                {base}
                ORDER BY cd.cell_index,cd.id
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
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_detection(self, cell_detection_id: str) -> dict | None:
        row = self.connection.execute(
            text(
                f"""
                {self._detection_select()}
                {self._detection_base()}
                {self._detection_image_event_join()}
                WHERE cd.id=CAST(:id AS uuid)
                """
            ),
            {"id": cell_detection_id},
        ).mappings().first()
        return _dict(row)

    def crop(self, crop_id: str) -> dict | None:
        return _dict(
            self.connection.execute(
                text(
                    """
                    SELECT crop.*,cd.detection_run_id,cd.microscopy_image_id
                    FROM cell_crops crop
                    JOIN cell_detections cd ON cd.id=crop.cell_detection_id
                    WHERE crop.id=CAST(:id AS uuid)
                    """
                ),
                {"id": crop_id},
            ).mappings().first()
        )

    def source_image(self, detection_run_id: str, microscopy_image_id: str) -> dict | None:
        return _dict(
            self.connection.execute(
                text(
                    """
                    SELECT
                      mi.id,mi.storage_key,mi.sha256,mi.file_size_bytes,
                      mi.width_px current_width_px,mi.height_px current_height_px,
                      ari.input_sha256,ari.input_file_size_bytes,
                      ari.input_width_px,ari.input_height_px,
                      mi.mime_type,mi.status,
                      concat('Imagen ',lpad(ari.sequence_number::text,3,'0')) safe_name,
                      COALESCE(
                        (image_event.metadata_json->>'oriented_width_px')::integer,
                        ari.input_width_px
                      ) width_px,
                      COALESCE(
                        (image_event.metadata_json->>'oriented_height_px')::integer,
                        ari.input_height_px
                      ) height_px
                    FROM cell_detection_runs dr
                    JOIN microscopy_analysis_run_images ari
                      ON ari.analysis_run_id=dr.analysis_run_id
                    JOIN microscopy_images mi ON mi.id=ari.microscopy_image_id
                    LEFT JOIN LATERAL (
                      SELECT event.metadata_json
                      FROM cell_detection_events event
                      WHERE event.detection_run_id=dr.id
                        AND event.microscopy_image_id=mi.id
                        AND event.event_type='cell_detection.image.completed'
                      ORDER BY event.created_at DESC,event.id DESC
                      LIMIT 1
                    ) image_event ON true
                    WHERE dr.id=CAST(:run_id AS uuid)
                      AND mi.id=CAST(:image_id AS uuid)
                      AND mi.status='available'
                    """
                ),
                {
                    "run_id": detection_run_id,
                    "image_id": microscopy_image_id,
                },
            ).mappings().first()
        )

    def create_review(
        self,
        *,
        cell_detection_id: str,
        decision: str,
        comment: str | None,
        actor_user_id: str,
    ) -> dict | None:
        exists = self.connection.execute(
            text(
                "SELECT 1 FROM cell_detections WHERE id=CAST(:id AS uuid) FOR SHARE"
            ),
            {"id": cell_detection_id},
        ).scalar()
        if not exists:
            return None
        row = self.connection.execute(
            text(
                """
                INSERT INTO scientific_reviews(
                  id,entity_type,entity_id,decision,comment,actor_user_id
                ) VALUES(
                  :id,'cell_detection',CAST(:entity_id AS uuid),:decision,
                  :comment,CAST(:actor_user_id AS uuid)
                )
                RETURNING *
                """
            ),
            {
                "id": uuid4(),
                "entity_id": cell_detection_id,
                "decision": decision,
                "comment": comment,
                "actor_user_id": actor_user_id,
            },
        ).mappings().one()
        return dict(row)

    def reviews(
        self, cell_detection_id: str, *, limit: int, offset: int
    ) -> dict | None:
        if not self.connection.execute(
            text("SELECT 1 FROM cell_detections WHERE id=CAST(:id AS uuid)"),
            {"id": cell_detection_id},
        ).scalar():
            return None
        params = {"id": cell_detection_id, "limit": limit, "offset": offset}
        rows = self.connection.execute(
            text(
                """
                SELECT sr.*,u.username actor_username
                FROM scientific_reviews sr
                JOIN users u ON u.id=sr.actor_user_id
                WHERE sr.entity_type='cell_detection'
                  AND sr.entity_id=CAST(:id AS uuid)
                ORDER BY sr.created_at,sr.id
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
        total = self.connection.execute(
            text(
                """
                SELECT count(*) FROM scientific_reviews
                WHERE entity_type='cell_detection'
                  AND entity_id=CAST(:id AS uuid)
                """
            ),
            params,
        ).scalar_one()
        return {
            "items": [dict(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def events(self, detection_run_id: str) -> list[dict] | None:
        if not self.connection.execute(
            text("SELECT 1 FROM cell_detection_runs WHERE id=CAST(:id AS uuid)"),
            {"id": detection_run_id},
        ).scalar():
            return None
        rows = self.connection.execute(
            text(
                """
                SELECT * FROM cell_detection_events
                WHERE detection_run_id=CAST(:id AS uuid)
                ORDER BY created_at,id
                """
            ),
            {"id": detection_run_id},
        ).mappings().all()
        return [dict(row) for row in rows]
