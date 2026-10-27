# Validación PostgreSQL Docker

> **Estado documental:** `CURRENT_DOC`

`make db-status` comprueba de forma read-only el servicio `db`, la identidad de base,
usuario y versión PostgreSQL. No se consulta una revisión Alembic. `make test-db` selecciona el
marker `requires_docker_postgres`; solo deben ejecutarse pruebas con rollback o schema
temporal demostrado.

`make validate` ejecuta la guardia documental y de configuración sin requerir Docker ni
secretos. Los gates Alembic están retirados del contrato operativo (2026-10-27).

Contrato: [instancia Docker única](postgresql_docker_single_instance.md).
