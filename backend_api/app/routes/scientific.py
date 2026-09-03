from __future__ import annotations

from uuid import UUID

import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse

from app.audit import transactional_permission
from app.schemas.scientific import (
    ArchiveRequest, CaseCreate, CaseUpdate, ImageCreate, ImageUpdate,
    SampleCreate, SampleUpdate, SlideCreate, SlideUpdate, SubjectCreate, SubjectUpdate,
)
from app.security import Permission, Principal, require_permission
from app.services.scientific import ScientificError, ScientificService
from app.services.image_ingestion import ImageIngestionService
from app.services.local_storage import LocalStorage, StorageError
from app.services.smear_workflow import SmearWorkflowService


router = APIRouter(prefix="/api/v1/scientific", tags=["scientific-data"])
service = ScientificService()
ingestion = ImageIngestionService()
workflow_service = SmearWorkflowService()


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


@router.get("/subjects/lookup")
def lookup_subject(
    subject_code: str = Query(min_length=1, max_length=120),
    _: Principal = Depends(require_permission(Permission.SCIENTIFIC_SUBJECTS_READ)),
):
    return execute(lambda: ingestion.lookup_subject(subject_code))


@router.post("/subjects/auto", status_code=201)
def auto_subject(
    request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_SUBJECTS_CREATE)),
):
    return execute(lambda: ingestion.auto_subject(principal, request))


@router.get("/subjects/{subject_id}/samples")
def subject_samples(
    subject_id: UUID, sample_code: str | None = Query(None, max_length=120),
    _: Principal = Depends(require_permission(Permission.SCIENTIFIC_SAMPLES_READ)),
):
    return execute(lambda: {
        "items": ingestion.samples_for_subject(str(subject_id), sample_code)
    })


@router.post("/subjects/{subject_id}/samples/auto", status_code=201)
def auto_sample(
    subject_id: UUID, request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_SAMPLES_CREATE)),
):
    return execute(lambda: ingestion.auto_sample(str(subject_id), principal, request))


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


@router.get("/images/{image_id:uuid}", dependencies=[Depends(require_permission(Permission.SCIENTIFIC_IMAGES_READ))])
def get_image(image_id: UUID):
    return execute(lambda: service.get("image", str(image_id)))


@router.get("/workflows/{ingestion_batch_id}")
def get_smear_workflow(
    ingestion_batch_id: UUID,
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_ANALYSIS_READ)
    ),
):
    return execute(lambda: workflow_service.get(str(ingestion_batch_id)))


@router.get("/workflows")
def list_smear_workflows(
    run_code: str | None = Query(None, max_length=120),
    subject_code: str | None = Query(None, max_length=120),
    sample_code: str | None = Query(None, max_length=120),
    status: str | None = Query(None, max_length=40),
    quality_gate_status: str | None = Query(None, max_length=40),
    ready_for_analysis: bool | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_ANALYSIS_READ)
    ),
):
    if created_from and created_to and created_from > created_to:
        raise HTTPException(422, "El rango de fechas es inválido.")
    return execute(lambda: workflow_service.list(
        run_code=run_code,
        subject_code=subject_code,
        sample_code=sample_code,
        status=status,
        quality_gate_status=quality_gate_status,
        ready_for_analysis=ready_for_analysis,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
        offset=offset,
    ))


@router.get("/analysis-history/{analysis_run_id}")
def get_smear_history(
    analysis_run_id: UUID,
    _: Principal = Depends(
        require_permission(Permission.SCIENTIFIC_ANALYSIS_READ)
    ),
):
    return execute(
        lambda: workflow_service.get_by_analysis_run(str(analysis_run_id))
    )


@router.post("/images/upload", status_code=201)
async def upload_images(
    request: Request,
    files: list[UploadFile] = File(...),
    subject_mode: str = Form(...),
    subject_code: str | None = Form(None),
    sample_mode: str = Form(...),
    sample_id: str | None = Form(None),
    acquisition_origin: str = Form("manual_upload"),
    source_system: str | None = Form(None),
    external_patient_id: str | None = Form(None),
    external_sample_id: str | None = Form(None),
    source_component_id: str | None = Form(None),
    source_group_key: str | None = Form(None),
    captured_at: datetime | None = Form(None),
    metadata_json: str = Form("{}"),
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_IMAGES_REGISTER)),
):
    forbidden = {
        "created_by", "uploaded_by", "storage_key", "sha256", "mime_type",
        "file_size_bytes", "width_px", "height_px", "bit_depth", "channel_count",
        "color_space", "orientation", "status", "ingestion_status",
        "received_image_count", "created_at", "expected_image_count",
    }
    form = await request.form()
    supplied = sorted(forbidden.intersection(form.keys()))
    if supplied:
        raise HTTPException(422, f"Campos controlados por backend: {', '.join(supplied)}")
    try:
        parsed_metadata = json.loads(metadata_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(422, "metadata_json debe ser JSON válido.") from exc
    if not isinstance(parsed_metadata, dict):
        raise HTTPException(422, "metadata_json debe ser un objeto.")
    try:
        return await ingestion.upload(
            files=files, subject_mode=subject_mode, subject_code=subject_code,
            sample_mode=sample_mode, sample_id=sample_id,
            acquisition_origin=acquisition_origin, source_system=source_system,
            external_patient_id=external_patient_id, external_sample_id=external_sample_id,
            source_component_id=source_component_id, source_group_key=source_group_key,
            captured_at=captured_at, metadata_json=parsed_metadata,
            principal=principal, request=request,
        )
    except ScientificError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get("/images/{image_id:uuid}/content")
def image_content(
    image_id: UUID,
    _: Principal = Depends(require_permission(Permission.SCIENTIFIC_IMAGES_READ)),
):
    image = execute(lambda: service.get("image", str(image_id)))
    if image["status"] == "archived":
        raise HTTPException(404, "Imagen archivada.")
    if image["status"] != "available":
        raise HTTPException(404, "Contenido no disponible.")
    if image["mime_type"] not in {"image/jpeg", "image/png", "image/tiff"}:
        raise HTTPException(404, "Contenido no disponible.")
    try:
        path = LocalStorage().resolve_verified(
            image["storage_key"],
            expected_size_bytes=image["file_size_bytes"],
            expected_sha256=image["sha256"],
        )
    except (StorageError, OSError) as exc:
        raise HTTPException(404, "Contenido no disponible.") from exc
    return FileResponse(
        path, media_type=image["mime_type"], filename=image["original_filename"] or "image",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
            "ETag": f'"sha256-{image["sha256"]}"',
        },
    )


@router.patch("/images/{image_id:uuid}")
def update_image(
    image_id: UUID, body: ImageUpdate, request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_IMAGES_UPDATE)),
):
    return execute(lambda: service.update("image", str(image_id), values(body), principal, request))


@router.post("/images/{image_id:uuid}/archive")
def archive_image(
    image_id: UUID, body: ArchiveRequest, request: Request,
    principal: Principal = Depends(transactional_permission(Permission.SCIENTIFIC_IMAGES_ARCHIVE)),
):
    return execute(lambda: service.archive("image", str(image_id), principal, request, body.reason))


@router.get("/cases/{case_id}/traceability", dependencies=[Depends(require_permission(Permission.SCIENTIFIC_CASES_READ))])
def traceability(case_id: UUID):
    return execute(lambda: service.traceability(str(case_id)))
