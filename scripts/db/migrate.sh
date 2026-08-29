#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

compose exec -T backend python -m alembic current
compose exec -T backend python -m alembic heads
compose exec -T -e CAPSTONE_ROOT=/app backend python - \
  < "$CAPSTONE_ROOT/scripts/db/verify_alembic_adoption.py"
"$CAPSTONE_ROOT/scripts/db/backup.sh"
compose exec -T -e CAPSTONE_ROOT=/app backend python - \
  < "$CAPSTONE_ROOT/scripts/db/validate_alembic_transactionally.py"
compose exec -T backend python -m alembic upgrade head
compose exec -T backend python -m alembic current
compose exec -T backend python -m alembic heads
