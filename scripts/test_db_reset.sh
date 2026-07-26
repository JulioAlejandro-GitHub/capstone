#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export APP_ENV=test DATABASE_URL=postgresql://capstone_test:test-only-password@localhost:55433/capstone_test
export TEST_DATABASE_URL="$DATABASE_URL" TEST_DATABASE_ALLOW_RESET=true TEST_DATABASE_REQUIRE_EPHEMERAL=true
export JWT_SECRET=test-only-secret-at-least-thirty-two-characters
cd "$ROOT_DIR"
backend_api/.venv/bin/python -c 'from app.config import get_settings; from app.database_safety import assert_safe_test_database; assert_safe_test_database(get_settings(), confirmation=True)'
docker compose -f docker-compose.test.yml down -v
docker compose -f docker-compose.test.yml up -d --wait postgres
