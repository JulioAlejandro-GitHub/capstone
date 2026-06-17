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
```

La inicialización es idempotente: usa `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `CREATE OR REPLACE VIEW` e inserciones semilla con `WHERE NOT EXISTS`.

## Probar conexión e inserción

```bash
python scripts/test_db.py
```

La prueba crea o recupera experimento, dataset y modelo de smoke test; luego registra una ejecución, métricas, matriz de confusión, reportes, predicción, artefacto, explicabilidad, paquetes del entorno y consulta `vw_run_dashboard`.

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

Estas vistas quedan preparadas para alimentar un dashboard web futuro sin acoplar todavía el frontend.

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
