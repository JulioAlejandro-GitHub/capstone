# E10.5 — HttpRunReporter y frontera HTTP autenticada

Fecha: 2026-09-22. Alcance: entrega de eventos sintéticos; pendiente de revisión
humana. E10.6 no implementada. Referencias: [baseline](baseline.md),
[E10.1](e10_1_contracts.md), [E10.2](e10_2_result_service.md),
[E10.3](e10_3_postgres_result_repository.md), [E10.4](e10_4_docker_reporter.md).

Rutas abreviadas: `S` = `malaria_dl_local_project/src/malaria_dl`,
`T` = `malaria_dl_local_project/tests`, `B` = `backend_api`.

## 1. Auditoría previa de identidad Local

Se inspeccionaron `local_execution/{agent,worker,transport,backend,storage,processes}.py`,
la route Local y `app/security.py`; contratos, servicio y adaptador E10 aprobados;
`execution/repository.py`, `controlled.py` y el esquema versionado de jobs/sesiones/
intentos/runs. No fue necesario añadir columnas ni modificar migraciones.

| Identidad | Origen y significado actual | Uso E10.5 |
|---|---|---|
| `request_id` / `job_id` | Mac presenta UUID; claim lo persiste como PK `local_execution_jobs.id`. El agente guarda la solicitud antes del HTTP; siguientes trabajos secuenciales usan otro UUID. | Selector presentado por el cliente; sólo sirve junto con principal autenticado y agente coincidentes. |
| `agent_id` | Mac lo envía en claim; PostgreSQL lo vincula al job. | Selector contrastado con la fila; no constituye una credencial independiente. |
| `principal` | `Principal.user_id` proviene de JWT `sub`, validado por `current_principal`; claim lo persiste en el job. | Nunca se acepta del DTO. Se compara con el caller autenticado. |
| `request_hash` | Backend calcula `digest(data)` al reclamar. Repetir request id exige mismo hash y principal. | Identidad de la solicitud de claim, no credencial ni fingerprint del evento. No se transmite en events. |
| `local_execution_jobs.owner` | Backend genera UUID para token del gate. Claim lo publica como `result.owner` y sustituye por él el owner de la sesión pública. | Token de ejecución resuelto en DB; el cliente E10 ni siquiera lo presenta. |
| `train_execution_sessions.owner` | Repositorio genera el owner interno de la sesión. El job conserva una copia en `session.owner`. | Se obtiene de la sesión actual y se contrasta con la copia interna del job. Nunca con `result.session.owner`. |
| `run_id` | Repositorio crea run; job lo persiste como FK única y dentro de `session`. | Job → sesión/run inequívocos. `event.run_id` es una afirmación que debe coincidir. |
| `attempt_id` | Repositorio crea intento, lo vincula a `training_run_id`, miembro y sesión. | Se resuelve desde sesión + intento; `event.attempt_id` debe coincidir exactamente. |
| `session` | Snapshot interno persistido en job; sesión actual en `train_execution_sessions`. La copia pública cambia owner y rutas. | Sólo las dos fuentes internas participan en la resolución. |
| JWT | Bearer tomado de `CAPSTONE_AGENT_BEARER`; worker hereda el entorno. Firma, expiración, tipo access, usuario activo y permiso se validan en backend. | Mismo mecanismo, `AUTH_MODE=local_jwt`, `SYSTEM_ADMIN`. |
| Heartbeat | Envelope legacy job/agent/owner remoto + PID, create_time, host, platform. Backend fija/compara process; frecuencia 15 s, incertidumbre después de 60 s sin liberar. | Permanece separado, sin event_id ni sequence E10. |

Respuestas previas al diseño:

- **A:** worker puede presentar `job_id` y `agent_id`; son referencias, no autoridad.
- **B:** PK del job → FK única `run_id` → sesión → attempt → member/campaign;
  sesión actual y snapshot del job determinan owner interno. El token del gate
  está en job.owner. Existe identidad suficiente en el esquema actual.
- **C:** Mac proporciona request/agent, parámetros del claim, configuración de
  roots, identidad de proceso, evidencia legacy y eventos nuevos ya construidos.
- **D:** PostgreSQL conserva el vínculo autenticado principal/job/agent, token,
  run, snapshot interno y estado actual; sesión/intento/miembro/campaña contienen
  las identidades que necesita ExecutionContext.
- **E:** no confiar en owner interno, principal, estado, campaign/member,
  configuración/hashes ni identidad científica suministrada como contexto cliente.
  Run/attempt del evento también requieren comparación, aunque formen parte de
  la identidad inmutable del propio evento.

## 2. Qué conoce el Mac

El runtime legacy sigue recibiendo job público, token remoto, run, attempt,
configuración y referencias de almacenamiento. El nuevo reporter necesita sólo
URL, bearer, `RemoteExecutionIdentity(job_id, agent_id)` y el RunEvent completo.
No recibe `ExecutionContext`, owner interno, engine ni repositorio.

No se introduce una credencial criptográfica por agente: se conserva JWT + vínculo
persistido. Un agent_id por sí solo no autoriza. El administrador autenticado que
posee el job presenta el selector de agente asignado, y ambos se comprueban.

## 3. Qué resuelve el backend

`LocalExecutionContextResolver` consulta:

| Campo | Fuente autoritativa |
|---|---|
| execution token | `local_execution_jobs.owner` |
| run | `local_execution_jobs.run_id`, contrastado con snapshot y sesión |
| owner, attempt | `train_execution_sessions`, contrastados con snapshot del job |
| dataset_version | `runs.dataset_version_id` y snapshot dataset de sesión |
| model_id, adapter_version | `train_execution_sessions.configuration` |
| member, campaign | `campaign_attempts → campaign_members → experimental_campaigns` |
| configuration_hash, contract_hash | miembro y campaña, respectivamente |
| execution_mode | `LOCAL_PYTHON`, porque es una entrega autorizada de un job Local |

Job debe estar `held` o `calculation_reported`; sesión debe estar `active`. Se
contrasta campaign del job, training_run del intento, owner/run/attempt/configuración/
dataset del snapshot interno. Snapshot faltante o incoherente falla cerrado.
Los jobs Local actuales siempre pertenecen a un intento de campaña; no se inventa
un camino Local standalone sin esa identidad.

## 4. HttpRunReporter

`S/execution/reporters/http.py`: implementa `RunReporter` con
`HttpRunReporter(api_client, remote_execution_identity).report(event) -> None`.
Envía `EventRequest.to_dict()` mediante `Api.call_event()`. No genera UUID,
secuencia, timestamp, tipo, payload, fingerprint ni decisiones de persistencia.

El recibo debe contener exactamente status/run_id/event_id/sequence, referirse al
mismo evento y tener status `accepted` o `duplicate_accepted`. Cualquier otro recibo
produce `EventProtocolError`; HTTP 200 por sí solo no confirma entrega.

## 5. DTO HTTP

`S/local_execution/event_transport.py` contiene dataclasses inmutables explícitas.
Envelope exacto:

```json
{
  "job_id": "UUID del job",
  "agent_id": "UUID del agente asignado",
  "event": {
    "event_id": "UUID estable del evento",
    "run_id": "UUID del run",
    "attempt_id": "UUID del intento o null según RunEvent v1",
    "sequence": 1,
    "event_type": "epoch_completed",
    "schema_version": "run_event_v1",
    "occurred_at": "2026-09-22T13:00:00+00:00",
    "payload": {}
  }
}
```

No owner remoto/interno, principal, ExecutionContext, campaign/member, hashes ni
estado. Campos desconocidos se rechazan; no se ignoran. `RunEvent.from_dict`
mantiene la validación E10.1, sin coerción Pydantic que borre distinciones numéricas.
El JSON transporta 1, 1.0, bool, signed zero, Unicode/NUL/surrogates conforme al
contrato existente. Sólo el adaptador E10.3 canonicaliza para identidad durable.

## 6. Endpoint y composición

`POST /execution/local/events`, registrado antes de `/{operation}` en
`B/app/routes/local_execution.py`. Es una operación de la familia existente.
La route autentica/autoriza, valida DTO, llama backend y traduce recibo/errores;
no contiene SQL ni reglas de idempotencia. No necesita roots porque no escribe
artefactos ni interpreta payload científico.

Cliente: `S/local_execution/event_client.py::build_http_run_reporter`
compone Api → HttpRunReporter. Backend:
`event_backend.py::build_local_event_backend` compone resolver → ResultService →
adaptación Local de PostgresResultRepository. No framework DI adicional.

```text
Mac native Python (productor sintético)
      |
HttpRunReporter
      |
     HTTP
      |
Authenticated FastAPI
      |
Remote identity + JWT principal
      |
ContextResolver
      |
authoritative ExecutionContext
      |
ResultService
      |
PostgresResultRepository (+ revalidación Local dentro de su transacción)
      |
PostgreSQL

train() -------- X -------- HttpRunReporter
                   todavía no integrado
```

## 7. Context resolver y frontera transaccional

Resolver sólo lee y construye identidad; no inserta evidencia ni cambia estados.
Primera resolución: transacción READ ONLY propia y engine liberado al terminar.
No mantiene un lock exterior mientras otro engine intenta tomar el mismo gate.

La primera consulta no basta para autorizar un commit posterior. Por eso
`_LocalResultRepository` extiende únicamente `_authorize`: primero invoca el
fencing íntegro del adaptador aprobado; luego vuelve a resolver en **esa misma
conexión y transacción**, tomando `FOR SHARE NOWAIT` sobre el job y exigiendo
contexto/token idénticos a los resueltos. Así también protege principal y agente
contra cambios entre ambas consultas, incluso en retries.

No se cambia código E10.3, su port, su escritura, su canonicalización ni el commit.
La dependencia del método protegido es deliberada y queda cubierta por regresión:
si evoluciona la frontera de autorización E10.3, esta adaptación deberá revisarse.

## 8. Autenticación y autorización

Mismo `require_permission(Permission.SYSTEM_ADMIN)` que Local legacy. Se conserva
validación real de JWT y usuario activo; no hay endpoint anónimo ni bearer nuevo.
Además del opt-in `CAPSTONE_LOCAL_EXECUTION_ENABLED=1`, events exige explícitamente
`AUTH_MODE=local_jwt`; no admite el principal sintético del modo disabled. Esa
restricción afecta sólo events. Los tests no sustituyen current_principal ni el
permiso: usan JWT firmados y usuarios sintéticos en el esquema temporal.

## 9. Owner interno

El owner efectivo procede de `train_execution_sessions.owner` y debe coincidir
con `local_execution_jobs.session.owner`. **No** procede de `job.result`, ni del
owner público que legacy entrega al Mac. `job.owner` es exclusivamente el token
del gate. Se comprueba que ambos UUID son distintos en el fixture.

Inyectar `owner` en el DTO devuelve 422 antes de resolver. Corromper el owner del
snapshot interno del job en DB devuelve 403; no produce cambio de owner ni filas.
No se desactivan triggers para fabricar una sesión inválida.

## 10. Fencing y doble defensa

Nivel HTTP: JWT + permiso + job/principal/agent + contexto persistido coherente.
Nivel repository: token global, owner interno, sesión activa, run training/running,
intento y lineage autorizados, locks vigentes durante aceptación y commit.
La adaptación Local vuelve a comprobar job/principal/agent bajo esos locks.

Gate → lineage/sesión/run E10.3 → job compartido NOWAIT. Una colisión de locks
genera error de infraestructura reintentable, no éxito ni espera indefinida.
No se reemplaza la transacción raíz por un savepoint. Released/failed, sesión
inactiva y token revocado rechazan también reenvíos de eventos ya persistidos.

## 11. Idempotencia HTTP

Aceptación sólo se responde después del commit E10.3. El cliente hace un intento
por `call_event`; un error conserva el evento para retry explícito, sin crear ID.
`Api.call()` legacy mantiene intactos sus tres intentos y backoff.

Pruebas: evento → commit real → respuesta consumida y pérdida simulada → error
de transporte → reenvío exacto → duplicate_accepted y una sola fila. También se
recrean cliente, aplicación/servidor HTTP, resolver, servicio, repositorio y engines.
Un fallo real inyectado en el límite de commit revierte y retorna 503; reenviar el
mismo evento después de retirar el fallo produce una sola aceptación.

## 12. Sequence

Reporter y backend no asignan ni renumeran. El servicio/repositorio aprobados
mantienen contiguous desde 1, conflicto de slot y gap. Retry exacto de secuencia
antigua es idempotente mientras el writer siga autorizado. En un stream contiguo
append-only, un slot viejo ocupado da SEQUENCE_CONFLICT; STALE_SEQUENCE conserva
su mapping y sus tests E10.2, sin fabricar huecos SQL para ejercitarlo.

## 13. Mapping HTTP y errores del cliente

| Resultado | HTTP | Mensaje de route |
|---|---:|---|
| Nuevo | 200 | recibo `status=accepted` |
| Retry exacto autorizado | 200 | recibo `status=duplicate_accepted` |
| Sin JWT / JWT inválido / usuario inactivo | 401 | mecanismo auth existente |
| Permiso insuficiente | 403 | mecanismo auth existente |
| Job inexistente/otro agente/principal/estado u owner inválido; fencing | 403 | WRITER_NOT_AUTHORIZED |
| Run/attempt distintos | 409 | RUN_ID_MISMATCH / ATTEMPT_ID_MISMATCH |
| Mismo ID, distinto contenido | 409 | EVENT_ID_CONFLICT |
| Slot ocupado / gap / stale | 409 | SEQUENCE_CONFLICT / SEQUENCE_GAP / STALE_SEQUENCE |
| DTO/schema/tipo inválido | 422 | LOCAL_EVENT_CONTRACT_INVALID (o código de schema/tipo del servicio) |
| Persistencia/commit no confirmados | 503 | RESULT_PERSISTENCE_ERROR |
| Deshabilitado / modo auth inseguro | 503 | LOCAL_EXECUTION_DISABLED / LOCAL_EVENTS_REQUIRE_LOCAL_JWT |
| Excepción inesperada | 500 | LOCAL_EVENT_INTERNAL_ERROR |

En app.main el handler existente envuelve errores en
`error.{code,message,details,correlation_id,retryable}`: 403→FORBIDDEN,
409→CONFLICT, 503→DATABASE_UNAVAILABLE; `message` conserva el código sanitizado
de la route. Su fallback para HTTPException 422/500 es REQUEST_ERROR. El router
aislado de los tests tiene el envelope estándar `detail`; se prueba además el
handler de producción. No se altera ninguna convención global.

Cliente: HTTP <500 → `EventRejected(status)`; HTTP >=500 →
`EventServerFailure(status)`; red/timeout/conexión truncada →
`EventTransportFailure`; JSON o recibo inválido → `EventProtocolError`.
No incorpora cuerpos remotos, SQL, URL ni bearer en excepciones. Tamaño de request
limitado a 8 MiB y timeout existente 15 s. No hay fallback a archivos.

## 14. Pruebas y reproducción

Nuevas: `T/test_http_run_reporter.py`, `test_http_reporter_architecture.py`,
`test_http_reporter_postgres.py`. Guardas Docker conservan su allowlist original
aplicada específicamente a docker.py; HTTP tiene guardas propias de cliente.
Arquitectura verifica ausencia de imports SQL/servidor/ResultService en reporter,
agent, worker y cliente; resolver sin escrituras; route sin SQL; dominio sin HTTP.

Resultado: **398 tests aprobados: 58 nuevos + 340 de regresión**, sin fallos finales.

| Grupo | Aprobados |
|---|---:|
| E10.1/E10.2, Docker unitario y guardas aprobadas | 185 |
| HTTP reporter unitario y nuevas guardas AST | 22 |
| HTTP real/JWT/resolver/ResultService/PostgreSQL | 36 |
| E10.3/E10.4/E5/control/Local PostgreSQL | 114 |
| Readers/artefactos/coordinación E5 sin train | 19 |
| Auth HTTP y configuración existentes | 22 |
| **Total único (sin contar repeticiones de desarrollo)** | **398** |

Dos avisos de deprecación de dependencias existentes de TestClient
(httpx y BlockingPortal); no se añaden dependencias. `check_alembic_linearity.py`:
29 revisiones, head único `20260922_01`. `git diff --check`: limpio.

No se ejecuta fit ni campaña real. Fixtures E10.3 crean schemas
`capstone_test_e4_<uuid>` y verifican su
eliminación; las pruebas HTTP añaden usuarios y job sintéticos sólo allí.
Se reutiliza el servicio PostgreSQL Docker existente, con conexiones reales; no se
crea otra base ni se modifica `public`. El fixture lee la definición de audit_events
para clonarla, no copia sus datos. Ninguna migración se aplica a la BD operativa.

Reproducción en copia temporal dentro del backend, con `PYTHONPATH` apuntando a
`malaria_dl_local_project:backend_api`, `PYTHONDONTWRITEBYTECODE=1`,
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `python -B -m pytest -p no:cacheprovider`:

- E10.5 PostgreSQL: `RUN_E10_HTTP_POSTGRES_TESTS=1`, archivo HTTP PostgreSQL.
- E10.3/E10.4: `RUN_E10_POSTGRES_TESTS=1`,
  `RUN_E10_DOCKER_REPORTER_POSTGRES_TESTS=1`, sus dos archivos PostgreSQL.
- E5/control/Local: `RUN_STAGE5_POSTGRES_TESTS=1`,
  `RUN_STAGE93_CONTROLLED_POSTGRES_TESTS=1`, `RUN_LOCAL_EXECUTION_POSTGRES_TESTS=1`;
  archivos campaign_executor_postgres, controlled_train_postgres y
  local_execution_postgres; excluir `public` y
  `test_minimal_real_calculation_through_http_agent_and_subprocess`.
- Auth/config HTTP: `B/tests/test_foundation_http.py`, `test_foundation_config.py`.
- Contratos, ResultService, Docker reporter y guardas: suites unitarias E10.1–4
  y nuevas HTTP. Readers/artefactos: campaign_executor_e5 y campaign_exit_diagnostics,
  excluyendo el test que llama train y el bind check redundante.

La copia temporal incluye entrypoints `M/*.py` y código de
`malaria_dataset_split_project/src`, requeridos por imports de regresión y app.main.
Los primeros intentos de colección detectaron esas dos omisiones de la copia;
se completó el árbol temporal sin modificar esos archivos del repositorio.

## 15. Tampering

Se prueban por HTTP: run ajeno (409), intento ajeno (409), agente/principal ajeno
(403), job inexistente (403), owner/context extra (422), mismo event_id con otro
payload (409), schema desconocido y bool como sequence (422). No generan evidencia.
Cambiar principal, agente, estado o snapshot owner en DB después de la primera
resolución falla en la revalidación transaccional. No basta un contexto previamente
válido para confirmar un evento.

## 16. Side effects y readers

Snapshots completos antes/después de EVALUATION_COMPLETED y TRAINING_COMPLETED
comparan runs (incluido parameters), campaign_attempts, campaign_members y
train_execution_sessions. También se compara la fila completa del job. Sólo se
añaden los records E10 esperados. Session sigue active; ningún evento completa o
verifica run/miembro/sesión, ni libera job, ni escribe resultados científicos.

Las pruebas de regresión E10.4 conservan la verificación de readers, calibración,
artefactos y guardas legacy. La prueba HTTP de digest comprueba evidencia legacy
intacta y cambio de hash al añadir el evento terminal.

## 17. records_hash pendiente

**BLOCKER E10.6 abierto:** `ExecutionRepository.records()` devuelve también
`kind=e10_event`; `digest(records)` cambia. HttpRunReporter tiene exactamente el
mismo efecto que DockerRunReporter. No se excluyen filas del hash, no se cambia
canonical(), verify_session(), ni completion/lineage. Un hash calculado antes del
último evento no verifica la colección posterior. No conectar train hasta resolver
alcance, orden del último evento y cálculo de hash.

## 18. Cambios deliberadamente no realizados

Sin cambios en train ni firma, callbacks/productor, worker/agent Local, Reports,
Api.call legacy, heartbeat, rutas de artefactos, estados científicos, runs.parameters,
ResultService, port ResultRepository, implementación PostgresResultRepository,
contratos E10.1 o migraciones. Sin EventFactory/SequenceAllocator ni integración
productiva. La nueva operación queda disponible al montar la route existente con
opt-in; ningún runtime actual la invoca. No commit, despliegue ni reinicio de servicios.

## 19. Gaps concretos para E10.6

1. Resolver records_hash y orden final de evidencia/completion antes de integración.
2. Diseñar productor compartido y asignación contigua de sequence por run.
3. Retener identidad completa de cada evento para retry/reconexión del productor;
   reporter no es cola durable ni asignador.
4. Definir sustitución gradual de Reports y su API de lectura/finish, que RunReporter
   no implementa, manteniendo equivalencia Docker/Local.
5. Integrar train/callbacks sólo después de aprobar esa frontera y su regresión.
6. Mantener heartbeat operativo fuera del stream salvo decisión explícita posterior.
7. La consolidación en runs.parameters y transiciones terminales siguen sin implementarse;
   no inferirlas de los eventos terminales actuales.

E10.5 termina en la frontera HTTP probada. Espera revisión humana antes de E10.6.
