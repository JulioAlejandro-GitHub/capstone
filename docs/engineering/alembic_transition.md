# Transición a Alembic

Las migraciones SQL históricas 001–029 y sus checksums permanecen intactos. Una base nueva ejecuta `scripts/init_db.py`, valida la migración 029, hace `alembic stamp 20260726_00` y `alembic upgrade head`. La baseline es vacía deliberadamente: representa el esquema legado, no lo recrea. La revisión siguiente crea sólo auth/RBAC.

`scripts/db/verify_alembic_adoption.py` rechaza DB no-test, esquema incompleto, ausencia de 029 y versiones incompatibles. En una base existente el stamp debe ser siempre explícito y precedido por esa verificación.
