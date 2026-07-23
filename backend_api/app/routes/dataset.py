from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from app.services.dataset_browser import (
    DATASET_IMAGE_PAGE_SIZE_CHOICES,
    DEFAULT_DATASET_IMAGE_PAGE_SIZE,
    dataset_image_detail,
    dataset_summary,
    paginated_dataset_images,
    resolve_dataset_image_file,
)


router = APIRouter(prefix="/api/dataset", tags=["dataset"])


@router.get("")
def dataset(datasource: str | None = Query(default="malaria")):
    return dataset_summary(datasource)


@router.get("/summary")
def dataset_summary_endpoint(datasource: str | None = Query(default="malaria")):
    return dataset_summary(datasource)


@router.get("/split")
def dataset_split(datasource: str | None = Query(default="malaria")):
    summary = dataset_summary(datasource)
    return {
        "split_process": summary["split_process"],
        "counts": summary["counts"],
        "split_table": summary["split_table"],
    }


@router.get("/images")
def dataset_images(
    datasource: str | None = Query(default="malaria"),
    split: str | None = Query(default=None),
    class_name: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(
        default=DEFAULT_DATASET_IMAGE_PAGE_SIZE,
        description="Tamaño de página permitido: 12, 24, 48 o 96.",
        json_schema_extra={"enum": list(DATASET_IMAGE_PAGE_SIZE_CHOICES)},
    ),
):
    return paginated_dataset_images(
        datasource=datasource,
        split=split,
        class_name=class_name,
        page=page,
        page_size=page_size,
    )


@router.get("/images/{image_id}")
def dataset_image(
    image_id: str,
    datasource: str | None = Query(default="malaria"),
):
    return dataset_image_detail(datasource=datasource, image_id=image_id)


@router.get("/images/{image_id}/file")
def dataset_image_file(
    image_id: str,
    datasource: str | None = Query(default="malaria"),
):
    path, media_type = resolve_dataset_image_file(datasource=datasource, image_id=image_id)
    return FileResponse(
        path,
        media_type=media_type,
        headers={"X-Content-Type-Options": "nosniff"},
    )
