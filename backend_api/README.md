# Backend API

Runtime soportado: Python 3.12. `backend_api/.venv` conserva el entorno liviano
para tests y migraciones; no contiene TensorFlow. Para servir clasificación,
instale las dependencias declaradas por `malaria_dl_local_project/requirements.txt`
en su entorno Python 3.12 y use `scripts/start_backend_api.sh`. Auth está en
`/api/v1/auth`; liveness en `/health` y readiness en `/ready`.

El venv ML observado durante Prompt 8 aún no contiene `PyJWT`, `pwdlib` ni
`python-multipart`: están declaradas, pero no fueron instaladas porque no se
permitieron descargas. El script de inicio falla de forma explícita en su
preflight hasta sincronizar ese entorno; no debe interpretarse como una API
productiva arrancable en el estado validado.

`/api/v1/scientific` ofrece registro, consulta, actualización, archivado y trazabilidad
con JWT, RBAC y auditoría atómica. No carga binarios ni admite DELETE físico. Requiere la
revisión Alembic `20260727_01`.
# Ejecución local

```bash
./scripts/start_backend_api.sh
```

Requiere `APP_ENV=development`, `DATABASE_URL` y `JWT_SECRET` privados. Docker no es parte
del flujo oficial.

Prompt 4 agrega multipart por streaming, validación Pillow, SHA-256 backend-only,
lotes científicos y contenido autenticado. Use las variables de `.env.example`.
# Microscopy analysis API

`/api/v1/analysis` expone lotes elegibles, runs congelados, evaluaciones
técnicas, eventos y decisiones auditadas. Requiere PostgreSQL y storage local.

# Cell classification API

`/api/v1/cell-classification` resuelve exclusivamente `stage2/default`, congela
modelo e inputs, clasifica crops por batches y expone predicciones, resumen,
Grad-CAM manual y reviews append-only. Sin un slot válido responde con un
bloqueo explícito y no usa el último modelo. No usa `0.5` por defecto: ese
valor sólo es admisible cuando está publicado explícitamente y vinculado a la
calibración; nunca se usa como fallback.

Variables: `CELL_CLASSIFICATION_BATCH_SIZE`,
`CELL_CLASSIFICATION_REVIEW_MARGIN` y `CELL_CLASSIFICATION_PAGE_MAX`.

El esquema de esta API requiere la cadena Alembic
`20260728_01 → 20260728_02 → 20260728_03`. El endpoint de summary responde con
`automatic_summary` inmutable y `reviewed_summary` derivado. Las respuestas
públicas no incluyen storage keys, paths del checkpoint ni paths físicos; los
PNG Grad-CAM se descargan sólo mediante endpoints autenticados.
