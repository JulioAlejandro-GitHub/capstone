# Frontend Clinical Dashboard

El frontend React/Vite permite auditar el flujo clinico experimental completo desde `backend_api`.

Advertencia obligatoria: este sistema es experimental y esta destinado a apoyar el analisis de imagenes. No reemplaza la validacion de especialistas ni constituye diagnostico clinico definitivo.

## Convencion Clinica

```text
0 = uninfected
1 = parasitized
clase positiva = parasitized
raw_model_score = probability_parasitized
probability_parasitized >= threshold -> parasitized
probability_parasitized < threshold  -> uninfected
```

La interfaz usa frases como:

```text
sistema experimental de apoyo
compatible con celula parasitada
compatible con celula no parasitada
probabilidad estimada
explicacion visual experimental
```

No debe presentar resultados como diagnostico definitivo.

## Pantallas

- `Dashboard`: resumen general y bloque clinico del ultimo run con F2, PR-AUC, recall, specificity, balanced accuracy, threshold y alertas.
- `Evaluacion clinica`: tabla de runs clinicos desde `vw_clinical_run_summary`.
- `Runs`: listado operativo de ejecuciones.
- `Run Detail`: auditoria por run con metricas clinicas, checkpoint policy, threshold clinico, matriz de confusion, predicciones por imagen, artefactos, explicabilidad y parametros.
- `Model Comparison`: comparacion clinica por run y resumen historico por modelo.
- `Dataset`: fuente, split fisico 80/10/10, conteos por clase e imagenes paginadas desde PostgreSQL.
- `Explainability`: casos Grad-CAM/LIME/SHAP con `probability_parasitized`, `threshold_used`, `threshold_source`, `case_type`, imagen y artefacto.
- `Predicciones subidas`: inferencias externas registradas con `src.predict_image --track-db`.

## Backend Consumido

Endpoints principales:

```text
GET /dashboard/clinical
GET /runs/clinical/summary
GET /runs/{run_id}/clinical-summary
GET /runs/{run_id}/checkpoint-policy
GET /runs/{run_id}/threshold-calibration
GET /runs/{run_id}/artifacts
GET /runs/{run_id}/image-predictions
GET /runs/{run_id}/explainability
GET /models/comparison
GET /api/dataset/summary
GET /api/dataset/images
GET /explainability/cases
GET /predictions/uploads
```

Las respuestas leen vistas/tablas PostgreSQL:

```text
vw_clinical_run_summary
vw_checkpoint_policy_summary
vw_threshold_calibration_summary
vw_run_artifacts_summary
vw_run_image_predictions_summary
vw_dataset_browser_summary
vw_dataset_browser_images
vw_case_level_explainability
```

## Flujo Completo

1. Crear split fisico.
2. Registrar dataset en PostgreSQL.
3. Entrenar con metricas clinicas.
4. Seleccionar checkpoint con politica clinica.
5. Calibrar threshold con validation.
6. Evaluar test con `--threshold clinical`.
7. Inferir imagen externa.
8. Revisar resultados en frontend.
9. Revisar explicabilidad.
10. Auditar en PostgreSQL.

## Comandos

Inicializar BD:

```bash
python scripts/init_db.py
python scripts/test_db.py
```

Crear split fisico:

```bash
python scripts/create_physical_dataset_split.py \
  --seed 42 \
  --train-ratio 0.8 \
  --val-ratio 0.1 \
  --test-ratio 0.1
```

Registrar split en BD:

```bash
python scripts/register_physical_split_in_db.py \
  --dataset-dir data/malaria_physical_split \
  --dataset-name malaria_physical_split \
  --dataset-source tensorflow_datasets/malaria \
  --source-url https://www.tensorflow.org/datasets/catalog/malaria \
  --execute
```

Entrenar:

```bash
python -m src.train \
  --model custom_cnn \
  --epochs 30 \
  --img-size 200 \
  --batch-size 64 \
  --checkpoint-policy auc_with_min_recall \
  --min-recall 0.98 \
  --calibrate-threshold \
  --target-recall 0.98 \
  --track-db
```

Evaluar:

```bash
python -m src.evaluate \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --threshold clinical \
  --track-db
```

Inferir imagen externa:

```bash
python -m src.predict_image \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --image-path path/to/image.png \
  --threshold clinical \
  --explain gradcam \
  --track-db
```

Backend:

```bash
cd backend_api
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## SQL Util

```sql
SELECT *
FROM vw_clinical_run_summary
ORDER BY started_at DESC
LIMIT 20;
```

```sql
SELECT *
FROM vw_checkpoint_policy_summary
WHERE run_id = '<run_uuid>';
```

```sql
SELECT *
FROM vw_threshold_calibration_summary
WHERE run_id = '<run_uuid>';
```

```sql
SELECT *
FROM vw_run_image_predictions_summary
WHERE run_id = '<run_uuid>'
ORDER BY case_type, filename;
```

```sql
SELECT *
FROM vw_run_artifacts_summary
WHERE run_id = '<run_uuid>';
```

## Validacion Frontend

El proyecto actualmente no define `npm test` ni `npm run lint`. La validacion disponible es:

```bash
npm run build
```

Ese comando ejecuta TypeScript y build Vite.
