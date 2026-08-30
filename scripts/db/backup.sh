#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

backup_root="${CAPSTONE_BACKUP_DIR:-${TMPDIR:-/tmp}/capstone-backups}"
mkdir -p "$backup_root"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_path="$backup_root/capstone_${timestamp}.dump"
umask 077
temporary_path="$(mktemp "$backup_root/.capstone_${timestamp}.XXXXXX.tmp")"

cleanup() {
  if [[ -n "${temporary_path:-}" && -f "$temporary_path" ]]; then
    rm -f -- "$temporary_path"
  fi
}
trap cleanup EXIT HUP INT TERM

database_identity="$(
  compose exec -T backend python - <<'PY'
import re
import sys

from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.config import get_settings
from app.db import get_primary_engine

try:
    settings = get_settings()
    configured = make_url(settings.database_url)
    configured_user = configured.username
    configured_database = configured.database
    if configured.drivername not in {"postgresql", "postgresql+psycopg"}:
        raise RuntimeError
    if configured.host != "db" or (configured.port or 5432) != 5432:
        raise RuntimeError
    if not configured_user or not configured_database:
        raise RuntimeError
    safe_value = re.compile(r"^[A-Za-z0-9_.-]+$")
    if not safe_value.fullmatch(configured_user) or not safe_value.fullmatch(configured_database):
        raise RuntimeError
    with get_primary_engine().connect() as connection:
        actual_user, actual_database = connection.execute(
            text("SELECT current_user, current_database()")
        ).one()
    if actual_user != configured_user or actual_database != configured_database:
        raise RuntimeError
except BaseException:
    print("ERROR: la identidad canónica de backup no es válida", file=sys.stderr)
    raise SystemExit(2) from None

print(configured_user)
print(configured_database)
PY
)"

if [[ "$database_identity" != *$'\n'* ]]; then
  echo "ERROR: backend no devolvió una identidad canónica inequívoca." >&2
  exit 1
fi
database_user="${database_identity%%$'\n'*}"
database_name="${database_identity#*$'\n'}"
if [[ -z "$database_user" || -z "$database_name" || "$database_name" == *$'\n'* ]]; then
  echo "ERROR: backend no devolvió una identidad canónica inequívoca." >&2
  exit 1
fi

socket_identity="$(
  compose exec -T db sh -ceu '
    exec psql --no-password --username="$1" --dbname="$2" \
      --tuples-only --no-align \
      --command="SELECT current_user || chr(124) || current_database()"
  ' sh "$database_user" "$database_name"
)"
if [[ "$socket_identity" != "$database_user|$database_name" ]]; then
  echo "ERROR: la identidad del socket de db no coincide con backend." >&2
  exit 1
fi

compose exec -T db sh -ceu '
  exec pg_dump --no-password --username="$1" --dbname="$2" --format=custom
' sh "$database_user" "$database_name" > "$temporary_path"

if [[ ! -s "$temporary_path" ]]; then
  echo "ERROR: pg_dump produjo un archivo vacío." >&2
  exit 1
fi
chmod 600 "$temporary_path"

restore_list="$(compose exec -T db pg_restore --list < "$temporary_path")"
required_tables=(
  alembic_version
  runs
  run_lineage
  model_versions
  stage2_model_publications
  deployed_model_versions
)
for table_name in "${required_tables[@]}"; do
  if ! grep -Eq " TABLE public ${table_name} " <<< "$restore_list" \
      || ! grep -Eq " TABLE DATA public ${table_name} " <<< "$restore_list"; then
    echo "ERROR: el backup no contiene esquema y datos requeridos." >&2
    exit 1
  fi
done
if ! grep -Eq " (INDEX|CONSTRAINT|FK CONSTRAINT) public " <<< "$restore_list"; then
  echo "ERROR: el backup no contiene índices o constraints restaurables." >&2
  exit 1
fi

if [[ -e "$backup_path" ]]; then
  echo "ERROR: ya existe el nombre final del backup." >&2
  exit 1
fi
mv -- "$temporary_path" "$backup_path"
temporary_path=""
checksum="$(shasum -a 256 "$backup_path" | awk '{print $1}')"
echo "Identidad canónica verificada: usuario=$database_user base=$database_name"
echo "Contenido requerido verificado con pg_restore --list"
echo "Backup: $backup_path"
echo "SHA-256: $checksum"
