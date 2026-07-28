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
- Prompt 8: clasificación de crops con `stage2/default`, snapshot de modelo e
  inputs, predicciones canónicas, threshold publicado, agregado experimental,
  Grad-CAM manual, reviews append-only, RBAC/auditoría y workflow single page.
  La persistencia usa la cadena Alembic `20260728_01/02/03`; el summary público
  separa automático inmutable y proyección revisada, y los artefactos usan
  storage local confinado sin exponer keys.
- Validación Prompt 8: no se encontró un slot real `stage2/default`, por lo que
  no hubo fallback ni inferencia E2E y el estado seguro es
  `awaiting_productive_model`. Las dependencias API/ML faltantes quedaron
  declaradas y protegidas por preflight, pero no instaladas ni descargadas.

## 2026-07-27 — Prompt 4

- Ingesta multipart segura, streaming, SHA-256, JPEG/PNG/TIFF y recuperación.
- Paciente/muestra automáticos, lotes e importación NIH-NLM idempotente.
- Storage compensable, UI `/frotis/cargar` y contrato RBCNet documental.
# 2026-07-27 — Prompt 5

- Quality gate técnico reproducible, runs científicos con inputs congelados,
  perfiles versionados, RBAC, auditoría y revisión de advertencias.
- UI `/frotis/analisis`, migración `20260727_03`.
