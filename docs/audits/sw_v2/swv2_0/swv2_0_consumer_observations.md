# SWV2.0 — Observaciones de consumidores (entrada SWV2.1)

No se modificó ningún consumidor, repository, service, DTO, API ni React.

## Backend

Clasificación: **STARTS_BUT_CONSUMER_INCOMPATIBILITY**.

- `capstone_backend` inicia (`Application startup complete`); `GET /health` → 200.
- Conecta a BD-v2: sesión `current_user = julio`, `current_database() = malaria_experiments`; `assert_capstone_database` OK.
- `GET /ready` → 503 (`database/migrations: not_ready`). Diagnóstico READ ONLY dentro del contenedor: `require_e10_schema` → `E10SchemaNotReady(['v2_function_contract'])`. La revisión `pg_v2_baseline` sí es aceptada (`SUPPORTED_REVISIONS`), pero `malaria_dl_local_project/src/malaria_dl/persistence/schema_contract.py` compara los md5 de las funciones `v2_*`/`e04_*` con `v2_runtime_contract.json`, fijado al catálogo E.4 anterior; no coincide con la baseline certificada DBV2.x. Corrección en el consumidor (SWV2.1), **no** en la BD.
- Sin hooks de arranque que escriban. Contadores de escritura v2 sin cambios con backend conectado.

### TEMPORARY DEVELOPMENT CREDENTIAL DEPENDENCY

El backend conecta mediante `DATABASE_URL` compuesto por Compose desde `.env` → rol `julio` (SUPERUSER). Es una dependencia temporal de desarrollo: las restricciones de privilegios de `capstone_v2_runtime` (DML acotado, sin DDL/TRUNCATE/ledger) no aplican al backend mientras dure, y cualquier escritura legacy iniciada desde la UI llegaría a BD-v2 limitada sólo por constraints/triggers.

**Requisito SWV2.1:** backend PostgreSQL runtime role → `capstone_v2_runtime` (credencial separada del login DBeaver) y eliminar la dependencia del backend de `julio SUPERUSER`. No implementado en SWV2.0.

## Frontend

`capstone_frontend` inicia; `GET :80` → 200. Sin cambios. Su funcionalidad depende del backend.

## Tooling v2

- `alembic_v2/env.py` + `safety.py` (congelados) exigen un descriptor de aislamiento con puerto ≠ 5432, base `capstone_v2_isolated_*` y el container ID de `capstone_db_v2`. `docs/audits/db_v2/dbv2_3/persistent_target.json` queda histórico: una futura revisión Alembic v2 rechazará este destino hasta que una fase autorizada defina un nuevo mecanismo de target (sin editar la baseline).
- `scripts/db/dbv23_*`, `dbv24_*`, `dbv25_*` apuntan al endpoint histórico 56440 y quedan como evidencia; SWV2.0 añade `scripts/db/swv20_integration.py` parametrizado por endpoint.

## Tests / CI (preexistente, no introducido por SWV2.0)

- `test_scientific_storage_docker_contract.py` ya fallaba en HEAD por el bloque TEMPORAL de `docker-compose.override.yml` (`CAPSTONE_LOCAL_STORAGE_ROOTS`, 2026-09-15). SWV2.0 sólo actualizó la aserción del volumen `postgres_data` al contrato externo; la falla previa persiste igual. `test_docker_postgres_tooling.py`: 7/7.
- `scripts/check_docker_postgres_contract.py`: 33 infracciones en HEAD y 33 con SWV2.0 (ninguna nueva).

## Infraestructura residual

- Volumen legacy `capstone-malaria_postgres_data` (clúster sysid 7668020338728398886) conservado sin contenedor; decidir su archivo/eliminación explícitamente.
- 11 contenedores `capstone_v2_isolated_*` detenidos de fases previas, con sus volúmenes, sin tocar.
- La contraseña de `.env` usada por `julio` tiene menos de 8 caracteres; mitigado publicando el puerto sólo en 127.0.0.1.
