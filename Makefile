.PHONY: validate test test-backend test-backend-integration test-frontend test-ml db-status db-backup db-migrate-check db-migrate test-db test-schema-clean test-fresh-schema lint

PYTHON ?= malaria_dl_local_project/.venv/bin/python

validate:
	./scripts/validate.sh
test: test-backend test-frontend
test-backend:
	PYTHONPATH=backend_api $(PYTHON) -m pytest backend_api/tests
test-backend-integration test-db:
	TEST_EXECUTION=true TEST_ISOLATION_MODE=transaction PYTHONPATH=backend_api $(PYTHON) -m pytest backend_api/tests -m requires_local_postgres
test-frontend:
	npm --prefix frontend test
	npm --prefix frontend run build
test-ml:
	PYTHONPATH=malaria_dl_local_project $(PYTHON) -m pytest malaria_dl_local_project/tests -q -rs
db-status:
	./scripts/db/status.sh
db-backup:
	./scripts/db/backup.sh
db-migrate-check:
	PYTHONPATH=backend_api $(PYTHON) scripts/db/verify_alembic_adoption.py
	PYTHONPATH=backend_api $(PYTHON) -m alembic current
	PYTHONPATH=backend_api $(PYTHON) -m alembic heads
db-migrate:
	./scripts/db/migrate.sh
test-schema-clean:
	./scripts/db/test_schema_clean.sh
test-fresh-schema:
	PYTHONPATH=backend_api:malaria_dl_local_project $(PYTHON) scripts/db/validate_fresh_schema.py
lint:
	git diff --check
