from __future__ import annotations

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
    """PNG validation and key policy over the canonical clinical storage."""

    def __init__(self, local_storage: LocalStorage | None = None):
        self.local = local_storage or LocalStorage()
        self.root = self.local.root
        self.staging_root = self.local.staging / "cell-detection"
        self.crop_root = self.root / "cell-crops"

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

    @staticmethod
    def _validate_png(
        path: Path,
        *,
        expected_width_px: int,
        expected_height_px: int,
    ) -> None:
        try:
            with Image.open(path) as image:
                if image.format != "PNG":
                    raise StorageError("El crop derivado no es PNG.")
                if image.size != (expected_width_px, expected_height_px):
                    raise StorageError("Las dimensiones del crop no coinciden.")
                image.verify()
        except (UnidentifiedImageError, OSError, SyntaxError) as exc:
            raise StorageError("El crop derivado es inválido.") from exc

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
        staged_file = self.local.stage_bytes(
            png_bytes,
            namespace="cell-detection",
            suffix=".crop.png",
        )
        try:
            self._validate_png(
                staged_file.path,
                expected_width_px=expected_width_px,
                expected_height_px=expected_height_px,
            )
            key = self.build_key(
                analysis_run_id,
                detection_run_id,
                microscopy_image_id,
                cell_detection_id,
            )
            return StagedCellCrop(
                path=staged_file.path,
                relative_storage_key=key,
                sha256=staged_file.sha256,
                file_size_bytes=staged_file.size,
                width_px=expected_width_px,
                height_px=expected_height_px,
                format="PNG",
                padding_px=padding_px,
            )
        except Exception:
            self.cleanup([staged_file.path])
            raise

    def promote(self, staged: StagedCellCrop) -> Path:
        staged_key = staged.path.relative_to(self.root).as_posix()
        verified = self.local.resolve_verified(
            staged_key,
            expected_size_bytes=staged.file_size_bytes,
            expected_sha256=staged.sha256,
        )
        self._validate_png(
            verified,
            expected_width_px=staged.width_px,
            expected_height_px=staged.height_px,
        )
        return self.local.promote(
            staged.path,
            staged.relative_storage_key,
            expected_size_bytes=staged.file_size_bytes,
            expected_sha256=staged.sha256,
        )

    def resolve(self, relative_storage_key: str, *, must_exist: bool = True) -> Path:
        return self.local.resolve(relative_storage_key, must_exist=must_exist)

    def resolve_verified(
        self,
        relative_storage_key: str,
        *,
        expected_size_bytes: int,
        expected_sha256: str,
    ) -> Path:
        return self.local.resolve_verified(
            relative_storage_key,
            expected_size_bytes=expected_size_bytes,
            expected_sha256=expected_sha256,
        )

    def cleanup(self, paths: list[Path] | tuple[Path, ...]) -> None:
        self.local.cleanup(
            paths,
            boundaries=(self.staging_root, self.crop_root),
        )
