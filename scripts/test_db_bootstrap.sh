#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export APP_ENV=test
export DATABASE_URL=postgresql://capstone_test:test-only-password@localhost:55433/capstone_test
export TEST_DATABASE_URL="$DATABASE_URL"
export TEST_DATABASE_ALLOW_RESET=true
export TEST_DATABASE_REQUIRE_EPHEMERAL=true
export JWT_SECRET=test-only-secret-at-least-thirty-two-characters
cd "$ROOT_DIR"
backend_api/.venv/bin/python malaria_dl_local_project/scripts/init_db.py
backend_api/.venv/bin/python scripts/db/verify_alembic_adoption.py --pre-stamp
backend_api/.venv/bin/alembic stamp 20260726_00
backend_api/.venv/bin/alembic upgrade head
backend_api/.venv/bin/python scripts/db/verify_alembic_adoption.py
