# E4 — Integración PostgreSQL sintética verificada

Evidencia aportada por el usuario mediante Docker Compose:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE4_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_campaigns_postgres.py -k 'not public_migration_readonly'
```

Resultado comunicado: **49 passed, 1 deselected in 4.43s**. No es una ejecución directa del asistente; la salida no incluye hashes del contenedor. El manifiesto efectivo de código previo es `etapa_4_manifiesto_concurrencia_driver_2026-09-11.json`.

Estado de integración sintética: **VERIFICADA**, según el resultado comunicado y las aserciones de la suite actual. Incluye instalación de ambas revisiones en esquemas sintéticos, round-trip, rechazo de NULL/campos ausentes/tipos/presupuestos inválidos, identidad relacional de TRAIN y alias admitidos, compatibilidad con el escritor E2, atomicidad, concurrencia con dos conexiones, reconstrucción desde otro proceso y limpieza de esquemas. Los casos transaccionales verifican rollback y ausencia posterior; el caso concurrente hace commits sólo en el esquema sintético y verifica su eliminación. No se equipara este resultado a durabilidad de un commit operativo.

Estado de instalación pública: **NO VERIFICADA** en esta ejecución. La única prueba deseleccionada es `test_public_migration_readonly`. Pasar las pruebas sintéticas no acredita que public tenga instalada la revisión 20260911_02. No se aplicó ni se autoriza aplicar una migración operativa por este registro; se mantiene la restricción del usuario y el procedimiento de preflight/backup del repositorio.

Dictamen global E4: **NO APROBADA**, pendiente de acreditar la instalación operativa correspondiente y su comprobación pública. La brecha de integración sintética queda cerrada. No se inició E5 ni entrenamientos. Se conservan todos los informes anteriores; este documento añade evidencia sin modificar código.
