# E10.2 — ResultService y puerto de persistencia

## 1. Objetivo y referencias

Crear y probar la frontera de aplicación de aceptación de eventos, sin conectarla
a ningún ejecutor. Se leyeron completos [baseline E10.0](baseline.md) y
[contratos E10.1](e10_1_contracts.md), y se revisaron todos los módulos de
`execution/contracts/` antes de editar. E10.1 está aprobado y permanece intacto;
no se encontró un defecto bloqueante que requiera modificarlo.

Base inspeccionada: `a9b217e202eebaf566b98d9a49a28c2686e96de3`, árbol inicialmente
limpio. Inspección adicional: `execution/repository.py`, `execution/campaign.py`,
`local_execution/agent.py`, `transport.py`, `backend.py`, errores de governance y
DDL de `20260912_01_train_execution.py` / `20260915_01_local_execution.py`.
Las rutas Python abreviadas son relativas a `malaria_dl_local_project/src/malaria_dl/`.

El repositorio actual hace autorización, lookup idempotente y append de records
dentro de una transacción con bloqueo de sesión. Su clave actual es
(run, kind, phase, record_key), no event_id. Los guards mantienen owner activo,
identidad de sesión y evidencia append-only. No se importan ni copian esos adapters.

## 2. Arquitectura

```text
RunEvent + ExecutionContext
   |
   v
ResultService
   |
   | application port
   v
ResultRepository
   |
   v
[NO IMPLEMENTADO EN E10.2]
PostgreSQL adapter futuro
```

El servicio contiene las decisiones de identidad/idempotencia/secuencia. El puerto
proporciona autorización actual y un ámbito protegido de lectura/append/confirmación.
No hay construcción automática de repositorios, conexiones ni integración productiva.

## 3. Ubicación y archivos

Se eligió `results/`, junto a otros dominios como `campaigns/` y `assessment/`.
Expresa una responsabilidad de aplicación independiente de los ejecutores. Mantiene
ABC y dataclasses congeladas, como los contratos aprobados y convenciones existentes.
No se reorganizan módulos.

Archivos creados:

- `malaria_dl_local_project/src/malaria_dl/results/__init__.py`
- `malaria_dl_local_project/src/malaria_dl/results/service.py`
- `malaria_dl_local_project/src/malaria_dl/results/repository.py`
- `malaria_dl_local_project/src/malaria_dl/results/models.py`
- `malaria_dl_local_project/src/malaria_dl/results/errors.py`
- `malaria_dl_local_project/src/malaria_dl/results/identity.py`
- `malaria_dl_local_project/tests/result_repository_fake.py`
- `malaria_dl_local_project/tests/test_result_service.py`
- `malaria_dl_local_project/tests/test_result_dependencies.py`
- `docs/engineering/e10_execution_refactor/e10_2_result_service.md`

Archivos preexistentes modificados: ninguno. El fake vive en tests como helper
explícito; no se exporta desde el paquete productivo.

## 4. ResultService

API: `ResultService(repository: ResultRepository)` y
`accept_event(context: ExecutionContext, event: RunEvent) -> EventAcceptance`.

Orden de validación/decisión:

1. Exigir objetos de los contratos E10.1.
2. Comparar run_id y attempt_id, incluida la ausencia del intento.
3. Comprobar `run_event_v1` y enum RunEventType.
4. Entrar en el ámbito del repositorio: autorización/fencing antes de exponer estado.
5. Resolver event_id existente: duplicado exacto o conflicto.
6. Para evento nuevo, comprobar ocupación de sequence y continuidad.
7. Solicitar append sólo para evento nuevo válido.
8. Devolver aceptación sólo después de salir exitosamente del ámbito.

El payload es opaco: no se interpretan métricas, umbrales ni tipos científicos.
Todos los tipos E10.1 siguen esta misma regla, incluido HEARTBEAT. Los campos
fundamentales y JSON ya se validan al construir RunEvent. Las comprobaciones de
schema/enum del servicio son defensivas; los tests inyectan objetos alterados
artificialmente para recorrerlas, sin relajar el constructor E10.1.

## 5. ResultRepository: puerto abstracto

API única del repositorio:

```python
def acceptance_scope(
    self, context: ExecutionContext, event: RunEvent,
) -> AbstractContextManager[EventAcceptanceScope]: ...
```

El scope queda ligado al candidato exacto y sólo es válido dentro del `with`.
Su interfaz mínima es:

- `state: AcceptanceState`: snapshot protegido con `existing_event` buscado por
  event_id global, `sequence_event` buscado por (run_id, sequence), y `last_sequence`
  confirmado del run (0 si está vacío).
- `append() -> None`: prepara la escritura del evento ligado, sin reemplazarlo;
  no confirma éxito por sí mismo. Sólo se invoca una vez para un candidato nuevo.

Se escogió un ámbito atómico explícito en lugar de get/check/insert independientes.
Así la política permanece en ResultService y el adapter futuro controla aislamiento,
locks y commit. No hay API de tablas, query SQL, session ORM ni unidad de trabajo genérica.
`EventAcceptanceScope` también es ABC; es parte del mismo puerto de aceptación.

## 6. EventAcceptance

Dataclass frozen/slots/keyword-only: `status`, `run_id`, `event_id`, `sequence`.
Status es enum de strings:

- `ACCEPTED = "accepted"`.
- `DUPLICATE_ACCEPTED = "duplicate_accepted"`.

No contiene timestamps de respuesta variables, estado de runtime ni referencias de
transporte. Es determinística para el mismo evento y resultado; la primera aceptación
y su retry difieren deliberadamente en status. Un duplicado antiguo devuelve su
sequence original, no el watermark actual.

## 7. Errores tipados

Jerarquía pequeña: `ResultError(RuntimeError)` y subclases con código estable.
Los errores no incorporan detalles del driver o del payload a su mensaje.

| Clase | Código |
| --- | --- |
| RunIdentityMismatch | RUN_ID_MISMATCH |
| AttemptIdentityMismatch | ATTEMPT_ID_MISMATCH |
| UnsupportedEventSchema | UNSUPPORTED_EVENT_SCHEMA |
| InvalidEventType | INVALID_EVENT_TYPE |
| WriterNotAuthorized | WRITER_NOT_AUTHORIZED |
| EventIdConflict | EVENT_ID_CONFLICT |
| SequenceConflict | SEQUENCE_CONFLICT |
| SequenceGap | SEQUENCE_GAP |
| StaleSequence | STALE_SEQUENCE |
| ResultPersistenceError | RESULT_PERSISTENCE_ERROR |

La entrada que no sea ExecutionContext/RunEvent produce TypeError. Los conflictos
no se representan con bool. Las excepciones del repositorio se propagan: nunca se
transforma un fallo en ACCEPTED. El adapter futuro deberá traducir errores propios
de almacenamiento a ResultPersistenceError; la capa de aplicación no conoce drivers.
Un fallo de confirmación puede representar commit incierto, no rollback asegurado.

## 8. Identidad

`context.run_id == event.run_id` y `context.attempt_id == event.attempt_id` exactamente.
None sólo es aceptable en ambos lados (standalone). Un attempt presente unilateralmente
se rechaza; no se completa desde el contexto ni se inventa.

El puerto contrasta el contexto con la identidad autorizada de la ejecución. Los
campos opcionales suministrados deben ser compatibles con la fuente autoritativa;
None no permite omitir controles obligatorios de run/attempt/owner/estado. El fake
registra un contexto autorizado por run y exige igualdad completa. Esto permite
simular tanto rechazo de metadatos incompatibles como renovación explícita del owner.

## 9. Owner y fencing

ExecutionContext contiene el owner aceptado por la capa que lo construye. El servicio
no compara tokens remotos con owners internos ni bifurca por execution_mode.
El puerto debe verificar identidad, sesión activa y fencing al entrar, manteniendo
esa autorización protegida hasta confirmar la operación. La revocación concurrente
debe serializarse con esa protección; una autorización previa fuera del scope no basta.

También se autoriza antes de responder a un duplicado: un owner revocado o una sesión
inactiva no obtiene DUPLICATE_ACCEPTED. Esto conserva la exigencia actual de writer
activo. Una política de consulta/reconciliación tras cierre, si se requiere, será
responsabilidad futura separada y explícita. Cambiar owner fuera del evento no altera
su identidad; un nuevo writer autorizado puede reenviar el mismo evento.

## 10. Idempotencia canónica

`canonical_event(event)` usa exclusivamente `event.to_dict()` de E10.1 y
`json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)`.
Se compara el texto completo, sin hash susceptible de colisión ni repr.
Incluye los ocho campos del envelope: IDs, sequence, tipo, schema, instante y payload.
El orden de claves de objetos no importa, incluso anidado. El orden de arrays sí.
Los timestamps equivalentes ya están normalizados a UTC por E10.1.

Se preservan distinciones del contrato Python/JSON: 1 frente a 1.0, true frente a 1,
0.0 frente a -0.0, y strings Unicode sin normalización adicional. No se usa igualdad
de dict/dataclass, que equipararía algunos de esos valores. No se usa la canonicalización
de campañas, que normaliza floats integrales. Esta representación es un contrato de
esta aplicación Python, no una afirmación de implementar RFC 8785.

Alcance de event_id: único en el repositorio, incluso entre runs. Reutilizarlo para
otro run/attempt genera EVENT_ID_CONFLICT tras validar/autorizar el contexto recibido.
El adapter debe conservar la representación suficiente para distinguir los tipos
numéricos anteriores; reconstruir únicamente desde una representación que los colapse
no satisface este contrato.

| Caso autorizado | Resultado |
| --- | --- |
| event_id desconocido y sequence siguiente | ACCEPTED y un append |
| event_id conocido y canonical completo idéntico | DUPLICATE_ACCEPTED, sin append |
| event_id conocido y canonical distinto | EVENT_ID_CONFLICT, sin append |

El contexto no forma parte del canonical del evento: el owner no se incluye en
RunEvent aprobado; la compatibilidad del contexto se comprueba por autorización.

## 11. Sequence y concurrencia de heartbeat

Política por run: primer evento 1; para nuevos, `sequence == last_sequence + 1`.
La secuencia no se obtiene del timestamp, del número de registros ni del orden
lexicográfico kind/phase/record_key del ledger actual.

Prioridad después de autorización:

1. event_id conocido: duplicate o EVENT_ID_CONFLICT, aunque sequence sea antigua.
2. event_id nuevo con sequence ocupada: SEQUENCE_CONFLICT.
3. sequence mayor que la esperada: SEQUENCE_GAP; no reservar ni avanzar watermark.
4. sequence menor que la esperada sin registro coincidente: STALE_SEQUENCE.
5. sequence esperada: append.

En un stream íntegro y contiguo, una sequence antigua estará ocupada y dará conflicto.
STALE_SEQUENCE es defensa ante historia incompleta/watermark existente; no autoriza
borrar evidencia ni reutilizar huecos. El fake simula ese caso explícitamente.
Tras un gap, el emisor puede entregar el evento faltante y reenviar el rechazado
sin cambiar su identidad. El servicio no espera, renumera ni almacena pendientes.

Evidencia de concurrencia actual: `local_execution/agent.py` lanza un thread de
heartbeat cada 15 s mientras el proceso worker usa `Reports.put` síncrono.
`backend.py::operation` trata heartbeat separado de record; el heartbeat actual
actualiza el job y no produce RunEvent. Docker usa GlobalGate y wait del hijo,
sin un heartbeat periódico equivalente de sesión.

Por ello **no es válido conectar ambos productores a contadores locales independientes**.
La política se aplica exclusivamente al nuevo stream de RunEvent, que todavía no
recibe eventos productivos. El heartbeat operativo actual permanece fuera de él.
Si en una fase posterior se decide persistir HEARTBEAT como RunEvent, deberá compartir
un asignador/cola por run con los demás productores antes de entrar a ResultService.
No se define una segunda secuencia ni una excepción por tipo. La futura integración
requiere esa coordinación; E10.2 no afirma que el runtime actual ya la proporcione.

## 12. Retry semantics

El producer futuro genera event_id, sequence, occurred_at y payload una sola vez.
Un retry retransmite el mismo evento completo. Servicio y repositorio nunca generan
ni sustituyen esos campos. Tras una confirmación perdida, si el commit ocurrió,
retry devuelve DUPLICATE_ACCEPTED; si no ocurrió, puede ser ACCEPTED.

Si el writer dejó de estar autorizado, el retry se rechaza aunque el evento exista.
No se implementan reporter HTTP, spool, backoff, outbox ni reconciliación terminal.

## 13. Atomicidad requerida y fake

El scope debe proteger autorización, lookup de event_id global, ocupación de sequence,
watermark, append y confirmación. La concurrencia del mismo run y la colisión del
mismo event_id en runs diferentes deben tener un resultado serializable. El estado
leído no puede quedar obsoleto entre decisión y escritura.

Una salida normal del scope confirma durabilidad del append o lectura consistente
del duplicado. Una excepción del cuerpo cancela lo no confirmado; ninguna excepción
se suprime. Un error de escritura/commit/ACK se propaga. El servicio crea el recibo
dentro del scope y lo devuelve sólo después de su salida exitosa. No basta confirmar
un savepoint si la transacción exterior todavía puede revertirse.

El fake en tests mantiene un lock global (más fuerte que el aislamiento mínimo
por run/event_id), un contexto autorizado por run, índices por event_id y por sequence,
y watermark. Prepara append y sólo publica al salir normalmente. Simula fallos en
entrada, lectura, append, commit y ACK posterior al commit. Sus métodos de autorización
y revocación usan el mismo lock. No escribe archivos ni usa recursos externos.

Esto demuestra la política con un modelo en memoria, no certifica aislamiento o
durabilidad PostgreSQL. E10.3 debe probar esos aspectos con conexiones concurrentes.

## 14. Tests y validación

Python 3.12.13 y pytest del venv existente; sin instalaciones. Desde raíz:

```sh
PYTHONPATH=malaria_dl_local_project PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 malaria_dl_local_project/.venv-local-train/bin/python -B -m pytest -p no:cacheprovider malaria_dl_local_project/tests/test_execution_contracts.py malaria_dl_local_project/tests/test_execution_contract_dependencies.py malaria_dl_local_project/tests/test_result_service.py malaria_dl_local_project/tests/test_result_dependencies.py -q

PYTHONPATH=malaria_dl_local_project PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/e10_2_mpl malaria_dl_local_project/.venv-local-train/bin/python -B -m pytest -p no:cacheprovider malaria_dl_local_project/tests/test_campaign_executor_e5.py malaria_dl_local_project/tests/test_campaign_exit_diagnostics.py malaria_dl_local_project/tests/test_label_mapping.py malaria_dl_local_project/tests/test_decision.py malaria_dl_local_project/tests/test_image_quality.py -k 'not test_train_uses_only_train_and_val_without_csv and not test_migration_has_no_accidental_binds' -q
```

Resultado unitario: **167 passed** = 88 E10.1 intactos + 79 E10.2 (incluidas tres
guardas). Cobertura: los doce tipos en ambos modos; run/attempt/schema/enum;
autorización/metadatos/revocación; append único; retry exacto y antiguo; canonical
con orden de claves, timezone y tipos; conflictos de ID entre runs/intentos;
secuencia ocupada/gap/stale/streams independientes; fallos de repositorio y commit;
ACK perdido; cuatro escenarios concurrentes; recibo determinístico e inmutable; ABC.

Resultado de regresión: **36 passed, 2 deselected**, con dos avisos de deprecación
de `google._upb._message` sobre compatibilidad futura con Python 3.14.
La selección excluye el test que llama a train incluso con dobles, y el test de
migración. Los tests de coordinación tienen launcher/repositorio simulados. Los de
label mapping/decision/image quality son la regresión aislada habitual y usan
entradas sintéticas. No se usa fixture PostgreSQL ni se ejecuta discovery completo,
que incluye suites de BD y cálculo real. No se ejecutan TRAIN, TEST clínico,
campañas, migraciones ni escrituras sobre BD persistente.

## 15. Guardas de arquitectura

AST sobre todos los módulos de results, incluyendo imports dentro de funciones:
lista permitida de stdlib, hermanos de results y API pública execution.contracts.
Se rechazan infraestructura, repositorios concretos, imports dinámicos y eval/exec.
Una guarda adicional evita decisiones de autorización por execution_mode en service.

Un proceso nuevo con `-I -S -B` importa y ejercita la frontera sin site-packages,
con import finder que bloquea cualquier módulo fuera de stdlib, results, contratos
y sus paquetes padres. Las guardas de E10.1 también se ejecutan intactas.
Esto controla dependencias; no es un sandbox contra código deliberadamente malicioso.

## 16. Decisiones no implementadas

No hay PostgresResultRepository, reporters Docker/HTTP ni integración con train,
workers, agente, FastAPI, LocalBackend o ExecutionRepository. No se tocan PostgreSQL,
Alembic, tablas/columnas/índices/triggers, runs.parameters, completed/verified,
verificación de artefactos o gobernanza TRAIN/VAL/TEST. Se preserva runs como entidad
canónica y evidencia append-only. No se corrige todavía verified sin matriz.

No hay TrainingResultsV1, schema de métricas/matriz/threshold/completion, interpretación
científica, nueva persistencia de entorno, cambios de requirements/Dockerfile/venv,
spool, asignador de sequence ni cambios de heartbeat. No se crean commits.

## 17. Requisitos concretos para E10.3

1. Implementar el adapter del puerto con autorización/fencing vigente y protección
   hasta commit, resolviendo owner remoto/interno en la capa correspondiente.
2. Mapear event_id global, sequence por run, envelope completo y canonical a
   persistencia durable. El ledger actual no tiene esos campos de identidad: no
   derivarlos del orden lexicográfico de records. Cualquier cambio de esquema
   deberá evaluarse/autorizarse en esa fase, no está implementado aquí.
3. Conservar tipos/representación necesarios para retries exactos; evitar que una
   normalización de almacenamiento equipare 1/1.0, bool/int o pierda -0.0.
4. Demostrar con pruebas aisladas concurrencia por run y entre runs con mismo ID,
   rollback, fencing/revocación, commit visible y recuperación de ACK perdido.
   Acordar orden de locks compatible con los guards existentes, sin deadlocks.
5. No devolver aceptación antes del commit efectivo; definir traducción de errores
   y tratamiento de commit incierto sin exponer detalles de drivers.
6. Definir recuperación de streams históricos/incompletos sin fabricar IDs/secuencias,
   y eventual consulta de duplicados tras cierre sin relajar writer activo.
7. Mantener como prerrequisito de integración posterior un único asignador/cola por
   run si heartbeat, worker y orquestación comparten el stream. No conectar contadores
   independientes ni confundir heartbeat operativo con evento científico.

E10.2 termina con esta frontera aislada y sus pruebas; no implementa E10.3.
