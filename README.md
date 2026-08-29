# Capstone MIA — plataforma científica experimental

Monolito modular con FastAPI, React/TypeScript, PostgreSQL y `malaria_dl`. No es una
herramienta diagnóstica.

## Operación soportada

Docker Compose es la única forma soportada de operar Capstone:

```text
frontend → backend → db:5432 → postgres_data
```

Los servicios son `db`, `backend` y `frontend`. Las credenciales se definen en el
`.env` no versionado mediante `POSTGRES_USER`, `POSTGRES_PASSWORD` y `POSTGRES_DB`;
Compose inyecta `DATABASE_URL` en las aplicaciones.

```bash
docker compose up -d
docker compose ps
make db-status
make test-backend
make test-ml
make validate
```

No ejecute herramientas de administración de bases instaladas en el host ni scripts
históricos de inicialización. Backup, status y pruebas se operan mediante Makefile y
los wrappers de `scripts/db/`. Los comandos Alembic permanecen pendientes de
habilitación hasta corregir los mounts en Prompt 1B.1.

El contrato completo está en
[PostgreSQL Docker: instancia única](docs/engineering/postgresql_docker_single_instance.md).
El índice activo está en [docs/README.md](docs/README.md).

## Dominios científicos

La API científica mantiene trazabilidad pseudonimizada caso → muestra → frotis → imagen.
El flujo de análisis incluye quality gate, detección, clasificación y revisión humana.
La elegibilidad mínima Stage 2 continúa siendo `TRAIN completed + EVALUATE completed`.

Consulte `docs/architecture/scientific_data_model.md`,
`docs/architecture/cell_classification_pipeline.md` y
`docs/stage2_productive_training_card.md`.
