# Campañas: creación, configuración de modelos y ejecución (Docker y local)

Referencia técnica de cómo se crea una campaña, de dónde vienen sus datos, cómo se leen
y configuran los tres modelos habilitados (CustomCNN, VGG16, DenseNet121), y cómo se
ejecuta el TRAIN resultante — en el coordinador Docker y en el agente local (Mac) — y
qué mecanismos concilian ambas rutas.

Estado del ejecutor local a la fecha de este documento: implementado y verificado
(pruebas reales en PostgreSQL desechable + un intento real completo contra la campaña
`3acf89b7-dc42-4b7a-8e2a-ca6ea024c344`, ver `docs/audits/e9_3_local_agent_2026-09-15/`).
No confundir con resolución del OOM que motivó su construcción: eso sigue sin
diagnosticar.

## 1. Modelo de datos

Todas las tablas viven en PostgreSQL, gestionadas por Alembic
(`alembic/versions/`). Ninguna tiene equivalente en el sistema legacy de reportes
(`run_metrics`, `model_versions`, `artifacts`, etc.) — es una decisión de diseño
documentada, no un descuido (ver `docs/engineering/etapa_6_evaluate_explain_2026-09-11.md`).

| Tabla | Migración | Función |
|---|---|---|
| `experimental_campaigns` | `20260911_01_experimental_campaigns` | La campaña: `id`, `name`, `purpose`, `state` (`draft→frozen→active↔paused→finalized`), `dataset_version_id`, `dataset_snapshot` (jsonb), `dataset_evidence_id`, `requested`/`protocol`/`environment` (jsonb, congelados al `freeze`), `contract` (jsonb, la matriz expandida completa), `contract_hash`. |
| `campaign_members` | `20260911_01_...` | Una combinación `modelo × optimizador × semilla × variante` de la matriz. `id`, `campaign_id`, `position`, `configuration_hash` (apunta a `contract->matrix->configurations`), `state` (`pending/active/failed/interrupted/completed/verified/excluded`), `accepted_attempt_id`. |
| `campaign_attempts` | `20260911_01_...` | Cada vez que se lanza un TRAIN para un miembro. `id`, `member_id`, `ordinal`, `state`, `training_run_id`, `cause`, `finished_at`. Presupuesto de reintentos: `protocol.budget.max_attempts_per_member`. |
| `runs` | preexistente + `campaign_id` (columna nullable, ver `docs/engineering/campaign_scope_2026-09-14/decision_y_procedimiento.md`) | Identidad relacional del TRAIN: `model_id` (FK real a `models`), `run_type='training'`, `status`, `dataset_version_id`, `execution_parameters` (jsonb: `model_configuration_e2.configuration` = la config resuelta completa + `dataset_verification_evidence_id`). Las corridas legacy conservan `campaign_id=NULL`; nunca se infiere pertenencia por fecha. |
| `train_execution_sessions` | `20260912_01_train_execution` | Una fila por `run_id` (PK). `attempt_id`, `owner` (uuid de propiedad), `host`, `parent_pid`, `child_pid`, `state` (`active/completed/verified/failed/interrupted`), `configuration`/`dataset`/`environment` (jsonb, snapshot al reservar), `artifact_root`, `completion` (jsonb, al terminar el fit), `verification` (jsonb, tras re-verificar), `cause`. |
| `train_execution_records` | `20260912_01_...` | Evidencia append-only. PK `(run_id, kind, phase, record_key)`. `kind` ∈ `runtime/epoch/artifact_prepared/artifact/predictions/selection/phase/calibration`. Trigger `train_record_guard` exige `state='active'` y propietario correcto (`capstone.train_owner`). |
| `campaign_execution_events` | `20260911_01_...` | Log de pausas/reanudaciones de campaña (`code`, `created_at`). |
| `campaign_technical_revisions` | `20260914_01_controlled_train` | Revisión técnica explícita para un intento controlado: `payload` (`original_environment`, `environment`, `contract_hash`, `reason`, `files` con hashes, `tests`, `authorization`), `payload_hash`. Sólo se puede registrar con campaña `paused`; **inmutable** una vez creada. |
| `campaign_controlled_requests` | `20260914_01_...` | Idempotencia del intento único controlado, por `request_id`. |
| `experiment_execution_gate` | `20260914_02_global_execution` | Fila singleton: exclusividad global. `owner` (uuid o null), `db_pid`, `process_evidence` (jsonb: identidades de proceso + `release_confirmed`), `blocked_reason` (circuito de OOM/fallos). |
| `local_execution_jobs` | `20260915_01_local_execution` | Un job del agente local: `principal`, `agent_id`, `owner`, `request_hash`, `campaign_id`, `run_id`, `state` (`held/calculation_reported/released/failed`), `session`/`result`/`completion`/`exit_proof` (jsonb), `heartbeat_at`. Índice único parcial: sólo un job `held`/`calculation_reported` a la vez. |

## 2. Origen de los datos

El dataset es gobernado, no un directorio suelto. Todo TRAIN referencia un
`dataset_version_id` (hoy: `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`), verificado en cada
paso crítico vía `persistence/dataset_evidence.py::verify_dataset_for_execution` contra
la evidencia sellada en `audit_events` (tipo `ml.dataset_verification`). Esa función
devuelve un `GovernedDatasetSnapshot` (`data/governed_dataset.py`): `dataset_version_id`,
`dataset_materialization_id`, `dataset_root` (ruta absoluta — dentro del contenedor
Docker, `/app/malaria_dl_local_project/data/malaria_dataset_versions/<id>`), y cuatro
fingerprints (`patient_assignment`, `record_assignment`, `source_population`,
`clinical_identity`) más `counts` por partición (train/val/test).

- **En la creación** (`CampaignService.create`) y **al congelar** (`freeze`), se llama a
  `verify_dataset_for_execution` y se persiste el snapshot dentro de
  `experimental_campaigns.dataset_snapshot`/`contract.dataset`.
- **En cada preflight de ejecución** (`execution/campaign.py::preflight`,
  `local_execution/backend.py::preflight`) se vuelve a verificar y se compara con
  `data/governed_dataset.py::assert_run_dataset_snapshot_unchanged` — si el dataset
  cambió desde el congelamiento, la ejecución se rechaza.
- TRAIN **nunca** toca la partición TEST (`config["resolved"]["execution"]["evaluate_best_on_test"]`
  debe ser `False`; `execution/campaign.py::preflight` lo exige explícitamente,
  `CampaignError('TEST_FORBIDDEN')` si no).
- Conteos actuales del dataset: TRAIN 22180, VAL 2693, TEST 2685 (121/15/15 pacientes
  por clase, sin sumar sin deduplicar).

## 3. Creación de una campaña

CLI exclusivo: `python -m src.campaign <operación>`
(`malaria_dl_local_project/src/campaign.py`), siempre dentro del contenedor backend. No
hay endpoint HTTP ni pantalla de frontend para crear/editar campañas.

```sh
docker compose exec -T -w /app/malaria_dl_local_project backend \
  python -B -m src.campaign inspect  --request matrix-request.json --protocol protocol-draft.json
docker compose exec -T -w /app/malaria_dl_local_project backend \
  python -B -m src.campaign create   --request matrix-request.json --protocol protocol-draft.json \
    --dataset-version-id "$DATASET_VERSION_ID" --name "..." --purpose "..." --actor "$ACTOR"
docker compose exec -T -w /app/malaria_dl_local_project backend \
  python -B -m src.campaign edit     --campaign-id "$CAMPAIGN_ID" --request ... --protocol ...
docker compose exec -T -w /app/malaria_dl_local_project backend \
  python -B -m src.campaign validate --campaign-id "$CAMPAIGN_ID"
docker compose exec -T -w /app/malaria_dl_local_project backend \
  python -B -m src.campaign freeze   --campaign-id "$CAMPAIGN_ID" --dataset-version-id "$DATASET_VERSION_ID"
docker compose exec -T -w /app/malaria_dl_local_project backend \
  python -B -m src.campaign show     --campaign-id "$CAMPAIGN_ID"
```

`CampaignService` (`campaigns/service.py`) implementa cada operación:

- **`inspect(request, protocol)`** → `campaigns/contracts.py::expand_matrix` — sólo
  valida y expande, no conecta a BD.
- **`create(...)`** → `inspect()` + `verify_dataset_for_execution` + `self.environment()`
  (`planning_environment()`: hash SHA-256 de todo `src/`+`configs/`+`run_*.py`, versión
  de Python/TensorFlow, git commit si está disponible, variables de determinismo) →
  `CampaignRepository.create(...)`, estado `draft`.
- **`edit(...)`** — sólo permitido en `draft`.
- **`validate(campaign_id)`** — en `draft` resuelve la matriz completa (sin persistir);
  en `frozen` devuelve el contrato ya guardado. Lectura pura.
- **`freeze(...)`** — reexpande la matriz con `frozen=True`, exige que
  `planning_environment()` **no** haya cambiado desde el `create` (si cambió:
  `DRAFT_CODE_ENVIRONMENT_CHANGED_CREATE_NEW_DRAFT`), reverifica el dataset, y escribe
  `contract` (`version: campaign_contract_v1`, incluye `matrix` completa) + `contract_hash`.
  A partir de aquí el contrato es **inmutable**.

### La matriz (`campaigns/contracts.py::expand_matrix`)

`request = {models, optimizers, seeds, variants, exclusions}`. `models=null` expande a
`enabled_models()` (los tres modelos habilitados). Cada `variant` puede sobreescribir
config por variante y por modelo (`by_model`), nunca incluye `seed` en `selected`. El
producto `modelos × optimizadores × semillas × variantes` menos `exclusions` genera las
`campaign_members`; cada combinación se resuelve vía `models/configuration.py::resolve_config`
y su hash de configuración identifica la fila en `contract.matrix.configurations`.
Ejemplo real (`configs/science/e7_campaign_plan.json`, campaña actual): 3 modelos × 4
optimizadores (`adadelta, adam, adamw, sgd`) × 3 semillas (`11, 29, 47`) = 36 miembros.

### El protocolo

JSON aportado por el usuario (nunca inventado): métricas primaria/secundaria, roles de
partición (`train/selection=val/calibration=val/final_test=test`), política de
checkpoint/early-stopping, calibración de threshold, presupuesto (`max_members`,
`max_attempts_per_member`), manejo de faltantes/reintentos, `test_access:
final_only_after_candidate_lock`. Fuerza `evaluate_best_on_test=false` en cada
configuración resuelta. `tests/test_campaigns_e4.py::protocol()` documenta la forma
completa (valores sintéticos, no recomendación científica).

## 4. Cómo se leen y configuran los modelos

### Registro (`models/registry.py`)

`MODEL_REGISTRY` es un `dict[str, ModelDescriptor]` poblado al importar el módulo, con
exactamente estas tres entradas:

| `id` | alias | adapter | `version` | `strategies` | preprocesamiento externo | preprocesamiento interno |
|---|---|---|---|---|---|---|
| `custom_cnn` | — | `CustomCNNAdapter` | 1.0 | `("base",)` | `rescale_0_1` | ninguno |
| `vgg16` | `vgg16_transfer_learning` | `VGG16Adapter` | 1.1 | `("base","fine_tuning")` | `vgg16_imagenet` | ninguno |
| `densenet121` | — | `DenseNet121Adapter` | 1.0 | `("base","fine_tuning")` | `rescale_0_1` | `densenet_imagenet_channel_mean_std` |

`resolve_descriptor(name)` busca por `id`/alias, exige `enabled and trainable`
(`MODEL_NOT_EXECUTABLE` si no) y unicidad (`UNKNOWN_OR_AMBIGUOUS_MODEL`).
`enabled_models()` devuelve los tres ids — es lo que usa `expand_matrix` cuando
`request.models` es `null`. Config JSON por modelo:
`malaria_dl_local_project/configs/models/{custom_cnn,vgg16,densenet121}.json`.

Único punto de entrada real: `models/configuration.py::resolve_config()` — **nunca** se
llama `resolve_descriptor` sin pasar también por `resolve_config`.

### Configuración (`models/configuration.py::resolve_config`)

Precedencia `defaults JSON < selected (variante) < overrides (CLI)`, vía
`merge_strict` (rechaza claves desconocidas; reemplaza `optimizer.parameters` entero, no
lo mezcla). Validación estricta tras el merge: `input_shape` cuadrado, canal 3, ≥32px;
`dropout`/`l2` en `[0,1)`; **`head_units` y `batch_normalization` no son realmente
configurables** — cualquier valor distinto al default del modelo lanza
`UNSUPPORTED_MODEL_PARAMETER`; `weights=imagenet` sólo permitido si el modelo declara
`fine_tuning` en `strategies`. Genera `input_contract` vía `data/input_contract.py::make_input_contract`
y lo congela en `resolved.input_contract`. El resultado (`resolved`) es lo que se
persiste tal cual en `runs.execution_parameters->model_configuration_e2->configuration`
y en `train_execution_sessions.configuration`.

### Valores por defecto reales

| | CustomCNN | VGG16 | DenseNet121 |
|---|---|---|---|
| `input_shape` | 200×200×3 | 200×200×3 | 200×200×3 |
| `weights` | `none` | `imagenet` | `imagenet` |
| `dropout` | 0.4 | 0.5 | 0.5 |
| `l2` | 0.0001 | 0.0 | 0.0 |
| `head_units` | 128 | 1024 | 0 (sin cabeza densa intermedia) |
| `fine_tune_layers` | 0 | 4 | 4 |
| `fine_tune_learning_rate` | 1e-5 | 1e-5 | 1e-5 |
| optimizer por defecto | adam (lr 1e-4) | adam | adam |
| `max_epochs` (perfil batch) | 100 | 100 | 100 |
| `fine_tune_epochs` (perfil batch) | 0 | 20 | 20 |
| `batch_size` | 64 | 64 | 64 |
| `seed` | 42 | 42 | 42 |

Perfil `batch=True` (el que usan las campañas): `early_stopping_patience=12`,
`checkpoint_monitor=early_stopping_monitor='val_f2_parasitized'`, `mode='max'`,
`calibrate_threshold=true`. `recipe` compartido: `binary_crossentropy`, métricas
`binary_clinical_v1`, augmentación (flip/rotación 0.07/traslación 0.2/zoom 0.2/contraste
0.3), reduce-LR en `val_loss` (factor 0.5, paciencia 4, mínimo 1e-6).

### Adaptadores (`models/adapters.py`)

- **`CustomCNNAdapter.build`** → `architectures.build_custom_cnn`: 4 bloques
  `Conv2D→BatchNorm→ReLU→MaxPool` (32/64/128/256 filtros) desde cero, sin backbone,
  `GlobalAveragePooling2D → Dense(128, relu, l2) → Dropout → Dense(1, sigmoid)`. Sin
  pesos preentrenados; `set_phase` es no-op (no hay backbone que congelar).
- **`VGG16Adapter.build`** → `tf.keras.applications.VGG16(include_top=False,
  weights=...)`. Pesos ImageNet descargados/cacheados por el propio mecanismo de Keras
  (`~/.keras/models`, verificación de hash oficial incluida). Todas las capas del
  backbone parten `trainable=False`; cabeza `GlobalAveragePooling2D → Dense(1024, relu)
  → Dropout(0.5) → Dense(1, sigmoid)`.
- **`DenseNet121Adapter.build`** → `tf.keras.applications.DenseNet121(include_top=False,
  weights=...)`, con una capa `Normalization` (media/varianza ImageNet) **dentro del
  grafo Keras**, antes del backbone — es el preprocesamiento interno declarado en el
  registro. Cabeza mínima: `GlobalAveragePooling2D → Dropout(0.5) → Dense(1, sigmoid)`
  (sin densa intermedia, `head_units=0`).

`fine_tune_layers` decide cuántas capas finales del backbone se descongelan en la fase
`fine_tuning` (`set_phase`); `fine_tune_epochs` cuántas épocas corre esa fase;
`fine_tune_learning_rate` reemplaza el `learning_rate` del optimizador sólo en esa fase.

### De `session["configuration"]` a modelo compilado (`execution/train.py::train`)

1. `config = session["configuration"]; r = config["resolved"]` — ya resuelto por
   `resolve_config` en el momento de la reserva; `train()` **no** vuelve a resolver.
2. Construcción de datasets (`data/*`) usando `r.model.input_shape[0]` y
   `r.model.preprocessing`.
3. `adapter = descriptor.create_adapter()` — instancia la clase vía el string
   `"módulo:Clase"` del registro.
4. `built = adapter.build(r)` → modelo sin compilar (`AdapterResult`).
5. Por cada fase (`base`, y `fine_tuning` si `fine_tune_epochs>0`):
   `execution/train.py`/`models/adapters.py::compile_phase(adapter, built, r, phase)` —
   aplica `set_phase` (congela/descongela), valida el `input_contract` contra el modelo
   real, compila (`architectures.compile_binary_model`) y corre `model.fit(...)` con los
   callbacks de selección/calibración, persistiendo checkpoint por época.

Puntos de llamada a `resolve_descriptor` en todo el repo: `execution/campaign.py`
(preflight, valida adaptador/versión congelados contra el registro actual antes de
ejecutar), `execution/worker.py` (worker Docker), `local_execution/worker.py` (worker
Mac), y el CLI de `execution/train.py`. Ningún otro sitio.

## 5. Ejecución de la campaña

Tres caminos, mismo motor interno (`ExecutionRepository`/`ControlledRepository` +
`execution/train.py::train`):

### A) Cola secuencial — coordinador Docker

```sh
docker compose exec backend python -m run_train_all_models \
  --campaign-id "$CAMPAIGN_ID" --dataset-version-id "$DATASET_VERSION_ID" \
  --artifact-root /app/var/artifacts/campaign_runs   # [--resume]
```

`execution/campaign.py::execute_campaign` — bucle: `ExecutionRepository.claim()` toma el
siguiente miembro elegible (`FOR UPDATE`, presupuesto no agotado) → `run_child()` lanza
`python -m src.malaria_dl.execution.worker` como **subproceso Linux real** (handshake
por pipe, registrado en `GlobalGate`, `start_new_session=True`) → espera su salida →
`verify_session()` (rehash + carga real del checkpoint) → `finish(..., 'verified')`.
Falla sistémica → `pause(campaign, 'SYSTEMIC_<excepción>')`, nunca sigue encadenando a
ciegas.

### B) Intento único controlado

```sh
docker compose exec backend python -m src.malaria_dl.execution.controlled execute \
  --campaign-id "$CAMPAIGN_ID" --dataset-version-id "$DATASET_VERSION_ID" \
  --member-id "$MEMBER_ID" --previous-attempt-id "$PREVIOUS_ATTEMPT_ID" \
  --revision-id "$REVISION_ID" --request-id "$(uuidgen)" --reason "..." \
  --artifact-root /app/var/artifacts/campaign_runs
```

`ControlledRepository.reserve()` exige campaña `paused`, miembro `failed`/`interrupted`,
una `campaign_technical_revisions` ya registrada, y es **idempotente por
`request_id`**. Un único run, sin encadenar al resto de la matriz.

### C) Ejecución local (Mac) + backend/PostgreSQL en Docker

```sh
cd malaria_dl_local_project
.venv-local-train/bin/python -m src.malaria_dl.local_execution.agent start \
  --config agent_config.json --state agent_state.json
```

Ver sección 6 — es el mismo ciclo B (o secuencial) pero el subproceso TRAIN corre
nativamente en el Mac y reporta por HTTP, nunca por SQL directo.

### Ciclo de vida de un TRAIN individual (los tres caminos)

1. Reserva atómica (`claim`/`reserve`) → `campaign_attempts` + `runs` +
   `train_execution_sessions('active')` en una transacción.
2. `train()` entrena; cada `put()` (kind `epoch/artifact_prepared/artifact/predictions/
   selection/phase/calibration`) es su propia transacción — archivo y fila de BD **no**
   son atómicos entre sí por diseño (el archivo se cierra y renombra antes de registrar
   su hash).
3. `finish(..., 'completed', evidence)` — `evidence.records_hash = digest(records)`.
4. El padre (coordinador o agente) espera la salida **real** del proceso y sólo entonces
   llama `verify_session()`: rehashea el checkpoint seleccionado, lo **carga de
   verdad**, valida completitud de todos los registros → `finish(..., 'verified')`.
5. Recién ahí se libera la reserva; el siguiente trabajo (si aplica) se pide después.

### Exclusividad global (`execution/global_gate.py`)

Un único experimento gestionado activo en todo el sistema, sin importar el camino.
`GlobalGate` toma un advisory lock de PostgreSQL (`120994,1`), exige prueba de que
ningún proceso del intento anterior sigue vivo (`verify_retained_processes`, vía
`/proc`), se vuelve subreaper del hijo, y sólo entonces marca
`experiment_execution_gate.owner`. Vencimiento de heartbeat o SIGKILL nunca se tratan
como "terminó limpio": se exige evidencia explícita de ausencia de proceso.
`blocked_reason` es un circuito de seguridad (nuevo OOM del contenedor, fallos
consecutivos) que requiere reconciliación explícita, nunca automática.

## 6. Diferencia entre ejecución Docker y ejecución local — y cómo se concilian

El ejecutor local (`malaria_dl_local_project/src/malaria_dl/local_execution/`) existe
para sacar el cómputo del **límite de memoria del contenedor Docker**, manteniendo
backend y PostgreSQL en Docker. No es una ruta separada del motor de campañas: reutiliza
`ControlledRepository`/`ExecutionRepository`/`train()` sin cambios — sólo cambia **cómo
se reporta el progreso**.

| | Docker (`run_child`/`execution/worker.py`) | Local (`local_execution/agent.py` + `worker.py`) |
|---|---|---|
| Dónde corre el TRAIN | Subproceso Linux dentro del contenedor backend | Subproceso Python nativo en el Mac (arm64) |
| Cómo persiste progreso | `ExecutionRepository.put/finish` → SQL directo | `local_execution/transport.py::Reports` → HTTP a `POST /execution/local/{operation}` → el backend (en Docker) ejecuta el mismo `put/finish` |
| Acceso a PostgreSQL | Directo (`db:5432`, sólo desde el backend) | **Nunca** directo — el agente no importa `psycopg`/`SQLAlchemy` |
| Exclusividad | `GlobalGate` (Python, clase completa: advisory lock + subreaper + `/proc`) | `LocalBackend.claim()` (`local_execution/backend.py`): mismo advisory lock tomado por SQL directo, sin la clase `GlobalGate` — **sin mecanismo de `acknowledge`** para el circuito de OOM (a diferencia de Docker) |
| Heartbeat | Implícito (el proceso padre espera al hijo) | Explícito: hilo separado, 15s de intervalo, 60s de vencimiento (`local_execution/processes.py`) — vencido ⇒ `communication:'uncertain'`, nunca libera solo |
| Identidad de proceso | `/proc` del contenedor (Linux) | `processes.py::ProcessTracker` (psutil, funciona en Darwin/Linux) — **pero** el chequeo cruzado "¿hay un coordinador Docker vivo?" (`process_table()`/`managed_execution`) sigue siendo Linux-only (`/proc`), así que sólo funciona cuando se ejecuta *dentro* del backend (correcto, porque `LocalBackend` siempre corre ahí, nunca en el Mac) |
| Checkpoint | Se escribe y se lee desde el mismo filesystem del contenedor | Se escribe en el Mac; el backend necesita **leerlo también** para `verify_session`/`load_checkpoint` (subproceso `keras_loader` corre dentro del contenedor) → requiere una raíz de artefactos **compartida** (bind mount Mac↔contenedor) |
| Identidad de entorno | `planning_environment()` corriendo en el contenedor (Linux, Python del contenedor) | Debe declarar explícitamente `execution_mode='local_python', platform='Darwin', machine='arm64', device='CPU', precision='float32'` (`local_execution/revision.py::valid_environment`) — **nunca se afirma equivalencia numérica exacta** con Linux sin evidencia |
| Autorización de la revisión técnica | No aplica (mismo entorno que congeló la campaña) | Obligatoria: `ControlledRepository.register_revision` con un payload `local_python` explícito, campaña `paused`, revisión inmutable una vez registrada |
| Mapeo de rutas | Ninguno — todo vive dentro del contenedor | `dataset_root_id`/`artifact_root_id` — identificadores lógicos, nunca rutas absolutas del Mac en los contratos; se resuelven vía `CAPSTONE_LOCAL_STORAGE_ROOTS` (backend, rutas del contenedor) y el `roots` de `agent_config.json` (Mac, rutas reales) por separado |
| Auth de la API | No aplica (llamadas Python internas) | JWT real (`AUTH_MODE=local_jwt`) + `Permission.SYSTEM_ADMIN`; `CAPSTONE_LOCAL_EXECUTION_ENABLED=1` explícito — deshabilitado por defecto |

### Cómo se resuelven concretamente estas diferencias (lo verificado el 15/09/2026)

1. **Nunca dos coordinadores a la vez.** `LocalBackend.claim()` toma el mismo advisory
   lock (`120994,1`) y escribe `process_evidence={'release_confirmed': false, ...}`
   mientras el job local está vivo — cualquier `GlobalGate` Docker que intente entrar
   choca con `PROCESS_TREE_RELEASE_UNPROVEN`. En la otra dirección, mientras Docker tiene
   el lock de sesión, el `pg_try_advisory_xact_lock` del agente falla de inmediato
   (`GLOBAL_EXPERIMENT_BUSY`). Verificado con pruebas reales
   (`test_local_job_blocks_docker_gate_while_held`, `test_docker_gate_blocks_local_claim`
   en `malaria_dl_local_project/tests/test_local_execution_postgres.py`).
2. **Checkpoint compartido.** Se agregó un bind mount dedicado
   (`./malaria_dl_local_project/local_execution_artifacts:/app/var/local_artifacts`,
   `docker-compose.override.yml`) para que el backend (Linux) pueda leer y verificar el
   checkpoint que el agente escribió en el Mac — sin este mount, `verify_session` fallaría
   siempre al final de un TRAIN real, después de horas de cómputo.
3. **Migración necesaria pero no aplicada por defecto.** La tabla `local_execution_jobs`
   requiere `alembic upgrade` explícito (`20260915_01_local_execution`); el ejecutor
   local queda inoperante hasta que se aplica deliberadamente (`make db-migrate`,
   nunca un upgrade manual fuera del wrapper).
4. **El entorno se declara, nunca se asume.** `valid_environment()` exige los campos
   `execution_mode/platform/machine/device/precision` explícitos; con eso,
   `validate_revision` permite que el resto del entorno (versiones de paquetes, hash de
   fuente) difiera del entorno Docker sin exigir igualdad byte a byte — pero exige que
   la revisión técnica quede registrada, con archivos/hashes/tests/justificación.
5. **Verificado realmente, no sólo en teoría**, mediante un recorrido real
   (uvicorn nativo en el Mac apuntando a un esquema Postgres desechable, agente y worker
   como subprocesos reales, TensorFlow 2.17.1 real en CPU arm64, checkpoint real
   hasheado y recargado): ~600–660 ms/lote nativo vs. ~4 s/lote observado en el
   contenedor Docker el 14/09 — evidencia a favor de que el límite de memoria del
   contenedor influía, **no** un diagnóstico de causa raíz.

## 7. Archivos clave (referencia rápida)

| Archivo | Rol |
|---|---|
| `malaria_dl_local_project/src/campaign.py` | CLI de planificación (create/edit/validate/freeze/show) |
| `.../campaigns/contracts.py` | `expand_matrix`, `canonical`, `digest`, validaciones de protocolo/matriz |
| `.../campaigns/service.py` | `CampaignService`, `planning_environment()` |
| `.../campaigns/repository.py` | `CampaignRepository` (persistencia E4) |
| `.../execution/repository.py` | `ExecutionRepository` — `claim/put/finish/pause/resume/standalone` |
| `.../execution/controlled.py` | `ControlledRepository` — intento único, revisión técnica, CLI `execute/register/recover/dry-run` |
| `.../execution/campaign.py` | Coordinador secuencial Docker — `execute_campaign`, `run_child`, `reconcile` |
| `.../execution/worker.py` | Entrypoint del subproceso TRAIN en Docker |
| `.../execution/train.py` | `train(repository, session, descriptor)` — motor de entrenamiento compartido |
| `.../execution/artifacts.py` | `verify_session`, `file_identity`, `keras_loader` |
| `.../execution/global_gate.py` | `GlobalGate`, exclusividad global, `/proc` |
| `.../models/registry.py` | `MODEL_REGISTRY`, `resolve_descriptor`, `enabled_models` |
| `.../models/configuration.py` | `resolve_config` — defaults + variante + overrides |
| `.../models/adapters.py` | `CustomCNNAdapter`, `VGG16Adapter`, `DenseNet121Adapter`, `compile_phase` |
| `.../local_execution/backend.py` | `LocalBackend` — reserva/heartbeat/record/exit vía HTTP, dentro del backend Docker |
| `.../local_execution/agent.py` | Agente CLI que corre en el Mac |
| `.../local_execution/worker.py` | Entrypoint del subproceso TRAIN local |
| `.../local_execution/transport.py` | `Api`, `Reports` — adaptador HTTP del mismo contrato `put/records/finish` |
| `.../local_execution/storage.py` | Rutas relativas seguras, hash post-cierre |
| `.../local_execution/processes.py` | Heartbeat, identidad de proceso multiplataforma |
| `.../local_execution/revision.py` | `valid_environment` — contrato del entorno `local_python` |
| `backend_api/app/routes/local_execution.py` | Ruta HTTP `/execution/local/{operation}` |
| `run_train_all_models.py` | Entrypoint real del coordinador Docker (delega a `execution.campaign.main`) |

## 8. Limitaciones y estado conocido

- El OOM que motivó el ejecutor local **no está diagnosticado**; el ejecutor local
  evita el síntoma (límite de memoria del contenedor), no explica la causa.
- El motor de campañas no escribe en las tablas legacy de reportes
  (`run_metrics`/`model_versions`/`artifacts`) — es deliberado (E6), no un bug. Un
  lector nuevo (no un escritor) fue agregado a `backend_api/app/services/training_summaries.py`
  para mostrar métricas VAL de campaña donde antes no había ninguna.
- La ruta `POST /execution/local/{operation}` aún no tiene auditoría central
  (`app.audit`) en su cadena de dependencias FastAPI — hallazgo pendiente, no resuelto.
- `LocalBackend.claim()` no implementa `acknowledge` para el circuito de OOM; limpiarlo
  requiere siempre una decisión administrativa explícita y documentada, nunca un
  bypass automático.
