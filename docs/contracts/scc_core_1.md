# SCC-CORE.1 — Lectura científica compartida

Estado documental: `CURRENT_DOC` — implementación y verificación focalizada, 2026-10-15.

Base: rama `main`, HEAD `10a8f1adf7138bd9d4fa5093883175d3b9a88b27`. Cambios sin commit.

## Implementación y fuentes reutilizadas

Se consultaron CAPSTONE-REPORTS-01A y CAPSTONE-DATA-01A sin repetir sus auditorías. Las consultas actuales de `scientific_results_v2` se trasladaron desde el servicio a `repositories/scientific_results.py`; el servicio conserva sus exportaciones existentes y compone la lectura SCC. No se duplicaron esas consultas. El catálogo `/models` se extrajo a repositorio y servicio con inyección de dependencias. `AssessmentReadRepository` y `AssessmentReadService` siguen siendo la fuente de intentos y evidencia por muestra.

`assessment_lineage.py`, `lineage_children.py` y sus consumidores permanecen intactos. El contrato incluye la referencia al linaje existente para los hijos históricos representados por runs. Los intentos de assessments se leen íntegros, sin ranking ni selección del más reciente.

## Catálogo y configuración

`GET /models` conserva los campos de resumen existentes y añade `training_runs`, `has_training_runs`, `has_completed_training`, `training_evidence_status` y `comparison.scc_max_comparison_runs`.

La consulta parte de `models`, reutiliza `vw_model_run_summary` (verificada en PostgreSQL: parte de todos los modelos con LEFT JOIN a runs) y relaciona `runs.model_id = models.id`, con `run_type = 'training'`. No hay filtro por arquitectura. Varios TRAIN conservan sus UUID; un modelo sin TRAIN devuelve `[]` y ambos indicadores falsos. Tener un intento fallido no equivale a tener un entrenamiento completado.

`GET /models?datasource=malaria&view=traceability` limita el contexto a `model_type='classification'`, elimina localizadores físicos y excluye los agregados `best_*` del resumen histórico: esos agregados no acreditan un split científico único. Modelos de detección y segmentación quedan fuera de esta proyección. Una arquitectura nueva clasificada correctamente en PostgreSQL aparece automáticamente.

`SCC_MAX_COMPARISON_RUNS` se configura en `.env`, con ejemplo versionado en `.env.example`; `Settings` valida un entero >=1, con default 4 en un único punto del código. Compose ya carga `.env`. El frontend obtiene el valor efectivo de `/models`, sin fallback numérico propio. Cambios posteriores de la variable requieren recrear el servicio para recargar su entorno. El límite no recorta el catálogo ni los historiales; la selección simultánea y su validación corresponden a entregas UI/preflight posteriores.

## Contrato y endpoints

Las rutas públicas existentes se conservan. `view=traceability` opta por la proyección SCC sin alterar las respuestas predeterminadas de los reportes.

| Lectura | Contrato |
|---|---|
| `/runs/{training_run_id}/scientific-results?view=traceability` | `scc_core_1`: modelo, TRAIN, dataset versionado, evidencia, assessments, estados y referencias |
| `/assessments?training_run_id=…&view=traceability` | Historial paginado, `identity_id`, `attempt_id`, modelo, split, estado, ordinal, checkpoint y verificación |
| `/assessments/{attempt_id}?view=traceability` | Identidad científica completa y metadatos públicos del intento exacto |
| `/assessments/{attempt_id}/results?view=traceability` | Resultados por muestra, paginados y con procedencia del intento |
| `/assessments/{attempt_id}/artifacts?view=traceability` | Referencias por `artifact_id`, con procedencia y disponibilidad física no comprobada |
| `/runs/{id}/image-predictions?view=traceability` | Lectura histórica existente por run/split, sin localizadores físicos |
| `/runs/{id}/lineage-children` | Relación histórica de hijos, discriminada por tipo de fuente, sin cambios |

TRAIN devuelve las fuentes existentes: `run_configurations`, `training_history`, `evaluations`, `evaluation_ensemble_members`, `run_clinical_metrics`, `xai_evidence`, `xai_artifacts`, evaluaciones cuantitativas, interpretaciones y revisiones XAI. Añade `run_checkpoint_policy`, `run_metrics`, `artifacts`, `run_io_records`, `dataset_versions`, `model_versions` y una página de `predictions`.

`prediction_limit` (1–1000, default 100) y `prediction_offset` paginan `evidence.predictions`, que incluye `total`, `limit`, `offset`. Cada predicción conserva su ID, `evaluation_id`, identidad de registro del dataset y split de la evaluación acreditada. La consulta no busca un split alternativo cuando falta. Los resultados E6 se consultan por attempt, sin mezclar sus páginas con predicciones históricas. La colección de assessments incluida en TRAIN no está limitada a 50 ni al máximo de comparación; la lectura independiente de `/assessments` mantiene `limit/offset`.

Los métodos frontend `api.getScientificModels` y `api.scientificTraceability` comparten estas fuentes y contratos TypeScript. No se construyó una pantalla SCC ni se migraron secciones visuales de reportes.

## Identidades y separación científica

- `models.id`: modelo registrado; `runs.id`/`training_run_id`: TRAIN concreto.
- `assessment_identities.id`/`identity_id`: identidad científica; `assessment_attempts.id`/`attempt_id`: intento concreto. El campo histórico `id` se conserva por compatibilidad.
- `sample_id` identifica muestras E6; las predicciones históricas conservan sus propias claves `image_id`/`dataset_source_record_id`. No se inventa equivalencia entre esos dominios.
- `artifact_id` identifica evidencia; `dataset_version_id` identifica el dataset. Checkpoints se leen desde sus relaciones persistidas en política, versiones de modelo e identidades; no se elige el último ni se reconstruye uno.
- PostgreSQL actual representa TEST con `kind='evaluate'` y `identity.split='test'`. La proyección añade `assessment_type='TEST'`, preservando `kind`, split e identidad originales. EVALUATE sobre VAL permanece separado de TEST. EXPLAIN conserva su identidad y no se vincula a EVALUATE por semejanza.

Las métricas conservan su tabla, run/evaluation/attempt y split cuando está persistido. Métricas genéricas sin split acreditado siguen sin split; no son automáticamente comparables. No se agregan VAL y TEST ni se selecciona checkpoint usando TEST.

## Ausencia, errores y archivos

`available` indica registros disponibles; `not_persisted` indica una colección sin registros o sin verificación persistida. No prueba que el proceso nunca se ejecutara. El catálogo sin TRAIN declara `training_evidence_status=not_generated`; para intentos sin verificación, `generation_status=unknown` evita inventar la causa. Un estado failed/active/interrupted se conserva aunque existan resultados parciales.

La proyección elimina claves de almacenamiento, comandos y serializaciones canónicas con rutas, y oculta localizadores absolutos presentes en metadatos de extensión. Mantiene IDs y hashes. Las respuestas predeterminadas anteriores conservan sus campos para no romper reportes; los nuevos consumidores deben pedir `view=traceability`.

`file_availability=not_checked` separa registro y existencia física. No se ejecuta I/O masivo para certificar archivos. SCC-ART.1 deberá distinguir archivos disponibles, ausentes y errores de acceso; esta entrega no etiqueta un archivo como disponible por estar registrado. Tampoco evalúa soporte Grad-CAM, embeddings o CKA por el nombre del modelo.

Un UUID inexistente produce 404; un run que no es TRAIN o un modelo ajeno a clasificación produce 422 en la lectura SCC. Errores SQL, de integridad y autorización se propagan a los manejadores existentes: no se convierten en listas vacías. `read_only_transaction` protege las consultas nuevas con transacciones READ ONLY y límites de tiempo.

## Verificación

Comando reproducible: `make test-scc-core`. Ejecuta pruebas dentro de los servicios Docker, incluida comprobación TypeScript sin emisión. Incluye suites de detalle TRAIN, catálogo comparativo histórico, linaje agrupado/hijos, configuración, métricas científicas y E6.

Los fixtures PostgreSQL usan CTE y `jsonb_populate_recordset`, sin INSERT, tablas temporales ni migraciones. Cubren arquitectura adicional, dos TRAIN de un modelo, modelo sin TRAIN, exclusión de otras tareas, múltiples intentos, reintentos, TEST/VAL, identidad frente a intento, ausencia, sanitización, configuración y errores. Los GET ASGI y SELECT reales se ejecutan contra la base científica actual, no contra exec1-postgres. TRAIN representativo: `bbbd5b60-afaa-4034-a504-a60ed642aafe`; se verifican dataset/modelo/configuración y los tres intentos asociados, incluidos resultados y artefactos paginados.

No se ejecutaron procesos científicos, escritores de datos, cambios de esquema, regeneración de archivos, commits ni pushes. No se verificó disponibilidad física (SCC-ART.1), presentación visual ni algoritmos comparativos. La arquitectura futura se verificó mediante fixtures, no registros reales nuevos.

## Dependencias posteriores

- SCC-ART.1: resolución HTTP segura por artifact_id y comprobación de archivo ausente/acceso; reutilizar procedencia aquí expuesta.
- SCC-NAV.1: normalizar rutas y retirar `/e6/`; no se cambiaron rutas aquí.
- SCC-REPORT.1: consumir esta lectura en detalle EVALUATE/EXPLAIN.
- SCC-REPORT.2: en `/modelo-ia/ejecuciones?datasource=malaria`, convertir `report-run-name` en enlace TRAIN, mostrar Run ID completo y preservar datasource. En `/modelo-ia/ejecuciones/:runId`, actualizar predicciones por imagen, explicabilidad por caso, métricas/reportes técnicos y artefactos usando estas fuentes compartidas.
- SCC-UI.1 y siguientes: UI y selección limitada por configuración efectiva, preflight y compatibilidad científica verificable, comparaciones TRAIN/VAL/TEST, métricas, errores, explicabilidad, embeddings y representaciones.

## Estado de entrega

Implementado el contrato de lectura dentro del alcance SCC-CORE.1. La comprobación física de artefactos y las funcionalidades posteriores conservan sus límites explícitos. El árbol de trabajo contiene cambios de esta entrega sobre el HEAD indicado; `.env` es local e ignorado por Git. Resultado final: `make test-scc-core` terminó con **75 passed**, cero fallos y TypeScript correcto. Dos advertencias de deprecación pertenecen a Starlette/httpx/AnyIO. `git diff --check` terminó sin errores. No se detectaron regresiones en las suites ejecutadas; no se afirma cobertura de toda la aplicación.

Archivos modificados: `.env.example`, `Makefile`, `backend_api/app/config.py`, `backend_api/app/repositories/assessments.py`, `backend_api/app/routes/assessments.py`, `backend_api/app/routes/catalog.py`, `backend_api/app/routes/runs.py`, `backend_api/app/services/assessments.py`, `backend_api/app/services/scientific_results.py`, `frontend/src/services/api.ts`, `docs/README.md`.

Archivos nuevos: `backend_api/app/repositories/catalog.py`, `backend_api/app/repositories/scientific_results.py`, `backend_api/app/schemas/scientific_read.py`, `backend_api/app/services/catalog.py`, `backend_api/app/services/scientific_public.py`, `backend_api/tests/test_scc_core.py`, `frontend/src/types/scientificRead.ts` y este documento.

Estado final: 11 archivos versionados modificados y 8 archivos nuevos sin seguimiento; adicionalmente `.env` local actualizado. Rama y HEAD permanecen iguales. SCC-CORE.1 satisface el contrato de lectura y las pruebas focalizadas dentro del alcance declarado; la disponibilidad física queda explícitamente sin certificar, reservada para SCC-ART.1.
