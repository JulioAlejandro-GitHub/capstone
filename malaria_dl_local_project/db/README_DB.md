# Base de datos de experimentos ML

Este proyecto queda preparado para registrar ejecuciones, parámetros, métricas, artefactos, explicabilidad, errores y entorno de ejecución en PostgreSQL local.

## Supuesto

PostgreSQL 17.9 está instalado y ejecutándose en `localhost`.

Configuración por defecto:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=malaria_experiments
DB_USER=postgres
DB_PASSWORD=postgres
DB_SCHEMA=public
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/malaria_experiments
```

No se usa Docker en esta iteración.

## Crear base de datos si no existe

```bash
createdb -h localhost -p 5432 -U postgres malaria_experiments
```

## Copiar variables de entorno

Desde la raíz del proyecto `malaria_dl_local_project`:

```bash
cp .env.example .env
```

Edita `.env` si tu usuario, contraseña, puerto o nombre de base son distintos.

## Inicializar esquema

```bash
python scripts/init_db.py
```

El script ejecuta en orden:

```text
db/init/001_schema.sql
db/init/002_indexes.sql
db/init/003_views.sql
db/init/004_seed.sql
db/init/007_case_level_explainability_views.sql
db/init/008_case_level_explainability_indexes.sql
```

También ejecuta automáticamente otros archivos numerados `NNN_*.sql` si existen, por ejemplo `005_frontend_views.sql` o `006_frontend_indexes.sql`.

La inicialización es idempotente: usa `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `CREATE OR REPLACE VIEW` e inserciones semilla con `WHERE NOT EXISTS`.

## Probar conexión e inserción

```bash
python scripts/test_db.py
```

La prueba crea o recupera experimento, dataset y modelo de smoke test; luego registra una ejecución, métricas, matriz de confusión, reportes, predicción, artefacto, explicabilidad, paquetes del entorno y consulta `vw_run_dashboard`.

## Tracking automático de ejecuciones reales

Los scripts principales aceptan `--track-db`. La bandera está desactivada por defecto, por lo que ejecutar los comandos sin `--track-db` mantiene el comportamiento anterior.

Entrenamiento con tracking:

```bash
python -m src.train --model custom_cnn --epochs 30 --img-size 200 --batch-size 64 --track-db
```

Evaluación con tracking:

```bash
python -m src.evaluate --checkpoint outputs/vgg16/best_model.keras --img-size 200 --batch-size 64 --track-db
```

Explicabilidad con tracking:

```bash
python -m src.explain --checkpoint outputs/vgg16/best_model.keras --method gradcam --num-samples 20 --track-db
```

También se agregó tracking opcional a:

```bash
python -m src.svm_features --checkpoint outputs/vgg16/best_model.keras --track-db
python -m src.ensemble --models outputs/custom_cnn/best_model.keras outputs/vgg16/best_model.keras --track-db
python -m src.tta --checkpoint outputs/vgg16/best_model.keras --track-db
```

Si PostgreSQL no está disponible, el tracking emite un warning y el script continúa con su lógica normal. Si ocurre un error real del entrenamiento, evaluación o explicabilidad, el error se registra en la tabla `errors` cuando exista un `run_id`, y luego el script vuelve a fallar como antes.

Consultas para validar ejecuciones reales:

```sql
SELECT *
FROM vw_run_dashboard
ORDER BY started_at DESC
LIMIT 10;
```

```sql
SELECT model_name, total_runs, completed_runs, failed_runs
FROM vw_model_run_summary
ORDER BY total_runs DESC;
```

```sql
SELECT *
FROM vw_explainability_summary;
```

## Conectarse usando psql

```bash
psql -h localhost -p 5432 -U postgres -d malaria_experiments
```

## Ver tablas

```sql
\dt
```

## Ver vistas

```sql
\dv
```

## Tablas principales

- `experiments`: familias de experimentos o líneas de trabajo.
- `datasets`: datasets usados, origen, versión, distribución de clases y metadatos.
- `dataset_splits`: splits de entrenamiento, validación y test.
- `models`: modelos disponibles, arquitectura, framework y metadata técnica.
- `runs`: tabla central; cada ejecución realizada por entrenamiento, evaluación, explicabilidad, TTA, ensemble u otro flujo.
- `model_versions`: checkpoints y versiones concretas de modelos.
- `run_metrics`: métricas numéricas por run, split, clase, epoch o step.
- `training_history`: evolución por epoch durante entrenamiento.
- `confusion_matrices`: matrices de confusión y conteos TP/TN/FP/FN.
- `classification_reports`: precision, recall, F1 y support por clase.
- `predictions`: predicciones individuales, score, clase real, clase predicha y tipo de caso.
- `artifacts`: rutas a artefactos generados. No almacena binarios.
- `explainability_results`: resultados de LIME, SHAP y Grad-CAM.
- `execution_logs`: mensajes de ejecución asociados a un run.
- `errors`: errores, stack traces y script de origen.
- `environment_packages`: paquetes Python registrados por ejecución.
- `synthetic_data_runs`: soporte futuro para generación de datos sintéticos.

## Vistas para futuro frontend

- `vw_model_run_summary`: resumen por modelo, cantidad de ejecuciones, completadas, fallidas y mejores métricas.
- `vw_run_dashboard`: vista plana por ejecución con modelo, dataset, duración y métricas principales.
- `vw_explainability_summary`: conteos de explicaciones por método, éxito, error y tipo de caso.
- `vw_case_level_explainability`: detalle por imagen explicada, uniendo explicación, predicción, run, modelo, dataset y artefacto.
- `vw_false_positive_cases`: falsos positivos caso a caso.
- `vw_false_negative_cases`: falsos negativos caso a caso.
- `vw_low_confidence_cases`: predicciones cercanas al umbral de decisión.
- `vw_case_type_summary`: resumen por modelo, dataset, método y tipo de caso.
- `vw_explainability_gallery`: galería de imágenes explicadas con rutas de artefactos.

Estas vistas quedan preparadas para alimentar un dashboard web futuro sin acoplar todavía el frontend.

## Consultas caso a caso de explicabilidad

### Ver falsos positivos caso a caso

```sql
SELECT
    run_id,
    model_name,
    dataset_name,
    method,
    true_label,
    predicted_label,
    positive_label,
    score_positive_label,
    threshold,
    image_path,
    explanation_output_path,
    last_conv_layer,
    started_at
FROM vw_false_positive_cases
ORDER BY started_at DESC, score_positive_label DESC;
```

### Ver falsos negativos caso a caso

```sql
SELECT
    run_id,
    model_name,
    dataset_name,
    method,
    true_label,
    predicted_label,
    positive_label,
    score_positive_label,
    threshold,
    image_path,
    explanation_output_path,
    last_conv_layer,
    started_at
FROM vw_false_negative_cases
ORDER BY started_at DESC, score_positive_label ASC;
```

### Ver casos de baja confianza

```sql
SELECT
    run_id,
    model_name,
    dataset_name,
    method,
    true_label,
    predicted_label,
    score_positive_label,
    threshold,
    confidence_distance,
    image_path,
    explanation_output_path
FROM vw_low_confidence_cases
ORDER BY confidence_distance ASC;
```

### Resumen por tipo de caso

```sql
SELECT
    model_name,
    dataset_name,
    method,
    case_type,
    total_cases,
    ROUND(avg_score::numeric, 4) AS avg_score
FROM vw_case_type_summary
ORDER BY model_name, method, case_type;
```

### Galería de explicabilidad

```sql
SELECT
    gallery_id,
    run_id,
    model_name,
    dataset_name,
    method,
    case_type,
    true_label,
    predicted_label,
    score_positive_label,
    image_path,
    explanation_output_path
FROM vw_explainability_gallery
ORDER BY started_at DESC
LIMIT 100;
```

## Consultas SQL útiles

### Cantidad de ejecuciones por modelo

```sql
SELECT model_name, total_runs
FROM vw_model_run_summary
ORDER BY total_runs DESC;
```

### Mejores ejecuciones por AUC

```sql
SELECT *
FROM vw_run_dashboard
ORDER BY auc DESC NULLS LAST
LIMIT 10;
```

### Ejecuciones fallidas

```sql
SELECT id, run_name, script_name, started_at, status
FROM runs
WHERE status = 'failed'
ORDER BY started_at DESC;
```

### Resultados de explicabilidad por método

```sql
SELECT method, COUNT(*)
FROM explainability_results
GROUP BY method;
```

### Últimas ejecuciones

```sql
SELECT *
FROM vw_run_dashboard
ORDER BY started_at DESC
LIMIT 20;
```

## Integración futura

La integración con `src.train`, `src.evaluate`, `src.svm_features`, `src.ensemble`, `src.tta` y `src.explain` debe hacerse en una siguiente iteración usando `src.run_tracker`.

El diseño ya soporta:

- historial de ejecuciones;
- cantidad de ejecuciones por modelo;
- parámetros usados;
- resultados obtenidos;
- métricas comparativas;
- artefactos generados;
- imágenes explicadas;
- errores y logs;
- evolución del desempeño del sistema.
