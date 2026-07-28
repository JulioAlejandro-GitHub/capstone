# Validación reproducible de Prompt 8

## Recomendación con la evidencia disponible

**RECHAZAR.** El código implementa un bloqueo seguro, pero el entorno observado
no permite demostrar el E2E obligatorio con el modelo productivo real:

1. no existe ningún deployment activo `stage2/default`; la publicación activa
   es sólo catálogo y no puede usarse como fallback;
2. el venv ML local contiene TensorFlow, pero le faltan `PyJWT`, `pwdlib` y
   `python-multipart`, necesarias para servir la API combinada. Las tres
   dependencias quedaron declaradas y el startup las valida, pero no fueron
   instaladas ni descargadas dentro de este prompt.

Los gates de código, PostgreSQL, frontend, build, compilación y reconciliación
sí fueron ejecutados. Que pasen no sustituye la prueba con un
`stage2/default` real ni el runtime API/ML completo.

## Fuente de verdad y conducta segura

La única identidad inferible es exactamente un registro activo de
`deployed_model_versions` con `environment=stage2` y `alias=default`, enlazado al
mismo `model_version_id` de una publicación Stage 2 activa. No son fuentes de
verdad:

- una fila de `stage2_model_publications` por sí sola;
- el último TRAIN/EVALUATE;
- un checkpoint encontrado en disco;
- un threshold `0.5` no publicado.

Slot ausente o duplicado produce `PRODUCTIVE_MODEL_NOT_UNIQUE`; los demás
contratos inválidos producen códigos tipados específicos. En todos esos casos
el workflow permanece en `awaiting_productive_model`. No se crea un run de
clasificación ni se ejecuta inferencia con un candidato alternativo.

## Evidencia confirmada

### Precheck de entorno y datos

| Dato | Evidencia |
|---|---|
| Rama/commit inicial | `main` / `29bf45d63a8310a87879b4939c7a979342ddf541` |
| Working tree inicial | limpio |
| PostgreSQL | 17.9 Homebrew |
| Base/schema | `malaria_experiments` / `public` |
| Alembic inicial | `20260727_05 (head)` |
| Detección/crops | 1 run completado, 42 detecciones y 42 crops |
| Reconciliación crops | `metadata_rows=42 issues=0 mode=dry-run` |
| `deployed_model_versions` | 0 filas; no existe `stage2/default` |
| Publicación de catálogo | 1 activa; no utilizable como fallback |
| Checkpoint de esa publicación | archivo regular y SHA-256 verificado; no concede identidad productiva |
| Clasificaciones previas de Prompt 8 | ninguna |

No se entrenó, evaluó, calibró, publicó, promovió ni descargó ningún modelo. No
se modificó `stage2/default`, no se usó Docker y no se hizo commit o push.

### Verificaciones ya ejecutadas

| Gate | Resultado confirmado | Alcance |
|---|---|---|
| Backend baseline | `144 passed, 28 skipped` | antes de integrar los cambios finales de Prompt 8 |
| Frontend baseline | `108 passed`; build PASS | antes de integrar los cambios finales de Prompt 8 |
| Contrato workflow/RBAC dirigido | `40 passed` | tests dirigidos de workflow y matriz de permisos |
| Compilación dirigida | PASS | módulos nuevos principales, no reemplaza `compileall` final |
| Migraciones Prompt 8 | upgrade lineal PASS | `20260728_01 → 20260728_02 → 20260728_03` |
| Reconciliación de crops | PASS, 42 filas y 0 issues | dry-run |
| Grad-CAM real | PASS | TensorFlow CPU, heatmap `(20, 20)` y overlay `(20, 20, 3)` |

El E2E de inferencia con el modelo real no se ejecutó: el resolver bloqueó de
forma correcta la ausencia de `stage2/default`, sin fallback.

## Migraciones y contrato de summary

Prompt 8 requiere la cadena lineal completa:

| Revisión | Contrato |
|---|---|
| `20260728_01` | tablas, FKs/checks, append-only, explicaciones y resumen automático |
| `20260728_02` | reestablece la validación fuerte del resumen sobre predicciones inmutables |
| `20260728_03` | fija la forma canónica final `per_image_summary = {"images": [...]}` |

El head esperado tras la validación final es `20260728_03`. El endpoint
`/classification-runs/{id}/summary` devuelve:

```json
{
  "automatic_summary": {},
  "reviewed_summary": {
    "kind": "reviewed_projection",
    "automatic_summary_unchanged": true
  }
}
```

`automatic_summary` es persistido e inmutable. `reviewed_summary` se deriva en
lectura desde las últimas revisiones efectivas y nunca reescribe labels,
probabilidades ni el agregado automático.

## Grad-CAM, allowlists y storage

Grad-CAM se genera únicamente mediante un POST manual para una predicción. No
hay generación automática, masiva ni retry automático; un fallo sólo se
reintenta con `{"retry": true}` explícito.

Los filtros, enums, orden y bodies de la API están limitados por allowlists. El
storage sólo admite claves relativas confinadas bajo `STORAGE_ROOT`, sin
traversal ni symlinks. Heatmap y overlay son PNG create-only bajo
`cell-explanations/`, con tamaño y SHA-256; PostgreSQL conserva metadata, no
binarios. Los payloads públicos no exponen storage keys, paths físicos,
checkpoint paths, secretos ni tokens.

## Runtime local

`malaria_dl_local_project/requirements.txt` declara ahora el conjunto API/ML,
incluidas:

```text
PyJWT>=2.9.0,<3.0
pwdlib[argon2]>=0.2.1,<1.0
python-multipart>=0.0.20,<1.0
```

`scripts/start_backend_api.sh` usa el Python del venv ML y realiza un preflight
de imports antes de iniciar Uvicorn. En el entorno observado esas tres
dependencias siguen faltando. No se instaló nada porque este prompt prohíbe
descargas; la sincronización del venv debe ocurrir en una operación controlada
fuera de este alcance y luego debe repetirse toda la validación.

## Gates finales

| Gate | Estado | Resultado exacto |
|---|---|---|
| Alembic upgrade a `20260728_03` | PASS | cadena lineal aplicada sin downgrade ni stamp |
| Alembic current=head y heads único | PASS | current=`20260728_03`; head=`20260728_03` |
| Suite backend completa post-integración | PASS | `185 passed, 37 skipped, 5 warnings` |
| Tests opt-in PostgreSQL | PASS | `31 passed, 191 deselected, 5 warnings` |
| Suite PostgreSQL específica Prompt 8 | PASS | `7 passed, 1 warning`; rollback externo |
| Suite frontend completa post-integración | PASS | `123 passed, 0 failed` |
| Build frontend post-integración | PASS | TypeScript + Vite; warning no bloqueante por chunk de 548.48 kB |
| `compileall` backend/scripts/migraciones | PASS | salida vacía, exit 0 |
| Lógica de batches 1/50/500 | PASS | `3 passed`; 500 entradas en 16 batches (`15×32 + 20`) |
| Grad-CAM compatible real | PASS | `gradcam-runtime-ok conv_for_validation (20, 20) (20, 20, 3)` |
| Reconciliación originales | PASS | `issues=0 mode=dry-run` |
| Reconciliación crops final | PASS | `metadata_rows=42 issues=0 mode=dry-run` |
| Reconciliación explicaciones/staging | PASS | `metadata_rows=0 issues=0 mode=dry-run` |
| Inspección PostgreSQL | PASS | 7 tablas presentes; constraints/triggers ejercidos; `bytea_columns=0` |
| Ausencia de residuos/synthetic rows | PASS | 0 filas en las 7 tablas; 0 schemas temporales; 0 claves absolutas |
| `git diff --check` | PASS | salida vacía, exit 0 |
| E2E con `stage2/default` real y modelo usado verificable | BLOQUEADO | slot inexistente |
| Startup del runtime API/ML | BLOQUEADO | preflight exit 1: dependencias declaradas pero no instaladas |

## Comandos de cierre

```bash
git diff --check
pg_isready -h localhost -p 5432
psql "$DATABASE_URL" -c "SELECT version(),current_database(),current_schema();"
backend_api/.venv/bin/alembic current
backend_api/.venv/bin/alembic heads
(cd backend_api && PYTHONPATH=. .venv/bin/pytest tests -q -rs)
(cd backend_api && TEST_EXECUTION=true PYTHONPATH=. .venv/bin/pytest \
  tests -m requires_local_postgres -q -rs)
npm --prefix frontend test
npm --prefix frontend run build
backend_api/.venv/bin/python -m compileall backend_api/app scripts
backend_api/.venv/bin/python scripts/storage/reconcile.py
backend_api/.venv/bin/python scripts/storage/reconcile_cell_crops.py
backend_api/.venv/bin/python scripts/storage/reconcile_cell_explanations.py
malaria_dl_local_project/.venv/bin/python -c \
  "import fastapi,jwt,multipart,numpy,pwdlib,sqlalchemy,tensorflow,uvicorn"
```

## Límite científico

Los labels y outcomes son resultados experimentales sobre células candidatas.
La fracción de candidatos no es parasitemia, prevalencia, probabilidad de
enfermedad ni diagnóstico. Grad-CAM es una ayuda explicativa técnica y tampoco
constituye evidencia clínica.
