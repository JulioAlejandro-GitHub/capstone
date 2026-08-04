#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAPSTONE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ML_PYTHON="$CAPSTONE_ROOT/malaria_dl_local_project/.venv/bin/python"
ENV_FILE="$CAPSTONE_ROOT/.env"

if [[ ! -x "$ML_PYTHON" ]]; then
  echo "No existe el runtime ML Python 3.12: $ML_PYTHON" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "No existe la configuración local: $ENV_FILE" >&2
  echo "Copie .env.example a .env y complete DATABASE_URL y JWT_SECRET." >&2
  exit 1
fi

if ! "$ML_PYTHON" -c \
  'import PIL, fastapi, jwt, multipart, numpy, psycopg, pwdlib, sqlalchemy, tensorflow, uvicorn' \
  >/dev/null 2>&1; then
  echo "El runtime ML no contiene todas las dependencias API/ML declaradas." >&2
  echo "Instale malaria_dl_local_project/requirements.txt antes de iniciar." >&2
  exit 1
fi

export MPLCONFIGDIR="${MPLCONFIGDIR:-${TMPDIR:-/tmp}/capstone-matplotlib}"
mkdir -p "$MPLCONFIGDIR"

cd "$CAPSTONE_ROOT"
exec "$ML_PYTHON" -m uvicorn app.main:app \
  --app-dir backend_api \
  --host 127.0.0.1 \
  --port 8000 \
  --reload \
  --env-file .env
