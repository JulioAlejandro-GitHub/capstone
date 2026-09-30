# DBV2.5 — Estado Docker

| Contenedor | Proyecto Compose | Estado | Rol |
|---|---|---|---|
| `capstone_backend` | capstone-malaria | Up | aplicación (sin cambios) |
| `capstone_frontend` | capstone-malaria | Up | aplicación (sin cambios) |
| `capstone_db` | capstone-malaria | Up (healthy) | PostgreSQL legacy (sin cambios, sólo lectura READ ONLY) |
| `capstone_db_v2` | — (ninguno) | Up | PostgreSQL BD-v2 persistente |

- `capstone_db_v2` currently separate from `capstone-malaria` = **YES** (sin label `com.docker.compose.project`). Decisión explícita diferida a **Proyecto SW-V2**; no se modificó.
- Backend: `DATABASE_URL` presente, host = servicio `db` (legacy), puerto 5432; no apunta a BD-v2. `.env` no menciona BD-v2. `docker-compose.yml` sin cambios. → **APPLICATION DATABASE_URL SWITCHED TO V2 = NO** (sólo booleanos, `dbv2_5_database_url.json`).
- **CUTOVER = NO**. Legacy y BD-v2 coexisten intencionalmente.

## Recursos temporales DBV2.4 (rollback test, puerto 56441)

| Contenedor | ID | Volumen | Label isolation | Evidencia |
|---|---|---|---|---|
| `capstone_v2_isolated_fafc32d0d3a3` | `c9efa7a0808c…` | `capstone_v2_isolated_fafc32d0d3a3` | `fafc32d0-d3a3-41a9-936b-9f415618c664` | `dbv2_4/disposable/target.json` |
| `capstone_v2_isolated_1621252d7ab4` | `7a08b4f04101…` | `capstone_v2_isolated_1621252d7ab4` | `1621252d-7ab4-4a98-8b6a-4bcd2631d177` | `dbv2_4/superseded_attempt_1/disposable/target.json` |

Ambos: detenidos, no son `capstone_db_v2`, no montan `capstone_v2_isolated_persistent_data`, sysid distinto del certificado. Identificación inequívoca.

Decisión DBV2.5: **NO ELIMINADOS**. Esta fase es conservadora y su eliminación no es necesaria para el Freeze; quedan documentados como limpieza pendiente de autorización explícita (`docker rm` del contenedor + `docker volume rm` de su volumen propio, nunca el persistente). También persisten contenedores `capstone_v2_isolated_*` detenidos de fases DBV2.2/DBV2.3 y anteriores, fuera del alcance de DBV2.5.

Inventario completo: `dbv2_5_docker_state.json` (sin variables de entorno).
