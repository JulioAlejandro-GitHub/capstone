"""Database first; attributable artifact deletion only after verification."""
from scripts.maintenance.orchestrator import main

if __name__ == '__main__':
    raise SystemExit(main('all'))
