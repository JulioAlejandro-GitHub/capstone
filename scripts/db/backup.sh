#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:?DATABASE_URL es obligatoria}"
backup_root="${CAPSTONE_BACKUP_DIR:-${TMPDIR:-/tmp}/capstone-backups}"
mkdir -p "$backup_root"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_path="$backup_root/capstone_${timestamp}.dump"
pg_dump --format=custom --file="$backup_path" "$DATABASE_URL"
test -s "$backup_path"
pg_restore --list "$backup_path" >/dev/null
checksum="$(shasum -a 256 "$backup_path" | awk '{print $1}')"
echo "Backup: $backup_path"
echo "SHA-256: $checksum"
