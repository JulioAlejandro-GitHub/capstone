#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

backup_root="${CAPSTONE_BACKUP_DIR:-${TMPDIR:-/tmp}/capstone-backups}"
mkdir -p "$backup_root"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_path="$backup_root/capstone_${timestamp}.dump"
umask 077
set -o noclobber
trap 'if [[ ! -s "$backup_path" ]]; then rm -f -- "$backup_path"; fi' EXIT
compose exec -T db sh -ceu \
  'pg_dump --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --format=custom' \
  > "$backup_path"
if [[ ! -s "$backup_path" ]]; then
  echo "ERROR: pg_dump produjo un archivo vacío." >&2
  exit 1
fi
compose exec -T db pg_restore --list < "$backup_path" >/dev/null
chmod 600 "$backup_path"
checksum="$(shasum -a 256 "$backup_path" | awk '{print $1}')"
echo "Backup: $backup_path"
echo "SHA-256: $checksum"
