# Invoke from repository root. SCHEMA must be a read-only export of current PostgreSQL.
COMPOSE = docker compose -p capstone-data01b1-audit -f docs/audits/capstone_data_01b1_evidence/compose.yaml
SCHEMA ?= /tmp/capstone_data01b1_schema.sql
.PHONY: test
test:
	@test -s "$(SCHEMA)"
	@set -eu; \
	trap '$(COMPOSE) down --volumes' EXIT; \
	$(COMPOSE) up -d --wait audit-db; \
	$(COMPOSE) exec -T audit-db psql -X -v ON_ERROR_STOP=1 -q -U audit_fixture -d audit_fixture < "$(SCHEMA)"; \
	$(COMPOSE) run --rm --no-deps audit-tests
