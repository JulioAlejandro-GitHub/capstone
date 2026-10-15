from fastapi import APIRouter, Query, Depends
from fastapi.responses import FileResponse

from app.services.artifacts import resolve_artifact_reference, scientific_artifact
from app.repositories.artifacts import ArtifactReadRepository
from app.security import require_permission, Permission


router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/file", response_class=FileResponse, dependencies=[Depends(require_permission(Permission.ARTIFACTS_READ))])
def artifact_file(
    datasource: str | None = Query(default="malaria"),
    artifact_id: str | None = Query(default=None),
    path: str | None = Query(default=None),
    source: str = "training",
    attempt_id: str | None = None,
    training_run_id: str | None = None,
    repository: ArtifactReadRepository = Depends(),
) -> FileResponse:
    artifact = scientific_artifact(repository, datasource, artifact_id, source, attempt_id, training_run_id) if artifact_id else resolve_artifact_reference(
        datasource=datasource,
        artifact_id=artifact_id,
        path=path,
    )
    return FileResponse(
        artifact.path,
        media_type=artifact.media_type,
        filename=f"{artifact_id or 'artifact'}{artifact.path.suffix.lower()}",
        content_disposition_type="inline" if artifact.media_type.startswith("image/") else "attachment",
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store",
                 "Content-Security-Policy": "default-src 'none'; sandbox"},
    )
