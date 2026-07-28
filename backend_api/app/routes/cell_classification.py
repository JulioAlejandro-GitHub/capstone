from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response

from app.audit import service_audited_permission, transactional_permission
from app.config import get_settings
from app.schemas.cell_classification import (
    CellClassificationReviewCreate,
    CellClassificationRunCreate,
    CellExplanationRequest,
)
from app.security import Permission, Principal, require_permission
from app.services.cell_classification import (
    CellClassificationError,
    CellClassificationService,
)


router = APIRouter(
    prefix="/api/v1/cell-classification",
    tags=["cell-classification"],
)
service = CellClassificationService()


def execute(call):
    try:
        return call()
    except CellClassificationError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get("/eligible-detection-runs")
def eligible_detection_runs(
    detection_run_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_CELL_CLASSIFICATION_READ)
    ),
):
    return execute(
        lambda: service.eligible_detection_runs(
            detection_run_id=(
                str(detection_run_id) if detection_run_id is not None else None
            ),
            limit=limit,
            offset=offset,
        )
    )


@router.post("/classification-runs", status_code=201)
async def create_classification_run(
    body: CellClassificationRunCreate,
    request: Request,
    principal: Principal = Depends(
        service_audited_permission(
            Permission.SCIENTIFIC_CELL_CLASSIFICATION_EXECUTE
        )
    ),
):
    try:
        return await run_in_threadpool(
            service.execute_classification,
            str(body.detection_run_id),
            principal,
            request,
        )
    except CellClassificationError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get("/classification-runs")
def list_classification_runs(
    status: Literal[
        "created",
        "processing",
        "completed",
        "completed_with_warnings",
        "failed",
    ]
    | None = None,
    analysis_run_id: UUID | None = None,
    detection_run_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_CELL_CLASSIFICATION_READ)
    ),
):
    return execute(
        lambda: service.list_runs(
            status=status,
            analysis_run_id=(
                str(analysis_run_id) if analysis_run_id is not None else None
            ),
            detection_run_id=(
                str(detection_run_id) if detection_run_id is not None else None
            ),
            limit=limit,
            offset=offset,
        )
    )


@router.get("/classification-runs/{classification_run_id}")
def classification_run_detail(
    classification_run_id: UUID,
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_CELL_CLASSIFICATION_READ)
    ),
):
    return execute(lambda: service.get_run(str(classification_run_id)))


@router.get("/classification-runs/{classification_run_id}/predictions")
def classification_run_predictions(
    classification_run_id: UUID,
    microscopy_image_id: UUID | None = None,
    predicted_label: Literal["parasitized", "uninfected"] | None = None,
    near_threshold: bool | None = None,
    prediction_status: Literal["completed", "failed"] | None = None,
    review_status: Literal[
        "unreviewed", "confirmed", "corrected", "needs_attention"
    ]
    | None = None,
    cell_code: str | None = Query(default=None, max_length=40),
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_CELL_CLASSIFICATION_READ)
    ),
):
    maximum = get_settings().cell_classification_page_max
    if limit > maximum:
        raise HTTPException(422, f"limit no puede superar {maximum}.")
    return execute(
        lambda: service.list_predictions(
            classification_run_id=str(classification_run_id),
            microscopy_image_id=(
                str(microscopy_image_id)
                if microscopy_image_id is not None
                else None
            ),
            predicted_label=predicted_label,
            near_threshold=near_threshold,
            prediction_status=prediction_status,
            review_status=review_status,
            cell_code=cell_code,
            limit=limit,
            offset=offset,
        )
    )


@router.get("/classification-runs/{classification_run_id}/summary")
def classification_run_summary(
    classification_run_id: UUID,
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_CELL_CLASSIFICATION_READ)
    ),
):
    return execute(lambda: service.get_summary(str(classification_run_id)))


@router.get("/predictions/{prediction_id}")
def prediction_detail(
    prediction_id: UUID,
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_CELL_CLASSIFICATION_READ)
    ),
):
    return execute(lambda: service.get_prediction(str(prediction_id)))


@router.post("/predictions/{prediction_id}/explanation", status_code=201)
async def generate_prediction_explanation(
    prediction_id: UUID,
    request: Request,
    body: CellExplanationRequest | None = None,
    principal: Principal = Depends(
        service_audited_permission(
            Permission.SCIENTIFIC_CELL_CLASSIFICATION_EXPLAIN
        )
    ),
):
    retry = body.retry if body is not None else False
    try:
        return await run_in_threadpool(
            service.generate_explanation,
            str(prediction_id),
            retry,
            principal,
            request,
        )
    except CellClassificationError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get("/predictions/{prediction_id}/explanation")
def prediction_explanation(
    prediction_id: UUID,
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_CELL_CLASSIFICATION_READ)
    ),
):
    return execute(
        lambda: service.get_prediction_explanation(str(prediction_id))
    )


def _explanation_file(explanation_id: UUID, kind: Literal["heatmap", "overlay"]):
    explanation, payload = execute(
        lambda: service.explanation_content(str(explanation_id), kind)
    )
    size_key = f"{kind}_file_size_bytes"
    sha_key = f"{kind}_sha256"
    return Response(
        content=payload,
        media_type="image/png",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
            "Content-Length": str(explanation[size_key]),
            "ETag": f'"sha256-{explanation[sha_key]}"',
        },
    )


@router.get("/explanations/{explanation_id}/heatmap")
def explanation_heatmap(
    explanation_id: UUID,
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_CELL_CLASSIFICATION_READ)
    ),
):
    return _explanation_file(explanation_id, "heatmap")


@router.get("/explanations/{explanation_id}/overlay")
def explanation_overlay(
    explanation_id: UUID,
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_CELL_CLASSIFICATION_READ)
    ),
):
    return _explanation_file(explanation_id, "overlay")


@router.post("/predictions/{prediction_id}/reviews", status_code=201)
def create_prediction_review(
    prediction_id: UUID,
    body: CellClassificationReviewCreate,
    request: Request,
    principal: Principal = Depends(
        transactional_permission(
            Permission.SCIENTIFIC_CELL_CLASSIFICATION_REVIEW
        )
    ),
):
    return execute(
        lambda: service.create_review(
            prediction_id=str(prediction_id),
            decision=body.decision,
            reviewed_label=body.reviewed_label,
            comment=body.comment,
            principal=principal,
            request=request,
        )
    )


@router.get("/predictions/{prediction_id}/reviews")
def prediction_reviews(
    prediction_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_CELL_CLASSIFICATION_READ)
    ),
):
    return execute(
        lambda: service.reviews(str(prediction_id), limit=limit, offset=offset)
    )
