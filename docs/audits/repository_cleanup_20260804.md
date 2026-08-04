# Auditoría y limpieza segura del repositorio — 2026-08-04

> Estado: clasificación previa a la eliminación. Este documento se creó antes de
> borrar candidatos y se completará con los resultados de validación. El historial
> de Git no sustituye las exclusiones de seguridad: datos, storage, checkpoints y
> trazabilidad quedan fuera de alcance destructivo.

## Estado inicial

| Dato | Valor observado |
|---|---|
| Rama | `main` |
| Commit | `4f05fd942b7588826f6d46b8e589600b5a329e44` |
| Cambios preexistentes | ninguno; `git status --short` vacío |
| `git diff --check` | PASS |
| Archivos físicos, sin `.git` | 139.779 |
| Tamaño físico, sin `.git` | 7.822.184.152 bytes |
| Archivos versionados | 698 |
| Tamaño versionado | 8.392.526 bytes |
| Python del sistema | 3.14.4 |
| Python oficial ML/API | 3.12.13 |
| Node | 22.23.1 |
| PostgreSQL | 17.9 Homebrew, arm64 |
| Base vigente | `malaria_experiments`; no se modifica ni elimina |
| Alembic current/head | `20260728_03` / `20260728_03` |
| Revisiones Alembic | 11 |

Huella previa del schema-only dump:
`2944c298f1932aba044768be314cd42e8206323993cc30800e9cdb968e439541`.
El respaldo temporal sólo contiene DDL/metadata, no datos.

## Inventario

| Categoría | Archivos versionados | Entradas y responsabilidades |
|---|---:|---|
| IA/ML | 278 | CLIs TRAIN/EVALUATE/EXPLAIN, paquete `src/malaria_dl`, adapters históricos, tests y releases reproducibles |
| Documentación | 156 bajo `docs/`; 171 Markdown/TXT/RST totales | ADR, diseño, ciencia, operación, reportes históricos y contratos |
| Frontend | 107 | `index.html` → `main.tsx` → `App.tsx`; React Router, APIs, CSS, tests |
| Backend | 88 | `app.main:app`; 16 routers, servicios, repositorios, schemas y 24 archivos de test |
| Scripts | 26 | DB, storage, gobierno, diagnóstico, validación e inicio |
| Alembic | 13 | `env.py`, template y 11 revisiones lineales |
| Storage versionado | 13 | originales y Grad-CAM referenciados; protegido, `KEEP` |
| Configuración raíz | 17 | Makefile, CI, env examples, ignores y archivos de runtime |

Inventario PostgreSQL vigente: 62 tablas, 1.659 columnas, 62 PK, 137 FK,
38 unique constraints, 285 check constraints, 284 índices, 27 vistas,
58 funciones visibles, 54 filas de eventos de trigger, extensiones `pgcrypto` y
`plpgsql`, y roles funcionales `administrator`, `operator`, `read_only`,
`researcher` y `reviewer`.

## Mapa de dependencias

- FastAPI registra explícitamente todos sus routers en `backend_api/app/main.py`.
  Los servicios de persistencia usan SQL textual; no existe metadata ORM completa.
- El backend oficial y la inferencia comparten el entorno Python 3.12 de
  `malaria_dl_local_project/.venv`. Los adapters `src/*.py` sí tienen consumidores
  internos, tests y compatibilidad CLI/documentada.
- El pipeline vigente es upload → quality gate → detección/crops → clasificación
  TensorFlow → Grad-CAM manual → revisión → historial.
- El frontend no usa `React.lazy` ni imports dinámicos: el grafo productivo es
  estático. `/frotis/analizar` es la ruta canónica; los redirects antiguos
  conservan query parameters. Historial y sus deep links son entradas vigentes.
- PostgreSQL y `var/storage` contienen artefactos operacionales. La ausencia de un
  import nunca se usó para inferir que un checkpoint, release, imagen, crop o
  explicación estuviera muerto.

## Regla canónica de Productivo Etapa 2

La elegibilidad de publicación es sólo:

```text
TRAIN.status = completed AND EVALUATE.status = completed
```

`Stage2PublicationService` ya implementa esa regla. El carril técnico anterior
añade contrato, copia, calibración, smoke y deployment durante publicación; se
clasifica como `MERGE` y sólo podrá retirarse tras migrar sus consumidores y
mantener las validaciones de checkpoint, checksum, threshold, mapping,
preprocessing, framework e input shape dentro de la ejecución de inferencia.

## Tabla de decisión previa

| Elemento | Categoría | Evidencia de uso o desuso | Riesgo | Decisión |
|---|---|---|---|---|
| `var/storage`, datasets, outputs, releases, checkpoints, backups y `.env` | persistencia | rutas/filas reales, reproducibilidad o secretos | crítico | `KEEP / NO TOUCH` |
| 23 SQL de `malaria_dl_local_project/db` y 11 revisiones Alembic | DB | forman la única cadena de instalación/evolución disponible | crítico | `KEEP` |
| `.dockerignore`, tres Compose, `viejo-compose.yaml`, ambos Dockerfile | configuración Docker | se referencian sólo entre sí; Makefile/CI/runtime oficial no los invocan; arquitectura local excluye Docker | bajo | `DELETE_SAFE` |
| `scripts/test_db_{up,down,reset,bootstrap,status,wait}.sh` y targets retirados | scripts | stubs/alias sin consumidores; el estado canónico es `scripts/db/status.sh` | bajo | `DELETE_SAFE` tras actualizar Makefile/docs |
| `frontend/src/pages/SmearAnalysis.tsx` | frontend | sin importer, ruta, import dinámico ni test de esa página; sustituida por `SmearWorkflow` | bajo | `DELETE_SAFE` |
| API/tipos/CSS usados sólo por `SmearAnalysis.tsx` | frontend | consumidor único demostrado y reemplazado | medio visual | `DELETE_SAFE` quirúrgico tras tests/build |
| `backend_api/app/models/cell_classification.py` | backend | cero importadores; no es ORM, metadata, relación, reflexión ni contrato serializado | bajo | `DELETE_SAFE` |
| `backend_api/app/schemas/common.py` | backend | schemas sin `response_model`, importadores, subclases ni reflexión | bajo | `DELETE_SAFE` |
| `DetectionRunStatus`, `ScientificRead`, `stage2_default_candidates` | backend | símbolos aislados sin llamadores, registro o reflexión | bajo | `DELETE_SAFE` |
| `tqdm`, `opencv-python` | dependencias ML | sin import/CLI/plugin/config; detector vigente usa Pillow | medio | `DELETE_SAFE` tras suite ML |
| Stack técnico Stage 2 (`Stage2ModelAvailabilityService`, endpoints y scripts E2E antiguos) | backend/IA | aún tiene consumidores reales, pero contradice la regla vigente | alto | `MERGE`; borrar sólo tras migración y E2E |
| `Stage2ReleaseDetail`, modal y controles Stage 2 de Deployments/ModelVersions | frontend | rutas/consumidores reales con reglas antiguas | alto | `MERGE`; preservar deep links e historia |
| `CellReview.tsx` | frontend | sin ruta/importer, pero tests conservan una estación manual no inequívocamente reemplazada | medio | `REVIEW_REQUIRED` |
| `SmearAnalysisResultsView.tsx` y alias de tipo | frontend | wrapper sin runtime, pero compatibilidad verificada por tests recientes | medio | `REVIEW_REQUIRED` |
| CSS inmersivo/Liquid Glass y asset `smear-microscope.jpg` | diseño | consumidores y tests; no existen duplicados exactos | alto visual | `KEEP` |
| Docker, PostgreSQL efímero y paridad CI retirados | documentación | marcados superseded o sin referencia; contradicen runtime canónico | bajo | `DELETE_SAFE` |
| 14 cierres/prechecks `prompt*.md` | documentación | snapshots de ejecución, no contratos vigentes; contenido útil se consolida | bajo | `MERGE`, luego `DELETE_SAFE` |
| reportes de four-step/deployment/Stage 0 y reportes técnicos duplicados | documentación | estados intermedios y reglas productivas sustituidas | bajo | `MERGE`, luego `DELETE_SAFE` |
| inventarios/auditorías anteriores y planning ya ejecutado | documentación | huellas antiguas contradictorias; la auditoría actual los sustituye | bajo | `MERGE`, luego `DELETE_SAFE` |
| documentación científica, procedencia, ADR y contratos de diseño | ciencia/legal/diseño | trazabilidad académica o decisiones explícitas | medio | `KEEP`; rotular referencias no-runtime |
| cuatro SQL bajo `docs/`, OpenAPI draft Delivery 2, `complemento e2.txt`, informe académico integral | anexos | no ejecutables, pero posible valor académico no resoluble por grafo | medio | `REVIEW_REQUIRED` |
| `backend_api/.env.example` | configuración | contrato multi-DB no leído por `app.config`; raíz contiene el contrato canónico | bajo | `MERGE`, luego `DELETE_SAFE` |
| caches, bytecode, `.DS_Store`, `frontend/dist`, staging vacío | generado | ignorados/recreables; no son entradas ni persistencia | bajo | `DELETE_SAFE` al final |
| `malaria_dl_local_project/source` | entorno local | virtualenv ignorado y no referenciado; no es código/dataset/modelo | medio | `REVIEW_REQUIRED` hasta verificar metadata y procesos |

## Garantía para `DELETE_SAFE`

Cada grupo marcado `DELETE_SAFE` fue contrastado con entrypoints, imports estáticos,
imports dinámicos, router, scripts, configuración, tests, persistencia y
reproducibilidad. Documentación científica/legal y datos quedaron excluidos. Las
eliminaciones condicionadas no se ejecutan hasta migrar consumidores y pasar pruebas
incrementales.

## Baseline de base de datos: decisión previa

`BASELINE_REQUIRES_MANUAL_APPROVAL`. El SQL histórico construye el legado y la
revisión `20260726_00` es intencionalmente stamp-only; `init_db.py` no encadena
`alembic upgrade`. Aunque se validará una instalación nueva en un schema temporal y
se comparará su huella con `public`, no puede demostrarse desde este repositorio que
ninguna instalación externa necesite la cadena histórica. Por ello no se eliminará
ninguna migración ni se cambiará `alembic_version` de la base vigente.

