# Validación reproducible de Prompt 7

## Estado de la evidencia

**EJECUTADA — recomendación APROBAR.**

La evidencia siguiente fue obtenida el 2026-07-28 en el entorno local oficial.
Los conteos no se deducen del código: provienen del rerun consolidado final y
de las comprobaciones PostgreSQL read-only indicadas.

## Identidad del entorno

| Dato | Evidencia real |
|---|---|
| Fecha y zona | 2026-07-28, `America/Santiago` |
| Rama inicial/final | `main` / `main` |
| Commit inicial/final | `e25a7b653128225ae40026a12bdaa47be9897223` / el mismo, sin commit nuevo |
| Working tree inicial | limpio |
| Working tree final | cambios esperados de Prompt 7, sin commit ni push |
| PostgreSQL/version | PostgreSQL 17.9 Homebrew, disponible |
| Base/schema | `malaria_experiments` / `public` |
| Alembic inicial/final/head | `20260727_04` -> `20260727_05`; current=head |
| Storage | proveedor local bajo `var/storage`, reconciliado |

Comandos de precheck:

```bash
git branch --show-current
git rev-parse HEAD
git status --short
git diff --stat
git diff --check
pg_isready
psql "$DATABASE_URL" -c "SELECT version(), current_database(), current_schema();"
alembic current
alembic heads
alembic history
```

No se usaron `reset`, `clean`, stash automático, downgrade, stamp, `DROP`,
commit o push.

## Matriz de validación

| Área | Comando/evidencia | Estado |
|---|---|---|
| Migración `20260727_05` | aplicada live; seis tablas; current=head | PASS |
| Historial intacto | transición `20260727_04 -> 20260727_05`; previas sin editar | PASS |
| Constraints/índices/triggers | 81 constraints, 26 índices y 12 eventos de trigger inspeccionados | PASS |
| Preflight PostgreSQL | preflight transaccional | PASS |
| Backend consolidado | `pytest backend_api/tests -q -rs`: 119 passed, 26 skipped | PASS |
| Suites PostgreSQL | marker completo: 22 passed; Prompt 7: 5 passed | PASS |
| Suite focal | 43 tests focalizados | PASS |
| Detector sintético | círculo/contacto/borde/tamaños/vacío/cientos/imagen grande | PASS |
| Seguridad storage | traversal, absoluto, symlink, tamaño, SHA, PNG y dimensiones | PASS |
| Idempotencia/retry | replay sin reproceso; fallo permite intento manual nuevo | PASS |
| Reviews | comentarios obligatorios y triggers append-only SQLSTATE `55000` | PASS |
| RBAC | administrator/researcher/operator/reviewer/read_only | PASS |
| Auditoría | ciclo de detección y review con actor JWT | PASS |
| Frontend | `npm test`: 89 passed | PASS |
| Build | `npm run build` | PASS |
| Lint | no existe script `lint` en el proyecto | N/A |
| Python | `python -m compileall backend_api/app scripts` | PASS |
| Reconciliación de crops | `metadata_rows=0 issues=0 mode=dry-run` | PASS |
| Reconciliación de originales | `issues=0` | PASS |
| Whitespace | `git diff --check` y scan de los nueve docs | PASS |
| Estado final | cambios Prompt 7 presentes; mismo commit; sin commit/push | PASS |

## Casos backend obligatorios

Se verificaron los siguientes contratos:

1. run sin aprobación rechazado y run aprobado aceptado;
2. `connected_components_v1` `1.0.0`, snapshot y versiones persistidos;
3. equivalencia que devuelve el mismo run sin reprocesar y reintento manual tras
   fallo;
4. componentes candidatos, aceptados y rechazados;
5. bbox `original_image_pixels`, top-left, xywh y dentro de límites;
6. `cell_code`/orden únicos y estables;
7. crop correspondiente a bbox, padding limitado, PNG y SHA-256;
8. original con mismo SHA-256 antes/después;
9. cero binarios y cero paths absolutos en PostgreSQL;
10. content autenticado, `no-store`, `nosniff`, length, ETag;
11. path traversal y symlink rechazados;
12. eventos y auditoría sin payload sensible;
13. reviews append-only y reglas de comentario;
14. matriz RBAC;
15. error terminal en `failed`, compensación y sin retry automático.

Evidencia real:

```text
suite backend consolidada: 119 passed, 26 skipped
suite focalizada: 43 passed
backend_api/tests/test_cell_detection_postgres.py: 5 passed
marker PostgreSQL consolidado: 22 passed, 123 deselected
```

Los cinco E2E de Prompt 7 forman parte de las 26 pruebas opt-in omitidas por la
corrida normal y de las 22 pruebas seleccionadas por el marker PostgreSQL; los
conteos no se suman entre sí.

La suite PostgreSQL nueva comprobó con detector real:

- elegibilidad `pass`/`warning` aprobado y rechazo de bloqueado/no-ready;
- idempotencia sin segundo procesamiento;
- persistencia de componentes, detecciones, crops, eventos y auditoría;
- bbox dentro de límites en `original_image_pixels`, `cell_code`, PNG y
  checksums;
- original intacto y ausencia de columnas binarias;
- `accepted` seguido de `comment_only` sin cambiar el estado efectivo;
- triggers append-only para UPDATE/DELETE con SQLSTATE `55000` y run terminal
  inmutable;
- checksum corrupto que deja `failed` sin resultados automáticos parciales.

Usó rollback exterior más SAVEPOINT. El teardown verificó cero residuos de
usuarios, runs y auditoría; los binarios sintéticos vivieron en `tmp_path`.

## Casos frontend obligatorios

Se verificaron los siguientes contratos:

- navegación bajo `Análisis de frotis` y ausencia bajo `Modelo IA`;
- listado/elegibilidad/ejecución/apertura;
- tres paneles y adaptación móvil;
- filtros/conteos/imagen actual;
- crop -> box y box -> crop;
- zoom, fit, pan y alineación tras resize;
- toggles, anterior/siguiente/siguiente sin revisar;
- detalle e historial correctos;
- `safe_name` visible y ausencia de `original_filename`/Content-Disposition en
  la superficie cell-analysis;
- reviewer/researcher autorizados y operator sin review;
- comentario obligatorio/confirmación de rechazo;
- ausencia de clasificaciones o métricas clínicas inventadas;
- carga incremental, lazy loading y revocación de object URLs;
- regresión de Cargar imágenes, Control de calidad y Modelo IA.

Evidencia real:

```text
npm test: 89 passed
npm run build: PASS
frontend/tests/cell-review-workspace.test.mjs: incluido y aprobado
npm run lint: N/A, script no definido
```

La suite cubre navegación, permisos, workspace, filtros, selección
bidireccional, visor/toolbar, revisión, lazy loading, object URLs, estados
vacíos y ausencia de terminología clínica simulada. Cargar imágenes, Control de
calidad y Modelo IA permanecieron en la regresión frontend aprobada.

## Evidencia PostgreSQL y residuos

Las consultas se ejecutan contra `malaria_experiments/public` sólo después de
confirmar la conexión:

```sql
SELECT current_database(), current_schema();

SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN (
    'cell_detection_runs',
    'image_connected_components',
    'cell_detections',
    'cell_crops',
    'cell_detection_events',
    'scientific_reviews'
  )
ORDER BY tablename;

SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN (
    'cell_detection_runs',
    'image_connected_components',
    'cell_detections',
    'cell_crops',
    'cell_detection_events',
    'scientific_reviews'
  )
  AND data_type IN ('bytea', 'bit', 'bit varying');
```

Se verificó mediante transacción revertida/fixtures de limpieza la ausencia de:

- filas sintéticas en las seis tablas;
- `audit_events` sintéticos;
- crops/temporales sintéticos;
- staging residual;
- schemas temporales;
- rutas absolutas o keys inseguras;
- originales modificados.

Resultado real:

```text
database=malaria_experiments schema=public alembic=20260727_05 head
prompt7_tables=6 constraints=81 indexes=26 trigger_events=12
rows_in_prompt7_tables=0
synthetic_audit_events=0
temporary_test_schemas=0
binary_columns=0
absolute_storage_keys=0
cell_crop_reconcile: metadata_rows=0 issues=0 mode=dry-run
original_storage_reconcile: issues=0
synthetic_crop_or_staging_residue=0
modified_originals=0
```

El E2E también confirmó que un fallo por checksum no deja
componentes/detecciones/crops parciales. Los SHA-256 de los originales se
mantuvieron antes y después.

## Evidencia sintética del detector

No se descargaron imágenes clínicas. Las ejecuciones sintéticas reales
produjeron:

| Caso | Resultado |
|---|---|
| círculo aislado | 1 candidato aceptado y crop correspondiente |
| tres círculos separados | 3 componentes en orden raster estable |
| círculos en contacto | 1 componente, limitación `component_separation=none` |
| imagen uniforme/vacía | 0 componentes y warning explícito |
| borde/pequeño/grande | persistidos como `rejected_by_filter` |
| 500 candidatos | 500 aceptados en 0.064 s |
| imagen 12 MP con 130 candidatos | 130 aceptados en 0.235 s |

El runtime de FastAPI usó Pillow 12.3. NumPy, SciPy, scikit-image y OpenCV no
estaban disponibles allí; no se agregó una dependencia pesada y no se ejecutó
watershed. Estos tiempos son evidencia técnica local, no métricas clínicas ni
un benchmark garantizado para otro hardware.

## Checklist científico y arquitectónico

| Afirmación | Evidencia | Estado |
|---|---|---|
| No se ejecutó clasificación celular | detector y DTO sólo producen candidatos/geometry | PASS |
| No se generó probabilidad/diagnóstico/parasitemia | revisión de API/UI/tests | PASS |
| No existe revisión masiva ni edición de bbox | rutas y controles inspeccionados | PASS |
| No hay worker, cola automática ni retry automático | ejecución manual en threadpool | PASS |
| Cola de Prompt 6 no modificada | diff sin cambios en su migración/servicio/rutas | PASS |
| `stage2/default` no modificado | diff y estado inspeccionados | PASS |
| No se usó Docker/otra DB/storage remoto | runtime local PostgreSQL/storage local | PASS |
| No hubo commit ni push | commit inicial/final idéntico | PASS |

## Cierre

Recomendación final: **APROBAR**.

La migración live, suites backend/frontend/PostgreSQL, build, compileall,
reconciliaciones y comprobaciones de residuos tienen evidencia real. No se
detectaron cajas fuera de límites, originales modificados, binarios en
PostgreSQL, rutas absolutas, mezcla de revisión/resultado automático ni
artefactos sintéticos residuales.

Riesgos aceptados: el detector Otsu es una línea base no clínica; sin watershed,
los contactos pueden quedar unidos; sus thresholds son académicos. Ninguno
autoriza clasificación, probabilidad o diagnóstico.
