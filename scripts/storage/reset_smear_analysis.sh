#!/usr/bin/env bash
set -Eeuo pipefail
if [[ ! -f /app/scripts/storage/reset_smear_analysis.py ]]; then
  echo "ERROR: este comando sólo puede ejecutarse dentro del backend Docker Compose." >&2
  exit 2
fi
exec python /app/scripts/storage/reset_smear_analysis.py "$@"
