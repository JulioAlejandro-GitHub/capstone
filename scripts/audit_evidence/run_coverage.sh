#!/usr/bin/env bash
# CAPSTONE-EVIDENCE-COVERAGE-01: consulta de solo lectura sobre el PostgreSQL vigente (contenedor db).
# Uso, desde la raíz del repo:  bash scripts/audit_evidence/run_coverage.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
env_value() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- | sed -E 's/^["'\'']//; s/["'\'']$//'; }
POSTGRES_USER="${POSTGRES_USER:-$(env_value POSTGRES_USER)}"
POSTGRES_DB="${POSTGRES_DB:-$(env_value POSTGRES_DB)}"
out=docs/audits/capstone_evidence_coverage_01_evidence
mkdir -p "$out"
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -X -q \
  < scripts/audit_evidence/coverage.sql > "$out/db_coverage.json"
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print('OK', len(d['trains'] or []), 'TRAIN')" "$out/db_coverage.json"
