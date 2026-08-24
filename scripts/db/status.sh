#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:?DATABASE_URL es obligatoria}"
python_bin="${PYTHON:-backend_api/.venv/bin/python}"
target="$(PYTHONPATH=backend_api "$python_bin" -c 'from app.config import get_settings; from app.database_safety import redacted_database_target; print(redacted_database_target(get_settings().database_url))' 2>/dev/null)"
echo "Base configurada: $target"
PYTHONPATH=backend_api "$python_bin" - <<'PY'
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic.script import ScriptDirectory
from app.config import get_settings
from app.database_safety import assert_capstone_database, database_target
from app.db import normalize_sqlalchemy_url
s = get_settings()
host, port, expected = database_target(s.database_url)
with create_engine(normalize_sqlalchemy_url(s.database_url)).connect() as c:
    row = c.execute(text("select current_database(), current_user, version()")).one()
    assert_capstone_database(s, row[0])
    revision = c.execute(text("select version_num from alembic_version")).scalar_one_or_none()
head = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
print(f"Host: {host}\nPuerto: {port}\nBase: {row[0]}\nUsuario: {row[1]}")
print(f"Versión: {row[2]}\nAlembic current: {revision}\nAlembic head: {head}")
PY
