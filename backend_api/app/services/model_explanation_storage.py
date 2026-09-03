from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from app.services.artifacts import ARTIFACTS_ROOT, CAPSTONE_ROOT


class ModelExplanationStorageError(ValueError):
    pass


@dataclass(frozen=True)
class StoredModelExplanation:
    path: Path
    reference: str
    sha256: str
    file_size_bytes: int


class ModelExplanationStorage:
    """Non-clinical model explanations rooted exclusively at ARTIFACTS_ROOT."""

    def __init__(self, root: Path | None = None):
        configured = Path(root or ARTIFACTS_ROOT)
        if not configured.is_absolute():
            raise ModelExplanationStorageError("ARTIFACTS_ROOT debe resolverse a absoluto.")
        self.root = Path(os.path.abspath(configured))
        self.staging_root = self.root / ".staging" / "model-explanations"
        self.final_root = self.root / "model-explanations"
        self._assert_existing_chain(self.root)
        self._assert_existing_chain(self.staging_root)
        self._assert_existing_chain(self.final_root)

    @staticmethod
    def _assert_existing_chain(path: Path) -> None:
        current = Path(path.anchor)
        for part in path.parts[1:]:
            current /= part
            try:
                info = current.lstat()
            except FileNotFoundError:
                break
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise ModelExplanationStorageError(
                    "ARTIFACTS_ROOT contiene un componente inseguro."
                )

    def _ensure_directory(self, path: Path) -> Path:
        target = Path(os.path.abspath(path))
        if target != self.root and not target.is_relative_to(self.root):
            raise ModelExplanationStorageError("El destino escapa de ARTIFACTS_ROOT.")
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
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise ModelExplanationStorageError(
                    "El destino de artefactos contiene un componente inseguro."
                )
        return target

    def persist(
        self,
        prediction_id: str,
        explanation_id: UUID,
        payload: bytes,
    ) -> StoredModelExplanation:
        if not payload:
            raise ModelExplanationStorageError("La explicación de modelo está vacía.")
        prediction = UUID(str(prediction_id))
        explanation = UUID(str(explanation_id))
        staging_parent = self._ensure_directory(self.staging_root)
        operation_dir = staging_parent / uuid4().hex
        operation_dir.mkdir(mode=0o700)
        staged = operation_dir / f"{uuid4().hex}.png"
        destination = (
            self.final_root
            / str(prediction)
            / str(explanation)
            / "gradcam_overlay.png"
        )
        promoted = False
        try:
            digest = hashlib.sha256()
            with staged.open("xb") as output:
                os.chmod(staged, 0o600)
                digest.update(payload)
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            self._ensure_directory(destination.parent)
            try:
                destination.lstat()
            except FileNotFoundError:
                pass
            else:
                raise ModelExplanationStorageError(
                    "La explicación de modelo ya existe; no se sobrescribe."
                )
            try:
                os.link(staged, destination, follow_symlinks=False)
            except FileExistsError as exc:
                raise ModelExplanationStorageError(
                    "La explicación de modelo ya existe; no se sobrescribe."
                ) from exc
            promoted = True
            staged.unlink()
            operation_dir.rmdir()
            reference = (
                destination.relative_to(CAPSTONE_ROOT).as_posix()
                if destination.is_relative_to(CAPSTONE_ROOT)
                else str(destination)
            )
            return StoredModelExplanation(
                path=destination,
                reference=reference,
                sha256=digest.hexdigest(),
                file_size_bytes=len(payload),
            )
        except Exception:
            staged.unlink(missing_ok=True)
            try:
                operation_dir.rmdir()
            except OSError:
                pass
            if promoted:
                destination.unlink(missing_ok=True)
            raise

    def cleanup_created(self, path: Path) -> None:
        candidate = Path(os.path.abspath(path))
        if candidate == self.final_root or not candidate.is_relative_to(self.final_root):
            return
        try:
            info = candidate.lstat()
            if stat.S_ISLNK(info.st_mode) or stat.S_ISREG(info.st_mode):
                candidate.unlink()
            else:
                return
            parent = candidate.parent
            while parent != self.final_root and parent.is_relative_to(self.final_root):
                try:
                    parent.rmdir()
                except OSError:
                    break
                parent = parent.parent
        except (FileNotFoundError, OSError):
            return
