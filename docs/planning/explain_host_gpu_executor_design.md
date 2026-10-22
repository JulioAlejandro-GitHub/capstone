# EXPLAIN desde el reporte en la GPU del host

Estado: implementado el 2026-10-22 (pendiente: caché de modelo entre solicitudes, §4.2.4).

Uso: `scripts/host_services.sh start` (ambos servicios) · `status` · `restart` · `stop` · `logs explain` · `uninstall`.
Componentes: `alembic_v2/explain_host_executor.sql`, `backend_api/app/services/explain_agent.py`,
`explain_execution.py` (lógica compartida con el worker de Docker), `explain_host.py` (política y cola),
`GET /explain-generations/executor`, `scripts/host_service.py` (entrada launchd) y `scripts/host_services.sh`.
Medido: LIME de una célula en GPU Apple M4 Max 7,3 s (≈2 min en la CPU emulada del contenedor).

## 1. Situación actual

```
Navegador ──POST /explain-generations──▶ backend (Docker)
                                          │ ExplainService.submit: reutiliza si existe
                                          ▼
                                   ExplainLauncher → subprocess `python -m app.services.explain_worker`
                                          │ GlobalGate('assessment-explain-http')
                                          │ reusable → prepare → reserve_execution → handshake (≤60 s) → START
                                          ▼
                                   execute_reserved por método, en CPU del contenedor
```

- El contenedor del backend solo ve `CPU:0` y corre `linux/amd64` (forzado en `docker-compose.yml`, `platform: linux/amd64`) sobre un Mac arm64: TensorFlow va **emulado**. Un SHAP de 1.000 perturbaciones tarda ~2 min.
- La GPU (tensorflow-metal) solo existe en el host, en `.venv-metal`, para ejecuciones lanzadas por CLI con `execution/local_launch.py`: valida el venv, construye `DATABASE_URL` hacia `127.0.0.1:5432` con el rol `capstone_v2_runtime` y habla **directamente con PostgreSQL** ("no HTTP API, no JWT"). `execution/accelerator.py` exige GPU en ese modo y ejecuta un canario (meta-optimizer desactivado por el error de `relu(bias_add(matmul))` en Metal).
- `GlobalGate` ya serializa ejecuciones entre procesos mediante un advisory lock en PostgreSQL, por lo que coordina host y Docker por igual.
- Las rutas escritas por el host (`/Users/.../malaria_dl_local_project/...`) se resuelven en Docker con `storage_paths.local_scientific_path` (`outputs/train_runs`, `outputs/campaign_runs`, `artifacts/assessments`).

## 2. Objetivo y límites

- Objetivo: que "Generar LIME / SHAP / faltantes" del reporte ejecute en la GPU del host, con la misma identidad, reutilización y verificación que hoy.
- Fuera de alcance: cambiar el contrato científico de EXPLAIN, exponer el host a la red, EVALUATE/TRAIN desde la interfaz (el mecanismo quedaría reutilizable).

## 3. Opciones

| Opción | Cómo | A favor | En contra |
|---|---|---|---|
| A. Runtime HTTP en el host (como YOLO en `host.docker.internal:8765`) | El backend envía la solicitud a un servicio del host que ejecuta el worker | Respuesta inmediata; patrón ya usado | Nueva superficie de red y autenticación backend↔host; el servicio debe estar arriba; dos procesos validan lo mismo |
| **B. Cola en PostgreSQL + agente en el host (recomendada)** | El backend encola; un agente del host la toma con `FOR UPDATE SKIP LOCKED` y ejecuta | Sin puertos nuevos; mismo principio que `local_launch` (solo PostgreSQL); el backend no necesita alcanzar el host; tolera reinicios | Requiere tabla nueva y un proceso del host en ejecución |
| C. Seguir en Docker, sin emulación | Construir el backend `linux/arm64` | Mejora inmediata e independiente | Sigue sin GPU (Docker en macOS no accede a Metal) |

Recomendación: **B**, y evaluar **C** por separado como mejora rápida (hay que confirmar por qué se fijó `linux/amd64`; TensorFlow 2.17 publica ruedas `aarch64`).

## 4. Diseño recomendado

### 4.1 Datos (migración)

`explain_requests`

| Columna | Uso |
|---|---|
| `id uuid` | Identificador de la solicitud (= `operation_id` actual) |
| `request jsonb` | `ExplainRequest` validado (source_attempt_id, sample_id, methods, class_id, num_samples, background) |
| `actor text` | Usuario auditado |
| `executor text` | `host_gpu` \| `docker_cpu` |
| `state text` | `queued` → `claimed` → `running` → `completed` \| `failed` \| `cancelled` |
| `claimed_by jsonb` | Identidad del proceso (`host`, `boot_id`, `pid`, `start_ticks`) como en `GlobalGate` |
| `operations jsonb` | `[{method, attempt_id, state, error}]` por método |
| `cause text`, `created_at`, `claimed_at`, `finished_at` | Diagnóstico |

Índice único parcial por (`source_attempt_id`, `sample_id`, `class_id`, `num_samples`, `background`, método) mientras `state in (queued, claimed, running)`: un doble clic o dos pestañas no encolan dos veces lo mismo.

`executor_heartbeats`: `host`, `pid`, `device` (p. ej. `GPU:0 · Apple M…`), versiones de TensorFlow y tensorflow-metal, resultado del canario, `last_seen`. Lo escribe el agente cada ~10 s.

### 4.2 Agente del host: `python -m src.explain_agent`

1. Arranque con `local_launch.bootstrap()` (venv `.venv-metal`, Python 3.12, `DATABASE_URL` a loopback) y `accelerator.configure(tf)` con canario; si falla, no toma trabajo.
2. Bucle: latido; `SELECT … FROM explain_requests WHERE state='queued' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1` → `claimed`.
3. Ejecuta la **misma** lógica que hoy `explain_worker.execute` (se mueve a `malaria_dl` y la usan el worker de Docker y el agente): `GlobalGate`, reutilización por método, `prepare`, `reserve_execution`, `execute_reserved`. Actualiza `operations` y `state`.
4. Caché del modelo por SHA-256 del checkpoint entre solicitudes (1–2 modelos, sujeto a `GlobalGate.resources()`), para no recargar VGG16 en cada célula.
5. Al reiniciar, recupera solo sus propias solicitudes `claimed/running` comprobando sus PID (mismo host), igual que `repository.recover`. No se declara muerto un proceso por tiempo: el docstring de `GlobalGate` lo prohíbe.

### 4.3 Backend

- `ExplainService.submit`: valida el contexto y reutiliza como hoy. Si falta algún método, según `EXPLAIN_EXECUTOR`:
  - `host_gpu`: encola y responde 202 con `operations[].state = 'queued'`; si no hay latido reciente, 409 `EXPLAIN_HOST_EXECUTOR_UNAVAILABLE`.
  - `docker_cpu`: comportamiento actual.
  - Decidido (2026-10-22): no hay modo `auto` ni caída silenciosa a CPU. Sin latido reciente, la generación desde el reporte se bloquea y se avisa que se inicie el agente de GPU. `docker_cpu` queda solo como configuración explícita del entorno.
- `ExplainService.state`: incorpora las solicitudes en cola (`pending` con `executor`), además de los intentos.
- `GET /explain-generations/executor`: latido, dispositivo y antigüedad, para la interfaz.

### 4.4 Interfaz

- En Explicabilidad, un indicador "Ejecutor: GPU del host · activo". Sin latido reciente: aviso "Agente de GPU no activo. Inicia `python -m src.explain_agent` en el host (`.venv-metal`)", y los botones "Generar faltantes" y "Generar …" quedan desactivados con ese motivo. Se consulta el estado del ejecutor al abrir la sección y cada ~15 s, de modo que el botón se habilita solo al arrancar el agente.
- El botón bloqueado muestra "En cola · GPU del host" / "Generando en GPU del host…"; el resto del flujo (combinar EXPLAIN por célula, no reemplazar lo guardado) no cambia.

### 4.5 Integridad científica

- Reutilización: `compatible()` compara contexto científico y especificación del método, no el dispositivo; una célula ya explicada en CPU no se vuelve a generar en GPU (sin duplicados).
- Procedencia: registrar el dispositivo en `identity.code.accelerator` (o solo en el intento; §6). GPU y CPU pueden diferir numéricamente (~1e-4 en mapas); el reporte debe poder mostrarlo.
- Rutas: el host escribe rutas del Mac; Docker las resuelve con `local_scientific_path` (ya cubre `campaign_runs` y `artifacts/assessments`).
- Concurrencia con TRAIN en el host: `GlobalGate` hace esperar a EXPLAIN mientras TRAIN corre; la solicitud queda `queued`.

## 4.6 Arranque automático en macOS (launchd)

Preferido sobre la consola abierta. Dos LaunchAgents de usuario (no LaunchDaemon: Metal requiere la sesión gráfica del usuario):

| Agente | Programa | Condición |
|---|---|---|
| `cl.capstone.yolo-detector` | `.venv-metal/bin/python smear_segmentation_project/runtime_yolo.py --host 127.0.0.1 --port 8765` | Solo si `.env` tiene `CELL_DETECTOR_KEY=yolo26_seg_v1` |
| `cl.capstone.explain-agent` | `.venv-metal/bin/python -m src.explain_agent` | Siempre que se quiera EXPLAIN desde el reporte |

- `RunAtLoad` + `KeepAlive` con `SuccessfulExit=false`: arranca al iniciar sesión y se reinicia si falla; si el programa sale con 0 porque su condición no aplica (p. ej. otro `CELL_DETECTOR_KEY`), launchd no lo relanza.
- Un script de entrada lee `.env` y decide; launchd no evalúa `.env`.
- `WorkingDirectory` en el repositorio, `ProcessType=Interactive`, registros en `~/Library/Logs/Capstone/*.log` (`StandardOutPath`/`StandardErrorPath`).
- Instalación y control: `launchctl bootstrap gui/$(id -u) <plist>`, `launchctl kickstart -k gui/$(id -u)/cl.capstone.explain-agent`, `launchctl bootout …`; un script `scripts/host_services.sh install|status|restart|uninstall`.
- Restricción de privacidad de macOS: el proyecto está en `~/Desktop`, protegido por TCC. Un proceso lanzado por launchd no hereda el permiso de la Terminal y puede fallar con `Operation not permitted`. Opciones: dar "Acceso total al disco" al intérprete real (`/opt/homebrew/Cellar/python@3.12/…/python3.12`) o mover el repositorio fuera de Desktop/Documents.
- Límites: corre solo con la sesión iniciada y el Mac despierto; al dormir, el latido se detiene y el reporte bloquea la generación (§4.3).
- Memoria: YOLO y el agente comparten la memoria unificada; el agente respeta `GlobalGate.resources()` antes de tomar trabajo.

## 5. Plan de implementación

1. Mover `explain_worker.execute` a `malaria_dl` como función compartida; el worker de Docker la usa sin cambiar comportamiento (tests actuales en verde).
2. Migración `explain_requests` + `executor_heartbeats` (revisión con el guardián de esquema PostgreSQL).
3. Agente del host: arranque, canario, latido, toma con `SKIP LOCKED`, caché de modelo, recuperación; tests con repositorio falso.
4. Backend: política `EXPLAIN_EXECUTOR`, encolado, estado con cola, endpoint del ejecutor.
5. Interfaz: indicador de ejecutor y estados "En cola / Generando en GPU".
6. Verificación en el Mac: tiempo SHAP GPU vs CPU emulada, procedencia registrada, doble clic sin duplicados, reinicio del agente con trabajo en curso.

## 6. Decisiones pendientes

1. ~~Sin agente activo: ¿caer a CPU de Docker, preguntar o bloquear?~~ Decidido: bloquear y avisar (§4.3, §4.4).
2. Dispositivo en la identidad (cambia `identity_hash`) o solo en el intento.
3. ~~Arranque del agente~~ Decidido: `launchd` al iniciar sesión, junto al runtime YOLO (§4.6). El repositorio se mantiene en Desktop; el usuario concede "Acceso total al disco" al intérprete real de `.venv-metal` (2026-10-22). `host_services.sh status` debe detectar y explicar un fallo `Operation not permitted`.
4. ¿Extender después el mismo mecanismo a EVALUATE desde la interfaz?
5. Opción C (`linux/arm64`) como mejora inmediata, independiente de este diseño.
