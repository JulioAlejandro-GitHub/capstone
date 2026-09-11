# E6 — Integración PostgreSQL sintética aprobada

**Integración sintética de la revisión corregida: VERIFICADA. E6: NO APROBADA**, pendiente de instalación operativa y verificación pública/readiness.

El usuario ejecutó en Compose:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE6_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_assessment_postgres.py -k 'not public_e6_revision_readonly'
```

Resultado real aportado: **16 passed, 1 deselected in 2.29s**. La exclusión corresponde a la lectura de revisión/tablas/triggers en public. Las 16 pruebas de esta ejecución incluyen la reserva concurrente corregida; no se sumaron resultados de revisiones distintas.

La evidencia acredita los casos sintéticos de reserva, fencing, predicciones por lotes, conflictos, integridad SQL, artefactos, bloqueo final sintético, consumo de campaña y lectura entre conexiones. Los fixtures completaron sin error de limpieza: transacciones/savepoints y, en los casos que necesitan conexiones independientes, commit del esquema sintético seguido de su eliminación y comprobación de ausencia. No se extrapola a todas las constraints de las tablas padre operativas, a inferencia clínica ni a tolerancia ante caída física del host.

Procedencia: terminal del usuario. No reejecutado por el asistente. HEAD local permanece `cd5c64d703358797570f5183dd598d93314dc0eb`; **55/55 hashes** del manifiesto de concurrencia verificada coinciden. Sólo se agregan este registro y un manifiesto de evidencia; código, tests y migraciones permanecen iguales.

## Siguiente paso operativo

La integración sintética ya permite continuar con el procedimiento documentado. Desde raíz Capstone:

```sh
make db-migrate-check
```

Esperado según la última evidencia operativa: current `20260912_01`, head `20260912_02`. Si el estado difiere, revisar antes de migrar; no reescribir revisiones instaladas. Con el precheck satisfactorio:

```sh
make db-migrate
```

El wrapper revisado conserva validación de adopción, backup custom validado, preflight transaccional, rollback y upgrade, terminando con current/head. No se sustituye por un upgrade directo. La migración no fue aplicada en este turno ni se atribuye su instalación a las pruebas sintéticas.

Después de una migración satisfactoria:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE6_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider tests/test_assessment_postgres.py
curl --fail --silent --show-error http://localhost:8000/ready
```

Esperado: 17 pruebas aprobadas, revisión pública `20260912_02` y database/migrations/storage en ready. Estos resultados aún no se han recibido. E6 sigue NO APROBADA hasta cerrar esas evidencias. No se inicia E7 ni se ejecuta TEST operativo o publicación.
