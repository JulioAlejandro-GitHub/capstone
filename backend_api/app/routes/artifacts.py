from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from app.services.artifacts import resolve_artifact_path


router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/file")
def artifact_file(path: str = Query(...)):
    resolved = resolve_artifact_path(path)
    return FileResponse(resolved)

