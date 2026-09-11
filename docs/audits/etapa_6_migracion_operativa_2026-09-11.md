# E6 — Migración operativa instalada mediante wrapper

**Migración operativa: VERIFICADA según la salida aportada por el usuario. E6: NO APROBADA**, pendiente de suite completa y readiness posteriores al upgrade.

El usuario ejecutó `make db-migrate-check` y `make db-migrate` en la instancia Compose autorizada. Evidencias:

- Adopción Alembic válida en `malaria_experiments`; revisión inicial `20260912_01`, head del código `20260912_02`.
- Identidad canónica validada por el wrapper.
- Backup custom `capstone_20260911T183223Z.dump`, contenido requerido comprobado mediante `pg_restore --list`.
- SHA-256 del backup informado por el wrapper: `adbf49417bd66700ae9d6a10551e36ad47d6382ffd302cdfaa3441b1370ca1bd`.
- Preflight transaccional `20260912_01 → 20260912_02` satisfactorio.
- Rollback confirmado: revisión persistente todavía `20260912_01` después del preflight.
- Upgrade real ejecutado; current y head finales: **`20260912_02 (head)`**.

Esta evidencia distingue la prueba transaccional revertida del upgrade persistente posterior. No se presenta `pg_restore --list` como una restauración completa probada. El asistente no inspeccionó el archivo de backup ni reejecutó el wrapper: la fuente es la salida de terminal del usuario.

HEAD local `cd5c64d703358797570f5183dd598d93314dc0eb`; **59/59 hashes** del manifiesto anterior coinciden. No se cambia código, pruebas ni DDL en este turno. La revisión `20260912_02` pasa a considerarse instalada e inmutable: cualquier corrección futura de esquema requerirá una nueva migración conforme a la política del proyecto.

Se conservan las evidencias anteriores: 16 pruebas sintéticas aprobadas y diagnóstico/corrección concurrente. El fallo público y HTTP 503 registrados previamente ocurrieron antes de esta instalación; no se supone que sus comprobaciones posteriores ya hayan pasado.

## Validación pendiente después de migrar

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE6_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_assessment_postgres.py
curl --fail --silent --show-error http://localhost:8000/ready
```

Esperado: **17 passed**, incluida la lectura pública de revisión/tablas/triggers, y respuesta ready para database, migrations y storage. Todavía no se han recibido esos resultados posteriores al upgrade.

E6 permanece NO APROBADA hasta completar estas evidencias. No se inicia E7 ni se ejecutan evaluaciones científicas, TEST operativo o cambios de producción.
