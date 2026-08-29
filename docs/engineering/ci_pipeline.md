# Pipeline CI

`.github/workflows/ci.yml` ejecuta guardia Docker-only, validación del diff, unitarios
backend sin conexión, validación estática Alembic, frontend y ML rápido. CI no instala ni
inicia PostgreSQL y no crea una base de integración.

Las pruebas marcadas `requires_docker_postgres` quedan fuera de CI mientras no exista un
servicio Docker explícitamente aislado. Localmente solo se habilitan sobre `db` con
aislamiento demostrado.
