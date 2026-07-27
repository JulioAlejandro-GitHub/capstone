from __future__ import annotations

import hashlib
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.config import Settings, get_settings


class StorageError(ValueError):
    pass


class UploadTooLarge(StorageError):
    pass


@dataclass(frozen=True)
class StagedUpload:
    path: Path
    sha256: str
    size: int
    original_filename: str


def sanitize_filename(value: str | None) -> str:
    if value is None:
        return "image"
    if "\x00" in value:
        raise StorageError("El filename contiene un byte nulo.")
    name = value.replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(char for char in name if ord(char) >= 32 and ord(char) != 127).strip()
    name = re.sub(r"\s+", " ", name)
    return (name or "image")[:255]


class LocalStorage:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        if self.settings.storage_provider != "local":
            raise StorageError("Prompt 4 solo admite STORAGE_PROVIDER=local.")
        self.root = self.settings.storage_root.resolve()
        self.staging = self.root / ".staging"
        self.staging.mkdir(parents=True, exist_ok=True, mode=0o700)

    def resolve(self, storage_key: str, *, must_exist: bool = False) -> Path:
        if "\x00" in storage_key:
            raise StorageError("storage_key inválido.")
        key = PurePosixPath(storage_key)
        if key.is_absolute() or ".." in key.parts or not key.parts:
            raise StorageError("storage_key debe ser relativo y seguro.")
        candidate = self.root.joinpath(*key.parts)
        current = self.root
        for part in key.parts:
            current = current / part
            if current.is_symlink():
                raise StorageError("No se permiten symlinks en storage.")
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(self.root):
            raise StorageError("storage_key escapa de STORAGE_ROOT.")
        if must_exist:
            info = resolved.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                raise StorageError("El contenido no es un archivo regular.")
        return resolved

    async def stage(self, upload: UploadFile) -> StagedUpload:
        filename = sanitize_filename(upload.filename)
        path = self.staging / f"{uuid4()}.upload"
        digest = hashlib.sha256()
        size = 0
        try:
            with path.open("xb") as output:
                os.chmod(path, 0o600)
                while chunk := await upload.read(self.settings.upload_chunk_size_bytes):
                    size += len(chunk)
                    if size > self.settings.max_upload_size_bytes:
                        raise UploadTooLarge("El archivo excede MAX_UPLOAD_SIZE_BYTES.")
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            if size == 0:
                raise StorageError("El archivo está vacío.")
            return StagedUpload(path, digest.hexdigest(), size, filename)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

    @staticmethod
    def build_key(
        subject_id: UUID, sample_id: UUID, slide_id: UUID, image_id: UUID,
        sha256: str, extension: str,
    ) -> str:
        return (
            f"microscopy-images/{subject_id}/{sample_id}/{slide_id}/"
            f"{image_id}/{sha256}.{extension}"
        )

    def promote(self, staged: Path, storage_key: str) -> Path:
        destination = self.resolve(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if destination.exists():
            raise StorageError("El original ya existe; no se sobrescribe.")
        os.replace(staged, destination)
        os.chmod(destination, 0o600)
        return destination

    @staticmethod
    def cleanup(paths: list[Path]) -> None:
        for path in paths:
            try:
                if path.is_file() and not path.is_symlink():
                    path.unlink()
                parent = path.parent
                while parent.name and parent.exists():
                    try:
                        parent.rmdir()
                    except OSError:
                        break
                    parent = parent.parent
            except OSError:
                pass
