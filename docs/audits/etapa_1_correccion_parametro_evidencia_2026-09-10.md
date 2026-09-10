# E1 — Corrección de parámetros de evidencia

Fecha: 2026-09-10. **E1 NO APROBADA: integración corregida pendiente de ejecución efectiva.**

Revisión Git: `54c9d9568f04ca7a5f15582b784375b07a8463e2`. Se preservaron la modificación previa de `tests/test_dataset_evidence_postgres.py` y los informes complementarios sin seguimiento. No se hicieron commits ni cambios de esquema, servicios, dataset, split, checkpoints o publicaciones.

## Evidencia recibida y causa

El usuario ejecutó la prueba diagnóstica en Compose y aportó:

```text
Synthetic evidence failure: [{'phase': 'INSERT', 'type': 'GovernedDatasetError', 'sqlstate': None}]; diagnostics: [{'phase': 'INSERT', 'type': 'AmbiguousParameter', 'sqlstate': '42P08'}]
1 failed in 0.25s
```

Esto demuestra que el error original es de ambigüedad de parámetro en INSERT, anterior a liberación del savepoint, lectura y comparación. La inspección del INSERT identifica el único parámetro reutilizado: `:id` en `id` UUID y `correlation_id` TEXT. Es la causa identificada por diagnóstico y código; la confirmación de resolución exige repetir la integración con el cambio.

El reporte recibido no contiene fallos adicionales de rollback ni de ausencia posterior: según el flujo de la prueba ejecutada, esas comprobaciones terminaron sin excepción después del INSERT fallido. Esto no demuestra rollback de un evento insertado exitosamente, pues el primer INSERT fue rechazado.

## Corrección mínima

Rutas relativas a `malaria_dl_local_project`:

- `src/malaria_dl/persistence/dataset_evidence.py`: parámetros independientes `id` y `correlation_id`, con `CAST(:id AS uuid)` y `CAST(:correlation_id AS text)`, conservando el mismo UUID lógico. Lectura por ID también usa cast UUID explícito. Sin cambios en payload, comparación completa, transacciones ni sanitización pública.
- `tests/test_dataset_stage1.py`: regresión local de parámetros separados, tipos explícitos e identidad lógica igual en el escritor simulado.
- `tests/test_dataset_evidence_postgres.py`: añade comprobación del correlation_id persistido igual al UUID sintético. Conserva comparación de after_state/success/error_code, duplicado 23505, SELECT 1 tras rechazo, conteo 1 antes y 0 desde conexión posterior al rollback, incluso cuando falla el cuerpo. Diagnóstico y limpieza siguen separados.

No se debilitaron aserciones. No se crearon CSV ni fallback de archivos. El control local existente de ausencia de archivos laterales pasó.

## Validación

Desde `malaria_dl_local_project`:

```sh
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/etapa1-mpl \
XDG_CACHE_HOME=/private/tmp/etapa1-cache .venv/bin/python -B -m pytest \
-q -p no:cacheprovider --basetemp=/private/tmp/etapa1-fix-tests \
tests/test_dataset_stage1.py tests/test_dataset_evidence_postgres.py
```

Resultado: **56 passed, 1 skipped, 2 warnings**, 3.03 s. Advertencias protobuf ya conocidas. La aserción adicional de correlation_id pertenece exclusivamente a la prueba PostgreSQL omitida. `git diff --check` pasó.

Se intentó el comando PostgreSQL solicitado tras la corrección, pero esta sesión recibió salida 1 por acceso denegado al socket Docker. Error sanitizado:

```text
permission denied while trying to connect to the docker API at unix:///<usuario>/.docker/run/docker.sock
```

No implica caída de PostgreSQL. Ejecución pendiente desde la terminal del usuario con acceso, desde la raíz del repositorio y con los cambios visibles en el mount existente:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE1_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_dataset_evidence_postgres.py
```

## Dictamen

D1 y D2 permanecen comprobadas según el contexto aportado por el usuario. La causa del fallo INSERT está identificada y se implementó la corrección mínima; round-trip exitoso, rechazo del duplicado y rollback de un evento insertado siguen **NO VERIFICADOS** con esta versión en PostgreSQL. Por ello **E1 NO APROBADA**.

Un resultado aprobado de esta prueba acredita integración aislada con rollback, no durabilidad de commit entre sesiones. Se conservan los informes anteriores. No se inicia Etapa 2 y la selección de Producción permanece manual.
