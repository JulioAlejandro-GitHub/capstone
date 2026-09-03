from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from PIL import Image, UnidentifiedImageError

from app.services.local_storage import LocalStorage, StorageError


@dataclass(frozen=True)
class StagedExplanationArtifact:
    path: Path
    relative_storage_key: str
    sha256: str
    file_size_bytes: int
    width_px: int
    height_px: int
    format: str = "PNG"


@dataclass(frozen=True)
class StagedCellExplanation:
    heatmap: StagedExplanationArtifact
    overlay: StagedExplanationArtifact


class CellExplanationStorage:
    """Clinical Grad-CAM artifacts over the canonical storage boundary."""

    def __init__(self, local_storage: LocalStorage | None = None):
        self.local = local_storage or LocalStorage()
        self.root = self.local.root
        self.staging_root = self.local.staging / "cell-explanations"
        self.explanation_root = self.root / "cell-explanations"

    @staticmethod
    def build_keys(
        analysis_run_id: UUID,
        classification_run_id: UUID,
        cell_detection_id: UUID,
    ) -> tuple[str, str]:
        base = (
            f"cell-explanations/{analysis_run_id}/"
            f"{classification_run_id}/{cell_detection_id}"
        )
        return f"{base}/gradcam_heatmap.png", f"{base}/gradcam_overlay.png"

    @staticmethod
    def encode_heatmap_png(heatmap: Any) -> bytes:
        import numpy as np

        values = np.asarray(heatmap, dtype=np.float32)
        if values.ndim != 2 or not np.isfinite(values).all():
            raise StorageError("El heatmap Grad-CAM no es una matriz finita.")
        values = np.clip(values, 0.0, 1.0)
        output = io.BytesIO()
        Image.fromarray(
            np.rint(values * 255.0).astype(np.uint8), mode="L"
        ).save(output, format="PNG")
        return output.getvalue()

    @staticmethod
    def encode_overlay_png(overlay: Any) -> bytes:
        import numpy as np

        values = np.asarray(overlay, dtype=np.float32)
        if (
            values.ndim != 3
            or values.shape[-1] != 3
            or not np.isfinite(values).all()
        ):
            raise StorageError("El overlay Grad-CAM no es una imagen RGB finita.")
        values = np.clip(values, 0.0, 1.0)
        output = io.BytesIO()
        Image.fromarray(
            np.rint(values * 255.0).astype(np.uint8), mode="RGB"
        ).save(output, format="PNG")
        return output.getvalue()

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
                    raise StorageError("El artefacto Grad-CAM no es PNG.")
                if image.size != (expected_width_px, expected_height_px):
                    raise StorageError(
                        "Las dimensiones del artefacto Grad-CAM no coinciden."
                    )
                image.verify()
        except (UnidentifiedImageError, OSError, SyntaxError) as exc:
            raise StorageError("El artefacto Grad-CAM no es un PNG válido.") from exc

    def _stage_one(
        self,
        *,
        directory: Path,
        key: str,
        payload: bytes,
        suffix: str,
        expected_width_px: int,
        expected_height_px: int,
    ) -> StagedExplanationArtifact:
        staged = self.local.stage_bytes(
            payload,
            namespace="cell-explanations",
            suffix=suffix,
            directory=directory,
        )
        try:
            self._validate_png(
                staged.path,
                expected_width_px=expected_width_px,
                expected_height_px=expected_height_px,
            )
            return StagedExplanationArtifact(
                path=staged.path,
                relative_storage_key=key,
                sha256=staged.sha256,
                file_size_bytes=staged.size,
                width_px=expected_width_px,
                height_px=expected_height_px,
            )
        except Exception:
            self.cleanup([staged.path])
            raise

    def stage(
        self,
        *,
        analysis_run_id: UUID,
        classification_run_id: UUID,
        cell_detection_id: UUID,
        explanation_id: UUID,
        heatmap_png: bytes,
        overlay_png: bytes,
        expected_width_px: int,
        expected_height_px: int,
    ) -> StagedCellExplanation:
        del explanation_id  # the final immutable key remains tied to the cell
        if expected_width_px < 1 or expected_height_px < 1:
            raise StorageError("Las dimensiones de explicación deben ser positivas.")
        directory = self.local.create_staging_directory("cell-explanations")
        heatmap_key, overlay_key = self.build_keys(
            analysis_run_id, classification_run_id, cell_detection_id
        )
        staged: list[Path] = []
        try:
            heatmap = self._stage_one(
                directory=directory,
                key=heatmap_key,
                payload=heatmap_png,
                suffix=".heatmap.png",
                expected_width_px=expected_width_px,
                expected_height_px=expected_height_px,
            )
            staged.append(heatmap.path)
            overlay = self._stage_one(
                directory=directory,
                key=overlay_key,
                payload=overlay_png,
                suffix=".overlay.png",
                expected_width_px=expected_width_px,
                expected_height_px=expected_height_px,
            )
            staged.append(overlay.path)
            return StagedCellExplanation(heatmap=heatmap, overlay=overlay)
        except Exception:
            self.cleanup([*staged, directory])
            raise

    def _verify_staged(self, artifact: StagedExplanationArtifact) -> None:
        key = artifact.path.relative_to(self.root).as_posix()
        verified = self.local.resolve_verified(
            key,
            expected_size_bytes=artifact.file_size_bytes,
            expected_sha256=artifact.sha256,
        )
        self._validate_png(
            verified,
            expected_width_px=artifact.width_px,
            expected_height_px=artifact.height_px,
        )

    def promote(self, staged: StagedCellExplanation) -> tuple[Path, Path]:
        artifacts = (staged.heatmap, staged.overlay)
        for artifact in artifacts:
            self._verify_staged(artifact)
            destination = self.local.resolve(artifact.relative_storage_key)
            if destination.exists():
                raise StorageError(
                    "La explicación derivada ya existe; no se sobrescribe."
                )

        promoted: list[Path] = []
        try:
            for artifact in artifacts:
                promoted.append(
                    self.local.promote(
                        artifact.path,
                        artifact.relative_storage_key,
                        expected_size_bytes=artifact.file_size_bytes,
                        expected_sha256=artifact.sha256,
                    )
                )
            self.cleanup([staged.heatmap.path.parent])
            return promoted[0], promoted[1]
        except Exception:
            self.cleanup(promoted)
            raise

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
            boundaries=(self.staging_root, self.explanation_root),
        )
