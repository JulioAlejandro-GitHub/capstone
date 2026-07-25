# Auditoría inicial de archivos obsoletos

Fecha: 2026-07-25  
Rama: `chore/remove-obsolete-files`  
Commit base: `8f3988d6`

## Alcance y método

Se inventariaron los 418 archivos versionados con `git ls-files` (72.081
líneas de archivos de texto). La evaluación combinó:

- imports y exports Python y TypeScript, incluidos adaptadores y CLI;
- routers FastAPI y rutas React;
- comandos de `package.json`, shell, README y documentación operativa;
- migraciones y bootstrap SQL;
- rutas de artefactos, manifiestos, checksums y checkpoints del release;
- tests, fixtures y scripts ejecutables;
- búsquedas de carga dinámica, `importlib`, `subprocess` y rutas persistidas.

No existen en el árbol versionado Dockerfile, Docker Compose, Makefile,
GitHub Actions, Alembic, Redis, Celery ni una implementación de worker. Por
ello no hay entrypoints de esas categorías que puedan alcanzar archivos.

## Entry points confirmados

| Área | Entry points |
|---|---|
| Backend | `backend_api/app/main.py`, ejecutado por Uvicorn mediante `scripts/start_backend_api.sh`; registra 11 routers |
| Frontend | `frontend/index.html` → `src/main.tsx` → `src/App.tsx`; rutas canónicas en `src/router.ts` |
| Entrenamiento | `python -m src.train`, `python -m src.malaria_dl.training.cli`, `run_train_all_models.py` |
| Evaluación | `python -m src.evaluate`, `python -m src.calibrate`, CLI canónica y `run_evaluate_all_trainings.py` |
| Inferencia | `python -m src.predict_image`, CLI canónica y servicio de inferencia trazable |
| Explicabilidad | `python -m src.explain`, CLI canónica y `run_explain_all_trainings.py` |
| Detección/crops | Frontera `src/malaria_dl/cell_detection`; no contiene todavía implementación ejecutable independiente |
| Base de datos | `scripts/init_db.py` aplica, en orden, `db/init/*.sql`; scripts de diagnóstico, backfill y purga |
| Pruebas | `pytest` en API y ML; `node --test tests/*.test.mjs` en frontend |
| Validación local | `scripts/validate.sh`; scripts E2E de gobernanza en `scripts/` |

## Inventario por categoría

| Grupo | Cantidad | Clasificación predominante | Justificación |
|---|---:|---|---|
| Fuente ML canónica | 73 | A/B | Implementación del pipeline y APIs internas |
| Adaptadores ML `src.*` | 43 | B/H | Compatibilidad pública de CLI, notebooks, tests y automatizaciones históricas |
| Pruebas ML | 73 | A/H | Caracterización, reproducibilidad y contratos del release |
| Migraciones SQL | 22 | H | Reconstrucción histórica y bootstrap ordenado |
| Fuente backend | 22 | A | Todos los routers están registrados; servicios consumidos |
| Pruebas backend | 9 | A | Contratos API y casos PostgreSQL |
| Fuente frontend | 63 | A, salvo candidato D | Páginas/rutas/componentes alcanzables desde `App.tsx` |
| Pruebas frontend | 7 | A | Contratos de navegación y producción |
| Artefactos del release | 18 | H | Manifiestos, checksums, modelos, mapping, threshold y firmas |
| Documentación | 51 | H/G | Evidencia académica, decisiones y runbooks; conservar ante duda |
| Scripts | 22 | A/B/G | Entrenamiento, migración, diagnóstico y verificación manual |
| Configuración/otros | 15 | A/H | Dependencias, entornos de ejemplo, locks y `.gitkeep` |

## Plan de eliminación

| Archivo | Clasificación | Evidencia de no uso | Reemplazado por | Riesgo | Acción |
|---|---|---|---|---|---|
| `frontend/src/components/reports/RunPromotionAction.tsx` | D — obsoleto reemplazado | Cero imports/exports consumidores; no aparece en `App.tsx`, rutas, lazy imports, configuración ni tests. Búsqueda global del nombre sólo encuentra el propio archivo y documentación histórica. | `RunSummaryRow.tsx` y detalle `Stage2ReleaseDetail.tsx` | Bajo | Eliminado y validado en la primera pasada |
| `frontend/src/components/reports/Stage2AvailabilityAction.tsx` | D — obsoleto reemplazado | El grafo de imports desde `main.tsx` no lo alcanza; no tiene importadores, rutas, lazy imports ni consumidores. `stage2-availability.test.mjs` exige explícitamente que el flujo vigente no use `Stage2AvailabilityAction`. Sus selectores `stage2-action*` y `stage2-blockers` son exclusivos. | Resumen integrado en `RunSummaryRow.tsx` y flujo completo en `Stage2ReleaseDetail.tsx` | Bajo | Eliminar junto con CSS exclusivo; ejecutar tests, typecheck, build y búsqueda global |

### Función histórica y efectos previstos

`RunPromotionAction.tsx` presentaba el flujo anterior de preparación y promoción
desde una tarjeta TRAIN. La UX actual concentra una única acción “Ver detalle”
en `RunSummaryRow` y el detalle de liberación. El componente antiguo dejó de
ser importado al introducirse ese flujo. Su eliminación no modifica CSS
compartido ni el tipo `TrainingPromotionStatus`, ambos usados por componentes
activos.

`Stage2AvailabilityAction.tsx` fue introducido como acción técnica intermedia,
pero el cambio posterior movió el estado resumido a `RunSummaryRow` y las
operaciones a `Stage2ReleaseDetail`. Su eliminación tampoco cambia el bundle:
Vite ya no lo incluye en el grafo productivo. Se retiene la regla compartida
`.stage2-kicker`; sólo se eliminan los selectores exclusivos del componente.

## Elementos conservados por seguridad

- Todos los adaptadores en `malaria_dl_local_project/src/*.py`: el contrato
  documentado soporta `python -m src.*`, y consumidores externos/manuales no
  pueden descartarse con seguridad.
- `case_selection.py`, `lime_explainer.py`, `shap_explainer.py`,
  `gradcam.py` y `custom_metrics.py`: son fachadas públicas o puntos de carga
  indirecta para explicabilidad/checkpoints, aunque algunos no tengan
  importadores internos.
- Todas las migraciones y copias SQL documentales: las migraciones son
  obligatorias; las copias superiores se conservan como evidencia hasta
  confirmar fuera del repositorio que no forman parte de procedimientos
  operativos.
- Todo `releases/`: contiene artefactos productivos y Stage 2, incluidos
  checksums y modelos; duplicación de contenido entre ambientes es intencional.
- README, informes, auditorías y documentos de arquitectura: constituyen
  evidencia académica o trazabilidad de decisiones.
- Archivos ignorados locales (`.env`, `.venv`, `node_modules`, `dist`,
  caches, imágenes subidas y `.DS_Store`): no están bajo control de versiones
  y las reglas prohíben eliminarlos como parte de esta limpieza.

## Candidatos ambiguos para revisión manual

| Candidato | Motivo de ambigüedad | Decisión |
|---|---|---|
| `docs/023_schema_migrations_baseline.sql`, `025_deployed_model_versions.sql`, `026_inference_jobs.sql`, `027_model_governance_backfill_constraints.sql` | Parecen copias de `malaria_dl_local_project/db/init/`, pero pueden ser anexos académicos o comandos usados manualmente | Conservar |
| `malaria_dl_local_project/README_2.md` | Documento anterior, todavía citado por auditorías y por una prueba de tracking | Conservar |
| `scripts/verify_four_step_production_e2e.py`, `verify_relaxed_technical_production_e2e.py`, `verify_stage2_availability_e2e.py` | Flujos superpuestos, pero representan verificaciones manuales de contratos distintos | Conservar |
| Fachadas finas bajo `src/malaria_dl/explainability/` y `models/custom_metrics.py` | Sin consumidores internos directos; pueden ser API pública/deserialización dinámica | Conservar |
| Documentos de etapas y diagnósticos previos | Algunos describen estados anteriores, pero registran decisiones, auditorías y evidencia académica | Conservar |

## Línea base previa a la eliminación

| Validación | Resultado inicial |
|---|---|
| Frontend tests | PASS — 58/58 |
| Frontend typecheck + build Vite | PASS — 97 módulos |
| Backend tests con `backend_api/.venv` | No ejecutable: el entorno no contiene `pytest` |
| Suite ML | En ejecución al registrar este inventario |
