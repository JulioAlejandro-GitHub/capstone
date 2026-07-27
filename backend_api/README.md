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
