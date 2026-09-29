> Revisión D.1: esta certificación corresponde a la baseline anterior a la corrección propuesta de IDENTITY y defaults. D.1 no ha modificado ni recertificado la baseline. Véase [resolución estructural](e10_10_5d_structural_resolution.md).

# E10.10.5B — Certificación Ruta A

Fecha: 2026-09-29. Gate A aprobado por el usuario; B-01 aprobada por decisión arquitectónica. Alcance ejecutado: exclusivamente B.

**E10.10.5B — RUTA A CERTIFICADA EN POSTGRESQL 17. PENDIENTE DE REVISIÓN Y APROBACIÓN.**

## Resultado de las diez condiciones

| Condición | Resultado y evidencia |
| --- | --- |
| 1. PostgreSQL 17 aislado | PostgreSQL **17.9** real; contenedor, volumen y puerto exclusivos; identidad abajo |
| 2. Preflight antes de escrituras SQL | Preflight administrador antes de provisión y preflight migrador antes de Alembic; OID, system_identifier, versión, roles, owner, recuperación e infraestructura acreditados |
| 3. Roles contractuales | `capstone_v2_migrator` / `capstone_v2_runtime`, conforme a B-01; sin privilegios administrativos ni memberships |
| 4. Baseline mediante alembic_v2.ini | `upgrade head` instaló `pg_v2_baseline` desde public vacío, consumiendo únicamente recursos propios verificados |
| 5. Comparación contra manifiesto | **Cero diferencias** de catálogo y de metadatos de columnas |
| 6. Categorías de catálogo y permisos | Tablas, columnas/tipos/typmods/defaults/generadas/colaciones, PK/UNIQUE/CHECK/FK, índices, vistas, funciones, triggers, secuencia, extensiones, owners y ACL comparados |
| 7. Pruebas negativas críticas | **46/46** comprobaciones de servidor: 40 rechazos esperados y 6 controles positivos, como runtime |
| 8. Rollback y head falso | Fallo SQL real después de 500 CREATE/ALTER; previamente 103 tablas, 111 funciones public y 0 filas de head; después 0 relaciones public, 0 funciones public, sólo plpgsql y sin alembic_version |
| 9. Repetición upgrade head | Sin cambios de catálogo; en verificación ampliada tampoco de filas/xmin/ctid de las 103 tablas ni del estado de secuencia |
| 10. Backup/restore aislado | pg_dump/pg_restore **17.9**, backup custom, restauración en base vacía aislada; catálogo, datos de 103 tablas y secuencia idénticos |

**No quedan pruebas obligatorias de B fallidas o pendientes.** Los fallos iniciales y su corrección se conservan; no se eliminaron restricciones, no se desactivaron triggers ni se utilizó stamp. Gate B requiere revisión y aprobación del usuario.

## Identidad del destino

| Propiedad | Valor |
| --- | --- |
| Imagen | `postgres:17.9`, ID/digest capturados en commands.jsonl |
| Contenedor | `b0bf9a0c4185c4d5aa7000967c36462aa6585d1f2af8a2610da7cf98fd7a9fa1` |
| Nombre | `capstone_v2_isolated_c91e78474e3a` |
| Volumen local exclusivo | `capstone_v2_isolated_c91e78474e3a` |
| Etiqueta isolation_id | `c91e7847-4e3a-496b-8522-d4ec4eec9e3d` |
| Puerto | `127.0.0.1:55476 → 5432/tcp` |
| Base instalada | `capstone_v2_isolated_c91e78474e3a` |
| OID base | `16386` |
| system_identifier | `7691013340265599021` |
| Versión | `170009` (PostgreSQL 17.9, Debian, aarch64) |
| Propietario de base/objetos propios | `capstone_v2_migrator` |
| Estado al cierre | **Contenedor detenido**, volumen y backup conservados |

La creación del volumen y el initdb del contenedor prepararon el clúster; el preflight SQL ocurrió antes de CREATE ROLE/CREATE DATABASE del contrato. Antes de cualquier DDL de baseline se acreditó además la identidad completa como migrador. Cada base auxiliar se creó sólo tras revalidar el clúster y se acreditó vacía con OID propio antes de recibir DDL/datos.

[Preflight de provisión](e10_10_5b_evidence/run_b01/preflight_before_provision.json), [preflight Alembic](e10_10_5b_evidence/run_b01/preflight_before_alembic.json), [descriptor completo](e10_10_5b_evidence/run_b01/target.json), [estado final](e10_10_5b_evidence/run_b01/final_state.json).

El destino original rechazado por B-01 se conserva detenido con su descriptor **parcial** en `e10_10_5b_evidence/target.json`; no se reutilizó como autorización. Las bases auxiliares de referencia, rollback y restore están en el nuevo contenedor aislado; sus identidades se guardan en `run_b01/*_target.json` y `*_preflight.json`.

## Comparación del catálogo

El comparador lee los catálogos nativos PostgreSQL del instalado. Para evitar falsos positivos por formato/casts/typmods, PostgreSQL **17.9** representa canónicamente las sentencias verificadas del manifiesto en una base auxiliar vacía. Esa representación ocurre en una transacción revertida: no instala un head auxiliar ni consume SQL históricos. La definición de la tabla Alembic se toma del contrato `managed_by_alembic`, sin insertar una versión ficticia.

Además, se compilan por separado las declaraciones de columnas del manifiesto en tablas temporales de esa transacción y se comparan tipos/typmods, defaults, expresiones generadas y colaciones. Los nombres, orden y nulabilidad final se comparan directamente contra los metadatos del manifiesto. No se normalizan owners, ACL ni constraints para ocultar diferencias. Los OID internos, que difieren entre bases, se resuelven a nombres y definiciones.

| Objeto | Observado |
| --- | ---: |
| Tablas físicas | 103 (102 aplicación + Alembic) |
| Vistas | 33 |
| Funciones propias | 75 |
| Funciones de pgcrypto en public | 36 |
| Triggers de aplicación | 95 |
| PK / UNIQUE / CHECK / FK | 103 / 75 / 524 / 249 |
| Constraint triggers en pg_constraint | 6 (también incluidos en los 95 triggers) |
| Índices | 407 = 229 independientes + 178 de PK/UNIQUE |
| Secuencias | 1 |
| Extensiones | plpgsql y pgcrypto 1.3 |
| Tipos public | 272 tipos compuestos/arrays administrados por PostgreSQL |
| Filas de atributos | 2271 para tablas, vistas y secuencia |
| Privilegios efectivos tabla/vista del runtime comprobados | 952 combinaciones |

`pg_constraint` contiene 957 filas: las 950 restricciones de aplicación del manifiesto, la PK Alembic y seis constraint triggers. No es una divergencia. Los objetos internos RI/extensión se distinguen de los objetos propios; los tipos base de columnas son los tipos nativos de PostgreSQL, no tipos inventados por la baseline.

Hash del manifiesto: `c1063136941e9429373d91d666fbea5d25afd0dc39f111fdf2b9779aa1f51eb0`.

Hash normalizado del catálogo instalado, esperado y restaurado: `df07e6bfc58c21f8290ffb63324a8f3e57b4561e4fe12be74ce576be993fc58b`.

[Diff completo](e10_10_5_catalog_diff.json), [catálogo instalado](e10_10_5b_evidence/run_b01/installed_catalog.json), [representación esperada](e10_10_5b_evidence/run_b01/manifest_rendered_catalog.json), [catálogo restaurado](e10_10_5b_evidence/run_b01/restored_catalog.json).

Esta comparación acredita conformidad con el manifiesto; no es una especificación científica independiente. Las pruebas de comportamiento complementan esa comprobación y no sustituyen el recorrido de aplicación reservado a E.

## Correcciones e incidencias

1. **B-01 resuelta por decisión arquitectónica:** PostgreSQL rechazó `pg_v2_migrator` por prefijo reservado; el contrato ahora usa `capstone_v2_migrator` y `capstone_v2_runtime`. [Informe B-01](e10_10_5b_b01_resolution.md). No se eludió la reserva ni se tocaron archivos históricos inmutables.
2. **Guarda SQL/psycopg:** `LIKE 'pg_toast%'` y `LIKE 'pg_temp_%'` se enviaban como consulta parametrizada vacía. El driver rechazó el `%` antes del DDL. Se añadió `execution_options={"no_parameters": True}` exclusivamente a esa consulta; el criterio de identidad no cambió. La baseline ya aplicaba esa opción a sus recursos SQL.
3. **Fixtures de publicación:** se reordenaron para probar la FK antes de crear una publicación activa que disparaba una unicidad distinta; se corrigió el evento sintético al literal contractual `MODEL_STAGE2_PUBLISHED`. No se modificaron constraints ni diseño para que pasaran los tests.
4. **Procedimiento de restore:** el primer restore como postgres cambió el owner de pgcrypto y pg_dump omitió la representación explícita del ACL owner-only de alembic_version. Los datos ya coincidían. Se restauró el mismo backup en otra base vacía con `--role capstone_v2_migrator`, se reprodujeron los ACL de base (omitidos por dump sin --create) y el REVOKE exacto del manifiesto sobre alembic_version. El cotejo final es exacto, sin conceder privilegios extra ni modificar la fuente.

No se detectó una incompatibilidad de DDL/cuerpos entre el parser 18.4 y PostgreSQL 17.9 en la instalación. El error de rol es una reserva del servidor, no una diferencia demostrada entre esas versiones; el de `%` es del driver. Todos los cuerpos propios se crearon con `check_function_bodies=true`. No se afirma que se hayan recorrido todas las ramas de las 75 funciones.

## Rollback, idempotencia y restore

[Rollback](e10_10_5b_evidence/run_b01/rollback_result.json): hook de prueba externo a la baseline, sobre la ejecución real de Alembic y sus guardas. Después de 500 CREATE/ALTER ya ejecutados se lanzó `SELECT 1/0`. El proceso falló como se esperaba y una conexión nueva comprobó ausencia de objetos/head. No se añadieron flags de fallo al código de instalación.

[Idempotencia](e10_10_5b_evidence/run_b01/idempotence_result.json): segunda ejecución sobre la instalación vacía de datos científicos y otra repetición con fixtures sintéticos; catálogo y estado no cambian. La evidencia ampliada registra hashes de todas las filas, sus xmin/ctid, secuencia y filas técnicas.

[Restore](e10_10_5b_evidence/run_b01/restore_result.json): comparación de 103 tablas, incluidos fixtures sintéticos persistidos de dataset, TRAIN/configuración, modelo/checkpoint, evaluación externa y métricas generadas, además del head/gate técnico. Los otros fixtures negativos se revierten por transacción. No se copió nada de la base operativa.

Backup: [isolated_backup.dump](e10_10_5b_evidence/run_b01/isolated_backup.dump), SHA-256 `5d4ba68a9c0a5a91a4a08032f300059e4c0136f5e7ff96a75be3605c7196326c`. Hash de datos de origen y restore: `4d381af11f74f2ad7356acf2ed9d89b96257dd584a6c7617844e9cc18eb2e724`. El restore fallido inicial se conserva en `attempt_01_restore_result.json` / `attempt_01_restored_catalog.json` y no cuenta como aprobado.

## Comandos y reproducción

[Comandos capturados, stdin, stdout/stderr y códigos](e10_10_5b_evidence/run_b01/commands.jsonl). [Validación estática final](e10_10_5a_commands.json). Las consultas de catálogo y los fixtures SQL parametrizados están versionados en los scripts y sus hashes se conservan en el inventario de evidencia.

Desde la raíz se ejecutaron estos comandos (los reintentos y subcomandos Docker/psql/Alembic/backup constan en el log):

```sh
PYTHONPATH=/tmp/e10_10_4_sql_parser:. python3 scripts/db/build_v2_baseline.py --write
PYTHONPATH=/tmp/e10_10_4_sql_parser:. python3 scripts/db/check_v2_stage_a.py --alembic-python malaria_dl_local_project/.venv/bin/python
python3 scripts/db/certify_v2_route_a.py setup
malaria_dl_local_project/.venv/bin/python scripts/db/certify_v2_route_a.py preflight
python3 scripts/db/certify_v2_route_a.py upgrade
malaria_dl_local_project/.venv/bin/python scripts/db/verify_v2_route_a.py catalog
malaria_dl_local_project/.venv/bin/python scripts/db/test_v2_route_a_server.py
malaria_dl_local_project/.venv/bin/python scripts/db/verify_v2_route_a.py rollback
malaria_dl_local_project/.venv/bin/python scripts/db/verify_v2_route_a.py idempotence
malaria_dl_local_project/.venv/bin/python scripts/db/verify_v2_route_a.py backup_restore
malaria_dl_local_project/.venv/bin/python scripts/db/verify_v2_route_a.py restore_retry
```

`restore_retry` documenta el reintento real del backup existente; con el procedimiento corregido una reproducción nueva usa `backup_restore` directamente. Para reproducir desde cero sin reutilizar esta autorización, seleccionar un directorio de evidencia **nuevo** mediante `PGV2_EVIDENCE_DIR`, y ejecutar primero `certify_v2_route_a.py init <puerto_exclusivo>`. Ese comando crea un UUID/descriptor nuevo y rechaza puertos 5432/5433 y sobrescrituras. Después se siguen setup/preflight/upgrade/checks. La imagen 17.9 debe estar disponible; el runner de esta estación fija el socket local Docker Desktop que aparece en los logs. En otra estación se debe configurar explícitamente su endpoint local y comprobarlo mediante la misma guarda. Los intérpretes/dependencias están declarados en alembic_v2/requirements*.txt; `/tmp/e10_10_4_sql_parser` fue el entorno local del parser, no parte de la instalación.

Se ejecutaron además inspecciones de archivos con rg/sed/cat, formato/lint de los archivos nuevos, verificación JSON, generación de reportes y detención del contenedor por su ID exacto. La preparación original fallida de B-01 conserva sus comandos en `e10_10_5b_evidence/commands.jsonl`. Los comandos de revisión de código no abren bases.

## Límite y solicitud de Gate B

**PostgreSQL operativo permanece intacto por las acciones de esta entrega.** No recibió conexiones SQL, cambios de roles/datos, backups ni migraciones. Las inspecciones Docker de otros contenedores fueron sólo metadatos para acreditar aislamiento; no se usaron como fuente de adopción. No hubo modificaciones de datasets, modelos, usuarios, campañas ni eventos reales. No se inició C, D o E, ni cutover.

Se solicita **revisión y aprobación explícita de Gate B** sobre esta certificación. El trabajo se detiene aquí; la aprobación no se presume ni inicia automáticamente otra etapa.
