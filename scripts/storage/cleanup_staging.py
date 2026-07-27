#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend_api"))

from app.config import get_settings  # noqa: E402
from app.services.local_storage import LocalStorage  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Limpia staging antiguo sin seguir symlinks.")
    parser.add_argument("--apply", action="store_true", help="Elimina; por defecto sólo informa.")
    args = parser.parse_args()
    storage = LocalStorage()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=get_settings().staging_retention_hours)
    candidates = []
    for path in storage.staging.iterdir():
        if path.is_symlink() or not path.is_file():
            continue
        modified = datetime.fromtimestamp(path.stat(follow_symlinks=False).st_mtime, timezone.utc)
        if modified < cutoff:
            candidates.append(path)
    for path in candidates:
        print(f"{'DELETE' if args.apply else 'WOULD_DELETE'} {path.name}")
        if args.apply:
            path.unlink()
    print(f"staging_candidates={len(candidates)} mode={'apply' if args.apply else 'dry-run'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
