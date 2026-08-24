# Validación Prompt 2.2.1

> **Estado documental:** `HISTORICAL_AUDIT`
> **Uso operativo:** No; resultados y conteos pertenecen al corte indicado.
> **Snapshot:** 2026-07-27 / Prompt 2.2.1, head `20260726_02`.

Fecha: 2026-07-27.

- PostgreSQL 17.9 Homebrew, `127.0.0.1:5432`, `malaria_experiments/public`: PASS.
- Alembic current=head=`20260726_02`: PASS.
- migraciones 001–029, 027, test 027 y `complemento e2.txt`: diff vacío.
- backend local completo: 89 passed, 4 skipped.
- PostgreSQL auth/rollback focalizado: 13 passed.
- frontend: 62 passed; build Vite/TypeScript PASS; Vite local HTTP 200.
- ML rápida: 17 passed.
- ML amplia: 359 passed, 16 skipped, 37 subtests passed.
- `/health`: 200; `/ready`: 200 tras preparar storage local.
- password incorrecta, sin token y token manipulado: 401.
- usuario sintético deshabilitado: 401; residuo 0.
- usuarios/runs/audit_events/schemas sintéticos: 0.
- stage2 activo observado sin ejecutar ninguna mutación.
- workflow YAML: PASS; sin jobs Docker/PostgreSQL.

Limitaciones:

- login autorizado, `/auth/me` y flujo frontend real: BLOCKED por falta de credenciales;
- el fallo FK real demuestra rollback en la unidad transaccional común, pero las seis
  familias no fueron ejercitadas end-to-end contra cada repositorio y tabla de dominio;
- por lo anterior la recomendación permanece RECHAZAR.
