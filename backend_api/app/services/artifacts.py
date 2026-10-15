import os
from dataclasses import dataclass, replace
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException

from app.config import get_settings
from app.repositories.artifacts import ArtifactReadRepository
from app.services.local_storage import (LocalStorage, StorageError, StorageContentMissingError,
    StorageChecksumMismatchError, StorageSizeMismatchError, verify_regular_file)


_SOURCE_CAPSTONE_ROOT = Path(__file__).resolve().parents[3]
_CONFIGURED_ML_ROOT = os.getenv("MALARIA_DL_PROJECT_ROOT", "").strip()
MALARIA_PROJECT_ROOT = (
    Path(_CONFIGURED_ML_ROOT).expanduser().resolve()
    if _CONFIGURED_ML_ROOT
    else (_SOURCE_CAPSTONE_ROOT / "malaria_dl_local_project").resolve()
)
CAPSTONE_ROOT = (
    MALARIA_PROJECT_ROOT.parent
    if _CONFIGURED_ML_ROOT
    else _SOURCE_CAPSTONE_ROOT
)
_CONFIGURED_ARTIFACTS_ROOT = os.getenv("ARTIFACTS_ROOT", "./var/artifacts").strip()
_RAW_ARTIFACTS_ROOT = Path(_CONFIGURED_ARTIFACTS_ROOT).expanduser()
ARTIFACTS_ROOT = (
    _RAW_ARTIFACTS_ROOT.resolve()
    if _RAW_ARTIFACTS_ROOT.is_absolute()
    else (CAPSTONE_ROOT / _RAW_ARTIFACTS_ROOT).resolve()
)
ALLOWED_ARTIFACT_ROOTS = (
    (MALARIA_PROJECT_ROOT / "outputs").resolve(),
    (MALARIA_PROJECT_ROOT / "data").resolve(),
    (CAPSTONE_ROOT / "data").resolve(),
    (CAPSTONE_ROOT / "data" / "prediction_uploads").resolve(),
    ARTIFACTS_ROOT,
    # Read-only compatibility for references persisted before Storage B.2B.1.
    (CAPSTONE_ROOT / "var" / "storage" / "model-explanations").resolve(),
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
        # Historical rows can contain an absolute path from another checkout
        # (for example the host path while the API runs from /app). Rebase only
        # known project-owned suffixes; the allowed-root check below remains the
        # final authority and prevents arbitrary absolute-path traversal.
        parts = raw_path.parts
        if "malaria_dl_local_project" in parts:
            marker = parts.index("malaria_dl_local_project")
            candidates.append(MALARIA_PROJECT_ROOT.joinpath(*parts[marker + 1 :]))
        elif "var" in parts:
            marker = parts.index("var")
            if len(parts) > marker + 1 and parts[marker + 1] == "storage":
                candidates.append(CAPSTONE_ROOT.joinpath(*parts[marker:]))
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


def artifact_error(status: int, code: str) -> HTTPException:
    return HTTPException(status, detail={"code": code})


def scientific_artifact(
    repository: ArtifactReadRepository, datasource: str | None, artifact_id: str,
    source: str = "training", attempt_id: str | None = None,
    training_run_id: str | None = None,
) -> ServedArtifact:
    if source not in {"training", "assessment"}:
        raise artifact_error(400, "ARTIFACT_SOURCE_INVALID")
    try:
        artifact_id = str(UUID(artifact_id))
        attempt_id = str(UUID(attempt_id)) if attempt_id else None
        training_run_id = str(UUID(training_run_id)) if training_run_id else None
    except ValueError as exc:
        raise artifact_error(400, "ARTIFACT_ID_INVALID") from exc
    row = repository.get(datasource, artifact_id, source)
    if row is None:
        raise artifact_error(404, "ARTIFACT_NOT_REGISTERED")
    if (attempt_id and str(row.get("attempt_id")) != attempt_id) or (
        training_run_id and str(row["training_run_id"]) != training_run_id
    ):
        raise artifact_error(404, "ARTIFACT_RELATION_MISMATCH")
    try:
        if source == "assessment":
            payload = row["payload"]
            attempt = str(row["attempt_id"])
            raw = Path(payload["path"])
            registered_root = Path(row["artifact_root"])
            # Only the registered attempt subtree is translated; no host prefix mapping.
            if ".." in raw.parts or ".." in registered_root.parts:
                raise artifact_error(409, "ARTIFACT_LOCATION_INVALID")
            relative = raw.relative_to(registered_root)
            if registered_root.parts[-3:] != ("artifacts", "assessments", attempt):
                raise artifact_error(409, "ARTIFACT_LOCATION_INVALID")
            if str(payload.get("artifact_id")) != artifact_id or relative.stem != artifact_id:
                raise artifact_error(409, "ARTIFACT_RELATION_MISMATCH")
            if str(payload.get("sample_id")) != str(row["sample_id"]):
                raise artifact_error(409, "ARTIFACT_RELATION_MISMATCH")
            root = MALARIA_PROJECT_ROOT / "artifacts" / "assessments"
            storage = LocalStorage(replace(get_settings(), storage_root=root))
            key = f"{attempt}/{relative.as_posix()}"
            checksum, size = payload.get("sha256"), payload.get("bytes")
            resolved = storage.resolve(key, must_exist=True)
        else:
            checksum, size = row.get("checksum"), row.get("file_size_bytes")
            try:
                resolved = resolve_artifact_path(row["path"])
            except HTTPException as exc:
                if exc.status_code == 404:
                    raise artifact_error(410, "ARTIFACT_CONTENT_MISSING") from exc
                raise artifact_error(409, "ARTIFACT_LOCATION_INVALID") from exc
        if checksum:
            verify_regular_file(resolved, expected_size_bytes=size if size is not None else resolved.stat().st_size,
                                expected_sha256=checksum)
        suffix = resolved.suffix.lower()
        downloads = {".npy": "application/octet-stream", ".json": "application/json", ".csv": "text/csv"}
        if suffix in downloads:
            if suffix == ".npy":
                with resolved.open("rb") as stream:
                    if stream.read(6) != b"\x93NUMPY":
                        raise artifact_error(415, "ARTIFACT_MEDIA_INVALID")
            return ServedArtifact(resolved, downloads[suffix])
        if suffix not in ALLOWED_EXTENSIONS:
            raise artifact_error(415, "ARTIFACT_MEDIA_INVALID")
        return validate_served_artifact(resolved)
    except StorageContentMissingError as exc:
        raise artifact_error(410, "ARTIFACT_CONTENT_MISSING") from exc
    except (StorageChecksumMismatchError, StorageSizeMismatchError) as exc:
        raise artifact_error(409, "ARTIFACT_INTEGRITY_FAILED") from exc
    except (StorageError, ValueError, KeyError) as exc:
        raise artifact_error(409, "ARTIFACT_LOCATION_INVALID") from exc
    except OSError as exc:
        raise artifact_error(503, "ARTIFACT_STORAGE_UNAVAILABLE") from exc


def resolve_artifact_reference(
    datasource: str | None = None,
    artifact_id: str | None = None,
    path: str | None = None,
) -> ServedArtifact:
    if artifact_id:
        return scientific_artifact(ArtifactReadRepository(), datasource, artifact_id)
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
