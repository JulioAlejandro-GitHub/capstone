# E6 — Corrección de reserva concurrente y diagnóstico aislado

**E6 NO APROBADA.** El usuario aportó `1 failed, 15 passed, 1 deselected in 2.25s` para la integración sintética. Falló únicamente `test_concurrent_equivalent_requests_have_one_owner`; la lectura pública fue excluida. Estos resultados corresponden a la revisión anterior a este complemento, no a la corrección actual.

HEAD permanece `cd5c64d703358797570f5183dd598d93314dc0eb`, rama main, cambios previos preservados. No se aplicó ninguna migración ni se modificó el DDL E6. La lectura de current mediante Compose volvió a fallar por acceso denegado al socket Docker; no se interpreta como BD caída.

## Hallazgo y alcance de la causa

La salida aportada sólo identifica `CampaignError`, sin SQLSTATE. El repositorio de campañas sanitiza la excepción del driver en su frontera pública. Por tanto, **esa salida no demuestra todavía qué operación/constraint originó el fallo**.

La revisión comprueba que `assessment_identities` tiene dos restricciones únicas relevantes: `identity_hash` y `structural_hash`. El INSERT anterior declaraba únicamente `ON CONFLICT(identity_hash) DO NOTHING`. La hipótesis principal es un conflicto concurrente en la otra restricción. No se declara causa original confirmada sin el diagnóstico PostgreSQL correspondiente.

Corrección local mínima en `assessment/repository.py`:

- `ON CONFLICT DO NOTHING` contempla los conflictos de unicidad del INSERT, sin retirar constraints ni relajar CHECK/triggers.
- La lectura posterior sigue buscando exclusivamente `identity_hash` con `FOR UPDATE`.
- Si no existe esa identidad exacta, falla con `IDENTITY_CONFLICT_NOT_EXACT`. Una colisión estructural ajena no se convierte en reutilización.
- Se mantiene comparación íntegra del JSON y un único intento activo/verificado. No se selecciona por fecha ni se captura cualquier fallo SQL como éxito.

## Prueba y diagnóstico

La prueba concurrente abre dos conexiones del esquema sintético E4 y las sincroniza **antes del INSERT**, comprobando que tienen dos backend PID diferentes (no los imprime). Primero prueba el SQL anterior mediante una sustitución limitada al fixture. Recoge ambos resultados y diagnóstico de tipo, fase, SQLSTATE y una lista cerrada de nombres de constraints; nunca imprime mensajes, parámetros ni trazas del driver. El SQL anterior puede no fallar por el scheduling; ese caso se informa como no reproducido, no confirma ni refuta por sí solo la causa histórica.

Luego usa una identidad sintética nueva con el SQL corregido y exige: dos respuestas sin fallo, exactamente una creación, mismo UUID de intento y owner, estado active y conteos SQL de una identidad y un intento. La fase original es diagnóstica; la corregida es obligatoria para pasar.

Se conserva el fixture de limpieza E4: commit sólo del esquema sintético para permitir dos conexiones, rollback de transacciones fallidas y eliminación/verificación posterior del esquema temporal, incluso ante fallo del cuerpo. No se borran eventos ni datos operativos, ni se desactivan triggers. La aprobación de esta prueba no acredita una migración en public.

Pruebas locales afectadas:

```sh
cd malaria_dl_local_project
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q -p no:cacheprovider --tb=short \
  tests/test_assessment_e6.py tests/test_assessment_api_e6.py tests/test_assessment_postgres.py
```

Resultado: **39 passed, 17 skipped, 7 warnings in 12.31s**. Cuatro nuevos casos locales comprueban reutilización exacta, rechazo de colisión sin identidad, rechazo de payload distinto y sanitización del diagnóstico. No son simulaciones que acrediten locks PostgreSQL. Ruff y `git diff --check` aprobados. Las 194 pruebas del informe anterior no se presentan como repetidas en este cambio.

## Comandos pendientes desde raíz Capstone

Ejecutar primero con `-s` para conservar la evidencia diagnóstica incluso si la prueba corregida pasa:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE6_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -s -p no:cacheprovider \
  tests/test_assessment_postgres.py::test_concurrent_equivalent_requests_have_one_owner
```

Después de pasar, repetir toda la integración sintética:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE6_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_assessment_postgres.py -k 'not public_e6_revision_readonly'
```

Persisten como pendientes la concurrencia corregida, la suite PostgreSQL completa de esta revisión, la instalación operativa y `/ready`. No aplicar la migración mientras falle la integración sintética. Conservar los informes y el manifiesto originales; la revisión actual se identifica en `etapa_6_manifiesto_concurrencia_2026-09-11.json`. No se ejecutó TEST operativo ni se inició E7.
