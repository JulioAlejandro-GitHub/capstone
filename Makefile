.PHONY: validate test test-backend test-backend-integration test-frontend test-ml db-status db-backup db-migrate-check db-migrate check-alembic-linearity db-purge-plan db-purge-execute test-db test-schema-clean test-db-up test-db-down test-db-reset test-db-bootstrap smear-reset-plan smear-reset-execute lint

validate:
	./scripts/validate.sh
test: test-backend test-frontend
test-backend:
	docker compose exec -T backend python -m pytest tests -m "not requires_docker_postgres"

.PHONY: test-e6-lineage-backend test-e6-lineage-frontend
.PHONY: test-stage2-status-backend test-stage2-status-frontend
test-stage2-status-backend:
	docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 backend python -m pytest -q -p no:cacheprovider \
		tests/test_stage2_status_read_only.py tests/test_governance_api.py tests/test_e6_lineage_read_only.py \
		/app/malaria_dl_local_project/tests/test_stage2_publication_eligibility.py

test-stage2-status-frontend:
	docker compose exec -T frontend node --test tests/stage2-status.test.mjs tests/stage2-availability.test.mjs tests/executions-promotion.test.mjs tests/executions-lazy-loading.test.mjs tests/e6-lineage.test.mjs tests/four-step-production-flow.test.mjs
	docker compose exec -T frontend npm run build

# Synthetic SELECT fixtures and read-only evidence; no scientific execution or DB writes.
test-e6-lineage-backend:
	docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 backend python -m pytest -q -p no:cacheprovider \
		tests/test_lineage_children_api.py tests/test_training_summaries_api.py tests/test_e6_lineage_read_only.py

test-e6-lineage-frontend:
	docker compose exec -T frontend node --test tests/e6-lineage.test.mjs tests/executions-lazy-loading.test.mjs tests/clean-routing.test.mjs tests/scientific-results-v2.test.mjs tests/stage2-availability.test.mjs
	docker compose exec -T frontend npm run build
.PHONY: test-backend-detection-crop test-backend-detection-crop-integration
test-backend-detection-crop:
	docker compose exec -T backend python -m pytest -q \
		tests/test_detection_crop_equivalence.py tests/test_cell_detection_services.py \
		tests/test_cell_classification_services.py tests/test_smear_workflow_contract.py
test-backend-detection-crop-integration:
	docker compose exec -T -e TEST_EXECUTION=true -e TEST_ISOLATION_MODE=transaction backend \
		python -m pytest -q tests/test_cell_detection_postgres.py tests/test_cell_classification_postgres.py
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

.PHONY: test-governed-dataset
# Synthetic files and mocked persistence only; never run an official split.
DATASET_TEST_PYTHON ?= malaria_dl_local_project/.venv-local-train/bin/python
test-governed-dataset:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=malaria_dl_local_project $(DATASET_TEST_PYTHON) -m pytest -q -p no:cacheprovider \
		-k 'not test_byte_exact_canonical_rules_match_upstream_sources' \
		malaria_dl_local_project/tests/test_dataset_resolution.py \
		malaria_dl_local_project/tests/test_dataset_split_isolation.py \
		malaria_dl_local_project/tests/test_dataset_stage1.py \
		malaria_dl_local_project/tests/test_governed_dataset_contract.py::test_snapshot_is_immutable_and_change_is_rejected \
		malaria_dl_local_project/tests/test_local_train_launcher.py::test_relocated_host_prefix_is_the_same_dataset \
		malaria_dl_local_project/tests/test_local_train_launcher.py::test_different_dataset_is_still_rejected \
		malaria_dl_local_project/tests/test_local_train_launcher.py::test_docker_bootstrap_changes_nothing \
		malaria_dl_local_project/tests/test_local_train_launcher.py::test_host_bootstrap_needs_no_jwt \
		malaria_dl_local_project/tests/test_assessment_e6.py

.PHONY: test-train-persistence
test-train-persistence:
	python3 scripts/test_train_persistence.py
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
check-alembic-linearity:
	@# Gate estático de CI reproducible en local antes de hacer push: deriva el head del
	@# ScriptDirectory del repo y exige una única línea recta (un head, sin branch/merge
	@# points). No hay ningún head hardcodeado. Usa el intérprete de backend_api/.venv si
	@# existe (trae alembic); si no, `python` del PATH.
	@PY="$(CURDIR)/backend_api/.venv/bin/python"; [ -x "$$PY" ] || PY=python; \
	  "$$PY" scripts/db/check_alembic_linearity.py
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

.PHONY: limpiar-experimentos-bd limpiar-artefactos limpiar-experimentos
# Host Python orchestrates Docker only; SQL/dependencies run in the backend image.
limpiar-experimentos-bd:
	python3 -m scripts.maintenance.clean_experiments_db
limpiar-artefactos:
	python3 -m scripts.maintenance.clean_experiment_artifacts
limpiar-experimentos:
	python3 -m scripts.maintenance.clean_all_experiments

# S1.D source tools explicitly run offline without Docker/PostgreSQL.
SOURCE_PYTHON ?= malaria_dl_local_project/.venv-local-train/bin/python
.PHONY: test-dataset-sources test-dataset-source-regression
test-dataset-sources:
	PYTHONDONTWRITEBYTECODE=1 $(SOURCE_PYTHON) -m pytest -q -p no:cacheprovider malaria_dl_local_project/tests/source_preparation

test-dataset-source-regression:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=malaria_dataset_split_project/src $(SOURCE_PYTHON) -m pytest -q -p no:cacheprovider malaria_dataset_split_project/tests/unit/test_dataset_families.py malaria_dataset_split_project/tests/unit/test_polygon_set.py malaria_dataset_split_project/tests/unit/test_thin_blood_smears_pf.py malaria_dataset_split_project/tests/unit/test_freeze.py

.PHONY: test-canonical-nlm-identity audit-canonical-nlm-identity
# Pure adapters and offline evidence checks; no PostgreSQL test fixtures.
test-canonical-nlm-identity:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=malaria_dataset_split_project/src $(SOURCE_PYTHON) -m pytest -q -p no:cacheprovider malaria_dataset_split_project/tests/unit/test_nlm_identity.py scripts/audit_s1_2/test_audit.py

audit-canonical-nlm-identity:
	PYTHONDONTWRITEBYTECODE=1 $(SOURCE_PYTHON) scripts/audit_s1_2/audit.py

.PHONY: test-canonical-nlm-regression
test-canonical-nlm-regression:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=malaria_dataset_split_project/src $(SOURCE_PYTHON) -m pytest -q -p no:cacheprovider malaria_dataset_split_project/tests/unit/test_identity_resolver.py malaria_dataset_split_project/tests/unit/test_patient_group_stratified_v1.py malaria_dataset_split_project/tests/unit/test_patient_split_optimizer.py

.PHONY: test-smear-same-split audit-smear-same-split
# S2 real-source integration rehearsals use PostgreSQL transactions with rollback.
test-smear-same-split:
	docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/app/malaria_dataset_split_project/src backend python -m pytest -q -p no:cacheprovider /scripts/audit_s2/test_same_split.py

audit-smear-same-split:
	PYTHONDONTWRITEBYTECODE=1 $(SOURCE_PYTHON) scripts/audit_s2/audit.py $(FLAGS)

.PHONY: test-smear-same-split-regression
test-smear-same-split-regression:
	docker compose exec -T backend mkdir -p /tmp/capstone_s2_regression
	docker compose cp malaria_dataset_split_project/tests backend:/tmp/capstone_s2_regression/tests
	docker compose exec -T -w /tmp/capstone_s2_regression -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/app/malaria_dataset_split_project/src backend python -m pytest -q -p no:cacheprovider tests/integration/test_smear_source_ingest.py tests/integration/test_split_generation_rehearsal.py tests/integration/test_dataset_invariants_and_trainability.py

.PHONY: test-smear-validation test-smear-validation-regression audit-smear-validation
test-smear-validation:
	docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/app/malaria_dataset_split_project/src backend python -m pytest -q -p no:cacheprovider /scripts/audit_s3/test_validation.py

test-smear-validation-regression:
	docker compose exec -T backend mkdir -p /tmp/capstone_s3_regression
	docker compose cp malaria_dataset_split_project/tests backend:/tmp/capstone_s3_regression/tests
	docker compose exec -T -w /tmp/capstone_s3_regression -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/app/malaria_dataset_split_project/src backend python -m pytest -q -p no:cacheprovider tests/integration/test_formal_validation.py tests/integration/test_dataset_invariants_and_trainability.py tests/unit/test_freeze.py

audit-smear-validation:
	PYTHONDONTWRITEBYTECODE=1 $(SOURCE_PYTHON) scripts/audit_s3/audit.py $(FLAGS)

.PHONY: scientific-parameters-doc test-scientific-parameters
.PHONY: test-calibration-postgres
.PHONY: check-calibration-database-isolation
check-calibration-database-isolation:
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_calibration_database_isolation.py

# C2.12: one disposable database in the existing instance; guarded official v2 install.
test-calibration-postgres:
	PYTHONDONTWRITEBYTECODE=1 $(SOURCE_PYTHON) scripts/run_calibration_postgres.py

scientific-parameters-doc:
	PYTHONDONTWRITEBYTECODE=1 $(SOURCE_PYTHON) scripts/generate_scientific_parameters.py

test-scientific-parameters:
	PYTHONDONTWRITEBYTECODE=1 $(SOURCE_PYTHON) scripts/generate_scientific_parameters.py --check
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=malaria_dl_local_project $(SOURCE_PYTHON) -m pytest -q -p no:cacheprovider malaria_dl_local_project/tests/test_scientific_parameter_registry.py malaria_dl_local_project/tests/test_threshold_calibration.py malaria_dl_local_project/tests/test_checkpoint_policy.py malaria_dl_local_project/tests/test_training_results.py malaria_dl_local_project/tests/test_assessment_e6.py::test_threshold_no_implicit_clinical_fallback malaria_dl_local_project/tests/test_assessment_e6.py::test_test_forbidden_development

.PHONY: test-cell-activation-backend
test-cell-activation-backend:
	docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.cell-activation-test.yml up -d --wait cell-activation-db
	@trap 'docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.cell-activation-test.yml rm -sf cell-activation-db' EXIT; \
	docker compose run --rm --no-deps -T \
		-v "$(CURDIR)/alembic_v2:/app/alembic_v2:ro" -v "$(CURDIR)/alembic_v2.ini:/app/alembic_v2.ini:ro" \
		-e CELL_ACTIVATION_TEST_URL=postgresql+psycopg://postgres@cell-activation-db:5432/cell_activation_test \
		-e PYTHONDONTWRITEBYTECODE=1 backend python -m pytest -q -p no:cacheprovider \
		tests/test_cell_activation.py tests/test_cell_classification_services.py

.PHONY: test-cell-checkpoint-read-only
test-cell-checkpoint-read-only:
	docker compose exec -T -e PYTHONDONTWRITEBYTECODE=1 backend python -m pytest -q -p no:cacheprovider tests/test_cell_activation_read_only.py

.PHONY: migrate-cell-activation
migrate-cell-activation:
	python scripts/db/migrate_cell_activation.py
