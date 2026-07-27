from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from app.audit import transactional_permission
from app.schemas.scientific import (
    ArchiveRequest, CaseCreate, CaseUpdate, ImageCreate, ImageUpdate,
    SampleCreate, SampleUpdate, SlideCreate, SlideUpdate, SubjectCreate, SubjectUpdate,
)
from app.security import Permission, Principal, require_permission
from app.services.scientific import ScientificError, ScientificService


router = APIRouter(prefix="/api/v1/scientific", tags=["scientific-data"])
service = ScientificService()


def execute(call):
    try:
        return call()
    except ScientificError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


def values(body) -> dict:
    return body.model_dump(exclude_unset=True)


def listing(kind: str, status: str | None, search: str | None, limit: int, offset: int, **parent):
    return execute(lambda: service.list(
        kind, status=status, search=search, limit=limit, offset=offset, **parent,
    ))


@router.post("/subjects", status_code=201)
def create_subject(
    body: SubjectCreate, request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_SUBJECTS_CREATE)),
):
    return execute(lambda: service.create("subject", values(body), principal, request))


@router.get("/subjects", dependencies=[Depends(require_permission(Permission.SCIENTIFIC_SUBJECTS_READ))])
def list_subjects(
    status: str | None = None, search: str | None = None,
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
):
    return listing("subject", status, search, limit, offset)


@router.get("/subjects/{subject_id}", dependencies=[Depends(require_permission(Permission.SCIENTIFIC_SUBJECTS_READ))])
def get_subject(subject_id: UUID):
    return execute(lambda: service.get("subject", str(subject_id)))


@router.patch("/subjects/{subject_id}")
def update_subject(
    subject_id: UUID, body: SubjectUpdate, request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_SUBJECTS_UPDATE)),
):
    return execute(lambda: service.update("subject", str(subject_id), values(body), principal, request))


@router.post("/subjects/{subject_id}/archive")
def archive_subject(
    subject_id: UUID, body: ArchiveRequest, request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_SUBJECTS_ARCHIVE)),
):
    return execute(lambda: service.archive("subject", str(subject_id), principal, request, body.reason))


@router.post("/cases", status_code=201)
def create_case(
    body: CaseCreate, request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_CASES_CREATE)),
):
    return execute(lambda: service.create("case", values(body), principal, request))


@router.get("/cases", dependencies=[Depends(require_permission(Permission.SCIENTIFIC_CASES_READ))])
def list_cases(
    status: str | None = None, search: str | None = None,
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
):
    return listing("case", status, search, limit, offset)


@router.get("/cases/{case_id}", dependencies=[Depends(require_permission(Permission.SCIENTIFIC_CASES_READ))])
def get_case(case_id: UUID):
    return execute(lambda: service.get("case", str(case_id)))


@router.patch("/cases/{case_id}")
def update_case(
    case_id: UUID, body: CaseUpdate, request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_CASES_UPDATE)),
):
    return execute(lambda: service.update("case", str(case_id), values(body), principal, request))


@router.post("/cases/{case_id}/archive")
def archive_case(
    case_id: UUID, body: ArchiveRequest, request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_CASES_ARCHIVE)),
):
    return execute(lambda: service.archive("case", str(case_id), principal, request, body.reason))


@router.post("/cases/{case_id}/samples", status_code=201)
def create_sample(
    case_id: UUID, body: SampleCreate, request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_SAMPLES_CREATE)),
):
    return execute(lambda: service.create("sample", values(body), principal, request, parent_id=str(case_id)))


@router.get("/cases/{case_id}/samples", dependencies=[Depends(require_permission(Permission.SCIENTIFIC_SAMPLES_READ))])
def list_samples(
    case_id: UUID, status: str | None = None, search: str | None = None,
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
):
    return listing("sample", status, search, limit, offset, parent_column="case_id", parent_id=str(case_id))


@router.get("/samples/{sample_id}", dependencies=[Depends(require_permission(Permission.SCIENTIFIC_SAMPLES_READ))])
def get_sample(sample_id: UUID):
    return execute(lambda: service.get("sample", str(sample_id)))


@router.patch("/samples/{sample_id}")
def update_sample(
    sample_id: UUID, body: SampleUpdate, request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_SAMPLES_UPDATE)),
):
    return execute(lambda: service.update("sample", str(sample_id), values(body), principal, request))


@router.post("/samples/{sample_id}/archive")
def archive_sample(
    sample_id: UUID, body: ArchiveRequest, request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_SAMPLES_ARCHIVE)),
):
    return execute(lambda: service.archive("sample", str(sample_id), principal, request, body.reason))


@router.post("/samples/{sample_id}/slides", status_code=201)
def create_slide(
    sample_id: UUID, body: SlideCreate, request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_SLIDES_CREATE)),
):
    return execute(lambda: service.create("slide", values(body), principal, request, parent_id=str(sample_id)))


@router.get("/samples/{sample_id}/slides", dependencies=[Depends(require_permission(Permission.SCIENTIFIC_SLIDES_READ))])
def list_slides(
    sample_id: UUID, status: str | None = None, search: str | None = None,
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
):
    return listing("slide", status, search, limit, offset, parent_column="sample_id", parent_id=str(sample_id))


@router.get("/slides/{slide_id}", dependencies=[Depends(require_permission(Permission.SCIENTIFIC_SLIDES_READ))])
def get_slide(slide_id: UUID):
    return execute(lambda: service.get("slide", str(slide_id)))


@router.patch("/slides/{slide_id}")
def update_slide(
    slide_id: UUID, body: SlideUpdate, request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_SLIDES_UPDATE)),
):
    return execute(lambda: service.update("slide", str(slide_id), values(body), principal, request))


@router.post("/slides/{slide_id}/archive")
def archive_slide(
    slide_id: UUID, body: ArchiveRequest, request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_SLIDES_ARCHIVE)),
):
    return execute(lambda: service.archive("slide", str(slide_id), principal, request, body.reason))


@router.post("/slides/{slide_id}/images", status_code=201)
def register_image(
    slide_id: UUID, body: ImageCreate, request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_IMAGES_REGISTER)),
):
    return execute(lambda: service.create("image", values(body), principal, request, parent_id=str(slide_id)))


@router.get("/slides/{slide_id}/images", dependencies=[Depends(require_permission(Permission.SCIENTIFIC_IMAGES_READ))])
def list_images(
    slide_id: UUID, status: str | None = None, search: str | None = None,
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
):
    return listing("image", status, search, limit, offset, parent_column="slide_id", parent_id=str(slide_id))


@router.get("/images/{image_id}", dependencies=[Depends(require_permission(Permission.SCIENTIFIC_IMAGES_READ))])
def get_image(image_id: UUID):
    return execute(lambda: service.get("image", str(image_id)))


@router.patch("/images/{image_id}")
def update_image(
    image_id: UUID, body: ImageUpdate, request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_IMAGES_UPDATE)),
):
    return execute(lambda: service.update("image", str(image_id), values(body), principal, request))


@router.post("/images/{image_id}/archive")
def archive_image(
    image_id: UUID, body: ArchiveRequest, request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_IMAGES_ARCHIVE)),
):
    return execute(lambda: service.archive("image", str(image_id), principal, request, body.reason))


@router.get("/cases/{case_id}/traceability", dependencies=[Depends(require_permission(Permission.SCIENTIFIC_CASES_READ))])
def traceability(case_id: UUID):
    return execute(lambda: service.traceability(str(case_id)))
