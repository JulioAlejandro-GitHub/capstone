# E10.3 — Adapter PostgreSQL durable de ResultRepository

## 1. Objetivo y referencias

Implementar `PostgresResultRepository.acceptance_scope(context, event)` respetando
el puerto aprobado de E10.2, sin integrar productores ni consolidación científica.
Referencias leídas completas durante esta secuencia de trabajo: [baseline](baseline.md),
[E10.1](e10_1_contracts.md) y [E10.2](e10_2_result_service.md). Se contrastaron los
contratos, servicio, repositorios existentes, fixtures PostgreSQL y migraciones E4–Local.
Base de esta entrega: `cec163a772e80cd368f4719bc5593c7dcff5f925`, árbol inicialmente limpio.
E10.1 y E10.2 permanecen sin modificaciones; no se encontró defecto bloqueante.

```text
RunEvent + ExecutionContext
             |
             v
       ResultService
             |
             v
   ResultRepository (port)
             |
             v
 PostgresResultRepository
             |
             v
         PostgreSQL
```

## 2. Auditoría del esquema previo

Fuente: `alembic/versions/20260912_01_train_execution.py`; cambios posteriores
inspeccionados hasta `20260915_01_local_execution.py`. No se migró ni inspeccionó
contenido científico operativo; la acreditación SQL se hizo en schemas sintéticos.

`train_execution_records` antes de E10.3:

| Columna | Tipo y restricción |
| --- | --- |
| run_id | uuid NOT NULL, FK a train_execution_sessions(run_id) |
| kind | text NOT NULL, vocabulario abierto |
| phase | text NOT NULL |
| record_key | text NOT NULL |
| payload | jsonb NOT NULL, CHECK jsonb_typeof(payload)='object' |
| created_at | timestamptz NOT NULL DEFAULT clock_timestamp() |

PK e índice correspondiente: `(run_id, kind, phase, record_key)`. No había columnas
ni índices de event_id/sequence, ni fingerprint. Por ello UNIQUE(run_id,event_id)
y UNIQUE(run_id,sequence) no podían imponerse sobre columnas existentes.

`train_record_guard`, BEFORE INSERT/UPDATE/DELETE, rechaza UPDATE/DELETE; en INSERT
bloquea la sesión con FOR UPDATE y exige state='active' y owner igual a
`current_setting('capstone.train_owner', true)`. No se reemplaza ni deshabilita.

`train_execution_sessions.run_id` es PK/FK a runs; `attempt_id` es UUID nullable,
UNIQUE/FK a campaign_attempts; `owner` es UUID NOT NULL; state admite active,
completed, verified, failed, interrupted. Su guard conserva identidad y transiciones.
El intento liga `training_run_id`, miembro y campaña; los guards verifican ese linaje.

`ExecutionRepository.put()` configura capstone.train_owner dentro de su transacción,
bloquea sesión, valida owner/active, busca por la PK legacy, compara payload canónico
y hace INSERT sólo si falta. `CampaignRepository.transaction()` puede inyectar
capstone.execution_token; sus scopes de tests admiten savepoints. El nuevo adapter
no reutiliza esos scopes porque E10.2 exige commit efectivo antes de aceptar.

La migración global agrega `experiment_execution_gate`, el advisory lock de
coordinador `(120994,1)`, un índice de única sesión active/completed y guards de
reservas. `experiment_require_owner()` exige token de gate y lock de coordinador
o job Local retenido (held/calculation_reported). El guard bloquea la fila singleton.
No se agrega otro advisory lock en E10.3.

## 3. Decisión de persistencia

Se extiende `train_execution_records`; no se crea una tabla auxiliar, una segunda
identidad de run ni persistencia alternativa. `runs` sigue siendo canónico.

Se añaden sólo dos columnas nullable sin default/backfill:

- `event_id UUID`: identidad global de E10.2, con índice único parcial global.
  Es más fuerte que UNIQUE(run_id,event_id), preservando lo aprobado en E10.2.
- `event_sequence NUMERIC`: entero positivo finito, con índice único parcial
  `(run_id,event_sequence)`. NUMERIC evita imponer silenciosamente el límite bigint
  a los enteros Python admitidos por E10.1; CHECK exige trunc(sequence)=sequence.

El resto del envelope vive una sola vez como texto canónico en el payload existente:

```json
{"canonical_event": "<texto JSON exacto de canonical_event(event)>"}
```

Ese texto es la identidad/fingerprint completo, no un hash abreviado. Conserva
schema_version, event_type, occurred_at, payload y los IDs del envelope. Sólo los
IDs/sequence necesarios para índices y el schema del namespace se proyectan fuera.
No se crea columna redundante de fingerprint o timestamp científico.

JSONB normaliza representaciones numéricas y no admite todos los strings que E10.1
acepta. Guardar el canonical como string escapado permite conservar 1/1.0, true/1,
0.0/-0.0, NUL y surrogates escapados. El adapter reconstruye con RunEvent.from_dict
y exige igualdad del canonical y de run_id/event_id/sequence/kind/phase/record_key.
No usa igualdad numérica JSONB para idempotencia.

## 4. Migración

Archivo: `alembic/versions/20260922_01_result_events.py`.
Revision `20260922_01`, down_revision `20260915_01`; historia lineal, 29 revisiones.

Añade columnas, CHECK de metadatos completos/namespace, índices parciales
`train_event_id_unique` y `train_event_sequence_unique`, función train_event_guard
y trigger BEFORE INSERT `a_train_event_guard`. Se fija search_path de la función
al schema de instalación, igual que las migraciones existentes.

El trigger nuevo actúa sólo sobre filas E10. Reutiliza experiment_require_owner,
bloquea sesión, comprueba owner/active y exige siguiente sequence. El trigger original
continúa imponiendo append-only y ownership a todas las filas. No se desactiva ningún guard.

El CHECK exige los dos metadatos juntos o ambos NULL para legacy, y reserva kind
`e10_event`. Si una instalación histórica hubiera usado ese nombre reservado, el
upgrade fallaría en lugar de reinterpretar o borrar esos datos; no se inventa backfill.

PostgreSQL valida wrapper/namespace, ownership, secuencia e índices. El texto del
envelope es opaco para SQL: la validación completa E10.1/canonical reside en el
adapter. Intentar parsear ese texto en funciones JSON de PostgreSQL rechazaba strings
válidos de E10.1; la prueba de NUL detectó ese caso durante el desarrollo. Una fila
malformada insertada por SQL directo autorizado se rechaza al reconstruirla, sin
falsa aceptación. SQL directo no es una API alternativa de resultados científicos.

Downgrade adquiere ACCESS EXCLUSIVE antes de comprobar datos, evitando una carrera
con nuevos INSERT. Sin eventos E10 elimina sólo los objetos añadidos y conserva legacy.
Con eventos E10 aborta con E10_EVENTS_REQUIRE_FORWARD_MIGRATION: eliminar metadatos
perdería idempotencia durable. Requiere una migración posterior explícita, no borrado.
Se acreditó upgrade → inspección → downgrade → inspección → upgrade con legacy.

## 5. PostgresResultRepository

Ubicación: `malaria_dl_local_project/src/malaria_dl/persistence/result_repository.py`.
Coherente con el límite de infraestructura existente; queda fuera de results/.
Usa SQLAlchemy/psycopg y get_engine existentes, sin otra librería ni cambios de paquetes.

Construcción:

```python
repository = PostgresResultRepository(execution_token=trusted_gate_uuid)
service = ResultService(repository)
acceptance = service.accept_event(context, event)
```

El ejemplo describe composición futura; no se ejecuta desde rutas productivas.
`engine_factory` es inyectable para tests y debe devolver un Engine propiedad del
adapter. No recibe Connection, Session ni transacción externa.
La clase implementa exactamente el puerto aprobado y entrega un scope ligado al evento.
`scope.state` expone datos reconstruidos; `scope.append()` inserta una sola vez.
Usar el scope fuera de su vida útil produce ResultPersistenceError.

## 6. Transaction boundary

Cada aceptación obtiene Engine/conexión nuevos, establece READ COMMITTED e inicia
una transacción raíz. Configura ambos tokens con set_config(...,true), autoriza,
lee evidencia/secuencia, cede el scope al servicio, inserta cuando corresponde y
confirma antes de retornar. Cierra conexión y dispone Engine. No hay caché Python
ni posibilidad de confirmar únicamente un savepoint de una transacción exterior.

ResultError conserva su tipo. Fallos SQLAlchemy/DBAPI se traducen a
ResultPersistenceError; los mensajes exactos de fencing se traducen a
WriterNotAuthorized sin exponer SQL/parámetros del driver. Una excepción del cuerpo
se propaga y revierte trabajo sin confirmar. Un fallo de ACK tras commit puede ser
incierto: no se afirma rollback de un commit que PostgreSQL ya confirmó.

## 7. Locking

Orden del adapter:

1. experiment_require_owner bloquea el singleton de gate FOR UPDATE.
2. Si hay intento, campaña → miembro → intento FOR SHARE NOWAIT.
3. Sesión FOR UPDATE NOWAIT.
4. Run FOR SHARE NOWAIT.
5. Lecturas de event_id global, sequence y watermark; append; COMMIT.

Todos los locks duran hasta commit/rollback. El singleton existente serializa también
colisiones globales de event_id entre runs; el lock de sesión protege el orden por run.
Los índices son defensa adicional. No se crea un protocolo de advisory locks nuevo.

NOWAIT evita esperar en órdenes invertidos respecto de writers legacy que puedan
haber adquirido campaña/sesión antes del gate. Una contención de ese tipo falla
cerrada como ResultPersistenceError y admite retry con el mismo evento. No se altera
el locking legacy. El trigger E10 se ejecuta alfabéticamente antes del train_record_guard,
adquiriendo gate antes de sesión en INSERT directo; el trigger previo permanece activo.

Se demuestra con una segunda conexión que la sesión no puede bloquearse mientras
el append está sin commit, y que vuelve a poder bloquearse después del commit.

## 8. Fencing e identidad

Misma autorización para ExecutionMode.DOCKER y LOCAL_PYTHON; no hay ramas por modo.
Se comprueban:

- token del gate mediante la función PostgreSQL vigente;
- run/attempt del contexto y evento exactamente iguales;
- existencia de sesión, owner igual y state active, attempt exacto (incluido None);
- run training/running y dataset_version_id coincidente con contexto y snapshot;
- model_id del registry y adapter_version coincidentes con configuración de sesión;
- intento active ligado al run, miembro active y campaña active o paused (controlada);
- campaign_id/member_id/configuration_hash/contract_hash suministrados coincidentes.

Standalone acepta attempt_id=None sin fabricar linaje. Los campos opcionales no
omiten los controles obligatorios. Las comprobaciones se repiten también para retries.

El token global y el owner de sesión son identidades diferentes. El adapter recibe
execution_token desde composición confiable y exige que context.owner ya corresponda
al owner interno autorizado de sesión. Traducir el owner público Local en el contexto
futuro queda fuera de esta etapa; no se acepta indistintamente cualquier token.
La revocación de los writers existentes que respetan gate/sesión queda serializada.

## 9. Idempotencia durable

Lookup global por event_id, reconstrucción del envelope y decisión canónica en
ResultService sin cambios. Duplicate no ejecuta INSERT/UPDATE y conserva created_at,
occurred_at, payload y sequence. Mismo ID con contenido distinto genera EventIdConflict.
El índice global impide además insertar dos filas con el mismo event_id por SQL directo.
Se probó que un ID no puede trasladarse a otro run después de cerrar el anterior.

## 10. Sequence durable

`max(event_sequence)` sobre filas E10 del run, con cero para stream vacío. Legacy
NULL no cuenta. No se deduce de created_at, del número de records ni de orden lexicográfico.
El servicio mantiene la prioridad duplicate/ID conflict → sequence conflict → gap/stale.
El trigger impide insertar un salto aun mediante SQL directo.

En un historial contiguo append-only sano, una posición antigua siempre está ocupada:
corresponde SEQUENCE_CONFLICT antes que STALE_SEQUENCE. No se crea una historia con
huecos deshabilitando triggers para forzar ese caso. La rama STALE_SEQUENCE aprobada
sigue acreditada por E10.2; la prueba PostgreSQL acredita que el snapshot durable no
fabrica huecos. No existe purga/reutilización de secuencias ni contador en memoria.

## 11. Mapping de RunEvent

| Campo | Representación durable |
| --- | --- |
| run_id | FK existente run_id y envelope canónico |
| event_id | columna UUID, record_key textual y envelope |
| sequence | event_sequence NUMERIC entero y envelope |
| schema_version | phase='run_event_v1' y envelope |
| event_type | envelope, sin traducir al vocabulario científico legacy |
| occurred_at | ISO-8601 UTC dentro del canonical; distinto de created_at del INSERT |
| attempt_id | envelope; identidad contrastada con sesión por adapter |
| payload | payload científico íntegro dentro del canonical string |
| fingerprint | texto completo canonical_event, en payload.canonical_event |

Todas las filas nuevas tienen kind='e10_event'. EVALUATION_COMPLETED,
TRAINING_COMPLETED y TRAINING_FAILED sólo son evidencia de evento: no activan
completion, verificación, actualización de métricas o transición de estados.
HEARTBEAT puede representarse por el contrato, pero el heartbeat operativo no se integra.

## 12. Compatibilidad legacy y frontera temporal

Runtime, epoch, artifact_prepared, artifact, predictions, selection, phase y
calibration siguen escribiéndose por ExecutionRepository.put sin nuevos parámetros.
Columnas nuevas quedan NULL. La PK, FK, CHECK original, timestamps y guard original
se preservan; no hay backfill o reconstrucción de IDs/secuencias históricas.
Las pruebas comprueban los ocho kinds, retries legacy y rechazo de owner incorrecto.

El nuevo namespace no se inyecta en ningún run productivo. Cuando se integre, los
lectores actuales que incluyen todos los kinds (por ejemplo records_hash) deberán
ser evaluados explícitamente: coexistencia física no equivale a integración ya validada.

## 13. Concurrencia

Pruebas PostgreSQL con dos conexiones simultáneas y pg_backend_pid distintos,
barrera antes de aceptar, sin mocks del almacenamiento:

- IDs distintos / misma sequence: una aceptación y un SequenceConflict.
- Mismo evento: ACCEPTED + DUPLICATE_ACCEPTED, una fila.
- Mismo ID / payload distinto: una aceptación y EventIdConflict.
- Owner inválido compitiendo con válido: sólo el válido persiste.
- Writer que revierte mientras otro intenta: retry posterior acepta, sin residuo.

Se usan schemas temporales; no se simulan estas garantías sólo con un lock Python.

## 14. Rollback y migración reversible

Fallo controlado de SQLAlchemy en la frontera de commit, después del INSERT real:
ResultService levanta ResultPersistenceError; otra conexión acredita ausencia de fila;
retry limpio acepta. Excepción del cuerpo del scope también revierte y libera locks.
UPDATE/DELETE de evidencia siguen rechazados por el trigger original.

La prueba de roundtrip compara constraints, triggers habilitados e índices tras
re-upgrade, y verifica payload legacy y metadatos NULL. La prueba separada con evento
E10 acredita el bloqueo del downgrade y conservación de toda la evidencia.

## 15. Restart y ACK perdido

Cada llamada crea y elimina conexión/Engine; los tests repiten usando otro objeto
PostgresResultRepository. PostgreSQL devuelve DUPLICATE_ACCEPTED sin segunda fila.
La simulación de ACK perdido ocurre después de un COMMIT real y antes de entregar
respuesta al llamador: el retry conserva exactamente la fila original.
No se simula reinicio del servidor PostgreSQL ni se requiere para acreditar ausencia
de estado idempotente en memoria del backend/worker.

## 16. Pruebas, entorno y archivos

Archivos creados (cinco); ningún archivo preexistente modificado:

- `alembic/versions/20260922_01_result_events.py`
- `malaria_dl_local_project/src/malaria_dl/persistence/result_repository.py`
- `malaria_dl_local_project/tests/test_result_repository_postgres.py`
- `malaria_dl_local_project/tests/test_result_postgres_architecture.py`
- `docs/engineering/e10_execution_refactor/e10_3_postgres_result_repository.md`

Infraestructura: contenedor backend existente, PostgreSQL del servicio db y fixture
aprobada `test_campaigns_postgres.isolated`. Crea schema capstone_test_e4_<uuid>,
instala migraciones reales, usa padres sintéticos con FKs y se elimina en finally.
La fixture copia sólo definición de audit_events; no filas operativas. Sus padres
mínimos no acreditan todas las restricciones históricas de las tablas public.

No se creó otro servidor ni BD ni se aplicó upgrade al esquema operativo. Los jobs,
campañas y runs utilizados son sintéticos. No se tomó el advisory lock global operativo:
el gate sintético satisface la función real con un job held en el propio schema.
Pruebas de ExecutionMode no afirman haber ejecutado Docker/Local científicamente.

Código copiado a `/tmp/capstone_e10_3_767670a2` del backend, separado de la aplicación
desplegada. Python backend 3.12.14, pytest 8.4.2, SQLAlchemy 2.0.52, psycopg 3.3.5;
unitarios locales en el venv existente 3.12.13. Sin instalaciones.

Resultados finales únicos: **250 pruebas aprobadas**.

| Grupo | Resultado |
| --- | --- |
| E10.1/E10.2, incluidas guardas aprobadas | 167 passed |
| PostgreSQL E10.3 | 49 passed (46 iniciales + 3 comprobaciones adicionales) |
| Guardas E10.3 | 2 passed |
| Regresión PostgreSQL ExecutionRepository/controlada | 32 passed; 1 test public excluido |

La selección adicional de tres pruebas dejó 46 deselected ya aprobadas; no son
pruebas pendientes. Durante desarrollo se corrigieron sintaxis CASE de un borrador
SQL y procesamiento PostgreSQL de Unicode; esos errores no corresponden al resultado final.

Comandos desde la copia temporal del repo en backend (variables de conexión ya
configuradas por Compose, no impresas ni modificadas):

```sh
# Prefijo común: docker exec -w /tmp/capstone_e10_3_767670a2
# -e PYTHONPATH=/tmp/capstone_e10_3_767670a2/malaria_dl_local_project
# -e PYTHONDONTWRITEBYTECODE=1 -e PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
# añadir las variables opt-in antes de capstone_backend:
# -e RUN_E10_POSTGRES_TESTS=1
python -B -m pytest -p no:cacheprovider malaria_dl_local_project/tests/test_result_repository_postgres.py -q --tb=short
# Regresión: RUN_STAGE5_POSTGRES_TESTS=1 y RUN_STAGE93_CONTROLLED_POSTGRES_TESTS=1
python -B -m pytest -p no:cacheprovider malaria_dl_local_project/tests/test_campaign_executor_postgres.py malaria_dl_local_project/tests/test_controlled_train_postgres.py -k 'not public' -q --tb=short
```

Unitarios/guardas en raíz local con PYTHONPATH=malaria_dl_local_project,
PYTHONDONTWRITEBYTECODE=1 y PYTEST_DISABLE_PLUGIN_AUTOLOAD=1:

```sh
malaria_dl_local_project/.venv-local-train/bin/python -B -m pytest -p no:cacheprovider malaria_dl_local_project/tests/test_execution_contracts.py malaria_dl_local_project/tests/test_execution_contract_dependencies.py malaria_dl_local_project/tests/test_result_service.py malaria_dl_local_project/tests/test_result_dependencies.py -q
malaria_dl_local_project/.venv-local-train/bin/python -B -m pytest -p no:cacheprovider malaria_dl_local_project/tests/test_result_postgres_architecture.py -q
malaria_dl_local_project/.venv-local-train/bin/python -B scripts/db/check_alembic_linearity.py
```

Guardas: results/contratos no importan infraestructura ni PostgresResultRepository;
SQL de migración sin binds accidentales. Historia Alembic lineal comprobada.
Se revisan diff, AST y whitespace también para archivos nuevos no tracked.

## 17. Cambios deliberadamente no realizados

Sin cambios en train, firma, workers, agente, HTTP/FastAPI, Docker/Local, heartbeat,
requirements, VENV, Dockerfile, publicación/deployment, resultados científicos,
TrainingResultsV1, matriz, runs.parameters, progreso/resumen de runs o completed/verified.
No se ejecutaron TRAIN real, TEST clínico ni campañas reales. No se crearon reporters,
spool ni asignador de sequence. No se aplicó migración a public ni se modificaron datos
operativos; únicamente hubo DDL/DML de fixtures en schemas temporales del servicio db.
No se crean commits. E10.4 no implementada.

## 18. Gaps para E10.4

1. Composición externa del adapter y traducción confiable de owner Local a owner
   de sesión, manteniendo separado el token global; definir origen/autorización del contexto.
2. Integración explícita de productores/reporters y un único asignador de secuencia
   por run; el heartbeat operativo sigue fuera hasta acordar coordinación.
3. Evaluar lectores legacy, records_hash y verificación antes de mezclar evidencia E10
   en runs productivos; definir recuperación tras cierre sin relajar writer activo.
4. Aplicar la migración al entorno autorizado sólo en una fase solicitada; preparar
   operación de forward migration si ya existen eventos E10 y se necesita retroceder.
5. Diseñar payloads/consolidación científica posteriormente; persistir eventos no
   resuelve el gap de matriz ni equivale a completed/verified.
6. Probar composición real, fallos de red/reinicio de servidor y owner remapping en
   la integración futura. Esta entrega acredita durabilidad entre conexiones/objetos,
   no ejecuta un restart del servicio DB ni una campaña end-to-end.
