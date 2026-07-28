from __future__ import annotations

import hashlib
import io
import os
import stat
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
    """Secure storage for on-demand Grad-CAM derivatives.

    The crop is read-only input. Heatmap and overlay are written to staging,
    verified, and promoted as new artifacts without overwriting an existing
    explanation.
    """

    def __init__(self, local_storage: LocalStorage | None = None):
        self.local = local_storage or LocalStorage()
        self.root = self.local.root
        if self.local.staging.is_symlink():
            raise StorageError("No se permiten symlinks en el padre de staging.")
        self.staging_root = self.local.staging / "cell-explanations"
        if self.staging_root.is_symlink():
            raise StorageError("No se permiten symlinks en staging de explicaciones.")
        self.staging_root.mkdir(parents=True, exist_ok=True, mode=0o700)

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
        Image.fromarray(np.rint(values * 255.0).astype(np.uint8), mode="L").save(
            output, format="PNG"
        )
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
        Image.fromarray(np.rint(values * 255.0).astype(np.uint8), mode="RGB").save(
            output, format="PNG"
        )
        return output.getvalue()

    def _staging_dir(
        self,
        classification_run_id: UUID,
        cell_detection_id: UUID,
        explanation_id: UUID,
    ) -> Path:
        path = (
            self.staging_root
            / str(classification_run_id)
            / str(cell_detection_id)
            / str(explanation_id)
        )
        if not path.resolve(strict=False).is_relative_to(self.staging_root.resolve()):
            raise StorageError("El staging de explicación escapa de su raíz.")
        return path

    @staticmethod
    def _validate_png(
        path: Path,
        payload: bytes,
        *,
        expected_width_px: int,
        expected_height_px: int,
    ) -> None:
        if not payload:
            raise StorageError("El artefacto Grad-CAM está vacío.")
        try:
            with Image.open(io.BytesIO(payload)) as image:
                if image.format != "PNG":
                    raise StorageError("El artefacto Grad-CAM no es PNG.")
                if image.size != (expected_width_px, expected_height_px):
                    raise StorageError(
                        "Las dimensiones del artefacto Grad-CAM no coinciden."
                    )
                image.verify()
            with Image.open(path) as image:
                if image.format != "PNG":
                    raise StorageError("El artefacto staged no es PNG.")
                if image.size != (expected_width_px, expected_height_px):
                    raise StorageError(
                        "Las dimensiones del artefacto staged no coinciden."
                    )
                image.load()
        except (UnidentifiedImageError, OSError, SyntaxError) as exc:
            raise StorageError("El artefacto Grad-CAM no es un PNG válido.") from exc

    def _stage_one(
        self,
        *,
        path: Path,
        key: str,
        payload: bytes,
        expected_width_px: int,
        expected_height_px: int,
    ) -> StagedExplanationArtifact:
        with path.open("xb") as output:
            os.chmod(path, 0o600)
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        self._validate_png(
            path,
            payload,
            expected_width_px=expected_width_px,
            expected_height_px=expected_height_px,
        )
        if path.stat().st_size != len(payload):
            raise StorageError("El tamaño del artefacto staged no coincide.")
        return StagedExplanationArtifact(
            path=path,
            relative_storage_key=key,
            sha256=hashlib.sha256(payload).hexdigest(),
            file_size_bytes=len(payload),
            width_px=expected_width_px,
            height_px=expected_height_px,
        )

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
        if expected_width_px < 1 or expected_height_px < 1:
            raise StorageError("Las dimensiones de explicación deben ser positivas.")
        directory = self._staging_dir(
            classification_run_id, cell_detection_id, explanation_id
        )
        directory.mkdir(parents=True, exist_ok=False, mode=0o700)
        current = self.staging_root
        for part in directory.relative_to(self.staging_root).parts:
            current /= part
            if current.is_symlink():
                self.cleanup([directory])
                raise StorageError(
                    "No se permiten symlinks en staging de explicaciones."
                )
        heatmap_key, overlay_key = self.build_keys(
            analysis_run_id, classification_run_id, cell_detection_id
        )
        try:
            heatmap = self._stage_one(
                path=directory / "gradcam_heatmap.png",
                key=heatmap_key,
                payload=heatmap_png,
                expected_width_px=expected_width_px,
                expected_height_px=expected_height_px,
            )
            overlay = self._stage_one(
                path=directory / "gradcam_overlay.png",
                key=overlay_key,
                payload=overlay_png,
                expected_width_px=expected_width_px,
                expected_height_px=expected_height_px,
            )
            return StagedCellExplanation(heatmap=heatmap, overlay=overlay)
        except Exception:
            self.cleanup([directory])
            raise

    @staticmethod
    def _verify_staged(artifact: StagedExplanationArtifact) -> None:
        try:
            info = artifact.path.lstat()
        except FileNotFoundError as exc:
            raise StorageError("El artefacto Grad-CAM staged no está disponible.") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise StorageError("El artefacto Grad-CAM staged no es regular.")
        if info.st_size != artifact.file_size_bytes:
            raise StorageError("El tamaño del artefacto Grad-CAM cambió.")
        digest = hashlib.sha256()
        with artifact.path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
        if digest.hexdigest() != artifact.sha256:
            raise StorageError("El checksum del artefacto Grad-CAM cambió.")
        try:
            with Image.open(artifact.path) as image:
                if image.format != artifact.format:
                    raise StorageError("El formato del artefacto Grad-CAM cambió.")
                if image.size != (artifact.width_px, artifact.height_px):
                    raise StorageError("Las dimensiones del artefacto Grad-CAM cambiaron.")
                image.verify()
        except (UnidentifiedImageError, OSError, SyntaxError) as exc:
            raise StorageError("El artefacto Grad-CAM staged dejó de ser válido.") from exc

    def promote(self, staged: StagedCellExplanation) -> tuple[Path, Path]:
        artifacts = (staged.heatmap, staged.overlay)
        for artifact in artifacts:
            self._verify_staged(artifact)
        destinations = tuple(
            self.local.resolve(artifact.relative_storage_key) for artifact in artifacts
        )
        for destination in destinations:
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            # Re-resolve after mkdir so a substituted symlink is observed.
            self.local.resolve(destination.relative_to(self.root).as_posix())
            if destination.exists():
                raise StorageError(
                    "La explicación derivada ya existe; no se sobrescribe."
                )
        promoted: list[Path] = []
        try:
            for artifact, destination in zip(artifacts, destinations, strict=True):
                os.replace(artifact.path, destination)
                os.chmod(destination, 0o600)
                promoted.append(destination)
            return destinations[0], destinations[1]
        except Exception:
            self.cleanup(promoted)
            raise

    def resolve(self, relative_storage_key: str, *, must_exist: bool = True) -> Path:
        return self.local.resolve(relative_storage_key, must_exist=must_exist)

    def cleanup(self, paths: list[Path]) -> None:
        staging_root = Path(os.path.abspath(self.staging_root))
        explanation_root = Path(os.path.abspath(self.root / "cell-explanations"))
        for original in paths:
            try:
                path = Path(os.path.abspath(original))
                if not (
                    path.is_relative_to(staging_root)
                    or path.is_relative_to(explanation_root)
                ):
                    continue
                if path.is_dir() and not path.is_symlink():
                    for child in sorted(
                        path.rglob("*"), key=lambda item: len(item.parts), reverse=True
                    ):
                        if child.is_symlink() or child.is_file():
                            child.unlink()
                        elif child.is_dir():
                            child.rmdir()
                    path.rmdir()
                else:
                    info = path.lstat()
                    if stat.S_ISLNK(info.st_mode) or stat.S_ISREG(info.st_mode):
                        path.unlink()
                boundary = (
                    staging_root
                    if path.is_relative_to(staging_root)
                    else explanation_root
                )
                parent = path.parent
                while parent != boundary and parent.is_relative_to(boundary):
                    try:
                        parent.rmdir()
                    except OSError:
                        break
                    parent = parent.parent
            except (FileNotFoundError, OSError):
                continue
