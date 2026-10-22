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



Para usar YOLO:

1. YOLO_RUN_UUID: identificador utilizado para localizar el entrenamiento y sus pesos.
2. CELL_DETECTOR_KEY: yolo26_seg_v1 (Iniciar el servicio YOLO-DETECTOR) ó connected_components_v1 :: selecciona el adaptador de detección que utiliza el backend.

capstone % malaria_dl_local_project/.venv-metal/bin/python \
  smear_segmentation_project/runtime_yolo.py \
  --host 127.0.0.1 \
  --port 8765

En .env
CELL_DETECTOR_KEY=connected_components_v1 / yolo26_seg_v1
Después debes recrear el contenedor del backend para que cargue la nueva variable:
docker compose up -d --force-recreate backend

Ahora el servicio Es automatico, se dio acceso python del entorno .venv-metal.
Al ejecutar frontend Explain o CELL_DETECTOR_KEY=yolo26_seg_v1
Para entrenar YOL, si necesita el servicio.