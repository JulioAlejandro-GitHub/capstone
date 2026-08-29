#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

if [[ "${TEST_EXECUTION:-false}" != "true" ]]; then
  echo "ERROR: TEST_EXECUTION=true es obligatorio." >&2
  exit 2
fi

compose exec -T \
  -e TEST_EXECUTION=true \
  -e CONFIRM_DROP_TEMPORARY_TEST_SCHEMAS="${CONFIRM_DROP_TEMPORARY_TEST_SCHEMAS:-false}" \
  backend python - <<'PY'
import os

from sqlalchemy import text

from app.config import get_settings
from app.database_safety import assert_capstone_database, assert_safe_temporary_schema
from app.db import get_primary_engine

settings = get_settings()
engine = get_primary_engine()
with engine.connect() as connection:
    actual_database = connection.execute(text("SELECT current_database() ")).scalar_one()
    assert_capstone_database(settings, actual_database)
    schemas = connection.execute(text("""
        SELECT nspname
        FROM pg_namespace
        WHERE nspname ~ '^capstone_test_[a-z0-9_]{6,48}$'
        ORDER BY nspname
    """)).scalars().all()

if not schemas:
    print("No hay schemas temporales residuales.")
    raise SystemExit(0)

for schema in schemas:
    print(schema)
if os.getenv("CONFIRM_DROP_TEMPORARY_TEST_SCHEMAS") != "true":
    raise SystemExit(
        "Solo listado. Para limpiar, confirme explícitamente los schemas temporales."
    )

for schema in schemas:
    safe_schema = assert_safe_temporary_schema(settings, schema)
    quoted = engine.dialect.identifier_preparer.quote(safe_schema)
    with engine.begin() as connection:
        actual_database = connection.execute(text("SELECT current_database() ")).scalar_one()
        assert_capstone_database(settings, actual_database)
        connection.exec_driver_sql(f"DROP SCHEMA {quoted} CASCADE")
PY
