# DBV2.5 — Preflight

Estado de entrada: GATE DBV2.1–DBV2.4 aprobados. Branch `main`, HEAD `d8369f67be9a03166c3601356916529bb587b269` ("GATE DBV2.4 — APROBADO.").

| Comprobación | Resultado |
|---|---|
| `git status --short` / `git diff` / `git diff --cached` al inicio | vacío (árbol limpio) |
| Artefactos DBV2.4 reportados como untracked (`docs/audits/db_v2/dbv2_4/`, `scripts/db/dbv24_transfer.py`, `scripts/db/dbv24_evidence.py`) | ya versionados en `d8369f6` (68 + 2 archivos) |
| Baseline (`alembic_v2/`, `alembic_v2.ini`, manifest estructural) vs `d8369f6` | sin diff, sin untracked |
| Revisión raíz `20260929_01_pg_v2_baseline.py` SHA-256 (recalculado) | `e3aaad12e49e65cff8ad9742fcdd83af075f2e2fcfaa81733a2bec121efef279` PASS |
| Manifest estructural de referencia (archivo DBV2.2) SHA-256 (recalculado) | `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb` PASS |
| Manifest de recursos + 11 SQL de baseline (recalculados) | `232871ff0241c2912eef40daeee2c849fde70bdec5d64784cb72844e667b009a`, 11/11 PASS |
| Alembic estático (ScriptDirectory, sin BD) | revisión única `pg_v2_baseline`, down_revision `None`, roots 1, heads 1 |
| DBV2.4 `dbv2_4_hashes.sha256` re-verificado desde disco | 67/67 OK, todos versionados; SHA-256 del conjunto `eaecc880b60230c281c989857db2aea8b686b914fa492847e8b31aa3845e5f4e` PASS |
| DBV2.4 `dbv2_4_transfer_manifest.json` recalculado | `295ad3737e92d0e64333062f459a527026a4eacf6e9d36179ce31fbb89c33cf9` PASS |

Evidencia: `dbv2_5_baseline_files.json`, `dbv2_5_dbv24_evidence.json`.

## Modo de acceso

- BD-v2: rol `capstone_v2_migrator`, sesión `default_transaction_read_only=on` + `BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY`; `transaction_read_only = on` afirmado antes de cada consulta.
- Legacy (`capstone_db`, `malaria_experiments`): igual (`REPEATABLE READ READ ONLY`, `default_transaction_read_only=on`), identidad y sysid comparados con `dbv2_3/source_identity.json`.
- Ninguna sentencia INSERT/UPDATE/DELETE/TRUNCATE/DDL/GRANT/REVOKE/Alembic upgrade/downgrade/stamp fue ejecutada.
- Nota sobre `alembic_v2/safety.py`: `validate_server_snapshot` exige `read_only='off'` (semántica de migración). DBV2.5 **no modifica** safety.py; le entrega el modo a nivel servidor (`pg_settings.boot_val` de `default_transaction_read_only` = `off`, `pg_is_in_recovery() = false`) y afirma por separado que la sesión DBV2.5 es READ ONLY.
