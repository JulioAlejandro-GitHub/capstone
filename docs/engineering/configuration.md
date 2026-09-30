# Configuración

`APP_ENV=development` es el único ambiente. Las credenciales se mantienen exclusivamente
en el `.env` no versionado. Compose requiere `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`POSTGRES_DB` y `CAPSTONE_V2_RUNTIME_PASSWORD`, y construye una sola `DATABASE_URL` para
backend y ML con el rol PostgreSQL v2 `capstone_v2_runtime` (sin SUPERUSER, sin DDL). El
login `POSTGRES_USER` es sólo de administración local/DBeaver: Compose lo vacía en el
contenedor backend. `capstone_v2_migrator` nunca forma parte de la `DATABASE_URL` runtime.

No existen variables de conexión por datasource ni variables parciales en las
aplicaciones. `JWT_SECRET` continúa siendo obligatorio. Passwords, tokens y URLs completas
no se registran. CORS acepta únicamente orígenes HTTP(S) explícitos.

Compose fija el contrato de almacenamiento científico a
`STORAGE_PROVIDER=local` y `STORAGE_ROOT=/app/var/storage`, respaldado por el
named volume `scientific_storage`. El backend falla si `STORAGE_ROOT` falta,
está vacío o es relativo; no resuelve rutas desde el cwd ni crea directorios al
validar configuración.

Véase [PostgreSQL Docker](postgresql_docker_single_instance.md).
