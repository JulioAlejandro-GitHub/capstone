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

from app.db import get_primary_engine  # noqa: E402
from app.config import get_settings  # noqa: E402


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
        current = current / part
        if current.is_symlink():
            raise ValueError("symlink")
    if not candidate.is_relative_to(root):
        raise ValueError("outside_root")
    return candidate


def main() -> int:
    """Report metadata/file drift; intentionally never mutates storage."""

    root = Path(os.path.abspath(get_settings().storage_root))
    crop_root = root / "cell-crops"
    staging_root = root / ".staging" / "cell-detection"
    issues: list[tuple[str, str]] = []
    known: set[Path] = set()
    unsafe_root = root.is_symlink()
    unsafe_crop_root = unsafe_root or crop_root.is_symlink()
    unsafe_staging_root = (
        unsafe_root
        or (root / ".staging").is_symlink()
        or staging_root.is_symlink()
    )
    if unsafe_root:
        issues.append(("storage_root_symlink", "STORAGE_ROOT"))
    if crop_root.is_symlink():
        issues.append(("cell_crop_root_symlink", "cell-crops"))
    if (root / ".staging").is_symlink() or staging_root.is_symlink():
        issues.append(("staging_root_symlink", ".staging/cell-detection"))
    with get_primary_engine().connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT id,relative_storage_key,sha256,file_size_bytes,width_px,height_px
                FROM cell_crops
                ORDER BY created_at,id
                """
            )
        ).mappings().all()
        missing_crops = connection.execute(
            text(
                """
                SELECT cd.id
                FROM cell_detections cd
                LEFT JOIN cell_crops crop ON crop.cell_detection_id=cd.id
                WHERE crop.id IS NULL
                ORDER BY cd.created_at,cd.id
                """
            )
        ).mappings().all()
    for row in rows:
        if unsafe_crop_root:
            issues.append(("missing_or_invalid_crop", str(row["id"])))
            continue
        try:
            path = resolve_key(root, row["relative_storage_key"])
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                raise ValueError("not_regular")
            known.add(path)
            if info.st_size != row["file_size_bytes"]:
                issues.append(("size_mismatch", str(row["id"])))
            if checksum(path) != row["sha256"]:
                issues.append(("checksum_mismatch", str(row["id"])))
            try:
                with Image.open(path) as image:
                    if image.format != "PNG":
                        issues.append(("format_mismatch", str(row["id"])))
                    if image.size != (row["width_px"], row["height_px"]):
                        issues.append(("dimensions_mismatch", str(row["id"])))
                    image.verify()
            except (UnidentifiedImageError, OSError, SyntaxError):
                issues.append(("invalid_png", str(row["id"])))
        except (ValueError, FileNotFoundError, OSError):
            issues.append(("missing_or_invalid_crop", str(row["id"])))

    if crop_root.exists() and not unsafe_crop_root:
        for path in crop_root.rglob("*"):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                issues.append(("cell_crop_symlink", relative))
            elif path.is_file() and path not in known:
                issues.append(("orphan_crop", relative))

    if staging_root.exists() and not unsafe_staging_root:
        for path in staging_root.rglob("*"):
            if path.is_symlink() or path.is_file():
                issues.append(
                    ("staging_residue", path.relative_to(root).as_posix())
                )
    issues.extend(("detection_without_crop", str(row["id"])) for row in missing_crops)

    for kind, identity in issues:
        print(f"{kind}: {identity}")
    print(f"metadata_rows={len(rows)} issues={len(issues)} mode=dry-run")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
