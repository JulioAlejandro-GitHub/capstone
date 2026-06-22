# Reset Seguro Del Estado Experimental

Estos scripts permiten reiniciar el estado experimental antes de reentrenar modelos con una nueva convención de etiquetas.

Por seguridad, todos corren en `dry-run` por defecto. Ningún script elimina código fuente, datasets, configuración, scripts SQL ni estructura de base de datos.

## Qué Elimina Cada Script

`scripts/purge_db_data.py` elimina datos de tablas PostgreSQL mediante `TRUNCATE ... RESTART IDENTITY CASCADE`.

No elimina:

- schemas
- tablas
- índices
- vistas
- funciones
- `db/init/*.sql`
- `db/README_DB.md`

`scripts/clean_training_outputs.py` elimina artefactos generados en `outputs/`:

- modelos `.keras`, `.h5`
- modelos auxiliares `.joblib`, `.pkl`
- métricas `.json`
- predicciones y logs `.csv`
- imágenes de explicabilidad `.png`, `.jpg`, `.jpeg`, `.webp`
- subdirectorios generados de evaluación, TTA, ensemble, SVM, predicciones externas y explicabilidad

No elimina:

- `src/`
- `db/`
- `scripts/`
- `tests/`
- `data/`
- `.venv/`
- `README.md`
- `README_2.md`
- `requirements.txt`

## Purga De Base De Datos

Dry-run:

```bash
python scripts/purge_db_data.py
```

Ejecutar con backup:

```bash
python scripts/purge_db_data.py \
  --execute \
  --confirm PURGE_DB \
  --backup-before
```

Ejecutar y reinsertar seeds mínimos:

```bash
python scripts/purge_db_data.py \
  --execute \
  --confirm PURGE_DB \
  --backup-before \
  --reseed
```

El backup se guarda por defecto en:

```text
backups/db/backup_before_purge_YYYYMMDD_HHMMSS.sql
```

Si `pg_dump` no está disponible, el script falla de forma segura y no ejecuta la purga con `--backup-before`.

## Limpieza De Outputs

Dry-run:

```bash
python scripts/clean_training_outputs.py
```

Ejecutar con backup:

```bash
python scripts/clean_training_outputs.py \
  --execute \
  --confirm DELETE_OUTPUTS \
  --backup-before
```

El backup se guarda por defecto en:

```text
backups/outputs/outputs_before_clean_YYYYMMDD_HHMMSS.tar.gz
```

Después de limpiar, se recrea la estructura mínima:

```text
outputs/
outputs/custom_cnn/
outputs/vgg16/
outputs/cnn_features_svm/
outputs/ensemble/
outputs/explainability/
outputs/explainability/gradcam/
outputs/explainability/lime/
outputs/explainability/shap/
outputs/explainability/external_predictions/
outputs/explainability/external_predictions/gradcam/
outputs/predictions/
```

## Reset Completo

Dry-run:

```bash
python scripts/reset_experimental_state.py
```

Ejecutar DB + outputs con backup:

```bash
python scripts/reset_experimental_state.py \
  --execute \
  --confirm RESET_EXPERIMENTS \
  --backup-before
```

Opciones útiles:

```bash
python scripts/reset_experimental_state.py --skip-db
python scripts/reset_experimental_state.py --skip-outputs
python scripts/reset_experimental_state.py --execute --confirm RESET_EXPERIMENTS --backup-before --reseed
```

## Reinicializar Y Probar DB

Si necesitas reconstruir vistas, índices o seeds:

```bash
python scripts/init_db.py
python scripts/test_db.py
```

## Reentrenar Después De Limpiar

```bash
python -m src.train \
  --model custom_cnn \
  --epochs 30 \
  --img-size 200 \
  --batch-size 64 \
  --track-db
```

```bash
python -m src.train \
  --model vgg16 \
  --epochs 30 \
  --fine-tune-epochs 10 \
  --img-size 200 \
  --batch-size 64 \
  --track-db
```

## Tests

```bash
python -m pytest tests/test_clean_training_outputs.py
python -m pytest tests/test_purge_db_data.py
```

Los tests no conectan a PostgreSQL real ni eliminan `outputs/` real; usan mocks y directorios temporales.
