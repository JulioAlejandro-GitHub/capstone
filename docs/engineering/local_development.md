# Desarrollo local

> **Estado documental:** `CURRENT_DOC`

El desarrollo usa Docker Compose como runtime único de `db`, `backend` y `frontend`.
Complete el `.env` no versionado a partir de `.env.example` sin copiar credenciales a
Git.

```bash
docker compose up -d
docker compose ps
make db-status
make test-backend
make test-ml
make validate
```

El frontend se consulta por HTTP desde el navegador; sus URLs loopback no son conexiones
PostgreSQL. TRAIN, EVALUATE y EXPLAIN se ejecutan dentro del runtime que recibe la
`DATABASE_URL` canónica.

Contrato de base: [PostgreSQL Docker](postgresql_docker_single_instance.md).
