"""Orchestrate source preparation only. Scientific split integration awaits S2."""
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
from src.malaria_dl.data.full_smears_download import SourceError, prepare_full_smear_source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true', help='Verify both sources without downloads or writes')
    parser.add_argument('--root', help='Override Full Smear RAW root only')
    parser.add_argument('--split', type=float, nargs=3, metavar=('TRAIN', 'VAL', 'TEST'),
                        help='Reserved patient-level target percentages; disabled until S2')
    args = parser.parse_args(argv)
    if args.split is not None:
        print('SPLIT_NOT_ENABLED: Cell Classification: governed patient split AVAILABLE; '
              'Smear Segmentation: PENDING_S2. No source preparation or split was executed.', file=sys.stderr)
        return 2
    config = resolve_source_config(args.root)
    print('CAPSTONE — DATASET PREPARATION', flush=True)
    try:
        for position, (label, prepare) in enumerate([
            ('Cell Classification Source', prepare_cell_source),
            ('Full Smear Source', prepare_full_smear_source),
        ], start=1):
            print(f'[{position}/2] {label}', flush=True)
            print(json.dumps(prepare(config, verify_only=args.verify_only), indent=2), flush=True)
    except (SourceError, OSError, ValueError) as exc:
        print(f'DATASET SOURCES: NOT READY — {exc}', file=sys.stderr)
        return 1
    print('DATASET SOURCES: READY')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
