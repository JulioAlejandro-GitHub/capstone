# SWV2.0 — Git

## Estado de entrada

| Campo | Valor |
|---|---|
| Branch | `main` |
| HEAD | `28346b75c718e3b82b86328f822862184d420b3e` (Freeze DBV2.5, no modificado) |
| Working tree | limpio |

## Cambios SWV2.0 (hacia adelante)

| Archivo | Cambio |
|---|---|
| `docker-compose.yml` | `postgres_data` → volumen externo `capstone_v2_isolated_persistent_data` (+4 líneas) |
| `docker-compose.override.yml` | puerto `db` restringido a `127.0.0.1:5432:5432` |
| `backend_api/tests/test_scientific_storage_docker_contract.py` | aserción del volumen PostgreSQL adaptada al contrato externo; `scientific_storage` sigue exigido no externo |
| `scripts/db/swv20_integration.py` | verificación READ ONLY parametrizada por endpoint (nuevo) |
| `docs/audits/sw_v2/swv2_0/` | evidencia (nuevo) |

## Baseline congelada

`git diff --name-only 28346b7 -- alembic_v2 alembic_v2.ini docs/audits/db_v2` → **0 archivos**; no rastreados en esas rutas → **0**. `pg_v2_baseline`, recursos SQL, `catalog_manifest.json` y manifest estructural intactos.

## Fuera de Git (ignorado)

- `backups/swv2_0/` (backup BD-v2 + globals; contiene datos y verificadores SCRAM).
- `var/maintenance/swv20/` (digest privado del password hash de aplicación).

## Commit

Commit local `SWV2.0 integrate PostgreSQL v2 into development environment` sobre `28346b7` (que no se modifica). El SHA no puede figurar dentro del propio commit: es el commit que introduce este archivo (`git log --format=%H -- docs/audits/sw_v2/swv2_0/swv2_0_report.md`). Sin push ni tags.
