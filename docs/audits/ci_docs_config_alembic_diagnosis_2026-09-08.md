# Diagnóstico CI — jobs `docs-config` y `alembic-static` (run 34253061688 y sucesores)

Fecha: 2026-09-08
Autor: revisión asistida (Claude Code), rol arquitecto CI/CD
Método: `gh` (GitHub CLI 2.100.0, autenticado como `JulioAlejandro-GitHub`), descarga de
logs completos de Actions, reproducción local en worktree aislado al SHA exacto de cada
run, lectura de `.github/workflows/ci.yml` y `scripts/check_docker_postgres_contract.py`.
**Ningún fix aplicado.** Logs guardados en `/tmp/ci-diag/`.

---

## Fase 0 — Acceso y hallazgo de encuadre

| Paso | Resultado |
|---|---|
| `gh` disponible | No → instalado con `brew install gh` (2.100.0) |
| `gh auth login` | Ejecutado por el usuario (web browser), `✓ Logged in as JulioAlejandro-GitHub` |
| `gh run view 34253061688 --json headSha` | **`335b8eb8118d463c7d33578d310e84689944813e`** — commit *"delete rutas legacy"* |

### ⚠️ El run 34253061688 NO contiene el fix de Alembic

El run que se pidió diagnosticar corre sobre **`335b8eb8`**, que es el **padre** del commit
del fix `f44f8063 "alembic ok"`. La cadena real de `main` es:

```
003aa681  Create model_training_pipeline.md      run 34262292102  (HEAD actual)
f44f8063  alembic ok            ← FIX ESTRUCTURAL run 34259260381
335b8eb8  delete rutas legacy                     run 34253061688  ← el que se pidió
d71bded2  RESET MALARIA SMEAR ANALYSIS            run 34172183419
```

Matriz de resultados (todas obtenidas con `gh run view <id> --json jobs`):

| Run | SHA | `alembic-static` | `docs-config` |
|---|---|:--:|:--:|
| 33711166050 | c0b7686b | ❌ | ✅ |
| 33892559445 | a9d60ead | ❌ | ✅ |
| 34109821484 | **a99ffcd5** | ❌ | ❌ ← **regresión docs-config aquí** |
| 34172183419 | d71bded2 | ❌ | ❌ |
| **34253061688** | **335b8eb8** | ❌ | ❌ ← *el run del enunciado* |
| 34259260381 | **f44f8063** | ✅ ← **fix aplicado** | ❌ |
| 34262292102 | 003aa681 (HEAD) | ✅ | ❌ |

**Conclusiones de encuadre:**
1. **`alembic-static` YA ESTÁ ARREGLADO** en `main`. Falla en el run 34253061688 porque ese
   run es anterior a `f44f8063`. En `f44f8063` y en el HEAD actual (`003aa681`) **pasa**.
   El diagnóstico de abajo documenta la causa raíz histórica y confirma el fix.
2. **`docs-config` es el único job realmente roto hoy en `main`.** No es "CI contra código
   viejo": falla en el HEAD actual, reproducido localmente byte a byte.
3. `docs-config` **regresó en `a99ffcd5` "postgresql-client"** (2026-09-07); antes estaba
   verde. Luego `335b8eb8` sumó una infracción y `003aa681` sumó otra (esta última
   introducida por el documento `model_training_pipeline.md` creado en la tarea anterior).

---

## Job 1 — `alembic-static`

### 1.1 Cita textual del error (run 34253061688 @ `335b8eb8`, job `102151983048`)

`/tmp/ci-diag/alembic-static.log`, líneas 293-319. El paso del YAML era un heredoc inline
(no un script; en `335b8eb8` `scripts/db/check_alembic_linearity.py` **no existía**):

```
293  ##[group]Run PYTHONPATH=backend_api python - <<'PY'
295  from alembic.config import Config
296  from alembic.script import ScriptDirectory
298  scripts = ScriptDirectory.from_config(Config('alembic.ini'))
299  heads = scripts.get_heads()
300  revisions = list(scripts.walk_revisions())
301  assert heads == ['20260812_02'], f'expected head 20260812_02, found {heads}'
...
316  Traceback (most recent call last):
317    File "<stdin>", line 7, in <module>
318  AssertionError: expected head 20260812_02, found ['20260901_01']
319  ##[error]Process completed with exit code 1.
```

El fallo es en **la línea 7 del heredoc** = `assert heads == ['20260812_02']`. La segunda
aserción (historial lineal, líneas 302-305) **nunca se evaluó**; el historial sí es lineal.

### 1.2 Diferencias de dependencias CI vs. local

| | CI (log 34253061688, líneas 120-164) | Local (este diagnóstico) |
|---|---|---|
| Python | 3.12.14 (`actions/setup-python@v5`, `python-version: 3.12`) | 3.12 (`malaria_dl_local_project/.venv`) |
| alembic | 1.19.2 | 1.18.5 |
| SQLAlchemy | 2.0.52 | 2.0.51 |

`ScriptDirectory.get_heads()` / `walk_revisions()` es API estable en todo el rango
1.14–1.19; la diferencia de versión **no** influye. El head se calcula leyendo
`alembic/versions/*.py` y siguiendo `down_revision`.

### 1.3 Reproducción local (worktree aislado)

```
$ git worktree add /tmp/ci-debug 335b8eb8
$ cd /tmp/ci-debug
$ PYTHONPATH=backend_api <venv>/python - <<'PY'   # heredoc EXACTO del CI
...
AssertionError: expected head 20260812_02, found ['20260901_01']
heredoc exit=1
$ ls alembic/versions/*.py | wc -l
21
```

**Reproduce idéntico.** El head real es `20260901_01`; el constante en `ci.yml` es
`20260812_02` (desactualizado por 2 migraciones: `20260829_01_persist_training_release_status.py`
y `20260901_01_single_evaluation_training_parent.py`).

### 1.4 Causa raíz

Constante hardcodeada `'20260812_02'` en `.github/workflows/ci.yml` que fue quedando
obsoleta a medida que se añadieron migraciones. Es exactamente el hallazgo de
[`docs/audits/architecture_audit_2026-09-08.md`](architecture_audit_2026-09-08.md) §6.1 y
el objeto de [`docs/audits/alembic_ci_gate_fix_2026-09-08.md`](alembic_ci_gate_fix_2026-09-08.md).
No es un historial no lineal ni un problema de entorno del runner.

### 1.5 Estado del fix (`f44f8063` → HEAD)

`git diff 335b8eb8 f44f8063 -- .github/workflows/ci.yml`:

```diff
-      - name: Validate linear Alembic history
-        run: |
-          PYTHONPATH=backend_api python - <<'PY'
-          ...
-          assert heads == ['20260812_02'], f'expected head 20260812_02, found {heads}'
-          ...
-          PY
+      - name: Validate linear Alembic history
+        run: python scripts/db/check_alembic_linearity.py
+      - run: PYTHONPATH=backend_api pytest backend_api/tests/test_check_alembic_linearity.py
```

`scripts/db/check_alembic_linearity.py` **deriva** el head en vez de compararlo con un
literal. Verificado localmente en el HEAD actual:

```
$ python scripts/db/check_alembic_linearity.py
OK: historial Alembic lineal, 21 revisiones, head único 20260901_01     (exit 0)
$ PYTHONPATH=backend_api pytest backend_api/tests/test_check_alembic_linearity.py -q
8 passed
```

Coincide con el log del run 34259260381 (líneas 307-334). **`alembic-static` no requiere
más acción**; solo re-ejecutar CI o esperar el próximo push.

---

## Job 2 — `docs-config`

### 2.1 Qué paso falla (no inferido — citado)

Orden del job (`ci.yml` @ HEAD):

```yaml
  docs-config:
    steps:
      - uses: actions/checkout@v4
      - run: git diff --check
      - run: python scripts/check_docker_postgres_contract.py
      - run: test -f .env.example && test -f docs/engineering/configuration.md
```

**El paso que devuelve exit 1 es `python scripts/check_docker_postgres_contract.py`.**

- **`git diff --check` PASA.** Log run 34253061688 (`/tmp/ci-diag/docs-config.log`) líneas
  105-109: grupo abierto (105), comando (106), shell (107), `##[endgroup]` (108) y
  **directamente** el grupo del paso siguiente (109), sin salida ni error entre medias.
  Idéntico en el log de `f44f8063` (líneas 105-109) y `003aa681`
  (`/tmp/ci-diag/docs-config_003aa681.log` líneas 105-109). Confirmado local:
  `git diff --check` y `git diff HEAD --check` → exit 0.
- **`test -f …` NUNCA se ejecuta** (el shell es `bash -e`; el job ya abortó). De todos
  modos ambos archivos existen en `335b8eb8` y en HEAD (`git show <sha>:<path>` → OK).

### 2.2 Cita textual del error

**Run 34253061688 @ `335b8eb8`** (`/tmp/ci-diag/docs-config.log` líneas 113-117):

```
113  PG_DSN_HOST backend_api/tests/test_db_purge_tool.py:235: DSN PostgreSQL dirigido al host; contrato esperado: db:5432
114  PG_DSN_HOST backend_api/tests/test_smear_reset_tool.py:78: DSN PostgreSQL dirigido al host; contrato esperado: db:5432
115  HOST_POSTGRES_BINARY scripts/storage/reset_smear_analysis.py:902: binario PostgreSQL invocado directamente desde el host; contrato esperado: db:5432
116  Contrato PostgreSQL Docker: FALLÓ (3 infracciones, 678 archivos revisados, 22 excepciones contractuales).
117  ##[error]Process completed with exit code 1.
```

**Run 34262292102 @ `003aa681` (HEAD actual)** (`/tmp/ci-diag/docs-config_003aa681.log` líneas 113-118):

```
113  PG_DSN_HOST backend_api/tests/test_db_purge_tool.py:235: ...
114  PG_DSN_HOST backend_api/tests/test_smear_reset_tool.py:78: ...
115  PG_DSN_HOST docs/engineering/model_training_pipeline.md:162: ...          ← NUEVA
116  HOST_POSTGRES_BINARY scripts/storage/reset_smear_analysis.py:929: ...     (era :902, desplazada por f44f8063)
117  Contrato PostgreSQL Docker: FALLÓ (4 infracciones, 682 archivos revisados, 22 excepciones contractuales).
118  ##[error]Process completed with exit code 1.
```

### 2.3 Reproducción local

En el árbol de trabajo (HEAD `003aa681`, limpio) y en worktree a `335b8eb8`:

```
$ python3 scripts/check_docker_postgres_contract.py          # @ 003aa681
PG_DSN_HOST backend_api/tests/test_db_purge_tool.py:235: ...
PG_DSN_HOST backend_api/tests/test_smear_reset_tool.py:78: ...
PG_DSN_HOST docs/engineering/model_training_pipeline.md:162: ...
HOST_POSTGRES_BINARY scripts/storage/reset_smear_analysis.py:929: ...
Contrato PostgreSQL Docker: FALLÓ (4 infracciones, 682 archivos revisados, 22 excepciones contractuales).   exit=1

$ cd /tmp/ci-debug && python3 scripts/check_docker_postgres_contract.py   # @ 335b8eb8
... (3 infracciones, 678 archivos revisados, 22 excepciones contractuales)   exit=1
```

**Reproduce byte a byte** ambos SHA (mismos números de línea, mismos totales). El checker
es regex + `ast` puro, sin sensibilidad a la versión de Python (local 3.14 / 3.12; CI 3.12).

### 2.4 Análisis de las 4 infracciones

> Este documento **cita las líneas ofensoras por `archivo:línea`, no textualmente**, para
> no disparar el propio checker que diagnostica (los `.md` no son allowlistables). Abrir
> cada referencia para ver el literal.

| # | Ubicación | Regla | Introducida en | ¿Infracción real? |
|---|---|---|---|---|
| 1 | `backend_api/tests/test_db_purge_tool.py:235` | `PG_DSN_HOST` | **`335b8eb8`** (`git log -S`) | **No — falso positivo.** Línea dentro de `@pytest.mark.parametrize("url", [...])` en `test_build_engine_rejects_non_canonical_urls`: es un **caso negativo** (un DSN con host `localhost`) que existe para asertar que `purge.build_engine(url)` **lanza `PurgeRefused`**. El test *refuerza* el contrato Docker-only. |
| 2 | `backend_api/tests/test_smear_reset_tool.py:78` | `PG_DSN_HOST` | **`a99ffcd5`** | **No — falso positivo.** Idéntico patrón: caso negativo (DSN `postgresql+psycopg` con host `localhost`) en `test_rejects_noncanonical_database_address`, asertando `reset.validate_url(url)` → `ResetRefused`. |
| 3 | `docs/engineering/model_training_pipeline.md:162` | `PG_DSN_HOST` | **`003aa681`** | **Sí, pero es un artefacto de la tarea anterior.** La línea es prosa del hallazgo H6 que cita el valor `DATABASE_URL` con host `localhost`. Además **el hallazgo es fácticamente incorrecto**: dice "el `.env` **versionado**" pero `.env` está en `.gitignore:38` — no se versiona. Solo `.env.example` se versiona, y ahí `DATABASE_URL` no aparece con host local. |
| 4 | `scripts/storage/reset_smear_analysis.py:929` | `HOST_POSTGRES_BINARY` | **`a99ffcd5`** | **Discutible — regex demasiado amplia.** La línea es un `shutil.which(...)` para el binario `pg_restore`. El segundo patrón de la regla, `[\[(]\s*['"](?:psql\|pg_dump\|pg_restore\|pg_isready)['"]`, matchea la llamada a `which`. El uso real (líneas 929-935) es `pg_restore --list` sobre un **archivo** de dump para validar **offline** que el backup es restaurable — **no abre ninguna conexión** a `db:5432` ni a ningún host. La línea 931 dice literalmente `"pg_restore no está disponible en el contenedor"`: el script se diseñó para correr **dentro** del contenedor `backend` (que trae `postgresql-client` desde `a99ffcd5`). |

**Ninguna de las 4 es una violación semántica del contrato "PostgreSQL solo vía Docker
`db:5432`".** Son: 2 tests que *aplican* el contrato (1, 2), 1 línea de documentación con
un error de fondo (3), y 1 inspección offline de archivo dentro del contenedor gobernado (4).

### 2.5 Causa raíz

`scripts/check_docker_postgres_contract.py` es un **gate estático con allowlist mantenida a
mano** (`ALLOWLIST`, líneas 97-112) que **solo admite archivos de test `.py` exactos**
(`validate_allowlist`, líneas 258-296) y una única exención de código
(`_docker_governed_native_command`, líneas 155-161, que solo reconoce
`docker compose exec -T db`).

Tres commits añadieron contenido que dispara las reglas **sin actualizar la allowlist**:

- **`a99ffcd5` "postgresql-client"** (2026-09-07): creó `scripts/storage/reset_smear_analysis.py`
  (884 líneas nuevas) y `backend_api/tests/test_smear_reset_tool.py` (600 líneas nuevas),
  añadió `postgresql-client` al `backend_api/Dockerfile`. **No tocó
  `check_docker_postgres_contract.py` ni su `ALLOWLIST`.** → infracciones 2 y 4, docs-config
  pasa de ✅ a ❌.
- **`335b8eb8` "delete rutas legacy"**: añadió el `parametrize` con `@localhost` en
  `test_db_purge_tool.py`. → infracción 1.
- **`003aa681`**: el documento `model_training_pipeline.md` (creado en la tarea anterior,
  commiteado vía web UI de GitHub — mensaje "Create …"). → infracción 3.

Es **la misma clase de fragilidad que `alembic-static`**: un gate de CI con expectativas
declaradas a mano que se desincronizan del repositorio a medida que este evoluciona
(architecture_audit §6.1: *"un gate de CI que ya no protege lo que dice proteger"*). Pero
es **código y fallo independientes**: `f44f8063` arregló solo el de Alembic.

### 2.6 Hallazgo de proceso

`docs-config` lleva **roto desde `a99ffcd5` (2026-09-07)** y `alembic-static` desde antes de
`c0b7686b` (2026-09-03), y aun así se hicieron ≥5 pushes a `main` encima. **CI en `main` no
está bloqueando merges** (sin branch protection efectiva, o push directo). Esto en un
sistema con trazabilidad clínica como objetivo de diseño es en sí mismo un hallazgo.

---

## ¿Comparten causa raíz?

**Parcialmente.** Misma *categoría* (gate de CI con constante/lista hardcodeada que se
desincroniza del repo real), documentada ya en architecture_audit §6.1. Pero:

- **NO comparten commit causante**: `alembic-static` se rompió por el literal `20260812_02`
  en `ci.yml` (histórico); `docs-config` regresó por `a99ffcd5` sin actualizar la allowlist
  del contract-checker.
- **NO comparten fix**: `f44f8063` arregló solo Alembic (heredoc → `check_alembic_linearity.py`
  derivado). `docs-config` sigue sin tocar.
- El run 34253061688 los muestra fallando juntos **por coincidencia temporal**, no por una
  causa común en `335b8eb8`.

---

## Propuestas de fix (NO aplicadas)

### F1 — `alembic-static`: nada

Ya resuelto en `f44f8063`. Acción: re-lanzar el workflow del HEAD actual (`gh run rerun
34262292102` o un push) para que el check verde quede registrado sobre `main`.

### F2 — `docs-config` / infracciones 1 y 2 (tests): ampliar `ALLOWLIST`

En `scripts/check_docker_postgres_contract.py`, `ALLOWLIST` (línea 97), añadir:

```python
"backend_api/tests/test_db_purge_tool.py": {"PG_DSN_HOST": 1},
"backend_api/tests/test_smear_reset_tool.py": {"PG_DSN_HOST": 1},
```

Justificación: es el mismo mecanismo ya usado para
`backend_api/tests/test_database_url_contract.py: {"PG_DSN_HOST": 4}`. `validate_allowlist`
verifica el conteo exacto (hoy 1 en cada archivo — comprobado: las demás URLs de esos
`parametrize` usan host `db` o esquema no-postgresql y no matchean). Si un futuro cambio
añade otra URL `@localhost`, el gate volverá a fallar con `STALE_ALLOWLIST_ENTRY`,
forzando revisión humana. Coste: 2 líneas. Riesgo: nulo.

### F3 — `docs-config` / infracción 4 (`reset_smear_analysis.py:929`): decisión del equipo

El script corre **dentro** del contenedor `backend` y usa `pg_restore --list` para
inspección **offline** de un archivo. Opciones, de menor a mayor cambio:

1. **Exención dirigida en el checker.** Extender `_docker_governed_native_command` (o añadir
   una regla hermana) para reconocer `pg_restore`/`pg_dump` en `--list`/inspección de
   archivo, o `shutil.which("<bin>")` (chequeo de disponibilidad, no ejecución). ~5 líneas.
2. **Allowlist para no-tests.** Hoy `validate_allowlist` rechaza todo lo que no sea test
   `.py`. Añadir una segunda estructura `ALLOWLIST_NON_TEST` para
   `scripts/storage/reset_smear_analysis.py: {"HOST_POSTGRES_BINARY": 1}` con la misma
   verificación de conteo exacto.
3. **Marcador inline.** Soportar un comentario `# docker-postgres-contract: allow  <razón>`
   en la línea, que el scanner exima. Más general, más código.

Recomendación: **opción 1** (la regla `HOST_POSTGRES_BINARY` describe *"invocado desde el
host"* — `shutil.which(...)` no lo es; afinar el patrón es corregir el checker, no
debilitarlo).

### F4 — `docs-config` / infracción 3 (`model_training_pipeline.md:162`): reescribir el hallazgo H6

Dos problemas en esa línea, ambos originados en la tarea anterior:

1. **CI**: la línea contiene un DSN con esquema `postgresql://` y host local que matchea
   `PG_DSN_HOST`. Los `.md` **no** son allowlistables (`validate_allowlist` exige `.py` de
   test). Hay que **reformular sin el patrón** — describir "un DSN cuyo host es `localhost`"
   sin el prefijo de esquema, o usar solo ejemplos con host `db` (como hace este documento).
2. **Corrección de fondo**: el hallazgo H6 afirma "el `.env` **versionado**". `.env` está
   en `.gitignore:38`; **no se versiona**. Lo verificable es: `.env.example` (sí versionado)
   documenta `DATABASE_URL` como inyectado por Compose hacia `db:5432`, y no existe una
   plantilla de entorno que produzca una config ejecutable en host; toda corrida gobernada
   de TRAIN en BD corrió en el host macOS, lo que exige `DATABASE_URL=…@db:5432` + alias
   `db → 127.0.0.1` no documentado. Reescribir H6 en esos términos.

Alternativa: si el equipo considera que ese documento no debería haber entrado por web UI
sin pasar CI, revertir `003aa681` y reintroducirlo corregido en un PR.

### F5 — Proceso: activar branch protection en `main`

Exigir `docs-config`, `alembic-static`, `backend-unit`, `frontend`, `ml-fast` en verde
antes de permitir merge/push a `main`. Sin esto, los gates son informativos, no
protectores.

---

## Evidencia (archivos)

- `/tmp/ci-diag/docs-config.log` — run 34253061688 @ 335b8eb8 (134 líneas)
- `/tmp/ci-diag/alembic-static.log` — run 34253061688 @ 335b8eb8 (336 líneas)
- `/tmp/ci-diag/docs-config_f44f8063.log` — run 34259260381 @ f44f8063
- `/tmp/ci-diag/docs-config_003aa681.log` — run 34262292102 @ 003aa681 (HEAD)
- Worktree de reproducción: `/tmp/ci-debug` (eliminado tras el diagnóstico;
  `git worktree add /tmp/ci-debug 335b8eb8` para recrearlo)
