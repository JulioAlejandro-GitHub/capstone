# Tracking Clinico de Runs en PostgreSQL

Este documento describe el registro incremental de entrenamiento, evaluacion e inferencia en PostgreSQL.

La convencion clinica oficial es:

```text
0 = uninfected
1 = parasitized
clase positiva = parasitized
raw_model_score = probability_parasitized
threshold aplicado sobre probability_parasitized
label_mapping_version = clinical_v1_parasitized_positive
```

## Migraciones

Aplicar o reaplicar migraciones:

```bash
python scripts/init_db.py
python scripts/init_db.py
```

`scripts/init_db.py` es idempotente y ejecuta `db/init/*.sql` en orden. Si una sentencia falla, reporta archivo, indice de sentencia y un preview del SQL.

La migracion incremental principal es:

```text
db/init/017_clinical_run_tracking.sql
```

Tambien se corrigieron las migraciones que recrean
`vw_clinical_inference_predictions` (`010` y `011`) para usar:

```sql
DROP VIEW IF EXISTS vw_clinical_inference_predictions CASCADE;
CREATE VIEW vw_clinical_inference_predictions AS ...
```

Esto evita fallas de PostgreSQL cuando cambia la estructura de columnas de la vista.

## Tablas Nuevas o Extendidas

`run_io_records` se extiende con:

- `run_type`
- `model_name`
- `model_metadata`
- `clinical_metadata`

Tablas especificas de tracking clinico:

- `run_clinical_metrics`: metricas clinicas por run/split, confusion matrix, reporte, distribucion de predicciones y diagnostico de colapso.
- `run_checkpoint_policy`: politica de seleccion de checkpoint, epoch elegido, metricas usadas, warnings y rutas de artefactos.
- `run_threshold_calibration`: threshold seleccionado en validation, target recall, metricas asociadas y rutas de calibracion.
- `run_image_predictions`: predicciones por imagen para evaluacion, inferencia externa, TTA, ensemble o explicabilidad.

Tablas reutilizadas:

- `artifacts`
- `dataset_split_images`
- `run_dataset_images`
- `predictions`

## Vistas

Vistas principales:

- `vw_clinical_run_summary`
- `vw_checkpoint_policy_summary`
- `vw_threshold_calibration_summary`
- `vw_run_artifacts_summary`
- `vw_run_image_predictions_summary`
- `vw_clinical_inference_predictions`

Consultas utiles:

```sql
SELECT *
FROM vw_clinical_run_summary
ORDER BY started_at DESC NULLS LAST
LIMIT 20;
```

```sql
SELECT *
FROM vw_run_image_predictions_summary
WHERE run_id = '<run_uuid>'
ORDER BY created_at DESC;
```

```sql
SELECT *
FROM vw_threshold_calibration_summary
WHERE threshold_source = 'validation_calibration'
ORDER BY created_at DESC;
```

## Integracion Python

El modulo `src.tracking_integration` expone wrappers tolerantes a fallos:

- `record_run_io`
- `record_clinical_metrics`
- `record_checkpoint_policy`
- `record_threshold_calibration`
- `record_output_artifacts`
- `record_image_predictions`

Estos wrappers llaman a `src.run_tracker` mediante `safe_track`, por lo que una falla de PostgreSQL no debe romper entrenamiento o inferencia.

Flujos integrados:

- `src.train`
- `src.evaluate`
- `src.predict_image`
- `src.tta`
- `src.ensemble`
- `src.svm_features`
- `src.explain`

Ejemplo:

```bash
python -m src.evaluate \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --threshold clinical \
  --track-db
```

## Smoke Test

Validar conexion, inserciones basicas, tablas nuevas y vistas:

```bash
python scripts/test_db.py
```

Este script crea un run sintetico, registra metricas clinicas, politica de checkpoint, calibracion de threshold, predicciones por imagen, artefactos e IO, y luego consulta las vistas nuevas.

## Backend

Endpoints de lectura agregados:

```text
GET /runs/clinical/summary
GET /runs/{run_id}/clinical-metrics
GET /runs/{run_id}/checkpoint-policy
GET /runs/{run_id}/threshold-calibration
GET /runs/{run_id}/artifacts-summary
GET /runs/{run_id}/image-predictions
GET /runs/{run_id}/io-records
```

Estos endpoints leen las vistas/tablas de tracking y aceptan `datasource=malaria` por defecto.
