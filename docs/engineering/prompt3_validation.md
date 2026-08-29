# Prompt 3 — validación final

> **Estado documental:** `HISTORICAL_AUDIT`
> **Uso operativo:** No; resultados y schema corresponden al cierre de Prompt 3.
> **Snapshot:** 2026-07-27, head final `20260727_01`.

Fecha: 2026-07-27  
Recomendación: **APROBAR**

## Plataforma y migración

- Rama/commit inicial: `main` / `9fae68a2b29a92ede752b14d8ad12e7107f3754c`.
- PostgreSQL: 17.9 en el entorno anterior retirado.
- Base/schema: `malaria_experiments` / `public`.
- Current inicial: `20260726_02`.
- Nueva revisión y head final: `20260727_01`.
- Migraciones `20260726_00`–`20260726_02`: intactas.
- No se ejecutó downgrade, Docker, commit ni push.

## Resultado funcional

Se crearon `research_subjects`, `scientific_cases`, `blood_samples`, `smear_slides` y
`microscopy_images`, con FK RESTRICT, UUID, UTC, unicidad contextual, checks de estados,
JSON objeto, cronología, checksum, dimensiones y coherencia de archivado.

La API ofrece 21 operaciones de creación/lectura/listado/actualización/archivado y una
consulta jerárquica de trazabilidad. No expone DELETE. Los listados soportan status,
búsqueda, `limit` y `offset`.

RBAC sigue el modelo en código existente (el schema previo no posee tablas de permisos):
administrator recibe todo; researcher/operator lectura y escritura operativa;
reviewer/read_only sólo lectura. Las mutaciones usan permisos separados por recurso y
acción. El archivado queda reservado al administrator.

Las acciones `scientific.*.created|registered|updated|archived` insertan en
`audit_events` con actor, correlación, recurso y estados. Una constraint PostgreSQL de test
rechazó un evento real y confirmó rollback de la mutación.

## Pruebas

Comandos principales:

```text
TEST_EXECUTION=true PYTHONPATH=. .venv/bin/pytest -q tests/test_scientific_data_api_postgres.py
TEST_EXECUTION=true PYTHONPATH=. .venv/bin/pytest -q
backend_api/.venv/bin/alembic current
backend_api/.venv/bin/alembic heads
git diff --check
```

Resultados:

- suite científica PostgreSQL: 3 passed;
- suite backend completa: 92 passed, 4 skipped, 0 failed;
- compilación Python: correcta;
- Alembic: `20260727_01 (head)`;
- `git diff --check`: correcto;
- residuos: 0 sujetos, casos, muestras, frotis, imágenes y usuarios sintéticos;
- schemas `capstone_test_%`: 0;
- warning no bloqueante: deprecación TestClient/httpx;
- warning operativo existente: `.env` no puede cargarse literalmente con `source` por un
  valor con espacios sin quoting.

## Límites confirmados

No se almacenó PII ni binarios. No se implementó upload, calidad, inferencia, workers,
clasificación, explainability ni cambios Stage 2/default. Frontend no fue modificado.

Riesgos pendientes: el bloqueo de claves PII no reemplaza revisión humana; Prompt 4 debe
validar existencia/checksum del objeto externo; existe una colisión histórica de número
ADR-014 que requiere ordenamiento documental posterior.
