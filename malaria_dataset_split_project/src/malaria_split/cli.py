import argparse
import json
import os
from pathlib import Path

from malaria_split.discovery import scan_current_physical_split
from malaria_split.identity import (
    IdentityStatus,
    analyze_identities,
    build_source_identity_index,
    resolve_physical_manifest,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _capstone_root() -> Path:
    return _project_root().parent


def _read_simple_config(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values


def _csv_tuple(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def audit_current_split(config_path: Path, root_override: str | None = None) -> int:
    config = _read_simple_config(config_path)
    configured_root = root_override or os.getenv("MALARIA_CURRENT_SPLIT_ROOT") or config[
        "current_physical_split_root"
    ]
    root = Path(configured_root).expanduser()
    if not root.is_absolute():
        root = _capstone_root() / root
    result = scan_current_physical_split(
        root,
        _csv_tuple(config.get("expected_splits", "train,val,test")),
        _csv_tuple(config.get("expected_classes", "parasitized,uninfected")),
        _csv_tuple(config.get("expected_extensions", ".png,.jpg,.jpeg")),
    )
    payload = result.to_dict()
    payload["inspected_root"] = str(root.resolve())
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not result.structural_errors else 1


def _configured_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else _capstone_root() / path


def _spot_check(records, limit: int = 10) -> list[dict]:
    """Deterministic diverse sample for human evidence review."""
    selected = []
    seen = set()
    for item in records:
        if item.identity_status != IdentityStatus.VERIFIED:
            continue
        dimension = (item.historical_split, item.class_name, item.patient_id)
        if dimension in seen:
            continue
        selected.append(item.to_dict())
        seen.add(dimension)
        if len(selected) == limit:
            break
    return selected


def audit_patient_identity(config_path: Path) -> int:
    config = _read_simple_config(config_path)
    physical_root = _configured_path(config["current_physical_split_root"])
    original_root = _configured_path(config["tfds_original_images_root"])
    mappings = [
        _configured_path(config["patient_mapping_parasitized"]),
        _configured_path(config["patient_mapping_uninfected"]),
    ]
    source_index, index_diagnostics = build_source_identity_index(original_root, mappings)
    records = resolve_physical_manifest(
        physical_root / "files_manifest.csv", physical_root, source_index
    )
    analysis = analyze_identities(records)
    spot_check = _spot_check(records)
    output = _configured_path(config["identity_audit_output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_classification": "DERIVED AUDIT ARTIFACT",
        "source_index": index_diagnostics,
        "summary": {key: value for key, value in analysis.items() if key != "patients"},
        "patients": analysis["patients"],
        "manual_spot_check_sample": spot_check,
        "records": [item.to_dict() for item in records],
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "artifact_classification": payload["artifact_classification"],
        "output": str(output.resolve()),
        "source_index": index_diagnostics,
        "summary": payload["summary"],
        "spot_check_records": len(spot_check),
    }, ensure_ascii=False, indent=2))
    return 0 if len(records) == 27558 and not index_diagnostics["mapping_errors"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auditoría read-only del split físico")
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("audit-current-split")
    audit.add_argument("--config", type=Path, default=_project_root() / "config/current_split.yaml")
    audit.add_argument("--root", help="Override explícito de la ruta auditada")
    identity = subparsers.add_parser("audit-patient-identity")
    identity.add_argument("--config", type=Path, default=_project_root() / "config/current_split.yaml")
    args = parser.parse_args(argv)
    if args.command == "audit-current-split":
        return audit_current_split(args.config, args.root)
    if args.command == "audit-patient-identity":
        return audit_patient_identity(args.config)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
