#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

compose exec -T backend python - <<'PY'
from sqlalchemy import text

from app.config import get_settings
from app.database_safety import assert_capstone_database
from app.db import get_primary_engine

settings = get_settings()
with get_primary_engine().connect() as connection:
    row = connection.execute(
        text("SELECT current_database(), current_user, version()")
    ).one()
    assert_capstone_database(settings, row[0])
    revision = connection.execute(
        text("SELECT version_num FROM alembic_version")
    ).scalar_one_or_none()

print("Servicio: db")
print("Estado de conexión: OK")
print(f"Base: {row[0]}")
print(f"Usuario: {row[1]}")
print(f"Versión PostgreSQL: {row[2].splitlines()[0]}")
print(f"Alembic current: {revision or 'no disponible'}")
PY
