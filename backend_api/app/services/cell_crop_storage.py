from __future__ import annotations

import hashlib
import io
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from PIL import Image, UnidentifiedImageError

from app.services.local_storage import LocalStorage, StorageError


@dataclass(frozen=True)
class StagedCellCrop:
    path: Path
    relative_storage_key: str
    sha256: str
    file_size_bytes: int
    width_px: int
    height_px: int
    format: str
    padding_px: int


class CellCropStorage:
    """Confinement, validation, staging, and atomic promotion for derived crops."""

    def __init__(self, local_storage: LocalStorage | None = None):
        self.local = local_storage or LocalStorage()
        self.root = self.local.root
        if self.local.staging.is_symlink():
            raise StorageError("No se permiten symlinks en el padre de staging.")
        self.staging_root = self.local.staging / "cell-detection"
        if self.staging_root.is_symlink():
            raise StorageError("No se permiten symlinks en staging de crops.")
        self.staging_root.mkdir(parents=True, exist_ok=True, mode=0o700)

    @staticmethod
    def build_key(
        analysis_run_id: UUID,
        detection_run_id: UUID,
        microscopy_image_id: UUID,
        cell_detection_id: UUID,
    ) -> str:
        return (
            f"cell-crops/{analysis_run_id}/{detection_run_id}/"
            f"{microscopy_image_id}/{cell_detection_id}/crop.png"
        )

    def _staging_path(
        self,
        detection_run_id: UUID,
        microscopy_image_id: UUID,
        cell_detection_id: UUID,
    ) -> Path:
        path = (
            self.staging_root
            / str(detection_run_id)
            / str(microscopy_image_id)
            / str(cell_detection_id)
            / "crop.png"
        )
        if not path.resolve(strict=False).is_relative_to(self.staging_root.resolve()):
            raise StorageError("El staging de crop escapa de su raíz.")
        return path

    def stage(
        self,
        *,
        analysis_run_id: UUID,
        detection_run_id: UUID,
        microscopy_image_id: UUID,
        cell_detection_id: UUID,
        png_bytes: bytes,
        expected_width_px: int,
        expected_height_px: int,
        padding_px: int,
    ) -> StagedCellCrop:
        if not png_bytes:
            raise StorageError("El crop derivado está vacío.")
        path = self._staging_path(
            detection_run_id, microscopy_image_id, cell_detection_id
        )
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        current = self.staging_root
        for part in path.relative_to(self.staging_root).parts[:-1]:
            current = current / part
            if current.is_symlink():
                raise StorageError("No se permiten symlinks en staging de crops.")
        try:
            with path.open("xb") as output:
                os.chmod(path, 0o600)
                output.write(png_bytes)
                output.flush()
                os.fsync(output.fileno())
            digest = hashlib.sha256(png_bytes).hexdigest()
            try:
                with Image.open(io.BytesIO(png_bytes)) as image:
                    image.verify()
                with Image.open(path) as image:
                    if image.format != "PNG":
                        raise StorageError("El crop derivado no es PNG.")
                    if image.size != (expected_width_px, expected_height_px):
                        raise StorageError("Las dimensiones del crop no coinciden.")
                    image.load()
            except (UnidentifiedImageError, OSError, SyntaxError) as exc:
                raise StorageError("El crop derivado es inválido.") from exc
            if path.stat().st_size != len(png_bytes):
                raise StorageError("El tamaño del crop staged no coincide.")
            key = self.build_key(
                analysis_run_id,
                detection_run_id,
                microscopy_image_id,
                cell_detection_id,
            )
            return StagedCellCrop(
                path=path,
                relative_storage_key=key,
                sha256=digest,
                file_size_bytes=len(png_bytes),
                width_px=expected_width_px,
                height_px=expected_height_px,
                format="PNG",
                padding_px=padding_px,
            )
        except Exception:
            self.cleanup([path])
            raise

    def promote(self, staged: StagedCellCrop) -> Path:
        try:
            staged_info = staged.path.lstat()
        except FileNotFoundError as exc:
            raise StorageError("El crop staged no está disponible.") from exc
        if stat.S_ISLNK(staged_info.st_mode) or not stat.S_ISREG(staged_info.st_mode):
            raise StorageError("El crop staged no es un archivo regular.")
        if staged_info.st_size != staged.file_size_bytes:
            raise StorageError("El tamaño del crop staged cambió.")
        digest = hashlib.sha256()
        with staged.path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
        if digest.hexdigest() != staged.sha256:
            raise StorageError("El checksum del crop staged cambió.")
        try:
            with Image.open(staged.path) as image:
                if image.format != staged.format:
                    raise StorageError("El formato del crop staged cambió.")
                if image.size != (staged.width_px, staged.height_px):
                    raise StorageError("Las dimensiones del crop staged cambiaron.")
                image.verify()
        except (UnidentifiedImageError, OSError, SyntaxError) as exc:
            raise StorageError("El crop staged ya no es válido.") from exc
        destination = self.local.resolve(staged.relative_storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Resolve again after mkdir so any unexpected symlink is observed.
        destination = self.local.resolve(staged.relative_storage_key)
        if destination.exists():
            raise StorageError("El crop derivado ya existe; no se sobrescribe.")
        os.replace(staged.path, destination)
        os.chmod(destination, 0o600)
        return destination

    def resolve(self, relative_storage_key: str, *, must_exist: bool = True) -> Path:
        return self.local.resolve(relative_storage_key, must_exist=must_exist)

    def cleanup(self, paths: list[Path]) -> None:
        staging_root = Path(os.path.abspath(self.staging_root))
        crop_root = Path(os.path.abspath(self.root / "cell-crops"))
        for original in paths:
            try:
                # Absolute lexical confinement deliberately avoids following a
                # symlink that an attacker may have substituted after staging.
                path = Path(os.path.abspath(original))
                if not (path.is_relative_to(staging_root) or path.is_relative_to(crop_root)):
                    continue
                info = path.lstat()
                if stat.S_ISLNK(info.st_mode) or stat.S_ISREG(info.st_mode):
                    path.unlink()
                parent = path.parent
                boundary = staging_root if path.is_relative_to(staging_root) else crop_root
                while parent != boundary and parent.is_relative_to(boundary):
                    try:
                        parent.rmdir()
                    except OSError:
                        break
                    parent = parent.parent
            except (FileNotFoundError, OSError):
                continue
