# DBV2.5 — Freeze Git

## Estado inicial

- Branch: `main`
- HEAD before freeze: `d8369f67be9a03166c3601356916529bb587b269` ("GATE DBV2.4 — APROBADO.")
- `git status --short`, `git diff`, `git diff --cached`: vacíos. No había cambios ajenos ni pendientes.

## Artefactos DBV2.4 reportados como untracked

Ya estaban versionados en `d8369f6`: `docs/audits/db_v2/dbv2_4/` (68 archivos, incluidos los 67 del hash set), `scripts/db/dbv24_transfer.py`, `scripts/db/dbv24_evidence.py`.

## alembic_v2/safety.py

- Archivo modificado: `alembic_v2/safety.py` (el único `safety.py` de BD-v2; `backend_api/app/database_safety.py` y `tests/maintenance/test_safety.py` no fueron tocados).
- Último commit que lo modifica: `9b06418` ("bd v2"), diff +14 −1 respecto de `5bc65a8`: añade las etapas autorizadas `DBV2.2` (`gate_dbv21_approved`) y `DBV2.3` (`gate_dbv22_approved` + `persistent`), exige labels `org.capstone.pgv2.lifecycle=persistent` en contenedor y volumen para DBV2.3, y exige PostgreSQL 17.9 (`server_version_num == 170009`) para DBV2.2/DBV2.3.
- Motivo: sobre de autorización de instalación de DBV2.2/DBV2.3; documentado en `dbv2_3/authorization_envelope_change.json` y `dbv2_3/dbv2_3_report.md` ("no modifica el catálogo ni crea una revisión").
- SHA-256 actual `9e06a4ec6a79d134d5e02bb6ce84c408e82f866bf19dd32255b31e8888dec49b` = `current_sha256` certificado en DBV2.3 (`dbv2_3_hashes.sha256`). DBV2.4 no dejó cambios adicionales: no hay etapa `DBV2.4` en el archivo y `d8369f6` no lo toca; `dbv24_transfer.py` sólo importa `IDENTITY_SQL`, `ROLES_SQL`, `inspect_isolation`, `validate_server_snapshot`. El "+11 −2" citado en el cierre de DBV2.4 no corresponde a ningún cambio presente en el repositorio: el archivo en disco y en HEAD es el certificado en DBV2.3.
- Conclusión: pertenece a BD-v2, forma parte del estado certificado y ya está versionado. DBV2.5 no lo modifica (queda pinneado en `dbv2_5_hashes.sha256`).

## Artefactos BD-v2 bajo control de versiones (verificado con `git ls-files`)

| Grupo | Archivos |
|---|---|
| `alembic_v2/` (revisión raíz, 11 SQL + manifest de recursos, env, safety, contratos) | 23 |
| `alembic_v2.ini` | 1 |
| DBV2.1 (`docs/audits/db_v2/dbv2_1_*`) | 15 |
| DBV2.2 (`docs/audits/db_v2/dbv2_2/`) | 94 |
| DBV2.3 (`docs/audits/db_v2/dbv2_3/`) | 40 |
| DBV2.4 (`docs/audits/db_v2/dbv2_4/`) | 68 |
| Scripts DBV2.1–2.4 (`scripts/db/*dbv2*`, `v2_catalog_probe.py`, …) | versionados |
| `tests/db_v2/` | 5 |

Ignorados y excluidos (correcto): `__pycache__/`, `.DS_Store`, `var/maintenance/` (credenciales locales de BD-v2, nunca versionadas).

## Inventario del commit de Freeze (selección explícita, sin `git add -A`)

- `docs/audits/db_v2/dbv2_5/` (todos los archivos del directorio, listados en `dbv2_5_hashes.sha256` más el propio archivo de hashes)
- `scripts/db/dbv25_freeze.py`
- `scripts/db/dbv25_evidence.py`

Sin dumps, credenciales, binarios, logs de contenedor ni caches. Cambios ajenos a BD-v2: ninguno.

## Identificación del commit

El SHA del commit de Freeze no puede escribirse dentro de los archivos que ese mismo commit introduce (ciclo de hash). Se resuelve de forma determinista con:

    git log --format=%H -- docs/audits/db_v2/dbv2_5/db_v2_final_manifest.json

y se informa en el cierre de DBV2.5. La baseline y la evidencia DBV2.1–DBV2.4 están en `d8369f6`, ancestro directo del commit de Freeze.
