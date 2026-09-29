"""Rebuild the canonical database preserving authentication and scientific data."""
from scripts.maintenance.orchestrator import main

if __name__ == '__main__':
    raise SystemExit(main('db'))
