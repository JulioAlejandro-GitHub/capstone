#!/usr/bin/env bash
set -euo pipefail
python_bin="${PYTHON:-malaria_dl_local_project/.venv/bin/python}"
PYTHONPATH=backend_api "$python_bin" scripts/db/verify_alembic_adoption.py
./scripts/db/backup.sh
PYTHONPATH=backend_api "$python_bin" scripts/db/validate_alembic_transactionally.py
PYTHONPATH=backend_api "$python_bin" -m alembic upgrade head
PYTHONPATH=backend_api "$python_bin" -m alembic current
PYTHONPATH=backend_api "$python_bin" -m alembic heads
