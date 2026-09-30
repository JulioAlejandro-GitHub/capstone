# SWV2.1 — Inventario de consumidores backend

Localizado sobre el código real (HEAD `78a9ef2`) antes de implementar.

| Consumidor | Ubicación | Contrato actual (entrada) | Contrato v2 | Cambio |
|---|---|---|---|---|
| config / `.env` | `backend_api/app/config.py` (`os.getenv`, sin dotenv); root `.env` vía `env_file` | `DATABASE_URL` obligatoria, host `db`, puerto 5432 (`database_safety.validate_database_url`) | igual | **ALREADY COMPATIBLE** |
| Compose `DATABASE_URL` | `docker-compose.yml` servicio `backend` | `${POSTGRES_USER}:${POSTGRES_PASSWORD}` → `julio` SUPERUSER; además el contenedor heredaba `POSTGRES_USER/PASSWORD` por `env_file` | rol `capstone_v2_runtime` + `CAPSTONE_V2_RUNTIME_PASSWORD`; login admin vaciado en backend | **MUST CHANGE (P-02)** |
| SQLAlchemy engine/session | `backend_api/app/db.py` (`get_engine`, `read_only_transaction`, `check_connection`) | engine único desde `settings.database_url`, sin segunda URL ni fallback | igual | **ALREADY COMPATIBLE** |
| Schema guard | `malaria_dl/execution/schema.py::require_e10_schema` | revisiones `20260922_01`, `pg_v2_baseline`; capacidades E10 fail-closed | igual (4 capacidades E10 PASS en v2) | **ALREADY COMPATIBLE** |
| Contrato runtime v2 | `malaria_dl/persistence/schema_contract.py` + `v2_runtime_contract.json` | JSON capturado del candidato E.4 (`capture_v2_e4_runtime.py`), 14 funciones / 22 triggers | derivado de la baseline congelada: 13 funciones / 21 triggers / 40 constraints / 2 índices | **MUST CHANGE (P-01)** |
| ResultRepository | `malaria_dl/persistence/result_repository.py:121` | llama `require_e10_schema` antes de persistir | sin cambio; queda desbloqueado por P-01 | ALREADY COMPATIBLE (escrituras E10 = **OUT OF SCOPE**) |
| ResultService / Reporter / controlled / local_execution | `results/service.py`, `execution/controlled.py`, `execution/repository.py`, `local_execution/backend.py` | usan la misma guarda | sin cambio | **OUT OF SCOPE** (TRAIN/EVALUATE/EXPLAIN) |
| auth | `backend_api/app/routes/auth.py`, `security.py` | `users`/`user_roles`/`roles`; login hace `UPDATE users.last_login_at` + `INSERT audit_events` | runtime tiene SELECT/INSERT/UPDATE en esas tablas | **ALREADY COMPATIBLE** |
| dataset gobernado | `routes/dataset_versions.py` → `services/governed_datasets.py` | lectura `dataset_versions`, estadísticas, checks, materialización | igual | **ALREADY COMPATIBLE** |
| dataset browser legacy | `routes/dataset.py` → `services/dataset_browser.py` | agrega `dataset_split_images` | en v2 hay 2 raíces físicas (2 × 27,558 = 55,116) → conteos por clase no coinciden con el split gobernado | **OUT OF SCOPE** (observación para fase posterior) |
| health | `routes/health.py::health` | estático (status/version/env) | igual | **ALREADY COMPATIBLE** |
| ready | `routes/health.py::ready` | `current_database` + `assert_capstone_database` + `require_e10_schema` + storage RWX | igual; fallaba sólo por P-01 | ALREADY COMPATIBLE (desbloqueado por P-01) |
| Migrator | `alembic_v2/` (congelado), `adoption_v2/` | nunca usado por el backend | igual | **OUT OF SCOPE** |
| Tooling Alembic legacy | `Makefile db-migrate*`, `scripts/db/migrate.sh` (`alembic` legacy vía backend) | usaba la `DATABASE_URL` del backend | con el rol runtime fallará por privilegios (sin DDL): separación correcta runtime ≠ migrator | **OUT OF SCOPE** (no ejecutado) |
| `backend_api/.env` | local, ignorado, contiene variables legacy | no cargado: Compose sólo usa root `.env`; `.dockerignore` excluye `**/.env` | inerte | **OUT OF SCOPE** (no modificado) |

## Referencias buscadas

- **Revisiones Alembic antiguas / hashes E.4**: `v2_runtime_contract.json` (`stage: E10.10.5E.4`) y `scripts/db/capture_v2_e4_*` (históricos). Sólo el JSON es consumidor runtime.
- **`julio`**: sólo `.env` (`POSTGRES_USER`), scripts históricos `scripts/reset/*`, `tests/maintenance/run_isolated.py` (fixture aislado) y rutas absolutas de docker socket. Ningún uso en `backend_api/app` ni `malaria_dl/src`.
- **Puerto 56440 / `capstone_v2_isolated_persistent`**: `scripts/db/dbv23_*` y `tests/db_v2/test_dbv23_authorization.py` (evidencia histórica DBV2.3). Ningún consumidor runtime.
- **Fallback legacy / segunda DATABASE_URL / dual DB**: ninguno en el backend (`_datasources()` expone sólo `malaria`).
