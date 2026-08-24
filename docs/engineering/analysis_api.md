# API de análisis de frotis

Router autenticado `/api/v1/analysis`:

- `GET /eligible-batches`: filtros y paginación.
- `POST /runs`: congela un lote elegible.
- `POST /runs/{id}/quality-assessment`: evaluación síncrona en threadpool.
- `GET /runs` y `GET /runs/{id}`: lista y detalle trazable.
- `GET /runs/{id}/events`: eventos cronológicos paginados.
- `POST /runs/{id}/quality-decision`: revisión de warnings.
- `POST /queue`: agrega manualmente un run a la cola de quality assessment.
- `GET /queue`: lista por estado, prioridad e identidad científica.
- `POST /queue/{queue_item_id}/execute`: ejecuta manual y síncronamente el item
  en el threadpool.
- `POST /queue/{queue_item_id}/retry`: vuelve a `queued` un item fallido con
  prioridad explícita.

La idempotencia devuelve el run activo equivalente; para uno terminado responde
409 e incluye su `run_code`. NIH-NLM exige lote complete con cinco imágenes.
Las respuestas no exponen `storage_key` ni rutas absolutas.

La cola actual es una agenda PostgreSQL controlada por API; no implica worker,
lease, heartbeat, polling automático ni `FOR UPDATE SKIP LOCKED`. Crear,
consultar, ejecutar y reintentar usan permisos `scientific.analysis.queue.*`
separados.
