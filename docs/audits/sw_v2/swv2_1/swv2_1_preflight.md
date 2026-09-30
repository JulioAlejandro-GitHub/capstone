# SWV2.1 — Preflight

Verificado en vivo **antes de modificar código** (`psql` dentro de `capstone_db`, sólo SELECT; sin mostrar passwords ni hashes).

## Git

| Campo | Valor |
|---|---|
| Rama | `main` |
| HEAD de entrada | `78a9ef2746a948d4126fa14ab706837abdbee1d5` (= commit SWV2.0 esperado) |
| `git status --short` | vacío (sólo ignorados) |
| `prueba.py` / `palindromo.py` | **ausentes** del working tree al iniciar SWV2.1 (el snapshot previo los listaba untracked). No fueron creados, modificados ni eliminados por SWV2.1. |

## Docker

| Contenedor | Estado | Puertos |
|---|---|---|
| `capstone_db` | Up (healthy) | `127.0.0.1:5432->5432` |
| `capstone_backend` | Up | `0.0.0.0:8000->8000` |
| `capstone_frontend` | Up | `0.0.0.0:80->80` |

Volumen montado en `/var/lib/postgresql/data`: `capstone_v2_isolated_persistent_data` (external). Volumen legacy `capstone-malaria_postgres_data` presente, sin contenedor, no tocado.

## Identidad PostgreSQL

| Invariante | Esperado | Observado |
|---|---|---|
| Versión | 17.9 | `PostgreSQL 17.9 (Debian 17.9-1.pgdg13+1)` |
| Base | malaria_experiments | malaria_experiments |
| OID | 16386 | 16386 |
| sysid | 7691366089693499436 | 7691366089693499436 |
| `alembic_version` | pg_v2_baseline | `pg_v2_baseline` (1 fila) |
| Structural manifest | `15c95e0c…3eafb` | `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb` (archivo congelado y catálogo vivo; `swv2_1_check_*.json`) |

## Roles (sólo flags)

| Rol | exists | LOGIN | SUPERUSER | CREATEDB | CREATEROLE | BYPASSRLS | REPLICATION | password configurada |
|---|---|---|---|---|---|---|---|---|
| `julio` | YES | t | **t** | f | f | f | f | (no consultado) |
| `capstone_v2_runtime` | YES | t | f | f | f | f | f | sí (booleano) |
| `capstone_v2_migrator` | YES | t | f | f | f | f | f | sí (booleano) |

`capstone_v2_runtime` sin membresías de rol. Credencial runtime: `var/maintenance/dbv23_persistent/credentials.json` (DBV2.3, gitignored `/var/maintenance/`, modo 0600); login verificado desde la red Compose sin imprimirla: `current_user = session_user = capstone_v2_runtime`, `rolsuper = false`.

Resultado: **identidad coincide — no BLOCKED**.
