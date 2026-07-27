# Prompt 3 — precheck

Fecha: 2026-07-27  
Rama: `main`  
Commit inicial: `9fae68a2b29a92ede752b14d8ad12e7107f3754c`

## Snapshot

- `git status --short`: limpio al iniciar este prompt.
- `git diff --stat`: sin diferencias.
- `git diff --check`: correcto.
- Migraciones históricas: sin diferencias en el working tree.
- `20260726_02_audit_events.py`: sin modificaciones.

## PostgreSQL y Alembic

- PostgreSQL: `17.9 (Homebrew)`, arquitectura `aarch64`.
- Host y puerto: `127.0.0.1:5432`.
- Base: `malaria_experiments`.
- Schema: `public`.
- Alembic current inicial: `20260726_02`.
- Alembic head inicial: `20260726_02`.

La primera conexión desde el sandbox fue bloqueada por aislamiento de red. La comprobación
autorizada contra la instancia local confirmó que PostgreSQL acepta conexiones y que
`current=head`.

## Auditoría previa

No existen tablas científicas equivalentes. Las tablas de datasets, predicciones,
artefactos e imágenes de ejecución tienen semántica de entrenamiento/inferencia y no
representan la cadena de custodia caso → muestra → frotis → captura microscópica. Se crean
entidades nuevas para evitar reutilización semánticamente incorrecta.

La configuración `.env` contiene al menos un valor con espacios que no puede cargarse
directamente mediante `source .env`; los comandos operativos deben usar el mecanismo de
configuración del proyecto o corregir el quoting local sin publicar secretos.
