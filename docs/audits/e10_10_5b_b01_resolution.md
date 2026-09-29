# E10.10.5B — Resolución B-01

**B-01 RESUELTA POR DECISIÓN ARQUITECTÓNICA — E10.10.5B PUEDE REANUDARSE.** Decisión explícita del usuario aplicada el 2026-09-29.

## Evidencia original conservada

```sql
CREATE ROLE pg_v2_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
```

```text
ERROR:  role name "pg_v2_migrator" is reserved
DETAIL:  Role names starting with "pg_" are reserved.
```

El segundo nombre contractual, `pg_v2_runtime`, comparte el prefijo reservado; su CREATE no llegó a ejecutarse por ON_ERROR_STOP. [Log original](e10_10_5b_evidence/commands.jsonl), [preflight original](e10_10_5b_evidence/preflight_before_provision.json), [estado vacío original](e10_10_5b_evidence/blocked_state.json), [informe original](e10_10_5b_evidence/b01_original/e10_10_5_route_a_results.md).

## Enmienda autorizada y aplicada

| Antes | Vigente |
| --- | --- |
| pg_v2_migrator | capstone_v2_migrator |
| pg_v2_runtime | capstone_v2_runtime |

El migrador es owner de base/objetos propios v2, sin SUPERUSER, CREATEDB, CREATEROLE, REPLICATION, BYPASSRLS ni memberships. El runtime es independiente, sin esos privilegios ni DDL/TEMP/TRUNCATE/escritura Alembic o edición directa del ledger de migraciones. Las protecciones append-only de E10 y publicación permanecen activas y ensayadas. La lectura pg_control_system se concedió sólo al migrador, por el administrador de la instancia aislada, como exigía A.

Se corrigieron safety.py, README, generador, SQL ACL regenerado, manifiesto, fixtures/tests, runner de provisión/certificación e inventario. Se añadieron notas B-01 al diseño E10.10.4 de arquitectura, estrategia Alembic y plan. Los otros documentos E10.10.4 no contenían nombres de roles ni requerían cambio por B-01. Los SQL históricos, el ledger histórico y los snapshots previos no fueron objeto de sustitución global; sus hashes se volvieron a validar.

Los nombres anteriores permanecen únicamente en evidencia histórica y explicación de la incidencia, nunca en referencias ejecutables. Una prueba estática de regresión verifica esta condición y la suite final pasa.

## Nuevos hashes y comprobación real

Sólo el recurso SQL `10_privileges.sql` cambió por B-01; no cambió la semántica científica. Los hashes de los once recursos y del manifiesto están en [resource_hashes.json](e10_10_5b_evidence/run_b01/resource_hashes.json). El manifiesto previo se conserva en [b01_original/catalog_manifest.json](e10_10_5b_evidence/b01_original/catalog_manifest.json).

El cambio técnico adicional de env.py corrige el envío de literales `%` al driver, sin cambiar el SQL de la guarda. Las correcciones del procedimiento de restore y fixtures se describen en los [resultados Ruta A](e10_10_5_route_a_results.md).

**25/25 pruebas estáticas y 9/9 comandos offline; 46/46 comprobaciones de servidor.** Instalación PostgreSQL 17.9, catálogo exacto, rollback, no-op y backup/restore aprobados. El destino y descriptor nuevos son distintos del bloqueo original. El contenedor nuevo también quedó detenido al finalizar.

[Archivos y hashes finales](e10_10_5b_evidence/run_b01/implementation_files.json). Los snapshots históricos de A y del bloqueo se preservan en b01_original/; no se reescriben como si hubieran usado los nuevos nombres.
