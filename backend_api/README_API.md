# Backend API

API FastAPI de solo lectura para consultar el tracking PostgreSQL del proyecto Capstone.

## Configuracion

```bash
cd backend_api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Datasource activo por defecto:

```text
postgresql://julio@localhost:5432/malaria_experiments
```

Los datasources `bacteria` y `anemia` quedan configurados pero inactivos hasta habilitarlos con:

```text
ENABLE_BACTERIA_DATASOURCE=true
ENABLE_ANEMIA_DATASOURCE=true
```

## Ejecutar

```bash
uvicorn app.main:app --reload --port 8000
```

## Tests

El entorno actual no instala `pytest` en `backend_api/.venv`. Los tests backend
incluidos se pueden ejecutar con:

```bash
python -m unittest discover -s tests
```

## Endpoints

Todos aceptan `?datasource=malaria` de forma opcional.

```text
GET /health
GET /datasources
GET /dashboard/summary
GET /dashboard/clinical
GET /runs
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

`GET /predictions/uploads` lista imagenes externas evaluadas con `src.predict_image --track-db`. Acepta filtros `model_name`, `predicted_label`, `limit` y `offset`. La respuesta incluye `probability_parasitized`, `probability_uninfected`, `confidence_level`, `decision`, `tta`, `n_aug` y datos de explicabilidad si existen.

`GET /api/dataset/images` acepta `split`, `class_name`, `page` y `page_size`. El endpoint de archivo de dataset solo resuelve imágenes por `image_id` y valida que estén dentro de `data/malaria_physical_split`.

El endpoint de artefactos solo sirve `.png`, `.jpg`, `.jpeg` y `.webp` dentro de `malaria_dl_local_project/outputs`, `malaria_dl_local_project/data`, `data` y `data/prediction_uploads`. Resuelve rutas reales antes de validar sus raices para bloquear traversal y symlinks que escapen del proyecto.

Los endpoints clinicos usan la convencion `0 = uninfected`, `1 = parasitized` y
`raw_model_score = probability_parasitized`. `GET /runs/{run_id}/clinical-summary`
devuelve metricas clinicas, matriz de confusion, checkpoint policy, threshold
calibrado, conteo de artefactos y conteo de predicciones por imagen.
