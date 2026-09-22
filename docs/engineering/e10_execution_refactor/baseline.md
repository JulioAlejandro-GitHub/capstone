# E10.0 — Auditoría del estado actual de ejecución

Fecha: 2026-09-22. Base inspeccionada: `1cae4e30d8bee38405d4f066227737d13f9ef44c`.
Estado: **documentado para revisión humana; no constituye aprobación de E10.0 ni implementación de E10.1**.

## 1. Estado actual

Auditoría estática del código, SQL versionado, configuración, metadatos del VENV y tests existentes. No se consultó PostgreSQL, no se ejecutaron campañas, TRAIN, pytest, Alembic, servicios ni instalaciones. El árbol de trabajo estaba limpio al comenzar. El único archivo creado es este documento. Las conclusiones sobre persistencia describen las instrucciones del código y el esquema versionado; no certifican qué migraciones están instaladas ni el contenido de campañas productivas.

Convención de rutas para las referencias `archivo:Lx–Ly`:

- `M/` = `malaria_dl_local_project/`.
- `S/` = `malaria_dl_local_project/src/malaria_dl/`.
- `T/` = `malaria_dl_local_project/tests/`.
- `B/` = `backend_api/`.
- `A/` = `alembic/versions/`.

Los números corresponden al checkout indicado, no a numeración de documentos históricos. Se revisaron también adaptadores `M/src/train.py`, `M/src/metrics.py`, `M/src/run_tracker.py` y `M/src/tracking_integration.py`: el nombre histórico de un módulo no identifica por sí solo su implementación actual.

Hallazgos principales:

1. Docker y Local llaman **la misma función** `S/execution/train.py:25`, con el mismo registry/adapters/configuración resuelta. Docker entrega `ExecutionRepository`; Local entrega `Reports`.
2. El TRAIN actual escribe los resultados incrementales en `train_execution_records`, y completion/verification en `train_execution_sessions`. No escribe salida científica en `runs.parameters`. En el esquema versionado, el INSERT actual deja ese campo con su default `{}`.
3. El cálculo de la matriz existe. Por época el callback descarta matriz, TP/TN/FP/FN y F1 al proyectar métricas a `logs`. Al final, **si hay calibración**, la matriz y conteos sí se persisten dentro de `calibration.payload.result.selected_metrics` y `default_threshold_metrics`. **Si no hay calibración**, sólo se guarda `{"enabled": false, "threshold": 0.5}` como result, más muestras y epoch en el envoltorio; una sesión puede quedar `verified` sin matriz persistida.
4. `runs.execution_parameters` ya recibe la configuración de entrada con dataset y entorno; `runs.configuration` tiene un escritor de inferencia, no del TRAIN actual. El uso pretendido de `parameters` como OUTPUT aún no está implementado.
5. El agente/worker Local no construye conexiones SQL. `local_execution/backend.py` sí usa SQL, pero es código del servidor FastAPI, no del proceso científico nativo.
6. Completion, verificación, estado de `runs`, estado del intento, aceptación del miembro y liberación global son conceptos distintos. Local y Docker no los ejecutan en el mismo momento ni con la misma frontera transaccional.

### Documentación anterior frente al código

| Documento | Afirmación anterior | Evidencia vigente y discrepancia |
|---|---|---|
| `docs/engineering/model_training_pipeline.md:186–203,263–298` | Entrypoint conduce a `training/trainer.py`, escribe tablas legacy y evalúa TEST al terminar TRAIN | `M/run_train_all_models.py:146–148` conduce a `execution/campaign.py`; `M/src/train.py:2–4` conduce a `training/cli.py::main:377–385`, que llama `execution/train.py::standalone`. TRAIN E5 sólo carga train/val y usa records. El diagrama anterior no describe estos entrypoints actuales. |
| `docs/engineering/model_training_pipeline.md:426` | No hay configuración JSON separada | Existen `M/configs/models/*.json`, registry y resolver `S/models/configuration.py`; las campañas congelan `campaign_configurations`. |
| `docs/engineering/model_training_decoupling_design_2026-09-09.md:415–454` | Propone `run_configuration_snapshots` | Es diseño histórico, no evidencia de la ruta ejecutada: `_create_run` usa `runs.execution_parameters.model_configuration_e2`. No se adopta esa propuesta en esta auditoría. |

El cuerpo legacy `S/training/trainer.py::main` sigue siendo código invocable por importación; no se lo declara eliminado. Es una ruta distinta de los dos entrypoints solicitados.

## 2. Diagrama Docker real

“Docker” aquí significa el coordinador/worker ejecutados dentro del backend Linux configurado por Compose; `run_train_all_models.py` no crea un contenedor. El contenedor ya aporta intérprete, filesystem y acceso DB (`B/Dockerfile:3,21–28,35–40`; `docker-compose.yml:20–36`).

```text
M/run_train_all_models.py::main [146–148]
    ↓ importa main con alias execute_campaign (NO build_matrix)
S/execution/campaign.py::main [294–323]
    ↓ ExecutionRepository(); GlobalGate('campaign') [298,315–316]
S/execution/campaign.py::execute_campaign [173–270]
    ↓ preflight [31–75] / technical_row si revisión explícita [188–190]
    ↓ opcional resume → reconcile → repository.resume [198–200]
S/execution/repository.py::ExecutionRepository.claim [43–127]
    ↓ lock campaña; elegir miembro; insertar intento [45–88]
    ↓ member_configuration(config, seed) [66]
    ↓ _create_run [129–169] → INSERT runs
    ↓ vincular intento; INSERT train_execution_sessions [101–120]
    ↓ session(run) [19–30], diccionario leído desde PostgreSQL
S/execution/campaign.py::run_child [120–170]
    ↓ Popen(sys.executable, -B, -m src.malaria_dl.execution.worker,
             --run-id, --owner) [137–153]
    ↓ registrar PID en gate; desbloquear pipe; wait [154–157]
S/execution/worker.py::main [13–67]
    ↓ attach_worker [14–15]; ExecutionRepository [20]
    ↓ repo.session(run_id), owner/state guard, child_started [22–25]
    ↓ SQL para campaign_id; effective_row; member_configuration [28–47]
    ↓ comparar configuration/dataset/environment; preflight [48–54]
S/models/registry.py::resolve_descriptor [67–74]
    ↓
S/execution/train.py::train [25–257]
    ↓ llamada exacta en worker.py:62:
      train(repo, session, resolve_descriptor(session["configuration"]["model_id"]))
    ↓ repository.put(...) por etapa/época; repository.records(run)
    ↓ repository.finish(run, owner, "completed", completion) [257]
    ↓ worker retorna 0; proceso termina; padre wait/after_wait
S/execution/campaign.py::execute_campaign [223–244]
    ↓ exige exit 0 Y session.state == completed
    ↓ gate.require_healthy; preflight; verify_session [238–241]
S/execution/artifacts.py::verify_session [20–89]
    ↓ isolated_keras_loader cuando hay gate y loader por defecto
S/execution/process_verification.py::isolated_keras_loader [10–38]
    ↓ subprocess propietario → artifacts.py::keras_loader [92–103]
    ↓ hash/tamaño, carga, contrato input/output, evidencias verificadas
S/execution/repository.py::finish(..., "verified", evidence) [222–265]
    ↓ session.verification; attempt.state=verified; runs.status=completed
A/20260912_01_train_execution.py::campaign_attempt_state [64–71]
    ↓ member.state=verified; accepted_attempt_id=primer intento verified
S/execution/campaign.py::execute_campaign [265–270]
    ↓ finalize_terminal; summary; retorno 0/2; error sistémico pausa y retorna 3
S/execution/global_gate.py::GlobalGate.__exit__/close [265–297]
    ↓ prueba de procesos retenida y liberación del advisory lock
```

`claim` prioriza `pending`, luego `failed/interrupted`, ordena por posición y respeta `max_attempts_per_member` (`repository.py:51–56`). No hay un método `reserve` en este recorrido normal: ese nombre corresponde a `ControlledRepository.reserve` (`controlled.py:90–112`). La variante controlada usa `execute_one:197–239`, reserva un único intento de una campaña pausada y reutiliza `run_child`, verificación y `finish`; no reanuda la cola.

`session` **no es una sesión SQLAlchemy**: es `dict(row)` de `train_execution_sessions`. La conexión se construye mediante `CampaignRepository.transaction` → `connection_scope` → `persistence.database.get_engine` (`campaigns/repository.py:20–53`, `persistence/database.py:51–63`). Las transacciones propagan `capstone.execution_token`; `put/finish` además configuran `capstone.train_owner`.

El subprocess recibe IDs, token de gate y descriptor de pipe; no recibe configuración científica por argumentos. `attach_worker` valida el arranque y propiedad (`global_gate.py:299–319`). El worker vuelve a leer y contrastar la identidad congelada antes de entrenar.

Cierre anómalo: exit distinto de cero o ausencia de completed no equivale a éxito. Si aún está active, el padre escribe failed con causa `CHILD_EXIT_<code>` o `CHILD_EXIT_0_INCOMPLETE_RESULTS` (`campaign.py:224–236`); SIGINT/SIGTERM del padre termina y espera al grupo hijo y registra interrupted (`run_child:159–170`, `execute_campaign:245–252`). `reconcile:94–117` sólo interrumpe active tras probar ausencia del propietario y del hijo; una sesión completed se verifica, no se vuelve a entrenar. La campaña puede finalizar operativamente sin matriz completa: `finalize_terminal` excluye pending/active/completed; el retorno 2 señala matriz no totalmente verified.

## 3. Diagrama Local real

El agente no recibe un job previamente creado: `start` solicita la reserva por HTTP. La precondición es campaña/revisión registradas y roots configurados, no una nueva definición de modelos.

```text
S/local_execution/agent.py::main [10–58]
    ↓ leer config y bearer; persistir request_id antes de claim [13–14,30–32]
S/local_execution/transport.py::Api.call('claim', request) [16–27]
    ↓ POST <base>/execution/local/claim, JSON y Bearer
B/app/routes/local_execution.py::local_operation [19–31]
    ↓ service [10–16]: LocalBackend(ControlledRepository(), roots)
S/local_execution/backend.py::LocalBackend.claim [70–120]
    ↓ prepare [50–62] + preflight [28–35]; manifiesto train/val [79–85]
    ↓ advisory xact lock (120994,1) + fila gate FOR UPDATE [86–100]
    ↓ INSERT local_execution_jobs held + asignar gate/token [101–104]
    ↓ bound(c): mismo transaction scope con savepoints [37–42]
S/execution/controlled.py::ControlledRepository.reserve [90–112] (controlled)
    o S/execution/repository.py::ExecutionRepository.claim [43–127] (sequential)
    ↓ runs + attempt + session en backend; conservar owner interno
S/local_execution/backend.py::claim [110–120]
    ↓ session pública: UUID/timestamps a string; owner=token remoto
    ↓ dataset/artifact paths → {root_id, relative_path}
    ↓ guardar session interna/result en job; devolver job + manifiesto
S/local_execution/agent.py::main [33–47]
    ↓ verify_samples; subprocess.Popen([sys.executable,'-B','-m',
          'src.malaria_dl.local_execution.worker'], stdin=PIPE, start_new_session=True)
    ↓ ProcessTracker(pid); primer heartbeat aceptado [36–39]
    ↓ thread heartbeat cada 15 s; entregar job por stdin sólo después [40–47]
S/local_execution/worker.py::main [8–19]
    ↓ leer stdin; Api; verify_samples; resolver roots locales [10–16]
    ↓ llamada exacta [19]:
      train(Reports(api,job,artifact_root),session,
            resolve_descriptor(session['configuration']['model_id']))
S/execution/train.py::train [25–257]
    ↓ mismo build/fit/VAL/checkpoints/calibración
S/local_execution/transport.py::Reports.put / records / finish [37–56]
    ↓ POST record / records / calculation-ended
B/app/routes/local_execution.py::local_operation [25–26]
    ↓
S/local_execution/backend.py::operation [122–168]
    ↓ record: traducir path a backend, verificar hash → repo.put [143–150]
    ↓ records: repo.records [130–131]
    ↓ calculation-ended: job.completion + state=calculation_reported [151–153]
    ↓ NO finish de session y NO liberación aquí
S/local_execution/agent.py::main [48–56]
    ↓ esperar subprocess; detener heartbeat; guardar exit_proof
    ↓ POST exit con prueba de ausencia/exit code
S/local_execution/backend.py::operation('exit') [154–167]
    ↓ comprobar identidad y ausencia de procesos observados
    ↓ exit 0 + completion → repo.finish(completed)
    ↓ verify_session(repo, repo.session(rid), self.loader)
    ↓ load_checkpoint [21–26] en subprocess Python DEL BACKEND
    ↓ repo.finish(verified); job=released; limpiar gate
    ↓ fallo de hijo → finish(failed), pause(campaign), job=failed, gate bloqueado
S/local_execution/agent.py::main [53–56]
    ↓ sólo encadena en sequential, con code 0, sin pérdida de heartbeat,
      sin stop y con released confirmado; nuevo request_id y archivo state
```

### Contrato operativo y diferencias de cierre

`Reports.put` valida run/owner y transforma el path de artefacto local a referencia relativa. El backend valida root, prefijo de run, confinamiento y SHA256/tamaño del archivo compartido. **No se suben bytes del checkpoint por HTTP** (`transport.py:37–46`, `backend.py:143–150`). `Reports.records` lee los registros ya canonicalizados en servidor; por eso el hash de completion usa los paths del backend y el orden de DB, no una lista local divergente.

`Reports.finish` sólo admite completed, transmite evidence y no transmite una mutación arbitraria del estado de sesión (`transport.py:52–56`). `operation('exit')` hace completed, verificación, verified y liberación dentro de la transacción exterior del backend y savepoints del repositorio. Si falla la verificación, esa operación revierte: el job y gate previos siguen retenidos; no se confirma released. Docker ya había hecho commit de completed en el hijo antes de verificar en el padre.

Heartbeat: `agent.py:41–45` cada 15 segundos; `backend.py:127–142` actualiza `heartbeat_at`, fija/verifica identidad de proceso y reporta `uncertain` después de 60 segundos. **La expiración no libera ni reemplaza el job**. La identidad usa PID+create_time+host+platform (`processes.py:10–19`). `exit_proof:30–34` acredita sólo descendientes observados; el propio payload declara que no acredita hijos escapados no observados. Backend valida la prueba recibida, no inspecciona remotamente el sistema operativo del Mac.

`status/reconcile` (`agent.py:16–19`) consulta state o reenvía la prueba de salida persistida. `Api.call` limita a 8 MiB por request, 15 s por intento, tres intentos con espera 1/2 s; errores <500 se rechazan sin reintento (`transport.py:10–27`). El archivo de estado del agente es un control operativo de request/job/exit, no una alternativa de resultados científicos a PostgreSQL.

`LocalBackend.operation('exit')` no llama `finalize_terminal`; una cola Local agotada llega a `NO_ELIGIBLE_MEMBER` en claim (`backend.py:109`) en vez del cierre normal de campaña de Docker. Ésta es una diferencia de código, no una afirmación de que una campaña concreta esté actualmente afectada.

### Evidencia de ausencia de SQL directo en agente/worker

Se inspeccionaron imports y llamadas de `agent.py`, `worker.py`, `transport.py`, `processes.py`, `storage.py`, y la rama efectivamente invocada `execution/train.py::train` con registry/adapters, loaders y métricas. No llaman `get_engine`, `create_engine`, `connect`, repositorios SQL ni ejecutan SQL. `Api` usa `urllib.request.urlopen`. `train` sólo llama los métodos del objeto recibido. Los imports DB en **el mismo archivo** `execution/train.py:270–278` están dentro de `_standalone`, que el worker Local no llama. `campaigns/contracts.py` aporta JSON/hash/errores sin crear conexión.

No se extiende esta afirmación a todo `local_execution/`: `backend.py:8,44–166` contiene SQL explícito, invocado por FastAPI. Tampoco se afirma una barrera de sandbox/red: el VENV local incluye SQLAlchemy/psycopg y el hijo hereda el entorno del agente. La prueba es del camino de código actual, no una prohibición a nivel OS ni una traza de red ejecutada.

## 4. Firma actual de train()

Fuente literal `S/execution/train.py:25`:

```python
def train(repository, session, descriptor):
```

Sin anotaciones, defaults ni valor de retorno explícito; retorna `None` si concluye. No se propone aquí una firma nueva.

| Parámetro | Uso real | Dependencia |
|---|---|---|
| `repository` | `put(run, owner, kind, phase, key, clean(payload))` (90–91); `records(run)` (244); `finish(run, owner, 'completed', completion)` (257) | Interfaz implícita de escritura, lectura y cierre. Docker: `ExecutionRepository`; Local: `Reports`. No recibe engine/connection directamente. |
| `session` | `run_id`, `owner`, `configuration.resolved`, `dataset.dataset_root`, `artifact_root` (43–60); configuración execution/selection/model/recipe | Snapshot dict del backend/repositorio, con rutas resueltas por el worker Local. No es session ORM. Otros campos de la fila sirven a orquestación/verificación aunque no los lea train. |
| `descriptor` | `descriptor.create_adapter()` y `adapter.build(resolved)` (75–77) | `ModelDescriptor` del registry (registry.py:10–31,67–74); arquitectura y fases compartidas. |

| Responsabilidad | Implementación actual |
|---|---|
| Quién conoce `ExecutionRepository` | `execution/repository.py:10`; `execution/campaign.py:20,298`; `execution/worker.py:10,20`; `execution/train.py::_standalone:274,278`; `execution/controlled.py:13,39`; consumidores `assessment/lineage.py:16,45`, `science/comparison.py:13,68`. FastAPI construye la subclase ControlledRepository. La función train no importa esa clase. |
| Quién llama `put` | Closure `train.put:90` → repository; `PersistEpoch.on_epoch_end:106–157`; bucle runtime/phase 190/198; calibración 231. Reports.put → backend.operation('record') → ExecutionRepository.put. |
| Quién llama `finish` | train:257; standalone:307,311; campaign.reconcile:108,112; execute_campaign:226,242,246,257; controlled.recover:131,135 y execute_one:228,233,237; backend.operation('exit'):158,160,162. `Reports.finish` difiere el cierre SQL. |
| Artefactos binarios | `PersistEpoch.on_epoch_end:115–138`: save `.partial.keras`, comprobar no existencia final, `os.rename`, hash/tamaño, UUID `version_id`. Un checkpoint exclusivo por epoch global. No INSERT en tabla legacy `artifacts` en este camino. |
| Métricas | `models/adapters.py::compile_phase:92–142` → `architectures.py::compile_binary_model:153–176`; Keras fit; `ClinicalValidationMetricsCallback.on_epoch_end:520–592`; funciones `evaluation/clinical_metrics.py`. |
| Predicciones | `clinical_metrics.py::collect_predictions:430–464`; callback clínico, PersistEpoch (train:140), checkpoint seleccionado (train:219). Las invocaciones por época están duplicadas computacionalmente, aunque el código científico es común a ambos ejecutores. |
| Calibración | `threshold_calibration.find_threshold_for_target_recall:154–272`, llamada en train:220–230, sólo con VAL del checkpoint seleccionado. No es ajuste de Platt/isotonic en este camino. |
| Selección/checkpoint | `training/checkpoint_policy.py::select_best_epoch_from_history:319`, `select_best_epoch_by_monitor:422`, `_selection_result:225`; train:108–138,215–219. Selección sobre history acumulada entre fases; posteriormente carga el checkpoint de la epoch seleccionada. |

El acoplamiento no se limita a `put`: train lee la evidencia persistida para calcular `records_hash` y ordena completion. Además decide almacenamiento físico y formato Keras. `clean:11–22` convierte escalares NumPy y floats no finitos a JSON seguro (no finitos → null); `canonical` normaliza números enteros representados como float para hash/JSON (`campaigns/contracts.py:14–42`).

## 5. Persistencia actual: inventario de escrituras

### 5.1 Camino vigente E5/E9 y Local

“Ambos” significa SQL en Docker coordinador/worker o SQL en backend para un TRAIN Local. Nunca significa SQL desde el Mac agente. Se incluyen efectos de triggers, porque sin ellos el inventario de estados sería incompleto.

| Archivo | Función/líneas | Tabla/campo | Momento | Contenido | Docker/Local/ambos |
|---|---|---|---|---|---|
| `S/campaigns/repository.py` | `freeze:210–255`, INSERT 234 | `campaign_members` | Congelación previa | id,campaign_id,configuration_hash,seed,position,state pending/excluded,exclusion_reason | Ambos, dominio común |
| `S/execution/repository.py` | `claim:43–127`, INSERT 84 | `campaign_attempts` | Claim secuencial | id,member_id,ordinal,state active; timestamps default | Ambos |
| `S/execution/repository.py` | `_create_run:129–169`, INSERT 153 | `runs` | Antes de session/fit | id,model_id,experiment_id,run_type training,status running,random_seed,dataset_version_id,execution_parameters; campaign_id si corresponde | Ambos |
| `S/execution/repository.py` | `claim:101–106` | `campaign_attempts.training_run_id` | Tras crear run | UUID canónico del run | Ambos |
| `S/execution/repository.py` | `claim:107–120` | `train_execution_sessions` | Reserva | run/attempt/owner/host/parent_pid/configuration/dataset/environment/artifact_root; state active por default | Ambos |
| `S/execution/controlled.py` | `reserve:103–110` | `campaign_attempts`, `runs`, `train_execution_sessions` | Intento controlado | INSERT intento; `_create_run`; UPDATE training_run_id; INSERT session, con entorno de revisión | Ambos |
| `S/execution/repository.py` | `standalone:356–375` | `runs`, `train_execution_sessions` | CLI individual | `_create_run` sin campaña; session sin attempt_id, parent_pid=child_pid | Docker/CLI DB, no agente Local |
| `S/execution/repository.py` | `child_started:210–220` | `train_execution_sessions.child_pid,updated_at` | Inicio worker | PID; exige campo NULL | Docker; Local guarda PID en job |
| `S/execution/repository.py` | `put:171–208` | `train_execution_records` | Cada reporte | run_id,kind,phase,record_key string,payload JSON; created_at default | Ambos |
| `S/execution/repository.py` | `finish:243–251` | `train_execution_sessions.state,completion/verification,cause,updated_at` | Cierre/validación/error | evidence en completion salvo verified que escribe verification | Ambos; Local sólo en exit |
| `S/execution/repository.py` | `finish:252–259` | `campaign_attempts.state,cause,finished_at` | Cierre con attempt_id | Mismo state; reloj DB | Ambos |
| `S/execution/repository.py` | `finish:260–265` | `runs.status,finished_at` | Cada finish | completed para completed/verified; failed/interrupted según caso | Ambos |
| `A/20260912_01_train_execution.py` | `campaign_attempt_state:64–71` | `campaign_members.state,accepted_attempt_id` | Trigger de INSERT/UPDATE intento | Estado nuevo; primer intento verified por ordinal o NULL | Ambos |
| `S/campaigns/repository.py` | `create_attempt:279–309`; `update_attempt:311–339` | `campaign_attempts` | API de dominio E4 alternativa | Crear active; asociar run y actualizar state/cause/finished_at | Dominio común; no llamada del train actual |

`runs.parameters`: **ninguna escritura explícita** en este camino. `runs.configuration`: **ninguna**. `runs.execution_parameters` se inserta una vez en `_create_run`; no se mezcla con resultados al finalizar. El parámetro SQL llamado `parameters` en `_create_run:163` **se liga a la columna execution_parameters**, no a `runs.parameters`.

Columnas de `runs` omitidas por `_create_run` incluyen `started_at`, `duration_seconds`, `execution_type`, progreso/selección (`completed_epochs`, `best_epoch`, etc.), `run_name`, y campos explícitos de entorno (`python_version`, `tensorflow_version`, `keras_version`, host, etc.). `finish` no las rellena. No debe confundirse “preservadas en el esquema” con “pobladas por todos los caminos”. `started_at` en `M/db/init/001_schema.sql:69` no tiene default; la sesión sí tiene `started_at` default (`A/20260912_01_train_execution.py:17`). Este informe no atribuye valores a filas históricas sin consultarlas.

### 5.2 Escrituras auxiliares que condicionan los resultados

| Archivo | Función | Tabla/campo | Momento/contenido | Ejecutor |
|---|---|---|---|---|
| `S/execution/repository.py:74–76` | claim con revisión | `train_execution_revisions` | Binding attempt/campaign/revision | Ambos secuenciales |
| `S/execution/controlled.py:44–54,104` | register_revision/reserve | `campaign_technical_revisions`, `campaign_controlled_requests` | Evidencia explícita de revisión; request idempotente y binding de run/attempt | Ambos |
| `S/execution/repository.py:122–125,267–289,377–390` | claim/pause/resume/finalize_terminal | `experimental_campaigns`, `campaign_execution_events` | active/paused/finalized y causa de pausa | Ambos repositorios; finalizar cola sólo Docker |
| `S/local_execution/backend.py:102–119` | claim | `local_execution_jobs`, `experiment_execution_gate` | held, owners, request hash, session interna, respuesta pública y reserva global | Backend para Local |
| `S/local_execution/backend.py:141,153,165–166` | operation | `local_execution_jobs`, gate | heartbeat/process; calculation_reported/completion; exit proof/result/released o failed; liberar owner y posible blocked_reason | Backend para Local |
| `S/execution/global_gate.py:147–192,215–286` | event, enter, child_started, after_wait, outcome, close | `experiment_execution_gate`, `experiment_execution_events` | ownership DB/procesos, recursos, OOM/fallos, evidencia de ausencia | Docker |
| `S/persistence/dataset_evidence.py:87–152` | verify_dataset_for_execution | Evidencia de dataset en auditoría | Preflight puede persistir acreditación; por eso no se lo ejecutó durante esta auditoría | Docker/backend Local |

`put` es idempotente por `(run_id,kind,phase,record_key)`: contenido igual retorna sin INSERT, distinto lanza `RESULT_IDEMPOTENCY_CONFLICT`. El trigger `train_record_guard` prohíbe UPDATE/DELETE y exige owner/sesión active (`A/20260912_01_train_execution.py:32–41`). `kind` es texto libre, **no un enum ni CHECK de vocabulario** (`:22–26`).

`train_session_guard` mantiene identidad inmutable y permite active→completed/failed/interrupted y completed→verified; no admite completed→failed (`:42–63`). `campaign_attempt_guard` vigente se reemplaza en `A/20260914_02_global_execution.py:63–103`; incorpora binding técnico y mismo orden de estados. `experiment_require_owner` se reemplaza en `A/20260915_01_local_execution.py:20–28` para aceptar lock Docker o job Local retenido. Estos triggers son reglas de autorización/validación; no consolidan métricas en `runs.parameters`.

### 5.3 Otros escritores presentes: legacy, linaje y lifecycle

La búsqueda cubrió fuentes ML/backend, scripts, SQL inicial y migraciones; se separan las rutas invocables de los ejemplos, fixtures y copias de auditorías. “Legacy” no significa borrado: no se llega a ellos desde `execution/train.py::train`.

| Archivo | Función/líneas | Tabla/campo | Momento | Contenido | Docker/Local/ambos |
|---|---|---|---|---|---|
| `S/persistence/run_repository.py` | `start_run:340–435` | `runs`, incluido parameters y execution_parameters | Inicio tracking legacy | INPUT recibido; entorno recolectado; status started; started_at NOW; columnas detalladas abajo | Llamador DB/legacy, no Reports |
| `S/persistence/run_repository.py` | `update_run_execution:438–534` | `runs.execution_parameters` y columnas de ejecución | Progreso/cambio fase/cierre legacy | Merge JSONB y COALESCE de opciones, completed_epochs creciente | Legacy |
| `S/persistence/run_repository.py` | `log_training_history:717–791` | `training_history`; `runs.completed_epochs,updated_at` | Época legacy | CTE inserta history y actualiza máximo epoch+1 | Legacy |
| `S/persistence/run_repository.py` | `finish_run:537–622` | `runs.status,finished_at,duration_seconds,updated_at,metadata`, campos de selección | Fin legacy | completed, tiempos, metadata merge; opcional log_metrics_bulk a run_metrics | Legacy |
| `S/persistence/run_repository.py` | `fail_run:625–650` | `runs.status,finished_at,duration_seconds,updated_at,metadata` | Error legacy | failed y error log separado | Legacy |
| `S/persistence/model_configuration.py` | `persist_model_configuration:67–110` | `runs.execution_parameters.model_configuration_e2` | Pre-fit legacy | configuration,runtime,dataset,execution,environment; verifica readback | Legacy |
| `S/persistence/dataset_evidence.py` | `bind_dataset_evidence_to_run:155–180` | `runs.metadata` | Vínculo de evidencia legacy | dataset_verification_evidence_id; condicionado al mismo dataset | Legacy |
| `S/persistence/lineage.py` | `_attach_source_training_metadata:647–664`; `mark_lineage_unresolved:735–773` | `runs.metadata` del hijo | Linaje posterior a TRAIN | source training/advertencia; no salida del padre TRAIN | Consumidores DB |
| `S/persistence/training_release.py` | `set_training_release_status:265`, SQL `_UPDATE_RELEASE:134–145` | `runs.release_status,release_updated_at,release_changed_by,release_reason` del TRAIN | Lifecycle posterior | Estado de publicación/gobernanza con control de transición | Servicios DB; fuera de cierre train actual |
| `S/evaluation/evaluation_finalization_service.py` | SQL `_UPDATE_EVALUATION_COMPLETED:113–136`, `_UPDATE_EVALUATION_FAILED:139–154` | runs de tipo evaluation | Fin evaluación relacionada | status,tiempos,metadata; NO parameters ni fila training | Servicios DB; fuera de TRAIN |
| `S/governance/repository.py` | `create_inference_run:655–742`, INSERT 707 | `runs.configuration` y `runs.parameters` | Inferencia | mismo JSON configuration en ambas columnas; run_type inference | Backend; no TRAIN |
| `S/inference/traceable.py:104–107` | Flujo de inferencia | runs status/finished_at/error_message | Resultado inferencia | completed/failed | Backend; no TRAIN |
| `M/db/init/019_model_execution_parameters.sql:22–29` | SQL histórico | `runs.execution_parameters,completed_epochs` | Bootstrap/backfill | Copia parameters si execution_parameters es NULL; inicializa epochs nulos | Migración, no ejecución |
| `A/20260829_01_persist_training_release_status.py:181–193` | upgrade | `runs.release_*` del TRAIN | Backfill histórico | Deriva estado de release | Migración; no ejecución |

Columnas explícitas del INSERT legacy `start_run:375–400`: experiment_id,model_id,dataset_id,run_name,run_type,status,command,script_name,started_at,user_name,host_name,working_directory,git_commit,git_branch,python_version,tensorflow_version,keras_version,platform,machine,processor,gpu_available,gpu_devices,random_seed,parameters,notes,metadata,execution_type,execution_parameters,fine_tuning_start_epoch,total_epochs,completed_epochs,max_epochs,stopped_epoch,best_epoch,checkpoint_monitor,checkpoint_mode,best_validation_value,early_stopping_enabled,early_stopping_patience,early_stopping_min_delta,restore_best_weights,dataset_version_id.

`update_run_execution:463–512` modifica execution_type/execution_parameters, fine_tuning_start_epoch, total_epochs, completed_epochs, max_epochs, stopped_epoch, best_epoch, checkpoint_monitor/mode, best_validation_value, early_stopping_enabled/patience/min_delta, restore_best_weights, updated_at. `finish_run:559–600` puede modificar esos campos de resumen de early stopping/selección, pero no parameters ni execution_type; `finish_tracking_run:779–852` puede llamar primero a update_execution_tracking para completar execution_parameters.

El producer legacy de TRAIN es `training/trainer.py::main:926` → `tracking.start_tracking_run:494` (llamada trainer:1048), actualizaciones de ejecución/fase (trainer:1378,1551), métricas finales y `finish_tracking_run` (trainer:2167). El writer de matriz legacy es `tracking.log_metrics_and_reports:868–926` → `run_repository.log_confusion_matrix:794`; escribe `confusion_matrices`, no `runs.parameters`. Los wrappers `record_clinical_metrics:1230`, `record_checkpoint_policy:1257`, `record_threshold_calibration:1271` delegan a sus tablas legacy. Ninguna de esas llamadas existe en el train E5.

Los scripts de purga/mantenimiento y los fixtures no son productores de resultados del recorrido TRAIN: pueden borrar o fabricar datos explícitamente, pero no son alcanzados por los entrypoints auditados. No se ejecutaron. Tampoco las copias `.py.txt` en `docs/audits` definen runtime.

## 6. Auditoría de runs.parameters

### Quién lo escribe y qué significa hoy

| Contexto | Productor | Cuándo/estructura |
|---|---|---|
| TRAIN Docker E5, Local y standalone E5 | Ningún writer explícito de parameters; `_create_run:153–168` omite columna | Default `{}` del esquema (`M/db/init/001_schema.sql:86`), tanto antes como después de completed/verified. No hay consolidación científica. |
| Tracking legacy, también reutilizado por evaluation/calibration/inference | `tracking.start_tracking_run:520–525,630` → `run_repository.start_run:375–414` | Al inicio: argumentos/parameters proporcionados, enriquecidos con label_mapping_version,label_mapping,raw_model_score_meaning. Es INPUT histórico, no resumen de salida. |
| Inferencia gobernada | `governance/repository.py::create_inference_run:707–717` | Copia configuration a parameters. No es un productor TRAIN. |

No se encontró `UPDATE runs SET parameters=...` en las fuentes productivas inspeccionadas. Por tanto hay más de un productor general de la columna, pero **no dos consolidadores de resultados TRAIN Docker/Local**. La función genérica `start_run` también se puede llamar directamente sin `start_tracking_run`.

Ejemplos reales, sin valores inventados:

- Default SQL para el TRAIN E5 (no es lectura de un run productivo):

```json
{}
```

- Fixture de `T/test_model_execution_tracking.py:164–168`, argumento exacto `parameters` a `run_tracker.start_run(run_type='training', ...)`:

```json
{"epochs": 2}
```

El mismo test usa, por separado, `execution_parameters={"epochs": 2, "batch_size": 32}`. No son resultados clínicos. El constructor exacto del enriquecimiento legacy (`tracking.py:520–525`) es:

```python
run_parameters = {
    **(parameters if parameters is not None else args_to_parameters(args)),
    "label_mapping_version": LABEL_MAPPING_VERSION,
    "label_mapping": LABEL_MAPPING_METADATA,
    "raw_model_score_meaning": RAW_MODEL_SCORE_MEANING,
}
```

Docker/Local E5 tienen el mismo comportamiento de **ausencia de output en parameters** y el mismo default según DDL. Esto no acredita igualdad numérica ni JSON byte a byte de todos los resultados: paths, UUIDs, timestamps, entorno y entrenamiento pueden diferir. Sin consultar BD no se afirma que todos los runs existentes contengan `{}`.

### Campos científicos solicitados

| Campo | ¿Se escribe como OUTPUT en runs.parameters por TRAIN actual? | Evidencia persistida alternativa |
|---|---|---|
| threshold | No | calibration.result.threshold si deshabilitada; threshold_selected/threshold_used si habilitada; policy en selection/configuración |
| TP/TN/FP/FN | No | Sólo calibration.result.selected_metrics/default_threshold_metrics cuando calibrate_threshold=true |
| recall | No | epoch logs de TRAIN/VAL; selection/completion; calibration opcional |
| specificity | No | epoch logs de TRAIN/VAL; selection/completion; calibration opcional |
| precision | No | Keras `precision`/`val_precision` en epoch; precision_parasitized en calibration opcional |
| F1 | No | calibration opcional; no proyección por época |
| F2 | No | `val_f2_parasitized` en epoch/selection/completion; calibration opcional |
| balanced accuracy | No | epoch TRAIN/VAL, selection/completion; calibration opcional |
| ROC-AUC | No | Keras auc/val_auc y callback val_roc_auc_parasitized; calibration opcional |
| PR-AUC | No | Keras pr_auc/val_pr_auc y callback val_pr_auc_parasitized; calibration opcional |
| loss | No | epoch loss/val_loss; selected_metrics de selection puede incluir val_loss; configuración de loss en runtime es descripción, no valor de pérdida |

Un argumento de entrada denominado threshold que llegue al tracking legacy no equivale a persistir el umbral clínico calculado al cierre. Los puntos exactos de descarte se detallan en §8.

`execution_parameters` del TRAIN actual se construye literalmente (`repository.py:146–168`) con `model_configuration_e2={configuration,dataset,environment}` y `dataset_verification_evidence_id`. La rama legacy `persist_model_configuration` agrega además runtime/execution dentro de ese snapshot. No son esquemas idénticos aunque compartan el nombre de clave.

## 7. train_execution_records

El único INSERT productivo encontrado a esta tabla está en `ExecutionRepository.put:202`. El único producer científico actual del vocabulario es `execution/train.py`; Local transmite esos mismos tipos, y la API no restringe `kind` a una lista cerrada. Fixtures producen registros sintéticos, no tipos adicionales de producción.

| kind | Producer y línea | Payload | Cuándo ocurre | Consumidor |
|---|---|---|---|---|
| runtime | train:163,186–190 / compile_phase | phase,trainable_layers,optimizer,optimizer_class,loss,optimizer_state,input_contract,output_contract,architecture,compile,callbacks | Antes de fit de cada fase | verify_session comprueba presencia; hash de records |
| epoch | PersistEpoch:97–107 | logs Keras+callback limpios, epoch global, phase, phase_epoch, learning_rate | Final de cada epoch | History local para selección; verify_session secuencia/cantidad; hash |
| artifact_prepared | PersistEpoch:118–123 | path,epoch,run_id | Antes de model.save | verify_session exige presencia; evidencia de intento de guardado |
| artifact | PersistEpoch:128–137 | path,epoch,phase,phase_epoch,run_id,version_id,sha256,bytes | Después de renombrar checkpoint | verify_session identifica checkpoint seleccionado y valida archivo; lineage/assessment y comparación mediante verification |
| predictions | PersistEpoch:140–157 | role=val,epoch,samples[{sample,label,score}] | Cada epoch, inferencia adicional sobre VAL | verify_session comprueba cardinalidad/unicidad; evidencia por muestra; hash |
| selection | PersistEpoch:108–114,138 | `_selection_result`: policy,epoch seleccionada, selected_metric/value, threshold, selected_metrics, selected_record completo y flags | Cada epoch tras recalcular selección acumulada | completion.selection; verify_session compara última selection; summary/comparison |
| phase | train:198–213 | epochs,early_stopping[{stopped_epoch,best_epoch}] | Al volver fit de cada fase | verify_session espera base/fine_tuning y secuencia exacta |
| calibration | train:220–243 | result,checkpoint_epoch,samples[{sample,label,score}] | Después de cargar checkpoint seleccionado; siempre existe si TRAIN concluye | verify_session exige clave; assessment.lineage:54–84 valida vínculo epoch; threshold clínico; training_summaries:172–179,261–275 |

**No hay productores actuales de kind `evaluation`, `confusion_matrix` ni `metrics` en train_execution_records.** No se confunde esto con ausencia de métricas en payloads: existen dentro de epoch, selection y calibration. `assessment_results` y `assessment_attempts.verification`, y las tablas legacy `run_metrics`, `run_clinical_metrics`, `confusion_matrices`, son destinos diferentes. Como kind es texto libre y API acepta dict, la comprobación del código no permite asegurar que nadie haya insertado otro kind en una BD externa.

Orden persistido de lectura: `ORDER BY kind,phase,record_key` (`repository.py:38`), no cronológico. `record_key` es texto: el hash depende de ese orden concreto. Evidencia de completion = epochs, selection, records_hash, clinical_objective_met (`train:245–256`); no contiene todas las predicciones, la calibración ni una matriz agregada. `clinical_objective_met` se calcula a partir de **selection a threshold 0.5**, no selected_metrics de calibración.

## 8. Métricas y matriz de confusión

### Cálculo y persistencia real

`src.metrics` es un adaptador hacia `S/evaluation/clinical_metrics.py`. `compute_clinical_metrics:234–362` usa el orden `[uninfected, parasitized]`, negativo 0 y positivo 1. Matriz `[[TN, FP], [FN, TP]]`. `collect_predictions:430–464` acumula labels/scores y aplica convención de probabilidad clínica. La pérdida no la calcula esa función; procede de Keras fit con BinaryCrossentropy.

| Resultado | Función que calcula | Split en TRAIN actual | ¿Se persiste? | Destino actual |
|---|---|---|---|---|
| TP/TN/FP/FN | compute_clinical_metrics:261–262; también clinical_confusion_counts:127–143 y acumuladores custom Keras | VAL callback/calibración; Keras acumula TRAIN/VAL | No como conteos por epoch; sí si calibración habilitada | calibration.result.selected_metrics/default_threshold_metrics (`tn,fp,fn,tp` y aliases largos). Los weights internos del modelo no constituyen contrato JSON de conteos. |
| confusion_matrix | sklearn confusion_matrix en compute_clinical_metrics:261,329; también evaluate_binary_predictions | VAL | Sólo al calibrar en la ruta actual | Mismos subobjetos calibration; no tabla confusion_matrices del legacy |
| recall/sensitivity | compute_clinical_metrics:265,306–307; Keras Recall/ParasitizedRecall | TRAIN/VAL; calibración VAL | Sí | epoch recall/recall_parasitized y variantes val; selection; calibration opcional |
| specificity | compute_clinical_metrics:266,308; architectures.Specificity:68–117 | TRAIN/VAL; calibración VAL | Sí | epoch specificity/val_specificity; selection; calibration opcional |
| precision | sklearn precision_score:298–305; Keras Precision en compile_binary_model:167 | TRAIN/VAL; calibración VAL | Sí, métrica Keras por epoch; versión sklearn sólo calibración | epoch precision/val_precision; calibration.precision_parasitized |
| F1 | sklearn f1_score:309–316 | VAL | Sólo al calibrar | calibration.selected_metrics/default_threshold_metrics.f1_parasitized |
| F2 | sklearn fbeta_score(beta=2):317–324 | VAL | Sí | epoch.val_f2_parasitized, selection/completion; calibration opcional |
| balanced accuracy | (sensitivity+specificity)/2:328; architectures.BalancedAccuracy | TRAIN/VAL | Sí | epoch y selection; calibration opcional |
| ROC-AUC | `_safe_roc_auc:39–47` usa roc_auc_score; Keras AUC ROC:172 | TRAIN/VAL Keras; VAL sklearn | Sí cuando definida | epoch auc/val_auc y val_roc_auc_parasitized; selection; calibration. sklearn devuelve None si una sola clase. |
| PR-AUC | `_safe_pr_auc:50–58` usa average_precision_score; Keras AUC PR:173 | TRAIN/VAL Keras; VAL sklearn | Sí cuando definida | epoch pr_auc/val_pr_auc y val_pr_auc_parasitized; calibration. AP de sklearn y AUC PR de Keras son nombres/cálculos distintos; no tratarlos como idénticos. |
| threshold fijo/clínico | policy threshold=0.5 (train:78–85); find_threshold_for_target_recall:154–272 | VAL | Sí | calibration.result (fijo o calibrado), selection policy/config |
| loss | compile_binary_model:161–164, model.fit | TRAIN/VAL | Sí por epoch | epoch.loss/val_loss; selection.selected_metrics.val_loss cuando disponible. No loss recalculada al threshold calibrado. |

### Cadena causal de una ejecución exitosa sin matriz persistida

1. `ClinicalValidationMetricsCallback.on_epoch_end` calcula `clinical_metrics` completo (`checkpoint_policy.py:528–532`), incluyendo conteos/matriz/F1.
2. Su `metric_updates` sólo copia F2, PR/ROC-AUC, recall/sensitivity, specificity, balanced_accuracy y diagnóstico de colapso (`:548–570`). No copia TP/TN/FP/FN, matriz, F1 ni precision_parasitized. Keras ya aporta `precision/val_precision`, de modo que no sería correcto afirmar que toda precisión desaparece.
3. `PersistEpoch` recibe sólo `logs`; escribe ese dict, no `clinical_metrics` (`train.py:97–107`). `_selected_metrics` proyecta un subconjunto, pero `_selection_result` también conserva `selected_record` completo: son los logs de la época seleccionada, no el dict clínico previo al descarte (`checkpoint_policy.py:205–268`).
4. Se conserva evidencia por muestra, pero `train()` no llama `compute_clinical_metrics` para generar un resumen final independiente. Si `calibrate_threshold` es false, no llama a `find_threshold_for_target_recall` y usa el literal mínimo de train:229.
5. `verify_session` comprueba existencia del registro calibration pero no exige `result.selected_metrics`, matriz, conteos o F1 (`artifacts.py:34–35`). El fixture `T/test_campaign_executor_e5.py:25–60` incluso usa `calibration={"synthetic": True}` y es aceptado por la prueba de verificación con loader inyectado.
6. `finish` sólo escribe estado/tiempo y completion/verification; no rellena runs.parameters ni tablas legacy. Resultado: **verified es compatible con ausencia de matriz persistida**.

La configuración científica versionada ofrece un caso real del motivo: `M/configs/science/e7_v1.json:93,102` y las demás entradas fijan calibrate_threshold=false y evaluate_best_on_test=false; `e7_campaign_plan.json:54,63` coincide. `campaigns/contracts.py:325–326,495` deriva calibración del algoritmo del protocolo. Esto demuestra posibilidad por configuración vigente, no el contenido de campañas que no se consultaron.

Cuando calibración está habilitada, `_metric_subset:83–110` **sí incluye** conteos/matriz/F1/precision y `find_threshold_for_target_recall:241–270` devuelve selected_metrics, validation_metrics_at_threshold y default_threshold_metrics. `train.py:231–243` los persiste completos. No corresponde diagnosticar pérdida universal de matrices.

### Lectura visible al usuario

`B/app/services/training_summaries.py` ya contempla E5: selecciona recall/specificity/F2/AUC de `session.completion.selection` como fallback (114–131); busca calibration (172–179); prioriza matriz clínica legacy, confusion_matrices legacy y matriz calibrada E5 (221–290). No reconstruye una matriz a partir de predictions. Por ello sin calibración y sin filas legacy no hay matriz que mostrar, aunque haya scores por muestra. Además, el fallback de métricas escalares usa selection a 0.5 mientras el de matriz usa selected_metrics al threshold calibrado: no debe asumirse que todos los valores de una tarjeta describen el mismo punto operativo. La consulta sólo lee, no corrige esa diferencia.

## 9. TRAIN / VAL / TEST

| Uso | Evidencia exacta | Garantía y límite |
|---|---|---|
| Dataset TRAIN | train:57–74 carga `Path(session['dataset']['dataset_root'])/'train'` | Dataset físico materializado del snapshot; shuffle=true; augment según no_augment. No consulta SQL por imagen. |
| VAL en fit | train:191–196 `validation_data=datasets['val']` | VAL carga con shuffle=false; paths relativos se capturan antes del preprocessing (:65–69). |
| Etiquetas/preprocessing | data/loaders.py:378–429 | image_dataset_from_directory con CLASS_NAMES; preprocessing según resolved.model.preprocessing; augmentation sólo train. |
| Selección | train:108–114; checkpoint_policy.py:319–455 | VAL monitor explícito o política clínica; rechazo/fallback de colapso según política; history acumulada. TEST no alimenta ranking ni EarlyStopping. |
| Calibración | train:217–243 | Carga checkpoint exacto elegido y predice sólo VAL; búsqueda por recall/especificidad. Función pura de búsqueda no conoce split, la restricción depende del llamador. |
| Guard TRAIN | train:48–49 y campaign.preflight:64–65 | Si `evaluate_best_on_test is not False` produce `CampaignError('TEST_FORBIDDEN')`, incluso para None/0 que no son el booleano False. Si falta la clave, ocurre KeyError antes de ese error. |
| CLI individual | train._standalone:276–277 | evaluate_best_on_test o threshold_output_json → E5_TRAIN_TEST_OR_SIDECAR_FORBIDDEN. No es el mismo código TEST_FORBIDDEN. |
| Contrato científico | science/protocol.py:51–52; campaigns/contracts.py:325–326,480–495 | Configuración congelada prohíbe TEST dentro de TRAIN. Defaults antiguos de configs/models incluyen true (:45), pero protocolo de campaña lo fija false; no confundir defaults con config resuelta de una campaña. |
| Manifiesto Local | local_execution/backend.py:81–84; storage.verify_samples:35–40 | Sólo train/val; split ajeno → ValueError TEST_FORBIDDEN; comprueba path/split/hash. No impide a nivel permisos del OS leer una carpeta test fuera del flujo. |
| Prohibición calibrar TEST | threshold_calibration.validate_calibration_split:54–60 | test → ValueError(TEST_SET_CALIBRATION_ERROR); otras entradas no VAL se rechazan. train actual no llama esta validación porque pasa datasets['val'] directamente. |

La acreditación backend de integridad puede inspeccionar metadatos/hashes de los splits de un dataset sellado mediante `verify_dataset_for_execution`/governed_dataset. Esto no equivale a usar imágenes/labels TEST en fit, selección o calibración. La demostración de TRAIN se refiere al consumo científico; no afirma que el preflight nunca lea metadatos TEST.

TEST legítimo fuera de TRAIN: `assessment/cli.py::main:40` entra en `GlobalGate`; `_main:46` prepara la evaluación; `assessment/service.py::prepare:53–129` resuelve modelo verificado, dataset y threshold; `assessment/contracts.py::identity:82–96` exige purpose=final para split=test y protocolo compatible; reserva y guard DB exigen lock final (`A/20260912_02_assessments.py:71–76,149–151`, reglas assessment_final_locks y guard final). `assessment/service.py::run:193–245` invoca `KerasRuntime.predict` sobre las muestras acreditadas; `verify:132` reconstruye resultados. EXPLAIN usa `KerasRuntime.explain` con el mismo contrato de propósito, y SHAP usa TRAIN para background (`service.py:102–115`).

También existen helpers legacy `data.loaders.load_governed_test_split:484`, `load_raw_test_split:515`, `evaluation.clinical_metrics.evaluate_keras_model:662`, y `training.trainer.evaluate_selected_checkpoint_once`/`evaluate_selected_checkpoint_if_enabled`; son capacidad de evaluación legacy, no prueba de autorización final ni llamadas del TRAIN E5. No se alteró ninguna de estas rutas ni la gobernanza.

## 10. Docker vs Local

| Aspecto | Docker | Local |
|---|---|---|
| Proceso Python | sys.executable del contenedor Linux; worker con IDs y pipe de arranque; coordinador tiene GlobalGate | sys.executable del agente Mac; worker nativo con job por stdin después del primer heartbeat |
| TensorFlow | Import lazy en train; runtime del backend | Mismo import y código, runtime del VENV nativo; contrato de revisión Darwin/arm64/CPU/float32, no Metal |
| Dataset filesystem | Path absoluto del snapshot acreditado | root_id→path Mac; manifiesto train/val verificado por agente y worker; backend tiene su mapping |
| Checkpoints | root/run/epoch_N.keras; fichero parcial renombrado; hash y verificación aislada | Mismo save; filesystem compartido con backend; HTTP transporta referencias y hashes |
| DB access | Coordinador/worker mediante repositories + gate; PostgreSQL hostname db:5432 | Agente/worker sin SQL; backend ejecuta repositories/SQL |
| HTTP | No para reportar este TRAIN | claim, heartbeat, record, records, calculation-ended, exit, status |
| Reporter/repository actual | ExecutionRepository, o ControlledRepository en variante controlada | Reports → Api → LocalBackend → ControlledRepository heredado de ExecutionRepository |
| Heartbeat | No loop HTTP ni heartbeat periódico de sesión; lock DB y require_healthy en fronteras; Popen.wait bloquea durante fit | Thread 15 s; >60 s uncertain; reserva no expira |
| Exclusividad global | Advisory lock de sesión + token + evidencia /proc/subreaper + guards | Advisory xact lock al claim y job/gate durables + token remoto; mismos guards adaptados |
| Verificación | Parent preflight final; verify_session; isolated_keras_loader con gate/pipe y recursos | verify_session al recibir exit; load_checkpoint con subprocess del backend, sin handshake de isolated_keras_loader; timeout 120 s |
| Finalización | Hijo completed committed antes de salir; padre verified; luego finalize_terminal campaña | calculation-ended sólo job; exit prueba ausencia y hace completed/verified/release en transacción backend; sin finalize_terminal de cola |

Código común: modelo/configuración (`models/registry.py`, `models/configuration.py`, `models/adapters.py`), datos/preprocessing, train, métricas/callbacks/calibración, serialization/hash, dominio de campañas, repository de resultados y verify_session/keras_loader. Duplicación real: launcher y tratamiento de procesos; checks de entorno/dataset antes de ejecución; traducción/confinamiento de paths y chequeo de identidad de artefactos; orquestación de estados y error handling; dos wrappers de carga aislada (process_verification y LocalBackend.load_checkpoint). El train científico no está duplicado entre Docker y Local. Existe además trainer legacy con build/fit/evaluate/tracking propios, separado de ambos recorridos vigentes.

No hay medición local automática de Python/paquetes en agent/worker: el backend compara el environment enviado con la revisión registrada (`backend.prepare:54`), preflight compara source_sha256 del backend (`:34`), y reserve controlado recibe ese environment como current (`:107`). Esto acredita consistencia de declaración/revisión, no que el proceso Mac que arranca coincida realmente con lo declarado. El registry local resuelve el model_id sin repetir las comparaciones descriptor.version/adapter del preflight Docker.

## 11. Entornos Python

Fuentes: `B/Dockerfile:3,22–28`, `M/requirements.txt`, `B/requirements.txt`, `M/requirements-local-train.txt`. No hay lock Python referenciado en el build Docker. `pip` se actualiza y resuelve rangos en cada construcción. No se inspeccionó un contenedor vivo ni se ejecutó TensorFlow para esta auditoría.

| Dependencia | Docker declarado | Local declarado | Evidencia local instalada, sólo metadatos |
|---|---|---|---|
| Python | python:3.12-slim, patch/digest no fijado | Comentario requirements-local: Python 3.12 arm64 | `.venv-local-train/pyvenv.cfg:3`: 3.12.13; Homebrew Python 3.12 |
| TensorFlow | requirements.txt:1 `==2.17.1` | `==2.17.1` | tensorflow-2.17.1.dist-info/METADATA:3 |
| Keras | No pin directo; dependencia transitiva de TF | `==3.15.1` | keras-3.15.1.dist-info/METADATA:3 |
| NumPy | `>=1.26,<2.0` | `==1.26.4` | numpy-1.26.4.dist-info/METADATA:3 |
| scikit-learn | `>=1.5` | `==1.9.1` | scikit_learn-1.9.1.dist-info/METADATA:3 |
| psutil | No entrada en requirements ML/backend | `==6.1.1` | Agente lo importa en processes.py:5 |
| Metal | Comentado en requirements ML | No tensorflow-metal en lock local | Contrato revision.valid_environment:8 requiere CPU |

El VENV esperado es `M/.venv-local-train` según `requirements-local-train.txt:1–3`, y existe con `include-system-site-packages=false`. El agente usa el intérprete con el que se lo invoca, no fuerza ese path ni comprueba el VENV. Se leyeron archivos METADATA de ese VENV, sin activar, importar paquetes ni instalar nada.

Conclusión: TF y versión menor Python están alineados declarativamente; diverge la estrategia de fijación (Docker rangos/transitivas; Local freeze exacto). NumPy y scikit-learn locales satisfacen las restricciones Docker, pero **no se puede probar igualdad de versiones instaladas en Docker** con esas fuentes. No se infiere incompatibilidad numérica ni equivalencia científica sólo por satisfacer rangos.

`campaigns.service.planning_environment:17–55` registra source_sha256, Python, TF, Keras, NumPy, SQLAlchemy, psycopg y variables de determinismo. No incluye scikit-learn en packages pese a su papel en métricas/calibración. El contrato local exige estructura de environment, Darwin/arm64/CPU/float32 (`local_execution/revision.py:5–12`); no ejecuta validación del runtime remoto. Los campos de entorno existentes en runs y los snapshots permanecen intactos.

## 12. Tests existentes y alcance

**Localizados/inspeccionados, no ejecutados.** Nombres indican funciones reales; cuando se agrupan se explicita el alcance. Los tests PostgreSQL usan fixtures opt-in y algunos aplican migrations/esquemas de prueba; los tests de cálculo mínimo sí hacen fit. Ejecutarlos aquí infringiría el alcance de validación estática solicitado.

| Test | Archivo y línea | Qué acredita por sus assertions/fixtures | Qué NO acredita |
|---|---|---|---|
| test_valid_checkpoint_requires_loader_and_complete_records; test_partial_results_never_verified; test_checkpoint_mutation_and_invalid_load | T/test_campaign_executor_e5.py:63,85,93 | Verificación exige ocho tipos, loader y hash de checkpoint | Semántica de matriz/calibration; usa checkpoint/records sintéticos |
| test_train_uses_only_train_and_val_without_csv | T/test_campaign_executor_e5.py:138 | Flujo train con roles train/val, reportes y completed; sin CSV/JSON | Fit real; callback clínico real; DB; calibración habilitada; runs.parameters |
| test_frozen_twelve_and_resume_without_retraining; test_individual_failure_continues | T/test_campaign_executor_postgres.py:75,93 | Coordinación de matriz y reuso con DB/launch inyectado | Cálculo científico completo ni paridad Docker/Local |
| test_idempotency_and_fenced_owner; test_two_executors_claim_one_member | T/test_campaign_executor_postgres.py:123,164 | Idempotencia records, fencing y concurrencia DB | Idempotencia de output consolidado inexistente |
| test_zero_exit_without_evidence_never_verified; test_injected_failure_keeps_evidence | T/test_campaign_executor_postgres.py:152,228 | Exit 0 insuficiente; evidencia retenida ante fallos | Exigir matriz al cerrar |
| test_paused_atomic_idempotent_identity; test_concurrent_idempotence; test_distinct_concurrent_requests_only_one_reservation | T/test_controlled_train_postgres.py:35,80,141 | Reserva controlada, identidad y concurrencia | TRAIN real ni métricas finales |
| test_dry_run_no_writes; test_success_once_and_repeat_no_launch; test_recovery_requires_absence_and_never_launches | T/test_controlled_train_postgres.py:70,103,115 | Inspección sin cambios y recuperación sin relanzar | Entorno nativo remoto |
| test_two_coordinators_global_lock; test_reservations_require_global_owner; test_lost_db_lock_fences_owner | T/test_global_execution_postgres.py:48,63,190 | Exclusión y tokens DB | Igualdad científica |
| test_escaped_descendant_blocks_next_work; test_checkpoint_loader_owned_process_handshake; test_unverified_checkpoint_never_advances | T/test_global_execution_postgres.py:123,214,299 | Procesos Linux, handshake de verificación y bloqueo de avance | Descendientes Mac no observados; matriz |
| test_train_assessment_cross_exclusion | T/test_global_execution_postgres.py:252 | Exclusión entre TRAIN y assessment | Equivalencia de outputs |
| test_local_job_blocks_docker_gate_while_held; test_docker_gate_blocks_local_claim; test_two_local_agents_race_claim | T/test_local_execution_postgres.py:221,229,240 | Exclusividad Local/Docker y agentes concurrentes en esquema de fixture | Comparación real de resultados de los dos ejecutores |
| test_heartbeat_expiry_reports_uncertain_without_releasing; test_reconnect_and_duplicate_reports_are_idempotent; test_gate_owner_persists_until_exit | T/test_local_execution_postgres.py:265,277,537 | No liberación por timeout; reintentos; retención hasta exit | Red/caídas reales del Mac; ausencia de hijos no observados |
| test_single_controlled_attempt_does_not_chain; test_sequential_two_experiments_in_a_row | T/test_local_execution_postgres.py:320,422 | Modo controlado y encadenamiento backend con fixtures | Agotamiento/finalización de campaña Local en agente real |
| test_subprocess_failure_marks_failed_and_pauses_campaign; test_exit_requires_proven_absence_of_remaining_processes; test_persistence_rejection_leaves_no_false_record | T/test_local_execution_postgres.py:442,450,465 | Fallos, prueba de ausencia y rechazo DB | Matriz/calibración completa |
| test_identity_rejects_partial_and_verify_samples_rejects_test_split; test_artifact_hash_conflict_and_owner_conflict | T/test_local_execution_postgres.py:499,515 | TEST forbidden en manifiesto, integridad y owner | Sandbox OS que impida lectura TEST |
| test_route_dispatch_and_error_mapping | T/test_local_execution_postgres.py:559 | Dispatcher y HTTPException | Auth productiva end-to-end ni runtime científico |
| test_minimal_real_calculation_through_http_agent_and_subprocess | T/test_local_execution_postgres.py:591 | HTTP, agente, worker, fit, serialización, loader y readback verified reales en fixture | Docker real: servidor es nativo; process_table y preflight sustituidos; auth override; no comparación de parameters/matrices |
| test_minimal_real_train_serialization_and_committed_readback | T/test_pipeline_faults_postgres.py:97 | train real con adaptador diminuto y PostgreSQL, checkpoint y estado verified | Campaña operativa ni equivalencia entre plataformas ni output consolidado |
| test_commit_visible_lost_client_ack_and_repeat_finalize; test_val_persistence_failure_preserves_verified_train | T/test_pipeline_faults_postgres.py:48,138 | Commit/fallo de ACK, aislamiento entre TRAIN y assessment | Consolidación nueva de resultados |
| test_freeze_roundtrip_immutable_and_reconstruct; test_atomic_failure_leaves_draft_no_partial_matrix; test_attempts_retry_identity_and_train_link | T/test_campaigns_postgres.py:336,380,409 | Contrato congelado, rollback y vínculo TRAIN | Contenido de métricas del fit |
| test_exact_seal_and_upstream_hashing; test_changed_bytes_same_name_and_count_rejected; test_path_and_source_cannot_replace_governed_dataset | T/test_dataset_stage1.py:176,243,312 | Dataset sellado, integridad y origen gobernado | Proceso Local completo ni cierre con matriz |
| test_evidence_round_trip_and_write_failure_rolled_back | T/test_dataset_evidence_postgres.py:37 | Persistencia de evidencia de dataset | Resultados TRAIN |
| test_test_forbidden_development; test_exact_e5_binding_and_cross_version_rejected | T/test_assessment_e6.py:245,381 | TEST fuera de development y vínculo exacto E5 | TEST dentro de TRAIN real; parámetros consolidados |
| test_test_set_cannot_be_used_for_calibration | T/test_threshold_calibration.py:84 | Rechazo del split TEST en helper | Verificación automática del split de arrays entregados a find_threshold |
| test_confusion_matrix_values_clinical_order; test_f2_score_prioritizes_recall_for_parasitized; test_pr_auc_uses_probability_parasitized | T/test_clinical_metrics.py:21,35,53 | Cálculo clínico y orden de matriz | Persistencia DB |
| test_confusion_matrix_interpretation; test_compute_clinical_metrics_reports_f2_and_pr_auc | T/test_metrics.py:42,107 | Métricas/aliases y matriz sobre arrays | Transporte y cierre |
| test_callback_adds_clinical_validation_metrics_to_logs | T/test_clinical_validation_callback.py:22 | Proyección de métricas a logs | Preservar matriz/conteos; no lo exige |
| test_f2_policy_selects_highest_val_f2; test_auc_with_min_recall_selects_best_auc_among_valid_epochs; test_policy_rejects_collapsed_epoch_when_enabled | T/test_checkpoint_policy.py:102,118,178 | Selección y políticas con history artificial | DB/artefactos reales ni métricas calibradas al cierre |
| test_log_clinical_metrics_maps_confusion_matrix_and_json_payloads | T/test_clinical_metrics_tracking.py:58 | Mapping writer legacy con mocks | Camino E5/Reports ni commit DB |
| test_log_threshold_calibration_extracts_selected_metrics | T/test_threshold_calibration_tracking.py:44 | Mapping calibración legacy | train_execution_records end-to-end |
| test_run_tracker_start_run_serializes_new_columns; test_finish_run_casts_optional_completed_epochs_for_postgres; test_safe_track_swallows_tracking_failure | T/test_model_execution_tracking.py:156,58,249 | SQL/serialización legacy y tolerancia safe_track | Output científico en parameters; fail-closed de E5 |
| test_train_accepts_checkpoint_policy_and_calibration_args | T/test_train_integration.py:48 | Parser de opciones | No hace un TRAIN integrado aunque el archivo se llame integration |
| test_child_exit_preserved_without_accepting_partial_results | T/test_campaign_exit_diagnostics.py:12 | Diagnóstico exit y no aceptación parcial con repo simulado | Proceso/DB real |
| test_missing_git_keeps_same_source_identity; test_integral_jsonb_learning_rate_builds_without_mutating_config | T/test_campaign_environment_e9.py:7,20 | Identidad sin git y config JSONB integral | Versionado/igualdad Docker vs Local |
| test_training_summaries_http_is_exact_read_only_and_preserves_database | B/tests/test_training_summaries_postgres.py:108 | Lectura HTTP/DB sin mutación de resumen | Producer de matriz ni consolidación TRAIN |
| test_service_maps_release_fields_counts_and_metrics_without_transformation; test_sql_is_scoped_deterministic_distinct_and_release_is_not_recomputed | B/tests/test_training_summaries_api.py:112,163 | Mapping/contrato lectura | Persistencia científica del TRAIN |

Se localizaron además suites de `test_model_registry_e2`, `test_model_configuration_postgres`, `test_input_contract_e3/postgres`, `test_governed_dataset_contract`, `test_physical_dataset_split`, `test_assessment_postgres`, `test_persistence_e9_postgres`, `test_science_e7/postgres`, `test_checkpoint_selection_metadata`, `test_training_history_outputs`, `test_max_epochs_tracking`, `test_model_execution_outputs`, `test_train_checkpoint_policy_args`. El inventario de símbolos al final permite ubicar los tests relacionados sin equiparar su mera existencia con aprobación.

| Test adicional | Archivo y línea | Qué acredita | Qué NO acredita |
|---|---|---|---|
| test_configuration_roundtrip_and_rollback | T/test_model_configuration_postgres.py:147 | Snapshot model_configuration_e2 y rollback PostgreSQL | OUTPUT de runs.parameters ni equivalencia Local/Docker |
| test_snapshot_is_immutable_and_change_is_rejected | T/test_governed_dataset_contract.py:21 | Inmutabilidad del snapshot | Aislamiento físico del filesystem Local |
| test_final_requires_prior_exact_lock_and_synthetic_allow | T/test_assessment_postgres.py:214 | Rechazo SQL de evaluación final sin lock exacto | TEST dentro de TRAIN ni resultados de campaigns productivas |
| test_report_commit_visible_from_new_connection | T/test_persistence_e9_postgres.py:14 | Reporte ScienceRepository visible tras commit en conexión nueva | No es una prueba de records TRAIN ni de durabilidad tras reinicio |

Gaps de cobertura confirmados por el recorrido y las assertions revisadas: ninguna prueba del camino E5 exige un OUTPUT consolidado en runs.parameters; las pruebas de verify_session aceptan calibration sintética sin matriz; no hay una comparación end-to-end de outputs científicos Docker frente a Local con igual dataset/config; los dos tests de fit mínimo comprueban cierre/checkpoint/verified, no ese contrato consolidado. No se certifica que los tests pasen en el entorno actual.

## 13. Acoplamientos para E10

Clasificación de responsabilidades/riesgos, sin diseño de implementación ni firma nueva.

| Grupo | Archivo/función | Qué está acoplado; qué deberá cambiar o preservarse | Riesgo |
|---|---|---|---|
| A. train → persistencia | execution/train.py::train:90,244–257 | Interfaz implícita put/records/finish, hash del ledger y transición completed dentro del cálculo. Preservar evidencia, orden canónico y propagación de fallos; cualquier separación debe reconocer lectura además de escritura. | Hash distinto, finalización prematura o pérdida silenciosa de resultados. |
| A. train → archivos | train.py::PersistEpoch:115–138 | Nombres/rutas, formato Keras, publicación del archivo y metadata en el núcleo | Artefacto sin record o record sin binario; romper ownership/rutas. |
| B. Docker worker → persistencia | execution/worker.py::main:20–54 | Construye repo, lee SQL de campaign_id, valida snapshot, registra PID | Eliminar validación/fencing al desacoplar o entrenar configuración no congelada. |
| B. coordinador → DB/gate | execution/campaign.py::execute_campaign; controlled.execute_one | Reserva, estados y recuperación transaccional del dominio | Reintentar accepted members o consumir presupuesto dos veces. |
| C. Local worker → HTTP | local_execution/worker.py::main; transport.Reports | Construcción de session local, path translation, owner remoto y reportes síncronos | Confundir owner de session DB con token del job; hash sobre paths incorrectos; superar 8 MiB. |
| D. FastAPI → repositorios | B/app/routes/local_execution.py::service/local_operation; LocalBackend.bound/operation | Construye ControlledRepository, transacción exterior y savepoints, SQL propio de jobs/gate | Cambiar atomicidad de exit; autorización dependiente de SYSTEM_ADMIN/principal. |
| E. métricas → persistencia | checkpoint_policy.ClinicalValidationMetricsCallback; train.PersistEpoch; threshold_calibration._metric_subset | Proyección parcial a logs; matriz final depende de calibración; legacy escribe otras tablas | Omitir métricas o mezclar split, epoch y threshold; duplicar fuentes de verdad. |
| E. lectura de resultados | training_summaries SQL; assessment.lineage.resolve; science.comparison.read_evaluation | Consumidores conocen completion/selection/calibration/verification actuales | Romper consultas históricas, umbral de evaluación o selección de candidato. |
| F. completion → verification | artifacts.verify_session; repository.finish; campaign.execute_campaign; backend.operation('exit') | Hash, secuencia, binario y salida del proceso preceden aceptación/liberación; fases DB distintas por ejecutor | Liberar antes de que termine TF; marcar éxito con evidencia incompleta; transición SQL inválida. |

Deben preservarse `runs` como identidad canónica, FK de attempt/session, records append-only, dataset/config congelados, TEST aislado y campos de entorno existentes. El informe no prescribe tablas nuevas ni persistencia nueva de entornos.

## 14. Gaps confirmados

| ID | Hallazgo | Evidencia / alcance |
|---|---|---|
| G1 | runs.parameters no representa OUTPUT científico en el TRAIN vigente | _create_run omite; finish sólo status/tiempo (§5–6). |
| G2 | Matriz/conteos/F1 calculados por epoch no llegan a records; matriz final depende de calibración | Callback metric_updates, rama calibrate_threshold, verify_session (§8). |
| G3 | verified acredita un ledger y checkpoint, no contrato completo de métricas | artifacts.py:20–89; fixture calibration sintética. |
| G4 | Dos semánticas históricas de parameters/config snapshot coexisten | Tracking legacy INPUT e inferencia configuration; E5 default vacío. |
| G5 | Campos resumen/entorno explícitos de runs no se pueblan como en el legacy | Comparación SQL `_create_run`/`start_run`; session sí conserva evidencia. |
| G6 | Local declara entorno, no valida el runtime efectivo del agente | agent/worker sin medición; prepare compara request y revisión. |
| G7 | Versionado científico Docker no fija Keras/NumPy/sklearn exactos | Dockerfile + requirements; no se deduce versión instalada. |
| G8 | Validación Local difiere del preflight final Docker | Backend exit no vuelve a ejecutar preflight de dataset/entorno; verify_session verifica records/checkpoint, no todos los bytes del dataset. |
| G9 | Cola Local no ejecuta finalize_terminal y claim sin candidato da error | backend.py:109,154–167 frente a campaign.py:265. |
| G10 | Límites del transporte/procesos son parte del contrato práctico | Payload completo predictions/calibration vs 8 MiB; prueba sólo descendientes observados. No se calculó si una campaña real excede el límite. |
| G11 | Las métricas de selección y la matriz calibrada no necesariamente comparten threshold | training_summaries usa selection para escalares y calibration para matriz. |
| G12 | Documentación y tests legacy pueden inducir a auditar el camino equivocado | src.train CLI vs import, old build_matrix y trainer conservados; §1/§12. |

No se afirma que falten todas las métricas en PostgreSQL ni que toda campaña carezca de matriz. No se atribuye un fallo observado en producción sin datos: las causas anteriores se demuestran por código y fixtures/config versionados.

## 15. Riesgos para E10.1 y cierre de auditoría

La revisión posterior deberá considerar identidad/owner, idempotencia, hash y orden de records, semántica exacta de métricas (split, epoch, threshold, clase positiva y AP frente a AUC PR), compatibilidad de queries históricas, archivos compartidos y diferencias de atomicidad de cierre. Cambiar sólo la clase del primer argumento de train no elimina el acoplamiento a lectura del ledger, filesystem ni completion.

Riesgos concretos: una escritura de output que se confunda con configuration de entrada; mutación de records ya sellados; migración involuntaria del significado de parameters legacy; borrado de campos de entorno; carga de TEST durante selección; aprobación de un checkpoint distinto al calibrado; liberar el job antes de exit/verify; intentar completed→failed cuando el guard sólo permite completed→verified; asumir equivalencia numérica por compartir TF; ampliar la tarea hacia publication/deployment.

Validación de E10.0: búsqueda estática de productores/SQL/consumidores, inspección de firma y tests, comprobación de referencias y `git status --short --untracked-files=all`. No se ejecutaron imports de la aplicación ni tests, y no se modificó código, tests, requirements, Compose, migraciones o PostgreSQL. Se entrega el informe y se detiene el trabajo para revisión humana.

### Registro de inspección y catálogo de símbolos

Índice verificable: 58 archivos de código/configuración/esquema referenciados y 41 archivos de tests. Las búsquedas globales abarcaron además otras fuentes; este índice identifica la evidencia seleccionada. Los metadatos del VENV no versionado se documentan por separado en §11.

Las rutas siguientes son relativas a la raíz del repositorio; los enlaces se resuelven desde este documento.

| Archivo de evidencia |
|---|
| [alembic/versions/20260829_01_persist_training_release_status.py](../../../alembic/versions/20260829_01_persist_training_release_status.py) |
| [alembic/versions/20260912_01_train_execution.py](../../../alembic/versions/20260912_01_train_execution.py) |
| [alembic/versions/20260912_02_assessments.py](../../../alembic/versions/20260912_02_assessments.py) |
| [alembic/versions/20260914_02_global_execution.py](../../../alembic/versions/20260914_02_global_execution.py) |
| [alembic/versions/20260915_01_local_execution.py](../../../alembic/versions/20260915_01_local_execution.py) |
| [backend_api/Dockerfile](../../../backend_api/Dockerfile) |
| [backend_api/app/main.py](../../../backend_api/app/main.py) |
| [backend_api/app/routes/local_execution.py](../../../backend_api/app/routes/local_execution.py) |
| [backend_api/app/services/training_summaries.py](../../../backend_api/app/services/training_summaries.py) |
| [backend_api/requirements.txt](../../../backend_api/requirements.txt) |
| [docker-compose.override.yml](../../../docker-compose.override.yml) |
| [docker-compose.yml](../../../docker-compose.yml) |
| [malaria_dl_local_project/configs/science/e7_v1.json](../../../malaria_dl_local_project/configs/science/e7_v1.json) |
| [malaria_dl_local_project/db/init/001_schema.sql](../../../malaria_dl_local_project/db/init/001_schema.sql) |
| [malaria_dl_local_project/db/init/019_model_execution_parameters.sql](../../../malaria_dl_local_project/db/init/019_model_execution_parameters.sql) |
| [malaria_dl_local_project/requirements-local-train.txt](../../../malaria_dl_local_project/requirements-local-train.txt) |
| [malaria_dl_local_project/requirements.txt](../../../malaria_dl_local_project/requirements.txt) |
| [malaria_dl_local_project/run_train_all_models.py](../../../malaria_dl_local_project/run_train_all_models.py) |
| [malaria_dl_local_project/src/malaria_dl/assessment/runtime.py](../../../malaria_dl_local_project/src/malaria_dl/assessment/runtime.py) |
| [malaria_dl_local_project/src/malaria_dl/campaigns/repository.py](../../../malaria_dl_local_project/src/malaria_dl/campaigns/repository.py) |
| [malaria_dl_local_project/src/malaria_dl/campaigns/service.py](../../../malaria_dl_local_project/src/malaria_dl/campaigns/service.py) |
| [malaria_dl_local_project/src/malaria_dl/config/settings.py](../../../malaria_dl_local_project/src/malaria_dl/config/settings.py) |
| [malaria_dl_local_project/src/malaria_dl/data/input_contract.py](../../../malaria_dl_local_project/src/malaria_dl/data/input_contract.py) |
| [malaria_dl_local_project/src/malaria_dl/data/preprocessing.py](../../../malaria_dl_local_project/src/malaria_dl/data/preprocessing.py) |
| [malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py](../../../malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py) |
| [malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_finalization_service.py](../../../malaria_dl_local_project/src/malaria_dl/evaluation/evaluation_finalization_service.py) |
| [malaria_dl_local_project/src/malaria_dl/execution/__init__.py](../../../malaria_dl_local_project/src/malaria_dl/execution/__init__.py) |
| [malaria_dl_local_project/src/malaria_dl/execution/artifacts.py](../../../malaria_dl_local_project/src/malaria_dl/execution/artifacts.py) |
| [malaria_dl_local_project/src/malaria_dl/execution/campaign.py](../../../malaria_dl_local_project/src/malaria_dl/execution/campaign.py) |
| [malaria_dl_local_project/src/malaria_dl/execution/controlled.py](../../../malaria_dl_local_project/src/malaria_dl/execution/controlled.py) |
| [malaria_dl_local_project/src/malaria_dl/execution/global_gate.py](../../../malaria_dl_local_project/src/malaria_dl/execution/global_gate.py) |
| [malaria_dl_local_project/src/malaria_dl/execution/process_verification.py](../../../malaria_dl_local_project/src/malaria_dl/execution/process_verification.py) |
| [malaria_dl_local_project/src/malaria_dl/execution/repository.py](../../../malaria_dl_local_project/src/malaria_dl/execution/repository.py) |
| [malaria_dl_local_project/src/malaria_dl/execution/train.py](../../../malaria_dl_local_project/src/malaria_dl/execution/train.py) |
| [malaria_dl_local_project/src/malaria_dl/execution/worker.py](../../../malaria_dl_local_project/src/malaria_dl/execution/worker.py) |
| [malaria_dl_local_project/src/malaria_dl/governance/repository.py](../../../malaria_dl_local_project/src/malaria_dl/governance/repository.py) |
| [malaria_dl_local_project/src/malaria_dl/inference/traceable.py](../../../malaria_dl_local_project/src/malaria_dl/inference/traceable.py) |
| [malaria_dl_local_project/src/malaria_dl/local_execution/__init__.py](../../../malaria_dl_local_project/src/malaria_dl/local_execution/__init__.py) |
| [malaria_dl_local_project/src/malaria_dl/local_execution/agent.py](../../../malaria_dl_local_project/src/malaria_dl/local_execution/agent.py) |
| [malaria_dl_local_project/src/malaria_dl/local_execution/backend.py](../../../malaria_dl_local_project/src/malaria_dl/local_execution/backend.py) |
| [malaria_dl_local_project/src/malaria_dl/local_execution/processes.py](../../../malaria_dl_local_project/src/malaria_dl/local_execution/processes.py) |
| [malaria_dl_local_project/src/malaria_dl/local_execution/revision.py](../../../malaria_dl_local_project/src/malaria_dl/local_execution/revision.py) |
| [malaria_dl_local_project/src/malaria_dl/local_execution/storage.py](../../../malaria_dl_local_project/src/malaria_dl/local_execution/storage.py) |
| [malaria_dl_local_project/src/malaria_dl/local_execution/transport.py](../../../malaria_dl_local_project/src/malaria_dl/local_execution/transport.py) |
| [malaria_dl_local_project/src/malaria_dl/local_execution/worker.py](../../../malaria_dl_local_project/src/malaria_dl/local_execution/worker.py) |
| [malaria_dl_local_project/src/malaria_dl/models/configuration.py](../../../malaria_dl_local_project/src/malaria_dl/models/configuration.py) |
| [malaria_dl_local_project/src/malaria_dl/models/registry.py](../../../malaria_dl_local_project/src/malaria_dl/models/registry.py) |
| [malaria_dl_local_project/src/malaria_dl/persistence/database.py](../../../malaria_dl_local_project/src/malaria_dl/persistence/database.py) |
| [malaria_dl_local_project/src/malaria_dl/persistence/dataset_evidence.py](../../../malaria_dl_local_project/src/malaria_dl/persistence/dataset_evidence.py) |
| [malaria_dl_local_project/src/malaria_dl/persistence/lineage.py](../../../malaria_dl_local_project/src/malaria_dl/persistence/lineage.py) |
| [malaria_dl_local_project/src/malaria_dl/persistence/model_configuration.py](../../../malaria_dl_local_project/src/malaria_dl/persistence/model_configuration.py) |
| [malaria_dl_local_project/src/malaria_dl/persistence/run_repository.py](../../../malaria_dl_local_project/src/malaria_dl/persistence/run_repository.py) |
| [malaria_dl_local_project/src/malaria_dl/persistence/training_release.py](../../../malaria_dl_local_project/src/malaria_dl/persistence/training_release.py) |
| [malaria_dl_local_project/src/malaria_dl/training/trainer.py](../../../malaria_dl_local_project/src/malaria_dl/training/trainer.py) |
| [malaria_dl_local_project/src/metrics.py](../../../malaria_dl_local_project/src/metrics.py) |
| [malaria_dl_local_project/src/run_tracker.py](../../../malaria_dl_local_project/src/run_tracker.py) |
| [malaria_dl_local_project/src/tracking_integration.py](../../../malaria_dl_local_project/src/tracking_integration.py) |
| [malaria_dl_local_project/src/train.py](../../../malaria_dl_local_project/src/train.py) |

Catálogo de funciones de prueba obtenido por AST, sin importarlas ni ejecutarlas. Incluye todos los símbolos `test_*` de estos archivos, incluso tests auxiliares del mismo módulo. La parametrización puede generar más casos que funciones; los números no son tests aprobados. Interpretación y límites de las suites: §12.

<details>
<summary>backend_api/tests/test_training_summaries_api.py — 12 funciones</summary>

[Abrir archivo](../../../backend_api/tests/test_training_summaries_api.py)

```text
87: test_schema_accepts_each_canonical_release_status
92: test_schema_rejects_unknown_release_status
97: test_schema_preserves_nullable_release_status_and_release_metadata
112: test_service_maps_release_fields_counts_and_metrics_without_transformation
140: test_unknown_persisted_status_fails_with_explicit_contract_error
153: test_service_limit_is_bounded_without_opening_a_connection
163: test_sql_is_scoped_deterministic_distinct_and_release_is_not_recomputed
190: test_listing_has_no_governance_artifact_or_runtime_dependencies
217: test_read_only_helper_sets_postgresql_mode_timeouts_and_rolls_back
256: test_http_contract_openapi_static_order_and_validation
312: test_unknown_datasource_uses_existing_error_contract
319: test_uuid_and_timestamp_serialization_is_standard
```

</details>

<details>
<summary>backend_api/tests/test_training_summaries_postgres.py — 1 funciones</summary>

[Abrir archivo](../../../backend_api/tests/test_training_summaries_postgres.py)

```text
108: test_training_summaries_http_is_exact_read_only_and_preserves_database
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_assessment_e6.py — 25 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_assessment_e6.py)

```text
149: test_exact_reuse_does_not_predict
163: test_identity_changes
177: test_partial_failure_retry_new_attempt
202: test_active_response_no_predict
213: test_corruption_never_reused
227: test_threshold_no_implicit_clinical_fallback
245: test_test_forbidden_development
262: test_explanations_artifacts_separate_and_tamper_rejected
282: test_reconstruction_rejects_conflicting_labels
290: test_artifact_write_failure_never_verified
320: test_minimal_model_uses_exact_e3_input
372: test_not_loadable_checkpoint_rejected
381: test_exact_e5_binding_and_cross_version_rejected
416: test_dataset_override_rejected_before_verifier
430: test_prepare_rejects_input_and_foreign_evaluation
458: test_campaign_inspection_keeps_unaccepted_visible
474: test_cli_rejects_legacy_implicit_batch
483: test_legacy_multiple_versions_rejected
497: test_minimal_attribution_methods_preserve_raw_domain
525: test_recovery_requires_proven_dead_local_owner
556: test_finalization_failure_preserves_original_even_cleanup_fails
572: test_e6_migration_renders_without_accidental_parameters
605: test_accredited_sample_population_and_equivalent_override
630: test_reservation_conflicts_keep_exact_identity_required
670: test_concurrency_diagnostic_never_exposes_driver_text
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_assessment_postgres.py — 12 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_assessment_postgres.py)

```text
53: test_roundtrip_batches_duplicate_failure_and_retry
78: test_owner_fenced_and_verified_results_immutable
115: test_concurrent_equivalent_requests_have_one_owner
214: test_final_requires_prior_exact_lock_and_synthetic_allow
252: test_sql_rejects_json_null_identity
264: test_structural_hash_normalizes_numeric_spellings
279: test_explain_artifacts_roundtrip
294: test_readback_after_commit_in_separate_connection
305: test_public_e6_revision_readonly
340: test_raw_sql_rejects_wrong_patient_and_preserves_outer_transaction
351: test_corrupt_verification_count_rejected
364: test_campaign_consumer_requires_exact_accepted_train
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_campaign_environment_e9.py — 2 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_campaign_environment_e9.py)

```text
7: test_missing_git_keeps_same_source_identity
20: test_integral_jsonb_learning_rate_builds_without_mutating_config
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_campaign_executor_e5.py — 7 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_campaign_executor_e5.py)

```text
63: test_valid_checkpoint_requires_loader_and_complete_records
85: test_partial_results_never_verified
93: test_checkpoint_mutation_and_invalid_load
109: test_campaign_overrides_rejected
114: test_inspection_cli_and_unknown_host
122: test_migration_has_no_accidental_binds
138: test_train_uses_only_train_and_val_without_csv
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_campaign_executor_postgres.py — 9 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_campaign_executor_postgres.py)

```text
75: test_frozen_twelve_and_resume_without_retraining
93: test_individual_failure_continues
123: test_idempotency_and_fenced_owner
140: test_systemic_failure_pauses_before_claim
152: test_zero_exit_without_evidence_never_verified
164: test_two_executors_claim_one_member
199: test_parent_interruption_retains_attempt
228: test_injected_failure_keeps_evidence
277: test_public_e5_revision_readonly
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_campaign_exit_diagnostics.py — 1 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_campaign_exit_diagnostics.py)

```text
12: test_child_exit_preserved_without_accepting_partial_results
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_campaigns_e4.py — 19 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_campaigns_e4.py)

```text
115: test_matrix_cardinality_and_input
131: test_canonical_order_number_and_scientific_sensitivity
145: test_non_json_rejected
150: test_new_registry_only_affects_new_plans
163: test_exclusions_visible_and_unknown_not_silent
206: test_bad_matrix
229: test_protocol_blocks_invalid_or_pending
239: test_draft_and_roles_accreditation
249: test_protocol_variant_conflict
256: test_service_requires_uuid_and_no_implicit_db_or_training
275: test_service_rechecks_exact_dataset_and_rejects_code_change
303: test_cli_inspect_without_db_or_tensorflow
317: test_protocol_draft_cannot_use_test
326: test_repository_failure_sanitized_no_fallback
341: test_frozen_contract_self_contained_and_tamper_rejected
372: test_additive_migration_offline_and_linear
402: test_read_repository_does_not_import_model_registry
433: test_invalid_state_transition_before_update
448: test_conflicting_dataset_read_rejected_before_members
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_campaigns_postgres.py — 12 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_campaigns_postgres.py)

```text
300: test_public_migration_readonly
336: test_freeze_roundtrip_immutable_and_reconstruct
380: test_atomic_failure_leaves_draft_no_partial_matrix
409: test_attempts_retry_identity_and_train_link
486: test_concurrent_active_attempt_two_connections
572: test_incompatible_train_association
620: test_database_uniqueness_and_cross_campaign_fk
719: test_sql_rejects_missing_and_null_frozen_fields
785: test_sql_rejects_null_configuration
856: test_relational_model_and_explicit_alias
880: test_train_identity_guard_allows_real_e2_progress_writer
939: test_configuration_json_shape_operator_precedence
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_checkpoint_policy.py — 10 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_checkpoint_policy.py)

```text
22: test_auc_with_min_recall_score_prioritizes_constraint_then_auc
44: test_early_stopping_score_rejects_collapsed_epochs
64: test_collapsed_scores_remain_ordered_when_all_epochs_collapse
92: test_early_stopping_score_inverts_min_monitors
102: test_f2_policy_selects_highest_val_f2
118: test_auc_with_min_recall_selects_best_auc_among_valid_epochs
163: test_auc_with_min_recall_fallback_when_no_epoch_reaches_min_recall
178: test_policy_rejects_collapsed_epoch_when_enabled
206: test_policy_all_epochs_collapsed_returns_warning
235: test_get_monitor_for_f2_policy
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_checkpoint_policy_tracking.py — 3 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_checkpoint_policy_tracking.py)

```text
27: test_record_checkpoint_policy_passes_model_name_from_context
44: test_log_checkpoint_policy_extracts_policy_metrics_and_defaults
83: test_log_checkpoint_policy_uses_unknown_when_policy_is_absent
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_checkpoint_selection_metadata.py — 9 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_checkpoint_selection_metadata.py)

```text
87: test_checkpoint_selection_contains_required_contract
109: test_finalized_checkpoint_report_records_completed_test
125: test_completed_epochs_cannot_exceed_total_maximum
135: test_fallback_value_is_paired_with_its_actual_validation_metric
150: test_final_test_contract_is_written_once
186: test_skip_clears_stale_test_files_and_does_not_call_evaluator
200: test_threshold_output_rejects_reserved_artifact_names
215: test_threshold_output_cannot_overwrite_an_immutable_snapshot
229: test_execution_summary_explains_validation_selection_and_single_test
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_clinical_metrics.py — 6 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_clinical_metrics.py)

```text
15: test_label_mapping_is_clinical
21: test_confusion_matrix_values_clinical_order
35: test_f2_score_prioritizes_recall_for_parasitized
53: test_pr_auc_uses_probability_parasitized
74: test_prediction_collapse_all_parasitized
81: test_prediction_collapse_all_uninfected
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_clinical_metrics_tracking.py — 2 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_clinical_metrics_tracking.py)

```text
32: test_record_clinical_metrics_passes_context_and_threshold
58: test_log_clinical_metrics_maps_confusion_matrix_and_json_payloads
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_clinical_validation_callback.py — 2 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_clinical_validation_callback.py)

```text
22: test_callback_adds_clinical_validation_metrics_to_logs
40: test_callback_detects_validation_prediction_collapse
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_controlled_train_postgres.py — 14 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_controlled_train_postgres.py)

```text
35: test_paused_atomic_idempotent_identity
47: test_wrong_identity_rejected
53: test_invalid_revision_rejected
62: test_runtime_hash_and_active_rejected
70: test_dry_run_no_writes
80: test_concurrent_idempotence
92: test_launch_failure_no_chain
103: test_success_once_and_repeat_no_launch
115: test_recovery_requires_absence_and_never_launches
124: test_resume_and_revision_mutation_blocked
133: test_wrong_scientific_payload_sql_rejected
141: test_distinct_concurrent_requests_only_one_reservation
154: test_technical_worker_binding
164: test_controlled_failure_return_code_does_not_chain
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_dataset_evidence_postgres.py — 1 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_dataset_evidence_postgres.py)

```text
37: test_evidence_round_trip_and_write_failure_rolled_back
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_dataset_stage1.py — 24 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_dataset_stage1.py)

```text
168: test_resolver_rejects_before_database
176: test_exact_seal_and_upstream_hashing
210: test_rejected_contracts
236: test_each_fingerprint_is_recomputed
243: test_changed_bytes_same_name_and_count_rejected
252: test_missing_or_unexpected_file_rejected
269: test_parent_inheritance_normalized_and_pinned
289: test_historical_unaccredited_blocked_without_backfill
300: test_batch_pin_cannot_substitute_materialization
312: test_path_and_source_cannot_replace_governed_dataset
330: test_batch_cli_requires_uuid
336: test_legacy_command_builder_propagates_explicit_pin_to_twelve
347: test_dataset_only_legacy_training_invocation_rejected
354: test_failed_persistence_never_returns_verified
362: test_evidence_round_trip_without_sidecars
406: test_run_link_failure_is_fatal
416: test_programmatic_execution_missing_id_is_early
428: test_train_public_entry_rejects_before_model_or_images
450: test_consumers_reject_before_inference
472: test_inventory_requires_scope_before_connect
481: test_inventory_filters_and_rejects_wrong_training
516: test_byte_exact_canonical_rules_match_upstream_sources
543: test_additional_blocking_failure_is_not_ignored
551: test_rejection_evidence_retains_sealed_reference
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_global_execution_postgres.py — 19 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_global_execution_postgres.py)

```text
48: test_two_coordinators_global_lock
63: test_reservations_require_global_owner
79: test_new_oom_and_consecutive_failure_circuit
92: test_two_failures_pause_without_consuming_matrix
103: test_sequential_revision_and_verified_before_next
123: test_escaped_descendant_blocks_next_work
144: test_successful_child_reaped_and_identity_checked
157: test_insufficient_resources_fail_before_reservation
166: test_pause_after_work_prevents_next_claim
182: test_readiness_does_not_require_memory_optimization
190: test_lost_db_lock_fences_owner
202: test_migration_rejects_multiple_legacy_active_sessions
214: test_checkpoint_loader_owned_process_handshake
252: test_train_assessment_cross_exclusion
286: test_queue_launch_failure_is_recorded_and_paused
299: test_unverified_checkpoint_never_advances
313: test_unclean_disappearance_is_not_resource_release
327: test_queue_dry_run_selects_pending_and_never_reserves
340: test_inspection_is_not_an_executing_coordinator
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_governed_dataset_contract.py — 2 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_governed_dataset_contract.py)

```text
21: test_snapshot_is_immutable_and_change_is_rejected
29: test_orchestrator_propagates_only_dataset_version_selection
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_input_contract_e3.py — 10 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_input_contract_e3.py)

```text
60: test_vgg_reference_independent_and_dark_input
79: test_new_vgg_resolution_and_historical_auto
102: test_invalid_contract
109: test_historical_contract_preserved_and_overrides_rejected
148: test_other_architectures_unchanged
174: test_vgg_four_optimizers_step_reload
219: test_consumer_tensor_and_prediction_equivalence
299: test_vgg_augmentation_before_preprocessing_only_on_train
325: test_loaded_signature_and_double_normalization_rejected
338: test_consumer_main_blocks_before_load_or_predict
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_input_contract_postgres.py — 1 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_input_contract_postgres.py)

```text
18: test_input_snapshot_roundtrip
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_local_execution_postgres.py — 21 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_local_execution_postgres.py)

```text
184: test_claim_is_idempotent_by_request_id
194: test_claim_rejects_mismatched_repeat
204: test_owner_and_agent_fencing
221: test_local_job_blocks_docker_gate_while_held
229: test_docker_gate_blocks_local_claim
240: test_two_local_agents_race_claim
265: test_heartbeat_expiry_reports_uncertain_without_releasing
277: test_reconnect_and_duplicate_reports_are_idempotent
303: test_controlled_mode_requires_paused_campaign
310: test_sequential_mode_rejects_paused_and_accepts_active
320: test_single_controlled_attempt_does_not_chain
422: test_sequential_two_experiments_in_a_row
442: test_subprocess_failure_marks_failed_and_pauses_campaign
450: test_exit_requires_proven_absence_of_remaining_processes
465: test_persistence_rejection_leaves_no_false_record
484: test_resolve_rejects_escape_and_symlink
499: test_identity_rejects_partial_and_verify_samples_rejects_test_split
515: test_artifact_hash_conflict_and_owner_conflict
537: test_gate_owner_persists_until_exit
559: test_route_dispatch_and_error_mapping
591: test_minimal_real_calculation_through_http_agent_and_subprocess
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_max_epochs_tracking.py — 8 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_max_epochs_tracking.py)

```text
57: test_migration_is_incremental_and_declares_release_columns
80: test_resolver_accepts_nested_metadata_and_preserves_false
112: test_start_tracking_materializes_max_epochs_configuration
155: test_explicit_execution_parameters_override_legacy_parameters
188: test_total_epochs_is_not_misreported_as_base_max_epochs
196: test_update_effective_parameters_override_context_fallback
215: test_run_tracker_serializes_release_summary
247: test_update_and_finish_extract_final_values
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_metrics.py — 5 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_metrics.py)

```text
23: test_clinical_predictions_use_parasitized_probability
32: test_legacy_mapping_inverts_scalar_scores_explicitly
42: test_confusion_matrix_interpretation
57: test_metrics_are_computed_against_parasitized_positive_label
107: test_compute_clinical_metrics_reports_f2_and_pr_auc
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_model_configuration_postgres.py — 1 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_model_configuration_postgres.py)

```text
147: test_configuration_roundtrip_and_rollback
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_model_execution_outputs.py — 8 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_model_execution_outputs.py)

```text
39: test_training_output_lock_rejects_concurrent_same_model_writer
54: test_tracked_snapshot_uses_database_run_id_and_keeps_local_fallback
67: test_snapshot_json_paths_are_self_contained_but_cli_is_preserved
111: test_snapshot_copies_only_current_execution_artifacts
130: test_snapshot_preserves_required_checkpoint_lineage_artifacts
160: test_snapshot_rejects_different_artifacts_with_same_basename
179: test_combined_history_is_continuous_and_marks_boundary_epoch
202: test_execution_summary_writes_json_and_markdown
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_model_execution_tracking.py — 8 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_model_execution_tracking.py)

```text
58: test_finish_run_casts_optional_completed_epochs_for_postgres
70: test_resolves_canonical_execution_type_without_changing_run_type
95: test_resolves_total_epochs_from_base_and_fine_tuning
107: test_start_tracking_run_forwards_execution_contract
156: test_run_tracker_start_run_serializes_new_columns
183: test_log_training_history_persists_phase_aliases_and_progress
211: test_integration_records_actual_fine_tuning_start_and_epoch_metrics
249: test_safe_track_swallows_tracking_failure
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_model_registry_e2.py — 15 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_model_registry_e2.py)

```text
50: test_lazy_cli
59: test_discovery_and_descriptor_errors
103: test_matrix_and_identical_child_resolution
145: test_invalid_config_before_adapter
150: test_precedence_requested_resolved_and_tracking
188: test_beta_rejected_in_cli_and_policy
200: test_optimizer_config
215: test_real_adapters_step_and_reload
263: test_persistence_roundtrip_failure_no_files
309: test_persistence_failure_blocks_fit
366: test_f2_and_monitor_semantics
389: test_matrix_invalid_combination_rejected_before_preflight
401: test_clinical_target_independent_of_technical_selection
415: test_explicit_loss_matches_legacy_function
429: test_persistence_rejects_changed_readback
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_persistence_e9_postgres.py — 1 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_persistence_e9_postgres.py)

```text
14: test_report_commit_visible_from_new_connection
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_physical_dataset_split.py — 4 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_physical_dataset_split.py)

```text
21: test_class_names_are_clinical_order
24: test_validate_ratios_requires_sum_one
30: test_stratified_split_is_reproducible_and_balanced
63: test_metadata_label_mapping_matches_config
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_pipeline_faults_postgres.py — 6 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_pipeline_faults_postgres.py)

```text
21: test_calculation_success_database_rejects_without_false_success
48: test_commit_visible_lost_client_ack_and_repeat_finalize
67: test_disposable_process_sigkill_before_finalization
81: test_invalid_foreign_key_and_lost_test_connection
97: test_minimal_real_train_serialization_and_committed_readback
138: test_val_persistence_failure_preserves_verified_train
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_science_e7.py — 24 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_science_e7.py)

```text
74: test_protocol_document_and_full_matrix
94: test_frozen_protocol_change_rejected
103: test_positive_metrics_and_confusion
131: test_undefined_is_absent_with_reason
138: test_strict_threshold_098_not_success_and_stable_ties
153: test_baseline_is_tradeoff
158: test_patient_bootstrap_reproducible_and_paired
178: test_seed_variability_not_pooled
189: test_compare_lineage_protocol_and_empty_report
224: test_incompatible_evidence_excluded
245: test_historical_protocol_exploratory_not_relabelled
262: test_ambiguity_and_incomplete_exclusion
298: test_candidate_complete_matrix_deterministic_and_unmet
323: test_export_never_falls_back_on_database_failure
333: test_exact_e6_reader_revalidates_and_rejects_inconsistency
355: test_e4_plan_reconstructs_exact_frozen_configurations
373: test_report_artifact_protocol_and_metrics_correspondence
397: test_no_patient_independence_imputed_and_no_test_tuning
410: test_campaign_inventory_keeps_failures_and_first_verified_policy
482: test_freeze_rejects_missing_candidate_without_database
493: test_explain_exact_parent_rejection
515: test_invalid_prediction_mapping_duplicate_and_nonfinite
530: test_structured_export_and_curves_follow_persisted_report
555: test_export_refuses_to_replace_another_report
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_science_postgres.py — 3 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_science_postgres.py)

```text
35: test_report_roundtrip_idempotent_immutable_and_rollback
98: test_report_failed_write_no_export_and_savepoint_recovery
135: test_e6_explanation_inventory_and_final_lock_without_inference
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_threshold_calibration.py — 6 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_threshold_calibration.py)

```text
20: test_find_threshold_for_target_recall_satisfies_target_when_possible
38: test_find_threshold_uses_secondary_specificity_then_highest_threshold
52: test_find_threshold_fallback_when_target_not_reached
65: test_threshold_applied_to_probability_parasitized
77: test_build_threshold_candidates_includes_default_threshold
84: test_test_set_cannot_be_used_for_calibration
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_threshold_calibration_tracking.py — 3 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_threshold_calibration_tracking.py)

```text
27: test_record_threshold_calibration_passes_model_name_from_context
44: test_log_threshold_calibration_extracts_selected_metrics
92: test_log_threshold_calibration_skips_missing_selected_threshold
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_train_checkpoint_policy_args.py — 3 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_train_checkpoint_policy_args.py)

```text
14: test_train_cli_defaults_to_auc_with_min_recall
24: test_train_cli_accepts_f2_policy
40: test_allow_collapsed_checkpoint_disables_rejection
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_train_integration.py — 4 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_train_integration.py)

```text
16: test_execution_type_is_derived_from_fine_tune_epochs
20: test_train_accepts_densenet_combined_execution_parameters
48: test_train_accepts_checkpoint_policy_and_calibration_args
81: test_densenet_rejects_vgg16_preprocessing
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_training_history_outputs.py — 3 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_training_history_outputs.py)

```text
61: test_history_contains_required_columns_and_canonical_file
78: test_missing_optional_metrics_do_not_block_history
88: test_fine_tuning_epochs_are_continuous_and_marker_is_first_ft_epoch
```

</details>

<details>
<summary>malaria_dl_local_project/tests/test_training_selection.py — 2 funciones</summary>

[Abrir archivo](../../../malaria_dl_local_project/tests/test_training_selection.py)

```text
17: test_parasitized_recall_treats_label_one_as_clinical_positive
26: test_monitor_mode_uses_min_for_loss_and_max_for_clinical_metrics
```

</details>

Total del catálogo: **328 funciones de prueba localizadas; cero ejecutadas en E10.0**.

Comprobaciones reproducibles utilizadas (sólo lectura, excepto la creación de este Markdown): `git status --short --untracked-files=all`; `git ls-files`; `rg` sobre productores, SQL, kinds e imports; `ast.parse` de fuentes/tests y validación de existencia/rangos de referencias. Las búsquedas no interpretan los nombres de tests como evidencia de éxito.

Resultado de la validación estática de este entregable: firma y ocho kinds contrastados por AST; 15 secciones numeradas; referencias de archivos/rangos, enlaces relativos y nombres de tests de las tablas comprobados sin errores. `git diff --check` sin errores en archivos tracked; no hay cambios tracked. Estado final esperado y observado:

```text
?? docs/engineering/e10_execution_refactor/baseline.md
```
