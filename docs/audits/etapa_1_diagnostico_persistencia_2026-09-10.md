# Etapa 1 — Diagnóstico de integración de evidencia

Fecha: 2026-09-10. **E1 NO APROBADA: integración PostgreSQL pendiente.**

## Contexto y revisión

HEAD Git: `54c9d9568f04ca7a5f15582b784375b07a8463e2`. Al inicio únicamente estaba sin seguimiento `docs/audits/etapa_1_cierre_operativo_2026-09-10.md`; se conserva, junto al informe E1 original. Se aplican el contrato 0B v1.1 y PostgreSQL de instancia única revisados en la sesión.

El usuario aporta como comprobados: acceso Compose, base `malaria_experiments`, esquema `public`, revisión Alembic instalada y head `20260901_01`, resolver correcto para `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`, constraints validadas y trigger append-only activo. Son evidencia comunicada por el usuario, no comprobaciones repetidas aquí. La revisión Alembic no debe confundirse con el commit Git.

Se revisaron el escritor `src/malaria_dl/persistence/dataset_evidence.py`, la parametrización de lectura, `tests/test_dataset_evidence_postgres.py` y `persistence/database.py`, dentro de `malaria_dl_local_project`.

## Causa y corrección

**La causa original del fallo de persistencia no está demostrada.** El INSERT reutiliza `:id` para UUID y TEXT; la lectura lo usa únicamente para UUID. La configuración del proyecto usa psycopg. Esto respalda investigar inferencia de tipos, pero no acredita una excepción concreta del servidor. No se modificó el escritor ni se introdujo una corrección especulativa; el error público permanece sanitizado y la igualdad completa del round-trip permanece intacta.

Sí se confirmó por control de flujo un defecto de la prueba: si el cuerpo fallaba, el `finally` revertía la transacción, pero la excepción saltaba la comprobación de ausencia situada después. Además, una excepción de rollback podía sustituir la original.

Se modificó únicamente `malaria_dl_local_project/tests/test_dataset_evidence_postgres.py`:

- Diagnóstico de tipo original y SQLSTATE sin convertir la excepción del driver a texto, imprimir parámetros ni trazas. Las fases distinguen INSERT, apertura/liberación de savepoint, lectura, normalización y comparación.
- Diferencias del round-trip limitadas a nombres de campos distintos y comparación del conjunto de claves del objeto sintético; no se imprimen valores operativos.
- Se mantiene engine real local, transacción externa y proxy de escritura limitado a savepoints. No hay commits externos, DELETE, alteración de constraints/triggers ni escrituras de datasets/runs.
- Se exige igualdad de `after_state`, `success` y `error_code`; duplicado con SQLSTATE `23505`, transacción utilizable mediante SELECT 1 y un evento antes del rollback.
- El intento de rollback y la comprobación posterior desde otra conexión en READ ONLY ocurren también cuando falla el cuerpo. Los errores originales y de limpieza se acumulan por separado; el fallo final no imprime traceback del driver. También se captura un error de dispose sin reemplazar los anteriores.

No se afirma todavía que estas aserciones hayan pasado contra PostgreSQL. Si Docker permite ejecutar, el primer diagnóstico identificará si procede corregir parámetros UUID/TEXT o investigar otra operación. Una corrección funcional sigue pendiente de esa evidencia.

## Validación real

Desde `malaria_dl_local_project`:

```sh
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/etapa1-mpl \
XDG_CACHE_HOME=/private/tmp/etapa1-cache .venv/bin/python -B -m pytest \
-q -p no:cacheprovider --basetemp=/private/tmp/etapa1-diagnostic-tests \
tests/test_dataset_stage1.py tests/test_dataset_evidence_postgres.py
```

Resultado final: **56 passed, 1 skipped, 2 warnings**, 2.83 s. Advertencias de dependencias protobuf; integración omitida sin opt-in. Una primera invocación desde la raíz falló en colección por imports (`src`, `run_train_all_models`); se corrigió el directorio de ejecución, no el código para ocultar ese error.

Se ejecutaron dos comprobaciones sintéticas adicionales del sanitizador: excepción cuyo `__str__` falla deliberadamente y excepción sin SQLSTATE. Ambas pasaron. El SQLSTATE simulado no es evidencia del error PostgreSQL. `git diff --check` pasó. No se generaron CSV ni fallback de evidencia; el escritor no cambió.

Se intentaron tanto `docker compose ps --status running --services` como el comando de integración solicitado. Ambos terminaron con código 1:

```text
permission denied while trying to connect to the docker API at unix:///<usuario>/.docker/run/docker.sock
```

La restricción es de acceso en esta sesión; no contradice el acceso comunicado desde la terminal del usuario ni demuestra que la BD esté caída. No se cambiaron permisos ni servicios y no se usó otra instancia.

## Ejecución pendiente desde la terminal con acceso

Desde la raíz del repositorio, con el archivo de prueba actualizado visible en el mount existente:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE1_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_dataset_evidence_postgres.py
```

No requiere imprimir credenciales ni modificar servicios. Si falla, compartir únicamente el resumen `Synthetic evidence failure`, que conserva fase, tipo, SQLSTATE y diferencias estructurales sintéticas. Un rechazo de duplicado distinto de `23505` no se presenta como éxito.

## Dictamen

| Evidencia | Estado |
|---|---|
| D1 y D2 | Comprobadas según contexto aportado por el usuario; no repetidas aquí |
| Causa original del fallo | NO DEMOSTRADA; hipótesis UUID/TEXT pendiente |
| Defecto de limpieza del test | Confirmado estáticamente y corregido |
| Pruebas locales afectadas | 56 aprobadas |
| Inserción, igualdad, duplicado y continuidad de transacción en PostgreSQL | NO VERIFICADOS en esta sesión |
| Un evento antes y cero después del rollback desde conexión posterior | Aserciones implementadas; NO VERIFICADOS en PostgreSQL |
| E1 | **NO APROBADA** |

Una integración aislada aprobada con rollback demostraría el comportamiento dentro del aislamiento solicitado, no durabilidad de un commit entre sesiones. No se creó un TRAIN operativo ni se ejecutó fit/predict. Split, dataset, checkpoints, esquema y publicaciones permanecen intactos. Se conservan los informes anteriores. No se inicia Etapa 2; selección de Producción permanece manual.
