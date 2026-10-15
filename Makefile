.PHONY: validate test test-backend test-backend-integration test-frontend test-ml db-status db-backup db-migrate-check db-migrate check-alembic-linearity db-purge-plan db-purge-execute test-db test-schema-clean test-db-up test-db-down test-db-reset test-db-bootstrap smear-reset-plan smear-reset-execute lint

validate:
	./scripts/validate.sh
test: test-backend test-frontend
test-backend:
	docker compose exec -T backend python -m pytest tests -m "not requires_docker_postgres"
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

.PHONY: test-yolo-runtime
YOLO_PYTHON ?= malaria_dl_local_project/.venv-metal/bin/python
test-yolo-runtime:
	PYTHONDONTWRITEBYTECODE=1 $(YOLO_PYTHON) -m pytest -q -p no:cacheprovider smear_segmentation_project/tests

.PHONY: test-backend-yolo-adapter
test-backend-yolo-adapter:
	docker compose exec -T backend python -m pytest -q tests/test_yolo_detector_adapter.py

.PHONY: test-db02b
test-db02b:
	@set -eu; \
	trap 'docker compose -p capstone-db02b-test -f docker-compose.db02b-test.yml down --volumes' EXIT; \
	docker compose -p capstone-db02b-test -f docker-compose.db02b-test.yml up -d --wait db02b-db; \
	docker compose -p capstone-db02b-test -f docker-compose.db02b-test.yml run --rm --no-deps db02b-tests

.PHONY: test-db02c
test-db02c:
	@set -eu; \
	trap 'docker compose -p capstone-db02c-test -f docker-compose.db02c-test.yml down --volumes' EXIT; \
	docker compose -p capstone-db02c-test -f docker-compose.db02c-test.yml up -d --wait db02c-db; \
	docker compose -p capstone-db02c-test -f docker-compose.db02c-test.yml run --rm --no-deps db02c-tests

.PHONY: test-exec1 test-exec1-frontend
test-exec1:
	docker compose exec -T -w /app/malaria_dl_local_project backend python -m pytest -q tests/test_exec1.py tests/test_assessment_e6.py tests/test_dataset_split_isolation.py

test-exec1-frontend:
	docker compose exec -T frontend npm test
	docker compose exec -T frontend npm run build

.PHONY: test-exec1-postgres
test-exec1-postgres:
	docker compose cp alembic_v2/versions/20261012_01_exec1.py backend:/tmp/exec1_migration.py
	docker compose exec -T -w /app/malaria_dl_local_project backend python -m pytest -q tests/test_exec1_postgres.py

.PHONY: test-exec1-backend
test-exec1-backend:
	docker compose exec -T backend python -m pytest -q tests/test_e6_lineage_read_only.py malaria_dl_local_project/tests/test_assessment_api_e6.py

.PHONY: prepare-exec1-postgres test-exec1-train-regression
prepare-exec1-postgres:
	python3 scripts/testing/prepare_exec1_postgres.py

test-exec1-train-regression:
	docker compose exec -T -w /app/malaria_dl_local_project backend python -m pytest -q tests/test_train_checkpoint_policy_args.py tests/test_max_epochs_config.py tests/test_checkpoint_policy.py

.PHONY: test-cli01
test-cli01:
	cd malaria_dl_local_project && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. DATABASE_URL=postgresql://cli01:fixture@invalid/cli01 "$(abspath $(SOURCE_PYTHON))" -m pytest -q -p no:cacheprovider -k "not byte_exact_canonical_rules_match_upstream_sources and not test_process_identity_is_stable_on_this_host and not test_remote_released_evidence_is_accepted_unreleased_is_not and not test_local_live_process_still_blocks" tests/test_cli01.py tests/test_exec1.py tests/test_assessment_e6.py tests/test_dataset_split_isolation.py tests/test_dataset_stage1.py tests/test_governed_dataset_contract.py tests/test_campaign_cli_plan_swv22.py tests/test_local_train_launcher.py

.PHONY: test-scc-core
test-scc-core:
	docker compose exec -T backend python -m pytest -q tests/test_scc_core.py tests/test_scientific_results_v2.py tests/test_model_comparison_api.py tests/test_e6_lineage_read_only.py tests/test_run_detail_api.py tests/test_grouped_run_lineage_api.py tests/test_lineage_children_api.py tests/test_foundation_config.py
	docker compose exec -T frontend npx tsc --noEmit --incremental false -p tsconfig.json

.PHONY: test-scc-art
test-scc-art:
	docker compose exec -T backend python -m pytest -q tests/test_scc_art.py tests/test_artifacts_api.py tests/test_local_storage_contract.py tests/test_explainability_api.py
	$(MAKE) test-scc-core
	docker compose exec -T frontend node --test tests/scc-art.test.mjs tests/e6-lineage.test.mjs tests/run-detail-explainability.test.mjs tests/auth-foundation.test.mjs

.PHONY: test-scc-xai-fix test-scc-xai-original test-scc-xai-selection
# -k runs frontend even if an existing scientific regression suite fails.
test-scc-xai-fix: test-scc-xai-original test-scc-xai-selection test-exec1-frontend

test-scc-xai-original:
	docker compose exec -T backend python -m pytest -q tests/test_scc_xai_original.py tests/test_scc_art.py tests/test_artifacts_api.py tests/test_local_storage_contract.py

test-scc-xai-selection:
	docker compose exec -T -w /app/malaria_dl_local_project backend python -m pytest -q tests/test_sample_repository.py tests/test_cli01.py tests/test_assessment_e6.py tests/test_dataset_split_isolation.py tests/test_dataset_resolution.py tests/test_dataset_stage1.py tests/test_governed_dataset_contract.py
