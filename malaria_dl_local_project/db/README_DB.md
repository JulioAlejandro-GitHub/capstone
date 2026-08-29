# Persistencia de experimentos ML

La persistencia ML utiliza exclusivamente la instancia PostgreSQL Docker de Capstone:

```text
malaria_dl → DATABASE_URL → db:5432 → postgres_data
```

ML no configura una conexión independiente, no construye URLs mediante variables
parciales y no crea otra base para pruebas. Las credenciales provienen del `.env` no
versionado en la raíz y Compose inyecta `DATABASE_URL` dentro de `backend`.

## Operación

```bash
docker compose up -d
make db-status
make test-ml
make validate
```

El runner SQL histórico `scripts/init_db.py` está retirado como comando operativo. El
schema canónico se administra con Alembic; sus comandos quedan pendientes de habilitación
hasta Prompt 1B.1 por los mounts actuales.

Las pruebas PostgreSQL usan la misma base con rollback o schemas temporales validados.
Las suites legacy que aplicaban DDL o dependían de otra base permanecen bloqueadas.

El tracking de TRAIN, EVALUATE y EXPLAIN obtiene la conexión mediante la implementación
canónica `src.db`. La indisponibilidad o invalidez de `DATABASE_URL` falla de forma
explícita; no existe fallback hacia el host.

Para arquitectura y procedimientos vigentes consulte
[PostgreSQL Docker: instancia única](../../docs/engineering/postgresql_docker_single_instance.md).
