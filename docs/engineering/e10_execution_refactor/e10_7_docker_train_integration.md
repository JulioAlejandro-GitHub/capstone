# E10.7 — Integración Docker TRAIN

## 1. Objetivo y referencias

Integrar el worker Docker con el stream E10 sin sustituir evidencia ni política
científica legacy. Base: `1c2f07728c4db18e25730707d1fbed5112906219`, árbol inicialmente
limpio. Se leyeron completos [baseline](baseline.md), [E10.1](e10_1_contracts.md),
[E10.2](e10_2_result_service.md), [E10.3](e10_3_postgres_result_repository.md),
[E10.4](e10_4_docker_reporter.md), [E10.5](e10_5_http_reporter.md) y
[E10.6](e10_6_event_emitter_records_hash.md), y se contrastaron con las fuentes
TRAIN/worker/campaign/controlled/repository/artifacts, emitter/composition/reporters,
modelos/configuración/registry, adaptador PostgreSQL, readers y tests relacionados.

Rutas abreviadas: `S` = `malaria_dl_local_project/src/malaria_dl`,
`T` = `malaria_dl_local_project/tests`.

## 2. Estado previo y alcance

Docker y Local invocaban el mismo `train(repository, session, descriptor)` sin E10.
E10.6 ya separaba `records()` legacy de `result_events()` y resolvía records_hash.
El emitter aprobado conserva pending sólo en memoria. El worker de campaña recibe
run/owner por CLI, pero obtiene configuración, dataset, intento y linaje desde DB;
compara snapshots congelados y revisiones técnicas antes de entrenar.

Se integra `execution.worker` compartido por campaña secuencial y ejecución
controlada. El CLI individual `train._standalone` sigue legacy: no usa este worker
ni tiene linaje de campaña. No se fabrica linaje ni se amplía su composición en esta
etapa. Local permanece legacy; su integración corresponde a E10.8.

## 3. Firma transitoria de TRAIN

Anterior: `train(repository, session, descriptor)`.

Actual:

```python
train(repository, session, descriptor, *, event_emitter: RunEventEmitter | None = None)
```

El argumento keyword-only es explícito, tipado y opcional; no hay globals/singleton.
Sin emitter se conservan put/records/finish y la evidencia previa. Con emitter,
la closure `put` normaliza una vez, persiste legacy y entrega el evento derivado.
No cambian modelo, fit, callbacks científicos, loss, monitor, selección, early
stopping, recopilación VAL ni guard de TEST. El retorno sigue siendo None.

```text
ESTADO TRANSITORIO:
train()
   +--> repository.put() legacy
   +--> RunEventEmitter --> DockerRunReporter

ESTADO FINAL FUTURO:
train()
   --> RunReporter / scientific contract
       sin acceso directo a repository
```

La dependencia legacy de esta firma debe eliminarse en E10.11.

## 4. Composición Docker

`worker.main`: attach_worker existente → sesión autorizada → guard de esquema/stream
→ child_started existente → linaje/identidad congelada/effective_row/preflight
existentes → ExecutionContext → build_docker_run_reporter → RunEventEmitter →
run_scientific_train → train.

La factory E10.4 compone ResultService y PostgresResultRepository sin cambiar sus
contratos. Recibe el token global de `global_gate.token()` después de attach_worker;
no lo confunde con el owner interno. Cada report mantiene su transacción raíz y
ACK posterior al commit. TRAIN no importa reporters concretos, ResultService,
PostgresResultRepository, FastAPI ni composición.

## 5. Context autoritativo y doble defensa

| Campo | Fuente |
|---|---|
| run_id | train_execution_sessions.run_id |
| owner | train_execution_sessions.owner, previamente contrastado con CLI |
| attempt_id | sesión; contrastado con attempt.id y attempt.training_run_id |
| campaign_id | campaña leída por JOIN del intento reservado |
| member_id | attempt.member_id → miembro de esa campaña |
| dataset_version_id | snapshot de sesión; comparado con campaña/dataset snapshot |
| model_id | configuration.model_id de sesión; identidad del registry, no UUID models |
| adapter_version | configuration.adapter_version de sesión, validada por preflight |
| configuration_hash | miembro reservado; no recalculado desde config con seed |
| contract_hash | campaña congelada |
| execution_mode | DOCKER, definido por este entrypoint |

`docker_context` exige sesión/intento/miembro activos, campaña active o paused,
y coherencia de las identidades. El código existente compara configuración esperada,
dataset y entorno efectivo. PostgresResultRepository vuelve a verificar owner,
estados, token y linaje bajo locks en cada entrega, incluidos duplicados. Las
pruebas alteran owner del contexto y nueve componentes de linaje/estado.

## 6. Emitter único y precondiciones

Se construye un único reporter y un único emitter por invocación autorizada del
worker. Todas las fases, callbacks y terminales comparten esa instancia. No hay
retry automático ni journal. El heartbeat operativo no participa.

`ExecutionRepository.preflight_result_events(run_id)` se llama sólo desde Docker,
antes de importar/ejecutar TRAIN y antes de child_started. Sigue el patrón de
capabilities instaladas de ControlledRepository/GlobalGate: inspecciona columnas
UUID/NUMERIC, CHECK validado, índices únicos válidos y trigger E10 habilitado de
`20260922_01_result_events`. Falta de esquema produce
`E10_RESULT_EVENTS_MIGRATION_REQUIRED_20260922_01`. No ejecuta/stampa Alembic ni
requiere que la revisión sea exactamente el head para siempre. La instalación
operativa sigue el procedimiento de migraciones existente y no se realizó aquí.

Si hay cualquier fila E10 del run, falla con
`E10_ACTIVE_STREAM_RECOVERY_UNSUPPORTED`; no reconstruye ni reinicia sequence.
El guard es una lectura previa, no un nuevo lock. La unicidad del proceso sigue
protegida por attach_worker/child_started y gate existentes; el adapter conserva
fencing y rechazo de colisiones como segunda defensa. Un run sin eventos pero con
child_pid registrado tampoco puede relanzarse pasando por child_started.

## 7. Mapping E10.6 implementado

Payload común no terminal: `{legacy_record: {kind, phase, record_key}, result: ...}`.
Run/attempt están en el envelope; phase/key dan la identidad de la evidencia.

| Producer legacy | Evento | result |
|---|---|---|
| runtime | PHASE_STARTED | phase, callbacks; resto del runtime referenciado en legacy |
| epoch | EPOCH_COMPLETED | row completo ya producido, incluyendo epochs y métricas |
| artifact_prepared | ARTIFACT_PREPARED | path previsto, epoch, run_id |
| artifact | ARTIFACT_CREATED | payload actual con path, epoch, phase, version_id, SHA256, bytes |
| selection | SELECTION_COMPLETED | selección actual íntegra |
| predictions | PREDICTIONS_COMPLETED | role=val y epoch; muestras por referencia legacy |
| phase | PHASE_COMPLETED | epochs efectivas y early_stopping existentes |
| calibration habilitada | CALIBRATION_COMPLETED | split=val, checkpoint_epoch, resultado existente |
| calibration deshabilitada | Sin evento | se conserva el marcador legacy enabled=false |
| completion calculada | TRAINING_COMPLETED | completion actual limpia, incluido records_hash legacy |
| Excepción de TRAIN | TRAINING_FAILED condicional | causa fija sanitizada TRAIN_RUNTIME_FAILED |

La restricción expresa E10.7 prevalece sobre la posibilidad mencionada en E10.6
para emitir calibración deshabilitada. No se introduce otro mapping ni se recalculan
métricas. No se duplican arrays de predicciones/calibración en E10. Las referencias
Docker a archivos mantienen el path actual; no se transforman durante retries.
EVALUATION_COMPLETED permanece pendiente de E10.9; no se inventan conteos/matriz.

## 8. Orden de persistencia y checkpoints

Cada put confirma legacy antes de intentar su E10. Si legacy falla no se emite su
evento de éxito; puede intentarse TRAINING_FAILED. Si E10 falla no se continúa.

Orden real por época: epoch → artifact_prepared → save parcial → rename → identidad
del archivo → artifact → selection → predictions. Cada evidencia mapeada va seguida
de su E10 antes del siguiente paso. **ARTIFACT_PREPARED no afirma que el archivo ya
esté cerrado ni exista**: su punto aprobado está antes de model.save. La escritura
física y las comprobaciones de exclusividad permanecen intactas.

## 9. Secuencia acreditada

Doble determinístico: dos épocas por fase. Cada fase produce:

```text
PHASE_STARTED
EPOCH_COMPLETED, ARTIFACT_PREPARED, ARTIFACT_CREATED,
SELECTION_COMPLETED, PREDICTIONS_COMPLETED
EPOCH_COMPLETED, ARTIFACT_PREPARED, ARTIFACT_CREATED,
SELECTION_COMPLETED, PREDICTIONS_COMPLETED
PHASE_COMPLETED
```

Una fase sin calibración: 12 eventos de fase + terminal = **1…13**.
El run de integración PostgreSQL reservado (custom_cnn, dos épocas sintéticas,
calibración habilitada) acredita **1…14**: PHASE_COMPLETED=12,
CALIBRATION_COMPLETED=13 y TRAINING_COMPLETED=14.
Dos fases sin calibración: **1…25**; con calibración: **1…26**.
Las pruebas PostgreSQL obtienen el stream durable, comprueban la lista exacta
según las fases de la configuración reservada y sequence numérico contiguo.
También reenvían cada evento exacto mientras la sesión está activa: una fila por
sequence, sin duplicados. No se usa orden lexicográfico ni contador de legacy.

## 10. Terminal de éxito y completion

Todo legacy + E10 previo → records() legacy → completion/hash actual →
TRAINING_COMPLETED confirmado → emitter.closed → finish completed existente →
salida del hijo → preflight/verify_session del coordinador → finish verified.

Emit rechaza un pending previo. Ningún evento cambia estados de sesión/run/intento,
ni escribe runs.parameters. El terminal no sustituye completion ni verification.
No cambia el contrato de aceptación de runs históricos sin E10.

## 11. Terminal de fallo

`worker.run_scientific_train` captura el fallo de TRAIN y sólo intenta FAILED si
no hay pending y el emitter sigue abierto. La entrega aplica autorización actual
transaccional: un owner ya revocado no puede insertar. No se persisten mensajes
arbitrarios de excepciones ni fase inventada. Si la entrega de FAILED falla, se
agrega una nota sanitizada y se relanza **la excepción original**.

El main conserva sus categorías de exit existentes; campaign/controlled siguen
siendo responsables del finish failed/interrupted legacy. El helper no cambia
esa política ni intenta completar una ejecución fallida.

## 12. Pending y caída del proceso

La política elegida es fallar inmediatamente. Un error de entrega, incluso ACK
perdido después de commit, deja el mismo evento pending en memoria. No se intenta
FAILED sobre ese pending ni se descarta/reemplaza. El run no completa normalmente.
Un stream no terminal en un run fallido es aceptable en E10.7. Al morir el proceso
se pierde pending; no se promete recuperación. Retry exacto sigue disponible en
el emitter aprobado y se acredita con pruebas E10.6/servicio/adaptador.

## 13. Fallo de finish después del terminal

Se acredita terminal durable confirmado y emitter cerrado, seguido de finish
completed rechazado: sesión aún active hasta el manejo legacy del coordinador,
y eventos conservados. El coordinador puede marcar failed sin borrar el terminal.
No se emite un FAILED contradictorio ni se reabre el emitter.

TRAINING_COMPLETED significa **el cálculo científico terminó y su stream E10 cerró**;
no garantiza que la transacción posterior de finish completed haya terminado.
Completion/Verification futuras deberán reconciliar explícitamente esta evidencia.

## 14. Fallo de verify después del terminal

Se acredita sesión completed con terminal conservado y fallo de loader en
verify_session: no se ejecuta finish verified. El emitter queda cerrado. No se
intenta la transición inválida completed→failed. Las rutas operativas de pausa,
reconcile y diagnóstico existentes permanecen intactas.

## 15. records_hash y equivalencia

Sin cambios en canonical/digest, readers E10.6 ni verify_session. Cada evento
insertado y duplicado en PG deja exactamente el mismo digest de sus legacy records;
el terminal contiene el hash que persiste completion y acepta verify_session.

`T/fixtures/e10_6_train.py` congela literalmente el código previo hasta train,
sin CLI standalone. Un SHA256 fijo protege el fixture. La prueba ejecuta ese
baseline y el TRAIN nuevo, con/sin emitter, mismos datos/config/UUID de artefacto,
paths temporales y dobles determinísticos. Compara records completos (incluidas
métricas), completion/hash y bytes de todos los checkpoints. No afirma igualdad
bit a bit entre entrenamientos TensorFlow independientes.

## 16. Resume y recovery

`--resume` llama reconcile: verified se revalida; completed se verifica; active
requiere prueba de ausencia y pasa a interrupted. Claim crea UUID nuevos de
attempt y run; no entrena de nuevo la misma sesión. La prueba integra el camino
real execute_campaign(resume=True), con ausencia simulada y una sola nueva reserva:
stream anterior intacto, run/intento distintos, stream nuevo empieza en 1 y verifica.
Se pausa expresamente la campaña sintética tras ese intento para no recorrer la
matriz completa. El guard impide iniciar otro emitter sobre un stream existente.
No se reconstruye pending desde MAX(sequence), timestamps o logs.

## 17. Ejecución controlada

ControlledRepository.reserve crea nuevo intento/run para una nueva request elegible;
la request repetida conserva identidad y execute_one no relanza. effective_row
valida el binding de revisión técnica y conserva identidad científica. Se usa
exactamente worker.main, sin segundo mapping/factory.

Prueba real PG: reserva controlada con revisión → mismo worker → TRAIN → terminal
→ completed → verify → verified; campaña permanece paused. Repetición de request y
recover del run verificado no lanzan ni agregan eventos. La regresión existente
acredita recover active→interrupted sólo tras probar ausencia, nunca reentrenar.

## 18. Pruebas, resultados y reproducción

**LISTA PARA REVISIÓN: 531 pruebas aprobadas, 49 nuevas y 482 de regresión.**

| Grupo | Aprobadas |
|---|---:|
| Nuevas TRAIN/context/fallos/equivalencia | 35 |
| Nuevas guardas de arquitectura | 3 |
| Nuevas Docker TRAIN PostgreSQL | 11 |
| Regresión local E10.1–E10.6, artifacts/coordinación/legacy TRAIN | 268 |
| Regresión PostgreSQL/HTTP/Local/control/GlobalGate/API/auth | 214 |
| **Total único** | **531** |

Comando combinado local: 306 passed. Nueva integración PG: 11 passed.
Comando combinado backend de regresión: 214 passed, 2 deselected (las exclusiones
explícitas indicadas abajo). Avisos existentes de deprecación protobuf y
Starlette/httpx/anyio; ningún fallo final. El primer borrador del fixture unitario
omitía seed: se corrigió el fixture, sin cambiar semántica productiva.
Alembic: 29 revisiones lineales, head único 20260922_01. Ninguna revisión nueva.
`git diff --check` limpio. Las funciones legacy finish/_create_run/claim/standalone
permanecen iguales por comparación AST; no se crean commits.

Suites nuevas: test_docker_train_integration, test_docker_train_architecture,
test_docker_train_postgres; helpers docker_train_fixture y baseline congelado.
Las guardas E10.4/E10.6 se amplían sólo para permitir los imports ahora autorizados
en worker/train. Se mantienen dominio/reporter puros, Local sin emitter/reporters,
TRAIN sin implementación de transporte y firma Local de tres argumentos con Reports.

Las pruebas científicas usan el control flow real de TRAIN y dobles determinísticos
de modelo/fit/loaders/callback clínico, manteniendo selección y calibración reales
sobre dos muestras sintéticas VAL. No se usa el dataset oficial ni TEST clínico,
no se entrena una campaña pesada y no se acredita rendimiento científico.

La integración invoca worker.main en proceso de test dentro del backend Docker;
attach_worker y el preflight de dataset/entorno se sustituyen sólo allí para no
registrar un proceso ficticio ni usar datos operativos. Session/context/lineage,
child_started, composición, reporter/service/adapter, DDL/guards/commit y cierre/
verificación son reales. La suite GlobalGate separada conserva pruebas Linux de
locks, procesos, handshake, OOM y barreras. No se presenta el test en proceso como
un nuevo ensayo de subprocess TensorFlow end-to-end.

Comandos locales: PYTHONPATH=malaria_dl_local_project,
PYTHONDONTWRITEBYTECODE=1, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1,
MPLCONFIGDIR=/tmp/e10_7_mpl; venv existente, python -B -m pytest -p no:cacheprovider.

PostgreSQL/HTTP se ejecutan desde copia de código en `/tmp/capstone_e10_7_a94a`
del backend existente, con PYTHONPATH a M y backend_api. Opt-in nuevo:
RUN_E10_TRAIN_POSTGRES_TESTS=1. Regresión: RUN_E10_EMITTER_POSTGRES_TESTS,
RUN_E10_HTTP_POSTGRES_TESTS, RUN_E10_POSTGRES_TESTS,
RUN_E10_DOCKER_REPORTER_POSTGRES_TESTS, RUN_STAGE5_POSTGRES_TESTS,
RUN_STAGE93_CONTROLLED_POSTGRES_TESTS, RUN_LOCAL_EXECUTION_POSTGRES_TESTS y
RUN_STAGE93_GLOBAL_POSTGRES_TESTS=1. Excluir explícitamente
`test_public_e5_revision_readonly` y el fit HTTP Local
`test_minimal_real_calculation_through_http_agent_and_subprocess`.

Fixtures aprobadas crean schemas `capstone_test_e4_<uuid>` y verifican su eliminación;
sólo clonan definición de audit_events, no filas operativas. No se modifica public,
no se aplica upgrade operativo ni se crea otra base. No hay instalaciones,
despliegue, reinicio de servicios ni commit.

## 19. Cambios deliberadamente no realizados

Local worker/agent/Reports/transporte/heartbeat, backend/frontend, training summaries,
GlobalGate/locks/subreaper/process evidence/OOM, campaign/controlled, models,
configuración, callbacks científicos, artifacts.verify_session, finish, contratos,
ResultService y PostgresResultRepository no cambian. Tampoco runs.parameters,
consolidación, completion policy, release ni TEST. No hay migración nueva.
Sólo cambian train, worker, un preflight adicional en repository, dos docstrings y
guardas arquitectónicas; se agregan pruebas y este documento.

## 20. Deuda transitoria E10.11

TRAIN aún conoce put/records/finish, sesión dict, descriptor, paths/checkpoint Keras
y hash del ledger. Hay dos escrituras secuenciales por evidencia, no atomicidad
conjunta legacy/E10. La transición no convierte E10 en fuente científica de UI.
E10.11 debe eliminar ese acceso al repositorio y la firma opcional, conservando
las identidades y fronteras de cierre acordadas. El CLI standalone requiere una
composición explícita propia si se amplía la cobertura de eventos a ese entrypoint.

## 21. Requisitos concretos E10.8 y cierre

1. Integrar el worker Local con HttpRunReporter de forma explícita sin alterar
   heartbeat ni confundir owner remoto/interno.
2. Diseñar journal durable con evento completo y transición atómica
   pending/next_sequence/closed antes de IO y después de ACK; resolver errores del
   propio journal, crash y pérdida de ACK sin reconstruir eventos distintos.
3. Mantener un único writer/emitter por run y fencing backend actual.
4. Definir referencias de artefactos y evidencia legacy usando roots compartidos,
   sin mutarlas en reintentos ni duplicar arrays innecesarios.
5. Confirmar el terminal antes de calculation-ended, conservando exit proof,
   finish/verify/release Local y su frontera transaccional.
6. Probar reconexión/restart y terminal confirmado con fallos posteriores, sin
   asumir que un ACK E10 libera el proceso/job.

EVALUATION_COMPLETED, matriz sin calibración y consolidación quedan para E10.9.
E10.7 termina para revisión humana; no implementa Local ni journal durable.
