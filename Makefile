.PHONY: validate test test-backend test-backend-integration test-frontend test-ml db-status db-backup db-migrate-check db-migrate db-purge-plan db-purge-execute test-db test-schema-clean test-db-up test-db-down test-db-reset test-db-bootstrap smear-reset-plan smear-reset-execute lint

validate:
	./scripts/validate.sh
test: test-backend test-frontend
test-backend:
	docker compose exec -T backend python -m pytest tests -m "not requires_docker_postgres"
test-backend-integration test-db:
	docker compose exec -T -e TEST_EXECUTION=true -e TEST_ISOLATION_MODE=transaction backend \
		python -m pytest tests -m requires_docker_postgres
test-frontend:
	npm --prefix frontend test
	npm --prefix frontend run build
test-ml:
	docker compose exec -T -w /app/malaria_dl_local_project backend python -m pytest \
		tests/test_label_mapping.py \
		tests/test_decision.py \
		tests/test_image_quality.py
db-status:
	./scripts/db/status.sh
db-backup:
	./scripts/db/backup.sh
db-migrate-check:
	docker compose exec -T -e CAPSTONE_ROOT=/app backend python - < scripts/db/verify_alembic_adoption.py
	docker compose exec -T backend python -m alembic current
	docker compose exec -T backend python -m alembic heads
db-migrate:
	./scripts/db/migrate.sh
db-purge-plan:
	@test -n "$(FLAGS)" || (echo 'Uso: make db-purge-plan FLAGS="--dataset --run --cell"' >&2; exit 2)
	./scripts/db/purge.sh $(FLAGS)
db-purge-execute:
	@test -n "$(FLAGS)" || (echo 'Uso: make db-purge-execute FLAGS="--cell"' >&2; exit 2)
	@printf '%s\n' 'Purga REAL de datos. Escriba exactamente: PURGE'; read -r confirmation; \
	test "$$confirmation" = "PURGE" || (echo "Confirmación incorrecta." >&2; exit 2); \
	PURGE_DB_ALLOW_EXECUTION=1 ./scripts/db/purge.sh $(FLAGS) --yes
smear-reset-plan:
	docker compose exec -T backend /app/scripts/storage/reset_smear_analysis.sh
smear-reset-execute:
	@test -n "$(BACKUP)" || (echo "Uso: make smear-reset-execute BACKUP=/app/backups/<archivo>.dump" >&2; exit 2)
	@printf '%s\n' 'Para autorizar escriba exactamente: RESET MALARIA SMEAR ANALYSIS'; read -r confirmation; \
	docker compose exec -T -e SMEAR_RESET_ALLOW_EXECUTION=1 backend \
	  /app/scripts/storage/reset_smear_analysis.sh --execute --backup "$(BACKUP)" --confirmation "$$confirmation"
test-schema-clean:
	./scripts/db/test_schema_clean.sh
test-db-up test-db-down test-db-reset test-db-bootstrap:
	@echo "Comando retirado: las pruebas usan el servicio Docker db con rollback; no se crea, elimina ni reinicia otra base."; exit 2
lint:
	git diff --check
