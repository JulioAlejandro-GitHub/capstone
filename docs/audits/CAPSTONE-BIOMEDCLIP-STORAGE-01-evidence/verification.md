# Verificación de CAPSTONE-BIOMEDCLIP-STORAGE-01

Fecha: 2026-10-27. No se escribieron filas ni esquemas PostgreSQL.

- `PYTHONPATH=malaria_dl_local_project malaria_dl_local_project/.venv-metal/bin/python -m pytest -q malaria_dl_local_project/tests/test_zero_shot_storage.py malaria_dl_local_project/tests/test_model_version_resolver.py`: 21 PASS.
- Tests `test_accelerator_guard.py`, `test_local_train_launcher.py` junto a la primera versión de storage: 57 PASS, 1 skip. La variable local permanece intacta.
- `docker exec capstone_backend python -m pytest -q tests/test_cell_classification_services.py tests/test_stage2_status_read_only.py tests/test_cell_activation.py`: 60 PASS, 13 skip. No se habilitó el opt-in de integración.
- Tests host `test_docker_postgres_tooling.py`, `test_db_purge_tool.py`, `test_smear_reset_tool.py`: 193 PASS. PYTHONPATH incluye backend_api, malaria_dl_local_project y smear_segmentation_project/src; conexión ficticia para mocks.
- Regresión `test_model_registry_e2.py`, `test_input_contract_e3.py`, `test_biomedclip_pretrained.py`, `test_assessment_e6.py`, `test_model_execution_config.py`: 98 casos aprobados tras corregir PYTHONPATH del subproceso y los campos framework/architecture de la fixture. Lectura del catálogo con `PGOPTIONS='-c default_transaction_read_only=on'`, URL obtenida en memoria con `execution.local_launch.database_url()`. 95 PASS iniciales y 3 reejecutados; equivalencia de preprocesamiento: 2 PASS. No se ejecutó TRAIN científico.
- `npm --prefix frontend test`: 443 PASS.
- `npm --prefix frontend run build`: PASS; advertencia no bloqueante de tamaño de chunks.
- `docker compose config -q`: PASS.
- `docker exec capstone_db pg_isready`: accepting connections.
- `GET http://localhost:8000/health`: 200.
- Los tres SQL nuevos se ejecutaron con `PGOPTIONS='-c default_transaction_read_only=on'` y `psql -v ON_ERROR_STOP=1`. El de incorporación sólo PREPARE/DEALLOCATE; ningún EXECUTE.
- `git diff --check`: PASS.

## Smoke de inferencia

Entorno: `/Users/julio/.cache/capstone-biomedclip-01b/venv/bin/python`.
`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `PGOPTIONS='-c default_transaction_read_only=on'`.
Resolvedor productivo con raíz permitida explícita de la caché actual del host;
ModelVersionResolver con versión `3fd16a84-b5c7-442b-916b-e0438bb0f3e5`.
Se compararon IDs, SHA, dependencias, snapshot y transformadores, y se predijo una
imagen RGB sintética 80×100 de color (120,60,90). Resultado en resolver-smoke.json.
No se invocó activación, publicación, clasificación persistida ni evaluación científica.
El mismo directorio no está montado en el backend actual; su resolución allí falla.

## Inventarios

storage.json: consulta de models/runs/artifacts/model_versions, catálogo de constraints,
y hash/tamaño de los 40 archivos (cinco originales + 35 copias). Lectura chunked SHA-256.
isolated.json: SELECT READ ONLY por los siete UUID en siete bases aisladas ya existentes.
Se verificaron los 25 registros recuperados contra sus archivos; cinco carpetas se conservan.
No se inició ni detuvo el contenedor aislado ni se aplicó su esquema a la base operativa.
