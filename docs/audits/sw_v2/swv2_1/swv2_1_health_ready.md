# SWV2.1 — /health y /ready

Semántica (sin cambios en `backend_api/app/routes/health.py`):

- `/health`: liveness estático (`status`, `version`, `environment`); no consulta la base.
- `/ready`: `database` + `migrations` = `SELECT current_database()` + `assert_capstone_database` + `require_e10_schema`; `storage` = `STORAGE_ROOT` y `ARTIFACTS_ROOT` con permisos RWX. 503 si algún componente falla.

| Momento | Rol backend | /health | /ready | Payload /ready |
|---|---|---|---|---|
| Entrada (SWV2.0) | `julio` | 200 | **503** | `database/migrations: not_ready` (`v2_function_contract`) |
| Integrado (P-01 + P-02) | `capstone_v2_runtime` | 200 | **200** | `{"status":"ready","components":{"database":"ready","migrations":"ready","storage":"ready"}}` |
| Post `docker compose restart` | `capstone_v2_runtime` | 200 | **200** | idem |

Sin bypass, mock, monkeypatch, superuser ni migrator: requests HTTP reales a `127.0.0.1:8000` contra el backend en Docker.

## Docker restart

`docker compose restart` (sin `down`, sin `-v`): `capstone_db` healthy (arranque 2026-09-30T22:14:10Z), `capstone_backend` running, `capstone_frontend` running. Volumen `capstone_v2_isolated_persistent_data` montado y sysid/OID intactos (`swv2_1_check_post_restart.json`). Antes del restart, el backend se recreó con `docker compose up -d --no-deps backend` para cargar el nuevo entorno (la base no se tocó).

## Smoke de endpoints sin procesamiento científico

`swv2_1_smoke_integrated.json`, `swv2_1_smoke_post_restart.json`:

| Endpoint | Status |
|---|---|
| `GET /health` | 200 |
| `GET /ready` | 200 |
| `GET /datasources` | 200 (`malaria` → `malaria_experiments`) |
| `GET /api/dataset/summary` | 200 |
| `GET /api/dataset/split` | 200 |
| `GET /api/v1/auth/me` sin token | 401 (autenticación sigue exigida) |
| `GET /api/v1/auth/me` con token | 200 (`swv2_1_auth.md`) |
| `GET /api/datasets`, `GET /api/datasets/{id}` con token | 200 / 200 (`swv2_1_dataset.md`) |
