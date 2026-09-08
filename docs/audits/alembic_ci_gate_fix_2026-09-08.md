# Fix estructural del gate de Alembic en CI

Fecha: 2026-09-08 · Rama: `main` · Alembic head real del repo: `20260901_01` (21 revisiones,
historial lineal). Este documento cubre **solo el mecanismo de validación**; no se agregó,
modificó ni reordenó ninguna revisión de Alembic.

---

## 1. Qué estaba mal

`.github/workflows/ci.yml`, job `alembic-static`, validaba el historial con un bloque
Python inline y un head fijado como string literal:

```python
assert heads == ['20260812_02'], f'expected head 20260812_02, found {heads}'
assert not any(r.is_branch_point or r.is_merge_point for r in revisions), 'expected a linear Alembic history'
```

Problemas de diseño:

- **Frágil por construcción.** Cada nueva migración obliga a editar el YAML a mano. Si
  alguien lo olvida, el gate no falla de forma útil: valida un head que ya no existe. En
  este repo el literal quedó en `20260812_02` mientras el head real avanzó a `20260901_01`
  (dos migraciones después: `20260829_01`, `20260901_01`), así que el gate llevaba tiempo
  "mintiendo".
- **Lógica no reutilizable.** Vivía dentro de un heredoc YAML: no se podía ejecutar en
  local antes de un push ni testear de forma aislada.
- **Mensaje de error pobre.** "expected a linear Alembic history" no dice qué revisión
  rompe la linealidad.

## 2. Qué cambió

### 2.1 Script versionado y testeable

**Nuevo:** [`scripts/db/check_alembic_linearity.py`](../../scripts/db/check_alembic_linearity.py)

- Deriva **todo** del `ScriptDirectory` en disco (`alembic/versions/`). No hay ningún head
  esperado, ni en el YAML, ni en el script, ni en ningún archivo paralelo que haya que
  mantener a mano.
- Protege exactamente las dos propiedades que protegía el assert anterior:
  1. **Un único head** (`len(get_heads()) == 1`).
  2. **Historial lineal**: ningún `is_branch_point` ni `is_merge_point` en todo el árbol.
- La garantía es *"un único head lineal"*, no *"el head es tal valor"*. Si mañana entran
  dos heads simultáneos, un branch point o un merge point, **el script falla**; nunca se
  vuelve un test que "siempre pasa".
- **Mensajes accionables:**
  - Múltiples heads → los lista con su archivo.
  - Branch point → identifica la revisión (id + archivo repo-relativo) y sus revisiones
    hijas.
  - Merge point → identifica la revisión (id + archivo) y sus revisiones padre.
- Es cwd-independiente (resuelve `script_location` contra la ubicación de `alembic.ini`).
- Reutilizable como módulo: expone `resolve_linear_head()` / `check_linear_history()` /
  `load_script_directory()`.

**Nuevo:** [`backend_api/tests/test_check_alembic_linearity.py`](../../backend_api/tests/test_check_alembic_linearity.py)
— tests unitarios con `ScriptDirectory` de fixture construidos en `tmp_path` (no contra el
repo real):

| Caso | Resultado esperado |
|---|---|
| Lineal con un head (`r1→r2→r3`) | pasa, devuelve `r3` |
| Dos raíces independientes (`alpha`, `omega`) | falla, lista ambos heads con archivo |
| Branch point intermedio (diamante `root→{left,right}→merge`) | falla, nombra `root` + archivo |
| Merge point (mismo diamante) | falla, nombra `merge` + archivo |
| `versions/` vacío | falla |
| CLI `main()` sobre fixture lineal / con branch | `0` / `1` + mensaje |
| Árbol **real** del repo | pasa, head derivado == `script.get_heads()[0]` (sin constante) |

### 2.2 CI

`.github/workflows/ci.yml`, job `alembic-static`: el bloque inline se reemplaza por

```yaml
- name: Validate linear Alembic history
  run: python scripts/db/check_alembic_linearity.py
- run: PYTHONPATH=backend_api pytest backend_api/tests/test_check_alembic_linearity.py
```

Sin lógica de validación duplicada en el YAML. El job ya compilaba `scripts/db` con
`compileall`, así que el script nuevo también entra ahí. Se corre además su test unitario
en el mismo job para atar la correctitud del script al gate (el job `backend-unit` ya lo
recogería por descubrimiento, pero el gate queda autocontenido).

### 2.3 Makefile — `make check-alembic-linearity`

Nuevo target que ejecuta el mismo script en local (usa `backend_api/.venv/bin/python` si
existe, si no `python` del PATH). Permite reproducir el gate **antes** de hacer push, no
descubrirlo en CI. Documentado junto al resto de targets de base de datos en
[`docs/engineering/postgresql_docker_single_instance.md`](../engineering/postgresql_docker_single_instance.md).

### 2.4 Otras referencias a un head hardcodeado (requisito de robustez 2)

Búsqueda: `grep -rn "20260812_02\|20260901_01\|20260829_01"` sobre `*.md *.yml *.sh *.py Makefile`.

| Ubicación | Antes | Ahora |
|---|---|---|
| `scripts/db/purge.py` | `EXPECTED_HEAD = "20260901_01"` | `_repo_linear_head()` deriva el head del `ScriptDirectory` en runtime y exige linealidad; si el historial no es lineal, `PurgeRefused`. |
| `scripts/storage/reset_smear_analysis.py` | `EXPECTED_HEAD = "20260901_01"` | `EXPECTED_HEAD = _repo_linear_head()` — derivado en import; si el historial no es lineal el módulo no importa (fail-closed). El resto del modelo plan/replay no cambia. |
| `scripts/db/verify_alembic_adoption.py` | ya derivaba (`_linear_head()`) | sin cambios; es el precedente del repo para esta derivación inline en guards. |
| `.github/workflows/ci.yml` | `heads == ['20260812_02']` | derivado (ver 2.2). |
| `docs/architecture/cell_classification_data_model.md`, `docs/architecture/scientific_validation.md` | "El head versionado actual es `20260812_02`" (prescriptivo) | "se deriva del repositorio (`make check-alembic-linearity` / `alembic heads`)". |

Se decidió **no** compartir un único módulo entre los tres guards (`purge.py`,
`reset_smear_analysis.py`, `verify_alembic_adoption.py`) y `check_alembic_linearity.py`: el
Dockerfile copia archivos individuales al `/app` del contenedor y cada guard se carga de
forma aislada (`importlib.util.spec_from_file_location`) en sus tests. Un helper local de
~10 líneas por guard, fail-closed, evita añadir acoplamiento entre directorios y una nueva
línea `COPY`. `check_alembic_linearity.py` es la implementación canónica y testeada; los
guards solo necesitan "un head lineal o rechazo", que es trivialmente correcto inline.

**Referencias hardcodeadas que se dejan fijas a propósito:**

- **Docs de auditoría / diagnóstico con fecha** (`docs/audits/*`, `docs/diagnóstico
  read-only…md`, `docs/codebase_dead_code_and_legacy_audit.md`,
  `malaria_dataset_split_project/docs/*`, `docs/engineering/alembic_runtime_validation.md`
  y `prompt8_validation.md`): son *snapshots* de un momento concreto. Su valor histórico
  depende de que **no** cambien. No son guía operativa vigente.
- **Tests de contenido de una migración concreta**
  (`backend_api/tests/test_training_release_status_migration.py`,
  `malaria_dl_local_project/tests/test_evaluation_training_lineage_migration.py`): afirman
  el `revision` / `down_revision` de una revisión *ya aplicada e inmutable*. El id de una
  revisión y su padre nunca cambian por política (`docs/engineering/alembic_simple_policy.md`),
  así que aquí el literal es correcto, no frágil.
- **Fuera de alcance (anotado):** varios tests `*_postgres.py` de
  `malaria_dl_local_project/tests/` afirman `SELECT version_num FROM alembic_version ==
  "20260901_01"` tras correr las migraciones. Eso sí es el mismo antipatrón, pero (a) están
  marcados como integración con PostgreSQL y **no corren en CI**, y (b) tocarlos excede
  "exclusivamente el mecanismo de validación en CI". Follow-up sugerido: derivar el
  esperado con `resolve_linear_head()` en su helper común.

---

## 3. Evidencia — pasa contra el estado real del repo

```
$ python scripts/db/check_alembic_linearity.py
OK: historial Alembic lineal, 21 revisiones, head único 20260901_01

$ make check-alembic-linearity
OK: historial Alembic lineal, 21 revisiones, head único 20260901_01

$ PYTHONPATH=backend_api pytest backend_api/tests/test_check_alembic_linearity.py -q
8 passed

$ PYTHONPATH=backend_api pytest backend_api/tests/test_db_purge_tool.py \
      backend_api/tests/test_smear_reset_tool.py \
      backend_api/tests/test_check_alembic_linearity.py \
      backend_api/tests/test_training_release_status_migration.py -q
204 passed
```

Equivalente exacto del job `alembic-static` ejecutado en aislamiento (venv con
`alembic 1.19.2`, `SQLAlchemy 2.0.52`, `pytest 8.4.2`):

```
$ python -m compileall -q alembic backend_api scripts/db      # ok
$ python scripts/db/check_alembic_linearity.py                 # exit 0
$ pytest backend_api/tests/test_check_alembic_linearity.py     # 8 passed
```

## 4. Evidencia — detecta una bifurcación simulada

### 4.1 Fork real en el árbol del repo (descartado inmediatamente)

Se creó de forma temporal `alembic/versions/99999999_99_ci_branch_probe_DELETEME.py` con
`down_revision = "20260812_01"` (bifurca una revisión intermedia; genera un segundo head):

```
$ python scripts/db/check_alembic_linearity.py
FAIL: Se esperaba un único head Alembic; se encontraron 2:
  - 20260901_01 (alembic/versions/20260901_01_single_evaluation_training_parent.py)
  - 99999999_99 (alembic/versions/99999999_99_ci_branch_probe_DELETEME.py)
Hay ramas divergentes. Reconcilia el historial a una sola línea (rebase de las
migraciones nuevas sobre el head real) antes de continuar.
exit=1

$ PYTHONPATH=backend_api pytest ...::test_real_repo_history_is_linear_and_head_is_derived -q
1 failed

$ rm alembic/versions/99999999_99_ci_branch_probe_DELETEME.py   # descartado
$ python scripts/db/check_alembic_linearity.py
OK: historial Alembic lineal, 21 revisiones, head único 20260901_01
$ git status --porcelain    # sin rastro del probe
```

### 4.2 Branch point y merge point intermedios (fixture aislado)

`ScriptDirectory` de fixture con un diamante `root → {left, right} → merge`:

```
FAIL: El historial Alembic no es lineal:
  - branch point: root (…/root_fixture.py) es down_revision de 2 revisiones:
      [left (…/left_fixture.py), right (…/right_fixture.py)]
  - merge point: merge (…/merge_fixture.py) desciende de 2 revisiones:
      [left (…/left_fixture.py), right (…/right_fixture.py)]
exit=1
```

Cubierto de forma permanente por `test_branch_point_fails_and_identifies_revision` y
`test_merge_point_fails_and_identifies_revision`.

---

## 5. Archivos tocados

| Archivo | Cambio |
|---|---|
| `.github/workflows/ci.yml` | job `alembic-static`: inline → invoca el script + su test |
| `scripts/db/check_alembic_linearity.py` | **nuevo** — validador derivado, mensajes accionables |
| `backend_api/tests/test_check_alembic_linearity.py` | **nuevo** — tests unitarios con fixtures |
| `Makefile` | nuevo target `check-alembic-linearity` (+ `.PHONY`) |
| `scripts/db/purge.py` | `EXPECTED_HEAD` literal → `_repo_linear_head()` en runtime |
| `scripts/storage/reset_smear_analysis.py` | `EXPECTED_HEAD` literal → derivado en import |
| `backend_api/tests/test_db_purge_tool.py` | fake DB usa `purge._repo_linear_head()` |
| `docs/architecture/cell_classification_data_model.md` | head prescriptivo → "derivar del repo" |
| `docs/architecture/scientific_validation.md` | head prescriptivo → "derivar del repo" |
| `docs/engineering/postgresql_docker_single_instance.md` | documenta `make check-alembic-linearity` |

## 6. Follow-ups (no bloqueantes, fuera de alcance de este fix)

- `alembic.ini` no define `path_separator`; alembic 1.19 emite un `DeprecationWarning` al
  cargar el `ScriptDirectory`. Añadir `path_separator = os` lo silencia (seguro: `prepend_sys_path`
  es una sola ruta sin separadores).
- Tests `*_postgres.py` de `malaria_dl_local_project` que afirman el head literal tras
  migrar (ver 2.4).
- `scripts/db/verify_alembic_adoption.py._linear_head()` podría reusar
  `check_alembic_linearity` y heredar los mensajes accionables.
