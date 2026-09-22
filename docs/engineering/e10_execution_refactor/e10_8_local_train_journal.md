# E10.8 — Local TRAIN y journal durable

## 1. Objetivo

Integrar E10 en el worker Python nativo con el mismo TRAIN de Docker, conservando
Reports y la política legacy. Añadir recuperación durable de transporte mediante
SQLite stdlib, sin PostgreSQL en el cliente ni nueva migración. No se implementa
E10.9. Rutas abreviadas: S=`malaria_dl_local_project/src/malaria_dl`,
T=`malaria_dl_local_project/tests`.

## 2. Ciclo Local previo: auditoría anterior a la implementación

Referencias E10.0–E10.7 leídas durante esta secuencia de trabajo y contrastadas con
los contratos, emitter, TRAIN, reporters y módulos Local actuales. El árbol incluye
la entrega E10.7 todavía sin commit: se preserva como base de esta etapa.

Ciclo previo: `agent.main(start)` guarda request antes de claim; `LocalBackend.claim`
reserva job held, intento/run y sesión interna; devuelve job público. El agente
crea `Popen([sys.executable, '-B', '-m', 'src.malaria_dl.local_execution.worker'])`.
Después de heartbeat aceptado entrega por stdin job/roots/url. El worker verifica
manifiesto, traduce roots y llama el TRAIN compartido con Reports. Reports.finish
sólo llama calculation-ended; backend guarda completion y pasa a calculation_reported,
sin cerrar sesión ni liberar gate. El agente observa salida real, guarda exit proof
y llama exit. Backend exige identidad/ausencia; en la misma transacción hace
finish completed, verify_session, finish verified, job released y libera gate.
Con exit no exitoso hace failed/pausa. Error de verify revierte esa transacción.

| Identidad/operación | Fuente o función |
|---|---|
| Creador del worker | agent.main; intérprete nativo sys.executable |
| Payload | stdin: job, roots, url |
| run_id | job.run_id y job.session.run_id |
| attempt_id | job.session.attempt_id |
| job_id / agent_id | job.job_id / job.agent_id |
| dataset_version_id | job.session.dataset.dataset_version_id |
| Owner remoto | job.owner; Reports lo usa, nunca es owner interno E10 |
| Context E10 interno | LocalExecutionContextResolver desde PostgreSQL |
| finish del científico | train → Reports.finish → calculation-ended |
| exit | agent tras child.wait y ProcessTracker.exit_proof |
| verify/release | LocalBackend.operation('exit'), transacción backend |

`calculation_reported` mantiene sesión active y autorización E10.5: resolver admite
held/calculation_reported y el global guard acepta un job retenido. Released/failed
rechazan eventos. Heartbeat sigue a 15 s y reporta incertidumbre después de 60 s;
no libera reserva por tiempo.

Diseño: journal SQLite operacional junto al estado del agente, exclusivo por
job/run, con identidad job/agent/run/attempt, schema versionado y estado atómico.
Recuperación de transporte no reinicia fit. Un arranque científico sólo puede usar
un journal recién creado y un estado remoto vacío. Un journal preexistente recupera
pending, pero rechaza reentrenar; un closed permanece cerrado. Consulta remota
mínima autenticada para detectar ausencia/divergencia. El agente conserva exit proof
y retiene la reserva si queda pending, para reconcile explícito antes de exit.

## 3. Ciclo posterior

```text
Mac
 └─ Local worker (sys.executable del agente)
      └─ train() compartido
          ├─ Reports legacy
          │    └─ HTTP legacy
          └─ RunEventEmitter
               ├─ EventJournal → SQLite durable local
               └─ HttpRunReporter
                    └─ HTTP autenticado
                         └─ ResultService
                              └─ PostgreSQL
```

El agente añade al estado y stdin la ubicación del journal. No se cambia el comando
Popen ni el handshake del primer heartbeat. Worker verifica samples/resuelve roots,
consulta estado remoto, abre journal, compone reporter/emitter y llama train con
`event_emitter=...`. No hay train_local/train_docker ni bifurcación científica.

## 4. Composición

`local_execution.event_runtime.compose` usa Api y `build_http_run_reporter` E10.5,
RemoteExecutionIdentity, SQLiteEventJournal y el mismo RunEventEmitter. No construye
ResultService/repositorios DB. HttpRunReporter y su endpoint de escritura aprobado
permanecen intactos. `train.py`, Docker worker y composición Docker no cambian respecto
a E10.7. El único cambio compartido funcional es el soporte opcional del journal y
preparación de referencias en el emitter; Docker mantiene los defaults en memoria.

## 5. Identidad

El journal liga job_id, agent_id, run_id y attempt_id (nullable). El archivo lleva
job/run UUID en el nombre; el body valida los cuatro campos. `stream_identity`
contrasta job.run_id con session.run_id. RunEvent usa sólo run/attempt; el DTO HTTP
sigue siendo job_id/agent_id/event. El Mac no declara owner interno ni contexto.
El resolver backend E10.5 conserva íntegros su código y revalidación transaccional.

## 6. EventJournal port

`execution/journal.py`: EventJournal ABC con `load(run_id, attempt_id) -> EventState`
y `transition(expected, updated) -> None`. Esta segunda operación compara y reemplaza
el estado completo atómicamente. El port no conoce SQLite/filesystem/HTTP/SQL.
EventState es frozen y valida sequence positiva estricta, pending ligado al run/
intento/sequence, exclusión de heartbeat y coherencia closed/terminal_type.

Emitter mantiene lock de entrega y estado en memoria. Con journal, restaura su estado
validado. Sin journal comienza en 1 y conserva comportamiento Docker aprobado.

## 7. Implementación durable

`local_execution/event_journal.py` usa sqlite3, transacciones BEGIN IMMEDIATE,
COMMIT y rollback ante excepciones; synchronous=FULL, fullfsync=ON y rollback journal
DELETE. Un flock exclusivo no bloqueante, retenido durante toda la apertura, impide
dos procesos usando el mismo journal. No es un lock distribuido entre Macs: el job,
heartbeat de identidad y fencing central siguen gobernando autorización.

El archivo inicial se crea con O_EXCL, no se trunca un existente. Se confirma schema
+ estado en una transacción y se hace fsync del directorio. Una creación interrumpida
que deje un archivo vacío falla cerrada; no se interpreta como journal nuevo.
No hay nuevas dependencias ni modificación de requirements/VENV.

## 8. Ubicación y storage

`journal_path(agent_state, job)` devuelve:

```text
<directorio de --state>/e10_journals/<job_uuid>_<run_uuid>.sqlite3
```

La raíz proviene del estado Local configurado, nunca de `/Users/...`, dataset o
PostgreSQL. Se crea directorio con modo 0700 y archivos/lock 0600; se rechazan symlinks
directos. No se borran al cerrar ni al completar. El lock vacío permanece; el lock
OS se libera al cerrar o morir el proceso.

El journal contiene identidad operacional y estado/evento, no JWT/passwords, imágenes
ni bytes de checkpoints. Las referencias a archivos se preparan **antes de construir
RunEvent** mediante un callback de composición: path Mac → `{root_id, relative_path}`.
El emitter no conoce roots ni muta eventos en retry. No cambia escritura de checkpoints
ni Reports/storage; backend sigue verificando los archivos por su raíz compartida.
La ruta absoluta del journal vive sólo en el estado operacional del agente/stdin.

## 9. Schema y versión

SQLite `PRAGMA user_version=1`. Una tabla `stream(id=1, body TEXT, sha256 TEXT)`.
Body JSON canónico local:

```json
{"version":1,"identity":{"job_id":"UUID","agent_id":"UUID","run_id":"UUID","attempt_id":"UUID o null"},"state":{"next_sequence":1,"pending":null,"closed":false,"terminal_type":null}}
```

pending es el envelope completo `RunEvent.to_dict()`, sin proyección parcial.
SHA256 detecta corrupción accidental; no pretende autenticar archivos manipulados
por un actor con acceso al usuario. Se validan quick_check, versión, objetos/columnas,
única fila, checksum, claves exactas, identidad y semántica. No migración automática
de formatos desconocidos. Sequence se codifica como entero JSON en TEXT, sin limitarla
silenciosamente al rango INTEGER de SQLite.

## 10. Durable-before-send

emit valida/prepara payload, construye RunEvent una sola vez, conserva pending en
memoria, confirma pending en journal y sólo entonces llama reporter.report. Al retorno
normal, una transición confirma conjuntamente pending=None, next_sequence+1 y closed/
terminal_type cuando corresponda. El estado de memoria avanza después del commit local.
Las pruebas observan pending confirmado desde otra conexión antes de report.

Si save falla no hay HTTP. Si confirm falla, pending de memoria no se pierde y el
emitter queda invalidado para más entregas hasta reapertura. Esto evita sobreescribir
un commit local incierto. Reabrir determina si quedó pending (retry exacto) o si
confirmación ya había quedado durable (sequence avanzado), sin adivinar.

## 11. Pending

Error HTTP detiene TRAIN y deja pending durable. No hay retry automático nuevo, loop,
backoff ni descarte; el transporte E10 sigue haciendo un intento. Legacy conserva sus
tres intentos. No se crea FAILED sobre otro pending. Nuevos emits siguen bloqueados.
Un stream no terminal puede pertenecer a un intento fallido; no se fabrica su cierre.

## 12. ACK perdido

PostgreSQL puede confirmar antes de que el worker reciba el ACK. El journal conserva
el mismo ID, sequence, tiempo, schema y payload. Al reabrir, retry usa ese evento
exacto: backend devuelve DUPLICATE_ACCEPTED y el journal confirma una vez. El mismo
caso se prueba por HTTP real con proceso que muere tras consumir la respuesta de
aceptación y antes de entregarla a HttpRunReporter.

## 13. Crash points

Pruebas con `os._exit` en subprocesses reales, sin finally/close voluntario:

| Punto | Estado remoto tras crash | Reapertura |
|---|---|---|
| A: pending durable antes de HTTP | Sin evento | Reenvía pending exacto y acepta |
| B: commit PG, ACK perdido | Un evento | Retry duplicado, confirma local |
| C: HTTP success antes de confirm local | Un evento | Retry duplicado, confirma local |
| D: confirm local antes del siguiente evento | Un evento | pending=None, next_sequence=2 |

Después de recovery se entrega sequence=2 y hay dos filas durables, sin duplicados.
También se prueban rollback SQLite, confirm fallido antes/después de commit y writer
concurrente rechazado desde otro proceso.

## 14. Restart y scientific resume

Un journal existente restaura next/pending/closed; no inicializa sequence=1 otra vez.
Si el worker recibe el mismo run, recupera pending primero cuando está autorizado,
pero después lanza `LOCAL_SCIENTIFIC_RESUME_UNSUPPORTED`. **Nunca vuelve a ejecutar
fit sobre ese run**, incluso si next=1 y no hay pending: el journal podría haberse
creado antes de una caída en una frontera científica no recuperable.

Transport recovery no recupera pesos/optimizer/callbacks en mitad del entrenamiento.
El siguiente intento científico sigue requiriendo las reglas vigentes y un run nuevo.
Closed se conserva y rechaza nuevos eventos. No se borra journal ni estado automáticamente.

## 15. Journal ausente e historia remota

Antes de crear un journal, compose consulta `POST /execution/local/event-state`,
operación **de sólo lectura**, autenticada con el mismo SYSTEM_ADMIN/local_jwt/opt-in
que events. Recibe exclusivamente job_id y agent_id; devuelve run/attempt, último
sequence/event_id, terminal_type y legacy_exists. No owner ni snapshots internos.

Backend resuelve identidad en transacción REPEATABLE READ + READ ONLY, verifica que
las columnas E10 existan, valida el stream con el reader E10.6 y continuidad/terminal.
No reserva slots ni cambia tablas. Journal ausente + cualquier E10 o evidencia legacy
rechaza `LOCAL_E10_JOURNAL_REQUIRED_FOR_RECOVERY`. No hace MAX+1 como recuperación.
Con journal abierto se exige watermark compatible con el confirmado local o con su
pending exacto ya aceptado; divergencia falla cerrada. La comprobación es observación,
no sustituye el fencing transaccional del append.

## 16. Corrupción y fallos

Se prueban SQLite inválido/vacío, versión desconocida, tabla extra, checksum alterado,
estado inválido, pending no deserializable y cada componente de identidad cambiado.
Todos fallan cerrados conservando el archivo. Se rechazan objetos de schema extra.
No hay delete/recreate, fallback JSON, limpieza automática ni exposición de mensajes
SQLite con paths/datos. Error local ambiguo exige reapertura; recuperación destructiva
queda fuera de esta etapa.

## 17. Terminales

TRAINING_COMPLETED confirma pending durable, HTTP y closed durable antes de volver
a train y ejecutar Reports.finish. TRAINING_FAILED usa causa sanitizada idéntica a
Docker y sólo se intenta sin pending y con emitter abierto; backend aplica fencing.
Fallos secundarios no ocultan la excepción original. Un terminal confirmado no se
reabre si luego falla finalización o verificación.

## 18. calculation_reported

Orden probado: terminal HTTP/SQLite confirmado mientras job held/sesión active →
Reports.finish → calculation-ended → job calculation_reported. La regresión E10.5
acredita que calculation_reported todavía permite append con fencing válido; no se
relaja esa autorización. En éxito normal ya no se necesita otro evento.
Fallo de calculation-ended deja closed/terminal durable y nunca falso verified.

## 19. Exit proof y pending retenido

Tras child.wait, el agente guarda la prueba real de salida antes de revisar pending.
Si existe pending (o no puede leer journal corrupto), no llama exit ni libera la reserva.
Retorna fallo `LOCAL_E10_PENDING_RECONCILE_REQUIRED` para pending legible. Heartbeat ya
terminó porque el worker murió; la reserva no expira por tiempo.

`agent reconcile`, con exit_proof guardado, ejecuta sólo recover_pending y después
reenvía exit con la misma prueba. Si persiste fallo de red/journal, exit no se envía.
El exit_code original no se convierte en éxito porque un evento haya sido recuperado.
Los estados previos sin campo event_journal conservan el reconcile legacy.

## 20. Verification/release

El backend no cambia su operación exit. Exit 0 + completion hace completed/verify/
verified/released en su transacción; failure revierte. Se probó loader rechazado:
terminal y journal closed persisten, sesión vuelve a active y job sigue
calculation_reported; reconcile posterior verifica/libera sin repetir ciencia.
También se probó finalización legacy rechazada: intento/job failed con terminal
TRAINING_COMPLETED preservado. Su semántica sigue siendo fin del cálculo/stream,
no garantía de commit de finalización ni liberación.

## 21. records_hash y runs.parameters

No se cambia la separación de familias E10.6. Completion y verify_session leen
legacy; los tests nativos comparan digest de records con terminal, completion y
verification. La regresión HTTP/PG conserva pruebas de inserciones/retries sin cambiar
hash. No se escribe runs.parameters; se comprueba `{}` antes/después en fixtures.
No se cambia completion contract ni se exige matriz/EVALUATION_COMPLETED para verificar.

## 22. Paridad Docker/Local

Dos ejecuciones determinísticas del mismo train con DockerRunReporter y
HttpRunReporter + SQLite, con calibración activada/desactivada: mismos tipos,
mismo número, orden y sequences 1…26 / 1…25 para dos fases de dos épocas. Se fijó
sólo el reloj operativo de calibración en el test para comparar evidencia; producción
no cambia. Records científicos coinciden salvo identidad física de artefactos;
verify_session acepta ambos. Los IDs/timestamps propios de eventos no se equiparan.

Los runs nativos de una época producen 1…9: phase started, epoch, artifact prepared,
artifact created, selection, predictions, phase completed, calibration, terminal.
EVALUATION_COMPLETED sigue ausente en ambos modos.

## 23. Ejecución nativa Mac

Se ejecutaron agente y worker reales con el venv Python del Mac, subprocess real,
ProcessTracker y prueba de salida con platform=Darwin, PID distinto del proceso pytest,
ausencia acreditada y checkpoints Keras cargables. Dataset sintético: dos imágenes
TRAIN y dos VAL de 16x16, configuración de entrada 32x32, batch 2, una época; sin TEST.
No se construye imagen Docker ni se envía fit al backend.

El servidor FastAPI de esta prueba corre nativamente como fixture para acceder a las
mismas raíces temporales; usa JWT/usuarios sintéticos reales y PostgreSQL Docker
existente por su puerto publicado. Sólo se reemplazan preflight de dataset/entorno
operativo y el scan /proc de claim (Linux-only). Auth/context/eventos/guards/commit,
Reports, journal, fit, checkpoints, exit y verificación son reales. La aplicación
productiva backend continúa en sus rutas Docker existentes; la fixture nativa no
se presenta como un despliegue nuevo. Regresión Linux cubre GlobalGate/procesos.

## 24. Heartbeat y controlled

Thread 15 s, expiry/uncertain 60 s, process identity y política de no liberación
permanecen intactos. No usa journal, RunEvent ni sequence. Las guardas inspeccionan
su AST. Local controlled y sequential siguen usando el mismo worker; no se crea
una implementación separada. Los ensayos nativos usan controlled y verifican que
no encadena; la regresión existente cubre sequential y exclusividad Docker/Local.

## 25. Pruebas y reproducción

**LISTA PARA REVISIÓN: 572 pruebas únicas aprobadas: 40 nuevas y 532 de regresión.**

| Grupo | Aprobadas |
|---|---:|
| Journal SQLite/procesos/fallos nuevos | 20 |
| Runtime/recovery/referencias nuevos | 7 |
| Guardas nuevas | 2 |
| Paridad nueva | 2 |
| HTTP/PG crash y consulta remota nuevos | 5 |
| Agente/worker nativos nuevos (éxito, completion, verify, pending) | 4 |
| Regresión E10.1–E10.7 y lifecycle previa | 531 |
| Fit HTTP Local preexistente, actualizado y ejecutado en Mac | 1 |
| **Total** | **572** |

Comandos finales: 337 passed local; 230 passed/6 deselected backend (4 escenarios
nativos + fit Local + inspección public excluidos de ese comando); 5 passed/25
deselected en selección nativa. Las 25 restantes se cubren en los otros comandos,
salvo la inspección public deliberadamente fuera del alcance. Los cinco tests
HTTP/PG también se ejecutaron en Mac durante desarrollo; no se cuentan dos veces.
DeprecationWarning existentes de protobuf, Starlette/httpx/anyio. Sin fallos finales.

Dos intentos iniciales de configurar el runner nativo fallaron antes de tests por
hostname de DATABASE_URL y JWT_SECRET ausente; se corrigió sólo el entorno efímero.
Una comparación de paridad detectó created_at de calibración distinto: se fijó el
reloj exclusivamente en ese test, sin eliminar métricas ni alterar producción.

Nuevos archivos: test_event_journal, test_local_event_runtime,
test_local_journal_architecture, test_local_docker_event_parity,
test_local_journal_postgres. Se actualizan las guardas de etapas anteriores para
permitir la integración Local ahora autorizada sin relajar prohibiciones de SQL/
PostgreSQL en cliente, SQLite en científico/emitter/Docker, ni FastAPI en journal.
La prueba Local preexistente de fit mínimo se adapta al esquema/reporter E10; su
fixture ahora limita explícitamente fit a una época y entrada 32x32. Los
subprocesses confinan también KERAS_HOME a sus directorios temporales; se retiró
un keras.json por defecto generado durante el primer ensayo, ausente al inicio.

Local: PYTHONPATH=M:backend_api, PYTHONDONTWRITEBYTECODE=1,
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, MPLCONFIGDIR=/tmp/e10_8_mpl, KERAS_HOME=/tmp/e10_8_keras,
venv existente `python -B -m pytest -p no:cacheprovider`. Pruebas nuevas HTTP/PG:
RUN_E10_LOCAL_JOURNAL_POSTGRES_TESTS=1; nativas requieren platform Darwin.

Para fixture nativa se deriva DATABASE_URL de configuración existente sólo en el
entorno del proceso de test: host db, puerto publicado 5432 y libpq hostaddr=127.0.0.1.
JWT aleatorio efímero y STORAGE_ROOT=/tmp; no se imprimen credenciales ni se cambian
.env ni configuración persistente. No se accede a PostgreSQL desde agent/worker.

Regresión Docker desde copia `/tmp/capstone_e10_8_53ad` del backend, mismos opt-ins
E10.3–E10.7, Local/control/GlobalGate. Se excluye inspección histórica public; tests
nativos y fit Local se ejecutan en Mac. Fixtures crean y eliminan schemas
capstone_test_e4_<uuid>, copiando sólo definición de audit_events. No se modifica
public operativo, no se instala dependencia, no hay migración Alembic nueva.

## 26. Limitaciones

SQLite/FULL/fsync y crashes reales acreditan estas fronteras, no un ensayo físico
de corte de energía/disco defectuoso. Journal/lock son locales y requieren filesystem
local fiable; no proporcionan coordinación distribuida de writers ni backup.
Un journal perdido/corrupto exige diagnóstico, no reconstrucción especulativa.
El estado legacy del agente conserva su mecanismo previo; no se implementa recuperación
de un agente muerto antes de guardar exit proof ni resume de TensorFlow.

Si alguien cierra manualmente el job mientras hay pending, fencing puede impedir
su recuperación; no se reabre el job ni se relaja autorización. La retención del
agente evita ese cierre en el flujo integrado. Un error terminal no confirma éxito
científico. No existe política de garbage collection de journals en E10.8.

## 27. Deuda transitoria y archivos productivos

Reports y repository put/records/finish siguen acoplados a train; su firma opcional
sigue siendo transitoria hacia E10.11. Dos escrituras legacy/E10 siguen siendo
secuenciales, no una transacción distribuida. SQLite es estado operacional de entrega,
no fuente científica ni sustituto de PostgreSQL.

Nuevos: execution/journal.py, local_execution/event_journal.py,
local_execution/event_runtime.py. Modificados E10.8: execution/emitter.py,
local_execution/worker.py, agent.py, event_backend.py, event_client.py (docstring),
backend_api/app/routes/local_execution.py. HttpRunReporter, Api.call_event, Reports,
backend.operation, context resolver, ResultService, PostgresResultRepository,
TRAIN y Docker worker conservan sus implementaciones aprobadas.

## 28. Requisitos E10.9 y cierre

Definir contrato científico final compartido, punto inequívoco de EVALUATION_COMPLETED,
matriz/conteos cuando no se calibra, vinculación split/epoch/threshold y consolidación
de resultados en runs.parameters. No confundir ese trabajo con entrega durable ni
con el estado verified legacy. Nada de E10.9 se implementa aquí; no se modifica
Completion Contract ni se elimina Reports. Entrega para revisión humana, sin commit.

### Estado Git al cierre

El diff acumulado incluye E10.7, que ya estaba sin commit al comenzar E10.8.
14 archivos tracked modificados (256 inserciones, 32 eliminaciones) y 15 archivos
nuevos: seis de E10.7 y nueve de E10.8. No se crearon commits.
`git diff --check` limpio; Alembic sigue en 29 revisiones, head 20260922_01.
Las copias temporales del backend y los caches de pruebas se retiraron.

```text
 M backend_api/app/routes/local_execution.py
 M malaria_dl_local_project/src/malaria_dl/execution/composition.py
 M malaria_dl_local_project/src/malaria_dl/execution/emitter.py
 M malaria_dl_local_project/src/malaria_dl/execution/repository.py
 M malaria_dl_local_project/src/malaria_dl/execution/train.py
 M malaria_dl_local_project/src/malaria_dl/execution/worker.py
 M malaria_dl_local_project/src/malaria_dl/local_execution/agent.py
 M malaria_dl_local_project/src/malaria_dl/local_execution/event_backend.py
 M malaria_dl_local_project/src/malaria_dl/local_execution/event_client.py
 M malaria_dl_local_project/src/malaria_dl/local_execution/worker.py
 M malaria_dl_local_project/tests/test_docker_reporter_architecture.py
 M malaria_dl_local_project/tests/test_event_emitter_architecture.py
 M malaria_dl_local_project/tests/test_http_reporter_architecture.py
 M malaria_dl_local_project/tests/test_local_execution_postgres.py
?? docs/engineering/e10_execution_refactor/e10_7_docker_train_integration.md
?? docs/engineering/e10_execution_refactor/e10_8_local_train_journal.md
?? malaria_dl_local_project/src/malaria_dl/execution/journal.py
?? malaria_dl_local_project/src/malaria_dl/local_execution/event_journal.py
?? malaria_dl_local_project/src/malaria_dl/local_execution/event_runtime.py
?? malaria_dl_local_project/tests/docker_train_fixture.py
?? malaria_dl_local_project/tests/fixtures/e10_6_train.py
?? malaria_dl_local_project/tests/test_docker_train_architecture.py
?? malaria_dl_local_project/tests/test_docker_train_integration.py
?? malaria_dl_local_project/tests/test_docker_train_postgres.py
?? malaria_dl_local_project/tests/test_event_journal.py
?? malaria_dl_local_project/tests/test_local_docker_event_parity.py
?? malaria_dl_local_project/tests/test_local_event_runtime.py
?? malaria_dl_local_project/tests/test_local_journal_architecture.py
?? malaria_dl_local_project/tests/test_local_journal_postgres.py
```
