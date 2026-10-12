.PHONY: test-observability
test-observability:
	docker exec -e PYTHONDONTWRITEBYTECODE=1 capstone_backend python /tmp/capstone-db02a/docs/audits/capstone_db_02a/run_tests.py tests/test_db02a_observability.py tests/test_campaigns_api_swv22.py
.PHONY: test-errors-ui build-ui
test-errors-ui:
	cd frontend && node --test tests/db02a-errors.test.mjs
build-ui:
	npm --prefix frontend run build
.PHONY: test-db03
test-db03:
	docker exec -e PYTHONDONTWRITEBYTECODE=1 capstone_backend python /tmp/capstone-db02a/docs/audits/capstone_db_02a/run_tests.py tests/test_e6_lineage_read_only.py tests/test_lineage_children_api.py tests/test_training_summaries_api.py tests/test_training_summaries_postgres.py tests/test_lineage_children_postgres.py
.PHONY: test-db03-ui
test-db03-ui:
	cd frontend && node --test tests/e6-lineage.test.mjs tests/db02a-errors.test.mjs
