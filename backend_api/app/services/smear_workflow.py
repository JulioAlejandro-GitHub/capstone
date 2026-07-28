from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db import get_primary_engine
from app.services.cell_analysis import CellAnalysisService
from app.services.microscopy_analysis import MicroscopyAnalysisService
from app.services.scientific import ScientificError


ANALYSIS_FIELDS = (
    "id",
    "ingestion_batch_id",
    "subject_id",
    "case_id",
    "sample_id",
    "slide_id",
    "run_code",
    "run_status",
    "active_stage",
    "quality_gate_status",
    "ready_for_analysis",
    "quality_profile_key",
    "quality_profile_version",
    "quality_algorithm_version",
    "quality_profile_snapshot",
    "input_manifest_sha256",
    "input_image_count",
    "requested_by",
    "requested_by_username",
    "subject_code",
    "sample_code",
    "slide_code",
    "ingestion_status",
    "source_system",
    "started_at",
    "completed_at",
    "failed_at",
    "error_code",
    "error_message",
    "created_at",
    "updated_at",
    "images",
    "events",
    "decisions",
)
IMAGE_FIELDS = (
    "id",
    "image_code",
    "original_filename",
    "mime_type",
    "file_size_bytes",
    "sha256",
    "width_px",
    "height_px",
    "bit_depth",
    "detected_format",
    "channel_count",
    "color_space",
    "orientation",
    "status",
    "image_sequence_number",
    "captured_at",
    "created_at",
)
QUEUE_FIELDS = (
    "queue_item_id",
    "analysis_run_id",
    "run_code",
    "subject_code",
    "sample_code",
    "priority",
    "status",
    "attempt_count",
    "requested_by",
    "requested_by_username",
    "requested_at",
    "started_at",
    "completed_at",
    "failed_at",
    "last_error_code",
    "last_error_message",
    "created_at",
    "updated_at",
)
DETECTION_FIELDS = (
    "id",
    "analysis_run_id",
    "detection_run_code",
    "detector_key",
    "detector_version",
    "algorithm_version",
    "profile_snapshot",
    "input_manifest_sha256",
    "status",
    "image_count",
    "processed_image_count",
    "component_count",
    "detection_count",
    "crop_count",
    "warning_count",
    "requested_by",
    "analysis_run_code",
    "subject_code",
    "sample_code",
    "slide_code",
    "reviewed_count",
    "pending_review_count",
    "accepted_count",
    "rejected_count",
    "needs_attention_count",
    "started_at",
    "completed_at",
    "failed_at",
    "error_code",
    "error_message",
    "created_at",
    "updated_at",
    "images",
    "events",
    "review_counts",
)


def _only(row: dict | None, fields: tuple[str, ...]) -> dict | None:
    if row is None:
        return None
    return {field: row.get(field) for field in fields}


def derive_workflow_stage(
    batch: dict,
    analysis_run: dict | None,
    queue_item: dict | None,
    detection_run: dict | None,
) -> str:
    if detection_run:
        if detection_run["status"] in {"completed", "completed_with_warnings"}:
            return "review_ready"
        if detection_run["status"] in {"created", "processing"}:
            return "detection_processing"
        if detection_run["status"] == "failed":
            return "error"

    if analysis_run:
        # An approved warning retains quality_gate_status=warning. The durable
        # ready flag is therefore authoritative for advancing to detection.
        if analysis_run["ready_for_analysis"]:
            return "ready_for_detection"
        if analysis_run["quality_gate_status"] == "warning":
            return "quality_warning"
        if analysis_run["quality_gate_status"] == "fail":
            return "quality_failed"
        if analysis_run["quality_gate_status"] == "error":
            return "error"
        if analysis_run["run_status"] in {"failed", "cancelled"}:
            return "error"

    if queue_item:
        if queue_item["status"] == "running":
            return "quality_processing"
        if queue_item["status"] == "queued":
            return "quality_queued"
        if queue_item["status"] == "failed":
            return "error"

    if analysis_run and analysis_run["run_status"] == "quality_processing":
        return "quality_processing"
    if analysis_run:
        return "creating_analysis"
    if batch["status"] in {"failed", "inconsistent"}:
        return "error"
    return "ingested"


def build_workflow_payload(
    batch_row: dict,
    image_rows: list[dict],
    analysis_row: dict | None,
    queue_row: dict | None,
    detection_row: dict | None,
) -> dict:
    batch = {
        "id": batch_row["batch_id"],
        "subject_id": batch_row["subject_id"],
        "case_id": batch_row["case_id"],
        "sample_id": batch_row["sample_id"],
        "slide_id": batch_row["slide_id"],
        "acquisition_origin": batch_row["acquisition_origin"],
        "source_system": batch_row["source_system"],
        "expected_image_count": batch_row["expected_image_count"],
        "received_image_count": batch_row["received_image_count"],
        "status": batch_row["batch_status"],
        "created_at": batch_row["batch_created_at"],
        "updated_at": batch_row["batch_updated_at"],
        "completed_at": batch_row["batch_completed_at"],
        "subject_code": batch_row["subject_code"],
        "sample_code": batch_row["sample_code"],
        "slide_code": batch_row["slide_code"],
    }
    images = []
    for row in image_rows:
        image = _only(row, IMAGE_FIELDS)
        assert image is not None
        image["content_url"] = (
            f"/api/v1/scientific/images/{image['id']}/content"
        )
        images.append(image)
    analysis_run = _only(analysis_row, ANALYSIS_FIELDS)
    queue_item = _only(queue_row, QUEUE_FIELDS)
    detection_run = _only(detection_row, DETECTION_FIELDS)
    return {
        "stage": derive_workflow_stage(
            batch, analysis_run, queue_item, detection_run
        ),
        "batch": batch,
        "subject": {
            "id": batch_row["subject_id"],
            "subject_code": batch_row["subject_code"],
            "status": batch_row["subject_status"],
        },
        "case": {
            "id": batch_row["case_id"],
            "case_code": batch_row["case_code"],
            "status": batch_row["case_status"],
        },
        "sample": {
            "id": batch_row["sample_id"],
            "sample_code": batch_row["sample_code"],
            "status": batch_row["sample_status"],
        },
        "slide": {
            "id": batch_row["slide_id"],
            "slide_code": batch_row["slide_code"],
            "status": batch_row["slide_status"],
        },
        "images": images,
        "analysis_run": analysis_run,
        "queue_item": queue_item,
        "detection_run": detection_run,
    }


class SmearWorkflowService:
    def __init__(self, engine: Engine | None = None):
        self.engine = engine or get_primary_engine()

    def list(
        self,
        *,
        limit: int,
        offset: int,
        run_code: str | None = None,
        subject_code: str | None = None,
        sample_code: str | None = None,
        status: str | None = None,
        quality_gate_status: str | None = None,
        ready_for_analysis: bool | None = None,
        created_from=None,
        created_to=None,
    ) -> dict:
        clauses: list[str] = []
        params: dict = {"limit": limit, "offset": offset}
        filters = {
            "run_code": (run_code, "r.run_code ILIKE :run_code"),
            "subject_code": (
                subject_code,
                "rs.subject_code ILIKE :subject_code",
            ),
            "sample_code": (
                sample_code,
                "bs.sample_code ILIKE :sample_code",
            ),
            "status": (status, "r.run_status = :status"),
            "quality_gate_status": (
                quality_gate_status,
                "r.quality_gate_status = :quality_gate_status",
            ),
        }
        for key, (value, expression) in filters.items():
            if value is None or value == "":
                continue
            clauses.append(expression)
            params[key] = (
                f"%{value}%" if key.endswith("_code") else value
            )
        if ready_for_analysis is not None:
            clauses.append("r.ready_for_analysis = :ready_for_analysis")
            params["ready_for_analysis"] = ready_for_analysis
        if created_from is not None:
            clauses.append("r.created_at >= :created_from")
            params["created_from"] = created_from
        if created_to is not None:
            clauses.append("r.created_at < :created_to + INTERVAL '1 day'")
            params["created_to"] = created_to
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        base = f"""
          FROM microscopy_analysis_runs r
          JOIN research_subjects rs ON rs.id = r.subject_id
          JOIN blood_samples bs ON bs.id = r.sample_id
          JOIN smear_slides ss ON ss.id = r.slide_id
          JOIN image_ingestion_batches b ON b.id = r.ingestion_batch_id
          JOIN users u ON u.id = r.requested_by
          LEFT JOIN LATERAL (
            SELECT q.status
            FROM quality_assessment_queue_items q
            WHERE q.analysis_run_id = r.id
            ORDER BY q.updated_at DESC, q.created_at DESC, q.id DESC
            LIMIT 1
          ) q ON true
          LEFT JOIN LATERAL (
            SELECT d.id, d.status, d.detection_count
            FROM cell_detection_runs d
            WHERE d.analysis_run_id = r.id
            ORDER BY d.created_at DESC, d.id DESC
            LIMIT 1
          ) d ON true
          LEFT JOIN LATERAL (
            SELECT count(*) FILTER (
                     WHERE latest.decision IS NOT NULL
                       AND latest.decision <> 'comment_only'
                   )::integer reviewed_count
            FROM cell_detections cd
            LEFT JOIN LATERAL (
              SELECT sr.decision
              FROM scientific_reviews sr
              WHERE sr.entity_type = 'cell_detection'
                AND sr.entity_id = cd.id
                AND sr.decision <> 'comment_only'
              ORDER BY sr.created_at DESC, sr.id DESC
              LIMIT 1
            ) latest ON true
            WHERE cd.detection_run_id = d.id
          ) reviews ON true
          {where}
        """
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    f"""
                    SELECT
                      r.ingestion_batch_id,
                      r.id analysis_run_id,
                      r.run_code,
                      rs.subject_code,
                      bs.sample_code,
                      ss.slide_code,
                      r.input_image_count image_count,
                      r.run_status analysis_status,
                      r.quality_gate_status,
                      r.ready_for_analysis,
                      q.status queue_status,
                      d.id detection_run_id,
                      d.status detection_status,
                      COALESCE(d.detection_count, 0)::integer detection_count,
                      COALESCE(reviews.reviewed_count, 0)::integer reviewed_count,
                      u.username requested_by_username,
                      b.source_system,
                      r.created_at,
                      r.completed_at
                    {base}
                    ORDER BY r.created_at DESC, r.id DESC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                params,
            ).mappings().all()
            total = connection.execute(
                text(f"SELECT count(*) {base}"), params
            ).scalar_one()
        return {
            "items": [dict(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_by_analysis_run(self, analysis_run_id: str) -> dict:
        with self.engine.connect() as connection:
            identity = connection.execute(
                text(
                    """
                    SELECT ingestion_batch_id
                    FROM microscopy_analysis_runs
                    WHERE id = CAST(:id AS uuid)
                    """
                ),
                {"id": analysis_run_id},
            ).mappings().first()
        if not identity:
            raise ScientificError(404, "Análisis histórico inexistente.")
        return self.get(
            str(identity["ingestion_batch_id"]),
            analysis_run_id=analysis_run_id,
        )

    def get(
        self,
        ingestion_batch_id: str,
        analysis_run_id: str | None = None,
    ) -> dict:
        with self.engine.connect() as connection:
            batch = connection.execute(
                text(
                    """
                    SELECT
                      b.id batch_id,b.subject_id,b.case_id,b.sample_id,b.slide_id,
                      b.acquisition_origin,b.source_system,b.expected_image_count,
                      b.received_image_count,b.status batch_status,
                      b.created_at batch_created_at,b.updated_at batch_updated_at,
                      b.completed_at batch_completed_at,
                      rs.subject_code,rs.status subject_status,
                      c.case_code,c.status case_status,
                      bs.sample_code,bs.status sample_status,
                      ss.slide_code,ss.status slide_status
                    FROM image_ingestion_batches b
                    JOIN research_subjects rs ON rs.id=b.subject_id
                    JOIN scientific_cases c ON c.id=b.case_id
                    JOIN blood_samples bs ON bs.id=b.sample_id
                    JOIN smear_slides ss ON ss.id=b.slide_id
                    WHERE b.id=CAST(:id AS uuid)
                    """
                ),
                {"id": ingestion_batch_id},
            ).mappings().first()
            if not batch:
                raise ScientificError(404, "Workflow de frotis inexistente.")

            images = connection.execute(
                text(
                    """
                    SELECT
                      id,image_code,original_filename,mime_type,file_size_bytes,
                      sha256,width_px,height_px,bit_depth,detected_format,
                      channel_count,color_space,orientation,status,
                      image_sequence_number,captured_at,created_at
                    FROM microscopy_images
                    WHERE ingestion_batch_id=:id
                    ORDER BY image_sequence_number,id
                    """
                ),
                {"id": batch["batch_id"]},
            ).mappings().all()
            analysis_identity = connection.execute(
                text(
                    """
                    SELECT id
                    FROM microscopy_analysis_runs
                    WHERE ingestion_batch_id = :batch_id
                      AND (
                        CAST(:analysis_run_id AS uuid) IS NULL
                        OR id = CAST(:analysis_run_id AS uuid)
                      )
                    ORDER BY created_at DESC,id DESC
                    LIMIT 1
                    """
                ),
                {
                    "batch_id": batch["batch_id"],
                    "analysis_run_id": analysis_run_id,
                },
            ).mappings().first()
            if analysis_run_id and not analysis_identity:
                raise ScientificError(404, "Análisis histórico inexistente.")

            analysis = None
            queue = None
            detection_id = None
            if analysis_identity:
                analysis = MicroscopyAnalysisService().get(
                    str(analysis_identity["id"]), connection
                )
                queue = connection.execute(
                    text(
                        """
                        SELECT
                          q.id queue_item_id,q.analysis_run_id,r.run_code,
                          rs.subject_code,bs.sample_code,q.priority,q.status,
                          q.attempt_count,q.requested_by,
                          u.username requested_by_username,q.requested_at,
                          q.started_at,q.completed_at,q.failed_at,
                          q.last_error_code,q.last_error_message,
                          q.created_at,q.updated_at
                        FROM quality_assessment_queue_items q
                        JOIN microscopy_analysis_runs r
                          ON r.id=q.analysis_run_id
                        JOIN research_subjects rs ON rs.id=r.subject_id
                        JOIN blood_samples bs ON bs.id=r.sample_id
                        JOIN users u ON u.id=q.requested_by
                        WHERE q.analysis_run_id=:id
                        ORDER BY
                          CASE q.status
                            WHEN 'running' THEN 0
                            WHEN 'queued' THEN 1
                            ELSE 2
                          END,
                          q.updated_at DESC,q.created_at DESC,q.id DESC
                        LIMIT 1
                        """
                    ),
                    {"id": analysis["id"]},
                ).mappings().first()
                detection_identity = connection.execute(
                    text(
                        """
                        SELECT id
                        FROM cell_detection_runs
                        WHERE analysis_run_id=:id
                        ORDER BY created_at DESC,id DESC
                        LIMIT 1
                        """
                    ),
                    {"id": analysis["id"]},
                ).mappings().first()
                detection_id = (
                    detection_identity["id"] if detection_identity else None
                )

        detection = (
            CellAnalysisService(engine=self.engine).get_run(str(detection_id))
            if detection_id
            else None
        )

        return build_workflow_payload(
            dict(batch),
            [dict(row) for row in images],
            analysis,
            dict(queue) if queue else None,
            detection,
        )
