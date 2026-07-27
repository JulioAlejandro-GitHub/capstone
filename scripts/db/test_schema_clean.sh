#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:?DATABASE_URL es obligatoria}"
schemas="$(psql "$DATABASE_URL" -Atqc "SELECT nspname FROM pg_namespace WHERE nspname ~ '^capstone_test_[a-z0-9_]{6,48}$' ORDER BY nspname")"
if [[ -z "$schemas" ]]; then
  echo "No hay schemas temporales residuales."
  exit 0
fi
echo "$schemas"
if [[ "${CONFIRM_DROP_TEMPORARY_TEST_SCHEMAS:-false}" != "true" ]]; then
  echo "Solo listado. Para limpiar, establezca CONFIRM_DROP_TEMPORARY_TEST_SCHEMAS=true."
  exit 2
fi
while IFS= read -r schema; do
  [[ "$schema" =~ ^capstone_test_[a-z0-9_]{6,48}$ ]] || exit 3
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "DROP SCHEMA \"$schema\" CASCADE"
done <<< "$schemas"
