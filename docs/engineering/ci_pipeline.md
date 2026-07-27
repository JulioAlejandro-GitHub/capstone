# Pipeline CI

`.github/workflows/ci.yml` configura validación, backend sin PostgreSQL, seguridad pura,
frontend, ML rápido y validación estática de Alembic. No crea PostgreSQL ni ejecuta Docker.
La integración real es el gate local `requires_local_postgres`. Sin commit/push solo puede
declararse `REMOTE_CI_CONFIGURATION=PASS`, no una ejecución remota.
