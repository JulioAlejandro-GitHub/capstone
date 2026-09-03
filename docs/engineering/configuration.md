# Configuración

`APP_ENV=development` es el único ambiente. Las credenciales se mantienen exclusivamente
en el `.env` no versionado. Compose requiere `POSTGRES_USER`, `POSTGRES_PASSWORD` y
`POSTGRES_DB`, y construye una sola `DATABASE_URL` para backend y ML.

No existen variables de conexión por datasource ni variables parciales en las
aplicaciones. `JWT_SECRET` continúa siendo obligatorio. Passwords, tokens y URLs completas
no se registran. CORS acepta únicamente orígenes HTTP(S) explícitos.

Compose fija el contrato de almacenamiento científico a
`STORAGE_PROVIDER=local` y `STORAGE_ROOT=/app/var/storage`, respaldado por el
named volume `scientific_storage`. El backend falla si `STORAGE_ROOT` falta,
está vacío o es relativo; no resuelve rutas desde el cwd ni crea directorios al
validar configuración.

Véase [PostgreSQL Docker](postgresql_docker_single_instance.md).
