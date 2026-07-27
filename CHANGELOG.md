# Changelog

## Unreleased

- Navegación: nuevo módulo principal **Análisis de frotis**, separado de **Modelo IA**,
  con la carga existente disponible únicamente como **Cargar imágenes** en `/frotis/cargar`.
- Modelo científico pseudonimizado, API RBAC, auditoría atómica y trazabilidad mediante
  revisión Alembic `20260727_01`; las imágenes se registran sólo por metadata.
- Docker retirado de la arquitectura operativa, Makefile, CI y gates de aprobación.
- Fundación Etapa 2: configuración local/test/demo, DB test guardada, PostgreSQL 17
  efímero, transición Alembic, auth JWT/Argon2, RBAC, correlation ID, logging,
  health/readiness, Docker, CI y login frontend.
- Migraciones históricas 001–029 preservadas.

## 2026-07-27 — Prompt 4

- Ingesta multipart segura, streaming, SHA-256, JPEG/PNG/TIFF y recuperación.
- Paciente/muestra automáticos, lotes e importación NIH-NLM idempotente.
- Storage compensable, UI `/frotis/cargar` y contrato RBCNet documental.
