from pathlib import Path

from fastapi import HTTPException


CAPSTONE_ROOT = Path(__file__).resolve().parents[3]
MALARIA_PROJECT_ROOT = CAPSTONE_ROOT / "malaria_dl_local_project"
ALLOWED_ARTIFACT_ROOTS = [
    (MALARIA_PROJECT_ROOT / "outputs").resolve(),
    (CAPSTONE_ROOT / "data").resolve(),
]


def resolve_artifact_path(path: str) -> Path:
    if not path:
        raise HTTPException(status_code=400, detail="Parametro path requerido.")

    raw_path = Path(path)
    candidates = []
    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        candidates.append(CAPSTONE_ROOT / raw_path)
        if raw_path.parts and raw_path.parts[0] == "outputs":
            candidates.append(MALARIA_PROJECT_ROOT / raw_path)

    resolved = next((candidate.resolve() for candidate in candidates if candidate.exists()), None)
    if resolved is None:
        resolved = candidates[0].resolve()

    if not any(resolved == root or root in resolved.parents for root in ALLOWED_ARTIFACT_ROOTS):
        raise HTTPException(status_code=403, detail="Artefacto fuera de la carpeta permitida.")
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="Artefacto no encontrado.")
    return resolved
