"""Prepare or verify the approved TFDS malaria 1.0.0 cell source."""
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
from src.malaria_dl.data.cell_source import prepare_cell_source
from src.malaria_dl.data.full_smears_download import SourceError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true', help='Read existing TFRecords; never download')
    args = parser.parse_args(argv)
    config = resolve_source_config()
    print(f'Dataset: NLM-Falciparum-Thin-Cell-Images\nConfigured source: {config.cell_source}\nDownload mechanism: TFDS malaria 1.0.0', flush=True)
    try:
        result = prepare_cell_source(config, verify_only=args.verify_only)
    except (SourceError, OSError, ValueError) as exc:
        print(f'Status: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
