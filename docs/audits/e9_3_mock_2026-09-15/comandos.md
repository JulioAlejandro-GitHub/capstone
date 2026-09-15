# Repetición en Compose, sólo fixtures

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
 -e RUN_PIPELINE_MOCK_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
 -e TF_NUM_INTRAOP_THREADS=1 -e TF_NUM_INTEROP_THREADS=1 \
 backend python -B -m pytest -q -s -p no:cacheprovider tests/test_pipeline_faults_postgres.py
```

Regresión adicional ejecutada (46 casos antes del último caso TEST añadido):

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
 -e RUN_PIPELINE_MOCK_POSTGRES_TESTS=1 -e RUN_STAGE93_GLOBAL_POSTGRES_TESTS=1 \
 -e RUN_STAGE6_POSTGRES_TESTS=1 -e RUN_STAGE7_POSTGRES_TESTS=1 \
 -e PYTHONDONTWRITEBYTECODE=1 -e TF_NUM_INTRAOP_THREADS=1 -e TF_NUM_INTEROP_THREADS=1 \
 backend python -B -m pytest -q -s -p no:cacheprovider \
 tests/test_pipeline_faults_postgres.py tests/test_global_execution_postgres.py \
 tests/test_assessment_postgres.py tests/test_science_postgres.py \
 -k 'not public_e6_revision_readonly'
```

Los flags sólo habilitan fixtures. Nunca usar --resume, recover ni ack-breaker para estas pruebas. Los nuevos directorios tmp_path se eliminan por fixture al terminar; los esquemas se limpian por el fixture E4, incluso ante fallos.
