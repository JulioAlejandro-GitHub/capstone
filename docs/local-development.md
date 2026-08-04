# Desarrollo local

El entorno soportado usa macOS o Linux, Python 3.12, Node.js 22/npm 10 y una
instancia accesible de PostgreSQL 17. Docker no forma parte del flujo oficial.
Las versiones detalladas se mantienen en
[`engineering/runtime_versions.md`](engineering/runtime_versions.md).

## Preparación

Desde la raíz del repositorio:

```bash
cp .env.example .env
python3.12 -m venv malaria_dl_local_project/.venv
./malaria_dl_local_project/.venv/bin/python -m pip install -r malaria_dl_local_project/requirements.txt
npm --prefix frontend ci
```

Complete en `.env` una `DATABASE_URL` de la base Capstone y un `JWT_SECRET`
privado. `APP_ENV` sólo admite `development`; no existe una URL de test
alternativa. Consulte todas las variables en
[`engineering/configuration.md`](engineering/configuration.md).

El entorno único soportado para API, inferencia, migraciones y pruebas es
`malaria_dl_local_project/.venv`, porque reúne las dependencias FastAPI y
TensorFlow. No mantenga un segundo venv del backend como runtime alternativo.

## Base de datos

La base local es persistente y no debe reconstruirse. Antes de cambiarla:

```bash
set -a
source .env
set +a
make db-status
make db-migrate-check
```

`make db-migrate` crea un backup, valida el upgrade en una transacción y luego
aplica `alembic upgrade head`. Revise primero [database.md](database.md); no use
`stamp`, downgrade ni comandos destructivos como atajo.

## API

El comando canónico, ejecutado desde la raíz, es:

```bash
./malaria_dl_local_project/.venv/bin/python -m uvicorn \
  app.main:app \
  --app-dir backend_api \
  --reload \
  --port 8000 \
  --env-file .env
```

También puede usar:

```bash
./scripts/start_backend_api.sh
```

Verifique `GET http://127.0.0.1:8000/health` y luego `/ready`. `health` prueba
el proceso; `ready` comprueba que sus dependencias estén disponibles.

## Frontend

```bash
npm --prefix frontend run dev
```

Abra `http://localhost:5173`. La URL canónica del workflow es
`/frotis/analizar`; `/frotis/cargar`, `/frotis/analisis` y `/frotis/revision`
son redirects de compatibilidad. La sesión JWT se conserva en `localStorage` y
se restaura al recargar; cerrar sesión elimina el token local.

## Ciclo de trabajo

```bash
make validate
make test
make test-ml
make lint
```

Las pruebas marcadas `requires_local_postgres` escriben contra la base
configurada bajo aislamiento transaccional. Nunca apunte `.env` a una base que
no pertenezca a Capstone. Vea [testing.md](testing.md) y
[`engineering/database_safety_policy.md`](engineering/database_safety_policy.md).
