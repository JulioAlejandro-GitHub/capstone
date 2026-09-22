# E10.6 — Productor común y separación del hash legacy

## 1. Objetivo y auditoría previa

Referencias leídas completas antes de modificar código: [baseline](baseline.md),
[E10.1](e10_1_contracts.md), [E10.2](e10_2_result_service.md),
[E10.3](e10_3_postgres_result_repository.md), [E10.4](e10_4_docker_reporter.md) y
[E10.5](e10_5_http_reporter.md). Árbol inicialmente limpio. Fecha: 2026-09-22.

Se revisaron contratos, reporters, composición, results, adaptador PostgreSQL,
train/repository/artifacts/worker, todos los módulos Local y su route FastAPI.
Búsqueda global de records_hash, digest(records), finish, verify_session y SQL de
train_execution_records en fuentes ML, backend, scripts y migraciones.

| Pregunta | Estado anterior al cambio |
|---|---|
| A. Función | `campaigns.contracts.digest(value)`: SHA-256 de `canonical(value).encode('utf-8')`. |
| B. Estructura | Lista de objetos `{kind, phase, record_key, payload}` de `ExecutionRepository.records(run_id)`. |
| C. Orden | SQL `ORDER BY kind,phase,record_key`; claves textuales, no orden numérico de epoch ni created_at. canonical ordena claves de objetos, conserva orden de listas. |
| D. Campos | Exactamente esos cuatro, con todo payload. Excluye columnas run_id/created_at/event_id/event_sequence; los E10 sí introducen IDs/time/sequence dentro del canonical string y record_key. |
| E. Productor | `execution/train.py::train`, después de `repository.records(run)`. Mismo código Docker y Local. |
| F. Momento | Después de todas las fases y `put('calibration','val','selected',...)`, antes de `finish(...,'completed',completion)`. |
| G. Persistencia | Docker: `train_execution_sessions.completion` por finish. Local: Reports.finish → job.completion/calculation_reported; exit copia a sesión y verifica dentro de su transacción legacy. |
| H. Verificador | `execution.artifacts.verify_session`; llamado por campaign/reconcile, controlled/recover, standalone, Local exit y assessment.lineage.resolve. |
| I. Comparación | Primera comprobación después de leer records, antes de épocas/fases/predicciones/selección/checkpoint/loader. Devuelve de nuevo ese digest en verification. |
| J. Filas incluidas | Todas las del run: no había predicado de familia. Por eso añadir E10 cambiaba el digest. |
| K. Ocho kinds | runtime, epoch, artifact_prepared, artifact, predictions, selection, phase y calibration participan completos; no existe allowlist de hash. Cualquier otro kind legacy también participaba. |

Canonical legacy normaliza floats integrales a int (incluido -0.0→0), mantiene
bool/null, Unicode sin normalización, usa JSON compacto, ensure_ascii=False y
allow_nan=False. Ninguna de esas reglas debe cambiar. E10 preserva distinciones
numéricas con su canonical independiente; no se reutiliza el digest legacy allí.

Hallazgo de cierre: ambos guards y ResultRepository exigen sesión active. Por ello
el terminal E10 debe confirmarse **antes** de finish completed/failed. Emitirlo al
volver del train actual sería demasiado tarde. Esta etapa sólo documenta esa regla.

La auditoría anterior se escribió antes de editar código. El objetivo implementado
es preparar un único productor y lectores explícitos para E10.7, sin conectar train.

## 2. Hallazgo records_hash reproducible

La prueba `test_golden_hash_unaffected_by_one_many_events_and_exact_retries` ejecuta
la consulta **anterior exacta**, sin filtro, como diagnóstico: legacy → H1; añadir
E10 → H2 distinto. No se borra esa demostración al corregir el lector. En paralelo,
la consulta corregida conserva H1 después de uno y doce eventos, incluidos retries.

Las pruebas E10.4 y E10.5 que antes acreditaban el blocker se actualizan al nuevo
contrato: records legacy iguales, hash igual y eventos accesibles por result_events.
No se eliminan las comprobaciones de fencing, durabilidad o snapshots.

## 3. Semántica histórica de records_hash

Es el digest de la evidencia legacy completa del run. No es un digest universal
de cada fila física de la tabla durante la transición E10. No se cambian canonical,
digest, proyección, nombres de claves, orden SQL, numeración textual o payloads.
Se conservan los ocho kinds históricos y cualquier otro kind sin metadatos E10:
no se aplica una allowlist que pudiera excluir evidencia histórica adicional.

No hay backfill, reinterpretación de registros, event_stream_hash persistido ni
requisito de eventos E10 para verificar un run legacy. El nuevo contrato no admite
como sustituto un hash experimental calculado incluyendo E10; no hay conversión
silenciosa de completion ni doble aceptación de hashes incompatibles.

## 4. Separación de familias

```text
train_execution_records
    +-- event_id IS NULL ------> legacy records -----> records_hash
    |
    +-- event_id IS NOT NULL --> E10 result events --> canonical E10 + event reader

E10 events ---------------- X ---------------------- records_hash
```

El CHECK `train_event_metadata` de E10.3 exige event_id/event_sequence conjuntamente
NULL para legacy, o ambos presentes con namespace E10 válido. La clasificación se
basa en el **metadato de columna**, no en kind, event_type ni claves del payload.

Predicado SQL compatible usado: `(to_jsonb(record)->>'event_id') IS NULL` para legacy
y `IS NOT NULL` para E10. En esquema E10, UUID NULL produce SQL NULL; UUID presente
produce su texto. En esquema anterior, la propiedad no existe y produce SQL NULL:
todas las filas siguen siendo legacy. Esto permite leer sin forzar upgrade operativo
y ejecutar regresiones E5/control anteriores a E10.3. Se prueba la equivalencia
con una fixture que revierte exclusivamente la migración E10 en su esquema temporal.

El orden E10 usa `(to_jsonb(record)->>'event_sequence')::numeric`, preservando 1…12
en lugar de orden lexicográfico. El costo es convertir la fila a JSONB en lectura;
no se añade índice, caché de esquema ni sondeo a una base externa. Una optimización
futura puede usar columnas directas cuando el rollout de E10.3 sea obligatorio;
no debe alterar familia, proyección u orden histórico.

## 5. Lectores y clasificación completa

Nuevos helpers en `persistence/execution_record_readers.py`:

- `read_legacy_execution_records(connection, run_id)`: cuatro campos históricos,
  sin metadatos añadidos, ordenados como antes.
- `read_result_events(connection, run_id)`: lista de RunEvent, orden numérico,
  validación con el decoder E10.3 existente. Comprueba texto canónico y coherencia
  de las columnas; no devuelve silenciosamente evidencia corrupta. No es API HTTP
  de recovery ni autorización remota; presupone un llamador backend autorizado.

| Lector | Familia y decisión |
|---|---|
| `ExecutionRepository.records()` | Alias compatible de `legacy_records()`. Es el cambio mínimo que alcanza train y Reports sin editarlos. |
| `ExecutionRepository.legacy_records()` | Nueva API explícita legacy, delega al helper. |
| `ExecutionRepository.result_events()` | Nueva API explícita E10; permite leer incluso después de cerrar sesión. No autoriza nuevas escrituras. |
| Lookup idempotente de `ExecutionRepository.put()` | Legacy: se añade el mismo predicado. Así no puede reconocer como éxito legacy una fila E10 con la misma clave física. El CHECK vigente sigue rechazando nuevos inserts legacy en el namespace reservado. |
| `train()` / `verify_session()` | Consumidores legacy a través de records(); código intacto. |
| `Reports.records()` / LocalBackend records | Mismo endpoint/envelope legacy; reciben sólo legacy por delegación al repositorio. Código intacto. |
| campaign/reconcile, controlled/recover, standalone, Local exit | Heredan lectura legacy de verify_session, sin cambios. |
| `assessment.lineage.resolve()` | Revalida hash/verification legacy y lee calibración vía records. Se prueba resolución real tras cierre sintético. Sin cambio de código. |
| `training_summaries` lateral calibration | Se añade predicado de familia antes del filtro calibration/val/selected. Conserva fallback, payload, orden, columnas y respuesta. |
| `PostgresResultRepository` lookup event_id/sequence y max | Ya E10 explícito por metadatos: NULL no coincide con UUID/sequence ni cuenta para max. Sin cambio. |
| `ExecutionRepository.preflight` LIMIT 0/privilegios | Inspección de estructura/permisos, no enumeración de evidencia ni digest. Sin cambio. |
| SQL de guards históricos de epochs/artifacts | No se edita DDL. E10.3 reserva kind=e10_event para filas E10, por lo que los conteos de epoch/artifact existentes no los incluyen. |
| Queries administrativas de fixtures / consulta histórica del test | Enumeran deliberadamente ambas familias. Nunca alimentan completion. No se añade un endpoint administrativo productivo. |

El helper E10 reutiliza `_decode` del adaptador aprobado, sin copiar canonicalización.
Propaga `ResultPersistenceError` ante evidencia corrupta. La fachada histórica
ExecutionRepository conserva su traducción general a
`CampaignError('CAMPAIGN_DATABASE_OPERATION_FAILED')`. Nunca convierte corrupción
en lista vacía. La dependencia del decoder interno queda cubierta por las pruebas.

## 6. Fix mínimo aplicado

La única ruta modificada que afecta al hash es `records → legacy_records → helper`.
No se añade un segundo cálculo de hash ni un filtro posterior sobre objetos que ya
hayan perdido event_id. `verify_session` sigue comparando el hash antes de cualquier
validación científica. Su lógica y su salida permanecen intactas.

Se modifica también la selección de calibración del resumen y el lookup de put,
porque ambos son lectores legacy. No se cambia escritura del ledger ni validación
de resultados E10. El reader separado reconstruye los eventos completos con la
representación aprobada, incluidos Unicode y distinciones 1/1.0/true/-0.0.

## 7. Compatibilidad byte-for-byte y golden

`test_execution_record_readers.py` fija literalmente los bytes UTF-8 previos para
nueve filas sintéticas: los ocho kinds, más el runtime base del fixture PostgreSQL.
Incluye Unicode, booleano, null y normalización 1.0→1 / -0.0→0. SHA-256 fijo:

```text
5ac32b86fba927bfc9efdc66c6425d41f35dd4ef63395d3e11c06e0545d20c40
```

Se compara el byte string completo, además del digest, contra la consulta anterior
legacy-only y la nueva. No se genera el golden durante el test desde la función
bajo prueba. Cambiar/quitar cualquiera de los ocho kinds altera el hash y hace
fallar verify_session. Estas mutaciones se simulan sobre copias en memoria; no se
deshabilitan guards ni se alteran filas append-only para probar un hash incorrecto.

Añadir E10, reenviarlo o presentar contenido E10 distinto no cambia el hash legacy.
La modificación por SQL de un evento y su DELETE son rechazados; mismo ID con otro
payload produce EventIdConflict. Un canonical E10 inconsistente insertado por SQL
autorizado de fixture no contamina el hash legacy, pero el reader E10 lo rechaza.
Son mecanismos de integridad distintos, no una autorización para modificar eventos.

## 8. RunEventEmitter

Ubicación: `execution/emitter.py`. Biblioteca estándar + contratos E10.1 solamente.

```python
stream = RunEventEmitter(reporter, run_id=run_uuid, attempt_id=attempt_uuid)
event = stream.emit(RunEventType.EPOCH_COMPLETED, payload)
# Sólo si una entrega previa falló:
same_event = stream.retry_pending()
```

```text
future scientific producer -- event_type + payload --> RunEventEmitter
                                                          |
                                          UUID / UTC / sequence / binding
                                                          |
                                                     RunReporter
                                                  /               \
                                    DockerRunReporter          HttpRunReporter
                                           |                     HTTP/auth
                                           +-------- ResultService --+
                                                          |
                                                 ResultRepository
                                                          |
                                                     PostgreSQL

train() ---------------- X ---------------- RunEventEmitter
```

Constructor vincula run/attempt sin owner, modo, engine o contexto de infraestructura.
Cada nuevo evento genera uuid4 una vez, timestamp aware UTC, schema aprobado y
payload congelado por RunEvent. `emit` y `retry_pending` devuelven el RunEvent
confirmado para inspección; RunReporter conserva su firma y retorno None.

Estado interno: snapshot inmutable `_State(next_sequence, pending, closed)` y lock
de entrega. Propiedades de consulta sin setters. Un cambio de snapshot confirma
avance/cierre/limpieza juntos, sin ventana de clear-before-advance.

## 9. Sequence e invariante de productor

**Una instancia propietaria del stream científico por run.** Callbacks futuros
comparten esa instancia; no crean contadores separados. Empieza en 1, sólo avanza
después de retorno normal del reporter. Intento None es válido para standalone.
Distintos runs tienen contadores independientes; el repositorio aplica el fencing
y la continuidad durable como segunda defensa.

No se expone next_sequence arbitrario para saltar un pending ni se infiere sequence
de número de records legacy, timestamp o MAX al construir. Llamadas concurrentes
o reentrantes durante una entrega fallan con EventEmissionInProgress; no se encolan
ni disparan dos entregas del mismo slot. No es un asignador entre procesos.

## 10. Pending event

Antes de llamar al reporter se conserva el RunEvent completo en memoria. Toda
excepción de report, incluidas interrupciones, se propaga conservando pending y
next_sequence. Cambiar el dict/list original del producer no muta ese evento.
Con pending no confirmado, emit de otro evento falla con PendingEventExists,
incluido intentar sustituirlo por TRAINING_FAILED. No hay operación de descarte.
Payload inválido falla antes de ocupar el slot y permite volver a emitir en él.

```text
ready -- emit --> pending -- report normal --> ready(next + 1)
                    |
                    +-- report error --> mismo pending
                    |
                    +-- retry normal --> ready(next + 1) o closed
```

## 11. Retry exacto y éxito

`retry_pending()` pasa **la misma instancia** al reporter: ID, sequence, tiempo,
payload y canonical efectivo idénticos. No llama UUID ni reloj otra vez. Sin pending
produce NoPendingEvent. Los reporters aprobados convierten ACCEPTED y
DUPLICATE_ACCEPTED en retorno normal; ése es el único criterio de confirmación del
emitter. No interpreta excepciones de HTTP/DB, no las silencia y no tiene backoff.

Se prueba con ambos reporters y fake transport, más commit PostgreSQL real seguido
de pérdida simulada de ACK: el emitter conserva pending, bloquea el nuevo evento,
reintenta y avanza una vez, con una fila durable. La regresión HTTP real E10.5
conserva autenticación, resolución, fencing, errores y pérdida de respuesta.

## 12. Eventos terminales

TRAINING_COMPLETED y TRAINING_FAILED cierran el stream **sólo tras confirmación**.
Mientras fallen, permanecen pending y closed=False. Tras confirmar, closed=True,
pending=None y no se permite emit ni retry: EventStreamClosed. EVALUATION_COMPLETED
no es terminal. Cerrar el emitter no invoca finish ni cambia estados PostgreSQL.

Si hay un pending anterior no se puede saltar hacia un terminal de fracaso. La
orquestación futura deberá resolver esa entrega o registrar el fallo operativo
según el lifecycle vigente, sin fingir que el terminal E10 fue entregado.

## 13. Límites de restart

El estado es exclusivamente in-memory. Nueva instancia vuelve a 1 y **no recupera**
un stream existente; se prueba explícitamente. No hay promesa de supervivencia a
crash, reanudar desde un último contador leído ni reconstruir payloads desde logs.

Docker E10.7 debe distinguir un run nuevo sin stream de uno activo con evidencia
previa. No construir otro emitter automáticamente para el segundo. Recuperar un
owner autorizado en DB no recupera por sí solo la identidad del evento pendiente.
El nuevo reader de eventos permite inspección, no resuelve el caso de un pending
que nunca llegó al servidor.

## 14. Journal durable Local futuro

Se usa estado en memoria del emitter y reporters/repositorios en memoria sólo en
tests. **No se introduce EventJournal port en esta etapa**: es opcional en la
solicitud y separar save_pending/clear_pending/load_next_sequence antes de definir
atomicidad durable podría crear una promesa incorrecta de recovery.

E10.8 debe diseñar journal/spool con identidad del run/intento, evento serializado
completo y transición atómica de pending/next_sequence/closed, persistiendo antes
de enviar y confirmando después del ACK. Debe contemplar pérdida de ACK, writer
único, fencing y errores del propio journal. No hay implementación SQLite, archivos,
outbox, puerto especulativo ni cambio del agente Local en E10.6.

## 15. Heartbeat excluido

Aunque el enum aprobado conserve HEARTBEAT, emit lo rechaza con
OperationalHeartbeatExcluded antes de crear identidad o consumir sequence. No
entra en pending ni hash. Se conservan thread/endpoint, frecuencia 15 s, expiración
operativa 60 s y semántica de incertidumbre/no liberación del job. No se modifican
contratos ni aceptación genérica E10.2/E10.3 para eliminar aquel enum.

## 16. Mapa de producers futuros (sin integración)

Referencias relativas a `malaria_dl_local_project/src/malaria_dl/`.
La tabla describe datos ya existentes; no implementa un nuevo schema científico.
Los payloads deben derivarse una vez de la evidencia disponible, sin recalcular
métricas ni copiar indiscriminadamente history, snapshots o arrays de muestras.

| Producer actual | Evento futuro | Payload mínimo disponible / orden |
|---|---|---|
| `train.py:190` put runtime tras compile y configurar callbacks | PHASE_STARTED | phase y configuración runtime existente necesaria para identificar la fase; antes de fit. |
| `PersistEpoch.on_epoch_end:97–107` put epoch | EPOCH_COMPLETED | epoch global, phase, phase_epoch y métricas ya disponibles en row; después del callback clínico, antes del checkpoint de esa época. |
| `train.py:118–123` put artifact_prepared | ARTIFACT_PREPARED | run/epoch y referencia al artefacto previsto; antes de model.save(partial). |
| `train.py:124–137` save → rename → file_identity → put artifact | ARTIFACT_CREATED | referencia, epoch, version_id, sha256 y bytes existentes; después de publicación física y evidencia legacy. |
| `train.py:138` put selection | SELECTION_COMPLETED | epoch seleccionado y criterio/threshold ya presentes en selection; después de artifact. La selección se calcula antes, pero su evidencia se persiste aquí. |
| `train.py:140–157` collect VAL → put predictions | PREDICTIONS_COMPLETED | role=val, epoch y referencia a la evidencia de muestras persistida; después de selection. No duplicar arrays en otro payload sin contrato explícito. |
| `train.py:198–213` put phase después de fit | PHASE_COMPLETED | phase, epochs efectivas y evidencia de early stopping disponible; tras todas sus épocas. |
| `train.py:217–243` checkpoint seleccionado → VAL → put calibration | CALIBRATION_COMPLETED | checkpoint_epoch, split=val y resultado calibración existente; también puede describir enabled=False sin inventar métricas. |
| Callback clínico `checkpoint_policy.py:528–545`; calibración final `threshold_calibration.py:241–271` | EVALUATION_COMPLETED | Sólo métricas realmente calculadas, con split/epoch/threshold/clase positiva; ubicación final y schema se cierran en E10.9. |
| `train.py:244–257` construye completion y llama finish | TRAINING_COMPLETED | epochs, selección/referencia, records_hash legacy y objetivo ya calculados; confirmar evento **antes** de finish. |
| Catches actuales de campaign/controlled/standalone | TRAINING_FAILED | causa sanitizada y fase conocida, sin métricas ficticias; confirmar antes de finish failed mientras el owner siga activo y no haya pending previo. |

Orden por época acreditado: epoch → artifact_prepared → save/rename → artifact →
selection → predictions. ARTIFACT_PREPARED no acredita que el fichero exista;
ARTIFACT_CREATED exige que ya se haya finalizado y calculado identidad. No se toca
almacenamiento del checkpoint. La referencia de paths Docker/Local debe definirse
en la integración antes de construir el evento, nunca transformarse en retries.

**Evaluación:** hoy no existe un único punto final completo para todas las ramas.
El callback dispone del dict clínico completo en memoria antes de proyectarlo a
logs; allí se pierden TP/TN/FP/FN, matriz y F1 para el record epoch. Si calibración
está habilitada, el resultado final sí contiene selected_metrics y
default_threshold_metrics con conteos/matriz y threshold. Si está deshabilitada,
train sólo persiste `{enabled: false, threshold: 0.5}` más muestras/epoch. Loss
proviene de fit; no se recalcula al threshold calibrado. No se inventa un resultado
completo en esa rama, no se ejecuta TEST y no se resuelve el contrato E10.9 aquí.

## 17. Orden definitivo para futura integración E10.7

1. Producir y confirmar todos los records legacy, incluyendo calibración final;
   entregar los eventos científicos previos por la misma instancia del emitter.
2. Terminar el cálculo científico y dejar de añadir evidencia legacy.
3. Leer **legacy_records**, construir completion con su records_hash y la evidencia
   histórica exacta. Exigir que no haya evento pendiente anterior.
4. Emitir TRAINING_COMPLETED y confirmar su entrega (o retry exacto) con sesión
   todavía active. El evento no altera records_hash ni cierra la sesión en DB.
5. Ejecutar el finish completed legacy con esa misma completion. Un fallo de
   entrega no permite anunciar completed como si el terminal estuviera confirmado.
6. Conservar salida/ausencia de proceso y preflight del coordinador; verificar
   con verify_session y después finish verified/liberación existentes.

Por tanto E10.7 necesita un punto **dentro** del cierre actual de train, antes de
su finish, o una adaptación de esa frontera autorizada entonces. Un wrapper que
emita sólo después de volver train es incorrecto: sesión ya completed y fencing
rechaza. Tampoco se debe usar TRAINING_COMPLETED como sustituto de completion.

Fracaso: TRAINING_FAILED se confirma antes de finish failed, si la identidad sigue
activa y no existe otro pending. Un terminal completed ya confirmado cierra el
stream; un fallo operacional posterior de finish/verificación no habilita un
segundo terminal contradictorio. E10.7 debe conservar evidencia y tratarlo por
el lifecycle operativo, sin reabrir el emitter ni relajar guards. La prueba
PostgreSQL acredita el orden positivo y rechazo de escrituras tras el cierre.

Local futuro conserva calculation-ended → exit → finish/verify/release; antes de
abandonar el proceso científico deberá confirmar su terminal y resolver su journal.
Nada de este orden se conecta al runtime Local en esta etapa.

## 18. Tests, regresión y límites

Nuevos archivos: test_run_event_emitter (20 casos), test_execution_record_readers
(17), test_event_emitter_architecture (3), test_event_emitter_records_postgres (9).
Incluyen golden literal; ocho kinds cambiados/faltantes; retry de la misma instancia
y bytes; inmutabilidad del input; pending terminal; no heartbeat; concurrencia;
import aislado sin site-packages; compatibilidad ambos reporters; readers por
familia; schema pre-E10; SQL/ID tampering; canonical corrupto; ACK perdido; cierre
real sintético y relectura de linaje. No se ejecuta fit ni TEST clínico.

Resultados finales: **461 pruebas aprobadas: 49 nuevas + 412 de regresión**.

| Grupo | Aprobadas |
|---|---:|
| Nuevas emitter / hash / guardas puras | 40 |
| Nuevas PostgreSQL E10.6 | 9 |
| E10.1–E10.5 unitarias y guardas aprobadas | 207 |
| Artefactos/verify_session/coordinación E5 | 19 |
| E10.3–E10.5 PostgreSQL | 98 |
| ExecutionRepository/controlada/Local PostgreSQL | 52 |
| Auth HTTP/config y training_summaries API | 36 |
| **Total** | **461** |

266 tests locales; 194 en el comando combinado backend; un caso unitario de
configuración `[public]` ejecutado aparte porque el filtro `not public` lo excluía
por nombre. Las exclusiones deliberadas restantes son inspección de public y TRAIN
real, más dos casos locales excluidos (llamada train con dobles y bind check
redundante). Dos avisos de deprecación existentes de TestClient/httpx/BlockingPortal.
Alembic: 29 revisiones, head único `20260922_01`; diff sin errores de whitespace.

Entorno existente, sin instalaciones: venv Python 3.12.13 para unitarios; backend
Docker para PostgreSQL y HTTP real. Código copiado exclusivamente a
`/tmp/capstone_e10_6_b690`. Fixtures crean schemas `capstone_test_e4_<uuid>`, usan
DDL/DML sintético con guards reales y los eliminan verificando ausencia. Se usa
el servicio db existente; no se cambia public ni datos operativos. Se copia sólo
la definición de audit_events, nunca sus filas. No se requiere otra base de datos.

Reproducción: `PYTHONPATH=malaria_dl_local_project:backend_api`,
`PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`,
`python -B -m pytest -p no:cacheprovider` sobre los archivos nuevos y suites E10
aprobadas. Para PG activar RUN_E10_EMITTER_POSTGRES_TESTS, RUN_E10_HTTP_POSTGRES_TESTS,
RUN_E10_POSTGRES_TESTS, RUN_E10_DOCKER_REPORTER_POSTGRES_TESTS,
RUN_STAGE5_POSTGRES_TESTS, RUN_STAGE93_CONTROLLED_POSTGRES_TESTS y
RUN_LOCAL_EXECUTION_POSTGRES_TESTS a 1; excluir
`test_public_e5_revision_readonly` y
`test_minimal_real_calculation_through_http_agent_and_subprocess`.
Regresión UI/auth: test_training_summaries_api, test_foundation_http y
test_foundation_config. No ejecutar el test histórico de summaries PostgreSQL que
depende de cantidades/UUIDs operativos; su query de calibración real se acredita
con datos temporales y el mapping/respuesta con la suite API.

## 19. Cambios no realizados

Train, firma, Docker worker, Local worker/agent, Reports/transporte/heartbeat,
verify_session, finish, contratos, reporters, ResultService y adaptador E10.3
permanecen intactos. Ninguna escritura nueva a runs.parameters,
runs.execution_parameters o runs.configuration. Ningún cambio de reglas
completed/verified ni exigencia de E10 en sesiones históricas. No DDL productivo,
migración, backfill, tabla, columna, persistencia de nuevo hash, integración
productiva, commit, despliegue ni reinicio de servicios.

Los snapshots completos antes/después de emisiones incluyen runs y sus columnas
de configuración, attempts, members y sessions. Los tests que llaman finish lo
hacen explícitamente como preparación/prueba del lifecycle existente; el emitter
y los eventos no ejecutan esas transiciones.

Archivos productivos nuevos: execution/emitter.py y
persistence/execution_record_readers.py. Productivos modificados:
execution/repository.py (lectura legacy/E10 y lookup legacy) y
backend_api/app/services/training_summaries.py (predicado de familia).
Tests modificados: test_docker_reporter_postgres, test_http_reporter_postgres y
backend_api/tests/test_training_summaries_api. Cuatro suites nuevas y este documento.

## 20. Requisitos E10.7 / E10.8

- E10.7: conectar un emitter único por nuevo run Docker; resolver contexto confiable,
  compartirlo entre callbacks y cierre, conservar evidencia legacy y orden §17.
- E10.7: decidir reconstrucción de stream activo/recovery y tratamiento del fallo
  posterior a terminal confirmado; no resetear sequence ni crear otro event_id
  para un pending. No inferir éxito de cómputo a partir de ACK perdido.
- E10.7: mantener verificación/owner/gate y demostrar que las fases y artefactos
  conservan resultados y orden. No hacer depender runs históricos de un terminal E10.
- E10.8: journal durable Local, atomicidad del estado del emitter, reinicio y
  reconciliación; integración de worker/Reports separada de heartbeat.
- E10.9: contrato final de evaluación y consolidación científica, incluyendo el
  gap de matriz cuando no hay calibración. No inventar métricas ahora.

El blocker del **hash** queda resuelto; la integración productiva y recuperación
durable siguen pendientes. E10.6 queda lista para revisión humana y se detiene aquí.
