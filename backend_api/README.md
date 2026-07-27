# Backend API

Runtime soportado: Python 3.12. Configure mediante las variables de la raíz, instale
`requirements.txt` y ejecute `PYTHONPATH=backend_api uvicorn app.main:app`. Auth está en
`/api/v1/auth`; liveness en `/health` y readiness en `/ready`.

`/api/v1/scientific` ofrece registro, consulta, actualización, archivado y trazabilidad
con JWT, RBAC y auditoría atómica. No carga binarios ni admite DELETE físico. Requiere la
revisión Alembic `20260727_01`.
# Ejecución local

```bash
PYTHONPATH=backend_api backend_api/.venv/bin/uvicorn app.main:app --reload
```

Requiere `APP_ENV=development`, `DATABASE_URL` y `JWT_SECRET` privados. Docker no es parte
del flujo oficial.

Prompt 4 agrega multipart por streaming, validación Pillow, SHA-256 backend-only,
lotes científicos y contenido autenticado. Use las variables de `.env.example`.
# Microscopy analysis API

`/api/v1/analysis` expone lotes elegibles, runs congelados, evaluaciones
técnicas, eventos y decisiones auditadas. Requiere PostgreSQL y storage local.
