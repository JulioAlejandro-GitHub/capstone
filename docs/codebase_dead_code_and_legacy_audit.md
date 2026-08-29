# Auditoría exhaustiva de código en desuso y legacy

Fecha: 2026-08-24

Proyecto: `capstone`

Base auditada: rama `main`, commit inicial `0cb483ff`

Alcance: repositorio completo, sin commit ni push

## Resumen ejecutivo

Se inspeccionaron los 834 archivos versionados que existían al comenzar la auditoría,
incluyendo Python, TypeScript/React, CSS, SQL, shell, configuración, dependencias,
tests y documentación. La evidencia combinó grafo de imports, búsquedas globales de
referencias estáticas y dinámicas, registro de rutas, entrypoints CLI, configuración,
tests, historia Git y consultas de sólo lectura a PostgreSQL.

El diff versionado elimina seis archivos y contiene 1.156 líneas eliminadas y 1.559
insertadas. El incremento neto de 403 líneas corresponde principalmente a la
clasificación/corrección documental y a la corrección acotada del detalle de
explicabilidad. Se retiraron 23 imports
sin uso, siete funciones o métodos muertos, doce clases/tipos Python sin consumidores,
un componente frontend obsoleto y una dependencia directa sin uso. No se eliminó
ninguna ruta backend. También se corrigieron residuos de configuración, fixtures que
codificaban estados históricos y un guardrail DB cuyo import path era incompleto.

La limpieza conserva intencionalmente capacidades que no necesariamente tienen un
botón visible: arquitecturas ML, TTA, ensemble, LIME, SHAP, Grad-CAM, calibraciones,
Stage 2, herramientas de despliegue, scripts operativos y el pipeline completo para
crear futuras Dataset Versions. Se conservaron igualmente el split físico legacy,
runs y artefactos históricos, todas las migraciones Alembic y los SQL de fundación.

La limpieza no cambió el comportamiento productivo. Un TRAIN nuevo sigue resolviendo una
`dataset_version_id` gobernada, EVALUATE hereda esa identidad y no existe fallback
silencioso al split físico. La publicación sigue requiriendo únicamente TRAIN
`completed` más EVALUATE `completed`.

Durante la validación posterior se corrigió además un defecto activo del detalle de
Ejecuciones: la carga de “Explicabilidad por caso” hacía dos recorridos de una vista
costosa, transfería metadata repetida y ocultaba el timeout como cero casos. El
endpoint usa ahora un único recorrido, contrato compacto opt-in y linaje gobernado;
la UI muestra carga, error y reintento con timeout dedicado. Esta corrección funcional
no elimina ni reescribe resultados científicos.

## Convenciones de conteo

- `FILES_ANALYZED=834` corresponde al inventario versionado inicial; este informe es
  un entregable nuevo y no altera esa línea base.
- Los conteos de `*_COMPONENTS` corresponden a las filas o cohortes funcionales del
  inventario siguiente, no a archivos individuales. Una cohorte agrupa elementos con
  la misma evidencia, riesgo y decisión.
- `LINES_REMOVED=1156` y `LINES_ADDED=1559` proceden del diff versionado final. Git no
  incluye en esos valores los dos entregables documentales todavía no versionados:
  este informe y `docs/README.md`.
- Los candidatos LOW son las 16 cohortes retiradas o corregidas. Los 17 MEDIUM y cinco
  HIGH se conservaron.

## Método y cobertura

La fase de inventario precedió a las eliminaciones. Para cada candidato se revisaron:

- imports directos, reexports y usos por símbolo;
- FastAPI `include_router`, OpenAPI y rutas construidas en runtime;
- React router, imports dinámicos, aliases y módulos alcanzables desde `main.tsx`;
- `python -m`, scripts `run_*.py`, console scripts, npm scripts, Makefile, Docker y
  llamadas por subprocess;
- referencias en configuración, shell, documentación y tests;
- SQL, vistas, migraciones, datos, lineage y compatibilidad con runs históricos;
- historia Git como evidencia secundaria, nunca como único motivo de eliminación;
- AST Python, TypeScript estricto, build, dependencias instaladas y suites de tests.

Distribución inicial por extensión: 387 Python, 197 Markdown, 65 TSX, 17 TS, 48 JSON,
23 SQL, 19 MJS, 12 shell, cuatro CSS, cuatro YAML/YML principales y el resto en
configuración, imágenes o artefactos científicos versionados.

## Inventario ACTIVE

| ID | Component | Classification | Evidence | Risk | Action |
|---|---|---|---|---|---|
| A1 | `backend_api/app/main.py:app` y grafo de routers | ACTIVE | Entrada Uvicorn/Docker/script; OpenAPI construye 164 paths | HIGH | KEEP |
| A2 | Configuración, DB, auth, permisos, auditoría, health y observabilidad backend | ACTIVE | Importados por startup/routers; cobertura y smoke de aplicación | HIGH | KEEP |
| A3 | `/api/datasets`, detalle UUID y `governed_datasets` | ACTIVE | Consumidos por la UI actual y tests PostgreSQL; identidad end-to-end | HIGH | KEEP |
| A4 | Ingesta, calidad, detección, clasificación y revisión de frotis | ACTIVE | Routers registrados, workflow frontend y tests de servicios/API | HIGH | KEEP |
| A5 | `index.html` → `main.tsx` → auth/router/layout | ACTIVE | Cadena Vite real; 77 módulos TS/TSX alcanzables | HIGH | KEEP |
| A6 | Vista `/modelo-ia/dataset?datasource=malaria` | ACTIVE | Llama sólo a Dataset Versions y renderiza el contrato gobernado | HIGH | KEEP |
| A7 | Resolver gobernado y TRAIN ML | ACTIVE | TRAIN exige versión entrenable y persiste `dataset_version_id` | HIGH | KEEP |
| A8 | EVALUATE, checkpoint, threshold y probability calibration | ACTIVE | Entry points y tests; EVALUATE hereda la versión del TRAIN | HIGH | KEEP |
| A9 | Predicción, Grad-CAM y contratos de explicabilidad | ACTIVE | APIs/CLI/tests activos; Grad-CAM sigue en el modal de auditoría | HIGH | KEEP |
| A10 | Bootstrap, split, validación, materialización, freeze y trainability | ACTIVE | CLI oficial y 78 tests; capacidad para futuras versiones | HIGH | KEEP |
| A11 | `alembic.ini` raíz, head `20260812_02` y validación de schema | ACTIVE | Consumido por Makefile, CI, Docker y scripts DB | HIGH | KEEP |
| A12 | Suites, build, validadores y manifests de dependencias | ACTIVE | Comandos oficiales ejecutados con éxito | MEDIUM | KEEP |

Conteo: `ACTIVE_COMPONENTS=12`.

## Inventario LEGACY_REQUIRED

| ID | Component | Classification | Evidence | Risk | Action |
|---|---|---|---|---|---|
| L1 | `malaria_dl_local_project/data/malaria_physical_split` | LEGACY_REQUIRED | 27.558 imágenes para reproducibilidad; no es fallback de TRAIN nuevo | HIGH | KEEP |
| L2 | `/api/dataset` y `dataset_browser.py` | LEGACY_REQUIRED | Router registrado y testeado; explora inventario físico histórico, no Dataset Versions | MEDIUM | KEEP |
| L3 | Loaders/opciones CLI explícitas para runs o checkpoints legacy | LEGACY_REQUIRED | Compatibilidad reproducible y warnings explícitos; nunca selección silenciosa | MEDIUM | KEEP |
| L4 | 19 revisiones en `alembic/versions` | LEGACY_REQUIRED | Historia lineal aplicada, subtipo `IMMUTABLE_HISTORY` | HIGH | KEEP |
| L5 | 23 SQL históricos en `malaria_dl_local_project/db/init` | LEGACY_REQUIRED | Fundación y trazabilidad de schema; no son fuente para borrar por falta de callers UI | HIGH | KEEP |
| L6 | Runs, modelos, checkpoints, releases, outputs y artefactos científicos | LEGACY_REQUIRED | Evidencia experimental y de lineage; fuera del alcance de limpieza | HIGH | KEEP |
| L7 | Auditorías por etapa y reportes históricos | LEGACY_REQUIRED | Evidencia temporal; se distinguen de documentación operativa vigente | MEDIUM | KEEP |
| L8 | Redirects históricos y `SmearAnalysisResultsView` como alias | LEGACY_REQUIRED | Compatibilidad de URLs/imports y tests explícitos | MEDIUM | KEEP |
| L9 | Guardrails DB, wrappers `test_db_*`, `check_connection`, `viejo-compose.yaml` | LEGACY_REQUIRED | Compatibilidad y protección ante operaciones destructivas/entornos históricos | HIGH | KEEP |

Conteo: `LEGACY_REQUIRED_COMPONENTS=9`.

## Inventario OPTIONAL_CAPABILITY

| ID | Component | Classification | Evidence | Risk | Action |
|---|---|---|---|---|---|
| O1 | TTA y ensemble | OPTIONAL_CAPABILITY | CLI, tests y contratos válidos aunque no sean el flujo UI principal | MEDIUM | KEEP |
| O2 | LIME y SHAP | OPTIONAL_CAPABILITY | Dependencias, implementación y tests; capacidad científica intencional | MEDIUM | KEEP |
| O3 | Stage 2, reviews y cola de calidad backend | OPTIONAL_CAPABILITY | Routers/contratos registrados; consumidores pueden ser operativos o futuros | MEDIUM | KEEP |
| O4 | Rutas frontend registradas sin entrada visible | OPTIONAL_CAPABILITY | Evaluación, comparación, despliegues, trazabilidad, uploads y logs siguen alcanzables | MEDIUM | KEEP |
| O5 | Backfill, deploy, release y diagnóstico de modelos | OPTIONAL_CAPABILITY | Scripts ejecutables con guards y documentación | MEDIUM | KEEP |
| O6 | Tres verificaciones E2E manuales de producción | OPTIONAL_CAPABILITY | Gates opt-in y contratos distintos; no son duplicados equivalentes | MEDIUM | KEEP |
| O7 | Dockerfiles y Compose raíz/override | OPTIONAL_CAPABILITY | Entrypoints ejecutables; no son el gate oficial local | MEDIUM | KEEP |
| O8 | Reconciliación/cleanup de storage y tareas operativas | OPTIONAL_CAPABILITY | Dry-run/guards y uso de mantenimiento explícito | MEDIUM | KEEP |

Conteo: `OPTIONAL_CAPABILITY_COMPONENTS=8`.

## Inventario DUPLICATED

| ID | Component | Classification | Evidence | Risk | Action |
|---|---|---|---|---|---|
| D1 | `.env.example` raíz y `backend_api/.env.example` | DUPLICATED | Variables parcialmente solapadas, pero el segundo conserva knobs y aliases legacy | MEDIUM | REVIEW/KEEP |
| D2 | Nombres `/api/dataset` y `/api/datasets` | DUPLICATED | Solapamiento nominal; semánticas física histórica vs gobernada diferentes | MEDIUM | REVIEW/KEEP |
| D3 | `CellReview.tsx` frente al workspace vigente | DUPLICATED | Sin caller runtime, pero estación manual y tests propios | MEDIUM | REVIEW/KEEP |
| D4 | `SmearAnalysisResultsView` frente a la vista canónica | DUPLICATED | Alias explícito de compatibilidad cubierto por tests | MEDIUM | REVIEW/KEEP |
| D5 | `reporte_tecnico.md` y `docs/reporte_tecnico_20260729.md` | DUPLICATED | Contenido idéntico, pero una copia funciona como evidencia histórica fechada | MEDIUM | REVIEW/KEEP |

Conteo: `DUPLICATED_COMPONENTS=5`.

## Candidatos LOW eliminados o corregidos

| ID | Component | Classification | Evidence independiente | Risk | Action aplicada |
|---|---|---|---|---|---|
| R1 | `backend_api/app/models/cell_classification.py` | ORPHANED | Cero imports/referencias/reflexión; contratos activos viven en schemas/services | LOW | Archivo eliminado |
| R2 | `backend_api/app/schemas/common.py` | ORPHANED | `Datasource`/`HealthResponse` sin importadores; health usa contrato propio | LOW | Archivo eliminado |
| R3 | `backend_api/alembic.ini` vacío | ORPHANED | Cero bytes y cero referencias; todos los entrypoints usan el archivo raíz | LOW | Archivo eliminado |
| C1 | `DetectionRunStatus` y `ScientificRead` | DEAD_CODE | Cero consumidores/imports/tests/dynamic refs | LOW | Dos clases eliminadas |
| C2 | Imports inequívocamente no usados | DEAD_CODE | AST + compiladores + búsqueda de side effects | LOW | 23 imports eliminados |
| C3 | Exports, helpers y props frontend sin consumers | DEAD_CODE | Grafo desde `main.tsx`, TypeScript estricto y búsqueda global | LOW | Siete funciones y otros símbolos eliminados |
| C4 | Bloques de implementación comentada | DEAD_CODE | Reemplazo activo contiguo; Git preserva historia | LOW | Bloques TS/CSS/Python eliminados |
| C5 | Dependencia `opencv-python` | DEAD_CODE | Cero imports `cv2`, `Required-by` vacío y suite ML completa | LOW | Dependencia eliminada |
| OBL1 | `frontend/src/pages/SmearAnalysis.tsx` | OBSOLETE_LEGACY | Sin ruta/import dinámico; reemplazado por `SmearWorkflow` | LOW | Archivo eliminado |
| OBL2 | APIs/tipo exclusivos de `SmearAnalysis` | OBSOLETE_LEGACY | Único consumidor era la página retirada | LOW | Tres métodos y `EligibleBatch` eliminados |
| OBL3 | Cliente/tipos del DatasetBrowser físico | OBSOLETE_LEGACY | UI actual consume exclusivamente `/api/datasets`; cero consumers | LOW | Dos métodos/helpers y dos tipos eliminados |
| OBL4 | CSS exclusivo de páginas legacy | OBSOLETE_LEGACY | Selectores ausentes del DOM/TSX y reemplazo gobernado vigente | LOW | 16 declaraciones/clases de selector retiradas |
| OBL5 | `frontend/README_FRONTEND.md` | OBSOLETE_LEGACY | Duplicado, comandos falsos y arquitectura reemplazada | LOW | Archivo eliminado; README canónico actualizado |
| OBL6 | `docker-compose.test.yml` vacío | OBSOLETE_LEGACY | Sólo comentarios y `services: {}`; cero referencias | LOW | Archivo eliminado |
| OBL7 | Head CI viejo y DSN personal E2E | OBSOLETE_LEGACY | Head real distinto; fallback local no era contrato portable | LOW | Gates corregidos sin alterar flujo productivo |
| OBL8 | Fixtures/aserciones ligadas a estado histórico | OBSOLETE_LEGACY | Fallaban por omitir contrato o mezclar 27.558 legacy + 27.558 v1 | LOW | Tests corregidos para invariantes reales |

Conteos: `ORPHANED_COMPONENTS=3`, `DEAD_CODE_COMPONENTS=5`,
`OBSOLETE_LEGACY_COMPONENTS=8`, `LOW_RISK_REMOVAL_CANDIDATES=16`.

### Archivos eliminados

| Archivo | Motivo | Reemplazo o fuente canónica |
|---|---|---|
| `backend_api/app/models/cell_classification.py` | Modelos huérfanos | Schemas/services activos de clasificación |
| `backend_api/app/schemas/common.py` | DTOs huérfanos | Contratos específicos de rutas activas |
| `backend_api/alembic.ini` | Archivo vacío | `alembic.ini` raíz |
| `docker-compose.test.yml` | Compose sin servicios | Tests locales/CI y Compose operativo raíz |
| `frontend/src/pages/SmearAnalysis.tsx` | Página reemplazada y no enrutable | `SmearWorkflow` |
| `frontend/README_FRONTEND.md` | Documento duplicado obsoleto | `frontend/README.md` |

### Símbolos y dependencias retirados

- Clases/tipos Python: `ClassificationRunStatus`, `CellPredictionStatus`,
  `CellExplanationStatus`, `ClassificationReviewDecision`, `CanonicalCellLabel`,
  `SmearAnalysisOutcome`, `FrozenClassificationInput`, `ClassificationCounts`,
  `Datasource`, `HealthResponse`, `DetectionRunStatus` y `ScientificRead`.
- Funciones/métodos: `getEligibleBatches`, `executeQuality`, `getQualityQueue`,
  `datasetImageUrl`, `getDatasetSummary`, `confidenceLabel` y
  `normalizeDatasetImagePageSize`.
- Otros residuos frontend: `DatasetBrowserSummary`, `DatasetSplitRow`,
  `EligibleBatch`, `ApiArtifact`, `modelAiNavItems`, `navigationGroups`, tamaños de
  paginación no consumidos y tres props muertos de `CellDetailPanel`.
- Imports: cinco backend, cinco split, diez ML y tres frontend.
- Dependencia: `opencv-python`; no había import directo, plugin, CLI ni paquete que la
  declarase como `Required-by` en el entorno auditado.

## Candidatos MEDIUM/HIGH retenidos

Los 17 candidatos MEDIUM son L2, L3, L7, L8, O1–O8 y D1–D5. Requieren una tarea
separada con decisión de compatibilidad o consolidación; no se eliminaron.

Los cinco candidatos HIGH son L1, L4, L5, L6 y L9. Contienen datos históricos,
historia de schema, evidencia científica o guardrails; se conservaron sin cambios.

Temas recomendados para una auditoría posterior:

1. Unificar ejemplos de entorno sólo después de definir política de aliases y soporte.
2. Resolver la contradicción entre Compose ejecutable y documentación que privilegia
   ejecución local, sin asumir que Docker es obsoleto.
3. Decidir formalmente el ciclo de vida de `CellReview.tsx` y del alias de resultados.
4. Revisar la navegación de capacidades frontend ocultas con producto/operaciones.
5. Considerar code-splitting del bundle Vite de 588,31 kB; es rendimiento, no evidencia
   de código muerto.
6. Alinear el resolver ML de Dataset Versions con futuros checks bloqueantes: hoy
   valida explícitamente los 12 checks requeridos de v1, mientras el contrato general
   de trainability también contempla cualquier check adicional marcado
   `blocking_for_validation=true`. Para v1 ambos contratos producen PASS; el riesgo es
   una extensión futura del catálogo de checks.

## Dataset, ML y regla productiva preservados

Las consultas y tests de integración verificaron:

| Invariante | Resultado |
|---|---|
| `Malaria Patient Split v1` | Presente, semantic version `1.0.0` |
| Estado/trainability | `FROZEN`, `trainable=true` |
| Pacientes/registros | 201 / 27.558 |
| TRAIN/VAL/TEST | 22.180 / 2.693 / 2.685 |
| Pacientes por split | 161 / 20 / 20 |
| Validación | 12/12 `PASS` |
| Materialización/reconciliación | `READY` / `PASS` |
| Integridad de archivos | 27.558 hashes, cero mismatch |
| Lineage | Fingerprints finales completos |
| Split físico legacy | 27.558 archivos, conservado separadamente |
| UI vigente | Sólo `/api/datasets` y `/api/datasets/{dataset_version_id}` |

La tabla histórica `dataset_split_images` contiene dos raíces de 27.558 registros cada
una: `malaria_physical_split` y la materialización UUID de v1. El test obsoleto sumaba
ambas y esperaba erróneamente 27.558; ahora prueba cada raíz de forma explícita. No se
modificaron asignaciones, estadísticas, checks, materializaciones ni fingerprints.

El flujo TRAIN llama al resolver gobernado y guarda `dataset_version_id`. Si falta una
versión válida falla cerrado; no selecciona `malaria_physical_split`. EVALUATE y las
calibraciones heredan el dataset del TRAIN. Threshold y temperature calibration usan
VAL y rechazan TEST como fuente de ajuste. La elegibilidad de publicación continúa
siendo exactamente TRAIN `completed` más EVALUATE `completed`.

## Entrypoints reales

| Área | Entrypoints confirmados | Decisión |
|---|---|---|
| Backend | `uvicorn app.main:app`, `scripts/start_backend_api.sh`, Dockerfile/Compose | ACTIVE/OPTIONAL; conservar |
| Frontend | Vite `index.html` → `src/main.tsx`; scripts npm `dev`, `test`, `build` | ACTIVE; conservar |
| DB | Makefile, `scripts/db/{status,migrate,backup,test_schema_clean}.sh`, Alembic raíz | ACTIVE/guardrail; conservar |
| Split | console script `malaria-split` y 11 subcomandos de auditoría/governanza | ACTIVE; conservar |
| ML canónico | `python -m src.train/evaluate/predict_image/explain/ensemble/tta/calibrate` | ACTIVE/OPTIONAL; conservar |
| ML batch | `run_train_all_models.py`, `run_evaluate_all_trainings.py`, `run_explain_all_trainings.py` | OPTIONAL_CAPABILITY; conservar |
| Operación | release/deploy/diagnóstico/backfill/storage/E2E | OPTIONAL_CAPABILITY; conservar |

Los CLI se validaron mediante sus ayudas: 12/12 comandos split, 9/9 wrappers legacy
ML, 5/5 módulos canónicos y 3/3 scripts batch respondieron correctamente.

## Dependencias

| Grupo | Classification | Evidencia/decisión |
|---|---|---|
| Backend runtime/test | USED/TEST_ONLY | FastAPI, Uvicorn, SQLAlchemy, psycopg, Alembic, auth, Pillow, pytest/httpx justificados por runtime o tests |
| Frontend directas | USED | Todas las dependencias directas tienen import, build o uso de tooling; `npm ls` pasó |
| Split | USED | Pillow y SQLAlchemy participan en identidad/materialización y PostgreSQL |
| `tqdm` | TRANSITIVE_REQUIRED | Requerida por LIME/SHAP/TensorFlow Datasets; retenida |
| `importlib_resources`, `zipp` | OPTIONAL/MEDIUM | Compatibilidad/entorno; evidencia insuficiente para retirar |
| `opencv-python` | REMOVE_CANDIDATE | Cero uso y cero dependientes; eliminada |

`pip check` pasó en los entornos Python auditados. No se instaló tooling nuevo.

## CSS, comentarios y debugging

Se retiró CSS exclusivo del DatasetBrowser físico y de la página de calidad reemplazada,
además de tres declaraciones comentadas. Las reglas similares bajo breakpoints o clases
dinámicas se conservaron.

No quedaron TODO, FIXME, HACK o TEMP accionables en el código productivo inspeccionado.
El único `@deprecated` corresponde a un alias tipado de compatibilidad de la vista
inmersiva y se retuvo. Los `print` restantes son salida de CLI/progreso científico y el
logging frontend/backend restante es operativo; no se detectó un endpoint de debug
registrado ni un `console.log` temporal que justificara eliminación.

## Documentación

La revisión específica de `docs/` cubrió los 158 artefactos de contenido existentes
antes de crear el índice canónico: 143 Markdown, 14 JSON y un YAML, con 12.690
líneas. Se agregó `docs/README.md`, por lo que el resultado contiene 159 artefactos
de contenido y 13.322 líneas. El diff acumulado actualiza 106 documentos versionados;
no se eliminó ningún documento versionado bajo `docs/`.

| Clasificación documental final | Cantidad | Acción |
|---|---:|---|
| `CURRENT_DOC` | 74 | Conservar; el índice enlaza las fuentes operativas canónicas |
| `OPTIONAL_CAPABILITY` | 3 | Conservar; no agrega gates a la publicación Stage 2 |
| `HISTORICAL_AUDIT` / `HISTORICAL_DESIGN` | 63 | Conservar con snapshot y uso operativo deshabilitado |
| `OBSOLETE_DOC` / `SUPERSEDED` | 7 | Conservar con banner `NO`; seguir el reemplazo indicado |
| `LEGACY_REQUIRED` | 11 | Conservar por decisiones, contratos o compatibilidad |
| `DUPLICATED` | 1 | Retener la copia fechada hasta una decisión de archivo explícita |

Acciones aplicadas:

- se reescribieron `runbook_split_completo_malaria.md` y
  `guia_entrenamiento_patient_split.md`: usan el servicio Compose `db`,
  la base única y `DATABASE_URL` inyectada; ya no contienen DSN personal,
  apagado de servicios, rematerialización ni borrado de Dataset v1;
- se corrigieron auth/RBAC, anotaciones científicas, APIs, rutas frontend,
  Alembic, Docker opcional, menú visible y asociación real de runs;
- 37 snapshots de arquitectura/ingeniería, diez reportes root/audits, el draft
  OpenAPI, 13 JSON Schema y dos documentos de planificación recibieron estado
  histórico o sustituido inequívoco;
- seis ADR no materializados o sustituidos quedaron `LEGACY_REQUIRED`, sin
  alterar la decisión histórica; ADR-019 documenta la evolución de ruta;
- los flujos anteriores de Stage 2 quedaron como compatibilidad, mientras
  `stage2_productive_training_card.md` permanece como fuente de verdad para
  `TRAIN completed + EVALUATE completed`;
- se creó `docs/README.md` con taxonomía, fuentes canónicas y reglas de seguridad.
- se corrigió `scripts/db/status.sh` para que `make db-status` configure el
  `PYTHONPATH` requerido por el backend; una ejecución con destino ficticio confirmó
  que alcanza el diagnóstico de conexión sin realizar escrituras.

La única eliminación física de esta fase fue `docs/.DS_Store`, un artefacto generado
e ignorado. La copia exacta `docs/reporte_tecnico_20260729.md`, los ADR, auditorías,
contratos y reportes científicos se retuvieron por riesgo MEDIUM/HIGH y trazabilidad.

## SQL, migraciones y artefactos

- Cero archivos cambiados en `alembic/versions`, SQL, data, releases, outputs o storage
  científico.
- Alembic conserva 19 revisiones, un único head `20260812_02`, cero branch points y
  cero merge points.
- CI exige el head vigente y además la topología lineal; una eliminación accidental de
  la revisión final no pasaría inadvertida.
- `verify_alembic_adoption.py` reconoce el head lineal vigente y las revisiones de
  transición explícitas; `make db-migrate-check` pasó contra PostgreSQL.
- No hubo downgrade, stamp, reescritura de historia ni cambio de schema.
- Caches, `.pyc`, `.pytest_cache`, `node_modules`, `dist`, logs y temporales fueron
  clasificados `GENERATED_OR_RUNTIME_ARTIFACT`; no se confundieron con fuente. Sólo
  se retiró el `docs/.DS_Store` ignorado, sin tocar artefactos científicos.
- La inspección de explicabilidad detectó un riesgo histórico preexistente: nueve de
  150 visualizaciones del run `a04d875c-f18f-4141-9cf5-58b63747413e` existen y son
  servibles, pero sus bytes ya no coinciden con el checksum registrado debido a rutas
  globales reutilizadas bajo `outputs/explainability`. Se conservaron sin cambios;
  `available` describe disponibilidad, no integridad histórica.

## Validación final

| Validación | Resultado |
|---|---|
| Backend sin el antiguo marker de integración | 204 passed, 6 skipped, 38 deselected |
| Backend Dataset Versions con PostgreSQL real | 3 passed |
| Frontend tests | 154 passed |
| Frontend build Vite | PASS |
| TypeScript `noUnusedLocals/noUnusedParameters` | PASS |
| ML suite completa | 364 passed, 16 skipped |
| Split suite completa con PostgreSQL | 78 passed |
| OpenAPI/application import smoke | PASS, 164 paths |
| Alembic adoption/current/heads | PASS, head `20260812_02` |
| AST/compile Python | PASS |
| Shell syntax | PASS |
| `pip check` / `npm ls` | PASS |
| Markdown relativo | PASS, 43 enlaces locales |
| JSON/YAML documental | PASS, 14 JSON y un OpenAPI YAML |
| Contratos históricos | PASS, 128 refs resueltos; schemas sin cambio semántico salvo `$comment` |
| Patrones documentales peligrosos | PASS, cero DSN personales, `rm -rf` o apagado de servicios en `docs/` |
| `scripts/db/status.sh` | PASS sintáctico; import backend alcanzado con destino ficticio |
| Detalle XAI real `a04d875c-…` | HTTP 200; 150/150 resultados; 50 predicciones × 3 métodos; 5,18 s; 693.175 bytes compactos |
| Linaje XAI TRAIN/EVALUATE/EXPLAIN | PASS; los tres IDs resuelven sólo el EXPLAIN gobernado esperado |
| `git diff --check` | PASS |

Totales de las suites contabilizadas: 803 pruebas aprobadas, 22 omitidas, 38
deseleccionadas por marker y cero fallidas. Las tres pruebas PostgreSQL del contrato de
Dataset Versions se ejecutaron por separado y están incluidas en las 803 aprobadas.

No se ejecutó una campaña de entrenamiento, porque alteraría artefactos y excede el
smoke solicitado. Tampoco se levantó un navegador E2E; el estado de la UI se verificó
mediante el grafo de rutas y API, sus tests, TypeScript, build y la respuesta real del
backend. El único warning no bloqueante fue el chunk Vite de 588,31 kB.

## Métricas finales

```text
FILES_ANALYZED=834
FILES_CHANGED=165
ACTIVE_COMPONENTS=12
LEGACY_REQUIRED_COMPONENTS=9
OPTIONAL_CAPABILITY_COMPONENTS=8
DUPLICATED_COMPONENTS=5
ORPHANED_COMPONENTS=3
DEAD_CODE_COMPONENTS=5
OBSOLETE_LEGACY_COMPONENTS=8
LOW_RISK_REMOVAL_CANDIDATES=16
MEDIUM_RISK_CANDIDATES=17
HIGH_RISK_CANDIDATES=5
FILES_REMOVED=6
LINES_ADDED=1559
LINES_REMOVED=1156
NET_VERSIONED_LINES=403
UNUSED_IMPORTS_REMOVED=23
DEAD_FUNCTIONS_REMOVED=7
DEAD_CLASSES_REMOVED=12
OBSOLETE_FRONTEND_COMPONENTS_REMOVED=1
OBSOLETE_BACKEND_COMPONENTS_REMOVED=2
BACKEND_ROUTES_REMOVED=0
DEPENDENCIES_REMOVED=1
DOCUMENTS_ANALYZED=158
DOCUMENTS_UPDATED=106
DOCUMENTS_CREATED=2
DOCUMENTS_REMOVED=0
GENERATED_DOCUMENT_ARTIFACTS_REMOVED=1
DB_GUARDRAILS_FIXED=1
```

## Conclusión

La limpieza conserva los flujos vigentes y reduce deuda técnica demostrada sin
sacrificar capacidades opcionales ni trazabilidad; la única variación funcional
adicional corrige la carga y resolución por linaje del detalle de explicabilidad. Los
elementos
MEDIUM/HIGH quedaron documentados y retenidos. Dataset v1, el filesystem legacy, la
historia Alembic/SQL, los runs y los artefactos científicos permanecen intactos.
