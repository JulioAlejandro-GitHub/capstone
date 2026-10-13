# CAPSTONE-DB-02A — Cierre de Fase 2A

Estado documental: `HISTORICAL_AUDIT` — 2026-10-12. Dos bloques implementados y validados. **No desplegado**; un fallo previo de la suite global frontend permanece fuera de alcance.

La rama `capstone-db-02a`, checkout `/private/tmp/capstone-db-02a`, parte de `9961ede`. Se trabaja allí porque el backend operativo monta el checkout original con `uvicorn --reload`: editarlo habría recargado el servicio sin autorización. Los cambios no se han copiado al código operativo ni se han reiniciado/reconstruido servicios.

| Verificación | Estado |
|---|---|
| Respaldo previo | **PASS**: los 19 hashes de Fase 1 coinciden; nuevo custom dump, manifiesto SHA-256 y pg_restore --list exitosos |
| Observabilidad: causa original registrada de forma segura | **PASS**, trigger real y SQL inválido, códigos y correlation_id en log/HTTP, sanitización y rollback |
| Observabilidad: UI distingue red, 422 y 500 | **PASS**, además timeout/cancelación/otros estados |
| DB-03: lista, contadores y detalle | **PASS**, incluidos referencias, error de artefacto y paginación 100+6 |
| Pruebas ejecutadas en base aislada | **PASS**: 16 observabilidad/campañas + 52 DB-03 |
| Lectura de solo lectura sobre la base operativa | **PASS**: 14 TRAIN; uno con 1 EVALUATE + 2 EXPLAIN, otros 13 cero |
| Catálogo PostgreSQL idéntico a la línea base | **PASS**, igualdad byte a byte de catalog_initial.json y catalog_final.json |
| Sin DDL ni escrituras sobre la base operativa | **Confirmado** por operaciones ejecutadas y sesiones operativas read-only |

## Respaldo y entorno

Respaldo en el checkout original: `backups/capstone_db_02a/20261012_phase2a/`, excluido de Git; directorio 0700, archivos 0600. Se generó antes de modificar código. No se restauró sobre la base operativa.

Se creó `capstone_db02a_test_20261012` en la instancia existente, claramente separada de `malaria_experiments`. Solo se restauró el esquema vigente con pg_restore --schema-only, sin Alembic. Contiene tres modelos sintéticos para las pruebas de catálogo; no se copió el dataset ni datos operativos. La base aislada permanece disponible para reproducir las pruebas. Las pruebas nuevas de escritura comprueban explícitamente su nombre antes de escribir. Cero campañas/configuraciones/miembros persistidos por los ensayos fallidos.

El código de pruebas se copió a `/tmp/capstone-db02a` del contenedor backend y se importó desde allí en procesos separados; no se reemplazaron módulos del servicio operativo.

## Resultados y límites

- Pruebas específicas UI: 15 PASS. TypeScript/Vite: PASS.
- Suite completa frontend: 264 PASS / 1 FAIL. `executions-dataset-version.test.mjs` espera «No registrado»; `RunSummaryRow.tsx` ya contenía «No registrado 2» en el commit base. Es anterior a esta fase; no se modifica por estar fuera de alcance. No se declara PASS global.
- Deprecaciones existentes de Starlette/httpx y advertencia Vite por bundle mayor a 500 kB; sin instalación de dependencias.
- No se ejecutaron TRAIN/EVALUATE/EXPLAIN, creación de campañas desde UI, migraciones, cambios de DB-01/DB-02, constraints, triggers, funciones, índices o vistas operativas.
- No se verificaron imágenes externas ni hashes de sus contenidos. El frontend conserva referencias y reporta indisponibilidad del archivo sin ocultar la ejecución.
- El error concreto del usuario al crear campaña no puede atribuirse todavía mediante el nuevo correlation_id: requiere desplegar este código y que el usuario repita la acción. La prueba aislada confirma que CAMPAIGN_DATASET_EVIDENCE_CONFLICT se conserva; no demuestra que todo error operativo tenga esa causa.

Para ver los cambios en la interfaz operativa hace falta integrarlos y autorizar la recarga del servicio. Esta fase entrega el código revisable en la rama aislada y se detiene; no inicia DB-01/DB-02.

## Bitácora reproducible

1. Lectura del prompt, skills y documentos Fase 1; git status inicial: solo ZIP documental no seguido, preservado.
2. Python hashlib sobre backup_manifest.json: 19/19 PASS.
3. docker ps/inspect y SELECT pg_database: tres servicios, backend --reload, inicialmente solo malaria_experiments y postgres.
4. pg_dump custom con PGOPTIONS default_transaction_read_only=on: exit 0; pg_restore --list: exit 0; SHA-256 en manifiesto.
5. catalog_queries.sql de Fase 1 vía psql read-only: catalog_initial.json; repetido al cierre: catalog_final.json, idéntico.
6. git worktree add -b capstone-db-02a /private/tmp/capstone-db-02a HEAD.
7. createdb de capstone_db02a_test_20261012; pg_restore --schema-only --exit-on-error allí. No Alembic.
8. Tres INSERT sintéticos en models de la base aislada (un primer envío sin stdin no ejecutó SQL; se corrigió con docker exec -i).
9. Copia de app/tests/src/configs a /tmp del contenedor; Makefile de auditoría ejecuta run_tests.py que sustituye exclusivamente el nombre de base en la URL mantenida en memoria. No registra credenciales.
10. test-observability: 16 PASS. Fallos iniciales de preparación y su resolución figuran en 01_observability_changes.md.
11. test-db03: 52 PASS. Primera ejecución detectó UUID sintético inválido y dobles sin offset; corregidos, sin alterar el esquema.
12. test-db03-ui y build-ui: PASS. Suite completa documentada con fallo previo explícito.
13. read_operational.py mediante docker exec: PASS agregado de 14 TRAIN, sin IDs ni contenido clínico en salida.
14. git diff --check; revisión de archivos fuera de alcance; comparación del catálogo y actualización del manifiesto de respaldo.

Documentos limitados a `docs/audits/capstone_db_02a/`, conforme al alcance explícito del prompt; no se modifica el índice general docs/README.md.
