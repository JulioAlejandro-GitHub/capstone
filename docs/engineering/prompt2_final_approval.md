# Aprobación final de fundación

> **Estado documental:** `HISTORICAL_AUDIT`
> **Uso operativo:** No; la recomendación y los gates pertenecen a ese corte.
> **Snapshot:** 2026-07-27, head `20260726_02`.

Fecha: 2026-07-27. Recomendación histórica: **RECHAZAR** hasta cerrar credenciales E2E y cobertura
atómica por repositorio. Ese gate fue sustituido por el contrato Docker-only vigente.

|Gate|Resultado|Evidencia|Comando|Fecha|Observación|
|---|---|---|---|---|---|
|POSTGRES_SNAPSHOT|PASS|17.9, malaria_experiments/public|comprobaciones read-only históricas|2026-07-27|Una instancia usada|
|ALEMBIC_CURRENT_EQUALS_HEAD|PASS|20260726_02|`alembic current/heads`|2026-07-27|Sin upgrade|
|BACKEND_SNAPSHOT|PASS|Uvicorn iniciado en el entorno anterior|evidencia histórica|2026-07-27|Flujo retirado|
|FRONTEND_SNAPSHOT|PASS|Vite HTTP 200|evidencia histórica|2026-07-27|Flujo retirado|
|HEALTH_LOCAL|PASS|HTTP 200|`GET /health`|2026-07-27||
|READY_LOCAL|PASS|DB/migrations/storage ready|`GET /ready`|2026-07-27||
|LOGIN_AUTHORIZED_USER|BLOCKED|Variables E2E ausentes|precheck de entorno|2026-07-27|No se inventaron credenciales|
|AUTH_ME|BLOCKED|Requiere login autorizado|`GET /auth/me`|2026-07-27|401 sin token correcto|
|JWT_LOG_SANITIZATION|BLOCKED|Sin JWT real para revisión E2E|búsqueda sanitizada|2026-07-27|Sanitización unitaria pasa|
|DISABLED_USER_TOKEN_REJECTED|PASS|Usuario sintético, 401, rollback|test auth PostgreSQL|2026-07-27|Residuo 0|
|RBAC|PASS|Toda mutación inventariada|test mutation policy|2026-07-27|401/403 unitarios|
|AUDIT_FAILURE_ROLLBACK_E2E|PASS parcial|FK real inválida revierte transacción|test PostgreSQL parametrizado|2026-07-27|No cubre cada repositorio real|
|CRITICAL_MUTATION_ATOMICITY|BLOCKED|Unidad común probada; familias incompletas|tests focalizados|2026-07-27|No declarar cobertura plena|
|TRANSACTION_ISOLATION|PASS|13 tests locales|pytest local PostgreSQL|2026-07-27|Rollback garantizado|
|TEMPORARY_SCHEMA_RESIDUE|PASS|0|consulta pg_namespace|2026-07-27||
|TEST_DATA_RESIDUE|PASS|usuarios/runs/audit sintéticos 0|consultas read-only|2026-07-27||
|HISTORICAL_MIGRATIONS_UNCHANGED|PASS|diff vacío|`git diff <base> -- db/init`|2026-07-27||
|INCIDENTAL_FILES_CLEAN|PASS|027, test y complemento sin diff|diffs específicos|2026-07-27||
|BACKEND_TESTS|PASS|89 passed, 4 skipped|pytest backend con gate local|2026-07-27||
|FRONTEND_TESTS|PASS|62 passed|`npm test`|2026-07-27||
|FRONTEND_BUILD|PASS|Vite build|`npm run build`|2026-07-27||
|ML_FAST|PASS|17 passed|pytest focalizado|2026-07-27||
|ML_FULL|PASS|359 passed, 16 skipped, 37 subtests|pytest ML completo|2026-07-27|Sin descarga/entrenamiento|
|REMOTE_CI_CONFIGURATION|PASS|YAML válido en ese snapshot|parser YAML y revisión|2026-07-27|No ejecutado en GitHub|
|STAGE2_DEFAULT_UNCHANGED|PASS|No se ejecutó mutación; valor observado estable|consulta read-only|2026-07-27||

Para continuar de forma segura:

```bash
export CAPSTONE_E2E_USERNAME='usuario_autorizado'
read -s CAPSTONE_E2E_PASSWORD
export CAPSTONE_E2E_PASSWORD
```

Luego se debe ejecutar el gate E2E sin imprimir las variables.
