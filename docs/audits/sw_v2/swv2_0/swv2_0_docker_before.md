# SWV2.0 — Docker antes

Captura completa sin valores de entorno: `swv2_0_docker_before.json`.

| Contenedor | Proyecto / servicio | Imagen | Puerto | Volumen | Red | Estado |
|---|---|---|---|---|---|---|
| `capstone_db` (`2604ff98…`) | capstone-malaria / `db` | postgres:17.9 | `0.0.0.0:5432` | `capstone-malaria_postgres_data` | capstone-malaria_default | Up (healthy) — **legacy**, sysid 7668020338728398886 |
| `capstone_db_v2` (`1dc48428…`) | — (ninguno) | postgres:17.9 | `127.0.0.1:56440` | `capstone_v2_isolated_persistent_data` | bridge | Up — **BD-v2 certificada** |
| `capstone_backend` | capstone-malaria / `backend` | capstone-malaria-backend | `8000` | `capstone-malaria_scientific_storage` + binds | capstone-malaria_default | Up |
| `capstone_frontend` | capstone-malaria / `frontend` | node:20 | `80` | binds | capstone-malaria_default | Up |
| `capstone_v2_isolated_fafc32d0d3a3` | — | postgres:17.9 | — | propio (`…fafc32d0d3a3`) | — | Exited (desechable DBV2.4) |
| `capstone_v2_isolated_1621252d7ab4` | — | postgres:17.9 | — | propio (`…1621252d7ab4`) | — | Exited (desechable DBV2.4) |

Cada volumen tenía exactamente un contenedor usuario (sin ambigüedad): `capstone_v2_isolated_persistent_data` → sólo `capstone_db_v2`; `capstone-malaria_postgres_data` → sólo `capstone_db`.

Legacy: bases `malaria_experiments` (OID 1600436) y `malaria_pre_reset3_20260929`; rol `julio` = SUPERUSER LOGIN (creado por la imagen desde `POSTGRES_USER`).

Compose (`docker-compose.yml` + `docker-compose.override.yml`): servicio `db` → `container_name: capstone_db`, volumen lógico `postgres_data` (no externo → `capstone-malaria_postgres_data`), puerto sólo en override `"5432:5432"`, healthcheck `pg_isready`. Backend `DATABASE_URL` compuesto por Compose desde `.env` (`POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_DB`) → `db:5432`, `depends_on: db (service_healthy)`.
