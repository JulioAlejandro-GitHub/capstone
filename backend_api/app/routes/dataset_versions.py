from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.security import Permission, require_permission
from app.services.governed_datasets import (
    governed_dataset_version_detail,
    list_governed_dataset_versions,
)


router = APIRouter(
    prefix="/api/datasets",
    tags=["dataset-versions"],
    dependencies=[Depends(require_permission(Permission.DATASETS_READ))],
)


@router.get("")
def dataset_versions(datasource: str | None = Query(default="malaria")):
    return list_governed_dataset_versions(datasource)


@router.get("/{dataset_version_id}")
def dataset_version_detail(
    dataset_version_id: UUID,
    datasource: str | None = Query(default="malaria"),
):
    return governed_dataset_version_detail(datasource, dataset_version_id)
