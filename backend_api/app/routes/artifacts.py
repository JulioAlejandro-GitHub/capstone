from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from app.services.artifacts import resolve_artifact_reference


router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/file")
def artifact_file(
    datasource: str | None = Query(default="malaria"),
    artifact_id: str | None = Query(default=None),
    path: str | None = Query(default=None),
):
    artifact = resolve_artifact_reference(
        datasource=datasource,
        artifact_id=artifact_id,
        path=path,
    )
    return FileResponse(
        artifact.path,
        media_type=artifact.media_type,
        headers={"X-Content-Type-Options": "nosniff"},
    )
