#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_PYTHON="$ROOT_DIR/malaria_dl_local_project/.venv/bin/python"
DEFAULT_BACKEND_PYTHON="$ROOT_DIR/backend_api/.venv/bin/python"
if [[ -x "$DEFAULT_PYTHON" ]]; then
  PYTHON_BIN="${PYTHON_BIN:-$DEFAULT_PYTHON}"
else
  PYTHON_BIN="${PYTHON_BIN:-python}"
fi
BACKEND_PYTHON_BIN="${BACKEND_PYTHON_BIN:-$DEFAULT_BACKEND_PYTHON}"

export MPLCONFIGDIR="${MPLCONFIGDIR:-${TMPDIR:-/tmp}/capstone-matplotlib}"
mkdir -p "$MPLCONFIGDIR"

cd "$ROOT_DIR"
"$PYTHON_BIN" -m unittest discover -s malaria_dl_local_project/tests

if [[ -x "$BACKEND_PYTHON_BIN" ]]; then
  "$BACKEND_PYTHON_BIN" -m unittest malaria_dl_local_project.tests.test_backend_endpoints
else
  echo "Aviso: backend_api/.venv no existe; no se ejecutaron pruebas backend dedicadas."
fi

cd "$ROOT_DIR/frontend"
npm run build
