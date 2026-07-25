# Mapa de migración

| Ubicación antigua | Ubicación canónica | Adaptador heredado | Consumidores actualizados | Estado |
|---|---|---|---|---|
| `src/config.py` | `malaria_dl/config/settings.py` | Sí | paquete canónico | Migrado |
| `src/data.py`, `preprocessing.py`, `dataset_registry.py` | `malaria_dl/data/*` | Sí | paquete canónico | Migrado |
| `src/models.py` | `malaria_dl/models/*` | Sí | registry/custom objects | Migrado |
| `src/train.py` | `malaria_dl/training/trainer.py` | Sí | CLI canónica | Migrado |
| `src/evaluate.py`, `metrics.py`, calibración | `malaria_dl/evaluation/*` | Sí | CLI/pipelines | Migrado |
| `src/explain.py` | `malaria_dl/explainability/pipeline.py` | Sí | CLI canónica | Migrado |
| `src/predict_image.py`, inferencia | `malaria_dl/inference/*` | Sí | backend/CLI | Migrado |
| tracking, DB y lineage | `malaria_dl/persistence/*` | Sí | imports históricos | Migrado |
| gobernanza y servicios raíz | `malaria_dl/governance/*` | Sí | backend/scripts | Migrado |

