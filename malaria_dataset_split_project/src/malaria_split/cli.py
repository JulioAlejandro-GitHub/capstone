import argparse
import json
import os
from pathlib import Path

from malaria_split.discovery import scan_current_physical_split


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auditoría read-only del split físico")
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("audit-current-split")
    audit.add_argument("--config", type=Path, default=_project_root() / "config/current_split.yaml")
    audit.add_argument("--root", help="Override explícito de la ruta auditada")
    args = parser.parse_args(argv)
    if args.command == "audit-current-split":
        return audit_current_split(args.config, args.root)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

