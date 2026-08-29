# Backend API

Runtime soportado: Python 3.12 dentro del servicio Docker Compose `backend`. Auth se
expone en `/api/v1/auth`, liveness en `/health` y readiness en `/ready`.

## Ejecución

```bash
docker compose up -d
docker compose ps
make db-status
make test-backend
```

El backend recibe exclusivamente `DATABASE_URL` desde Compose y se conecta al servicio
`db:5432`. El parámetro funcional `datasource=malaria` no selecciona otra conexión.
No se soporta iniciar el backend con Python del host para acceder a PostgreSQL.

La cadena Alembic versionada se incluye en la imagen, pero los comandos de migración
permanecen pendientes de habilitación hasta Prompt 1B.1 porque el override actual oculta
los mounts necesarios.

## Capacidades

`/api/v1/scientific` ofrece registro, consulta, actualización, archivado y trazabilidad
con JWT, RBAC y auditoría atómica. `/api/v1/analysis` expone análisis microscópico y
`/api/v1/cell-classification` resuelve exclusivamente la publicación Stage 2 activa.
Las respuestas públicas no incluyen rutas físicas ni secretos.

Contrato PostgreSQL: [documento canónico](../docs/engineering/postgresql_docker_single_instance.md).
