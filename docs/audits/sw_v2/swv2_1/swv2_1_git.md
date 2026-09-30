# SWV2.1 — Git

## Entrada

| Campo | Valor |
|---|---|
| `git branch --show-current` | `main` |
| `git rev-parse HEAD` | `78a9ef2746a948d4126fa14ab706837abdbee1d5` (= SWV2.0 esperado) |
| `git status --short` | vacío; `prueba.py` y `palindromo.py` ausentes del working tree |

## Archivos del commit SWV2.1

Modificados:
- `docker-compose.yml` — P-02: `DATABASE_URL` backend con `capstone_v2_runtime`; login admin vaciado en backend.
- `.env.example`, `docs/engineering/configuration.md` — variable `CAPSTONE_V2_RUNTIME_PASSWORD` (sin valor).
- `malaria_dl_local_project/src/malaria_dl/persistence/schema_contract.py` — validación fail-closed del contrato; comparación independiente de collation.
- `malaria_dl_local_project/src/malaria_dl/persistence/v2_runtime_contract.json` — P-01: regenerado desde la baseline certificada.

Nuevos:
- `scripts/db/build_v2_runtime_contract.py` — generador/verificador reproducible del contrato.
- `scripts/db/swv21_backend.py` — evidencia SWV2.1 (READ ONLY / rollback).
- `malaria_dl_local_project/tests/test_v2_runtime_contract_guard.py`, `tests/db_v2/test_v2_runtime_contract.py`, `backend_api/tests/test_backend_runtime_role_contract.py`.
- `docs/audits/sw_v2/swv2_1/*`.

Fuera del commit: `.env` (ignorado; recibe `CAPSTONE_V2_RUNTIME_PASSWORD` localmente), `var/maintenance/*` (credenciales privadas, ignorado), `backups/*`, `prueba.py` (ausente).

## Congelados

`git diff --name-only 28346b7 -- alembic_v2 alembic_v2.ini docs/audits/db_v2` → 0; `git diff HEAD -- alembic_v2 alembic_v2.ini docs/audits/db_v2 alembic` → 0; untracked en esas rutas → 0.

| Recurso | sha256 |
|---|---|
| `alembic_v2/versions/20260929_01_pg_v2_baseline.py` | `e3aaad12e49e65cff8ad9742fcdd83af075f2e2fcfaa81733a2bec121efef279` |
| `alembic_v2/baseline/catalog_manifest.json` | `232871ff0241c2912eef40daeee2c849fde70bdec5d64784cb72844e667b009a` |
| `docs/audits/db_v2/dbv2_2/restart_r1/dbv2_2_catalog_manifest.json` | `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb` |

Commit local, sin push ni tag. El SHA final se informa en la respuesta de cierre (un commit no puede contener su propio hash).
