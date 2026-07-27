#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend_api"))

from app.db import get_primary_engine  # noqa: E402
from app.services.local_storage import LocalStorage, StorageError  # noqa: E402


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconciliación no destructiva de microscopy storage.")
    parser.parse_args()
    storage = LocalStorage()
    issues = []
    known = set()
    with get_primary_engine().connect() as connection:
        rows = connection.execute(text("""
          SELECT id,storage_key,file_size_bytes,sha256 FROM microscopy_images
        """)).mappings().all()
        batch_mismatches = connection.execute(text("""
          SELECT b.id,b.received_image_count,count(i.id) actual
          FROM image_ingestion_batches b LEFT JOIN microscopy_images i ON i.ingestion_batch_id=b.id
          GROUP BY b.id HAVING b.received_image_count<>count(i.id)
        """)).mappings().all()
    for row in rows:
        try:
            path = storage.resolve(row["storage_key"], must_exist=True)
            known.add(path)
            if path.stat().st_size != row["file_size_bytes"]:
                issues.append(("size_mismatch", row["id"]))
            if checksum(path) != row["sha256"]:
                issues.append(("checksum_mismatch", row["id"]))
        except (StorageError, OSError):
            issues.append(("missing_or_invalid_storage", row["id"]))
    image_root = storage.root / "microscopy-images"
    if image_root.exists():
        for path in image_root.rglob("*"):
            if path.is_file() and not path.is_symlink() and path not in known:
                issues.append(("orphan_file", path.relative_to(storage.root).as_posix()))
    issues.extend(("batch_count_mismatch", row["id"]) for row in batch_mismatches)
    for kind, identity in issues:
        print(f"{kind}: {identity}")
    print(f"issues={len(issues)} mode=dry-run")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
