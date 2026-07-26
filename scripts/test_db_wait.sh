#!/usr/bin/env bash
set -euo pipefail
for _ in {1..60}; do
  if docker compose -f docker-compose.test.yml exec -T postgres pg_isready -U capstone_test -d capstone_test >/dev/null; then exit 0; fi
  sleep 1
done
echo "PostgreSQL de test no alcanzó readiness" >&2
exit 1
