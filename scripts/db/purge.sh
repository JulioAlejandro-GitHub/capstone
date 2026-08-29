#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

verified_backup=""
backup_requested=false
execute_requested=false
for argument in "$@"; do
  if [[ "$argument" == "--backup-before" ]]; then
    backup_requested=true
  elif [[ "$argument" == "--execute" ]]; then
    execute_requested=true
  fi
done

if [[ "$backup_requested" == true && "$execute_requested" == true ]]; then
  backup_output="$("$CAPSTONE_ROOT/scripts/db/backup.sh")"
  printf '%s\n' "$backup_output"
  verified_backup="$(printf '%s\n' "$backup_output" | sed -n 's/^Backup: //p' | head -n 1)"
  if [[ -z "$verified_backup" ]]; then
    echo "ERROR: no se pudo identificar el backup verificado." >&2
    exit 2
  fi
fi

compose_arguments=(exec -T)
if [[ -n "${PURGE_DB_ALLOW_EXECUTION:-}" ]]; then
  compose_arguments+=(-e "PURGE_DB_ALLOW_EXECUTION=$PURGE_DB_ALLOW_EXECUTION")
fi
if [[ -n "$verified_backup" ]]; then
  compose_arguments+=(-e "CAPSTONE_VERIFIED_BACKUP=$verified_backup")
fi
compose "${compose_arguments[@]}" backend \
  python malaria_dl_local_project/scripts/purge_db_data.py "$@"
