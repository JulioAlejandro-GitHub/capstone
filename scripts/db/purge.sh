#!/usr/bin/env bash
# Wrapper del purgador de datos por subsistema (scripts/db/purge.py).
# Ejecuta el script DENTRO del contenedor backend de Docker Compose, que es donde
# DATABASE_URL apunta a db:5432 y donde vive una copia del script (COPY del Dockerfile).
#
#   scripts/db/purge.sh --dataset --run --cell                    # dry-run (por defecto)
#   PURGE_DB_ALLOW_EXECUTION=1 scripts/db/purge.sh --cell --yes    # purga real
#
# Cuando se pasa --yes, este wrapper crea y verifica primero un backup PostgreSQL con
# scripts/db/backup.sh y se lo entrega al script vía CAPSTONE_VERIFIED_BACKUP; el script
# rechaza --yes sin un backup válido, igual que scripts/storage/reset_smear_analysis.py.
#
# El purgador anterior (verdad-única legacy que truncaba TODA la base) vive en
# malaria_dl_local_project/scripts/purge_db_data.py y no lo cubre este wrapper.
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

execute_requested=false
for argument in "$@"; do
  if [[ "$argument" == "--yes" ]]; then
    execute_requested=true
  fi
done

verified_backup=""
if [[ "$execute_requested" == true ]]; then
  # El backup debe caer en ./backups para que el contenedor lo vea en /app/backups (ro).
  export CAPSTONE_BACKUP_DIR="${CAPSTONE_BACKUP_DIR:-$CAPSTONE_ROOT/backups}"
  backup_output="$("$CAPSTONE_ROOT/scripts/db/backup.sh")"
  printf '%s\n' "$backup_output"
  host_backup="$(printf '%s\n' "$backup_output" | sed -n 's/^Backup: //p' | head -n 1)"
  if [[ -z "$host_backup" || ! -f "$host_backup" ]]; then
    echo "ERROR: no se pudo identificar el backup verificado." >&2
    exit 2
  fi
  verified_backup="/app/backups/$(basename "$host_backup")"
fi

compose_arguments=(exec -T)
if [[ -n "${PURGE_DB_ALLOW_EXECUTION:-}" ]]; then
  compose_arguments+=(-e "PURGE_DB_ALLOW_EXECUTION=$PURGE_DB_ALLOW_EXECUTION")
fi
if [[ -n "$verified_backup" ]]; then
  compose_arguments+=(-e "CAPSTONE_VERIFIED_BACKUP=$verified_backup")
fi

compose "${compose_arguments[@]}" backend python /app/scripts/db/purge.py "$@"
