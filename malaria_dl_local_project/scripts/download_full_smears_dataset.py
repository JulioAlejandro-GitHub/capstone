"""Manual, database-independent preparation of the complete NLM RAW distribution."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (PROJECT_ROOT, PROJECT_ROOT.parent / 'malaria_dataset_split_project/src'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from malaria_split.source_config import resolve_source_config
from src.malaria_dl.data.full_smears_download import SourceError, prepare_full_smear_source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', help='Local RAW root (absolute or relative to capstone)')
    parser.add_argument('--verify-only', action='store_true', help='Offline validation; no data modifications')
    args = parser.parse_args(argv)
    config = resolve_source_config(args.root)
    print(f'Dataset: NIH-NLM-ThinBloodSmearsPf\nSource: {config.smear_source}\nDestination: {config.smear_root}', flush=True)
    try:
        result = prepare_full_smear_source(config, verify_only=args.verify_only)
    except (SourceError, OSError, ValueError) as exc:
        print(f'Status: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
