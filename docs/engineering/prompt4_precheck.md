# Prompt 4 — precheck

Fecha: 2026-07-27. Rama `main`; commit inicial
`661ad9eeb7bf74b1a0c8d7c916e289cc7cda5896`; working tree limpio.

PostgreSQL 17.9 Homebrew aceptó conexiones en localhost:5432. Base:
`malaria_experiments`; schema: `public`. Alembic inició en `20260727_01 (head)` y
la historia hasta esa revisión permanecía intacta.

Configuración inicial: `STORAGE_ROOT=./var/storage`,
`MAX_UPLOAD_SIZE_BYTES=20971520`. La raíz ahora se resuelve contra la raíz real
del repositorio. Pillow no estaba instalado en el entorno virtual al iniciar;
se declaró e instaló junto con `python-multipart`.

El inventario encontró la colisión `ADR-014-explainability-policy.md` /
`ADR-014-1-scientific-data-model.md`. El ADR científico fue renumerado a ADR-016,
primer número libre, y Prompt 4 usa ADR-017.
