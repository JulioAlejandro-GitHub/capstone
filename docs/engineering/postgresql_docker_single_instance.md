# PostgreSQL Docker: instancia única

> **Estado documental:** `CURRENT_DOC`
> **Fuente canónica:** arquitectura y operación PostgreSQL vigente.

```text
frontend → backend → db:5432 → postgres_data
                     PostgreSQL 17.9
```

PostgreSQL se ejecuta exclusivamente como servicio Docker Compose `db`; el contenedor
se llama `capstone_db` y la persistencia reside en el volumen `postgres_data`. La
configuración versionada no publica su puerto al host.

Backend y ML reciben exclusivamente `DATABASE_URL`, construida e inyectada por Compose.
El hostname interno permitido es `db` y el puerto canónico es `5432`. Las credenciales
provienen del `.env` no versionado mediante `POSTGRES_USER`, `POSTGRES_PASSWORD` y
`POSTGRES_DB`.

No existe una segunda base para pruebas. Las pruebas PostgreSQL usan la misma instancia
con transacciones revertidas o schemas temporales cuyo nombre se valida y cuyo cleanup
es obligatorio. Las suites sin aislamiento completo permanecen bloqueadas.

No se requieren herramientas PostgreSQL instaladas en macOS. Toda operación pasa por
Makefile o por wrappers Docker de `scripts/db/`.

## Comandos vigentes

```bash
docker compose up -d
docker compose ps
make db-status
make db-backup
make test-backend
make test-ml
make validate
```

Alembic dejó de ser requisito operativo el 2026-10-27. Los targets db-migrate,
db-migrate-check y check-alembic-linearity están retirados, junto con el gate de CI.
Se ejecuta SQL revisado contra el esquema actual; no se eliminan constraints ni triggers.

La guardia `scripts/check_docker_postgres_contract.py`, ejecutada por `make validate` y
CI, impide reintroducir conexiones o herramientas operativas hacia el host.
