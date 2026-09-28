# E10.OP1 — Guard de esquema anterior a la reserva

Fecha: 2026-09-28. Base revisada: `c3e4856`.
Referencia: [E10.PRE11, H1](e10_pre11_campaign_audit.md#10-hallazgos-y-límites-antes-de-e1011).

Se implementó el rechazo `E10_SCHEMA_NOT_READY` antes de reservar una campaña
E10 en PostgreSQL incompatible. El cambio está preparado para revisión humana;
no se desplegó ni se aplicó la migración operativa.

## 1. Puntos de reserva auditados

La búsqueda de llamadas a `claim` y `reserve` en los servicios y el backend
confirmó los siguientes accesos TRAIN. Las reservas de assessment y de la cola
de calidad no son TRAIN E10 y permanecen fuera de este cambio.

| Acceso | Último punto seguro / primera mutación relevante | Protección |
|---|---|---|
| Docker campaign, CLI y `execute_campaign` | Antes de adquirir GlobalGate desde CLI; antes de preflight de dataset, reconcile y resume desde el coordinador | `preflight_e10_schema()` |
| Claim secuencial común, también invocado por Local | Inicio de la transacción, antes de selección/locks de campaña y antes de INSERT en `train_execution_revisions`, attempts, runs y sessions | `require_e10_schema(c)` |
| Docker controlled, CLI y `execute_one` | Antes de GlobalGate desde CLI; después de consultar una petición ya existente y antes de los preflights que preceden la reserva | `preflight_e10_schema()` |
| `ControlledRepository.reserve` | Rama de petición nueva, antes de registrar `campaign_controlled_requests` y de crear attempt/run/session | `require_e10_schema(c)`; conserva el retorno idempotente de una reserva existente |
| Docker campaign resume | Antes de `reconcile` y `resume`, y nuevamente dentro de cada claim | Mismo guard; incompatibilidad se propaga sin entrar al manejador que pausa la campaña |
| Docker controlled recover | No tiene claim, reserva ni relanzamiento: reconcilia la reserva consumida | Se conserva; una recuperación histórica puede marcar interrupted sin consumir otro intento |
| Local prepare, ambos modos | Antes de leer/validar revisión y antes del preflight de dataset | `preflight_e10_schema()` |
| Local claim, ambos modos | Antes de crear el job; se repite dentro de la transacción, tras el retorno idempotente y antes del INSERT en `local_execution_jobs` y UPDATE del gate | `require_e10_schema(c)`; el claim/reserve común vuelve a comprobarlo |

El requisito de cero mutaciones ante incompatibilidad se aplica a los accesos
que preparan una **nueva reserva**. `recover` conserva su función de reconciliar
estados históricos, sin aumentar attempts, runs, sessions ni presupuesto. Una
petición nueva posterior a esa recuperación sí queda bloqueada en esquema viejo.

La excepción tipada se excluye del manejador genérico de fallos de campaña:
no causa pause, cambios en miembros ni eventos de fallo sistémico en la campaña.
El resto del manejo de errores conserva su comportamiento.

## 2. Guard y capacidades comprobadas

Nuevo módulo: `src/malaria_dl/execution/schema.py`, dentro de
`malaria_dl_local_project`.

`require_e10_schema(connection)` ejecuta exclusivamente SELECT. La fachada
`ExecutionRepository.preflight_e10_schema()` utiliza una transacción READ ONLY;
la comprobación interna utiliza la conexión de la propia reserva y tampoco
escribe. No importa Alembic ni ejecuta migraciones, DDL, stamping o reparaciones.

| Capacidad | Comprobación |
|---|---|
| Revisión instalada | `alembic_version` contiene exactamente `20260922_01`; metadata y ledger pertenecen al schema efectivo de la conexión |
| Columnas | `event_id uuid` y `event_sequence numeric` sin precisión restringida; ambas nullable para preservar filas legacy |
| Constraint | `train_event_metadata`, tipo CHECK, validado, definición canónica de E10, incluida identidad, secuencia entera finita positiva y formato del payload |
| Índices | `train_event_id_unique` y `train_event_sequence_unique`; únicos, válidos, ready e inmediatos; claves exactas y predicados parciales correspondientes |
| Trigger | `a_train_event_guard`, habilitado para origen, BEFORE INSERT por fila, sin condición ni argumentos |
| Función del trigger | `train_event_guard()` del mismo schema, PL/pgSQL, retorno trigger y search_path fijado al schema + pg_catalog; cuerpo correspondiente a la migración E10 |

La huella MD5 de `pg_proc.prosrc` es una comparación de definición, no una
credencial ni una garantía criptográfica de seguridad. Evita aceptar una función
sustituida por un `RETURN NEW` sin los guards de ownership, sesión activa y
secuencia contigua. La prueba instala la migración original y verifica la huella.

Una revisión desconocida, incluida una futura, falla de forma cerrada. Cambiar
la función o la representación canónica del constraint exige revisar este
contrato de compatibilidad. No se acepta una revisión posterior por comparación
lexicográfica. El guard informa las capacidades faltantes; los errores SQL de
inspección se sanitizan como `schema_inspection_failed`.

No se alteraron `preflight_result_events` del worker Docker ni la comprobación
`event-state` Local. Siguen siendo la segunda defensa. Una comprobación de lectura
no impide DDL administrativo posterior: se repite al reservar, pero no constituye
un bloqueo de migraciones concurrentes. No se cambiaron GlobalGate, heartbeat,
políticas de reintento, ResultService ni las configuraciones científicas.

`ExecutionRepository.standalone` permanece sin este guard; se comprobó su reserva
legacy sobre una fixture sin capacidades E10.

## 3. Pruebas nuevas y evidencia de presupuesto

Archivo: `tests/test_e10_preclaim_schema_postgres.py` — **32 passed**.

Se reutilizó el aislamiento `capstone_test_e4_<uuid>` con search_path al schema
sintético y pg_catalog, sin public como fallback. Las fixtures instalan las
migraciones existentes con Operations; crean únicamente la metadata estándar
Alembic dentro del schema de prueba. No hay tablas nuevas del producto ni DDL en
public. La fixture elimina su schema al finalizar.

### A. Esquema anterior: 20260915_01

Instalación de las migraciones existentes hasta Local, sin E10. Se prueban dos
rechazos consecutivos por acceso: claim común, reserve, campaign, resume,
execute_one, Local prepare y Local claim controlled/sequential.

| Evidencia | Antes | Después de cada rechazo |
|---|---:|---:|
| attempts | 0 | 0 |
| runs | 0 | 0 |
| sessions | 0 | 0 |
| jobs | 0 | 0 |
| Miembros y estado de campaña | Snapshot original | Idéntico |
| Presupuesto y ordinales | Contrato original; sin attempts | Idéntico |

Además de comparar filas completas, un listener SQL verifica **cero sentencias
INSERT/UPDATE/DELETE/CREATE/ALTER/DROP** durante esos accesos. Los launchers,
verificadores de dataset y loaders se sustituyen por funciones que fallarían si
se invocaran. Los tres accesos CLI rechazan antes de adquirir GlobalGate.

Hay 15 casos de daño parcial: revisión vieja/futura/ausente, columnas ausentes,
constraint ausente/no validado/permisivo, índices ausentes o con claves
incorrectas, trigger deshabilitado/ausente, search_path de función incorrecto y
función reemplazada. Todos rechazan sin alterar el snapshot de reservas.

### B. Esquema E10: 20260922_01

La migración original se instala sólo en el schema aislado. El preflight pasa
en una conexión independiente con `transaction_read_only=on`. La reserva real,
bajo el guard de ownership existente, crea un attempt, run y session; no invoca
TRAIN. El siguiente claim conserva el orden pending-first y el intento fallido.

Local controlled y sequential se prueban con una campaña que ya posee un intento
fallido. En esquema anterior, prepare y claim repetidos dejan todas las filas
intactas. Tras instalar E10 en ese schema, el claim crea exactamente un nuevo
attempt/run/session/job; la repetición devuelve el mismo resultado. Los ordinales
son `[1, 2]`, el primero sigue failed y el presupuesto congelado es idéntico.

También se cambia la revisión entre prepare y la transacción Local: el segundo
guard rechaza sin dejar job, run, session ni attempt. Controlled idempotente y
recover sobre esquema anterior conservan el número de intentos; una petición
nueva posterior es rechazada. Standalone legacy continúa funcionando.

## 4. Regresión ejecutada sin TRAIN

**621 casos distintos aprobados: 32 nuevos y 589 de regresión.** Las repeticiones
de OP1 durante el desarrollo no se suman. Un caso nuevo de standalone falló
inicialmente porque la fixture pasó un UUID en vez del texto requerido; se
corrigió exclusivamente el dato de prueba y el último pase de OP1 fue 32/32.

| Grupo | Resultado final | Cobertura |
|---|---:|---|
| Unitarios y arquitectura en `.venv-local-train` | 395 passed | Contratos, ResultService, reporters, emitter, journal, runtime Local, readers/hash, checkpoints, TrainingResults, arquitectura de completion y campañas |
| PostgreSQL, coordinación + persistencia + Local + journal | 166 regresiones passed | Campaign executor, controlled, Local claim/idempotencia/concurrencia, result repository, proyección TrainingResults, emitter/readers, HTTP, recuperación de journal |
| Reporter Docker y E10.10 sin cálculo | 16 passed | 13 reporter; 2 finalizaciones failed/interrupted y 1 completed/verified legacy |
| E10.7 sin cálculo | 12 passed | 2 guards de worker previos a ciencia y 10 comprobaciones de contexto/lineage |
| OP1 | 32 passed | Esquemas viejo/E10, daños parciales, accesos, presupuesto, CLI, recuperación y standalone |

El primer lote PostgreSQL informó `193 passed, 13 skipped, 9 deselected`:
193 incluye los 27 casos OP1 existentes entonces. Los 13 skipped eran el reporter
Docker por nombre de opt-in; se ejecutaron después con el opt-in correcto y
pasaron. Los nueve deselected excluyeron la expectativa histórica de revisión
public y pruebas que llaman TRAIN. El lote unitario excluyó un test de TRAIN.
Dos avisos de deprecación de protobuf no afectaron los resultados.

**Límite explícito:** no se ejecutó la regresión científica completa E10.7–E10.10:
las pruebas que llaman `train`, incluso con dobles de fit, y las pruebas de agente
nativo con cálculo quedaron excluidas para respetar «NO ejecutar TRAIN». Se
cubrieron esas etapas mediante sus contratos, persistencia, journal, guards y
finalización sin cálculo. No se afirma equivalencia numérica nueva ni un pase
completo de las suites científicas.

Reproducción de OP1 en el contenedor existente, usando una copia de trabajo en
`/tmp/e10_op1`:

```sh
PYTHONPATH=/tmp/e10_op1/malaria_dl_local_project:/tmp/e10_op1/backend_api \
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
RUN_E10_POSTGRES_TESTS=1 \
python -m pytest -q -p no:cacheprovider \
  malaria_dl_local_project/tests/test_e10_preclaim_schema_postgres.py
```

Los lotes PostgreSQL utilizaron los opt-ins `RUN_STAGE5_POSTGRES_TESTS`,
`RUN_STAGE93_CONTROLLED_POSTGRES_TESTS`, `RUN_LOCAL_EXECUTION_POSTGRES_TESTS`,
`RUN_E10_POSTGRES_TESTS`, `RUN_E10_EMITTER_POSTGRES_TESTS`,
`RUN_E10_HTTP_POSTGRES_TESTS`, `RUN_E10_LOCAL_JOURNAL_POSTGRES_TESTS` y
`RUN_E10_DOCKER_REPORTER_POSTGRES_TESTS`. Para E10.7 se seleccionaron únicamente
`test_worker_restart_rejected_before_science_or_new_emitter`,
`test_missing_migration_fails_before_science`,
`test_context_fields_come_from_reserved_session_and_lineage` y
`test_context_rejects_incoherent_lineage`. Para E10.10 sólo
`test_completion_boundary_architecture`,
`test_failure_paths_need_no_final_evaluation` y
`test_legacy_completion_and_verification_without_e10`.

`git diff --check`: aprobado.

## 5. Estado operativo de public: sólo SELECT

Lecturas de control: **2026-09-28 16:38:07 UTC** y **16:44:01 UTC**, con
REPEATABLE READ y `transaction_read_only=on`. Son agregados de todo public,
no sólo de la campaña individual auditada en PRE11.

| Dato | Primera lectura | Última lectura |
|---|---:|---:|
| Revisión Alembic | 20260915_01 | 20260915_01 |
| Campañas paused | 2 | 2 |
| attempts | 11 | 11 |
| runs | 99 | 99 |
| sessions | 11 | 11 |
| jobs existentes | 1 | 1 |
| Miembros failed / interrupted / pending / verified | 7 / 1 / 63 / 1 | 7 / 1 / 63 / 1 |
| Schemas sintéticos preexistentes | 9 | Los mismos 9 |

En ambas lecturas, el guard ejecutado directamente mediante SELECT devolvió:

```text
E10_SCHEMA_NOT_READY: alembic_revision_20260922_01, event_columns,
event_metadata_constraint, event_unique_indexes, event_trigger_guard
```

Las consultas fueron `SELECT version_num FROM public.alembic_version`, conteos de
las cuatro tablas, agrupaciones por state de campaigns/members y lecturas de
catálogos del guard. No se utilizó claim como sondeo, ni se lanzó preflight de
dataset operativo. Los nueve schemas preexistentes no se borraron; las fixtures
propias no dejaron schemas adicionales.

Public continúa **no preparado para reservar TRAIN E10**. Esta es la condición
que OP1 bloquea; aprobar el cambio no autoriza ni acredita la migración operativa.

## 6. Archivos modificados

Bajo `malaria_dl_local_project/`:

- `src/malaria_dl/execution/schema.py`: nuevo guard SELECT y error tipado.
- `src/malaria_dl/execution/repository.py`: fachada READ ONLY y guard de claim.
- `src/malaria_dl/execution/campaign.py`: entrada, resume y propagación sin pause.
- `src/malaria_dl/execution/controlled.py`: entrada y reserva nueva.
- `src/malaria_dl/local_execution/backend.py`: prepare y guard previo al job.
- `tests/test_e10_preclaim_schema_postgres.py`: 32 pruebas nuevas.
- `tests/e10_schema_fixture.py`: instalación E10 y metadata sólo en schema test.
- `tests/test_campaign_executor_postgres.py`, `tests/test_controlled_train_postgres.py`,
  `tests/test_result_repository_postgres.py`: fixtures de reservas adaptadas a E10.
- `tests/test_local_execution_postgres.py`, `tests/test_local_journal_postgres.py`:
  eliminación de la segunda instalación E10 ahora heredada de la fixture común.

Documento nuevo:
`docs/engineering/e10_execution_refactor/e10_op1_preclaim_schema_guard.md`.

Sin migraciones operativas, sin TRAIN, sin reanudación de campañas operativas,
sin E10.11. Trabajo detenido para revisión humana.

**APROBADO**
