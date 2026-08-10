from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.audit import transactional_permission
from app.schemas.scientific import (
    ArchiveRequest,
    ScientificValidationAnnotationCreate,
    ScientificValidationAnnotationUpdate,
    ScientificValidationCreate,
    ScientificValidationUpdate,
)
from app.security import Permission, Principal, require_permission
from app.services.scientific import ScientificError
from app.services.scientific_validation import ScientificValidationService


router = APIRouter(prefix="/api/v1/scientific-validation/sessions", tags=["scientific-validation"])
annotations_router = APIRouter(
    prefix="/api/v1/scientific-annotations", tags=["scientific-validation"]
)
service = ScientificValidationService()


def execute(call):
    try:
        return call()
    except ScientificError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("", status_code=201)
def create_session(
    body: ScientificValidationCreate,
    request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_VALIDATION_CREATE)),
):
    return execute(lambda: service.create(body.model_dump(), principal, request))


@router.get("")
def list_sessions(
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: Principal = Depends(require_permission(Permission.SCIENTIFIC_VALIDATION_READ)),
):
    return execute(lambda: service.list(status, limit, offset))


@router.post("/{session_id}/annotations", status_code=201)
def create_annotation(
    session_id: UUID,
    body: ScientificValidationAnnotationCreate,
    request: Request,
    principal: Principal = Depends(
        transactional_permission(Permission.SCIENTIFIC_VALIDATION_ANNOTATE)
    ),
):
    return execute(lambda: service.create_annotation(
        str(session_id), body.model_dump(), principal, request
    ))


@router.get("/{session_id}/annotations")
def list_annotations(
    session_id: UUID,
    target_type: str | None = Query(None, pattern="^(cell|analysis|sample)$"),
    cell_id: UUID | None = None,
    analysis_run_id: UUID | None = None,
    sample_id: UUID | None = None,
    category: str | None = Query(None, min_length=1, max_length=120),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: Principal = Depends(require_permission(Permission.SCIENTIFIC_VALIDATION_READ)),
):
    return execute(lambda: service.list_annotations(
        str(session_id), target_type=target_type,
        cell_id=str(cell_id) if cell_id else None,
        analysis_run_id=str(analysis_run_id) if analysis_run_id else None,
        sample_id=str(sample_id) if sample_id else None,
        category=category, limit=limit, offset=offset,
    ))


@router.get("/{session_id}/annotations/{annotation_id}")
def get_annotation(
    session_id: UUID,
    annotation_id: UUID,
    _: Principal = Depends(require_permission(Permission.SCIENTIFIC_VALIDATION_READ)),
):
    return execute(lambda: service.get_annotation(str(session_id), str(annotation_id)))


@router.patch("/{session_id}/annotations/{annotation_id}")
def update_annotation(
    session_id: UUID,
    annotation_id: UUID,
    body: ScientificValidationAnnotationUpdate,
    request: Request,
    principal: Principal = Depends(
        transactional_permission(Permission.SCIENTIFIC_VALIDATION_ANNOTATE)
    ),
):
    return execute(lambda: service.update_annotation(
        str(session_id), str(annotation_id), body.model_dump(exclude_unset=True),
        principal, request,
    ))


@router.get("/{session_id}/annotations/{annotation_id}/history")
def annotation_history(
    session_id: UUID,
    annotation_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: Principal = Depends(require_permission(Permission.SCIENTIFIC_VALIDATION_READ)),
):
    return execute(lambda: service.annotation_history(
        str(session_id), str(annotation_id), limit=limit, offset=offset
    ))


@annotations_router.post("", status_code=201)
def create_general_annotation(
    body: ScientificValidationAnnotationCreate,
    request: Request,
    principal: Principal = Depends(
        transactional_permission(Permission.SCIENTIFIC_VALIDATION_ANNOTATE)
    ),
):
    return execute(lambda: service.create_annotation(None, body.model_dump(), principal, request))


@annotations_router.get("")
def list_general_annotations(
    target_type: str = Query(pattern="^(cell|analysis|sample)$"),
    cell_id: UUID | None = None,
    analysis_run_id: UUID | None = None,
    sample_id: UUID | None = None,
    category: str | None = Query(None, min_length=1, max_length=120),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: Principal = Depends(require_permission(Permission.SCIENTIFIC_VALIDATION_READ)),
):
    target_ids = {"cell": cell_id, "analysis": analysis_run_id, "sample": sample_id}
    if target_ids[target_type] is None or sum(value is not None for value in target_ids.values()) != 1:
        raise HTTPException(422, "Debe especificarse exactamente el identificador del target.")
    return execute(lambda: service.list_annotations(
        None, target_type=target_type,
        cell_id=str(cell_id) if cell_id else None,
        analysis_run_id=str(analysis_run_id) if analysis_run_id else None,
        sample_id=str(sample_id) if sample_id else None,
        category=category, limit=limit, offset=offset,
    ))


@annotations_router.patch("/{annotation_id}")
def update_general_annotation(
    annotation_id: UUID,
    body: ScientificValidationAnnotationUpdate,
    request: Request,
    principal: Principal = Depends(
        transactional_permission(Permission.SCIENTIFIC_VALIDATION_ANNOTATE)
    ),
):
    return execute(lambda: service.update_annotation(
        None, str(annotation_id), body.model_dump(exclude_unset=True), principal, request
    ))


@annotations_router.get("/{annotation_id}/history")
def general_annotation_history(
    annotation_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: Principal = Depends(require_permission(Permission.SCIENTIFIC_VALIDATION_READ)),
):
    return execute(lambda: service.annotation_history(
        None, str(annotation_id), limit=limit, offset=offset
    ))


@router.get("/{session_id}")
def get_session(
    session_id: UUID,
    _: Principal = Depends(require_permission(Permission.SCIENTIFIC_VALIDATION_READ)),
):
    return execute(lambda: service.get(str(session_id)))


@router.patch("/{session_id}")
def update_session(
    session_id: UUID,
    body: ScientificValidationUpdate,
    request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_VALIDATION_UPDATE)),
):
    return execute(lambda: service.update(
        str(session_id), body.model_dump(exclude_unset=True), principal, request
    ))


@router.delete("/{session_id}")
def archive_session(
    session_id: UUID,
    request: Request,
    body: ArchiveRequest | None = None,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_VALIDATION_ARCHIVE)),
):
    return execute(lambda: service.archive(
        str(session_id), principal, request, body.reason if body else None
    ))
