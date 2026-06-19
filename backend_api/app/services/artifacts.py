import json
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException

from app.db import fetch_one


CAPSTONE_ROOT = Path(__file__).resolve().parents[3]
MALARIA_PROJECT_ROOT = CAPSTONE_ROOT / "malaria_dl_local_project"
ALLOWED_ARTIFACT_ROOTS = [
    (MALARIA_PROJECT_ROOT / "outputs").resolve(),
    (CAPSTONE_ROOT / "data").resolve(),
]

IMAGE_MIME_BY_EXTENSION = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}
TEXT_MIME_BY_EXTENSION = {
    ".csv": "text/csv",
    ".json": "application/json",
    ".txt": "text/plain",
    ".log": "text/plain",
    ".md": "text/markdown",
}
ALLOWED_EXTENSIONS = set(IMAGE_MIME_BY_EXTENSION) | set(TEXT_MIME_BY_EXTENSION)
TEXT_SAMPLE_BYTES = 8192


@dataclass(frozen=True)
class ServedArtifact:
    path: Path
    media_type: str


def resolve_artifact_path(path: str) -> Path:
    if not path:
        raise HTTPException(status_code=400, detail="Parametro path requerido.")

    raw_path = Path(path)
    candidates = []
    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        candidates.append(CAPSTONE_ROOT / raw_path)
        if raw_path.parts and raw_path.parts[0] == "outputs":
            candidates.append(MALARIA_PROJECT_ROOT / raw_path)

    resolved = next((candidate.resolve() for candidate in candidates if candidate.exists()), None)
    if resolved is None:
        resolved = candidates[0].resolve()

    if not any(resolved == root or root in resolved.parents for root in ALLOWED_ARTIFACT_ROOTS):
        raise HTTPException(status_code=403, detail="Artefacto fuera de la carpeta permitida.")
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="Artefacto no encontrado.")
    return resolved


def resolve_artifact_by_id(datasource: str | None, artifact_id: str) -> Path:
    try:
        parsed_artifact_id = UUID(artifact_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="artifact_id invalido.") from exc

    row = fetch_one(
        datasource,
        """
        SELECT id, path
        FROM artifacts
        WHERE id = CAST(:artifact_id AS uuid)
        """,
        {"artifact_id": str(parsed_artifact_id)},
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Artefacto no encontrado.")
    return resolve_artifact_path(row["path"])


def resolve_artifact_reference(
    datasource: str | None = None,
    artifact_id: str | None = None,
    path: str | None = None,
) -> ServedArtifact:
    if artifact_id:
        resolved = resolve_artifact_by_id(datasource, artifact_id)
    elif path:
        resolved = resolve_artifact_path(path)
    else:
        raise HTTPException(status_code=400, detail="Parametro artifact_id o path requerido.")

    return validate_served_artifact(resolved)


def validate_served_artifact(path: Path) -> ServedArtifact:
    suffix = path.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=403,
            detail=f"Extension no permitida para artefactos: {suffix or 'sin extension'}.",
        )

    if suffix in IMAGE_MIME_BY_EXTENSION:
        media_type = detect_image_mime(path)
        expected_media_type = IMAGE_MIME_BY_EXTENSION[suffix]
        if media_type != expected_media_type:
            raise HTTPException(status_code=415, detail="MIME real no coincide con la extension.")
        return ServedArtifact(path=path, media_type=media_type)

    media_type = detect_text_mime(path, suffix)
    return ServedArtifact(path=path, media_type=media_type)


def detect_image_mime(path: Path) -> str:
    with path.open("rb") as file:
        header = file.read(16)
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "image/webp"
    if header.startswith(b"BM"):
        return "image/bmp"
    if header.startswith((b"II*\x00", b"MM\x00*")):
        return "image/tiff"
    raise HTTPException(status_code=415, detail="MIME real de imagen no permitido.")


def detect_text_mime(path: Path, suffix: str) -> str:
    if suffix == ".json":
        try:
            with path.open("r", encoding="utf-8") as file:
                json.load(file)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=415, detail="JSON invalido o no UTF-8.") from exc
        return "application/json"

    try:
        with path.open("rb") as file:
            sample = file.read(TEXT_SAMPLE_BYTES)
        sample.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=415, detail="Artefacto de texto no UTF-8.") from exc

    if b"\x00" in sample:
        raise HTTPException(status_code=415, detail="Artefacto de texto invalido.")

    return TEXT_MIME_BY_EXTENSION[suffix]
