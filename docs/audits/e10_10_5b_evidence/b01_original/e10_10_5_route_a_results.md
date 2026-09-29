# E10.10.5B — Ruta A bloqueada en PostgreSQL 17

Fecha: 2026-09-29. Gate A aprobado explícitamente por el usuario. **Gate B BLOQUEADO. Ruta A no certificada.**

## Resultado y decisión necesaria

PostgreSQL 17.9 real rechazó el primer comando de provisión:

```sql
CREATE ROLE pg_v2_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
```

```text
ERROR:  role name "pg_v2_migrator" is reserved
DETAIL:  Role names starting with "pg_" are reserved.
```

El contrato de A exige `pg_v2_migrator` y `pg_v2_runtime`; ambos nombres usan el prefijo reservado. El error observado corresponde al primer rol. `psql -v ON_ERROR_STOP=1` terminó con código 3 antes del segundo rol y de CREATE DATABASE. La validación estática con parser 18.4 no había detectado esta incompatibilidad del contrato con un servidor real. No se ha establecido que sea una diferencia entre versiones 18 y 17.

Se detuvo B por conflicto arquitectónico, conforme a la instrucción del usuario. Se solicita decisión para sustituir los dos nombres por `capstone_v2_migrator` y `capstone_v2_runtime`, actualizar de forma coherente contrato, guardas, compilador, baseline, manifiesto y tests, y reanudar exclusivamente B. **La propuesta no ha sido aplicada.** No se utilizaron mecanismos para permitir nombres reservados.

## Identidad y preflight

- Imagen local: `postgres:17.9`; ID y RepoDigests registrados en commands.jsonl.
- Contenedor: `ed496415af1c14a6e0f713e95b8d15eda4708c4453261048e63bce7a92bcec53`.
- Nombre y volumen local exclusivo: `capstone_v2_isolated_a150116595db`.
- Etiqueta de aislamiento: `a1501165-95db-4461-8aa5-b45ec3bc8c89`.
- Puerto: `127.0.0.1:55475 → 5432/tcp`.
- PostgreSQL: 17.9, `server_version_num=170009`, Linux aarch64.
- `system_identifier`: `7691009688503029805`.
- Base prevista: `capstone_v2_isolated_a150116595db`, **no creada**, sin OID acreditado.
- Preflight administrador conectado exclusivamente a `postgres` del contenedor aislado; recuperación false.

`inspect_isolation()` verificó identidad/etiquetas, volumen local sin opciones ni montajes compartidos, PGDATA, puerto y contenedor no privilegiado. Antes de CREATE ROLE se persistieron esa comprobación, los metadatos del destino y la lectura SQL de versión/system_identifier. La creación del volumen y el initdb inicial son la preparación de la instancia; el preflight precede toda escritura SQL de provisión del contrato. No se alcanzó el segundo preflight como migrador previo a Alembic.

El contenedor se inicializó con autenticación trust para la prueba local, sin credenciales operativas. **Quedó detenido** tras capturar el bloqueo; el volumen nuevo se conserva. No se efectuaron cambios de configuración en otros contenedores.

## Estado de condiciones obligatorias

| Condición | Resultado |
| --- | --- |
| 1. PostgreSQL 17, puerto y volumen independientes | Cumplida; contenedor posteriormente detenido |
| 2. Preflight antes de provisión SQL | Cumplida; preflight migrador no alcanzado |
| 3. Roles según contrato | **FALLÓ: prefijo reservado** |
| 4. Baseline con alembic_v2.ini | No ejecutada por bloqueo |
| 5–6. Comparación y certificación completa del catálogo | No ejecutada; diff no evaluado |
| 7. Negativas A-01, E10, calibración VAL y publicación | No ejecutadas por bloqueo |
| 8. Fallo intermedio/rollback y ausencia de head falso | No ejecutada la prueba; ausencia de head observada sólo tras provisión fallida |
| 9. Segundo upgrade head sin cambios | No ejecutada por bloqueo |
| 10. Backup/restore aislado | No ejecutado por bloqueo |

No hay correcciones aplicadas a la baseline ni al diseño científico. No se ejecutaron SQL históricos, IF NOT EXISTS, stamp, desactivación de triggers ni eliminación de restricciones. La ausencia de head en esta preparación fallida **no demuestra rollback de Alembic**.

## Evidencia y reproducción

- [Registro exacto de comandos de preparación, SQL, salidas y códigos](e10_10_5b_evidence/commands.jsonl).
- [Preflight persistido antes de provisión](e10_10_5b_evidence/preflight_before_provision.json).
- [Estado posterior mediante consulta de lectura](e10_10_5b_evidence/blocked_state.json): roles ausentes, base prevista inexistente, cero relaciones public y alembic_version ausente en postgres de esta instancia.
- [Descriptor parcial](e10_10_5b_evidence/target.json): deliberadamente sin database_oid; no sirve para autorizar una migración.
- [Runner de preparación y registro](../../scripts/db/certify_v2_route_a.py). No implementa una certificación completa ni reanuda automáticamente una preparación parcial.
- [Diff no evaluado](e10_10_5_catalog_diff.json).

Comando de preparación ejecutado desde la raíz: `python3 scripts/db/certify_v2_route_a.py setup`. Requiere Docker local autorizado y un descriptor nuevo con UUID/nombres exclusivos/puerto libre; el runner rechaza reutilizar un descriptor que ya tenga container_id. El comando SQL mostrado reproduce el rechazo en una instancia PostgreSQL 17 de pruebas con administrador. No se debe ejecutar contra la base operativa.

Las inspecciones iniciales fueron `docker version`, listado de imágenes postgres y listado de nombres/puertos de contenedores. Un primer acceso Docker fue rechazado por el sandbox; la ejecución con escalación fue aprobada y funcionó. La selección dinámica de puerto mediante bind local también fue rechazada por el sandbox, por lo que se fijó 55475 y Docker confirmó la publicación exclusiva al crear el contenedor. Estos problemas de entorno no son el bloqueo arquitectónico.

## Límite y cierre

PostgreSQL operativo no recibió conexiones SQL ni escrituras por esta sesión. Sólo se inspeccionaron metadatos Docker para acreditar aislamiento. No se inició C, D o E; no hubo adopción ni cutover, ni cambios en datasets, modelos, usuarios, campañas o eventos reales. La única escritura de infraestructura fue la creación e inicialización del destino aislado autorizado y su posterior detención.

**E10.10.5B — BLOQUEADA POR CONTRATO DE ROLES INCOMPATIBLE. GATE B BLOQUEADO.** Se requiere decisión arquitectónica antes de continuar; no se solicita aprobación de una certificación inexistente.
