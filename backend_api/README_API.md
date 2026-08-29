# Backend API

API FastAPI para consultar y operar los dominios gobernados de Capstone.

## Configuracion

La API de gobierno comparte el runtime Python 3.12 y ML del servicio `backend`.
Compose inyecta una única `DATABASE_URL`, validada para `db:5432`. El datasource
funcional soportado es `malaria` y no selecciona una conexión alternativa.

## Ejecutar

```bash
docker compose up -d
make db-status
```

El backend no se inicia desde un entorno Python del host como flujo oficial.

## Tests

```bash
make test-backend
```

Las pruebas PostgreSQL aisladas usan el marker `requires_docker_postgres` y el mismo
servicio `db`; las suites sin rollback completo permanecen bloqueadas.

## Endpoints

Todos aceptan `?datasource=malaria` de forma opcional.

```text
GET /health
GET /datasources
GET /dashboard/summary
GET /dashboard/clinical
GET /runs
GET /runs/grouped-lineage
GET /runs/{run_id}
GET /runs/clinical/summary
GET /runs/{run_id}/clinical-summary
GET /runs/{run_id}/checkpoint-policy
GET /runs/{run_id}/threshold-calibration
GET /runs/{run_id}/artifacts
GET /runs/{run_id}/image-predictions
GET /runs/{run_id}/explainability
GET /models
GET /models/comparison
GET /datasets
GET /api/dataset
GET /api/dataset/summary
GET /api/dataset/split
GET /api/dataset/images
GET /api/dataset/images/{image_id}
GET /api/dataset/images/{image_id}/file
GET /metrics/{run_id}
GET /confusion-matrix/{run_id}
GET /classification-report/{run_id}
GET /explainability
GET /explainability/cases
GET /explainability/cases/false-positives
GET /explainability/cases/false-negatives
GET /explainability/cases/low-confidence
GET /explainability/cases/summary
GET /explainability/gallery
GET /predictions/uploads
GET /errors
GET /logs
GET /artifacts/file?path=outputs/explainability/...
```

Los endpoints de casos aceptan filtros opcionales como `model_name`, `dataset_name`, `method`, `case_type`, `run_id`, `true_label`, `predicted_label`, `threshold_source`, `success`, `date_from`, `date_to`, `limit` y `offset`. Las fechas usan ISO-8601; cuando `date_to` contiene solo una fecha, se incluye el dia completo.

Los endpoints `/explainability/cases`, sus subconjuntos, `/explainability/gallery` y `/runs/{run_id}/explainability` leen `vw_visual_explainability_audit`. Cada caso agrega URLs relativas y codificadas para imagen, fuente, crop y explicacion, junto con probabilidades binarias, confianza, interpretacion y campos futuros de trazabilidad de imagen completa. Los campos no disponibles se devuelven como `null`.

`/runs/{run_id}/explainability` conserva la consulta exacta para un EXPLAIN y también
resuelve por `run_lineage` los EXPLAIN hijos de TRAIN o el sibling gobernado de un
EVALUATE. El cruce de EVALUATE exige la misma Dataset Version y prioriza
`model_version_id`, luego `checkpoint_artifact_id` y finalmente un checkpoint path no
nulo; nunca elige por recencia. `compact=true` evita metadata cruda duplicada y está
destinado a la tabla de detalle. `available` en las URLs significa que el archivo es
resoluble y servible; no acredita por sí solo que su checksum histórico coincida.

`GET /predictions/uploads` lista imagenes externas evaluadas con `src.predict_image --track-db`. Acepta filtros `model_name`, `predicted_label`, `limit` y `offset`. La respuesta incluye `probability_parasitized`, `probability_uninfected`, `confidence_level`, `decision`, `tta`, `n_aug` y datos de explicabilidad si existen.

`GET /api/dataset/images` acepta `split`, `class_name`, `page` y `page_size`. El endpoint de archivo de dataset solo resuelve imágenes por `image_id` y valida que estén dentro de `data/malaria_physical_split`.

El endpoint de artefactos solo sirve `.png`, `.jpg`, `.jpeg` y `.webp` dentro de `malaria_dl_local_project/outputs`, `malaria_dl_local_project/data`, `data` y `data/prediction_uploads`. Resuelve rutas reales antes de validar sus raices para bloquear traversal y symlinks que escapen del proyecto.

Los endpoints clinicos usan la convencion `0 = uninfected`, `1 = parasitized` y
`raw_model_score = probability_parasitized`. `GET /runs/{run_id}/clinical-summary`
devuelve metricas clinicas, matriz de confusion, checkpoint policy, threshold
calibrado, conteo de artefactos y conteo de predicciones por imagen.

`GET /runs/grouped-lineage?limit=100` devuelve los trainings recientes como
`items[]`. Cada item contiene `training`, `evaluations[]` y
`explainability[]`. Las evaluaciones incluyen metricas clinicas y matriz de
confusion; los runs de explicabilidad se deduplican por `run_id`, exponen
`methods[]` y suman `total_explanations`, `success_count` y `failed_count` por
metodo. Los runs evaluation/explainability sin parent valido se entregan en
`unlinked`, y los children asociados a mas de un training se excluyen de los
arboles y se informan en `conflicts` con `candidate_training_run_ids`. `totals`
resume las colecciones. El parametro `limit` acepta valores entre 1 y 500
y se aplica a los trainings; no oculta runs sin linaje.
