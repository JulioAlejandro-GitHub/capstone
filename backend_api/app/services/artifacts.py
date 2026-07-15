from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException

from app.db import fetch_one


CAPSTONE_ROOT = Path(__file__).resolve().parents[3]
MALARIA_PROJECT_ROOT = CAPSTONE_ROOT / "malaria_dl_local_project"
ALLOWED_ARTIFACT_ROOTS = (
    (MALARIA_PROJECT_ROOT / "outputs").resolve(),
    (MALARIA_PROJECT_ROOT / "data").resolve(),
    (CAPSTONE_ROOT / "data").resolve(),
    (CAPSTONE_ROOT / "data" / "prediction_uploads").resolve(),
)

IMAGE_MIME_BY_EXTENSION = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
ALLOWED_EXTENSIONS = frozenset(IMAGE_MIME_BY_EXTENSION)


@dataclass(frozen=True)
class ServedArtifact:
    path: Path
    media_type: str


def resolve_artifact_path(path: str) -> Path:
    if not path:
        raise HTTPException(status_code=400, detail="Parametro path requerido.")

    try:
        raw_path = Path(path)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Parametro path invalido.") from exc

    candidates: list[Path] = []
    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        candidates.append(CAPSTONE_ROOT / raw_path)
        if raw_path.parts and raw_path.parts[0] in {"outputs", "data"}:
            candidates.append(MALARIA_PROJECT_ROOT / raw_path)

    try:
        resolved_candidates = [candidate.resolve(strict=False) for candidate in candidates]
    except (OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Parametro path invalido.") from exc

    allowed_candidates = [
        candidate
        for candidate in resolved_candidates
        if any(candidate == root or root in candidate.parents for root in ALLOWED_ARTIFACT_ROOTS)
    ]

    # A relative reference such as ``data/foo.png`` can exist in either the
    # capstone data directory or the nested malaria project. Prefer the first
    # existing allowed match, while never falling back to a disallowed path.
    resolved = next((candidate for candidate in allowed_candidates if candidate.exists()), None)
    if resolved is None and allowed_candidates:
        resolved = allowed_candidates[0]

    if resolved is None:
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

    media_type = detect_image_mime(path)
    expected_media_type = IMAGE_MIME_BY_EXTENSION[suffix]
    if media_type != expected_media_type:
        raise HTTPException(status_code=415, detail="MIME real no coincide con la extension.")
    return ServedArtifact(path=path, media_type=media_type)


def detect_image_mime(path: Path) -> str:
    with path.open("rb") as file:
        header = file.read(16)
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "image/webp"
    raise HTTPException(status_code=415, detail="MIME real de imagen no permitido.")
