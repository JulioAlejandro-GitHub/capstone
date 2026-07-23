#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAPSTONE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ML_PYTHON="$CAPSTONE_ROOT/malaria_dl_local_project/.venv/bin/python"

if [[ ! -x "$ML_PYTHON" ]]; then
  echo "No existe el runtime ML Python 3.12: $ML_PYTHON" >&2
  exit 1
fi

exec "$ML_PYTHON" -m uvicorn app.main:app \
  --app-dir "$CAPSTONE_ROOT/backend_api" \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
