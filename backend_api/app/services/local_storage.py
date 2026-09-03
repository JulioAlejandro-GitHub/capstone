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


SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
STAGING_NAMESPACES = frozenset({"uploads", "cell-detection", "cell-explanations"})
CLINICAL_NAMESPACES = frozenset(
    {"microscopy-images", "cell-crops", "cell-explanations"}
)


class StorageError(ValueError):
    pass


class UnsafeStorageKeyError(StorageError):
    pass


class StorageContentMissingError(StorageError):
    pass


class StorageFileTypeError(StorageError):
    pass


class StorageSizeMismatchError(StorageError):
    pass


class StorageChecksumMismatchError(StorageError):
    pass


class UploadTooLarge(StorageError):
    pass


@dataclass(frozen=True)
class StagedFile:
    path: Path
    sha256: str
    size: int


@dataclass(frozen=True)
class StagedUpload(StagedFile):
    original_filename: str


def sanitize_filename(value: str | None) -> str:
    if value is None:
        return "image"
    if "\x00" in value:
        raise StorageError("El filename contiene un byte nulo.")
    name = value.replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(
        char for char in name if ord(char) >= 32 and ord(char) != 127
    ).strip()
    name = re.sub(r"\s+", " ", name)
    return (name or "image")[:255]


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(path))


def verify_regular_file(
    path: Path,
    *,
    expected_size_bytes: int,
    expected_sha256: str,
) -> None:
    """Verify one already-confined regular file through a no-follow descriptor."""

    try:
        expected_size = int(expected_size_bytes)
    except (TypeError, ValueError, OverflowError) as exc:
        raise StorageSizeMismatchError(
            "El tamaño esperado del contenido es inválido."
        ) from exc
    if isinstance(expected_size_bytes, bool) or expected_size < 0:
        raise StorageSizeMismatchError("El tamaño esperado del contenido es inválido.")

    descriptor: int | None = None
    try:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise StorageFileTypeError("El contenido no es un archivo regular.")
        if before.st_size != expected_size:
            raise StorageSizeMismatchError(
                "El tamaño del contenido no coincide con su metadata."
            )
        expected_checksum = str(expected_sha256 or "").strip().lower()
        if SHA256_PATTERN.fullmatch(expected_checksum) is None:
            raise StorageChecksumMismatchError(
                "El checksum esperado del contenido es inválido."
            )
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        after = os.fstat(descriptor)
        if (
            before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
        ):
            raise StorageChecksumMismatchError(
                "El contenido cambió durante la verificación."
            )
        if digest.hexdigest() != expected_checksum:
            raise StorageChecksumMismatchError(
                "El checksum del contenido no coincide con su metadata."
            )
    except FileNotFoundError as exc:
        raise StorageContentMissingError(
            "El contenido solicitado no está disponible."
        ) from exc
    except OSError as exc:
        raise StorageFileTypeError(
            "El contenido no puede abrirse de forma segura."
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


class LocalStorage:
    """Canonical filesystem boundary for clinical content.

    Construction and resolution are read-only. Directory creation is limited to
    explicit staging and promotion operations.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        if str(self.settings.storage_provider).strip().lower() != "local":
            raise StorageError("El almacenamiento clínico requiere STORAGE_PROVIDER=local.")
        configured_root = Path(self.settings.storage_root)
        if not configured_root.is_absolute():
            raise StorageError("STORAGE_ROOT debe ser una ruta absoluta.")
        self.root = _lexical_absolute(configured_root)
        self.staging = self.root / ".staging"
        self._owned_paths: set[Path] = set()
        self._assert_existing_directory_chain(self.root, "STORAGE_ROOT")
        self._assert_existing_directory_chain(self.staging, "staging")

    @staticmethod
    def _assert_existing_directory_chain(path: Path, label: str) -> None:
        current = Path(path.anchor)
        for part in path.parts[1:]:
            current /= part
            try:
                info = current.lstat()
            except FileNotFoundError:
                break
            if stat.S_ISLNK(info.st_mode):
                raise UnsafeStorageKeyError(
                    f"No se permiten symlinks en {label} ni sus ancestros."
                )
            if not stat.S_ISDIR(info.st_mode):
                raise StorageFileTypeError(f"{label} atraviesa una ruta no directorio.")

    @staticmethod
    def _key_parts(storage_key: str) -> tuple[str, ...]:
        if not isinstance(storage_key, str) or not storage_key:
            raise UnsafeStorageKeyError("storage_key no puede estar vacío.")
        if "\x00" in storage_key:
            raise UnsafeStorageKeyError("storage_key contiene un byte nulo.")
        key = PurePosixPath(storage_key)
        if key.is_absolute() or not key.parts or ".." in key.parts:
            raise UnsafeStorageKeyError("storage_key debe ser una ruta POSIX relativa segura.")
        return key.parts

    def resolve(self, storage_key: str, *, must_exist: bool = False) -> Path:
        parts = self._key_parts(storage_key)
        self._assert_existing_directory_chain(self.root, "STORAGE_ROOT")
        candidate = _lexical_absolute(self.root.joinpath(*parts))
        if not candidate.is_relative_to(self.root):
            raise UnsafeStorageKeyError("storage_key escapa de STORAGE_ROOT.")

        current = self.root
        for index, part in enumerate(parts):
            current /= part
            try:
                info = current.lstat()
            except FileNotFoundError:
                break
            if stat.S_ISLNK(info.st_mode):
                raise UnsafeStorageKeyError("No se permiten symlinks en storage.")
            if index < len(parts) - 1 and not stat.S_ISDIR(info.st_mode):
                raise StorageFileTypeError(
                    "storage_key atraviesa un componente no directorio."
                )

        if must_exist:
            try:
                info = candidate.lstat()
            except FileNotFoundError as exc:
                raise StorageContentMissingError(
                    "El contenido solicitado no está disponible."
                ) from exc
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                raise StorageFileTypeError("El contenido no es un archivo regular.")
        return candidate

    def resolve_verified(
        self,
        storage_key: str,
        *,
        expected_size_bytes: int,
        expected_sha256: str,
    ) -> Path:
        path = self.resolve(storage_key, must_exist=True)
        verify_regular_file(
            path,
            expected_size_bytes=expected_size_bytes,
            expected_sha256=expected_sha256,
        )
        return path

    @staticmethod
    def build_key(
        subject_id: UUID,
        sample_id: UUID,
        slide_id: UUID,
        image_id: UUID,
        sha256: str,
        extension: str,
    ) -> str:
        return (
            f"microscopy-images/{subject_id}/{sample_id}/{slide_id}/"
            f"{image_id}/{sha256}.{extension}"
        )

    def _ensure_directory(self, directory: Path) -> Path:
        target = _lexical_absolute(directory)
        if target != self.root and not target.is_relative_to(self.root):
            raise UnsafeStorageKeyError("El directorio solicitado escapa de STORAGE_ROOT.")
        current = Path(target.anchor)
        for part in target.parts[1:]:
            current /= part
            try:
                info = current.lstat()
            except FileNotFoundError:
                try:
                    current.mkdir(mode=0o700)
                except FileExistsError:
                    pass
                info = current.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise UnsafeStorageKeyError(
                    "No se permiten symlinks al preparar storage."
                )
            if not stat.S_ISDIR(info.st_mode):
                raise StorageFileTypeError(
                    "Storage atraviesa un componente no directorio."
                )
        return target

    def ensure_writable_layout(self) -> None:
        self._ensure_directory(self.root)
        self._ensure_directory(self.staging)

    def ensure_writable_directory(self, storage_key: str) -> Path:
        self.ensure_writable_layout()
        directory = self.resolve(storage_key)
        return self._ensure_directory(directory)

    def create_staging_directory(self, namespace: str) -> Path:
        if namespace not in STAGING_NAMESPACES:
            raise UnsafeStorageKeyError("Namespace de staging no autorizado.")
        parent = self.ensure_writable_directory(f".staging/{namespace}")
        for _ in range(10):
            directory = parent / uuid4().hex
            try:
                directory.mkdir(mode=0o700)
            except FileExistsError:
                continue
            self._owned_paths.add(directory)
            return directory
        raise StorageError("No fue posible reservar staging exclusivo.")

    def _new_staging_path(
        self,
        namespace: str,
        suffix: str,
        *,
        directory: Path | None = None,
    ) -> Path:
        if namespace not in STAGING_NAMESPACES:
            raise UnsafeStorageKeyError("Namespace de staging no autorizado.")
        if "/" in suffix or "\\" in suffix or "\x00" in suffix:
            raise UnsafeStorageKeyError("Sufijo de staging inválido.")
        parent = directory or self.ensure_writable_directory(f".staging/{namespace}")
        parent = _lexical_absolute(parent)
        namespace_root = self.staging / namespace
        if parent != namespace_root and (
            not parent.is_relative_to(namespace_root) or parent not in self._owned_paths
        ):
            raise UnsafeStorageKeyError("Directorio de staging no autorizado.")
        self._assert_existing_directory_chain(parent, "staging")
        return parent / f"{uuid4().hex}{suffix}"

    async def stage(self, upload: UploadFile) -> StagedUpload:
        filename = sanitize_filename(upload.filename)
        path = self._new_staging_path("uploads", ".upload")
        digest = hashlib.sha256()
        size = 0
        self._owned_paths.add(path)
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
            self.cleanup([path], boundaries=(self.staging / "uploads",))
            raise
        finally:
            await upload.close()

    def stage_bytes(
        self,
        payload: bytes,
        *,
        namespace: str,
        suffix: str,
        directory: Path | None = None,
    ) -> StagedFile:
        if not payload:
            raise StorageError("El contenido staged está vacío.")
        path = self._new_staging_path(namespace, suffix, directory=directory)
        digest = hashlib.sha256()
        self._owned_paths.add(path)
        try:
            with path.open("xb") as output:
                os.chmod(path, 0o600)
                digest.update(payload)
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            return StagedFile(path, digest.hexdigest(), len(payload))
        except Exception:
            self.cleanup([path], boundaries=(self.staging / namespace,))
            raise

    def promote(
        self,
        staged: Path,
        storage_key: str,
        *,
        expected_size_bytes: int | None = None,
        expected_sha256: str | None = None,
    ) -> Path:
        staged_path = _lexical_absolute(staged)
        if staged_path not in self._owned_paths or not staged_path.is_relative_to(
            self.staging
        ):
            raise UnsafeStorageKeyError(
                "Sólo se pueden promover archivos creados por esta operación."
            )
        staged_key = staged_path.relative_to(self.root).as_posix()
        if expected_size_bytes is None or expected_sha256 is None:
            raise StorageError("La promoción requiere tamaño y checksum esperados.")
        self.resolve_verified(
            staged_key,
            expected_size_bytes=expected_size_bytes,
            expected_sha256=expected_sha256,
        )

        destination_parts = self._key_parts(storage_key)
        if destination_parts[0] not in CLINICAL_NAMESPACES:
            raise UnsafeStorageKeyError("Namespace clínico de destino no autorizado.")
        key = PurePosixPath(*destination_parts)
        parent_key = key.parent.as_posix()
        if parent_key == ".":
            self.ensure_writable_layout()
        else:
            self.ensure_writable_directory(parent_key)
        destination = self.resolve(storage_key)
        try:
            destination.lstat()
        except FileNotFoundError:
            pass
        else:
            raise StorageError("El destino ya existe; no se sobrescribe.")

        try:
            os.chmod(staged_path, 0o600)
            os.link(staged_path, destination, follow_symlinks=False)
        except FileExistsError as exc:
            raise StorageError("El destino ya existe; no se sobrescribe.") from exc
        except OSError as exc:
            raise StorageError("No fue posible promover el contenido staged.") from exc
        self._owned_paths.add(destination)
        try:
            staged_path.unlink()
        except OSError:
            destination.unlink(missing_ok=True)
            self._owned_paths.discard(destination)
            raise
        self._owned_paths.discard(staged_path)
        return destination

    def cleanup(
        self,
        paths: list[Path] | tuple[Path, ...],
        *,
        boundaries: tuple[Path, ...],
    ) -> None:
        safe_boundaries = tuple(_lexical_absolute(boundary) for boundary in boundaries)
        if any(
            boundary == self.root or not boundary.is_relative_to(self.root)
            for boundary in safe_boundaries
        ):
            raise UnsafeStorageKeyError(
                "Cleanup requiere boundaries internos y distintos de STORAGE_ROOT."
            )
        for original in paths:
            path = _lexical_absolute(original)
            boundary = next(
                (
                    candidate
                    for candidate in sorted(
                        safe_boundaries, key=lambda item: len(item.parts), reverse=True
                    )
                    if path != candidate and path.is_relative_to(candidate)
                ),
                None,
            )
            if boundary is None or path not in self._owned_paths:
                continue
            try:
                info = path.lstat()
                if stat.S_ISLNK(info.st_mode) or stat.S_ISREG(info.st_mode):
                    path.unlink()
                elif stat.S_ISDIR(info.st_mode):
                    path.rmdir()
                else:
                    continue
                self._owned_paths.discard(path)
                parent = path.parent
                while parent != boundary and parent.is_relative_to(boundary):
                    try:
                        parent.rmdir()
                    except OSError:
                        break
                    self._owned_paths.discard(parent)
                    parent = parent.parent
            except (FileNotFoundError, OSError):
                continue
