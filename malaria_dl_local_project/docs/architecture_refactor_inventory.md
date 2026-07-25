# Inventario previo a la migración

Se encontraron imports `src.*` en pruebas, backend y scripts; comandos
`python -m src.*`; ajustes de `sys.path`; y rutas basadas en `__file__`.
Esto exige adaptadores temporales.

| Archivo actual | Responsabilidades | Destino propuesto | Símbolos públicos | Consumidores | Riesgo |
|---|---|---|---|---|---|
| `src/train.py` | CLI, callbacks, artifacts, tracking, entrenamiento | `training/trainer.py`, `cli.py` | `main`, `parse_args`, helpers | tests/CLI | Alto |
| `src/evaluate.py` | evaluación y lineage | `evaluation/evaluator.py` | `main`, helpers | tests/CLI | Alto |
| `src/explain.py` | casos, Grad-CAM, LIME, SHAP | `explainability/pipeline.py` | helpers, `main` | tests | Alto |
| `src/predict_image.py` | inferencia clínica | `inference/predictor.py` | `run_clinical_inference` | tests/backend | Alto |
| `src/models.py` | arquitecturas, métricas, optimizers | `models/*` | builders/custom objects | checkpoints | Crítico |
| `src/metrics.py` | métricas clínicas | `evaluation/clinical_metrics.py` | métricas | TRAIN/EVALUATE | Crítico |
| `src/data.py` | físico/TFDS/augmentations | `data/loaders.py` | loaders | pipelines | Alto |
| `src/checkpoint_policy.py` | selección y callbacks | `training/checkpoint_policy.py` | políticas | TRAIN | Crítico |
| `src/run_tracker.py` | persistencia de runs | `persistence/run_repository.py` | logging | pipelines | Alto |
| `src/tracking_integration.py` | fachada tracking | `persistence/tracking.py` | tracking | pipelines | Alto |
| `src/run_lineage.py` | lineage | `persistence/lineage.py` | resolución | EVALUATE/EXPLAIN | Alto |
| `src/model_governance/*` | entidades, SQL, SHA/releases | `governance/*` | dominio/repositorio | servicios | Crítico |
| `src/model_deployment_service.py` | deployment/alias/smoke | `governance/services/deployment_service.py` | servicio | backend | Crítico |
| `src/model_contract_service.py` | contrato | `governance/services/contract_service.py` | servicio | backend | Alto |
| `src/prepare_model_release_service.py` | promoción | `governance/services/prepare_release_service.py` | servicio | backend | Crítico |
| `src/stage2_model_availability_service.py` | Etapa 2 | `governance/services/stage2_availability_service.py` | servicio | backend/frontend | Crítico |
| `src/traceable_inference.py` | caché/inferencia gobernada | `inference/traceable.py` | cache/servicio | backend | Crítico |

No se identificó necesidad de alterar PostgreSQL ni checkpoints.

