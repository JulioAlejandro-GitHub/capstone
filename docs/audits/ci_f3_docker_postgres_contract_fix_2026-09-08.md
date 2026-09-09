# Fix CI — `docs-config` / infracción #4 (F3): `HOST_POSTGRES_BINARY` demasiado amplia

Fecha: 2026-09-09
Autor: revisión asistida (Claude Code), rol arquitecto CI/CD
Alcance: **solo** la infracción #4 del diagnóstico
[`ci_docs_config_alembic_diagnosis_2026-09-08.md`](ci_docs_config_alembic_diagnosis_2026-09-08.md)
§2.4 (F3 en §"Propuestas de fix"). F1/F2/F4 ya aplicados en `a96dbe55` y `8e4044ac`.

Log de CI que motivó el fix:
<https://github.com/JulioAlejandro-GitHub/capstone/actions/runs/34289415465/job/102272373652>

```
HOST_POSTGRES_BINARY scripts/storage/reset_smear_analysis.py:929: binario PostgreSQL
invocado directamente desde el host; contrato esperado: db:5432
```

---

## Fase 1 — El uso en `reset_smear_analysis.py:929` es legítimo

### 1.1 Bloque completo (`validate_backup`, HEAD `8e4044ac`, líneas 916‑935)

```python
def validate_backup(path: Path | None) -> None:
    if path is None or not path.is_absolute() or not path.is_file() or path.is_symlink() or path.stat().st_size < 1024:
        raise ResetRefused("backup PostgreSQL durable, absoluto y no vacío requerido")
    with directory_fd(path.parent):
        pass
    with path.open("rb") as stream:
        data = stream.read(5)
    if data != b"PGDMP":
        raise ResetRefused("backup PostgreSQL custom-format inválido")
    with directory_fd(path.parent):
        pass
    if not os.access(path, os.R_OK) or not (os.statvfs(path).f_flag & os.ST_RDONLY):
        raise ResetRefused("backup debe estar en un mount durable de solo lectura")
    pg_restore = shutil.which("pg_restore")                       # <- línea 929
    if not pg_restore:
        raise ResetRefused("pg_restore no está disponible en el contenedor")
    checked = subprocess.run([pg_restore, "--list", str(path)], capture_output=True,
                             text=True, timeout=30, check=False)
    if checked.returncode or any(f" TABLE DATA public {table} " not in checked.stdout for table in ("alembic_version", "users", "runs", "model_versions")):
        raise ResetRefused("backup no es restaurable o no contiene las tablas preservadas")
```

- **Línea 929** — `shutil.which("pg_restore")`: localiza el binario en `PATH`. No abre
  ninguna conexión; si falta, `ResetRefused("pg_restore no está disponible en el
  contenedor")` (línea 931) — el mensaje confirma que el script está pensado para correr
  **dentro** del contenedor `backend`, que trae `postgresql-client` desde `a99ffcd5`.
- **Línea 932** — `subprocess.run([pg_restore, "--list", str(path)], …)`: `pg_restore
  --list` lee **únicamente el TOC del archivo de dump** (`str(path)`), operación
  documentada como *offline* en PostgreSQL. **No hay `-h` / `--host` / `-d` / `--dbname`
  / conninfo**: `pg_restore --list` no puede conectarse a un servidor. `path` es el
  archivo de backup ya validado (cabecera `PGDMP`, mount de solo lectura, ruta absoluta,
  tamaño ≥ 1 KiB).

### 1.2 El script nunca contacta un servidor Postgres saltándose el contrato

Auditoría completa de conexiones y subprocess en `scripts/storage/reset_smear_analysis.py`:

| Línea | Uso | ¿Conecta? | ¿Gobernado por `db:5432`? |
|---|---|---|---|
| 22 | `from sqlalchemy import create_engine, text` | — | — |
| 800 / 977 / 1055 | `engine.connect()` | Sí, vía SQLAlchemy | **Sí** — el engine sale de `create_engine(database_url)` (línea 1043) y `validate_url` (líneas 850‑856) **rechaza** cualquier `DATABASE_URL` cuyo `host != "db"` o puerto `!= 5432` (`ResetRefused("DATABASE_URL debe apuntar a PostgreSQL db:5432")`). |
| 929 | `shutil.which("pg_restore")` | No | n/a (localización de binario) |
| 932 | `subprocess.run([pg_restore, "--list", <archivo>])` | No | n/a (inspección offline del archivo de dump) |

No existe en el script ningún `pg_restore -d …` / `pg_restore -h …` / `psql` contra una
conexión real. **La infracción #4 es un falso positivo confirmado**: el checker matchea el
*nombre* del binario dentro de `shutil.which("pg_restore")`, no una invocación de conexión.
No se abre un hallazgo aparte.

---

## Fase 2 — Por qué matcheaba

`HOST_POSTGRES_BINARY` (`scripts/check_docker_postgres_contract.py`) es:

```python
re.compile(
    r"^(?:\s*(?:[-*]\s+|[$>]\s*)?)(?:sudo\s+)?(?:psql|pg_dump|pg_restore|pg_isready)\b"
    r"|[\[(]\s*['\"](?:psql|pg_dump|pg_restore|pg_isready)['\"]",
    re.IGNORECASE,
)
```

Segunda alternativa: «un `[` o `(`, comilla, nombre de binario, comilla». Su intención es
cazar el `argv` de un `subprocess.run` cuyo primer token entrecomillado es un cliente
Postgres, pero el `(` también abarca la llamada `shutil.which(<comilla>pg_restore…)` →
`(<comilla>pg_restore`. El patrón **no distingue**:

> Los ejemplos de esta sección van despojados de comillas/prefijo de esquema a propósito,
> para no disparar el propio checker sobre este `.md` (que no es allowlistable). Ver los
> literales exactos en `backend_api/tests/test_docker_postgres_contract_guard.py`.

| Forma | Ejemplo (neutralizado) | ¿Debe ser violación? | Antes | Después |
|---|---|:--:|:--:|:--:|
| Invocación real con destino de conexión | lista `argv` `[ pg_restore , -h , localhost , … ]` | **Sí** | ✅ detecta | ✅ detecta |
| Cliente al inicio de línea (shell / markdown) | `psql` como primer token de línea con conninfo a host `localhost` | **Sí** | ✅ | ✅ |
| `docker compose exec -T db pg_dump …` | backup gobernado | No | exento (`_docker_governed_native_command`) | exento |
| **Localización del binario** | `shutil.which(` + binario | **No** | ❌ falso positivo | ✅ exento |
| **Inspección offline de un archivo** | `pg_restore --list <archivo>` (sin flags de host) | **No** | ❌ (si el `argv` es literal) | ✅ exento |

Otros usos de binarios PostgreSQL en el repo, revisados para no romper ninguno:

| Archivo | Línea | Contexto | Estado |
|---|---|---|---|
| `scripts/db/backup.sh` | 72, 83, 92 | `exec psql …` / `exec pg_dump …` dentro de `compose exec -T db sh -ceu '…'`; `compose exec -T db pg_restore --list < …` | No matchea (prefijo `exec `, no literal entre corchetes) y además cubierto por `_docker_governed_native_command`. Sin cambios. |
| `docker-compose.yml` | 15 | healthcheck del propio servicio `db`: el primer literal de la lista es `CMD-SHELL`, no el binario; `pg_isready` va dentro del segundo string | No matchea. Sin cambios. |
| `backend_api/tests/test_docker_postgres_*` | varias | fixtures del contrato | allowlist exacta con conteo (mecanismo ya existente). |
| `docs/**` prosa | varias | `pg_restore --list` citado como texto | No matchea (no está al inicio de línea ni como literal `argv`). Sin cambios. |

---

## Fase 3 — Corrección del checker (afinada, no debilitada)

### 3.1 `diff` exacto de `scripts/check_docker_postgres_contract.py`

```diff
@@ ALLOWLIST
     "backend_api/tests/test_docker_postgres_contract_guard.py": {
         "HOST_ADMIN_COMMAND": 2,
+        "HOST_POSTGRES_BINARY": 3,
         "PG_DSN_HOST": 5,
         "PG_HOST_ENV": 1,
         "RETIRED_DATABASE_URL": 1,
         "RETIRED_IDENTIFIER": 1,
     },
@@ tras _docker_governed_native_command
+
+# A PostgreSQL client binary that is only *named* -- resolved on ``PATH`` or used
+# to read a dump *file* -- never opens a connection, so it cannot bypass the
+# ``db:5432`` contract. These two shapes are exempt; anything that carries a
+# connection target (``-h``/``--host``/``--dbname``/conninfo) stays a violation.
+_BINARY_AVAILABILITY_PROBE = re.compile(
+    r"\bwhich\s*\(\s*['\"](?:psql|pg_dump|pg_restore|pg_isready)['\"]",
+    re.IGNORECASE,
+)
+_OFFLINE_ARCHIVE_INSPECTION = re.compile(
+    r"\bpg_restore\b[^\n]*?(?<![\w-])(?:--list|-l)(?![\w-])",
+    re.IGNORECASE,
+)
+_EXPLICIT_CONNECTION_TARGET = re.compile(
+    r"(?<![\w-])(?:-h|--host|-d|--dbname|-U|--username)(?![\w-])"
+    r"|postgresql(?:\+[a-z0-9]+)?://",
+    re.IGNORECASE,
+)
+
+
+def _binary_named_but_not_connecting(line: str) -> bool:
+    if _BINARY_AVAILABILITY_PROBE.search(line):
+        return True
+    return bool(
+        _OFFLINE_ARCHIVE_INSPECTION.search(line)
+        and not _EXPLICIT_CONNECTION_TARGET.search(line)
+    )
@@ _eligible_rule_matches
-        if rule.identifier == "HOST_POSTGRES_BINARY" and _docker_governed_native_command(text, line):
+        if rule.identifier == "HOST_POSTGRES_BINARY" and (
+            _docker_governed_native_command(text, line)
+            or _binary_named_but_not_connecting(line)
+        ):
             continue
@@ scan_text
-            if (
-                rule.identifier == "HOST_POSTGRES_BINARY"
-                and _docker_governed_native_command(text, line)
+            if rule.identifier == "HOST_POSTGRES_BINARY" and (
+                _docker_governed_native_command(text, line)
+                or _binary_named_but_not_connecting(line)
             ):
                 continue
```

**Diseño.** No se toca la regex `HOST_POSTGRES_BINARY` ni se añade una allowlist para el
script de producción (eso sería el patrón frágil que F2 sólo justifica para *tests*). Se
añade un guard hermano de `_docker_governed_native_command` — el mecanismo de exención ya
existente del checker — que exime **dos formas que jamás abren una conexión**:

1. `shutil.which("<bin>")` / `which("<bin>")` — resolución de ruta.
2. `pg_restore --list` / `pg_restore -l` — lectura del TOC de un archivo, **siempre que la
   misma línea no lleve** `-h`/`--host`/`-d`/`--dbname`/`-U`/`--username`/conninfo.

Cualquier invocación con destino de conexión sigue siendo violación: un host no canónico
no puede colarse. El `HOST_POSTGRES_BINARY: 3` de la allowlist corresponde a las 3
fixtures nuevas de test que **sí** deben disparar la regla (ver 3.2); `validate_allowlist`
verifica el conteo exacto, así que si alguien añade otra el gate lo obliga a revisar.

### 3.2 Tests nuevos (`backend_api/tests/test_docker_postgres_contract_guard.py`)

Se ejecutan en CI en el job `backend-unit`
(`PYTHONPATH=backend_api pytest backend_api/tests`).

**Caso negativo — no dispara violación** (`test_allowed_patterns_pass` +
`test_which_lookup_of_pg_binary_is_not_a_host_invocation`):

```python
'    pg_restore = shutil.which("pg_restore")',          # exacto de reset_smear_analysis.py:929
'if shutil.which("psql") is None:',
'subprocess.run([pg_restore, "--list", str(path)], check=False)',
'subprocess.run(["pg_restore", "--list", "backup.dump"])',
"pg_restore -l backup.dump",
```

```python
def test_which_lookup_of_pg_binary_is_not_a_host_invocation():
    source = (
        "import shutil, subprocess\n"
        'pg_restore = shutil.which("pg_restore")\n'
        'subprocess.run([pg_restore, "--list", str(path)], check=False)\n'
    )
    violations, _ = guard.scan_text("scripts/storage/reset_smear_analysis.py", source)
    assert violations == []
```

**Caso positivo — sigue disparando `HOST_POSTGRES_BINARY`** (`test_forbidden_patterns_fail`,
3 de ellas cuentan en la allowlist como `HOST_POSTGRES_BINARY: 3`). Descritas sin el
literal exacto (está en el test); todas son un `subprocess.run` con lista `argv`:

| `argv` (neutralizado) | Por qué sigue siendo violación |
|---|---|
| `[ pg_restore , -h , localhost , … ]` | `-h` a host distinto de `db` |
| `[ psql , --host , 127.0.0.1 , -c , … ]` | `--host` a loopback |
| `[ pg_restore , --username , u , --dbname , app , … ]` | restaura **contra una BD viva** (`--dbname`) |
| shell: `pg_restore --list --host replica.internal …` | `--list` es offline, pero el `--host` explícito lo vuelve un intento de conexión |

### 3.3 Verificación local

```
$ python3 scripts/check_docker_postgres_contract.py
Contrato PostgreSQL Docker: OK (684 archivos revisados, 27 excepciones contractuales).   exit=0

# antes del fix, mismo HEAD:
# HOST_POSTGRES_BINARY scripts/storage/reset_smear_analysis.py:929: …
# Contrato PostgreSQL Docker: FALLÓ (1 infracciones, 684 archivos revisados, 24 excepciones contractuales).   exit=1

$ pytest -q backend_api/tests/test_docker_postgres_contract_guard.py \
              backend_api/tests/test_docker_postgres_tooling.py
48 passed
```

Infracción #4 eliminada, 0 infracciones, sin infracciones nuevas. Las 27 (antes 24)
«excepciones contractuales» = +3 por las fixtures de test allowlisted; el `shutil.which`
del script **no** cuenta como excepción (igual que `_docker_governed_native_command`),
queda simplemente fuera del alcance de la regla.

---

## Fase 4 — CI

- `git diff --check` → limpio.
- Commit único para este fix (`792f1230`): `scripts/check_docker_postgres_contract.py`,
  `backend_api/tests/test_docker_postgres_contract_guard.py`, este documento.
- **Run de CI en verde** (`main` @ `792f1230`):
  <https://github.com/JulioAlejandro-GitHub/capstone/actions/runs/34350765088>

  | Job | Resultado |
  |---|---|
  | `docs-config` | ✅ success — la infracción #4 desaparece |
  | `backend-unit` | ✅ success — corre `test_docker_postgres_contract_guard.py` (tests nuevos) |
  | `alembic-static` | ✅ success |
  | `frontend` / `ml-fast` | ✅ success |

  Primer run con **los 5 jobs en verde** sobre `main` (ver hallazgo de proceso F5 del
  diagnóstico: activar branch protection para que esto no vuelva a regresar sin bloquear).

### Nota de entorno

La suite completa de `backend_api/tests` requiere Python 3.12 + `requirements.txt` (como en
CI); el entorno local sólo tiene 3.9/3.14 sin venv del proyecto (`app.security` usa
`enum.StrEnum`, 3.11+). Se ejecutaron localmente los tests self-contained relevantes
(`test_docker_postgres_contract_guard.py`, `test_docker_postgres_tooling.py` → 48 passed) y
el checker; el resto lo valida el job `backend-unit` del run enlazado arriba.
