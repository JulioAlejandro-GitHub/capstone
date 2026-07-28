from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from app.audit import service_audited_permission, transactional_permission
from app.config import get_settings
from app.schemas.cell_analysis import CellDetectionRunCreate, ScientificReviewCreate
from app.security import Permission, Principal, require_permission
from app.services.cell_analysis import CellAnalysisError, CellAnalysisService


router = APIRouter(prefix="/api/v1/cell-analysis", tags=["cell-analysis"])
service = CellAnalysisService()


def execute(call):
    try:
        return call()
    except CellAnalysisError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get("/eligible-analysis-runs")
def eligible_analysis_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_CELL_DETECTION_READ)
    ),
):
    return service.eligible_analysis_runs(limit=limit, offset=offset)


@router.post("/detection-runs", status_code=201)
async def create_detection_run(
    body: CellDetectionRunCreate,
    request: Request,
    principal: Principal = Depends(
        service_audited_permission(Permission.SCIENTIFIC_CELL_DETECTION_EXECUTE)
    ),
):
    try:
        return await run_in_threadpool(
            service.execute_detection,
            str(body.analysis_run_id),
            principal,
            request,
        )
    except CellAnalysisError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get("/detection-runs")
def list_detection_runs(
    status: Literal[
        "created", "processing", "completed", "completed_with_warnings", "failed"
    ]
    | None = None,
    analysis_run_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_CELL_DETECTION_READ)
    ),
):
    return service.list_runs(
        status=status,
        analysis_run_id=str(analysis_run_id) if analysis_run_id else None,
        limit=limit,
        offset=offset,
    )


@router.get("/detection-runs/{detection_run_id}")
def detection_run_detail(
    detection_run_id: UUID,
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_CELL_DETECTION_READ)
    ),
):
    return execute(lambda: service.get_run(str(detection_run_id)))


@router.get("/detection-runs/{detection_run_id}/images")
def detection_run_images(
    detection_run_id: UUID,
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_CELL_DETECTION_READ)
    ),
):
    return execute(lambda: service.list_images(str(detection_run_id)))


@router.get(
    "/detection-runs/{detection_run_id}/images/{microscopy_image_id}/detections"
)
def image_detections(
    detection_run_id: UUID,
    microscopy_image_id: UUID,
    review_status: Literal[
        "unreviewed", "accepted", "rejected", "needs_attention"
    ]
    | None = None,
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_CELL_DETECTION_READ)
    ),
):
    maximum = get_settings().cell_detection_page_max
    if limit > maximum:
        raise HTTPException(422, f"limit no puede superar {maximum}.")
    return execute(
        lambda: service.list_detections(
            detection_run_id=str(detection_run_id),
            microscopy_image_id=str(microscopy_image_id),
            review_status=review_status,
            limit=limit,
            offset=offset,
        )
    )


@router.get(
    "/detection-runs/{detection_run_id}/images/{microscopy_image_id}/content"
)
def source_image_content(
    detection_run_id: UUID,
    microscopy_image_id: UUID,
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_CELL_DETECTION_READ)
    ),
):
    image, path = execute(
        lambda: service.source_image_content(
            str(detection_run_id), str(microscopy_image_id)
        )
    )
    return FileResponse(
        path,
        media_type=image["mime_type"],
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
            "Content-Length": str(image["input_file_size_bytes"]),
            "ETag": f'"sha256-{image["input_sha256"]}"',
        },
    )


@router.get("/detections/{cell_detection_id}")
def detection_detail(
    cell_detection_id: UUID,
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_CELL_DETECTION_READ)
    ),
):
    return execute(lambda: service.get_detection(str(cell_detection_id)))


@router.get("/crops/{crop_id}/content")
def crop_content(
    crop_id: UUID,
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_CELL_DETECTION_READ)
    ),
):
    crop, path = execute(lambda: service.crop_content(str(crop_id)))
    return FileResponse(
        path,
        media_type="image/png",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
            "Content-Length": str(crop["file_size_bytes"]),
            "ETag": f'"sha256-{crop["sha256"]}"',
        },
    )


@router.post("/detections/{cell_detection_id}/reviews", status_code=201)
def create_review(
    cell_detection_id: UUID,
    body: ScientificReviewCreate,
    request: Request,
    principal: Principal = Depends(
        transactional_permission(Permission.SCIENTIFIC_CELL_DETECTION_REVIEW)
    ),
):
    return execute(
        lambda: service.create_review(
            cell_detection_id=str(cell_detection_id),
            decision=body.decision,
            comment=body.comment,
            principal=principal,
            request=request,
        )
    )


@router.get("/detections/{cell_detection_id}/reviews")
def detection_reviews(
    cell_detection_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_CELL_DETECTION_READ)
    ),
):
    return execute(
        lambda: service.reviews(str(cell_detection_id), limit=limit, offset=offset)
    )
