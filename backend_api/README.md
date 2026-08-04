# Backend API

API FastAPI del monolito modular Capstone. Expone autenticación local,
trazabilidad experimental, gobierno de modelos y análisis técnico de frotis.
No sirve el frontend y sus resultados no constituyen diagnóstico clínico.

## Runtime

El único entorno local soportado para API e inferencia es Python 3.12 en
`malaria_dl_local_project/.venv`. Desde la raíz del repositorio:

```bash
./malaria_dl_local_project/.venv/bin/python -m uvicorn \
  app.main:app \
  --app-dir backend_api \
  --reload \
  --port 8000 \
  --env-file .env
```

`./scripts/start_backend_api.sh` añade validación de `.env` y dependencias y
limita el bind a `127.0.0.1`. Requiere `DATABASE_URL` y `JWT_SECRET` privados;
la plantilla única está en `/.env.example`.

Liveness: `GET /health`. Readiness: `GET /ready`.

## Superficies HTTP

- `/api/v1/auth`: login y principal autenticado.
- `/api/v1/scientific`: identidad pseudonimizada y trazabilidad de casos,
  muestras, frotis e imágenes.
- `/api/v1/analysis`: quality gate y runs de análisis.
- `/api/v1/cell-analysis`: detección, crops y revisión.
- `/api/v1/cell-classification`: clasificación, resúmenes, Grad-CAM y revisión.
- `/api/...`: endpoints existentes de runs, artefactos, catálogo y gobierno de
  modelos.

JWT, RBAC y ownership se validan en backend. Las respuestas públicas no deben
exponer paths físicos, storage keys privadas, secretos ni stack traces. Las
mutaciones sensibles escriben auditoría en la misma transacción.

## Base de datos

El bootstrap SQL histórico y toda la cadena Alembic son inmutables. Antes de
iniciar contra una base persistente:

```bash
make db-status
make db-migrate-check
```

Use `make db-migrate` para backup, preflight transaccional y upgrade al head
vigente. No use `stamp`, downgrade o resets como atajo. La política completa
está en [`../docs/database.md`](../docs/database.md).

## Pruebas

```bash
make test-backend
make test-backend-integration  # PostgreSQL local, rollback obligatorio
```

Arquitectura y operación: [`../docs/architecture.md`](../docs/architecture.md),
[`../docs/security.md`](../docs/security.md),
[`../docs/stage2-workflow.md`](../docs/stage2-workflow.md) y
[`../docs/operations.md`](../docs/operations.md).
