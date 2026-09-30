# SWV2.1 — P-02 identidad runtime del backend

## Cambio

`docker-compose.yml`, servicio `backend`:

```yaml
DATABASE_URL: postgresql+psycopg://capstone_v2_runtime:${CAPSTONE_V2_RUNTIME_PASSWORD:?...}@db:5432/${POSTGRES_DB:?...}
POSTGRES_USER: ""
POSTGRES_PASSWORD: ""
```

- El rol es literal del contrato (no configurable a `julio` ni al migrator); la password proviene del mecanismo existente (`.env` no versionado, nueva clave `CAPSTONE_V2_RUNTIME_PASSWORD`), copiada sin imprimir desde la credencial DBV2.3 (`var/maintenance/dbv23_persistent/credentials.json`, gitignored).
- `POSTGRES_USER/PASSWORD` (login admin/DBeaver `julio`) siguen alimentando sólo al servicio `db`; en el contenedor backend quedan vacíos (antes llegaban por `env_file`).
- `.env.example` y `docs/engineering/configuration.md` documentan la variable sin valor.
- `julio` intacto: no eliminado, password y permisos sin cambios; no usado para pruebas backend.
- Sin GRANT/REVOKE: el runtime funcionó con los privilegios certificados; **0 `permission denied`** en logs y pruebas.

## Evidencia (sesión del propio backend: `app.db.get_primary_engine()`)

`swv2_1_runtime_integrated.json`, `swv2_1_runtime_post_restart.json`:

| Invariante | Valor |
|---|---|
| `current_user` / `session_user` | `capstone_v2_runtime` / `capstone_v2_runtime` |
| `current_user != julio` | true |
| `current_user != capstone_v2_migrator` | true |
| rolsuper / rolcreatedb / rolcreaterole / rolbypassrls / rolreplication | false / false / false / false / false |
| CREATE en schema `public` / en la base | false / false |
| INSERT/UPDATE/DELETE/TRUNCATE sobre `alembic_version` | false |
| miembro de `capstone_v2_migrator` / de `julio` | false / false |
| destino (redactado) | `db:5432/malaria_experiments` |
| `require_e10_schema` | PASS (`pg_v2_baseline`) |

En el contenedor: `POSTGRES_USER=""`, `len(POSTGRES_PASSWORD)=0`; `DATABASE_URL` (redactada) `postgresql+psycopg://capstone_v2_runtime:<redacted>@db:5432/malaria_experiments` — sin `capstone_v2_migrator` ni `julio`.

Regresión estática: `backend_api/tests/test_backend_runtime_role_contract.py` (3 tests) impide volver a `POSTGRES_USER`, `julio` o el migrator en la `DATABASE_URL` del backend.

## Auditoría vs runtime

Las verificaciones de continuidad (`swv2_1_check_*.json`) reutilizan el procedimiento certificado SWV2.0 (sesión `READ ONLY REPEATABLE READ` como `capstone_v2_migrator`, host). Es una sesión de auditoría separada, nunca la identidad del backend.
