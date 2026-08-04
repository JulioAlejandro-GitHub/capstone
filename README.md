# Capstone MIA — análisis experimental de malaria

Plataforma científica local para trazabilidad de experimentos de deep learning y
análisis técnico de frotis. Integra FastAPI, React/TypeScript, PostgreSQL y el
paquete `malaria_dl` en un monolito modular. Sus resultados son experimentales:
**no constituyen diagnóstico, decisión clínica ni estimación validada de
parasitemia**.

## Inicio rápido

Requisitos soportados: Python 3.12, Node.js 22/npm 10 y una instancia local de
PostgreSQL 17. El runtime oficial no usa Docker.

1. Copie `.env.example` a `.env` y complete, al menos, `DATABASE_URL` y
   `JWT_SECRET`. Nunca confirme secretos en Git.
2. Cree el entorno Python e instale las dependencias:

   ```bash
   python3.12 -m venv malaria_dl_local_project/.venv
   ./malaria_dl_local_project/.venv/bin/python -m pip install -r malaria_dl_local_project/requirements.txt
   ```

3. Verifique la base existente y aplique migraciones sólo mediante el flujo
   protegido descrito en [docs/database.md](docs/database.md):

   ```bash
   make db-status
   make db-migrate-check
   ```

4. Desde la raíz del repositorio, inicie la API:

   ```bash
   ./malaria_dl_local_project/.venv/bin/python -m uvicorn \
     app.main:app \
     --app-dir backend_api \
     --reload \
     --port 8000 \
     --env-file .env
   ```

   `./scripts/start_backend_api.sh` ejecuta el mismo runtime, agrega un preflight
   de dependencias y fija el host local.

5. En otra terminal, inicie el frontend:

   ```bash
   npm --prefix frontend ci
   npm --prefix frontend run dev
   ```

La API expone liveness en `http://127.0.0.1:8000/health` y readiness en
`http://127.0.0.1:8000/ready`. La SPA se sirve normalmente en
`http://localhost:5173`; su flujo de frotis canónico es `/frotis/analizar` y el
historial es `/frotis/historial`.

## Documentación canónica

- [Arquitectura actual](docs/architecture.md)
- [Desarrollo local](docs/local-development.md)
- [Base de datos y Alembic](docs/database.md)
- [Pipeline de IA y linaje científico](docs/ai-pipeline.md)
- [Workflow y publicación de Etapa 2](docs/stage2-workflow.md)
- [Seguridad](docs/security.md)
- [Pruebas y gates](docs/testing.md)
- [Operaciones](docs/operations.md)
- [Sistema de diseño y rutas](docs/design-system.md)

Los ADR, contratos JSON y documentos científicos detallados se conservan como
fuentes especializadas y están enlazados desde estos nueve documentos. Los
artefactos de Delivery 2 se conservan únicamente como `DESIGN_REFERENCE /
NOT_RUNTIME`; no describen por sí solos la implementación ejecutable.

## Comandos de calidad

```bash
make validate
make test
make test-ml
make test-backend-integration  # requiere PostgreSQL local configurado
make lint
```

No ejecute resets, downgrades, `DROP DATABASE` ni `DROP SCHEMA public`. Las
migraciones SQL históricas, las revisiones Alembic y `var/storage` forman parte
de la trazabilidad persistente del proyecto.
