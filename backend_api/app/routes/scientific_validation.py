from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.audit import transactional_permission
from app.schemas.scientific import ArchiveRequest, ScientificValidationCreate, ScientificValidationUpdate
from app.security import Permission, Principal, require_permission
from app.services.scientific import ScientificError
from app.services.scientific_validation import ScientificValidationService


router = APIRouter(prefix="/api/v1/scientific-validation/sessions", tags=["scientific-validation"])
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
