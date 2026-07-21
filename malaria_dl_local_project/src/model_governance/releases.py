"""Inventory, lineage resolution and immutable model release utilities."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path


RUN_RE = re.compile(r"/runs/([0-9a-f]{8}-[0-9a-f-]{27,})/", re.I)
MODEL_SUFFIXES = {".keras", ".h5", ".hdf5", ".ckpt", ".weights", ".pb"}
CLASS_MAPPING = {
    "0": "uninfected", "1": "parasitized",
    "positive_class": 1, "positive_label": "parasitized",
}


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _format(path: Path) -> str:
    if path.name == "saved_model.pb":
        return "tensorflow_saved_model"
    return {".keras": "keras", ".h5": "hdf5", ".hdf5": "hdf5",
            ".pb": "protobuf", ".ckpt": "checkpoint"}.get(path.suffix.lower(), "weights")


def _is_model(path: Path) -> bool:
    name = path.name.lower()
    return (path.suffix.lower() in MODEL_SUFFIXES or ".weights." in name
            or name == "saved_model.pb" or name == "checkpoint")


def inventory_artifacts(project_root: Path, registered_paths=()) -> list[dict]:
    """Hash model files in governed roots plus explicitly registered DB paths."""
    root = Path(project_root).resolve()
    candidates: set[Path] = set()
    for folder in ("outputs", "models", "checkpoints", "artifacts"):
        base = root / folder
        if base.exists():
            candidates.update(p for p in base.rglob("*") if p.is_file() and _is_model(p))
    for value in registered_paths:
        path = Path(value)
        path = path if path.is_absolute() else root / path
        if path.is_file() and _is_model(path):
            candidates.add(path)
    items = []
    for path in sorted(candidates):
        resolved = path.resolve()
        stat = resolved.stat()
        relative = os.path.relpath(resolved, root)
        match = RUN_RE.search("/" + relative.replace(os.sep, "/"))
        parts = Path(relative).parts
        model_name = parts[1] if len(parts) > 1 and parts[0] == "outputs" else None
        items.append({
            "absolute_path": str(resolved), "relative_path": relative,
            "sha256": sha256_file(resolved), "size_bytes": stat.st_size,
            "file_modified_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
            "format": _format(resolved), "model_name": model_name,
            "training_run_id_candidate": match.group(1) if match else None,
            "generic_path": resolved.name in {"best_model.keras", "final_model.keras"} and not match,
        })
    return items


def resolve_lineage(items: list[dict], known_training_run_ids=()) -> list[dict]:
    """Resolve only path UUIDs known as training runs or unique hash matches."""
    known = {str(value) for value in known_training_run_ids}
    by_hash: dict[str, set[str]] = {}
    for item in items:
        candidate = item.get("training_run_id_candidate")
        if candidate and (not known or candidate in known):
            by_hash.setdefault(item["sha256"], set()).add(candidate)
    result = []
    for original in items:
        item = dict(original)
        candidate = item.get("training_run_id_candidate")
        if candidate and (not known or candidate in known):
            item.update(training_run_id=candidate, lineage_status="resolved",
                        lineage_evidence="run_id_in_artifact_path")
        else:
            matches = by_hash.get(item["sha256"], set())
            if len(matches) == 1:
                item.update(training_run_id=next(iter(matches)), lineage_status="resolved",
                            lineage_evidence="unique_sha256_match")
            else:
                cause = "hash_matches_multiple_training_runs" if len(matches) > 1 else "no_strong_lineage_evidence"
                item.update(training_run_id=None, lineage_status="unresolved",
                            lineage_evidence=None, lineage_metadata={"cause": cause})
        result.append(item)
    return result


def validate_model_artifact(path: Path) -> None:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Model artifact does not exist: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"Model artifact is empty: {path}")
    if path.suffix.lower() == ".keras":
        if not zipfile.is_zipfile(path):
            raise ValueError(f"Corrupt or incompatible Keras artifact: {path}")
        with zipfile.ZipFile(path) as archive:
            if not {"config.json", "metadata.json"}.issubset(archive.namelist()):
                raise ValueError(f"Incomplete Keras artifact: {path}")
    elif path.suffix.lower() in {".h5", ".hdf5"}:
        with path.open("rb") as stream:
            if stream.read(8) != b"\x89HDF\r\n\x1a\n":
                raise ValueError(f"Corrupt HDF5 artifact: {path}")


def create_release(*, project_root: Path, artifact_path: Path, training_run_id: str,
                   model_name: str, output_dir: Path, status: str = "candidate",
                   evaluation_run_id=None, explainability_run_id=None,
                   preprocessing=None, threshold=None, input_signature=None,
                   output_signature=None, model_version_id=None) -> dict:
    """Copy a valid source once into a UUID-addressed immutable release."""
    uuid.UUID(str(training_run_id))
    source = Path(artifact_path).resolve()
    validate_model_artifact(source)
    source_hash = sha256_file(source)
    version_id = str(model_version_id or uuid.uuid4())
    release_dir = Path(output_dir).resolve() / model_name / version_id
    if release_dir.exists():
        raise FileExistsError(f"Release already exists; refusing overwrite: {release_dir}")
    release_dir.mkdir(parents=True)
    target = release_dir / ("model" + source.suffix.lower())
    try:
        shutil.copy2(source, target)
        if sha256_file(target) != source_hash:
            raise OSError("Immutable copy checksum mismatch")
        metadata_path = source.parent / "model_metadata.json"
        metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
        manifest = {
            "model_version_id": version_id, "training_run_id": str(training_run_id),
            "model_name": model_name, "version_number": None,
            "original_artifact_path": str(source), "immutable_artifact_path": str(target),
            "sha256": source_hash, "size_bytes": target.stat().st_size,
            "framework": "keras" if source.suffix.lower() in {".keras", ".h5", ".hdf5"} else "tensorflow",
            "framework_version": metadata.get("framework_version"),
            "preprocessing": preprocessing or metadata.get("preprocessing") or {},
            "class_mapping": CLASS_MAPPING, "input_signature": input_signature or {},
            "output_signature": output_signature or {},
            "threshold": threshold if threshold is not None else metadata.get("clinical_threshold"),
            "evaluation_run_id": evaluation_run_id, "explainability_run_id": explainability_run_id,
            "created_at": datetime.now(UTC).isoformat(), "release_status": status,
            "lineage_status": "resolved", "deployment_created": False,
        }
        files = {
            "manifest.json": manifest, "preprocessing.json": manifest["preprocessing"],
            "class_mapping.json": CLASS_MAPPING, "threshold.json": manifest["threshold"] or {},
            "evaluation_summary.json": {"evaluation_run_id": evaluation_run_id},
            "explainability_summary.json": {"explainability_run_id": explainability_run_id},
            "signature.json": {"input": manifest["input_signature"], "output": manifest["output_signature"]},
        }
        for name, content in files.items():
            (release_dir / name).write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n")
        (release_dir / "model_card.md").write_text(f"# {model_name}\n\nStatus: {status}\n")
        (release_dir / "checksums.sha256").write_text(f"{source_hash}  {target.name}\n")
        return manifest
    except Exception:
        shutil.rmtree(release_dir, ignore_errors=True)
        raise
