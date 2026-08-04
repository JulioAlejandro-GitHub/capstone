# Pipeline CI

`.github/workflows/ci.yml` configura validación de documentación/configuración,
backend sin PostgreSQL, frontend, ML rápido y validación estática de Alembic. No
crea PostgreSQL ni usa Docker. La integración real es el gate local
`requires_local_postgres`. Sin una ejecución de GitHub Actions sólo puede
validarse la configuración del workflow, no declarar exitoso el CI remoto.
