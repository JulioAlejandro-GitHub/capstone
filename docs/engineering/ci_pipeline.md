# Pipeline CI

`.github/workflows/ci.yml` separa documentación/configuración, backend unitario, integración PostgreSQL 17, frontend test/build, ML rápido determinista, Alembic y Docker. Usa permisos read-only, timeouts y credenciales efímeras. No descarga datasets/modelos, no entrena, publica ni despliega.
