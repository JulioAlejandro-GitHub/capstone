# Prompt 5 — precheck

> **Estado documental:** `HISTORICAL_AUDIT`
> **Uso operativo:** No; precheck fechado, no diagnóstico actual.
> **Snapshot:** 2026-07-27, `main@9a45bbb1861cc7e6b782244a5afc1a7b9eacc3c4`.

Fecha: 2026-07-27 (America/Santiago).

- Rama: `main`.
- Commit inicial real: `9a45bbb1861cc7e6b782244a5afc1a7b9eacc3c4` (difiere del commit informado `661ad9e...`).
- Working tree inicial: únicamente `var/` sin seguimiento; no se modificó ni eliminó.
- `git diff --stat` y `git diff --check`: sin diferencias rastreadas ni errores.
- PostgreSQL: 17.9 en el entorno anterior retirado; dato histórico, no instrucción operativa.
- Base y schema: `malaria_experiments`, `public`.
- Alembic inicial: `current = head = 20260727_02`.
- Historia intacta: `20260726_00 → 20260726_01 → 20260726_02 → 20260727_01 → 20260727_02`.
- Tablas verificadas: `research_subjects`, `scientific_cases`, `blood_samples`,
  `smear_slides`, `microscopy_images`, `image_ingestion_batches`.
- RBAC existente: roles en `roles`/`user_roles`; permisos definidos en código en
  `backend_api/app/security.py`.
- Rutas existentes de Análisis de frotis: `/frotis/cargar` y
  `/api/v1/scientific/...`.
- Storage: proveedor local, `STORAGE_ROOT=./var/storage`; originales bajo claves
  relativas y endpoint autenticado `/api/v1/scientific/images/{id}/content`.
- Librerías de imagen en el venv: Pillow 12.3.0. NumPy, OpenCV y SciPy no están
  instaladas; Prompt 5 usa Pillow y Python estándar para no descargar dependencias.

El precheck habilita la migración `20260727_03`; no se ejecutaron reset, clean,
stash, downgrade, stamp, Docker, commit ni push.
