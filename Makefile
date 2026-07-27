.PHONY: validate test test-backend test-backend-integration test-frontend test-ml db-status db-backup db-migrate-check db-migrate test-db test-schema-clean test-db-up test-db-down test-db-reset test-db-bootstrap lint

PYTHON ?= backend_api/.venv/bin/python

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
	PYTHONPATH=malaria_dl_local_project malaria_dl_local_project/.venv/bin/python -m pytest \
		malaria_dl_local_project/tests/test_label_mapping.py \
		malaria_dl_local_project/tests/test_decision.py \
		malaria_dl_local_project/tests/test_image_quality.py
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
test-db-up test-db-down test-db-reset test-db-bootstrap:
	@echo "Comando retirado: PostgreSQL local no se inicia, detiene, resetea ni reconstruye. Use make test-db."
lint:
	git diff --check
