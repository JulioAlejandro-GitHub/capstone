.PHONY: validate test test-backend test-frontend test-db-up test-db-bootstrap test-db-reset test-db-down lint docker-build
validate:
	./scripts/validate.sh
test: test-backend test-frontend
test-backend:
	backend_api/.venv/bin/python -m pytest backend_api/tests
test-frontend:
	npm --prefix frontend test
	npm --prefix frontend run build
test-db-up:
	./scripts/test_db_up.sh
test-db-bootstrap:
	./scripts/test_db_bootstrap.sh
test-db-reset:
	./scripts/test_db_reset.sh
test-db-down:
	./scripts/test_db_down.sh
lint:
	git diff --check
docker-build:
	docker compose build backend
