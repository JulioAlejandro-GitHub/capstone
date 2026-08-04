#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_PYTHON="$ROOT_DIR/malaria_dl_local_project/.venv/bin/python"
if [[ -x "$DEFAULT_PYTHON" ]]; then
  PYTHON_BIN="${PYTHON_BIN:-$DEFAULT_PYTHON}"
else
  PYTHON_BIN="${PYTHON_BIN:-python}"
fi

export MPLCONFIGDIR="${MPLCONFIGDIR:-${TMPDIR:-/tmp}/capstone-matplotlib}"
mkdir -p "$MPLCONFIGDIR"

cd "$ROOT_DIR"
"$PYTHON_BIN" -m unittest discover -s malaria_dl_local_project/tests
"$PYTHON_BIN" -m unittest malaria_dl_local_project.tests.test_backend_endpoints

cd "$ROOT_DIR/frontend"
npm run build
