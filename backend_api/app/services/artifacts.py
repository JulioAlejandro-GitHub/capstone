from pathlib import Path

from fastapi import HTTPException


CAPSTONE_ROOT = Path(__file__).resolve().parents[3]
MALARIA_PROJECT_ROOT = CAPSTONE_ROOT / "malaria_dl_local_project"
ALLOWED_ARTIFACT_ROOTS = [
    (MALARIA_PROJECT_ROOT / "outputs").resolve(),
]


def resolve_artifact_path(path: str) -> Path:
    if not path:
        raise HTTPException(status_code=400, detail="Parametro path requerido.")

    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = MALARIA_PROJECT_ROOT / candidate

    resolved = candidate.resolve()
    if not any(resolved == root or root in resolved.parents for root in ALLOWED_ARTIFACT_ROOTS):
        raise HTTPException(status_code=403, detail="Artefacto fuera de la carpeta permitida.")
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="Artefacto no encontrado.")
    return resolved

