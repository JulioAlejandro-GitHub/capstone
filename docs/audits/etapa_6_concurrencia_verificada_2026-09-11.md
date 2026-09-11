# E6 — Concurrencia PostgreSQL verificada por el usuario

**Reserva concurrente: VERIFICADA en esquema sintético. E6: NO APROBADA**, pendiente de la suite sintética completa de la revisión corregida, migración operativa y lectura pública/readiness.

Evidencia recibida del usuario: ejecución Compose de `tests/test_assessment_postgres.py::test_concurrent_equivalent_requests_have_one_owner`, con `RUN_STAGE6_POSTGRES_TESTS=1`, `PYTHONDONTWRITEBYTECODE=1`, `pytest -q -s -p no:cacheprovider`. Resultado: **1 passed in 0.55s**.

Diagnóstico original reproducido:

```text
phase=original:INSERT
exception=UniqueViolation
SQLSTATE=23505
constraint=assessment_identities_structural_hash_key
original successes=1; failures=1
```

Esto confirma la hipótesis registrada en el complemento anterior: el INSERT anterior manejaba únicamente `identity_hash`, mientras el conflicto concurrente se producía en la unicidad de `structural_hash`. El `CampaignError` externo era la sanitización del fallo del driver, no su causa original.

La fase corregida informó:

```text
E6 corrected reservation: two connections, one identity, one active attempt, one owner
```

Pasaron las aserciones de dos conexiones diferentes, una sola creación, igualdad del intento y propietario y conteos SQL de una identidad/un intento. Se conservó el aislamiento revisado: conexiones al esquema sintético, commit sólo para hacerlo visible entre conexiones y limpieza verificada por el fixture. No hubo error de teardown en la salida aportada. Esto no acredita instalación en public ni resiliencia ante caída física del host.

Procedencia: resultado ejecutado por el usuario, no reejecutado por el asistente. HEAD local `cd5c64d703358797570f5183dd598d93314dc0eb`; comprobadas **53/53 entradas** del manifiesto de concurrencia sin diferencias. En este cierre sólo se agregan documentación y manifiesto; no se cambia código, pruebas ni migraciones. Se preservan los informes anteriores como evidencia cronológica.

No se suman las 15 pruebas aprobadas de la revisión anterior y esta prueba aislada como si fueran una ejecución completa de la revisión corregida. El siguiente paso es:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE6_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_assessment_postgres.py -k 'not public_e6_revision_readonly'
```

Esperado: 16 passed, 1 deselected. Resultado de esa ejecución aún pendiente. La migración operativa no se ha aplicado desde esta sesión. Se mantienen las restricciones de TEST operativo, producción y E7.
