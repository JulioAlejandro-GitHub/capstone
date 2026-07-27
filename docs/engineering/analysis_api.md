# API de análisis de frotis

Router autenticado `/api/v1/analysis`:

- `GET /eligible-batches`: filtros y paginación.
- `POST /runs`: congela un lote elegible.
- `POST /runs/{id}/quality-assessment`: evaluación síncrona en threadpool.
- `GET /runs` y `GET /runs/{id}`: lista y detalle trazable.
- `GET /runs/{id}/events`: eventos cronológicos paginados.
- `POST /runs/{id}/quality-decision`: revisión de warnings.

La idempotencia devuelve el run activo equivalente; para uno terminado responde
409 e incluye su `run_code`. NIH-NLM exige lote complete con cinco imágenes.
Las respuestas no exponen `storage_key` ni rutas absolutas.
