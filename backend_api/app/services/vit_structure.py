"""Cached structure of a registered ViT base, one JSON per base checkpoint SHA-256. Never overwritten."""
import json
import subprocess
import sys
from pathlib import Path
from threading import Lock
from typing import Any
from app.config import get_settings
from app.services.vit_structure_compute import VERSION

TIMEOUT_SECONDS = 240
# One base load at a time keeps the machine usable; it happens once per base.
computing = Lock()


class StructureUnavailable(Exception):
    """The base structure could not be derived; the reason is shown, the reference structure is kept."""


class VitStructureService:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or get_settings().model_structure_root

    def path(self, sha256: str) -> Path:
        if len(sha256) != 64 or any(c not in '0123456789abcdef' for c in sha256):
            raise StructureUnavailable('Identidad de la base inválida.')
        return self.root / f'{sha256}.json'

    def _saved(self, path: Path, sha256: str) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        saved = json.loads(path.read_text())
        return saved if saved.get('version') == VERSION and saved.get('base', {}).get('sha256') == sha256 else None

    def read(self, base: dict[str, Any], input_size: int) -> dict[str, Any]:
        sha256 = str(((base or {}).get('checkpoint') or {}).get('sha256') or '')
        path = self.path(sha256)
        saved = self._saved(path, sha256)
        if saved:
            return saved
        if not computing.acquire(timeout=TIMEOUT_SECONDS):
            raise StructureUnavailable('Otra derivación de estructura está en curso; reintenta en un momento.')
        try:
            saved = self._saved(path, sha256)  # another request may have finished it meanwhile
            if saved:
                return saved
            job = dict(base=base, input_size=input_size, path=str(path))
            try:
                subprocess.run([sys.executable, '-m', 'app.services.vit_structure_compute'], input=json.dumps(job, default=str), text=True,
                               check=True, timeout=TIMEOUT_SECONDS, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
                raise StructureUnavailable('No fue posible cargar la base registrada para derivar su estructura.') from None
        finally:
            computing.release()
        saved = self._saved(path, sha256)
        if not saved:
            raise StructureUnavailable('La estructura derivada no corresponde a la base registrada.')
        return saved
