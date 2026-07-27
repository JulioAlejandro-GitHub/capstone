# Validación Docker — SUPERSEDED

Documento histórico. Desde Prompt 2.2.1 Docker no forma parte de la arquitectura
operativa, desarrollo, CI ni gates de aprobación. Backend y frontend se ejecutan localmente.

Fecha: 2026-07-26.

- `docker version`, `docker info`, `docker compose version`: PASS.
- `docker compose ... config` para test y demo: PASS.
- Build backend/frontend: BLOCKED; las imágenes base no estaban en caché y el proxy no
  entregó `postgres:17-alpine`.
- Runtime `/health`, `/ready`, login y `/auth/me`: BLOCKED.
- Limpieza: PASS; no quedaron recursos `capstone-test`.

Se agregó frontend multi-stage Node 22/Nginx no-root y servicio Compose. Backend conserva
Python 3.12 y usuario no-root. `.dockerignore` excluye Git, env, datasets, outputs,
checkpoints y `node_modules`. No hay Redis ni worker científico.
