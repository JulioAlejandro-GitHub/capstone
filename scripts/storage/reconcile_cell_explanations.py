#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import stat
import sys
from pathlib import Path, PurePosixPath

from PIL import Image, UnidentifiedImageError
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend_api"))

from app.config import get_settings  # noqa: E402
from app.db import get_primary_engine  # noqa: E402


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_key(root: Path, key_value: str) -> Path:
    key = PurePosixPath(key_value)
    if key.is_absolute() or ".." in key.parts or not key.parts:
        raise ValueError("unsafe_key")
    candidate = root.joinpath(*key.parts)
    current = root
    for part in key.parts:
        current /= part
        if current.is_symlink():
            raise ValueError("symlink")
    if not candidate.is_relative_to(root):
        raise ValueError("outside_root")
    return candidate


def inspect_artifact(
    *,
    root: Path,
    row: dict,
    kind: str,
    known: set[Path],
) -> list[tuple[str, str]]:
    identity = f"{row['id']}:{kind}"
    issues: list[tuple[str, str]] = []
    key = row.get(f"{kind}_storage_key")
    expected_sha = row.get(f"{kind}_sha256")
    expected_size = row.get(f"{kind}_file_size_bytes")
    if not key or not expected_sha or not expected_size:
        return [("generated_metadata_incomplete", identity)]
    try:
        path = resolve_key(root, str(key))
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise ValueError("not_regular")
        known.add(path)
        if info.st_size != int(expected_size):
            issues.append(("size_mismatch", identity))
        if checksum(path) != str(expected_sha):
            issues.append(("checksum_mismatch", identity))
        try:
            with Image.open(path) as image:
                if image.format != "PNG":
                    issues.append(("format_mismatch", identity))
                if image.size != (int(row["width_px"]), int(row["height_px"])):
                    issues.append(("dimensions_mismatch", identity))
                image.verify()
        except (UnidentifiedImageError, OSError, SyntaxError):
            issues.append(("invalid_png", identity))
    except (ValueError, FileNotFoundError, OSError):
        issues.append(("missing_or_invalid_artifact", identity))
    return issues


def reconcile(*, root: Path, rows: list[dict]) -> list[tuple[str, str]]:
    explanation_root = root / "cell-explanations"
    staging_root = root / ".staging" / "cell-explanations"
    issues: list[tuple[str, str]] = []
    known: set[Path] = set()
    unsafe_root = root.is_symlink()
    unsafe_explanation_root = unsafe_root or explanation_root.is_symlink()
    unsafe_staging_root = (
        unsafe_root
        or (root / ".staging").is_symlink()
        or staging_root.is_symlink()
    )
    if unsafe_root:
        issues.append(("storage_root_symlink", "STORAGE_ROOT"))
    if explanation_root.is_symlink():
        issues.append(("cell_explanation_root_symlink", "cell-explanations"))
    if (root / ".staging").is_symlink() or staging_root.is_symlink():
        issues.append(
            ("cell_explanation_staging_symlink", ".staging/cell-explanations")
        )

    for row in rows:
        if row["status"] == "generated":
            if unsafe_explanation_root:
                issues.append(("missing_or_invalid_artifact", str(row["id"])))
                continue
            for kind in ("heatmap", "overlay"):
                issues.extend(
                    inspect_artifact(
                        root=root,
                        row=row,
                        kind=kind,
                        known=known,
                    )
                )
        elif any(
            row.get(field)
            for field in (
                "heatmap_storage_key",
                "heatmap_sha256",
                "heatmap_file_size_bytes",
                "overlay_storage_key",
                "overlay_sha256",
                "overlay_file_size_bytes",
            )
        ):
            issues.append(("non_generated_has_artifact", str(row["id"])))

    if explanation_root.exists() and not unsafe_explanation_root:
        for path in explanation_root.rglob("*"):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                issues.append(("cell_explanation_symlink", relative))
            elif path.is_file() and path not in known:
                issues.append(("orphan_explanation_artifact", relative))
    if staging_root.exists() and not unsafe_staging_root:
        for path in staging_root.rglob("*"):
            # Every descendant is residue in a dry-run reconciliation,
            # including empty directories left after interrupted promotion.
            issues.append(
                ("staging_residue", path.relative_to(root).as_posix())
            )
    return issues


def main() -> int:
    """Report metadata/file drift; intentionally never mutates storage."""

    root = Path(os.path.abspath(get_settings().storage_root))
    with get_primary_engine().connect() as connection:
        rows = [
            dict(row)
            for row in connection.execute(
                text(
                    """
                    SELECT
                      id,status,heatmap_storage_key,heatmap_sha256,
                      heatmap_file_size_bytes,overlay_storage_key,
                      overlay_sha256,overlay_file_size_bytes,width_px,height_px
                    FROM cell_explanations
                    ORDER BY created_at,id
                    """
                )
            ).mappings().all()
        ]
    issues = reconcile(root=root, rows=rows)
    for kind, identity in issues:
        print(f"{kind}: {identity}")
    print(f"metadata_rows={len(rows)} issues={len(issues)} mode=dry-run")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
