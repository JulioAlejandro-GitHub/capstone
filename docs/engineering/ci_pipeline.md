# Pipeline CI

`.github/workflows/ci.yml` ejecuta guardia Docker-only, validación del diff, unitarios
backend sin conexión, validación estática Alembic, frontend y ML rápido. CI no instala ni
inicia PostgreSQL y no crea una base de integración.

La validación estática Alembic (job `alembic-static`) invoca
`scripts/db/check_alembic_linearity.py`: deriva el head del `ScriptDirectory` del repo
—sin ningún valor hardcodeado en el YAML— y exige una única línea recta (un head, sin
branch/merge points), fallando con la revisión exacta si se bifurca. Reproducible en local
con `make check-alembic-linearity`.

Las pruebas marcadas `requires_docker_postgres` quedan fuera de CI mientras no exista un
servicio Docker explícitamente aislado. Localmente solo se habilitan sobre `db` con
aislamiento demostrado.
