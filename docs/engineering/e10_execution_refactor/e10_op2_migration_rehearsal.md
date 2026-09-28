# E10.OP2 — Preparación y ensayo de migración PostgreSQL

Fecha: 2026-09-28. Código revisado: `7f24fc58a12c82633645e64dac5f1ecce7cb4712`.
Referencias: [PRE11](e10_pre11_campaign_audit.md),
[OP1](e10_op1_preclaim_schema_guard.md),
[política Alembic](../alembic_simple_policy.md) y
[backup Docker-only](../capstone_backup_runbook.md).

**Resultado:** backup restaurado dos veces, migración ensayada en un PostgreSQL
separado y golden legacy conservado. Public permanece en `20260915_01`.
No se ejecutaron TRAIN, TEST, resume de E9, reservas nuevas ni cambios de release.
No se modificaron migraciones, código de producto o configuración científica.

La [evidencia estructurada](e10_op2_migration_rehearsal_evidence.json) registra
inventario de 97 tablas, identidades de los 36 miembros, siete attempts/runs,
12 configuration hashes, hashes de contenido, catálogos, fallos y recuperación.
SHA-256 del archivo: `1cbee4ae638cacd8f2b9c687dcddcbfd683e3aefda89b8da4e4cdd8e4837763f`.

## 1. Inventario operativo inicial y final

Conexiones SQLAlchemy con `postgresql_readonly=True`, REPEATABLE READ y
`transaction_read_only=on`. Consultas exclusivamente SELECT sobre public y
catálogos; no preflight de dataset, claim ni funciones con efectos operativos.

- Snapshot inicial: **2026-09-28 20:10:33.449183 UTC**.
- Snapshot final: **2026-09-28 20:23:48.807686 UTC**.
- PostgreSQL: **17.9**, base `malaria_experiments`, usuario canónico `julio`.
- Alembic: **20260915_01**, idéntico en ambas lecturas.
- **97 tablas, 1.192.666 filas** en public; los 97 hashes de contenido inicial/final
  son idénticos. También coincide el inventario completo de E9.

| Entidad | Cantidad inicial = final | Estados |
|---|---:|---|
| runs | 99 | completed 88, failed 10, interrupted 1 |
| experimental_campaigns | 2 | paused 2 |
| campaign_members | 72 | pending 63, failed 7, interrupted 1, verified 1 |
| campaign_attempts | 11 | failed 9, interrupted 1, verified 1 |
| train_execution_sessions | 11 | failed 9, interrupted 1, verified 1 |
| local_execution_jobs | 1 | released 1 |
| train_execution_records | 360 | Sin columnas E10; cero filas con kind=e10_event |

Cero sessions active/completed. El gate operativo no tiene owner, db_pid ni
blocked_reason. Estos datos son observaciones de lectura, no una adquisición de
exclusión ni una autorización para entrenar. Los nueve schemas sintéticos
preexistentes conservan sus nombres; **no se escribió en ninguno de ellos**.
Sus nombres completos figuran en la evidencia.

### Identidad de E9 preservada

- Campaign ID: `3acf89b7-dc42-4b7a-8e2a-ca6ea024c344`.
- Nombre: **E9 capstone_science_e7_v1 2026-09-14 corrección numérica**.
- Estado paused; 36 miembros, 12 configuraciones × semillas 11/29/47.
- Miembros pending 31, failed 4, verified 1; siete attempts/sessions/runs:
  seis failed y uno verified. **359 registros legacy** pertenecen a E9.
- Contract hash congelado:
  `02a63b0c76dc600bcb17c7163699abf7dd4e5579643b6adbc783f50d30fcf1ba`.
- Dataset: `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`;
  materialización `e15dc166-1c4b-558e-b77b-727b1783430c`.
- Presupuesto congelado: tres intentos por miembro, máximo 36 miembros.
- El JSON del contrato, protocolo, miembros, configurations y dataset snapshots
  permanece íntegro en el dump restaurado y en las comparaciones de filas. La
  evidencia aporta el protocolo, snapshot y hashes sin duplicar datos históricos
  completos de la base dentro del repositorio.

Los conteos de todo public no deben confundirse con los de esta campaña.

## 2. Migraciones revisadas

El verificador del proyecto confirmó **29 revisiones, una línea y un único head**
`20260922_01`. `verify_alembic_adoption.py`, forzado a READ ONLY, confirmó adopción
válida de `malaria_experiments` en `20260915_01`.

La cadena pendiente contiene **una sola revisión**, sin migraciones intermedias:

```text
20260915_01_local_execution
    → 20260922_01_result_events
```

Archivo: `alembic/versions/20260922_01_result_events.py`.
SHA-256: `8c2014ddfdd43244c81223095acc90be4b1cd83bad67064f86c181c4b7107290`.
No se modificó. También se revisaron `alembic/env.py`, `migrate.sh`, `backup.sh`,
`validate_alembic_transactionally.py`, la política y el verificador de adopción;
sus hashes están en la evidencia.

| DDL / metadata | Efecto |
|---|---|
| ALTER TABLE train_execution_records | Añade `event_id uuid` y `event_sequence numeric`, nullable, sin default |
| CHECK train_event_metadata | Admite metadata nula para legacy con kind distinto de e10_event; exige identidad, secuencia entera positiva finita y payload canónico para E10 |
| UNIQUE train_event_id_unique | Índice parcial de event_id no nulo |
| UNIQUE train_event_sequence_unique | Índice parcial de (run_id,event_sequence), secuencia no nula |
| FUNCTION train_event_guard() | Fencing global, owner y sesión active, secuencia anterior + 1; retorno inmediato para metadata legacy nula |
| TRIGGER a_train_event_guard | BEFORE INSERT por fila; conserva el guard append-only existente |
| ALTER FUNCTION ... SET search_path | Fija schema de instalación y pg_catalog |
| Alembic version update | Cambia `alembic_version` a 20260922_01 dentro de la misma transacción |

Única tabla del producto alterada: `train_execution_records`. No UPDATE de
payloads, runs, attempts, sessions, jobs, contratos o estados. No backfill ni
creación de tablas del producto.

Dependencias: `train_execution_sessions`, `experiment_require_owner()`, el guard
legacy del ledger y las capacidades E10 consumidas por OP1, el worker Docker,
el backend de eventos Local y el repositorio de resultados. Los readers separan
familias por event_id; agregar columnas nulas no crea eventos ni un sello E10.

### Bloqueos e interrupciones

El ALTER TABLE combinado exige ACCESS EXCLUSIVE; la validación del CHECK recorre
las filas existentes. La migración no pide NOT VALID ni índices CONCURRENTLY.
La espera puede bloquear lectores/escritores hasta completar la transacción.
Los índices convencionales también requieren una ventana sin escritores.
Fuentes: [ALTER TABLE PostgreSQL 17](https://www.postgresql.org/docs/17/sql-altertable.html)
y [CREATE INDEX PostgreSQL 17](https://www.postgresql.org/docs/17/sql-createindex.html).

`env.py` utiliza DDL transaccional PostgreSQL y admite una conexión suministrada.
Una pérdida de conexión antes del commit revierte DDL y revisión; se comprobó con
terminación real de una conexión **del contenedor de ensayo**. Si se pierde la
respuesta después del commit, no asumir rollback: leer revisión, capacidades y
golden para decidir. No ejecutar automáticamente downgrade o stamp.

## 3. Backup realizado y procedimiento previo al despliegue

Se ejecutó el wrapper existente, sin cambiarlo:

```sh
CAPSTONE_BACKUP_DIR=/private/tmp/e10_op2_backup bash scripts/db/backup.sh
```

El wrapper verificó identidad canónica por backend/socket, ejecutó pg_dump custom
completo dentro de `db`, rechazó un archivo vacío, validó TOC con pg_restore y
registró SHA-256. Pg_dump obtiene una copia consistente sin modificar los datos;
no cubre los roles globales ni archivos externos. Fuente:
[pg_dump PostgreSQL 17](https://www.postgresql.org/docs/17/app-pgdump.html).

| Propiedad | Evidencia |
|---|---|
| Archivo | `/private/tmp/e10_op2_backup/capstone_20260928T200858Z.dump` |
| Creación del archive | 2026-09-28 20:08:59 UTC |
| Tamaño | 86.829.628 bytes |
| SHA-256 | `6f003efa9e2647b6abb15af40c7372019247abb683de4bc9da4964febc42ecd7` |
| Formato/versiones | CUSTOM, gzip, pg_dump y PostgreSQL 17.9 |
| TOC | 2.856 entradas |
| Origen verificado al restaurar | 20260915_01 |
| Restauraciones efectivas | Dos, completas, con ON_ERROR_STOP y transacción única |
| Bloques COPY por restauración | 311, conservados byte por byte |
| SHA-256 de datos COPY transmitidos | `84bb4db3cad66a23250dae8347ddaa7e8c7803bec0b56029d44b5092a9633c1f` |
| Integridad posterior | 97 tablas de public idénticas al origen; E9 y golden idénticos |

**La validez del ensayo no se basa en el exit code o el TOC:** se restauró el
contenido, se comprobaron tablas, propietarios/ACL, secuencias y objetos, y se
compararon hashes y clasificación legacy. El dump también incluyó los nueve
schemas históricos; sus copias se restauraron sólo en el contenedor separado.
No se modificaron sus originales.

El archivo conservado en `/private/tmp` es evidencia temporal del ensayo, no una
política de retención durable. Antes de una migración real se requiere un **backup
nuevo**, en almacenamiento controlado persistente, checksum registrado y una
restauración verificada del mismo archivo bajo la ventana de mantenimiento.
Se conservará el backup anterior hasta aprobar el despliegue y su retención.

Deben preservarse por separado roles/privilegios globales, configuración de
conexión y los volúmenes de datasets/checkpoints. El dump restaura sus referencias,
no los `.keras` ni las imágenes externas. El rol propietario `julio` se recreó
como rol de fixture en el cluster desechable; no se restauraron contraseñas de
producción ni se ensayó un cambio de endpoints o credenciales operativos.

## 4. Ensayo aislado y procedimiento Alembic

- Contenedor nuevo: `capstone-e10-op2-e141392449`, imagen local `postgres:17.9`.
- Sin puertos publicados ni volúmenes operativos; volumen anónimo propio.
- Base de migración: `e10_op2_rehearsal`.
- Base de recuperación: `e10_op2_restoreproof`.
- Schema de destino en ambas: `capstone_test_op2_e141392449`.
- **Cero tablas en public de ambos destinos**. Public operativo nunca fue destino.

El archive original no se reescribió. Se produjo SQL con pg_restore y se remapeó
`public` al schema de ensayo sólo fuera de bloques COPY, incluidos los search_path
de rutinas. Los bloques COPY se transmitieron sin cambios. Se conservaron
propietarios y ACL del archive; no se usó `--no-owner` ni `--no-acl`.
La restauración se ejecutó mediante psql `-X --single-transaction -v ON_ERROR_STOP=1`.
El remapeo fue un adaptador de este ensayo, no una migración nueva o un cambio
al procedimiento productivo. Se validó por contenido y catálogo, no por sustitución
textual únicamente. [Opciones de restauración PostgreSQL 17](https://www.postgresql.org/docs/17/app-pgrestore.html).

Se utilizó el procedimiento Alembic del proyecto: Config del checkout, el árbol
original, `env.py` y `command.upgrade(config, 'head')`, con conexión suministrada
al destino aislado y aserciones de base/schema. No se llamó `upgrade()` directamente
sobre una migración ni se simuló el head con stamp. Se aplicó el patrón de preflight
transaccional del proyecto y luego un upgrade confirmado.

No se ejecutó `scripts/db/migrate.sh` completo: su conexión canónica apunta al
operativo. El verificador de adopción tiene consultas explícitas a public y se
usó sólo en READ ONLY sobre el origen; no se falseó para la copia remapeada.
Esta adaptación de conexión permite ensayar el mismo Alembic sin modificar scripts
aprobados ni la configuración del servicio.

| Ensayo | Resultado |
|---|---|
| Restauración inicial, antes de migrar | 97 tablas y E9 iguales al snapshot operativo |
| Upgrade dentro de transacción y rollback | Vuelve a 20260915_01; snapshot íntegro |
| Terminación de conexión tras DDL, antes de actualizar revisión | Rollback completo; snapshot íntegro |
| Lector reteniendo AccessShare + lock_timeout 300 ms | SQLSTATE 55P03, sin DDL parcial ni cambio de revisión |
| Upgrade confirmado | Head 20260922_01; 0,0135 s de migración en esta copia |
| Upgrade repetido | No-op; snapshot idéntico |
| Segunda restauración desde el dump origen, sin downgrade | Recupera 20260915_01 y todos los datos/golden |

En el ensayo se limitaron lock_timeout a 2 s y statement_timeout a 30 s para el
upgrade. Los 13,5 ms observados no son una estimación garantizada para producción.
Las restauraciones tardaron 10,591 s y 9,826 s, sin contar exportación, comparación,
aprovisionamiento o recuperación de archivos externos.

## 5. Integridad estructural y del contenido

Tras migrar, las **96 tablas distintas de alembic_version** conservan exactamente
sus hashes de filas originales. Para el ledger se comparó la proyección previa,
excluyendo las dos columnas nuevas, verificadas por separado como NULL en todas
las filas. Las 360 filas legacy siguen presentes y hay **cero filas con event_id
o event_sequence no nulos**.

| Catálogo del schema copiado | Restaurado anterior | Migrado |
|---|---:|---:|
| Constraints | 786 | 787 |
| Índices | 387 | 389 |
| Triggers no internos | 76 | 77 |
| Funciones | 100 | 101 |
| Columnas, incluidas vistas | 1.980 | 1.982 |
| Relaciones con owner/ACL comparados | 125 | 125 |
| Secuencias y valores comparados | 1 | 1 |

La comparación del catálogo de la segunda restauración, todavía en revisión
anterior, con la copia migrada arroja **sólo las adiciones E10 esperadas**.

Se investigaron dos diferencias de presentación entre origen y restauración:
41 defaults calificaban `pg_catalog.gen_random_uuid()` por el search_path del
ensayo; con el mismo orden de resolución las definiciones coinciden. Cuatro
CHECK mostraban el cast de un array varchar a text distribuido sobre sus
constantes. La segunda restauración reproduce esas representaciones antes de
migrar; se verificaron además **88 combinaciones**, incluidos NULL y valores
inválidos, con `IS NOT DISTINCT FROM` sobre las dos expresiones. No se alteró
ningún CHECK para lograr el resultado.

## 6. Golden legacy de los siete runs

Se usó la proyección histórica `kind, phase, record_key, payload`, ordenada por
`kind, phase, record_key`, y el `digest` canónico del proyecto. Antes/después se
compararon counts, payloads, IDs, configuration hashes, dataset snapshots,
attempts, filas completas de run/session, completion y verification.

Los hashes siguientes son **idénticos en origen, copia anterior, copia migrada y
restauración de recuperación**:

| Run ID | Records | records_hash conservado |
|---|---:|---|
| `3894deef-252f-424e-a4ad-d6cd555e063e` | 36 | `afd8e3ca5e80b793a904bfa02e8c0b666b3b100ee8feec511cb5b11af0641723` |
| `61bf6d6d-9db9-498e-a9ee-c26e94e46f2d` | 46 | `7e27f236e42d8d994a885ec48bfc2ac635a9f569ad3a8c9d66cc145d16d90dc6` |
| `79f39931-ac71-4bc1-a317-149a975d1f74` | 26 | `3b7bb3a058cc6e59703c35e1459aa1b5f7ccd231b38cf62e11885ff7e36d349d` |
| `8ebbd308-2cec-4275-93b7-ad56fa9e6931` | 31 | `9933548285bd03acffb1dec988608607f9d68e195a3d0b85455870f14da4916f` |
| `a5f36df1-3341-43fd-94b9-ee1cedb834c5` | 21 | `b4c913704b391467611999b90151d53ee7c175348895d3165a7e605ec3c194af` |
| `d1a1413b-760c-43a2-89ee-7913e780e87a` | 138 | `26ddc6680b16e07c65f7ee30146abca007b7981cf97a49a633276ee6fd6beb30` |
| `ec0975b2-b355-4d5c-a4ec-beac31da72dd` | 61 | `ba6842d3a6094a4c2db0e486606f26bcf3eb951a4ba9ef1363a164a2120eeb4d` |

Sólo el run verified tenía un `completion.records_hash` persistido; los seis
failed tenían completion NULL. No se inventaron seis sellos: para ellos se
comparó el hash calculado de su evidencia histórica. El hash almacenado del run
verified coincide con su proyección y no cambió. Completion y verification se
compararon íntegros, incluidos sus valores nulos.

Los readers reales devolvieron el mismo legacy y cero RunEvents para cada uno de
los siete runs. `is_e10_governed(...)` devolvió **False en los siete**. No se
reservó ningún intento, no se insertaron eventos y no hubo conversión o backfill
artificial a E10.

## 7. Comprobaciones E10.OP1

| Destino / fase | Docker | Local |
|---|---|---|
| Copia restaurada en 20260915_01 | E10_SCHEMA_NOT_READY | E10_SCHEMA_NOT_READY |
| Copia migrada en 20260922_01 | E10_SCHEMA_READY | E10_SCHEMA_READY |
| Public operativo inicial y final | E10_SCHEMA_NOT_READY | Mismas capacidades ausentes |

`E10_SCHEMA_READY` es la etiqueta del ensayo para el retorno exitoso del guard
OP1; no se modificó el formato de retorno del producto. Docker utilizó
`preflight_e10_schema()`. Local invocó su `prepare` real y se detuvo mediante
instrumentación en la siguiente lectura de campaña, después del guard y antes
de validar entorno o crear jobs. No se afirma que toda la preparación científica
Local quede autorizada por aprobar el esquema.

El guard confirmó revisión, tipos/nullability, CHECK validado y definición,
índices únicos/parciales válidos, trigger habilitado y función de fencing con
cuerpo y search_path esperados. Los snapshots antes/después de estas
comprobaciones son idénticos. No se ejecutó un claim como smoke test.

## 8. Riesgos y procedimiento propuesto para el despliegue futuro

No hay blocker observado en la migración aprobada. La aprobación de OP2 permite
**solicitar** despliegue; no sustituye su autorización ni habilita entrenamiento.

1. Fijar el commit, el head único y el checksum de la migración. Mantener E9 paused
   y detener admisión de nuevos trabajos durante la ventana, sin cambiar políticas.
2. Verificar identidad de base/usuario, permisos, sesiones activas, transacciones
   largas, locks, espacio para archive/WAL/índices y acceso a archivos históricos.
3. Ejecutar inventario READ ONLY, `alembic current`, `alembic heads` y el verificador
   de adopción del proyecto. Si origen/golden difieren de lo autorizado, detenerse.
4. Crear backup nuevo con `make db-backup` en ubicación durable; registrar checksum,
   revisión origen y golden. Restaurar ese mismo archivo a un destino aislado y
   aprobar conteos, hashes, constraints, secuencias y propietarios/ACL.
5. Ejecutar el preflight transaccional autorizado y confirmar rollback. Este paso
   también toma locks: requiere la ventana, aunque finalmente revierta el DDL.
6. Sólo con autorización de despliegue, ejecutar Alembic por los comandos del
   proyecto, con timeouts acordados para las conexiones del proceso. Después leer
   current/head, OP1 y golden; no reservar TRAIN para validar la migración.
7. Mantener admisión cerrada si falla cualquier comprobación. Habilitar código o
   entrenamiento exige su revisión y autorización separadas.

El wrapper actual no fija timeouts; public informa lock_timeout=0 y
statement_timeout=0. La siguiente secuencia reproduce los pasos Alembic del
proyecto con timeouts por proceso. **No se ejecutó sobre el operativo y sólo
corresponde después de autorización, backup nuevo restaurado y ventana abierta.**
Debe confirmarse previamente que el head del código autorizado es 20260922_01.

```sh
# Propuesta futura: límites sujetos a autorización; no ejecutar en OP2.
docker compose exec -T -e CAPSTONE_ROOT=/app \
  -e PGOPTIONS='-c lock_timeout=5s -c statement_timeout=60s' \
  backend python - < scripts/db/validate_alembic_transactionally.py
# Continuar sólo tras comprobar rollback a la revisión origen y golden.
docker compose exec -T \
  -e PGOPTIONS='-c lock_timeout=5s -c statement_timeout=60s' \
  backend python -m alembic upgrade head
docker compose exec -T backend python -m alembic current
docker compose exec -T backend python -m alembic heads
```

Confirmar los timeouts efectivos en las conexiones del proceso. Son propuestas
para acordar en la autorización, no cambios aplicados ni garantía de duración.
No cambiar índices a CONCURRENTLY ni editar la migración aprobada como reacción
automática a una espera.

Los riesgos residuales son cambios desde este snapshot, locks de otros procesos,
falta de espacio/permisos, roles globales o archivos externos no recuperables,
conexiones apuntando a otro destino y despliegue de un código/contrato distinto.
OP1 rechaza revisiones desconocidas y definiciones distintas: hay que revisar
compatibilidad al avanzar el head en otra etapa. Aprobar esquema no valida
revisiones técnicas de ejecución, comparabilidad científica ni la matriz E9.

## 9. Plan de restauración ante fallo

| Momento | Acción |
|---|---|
| Antes de comenzar | Si falta identidad, backup restaurado, golden, permiso o ventana, no ejecutar DDL. Mantener pausa/admisión cerrada. |
| Durante Alembic | Conservar error/log, esperar resolución de la transacción y leer revisión + objetos. El ensayo acredita rollback antes del commit; una respuesta perdida no demuestra su resultado. No stamp ni downgrade automático. |
| Después de Alembic, antes de entrenar | Si head, OP1 o golden fallan, mantener bloqueado y conservar el estado fallido para diagnóstico. Priorizar restauración del backup verificado a un destino limpio y comprobarlo antes de cualquier cambio de conexión. |
| Después de instalar código | Mantener admisión cerrada, registrar commit/imagen y verificar contrato esquema/código. Decidir bajo autorización si basta revertir código compatible o restaurar datos. No asumir que revertir código revierte PostgreSQL. |

La recuperación ensayada usó **el mismo archive original**, restaurado a otra
base vacía del cluster desechable, y recuperó las 97 tablas, revisión y golden
originales. No se utilizó downgrade. El downgrade de E10 tiene además un rechazo
si ya existen eventos; aunque no existan, quitar columnas no equivale a recuperar
un snapshot de datos, y la política del proyecto prohíbe downgrades sobre Capstone.

Para un incidente futuro: conservar la base fallida y el backup inmutable,
restaurar en un destino nuevo autorizado, validar todos los hashes/estados/ACL y
archivos, y sólo entonces solicitar el cambio de conexión. No usar DROP DATABASE,
DROP SCHEMA public o `pg_restore --clean` como recuperación automática. Si hubo
escrituras posteriores al backup, definir explícitamente qué datos se perderían
o cómo se recuperarán antes del corte; esta etapa no ensaya recuperación PITR
ni reconciliación de escrituras posteriores.

No se han cambiado endpoints, servicios, credenciales, releases ni deployment.

## 10. Checklist para autorización humana

Evidencia completada:

- [x] Cadena lineal y DDL revisados; migración aprobada sin modificaciones.
- [x] Inventario SELECT inicial/final; E9 identificada sin ambigüedad.
- [x] Backup con checksum, dos restauraciones y revisión origen comprobada.
- [x] Upgrade completo por Alembic en destino sin tablas public.
- [x] Golden de los siete runs y contratos congelados preservados.
- [x] OP1 rechazó antes y aprobó después; sin intentos nuevos.
- [x] Rollback transaccional, interrupción y lock timeout ensayados.
- [x] Recuperación desde backup sin downgrade comprobada.
- [x] Contenedor y volumen de ensayo eliminados; originales intactos.

Pendiente **antes de ejecutar una futura migración operativa**:

- [ ] Autorización humana explícita de destino, commit, revisión y ventana.
- [ ] Responsable de despliegue/restauración, límites de espera y criterios de aborto.
- [ ] Confirmar ausencia de escritores y capturar inventario/golden actualizado.
- [ ] Backup nuevo en ubicación durable y restauración de ese archivo aprobada.
- [ ] Confirmar recuperación de roles/configuración y retención de datasets/checkpoints.
- [ ] Aprobar el plan de corte/restauración sin operaciones destructivas automáticas.
- [ ] Acordar validaciones posteriores de sólo lectura y mantener TRAIN/TEST fuera
      de esta autorización salvo instrucción humana posterior expresa.

## 11. Evidencia, límites y cierre

El contenedor `capstone-e10-op2-e141392449` y su volumen anónimo se eliminaron al
cerrar; se comprobó que no compartía volúmenes con `capstone_db`. Ningún schema
operativo, incluidos los nueve históricos, fue eliminado. El SQL derivado de
restauración y las credenciales desechables se eliminaron. Se conserva el archive
original en la ruta indicada y la evidencia detallada temporal en
`/private/tmp/e10_op2_tools`; no hay credenciales ni dump de datos en el repositorio.

Se corrigieron errores del harness temporal (lectura de propietarios sin dueño
en TOC, permisos de una evidencia copiada y delimitación de una expresión CHECK).
No requirieron corregir migraciones, datos o código del producto. Las comprobaciones
finales descritas pasaron. El ensayo verifica migración/restauración PostgreSQL,
no TRAIN, TEST, inferencia, PITR, disponibilidad bajo carga o un cambio de release.

Archivos añadidos: este documento y
`e10_op2_migration_rehearsal_evidence.json`. Sin otros cambios del repositorio.
Trabajo detenido para revisión humana; no se ejecutó la migración operativa.

**LISTO PARA SOLICITAR MIGRACIÓN OPERATIVA.**
