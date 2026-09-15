# E9.3 — Ejecutor local Python (Mac) para TRAIN, backend/PostgreSQL en Docker

**Fecha:** 15/09/2026. **Campaña real pausada al inicio y al cierre**, sin reservas ni
entrenamientos reales nuevos. No se declara resuelto el OOM ni aprobada E9.3 por este
fix: esto habilita un *camino de ejecución alternativo*, no un diagnóstico del OOM del
run `79f39931-ac71-4bc1-a317-149a975d1f74`.

## 1. Diagnóstico y diseño aplicado

Al iniciar esta sesión ya existía, sin comitear, una implementación sustancial de este
mismo fix (probablemente de una sesión previa el mismo día): el módulo
`malaria_dl_local_project/src/malaria_dl/local_execution/`, la ruta HTTP
`backend_api/app/routes/local_execution.py` y la migración
`alembic/versions/20260915_01_local_execution.py`. La inspección (contratos existentes,
exclusividad global, revisión técnica) mostró un diseño correcto y consistente con las
convenciones del proyecto, pero **sin ninguna prueba automatizada** que lo ejerciera.
El trabajo de esta sesión fue: verificar ese diseño con pruebas reales contra
PostgreSQL, corregir los defectos reales que esas pruebas destaparon, preparar y
verificar el entorno Python local, y producir la documentación/auditoría faltante.

### Mecanismo de exclusividad (verificado)

`LocalBackend.claim()` toma el advisory lock `120994,1` transaccionalmente, escribe
`process_evidence={'release_confirmed': False, ...}` mientras el trabajo local está
vivo — esto bloquea a un `GlobalGate` Docker que intente entrar, porque
`verify_retained_processes` lanza `PROCESS_TREE_RELEASE_UNPROVEN` si
`release_confirmed is False` — y al liberar escribe `process_evidence='{}'`, que
`verify_retained_processes` trata como vacío y deja pasar sin error. En la dirección
opuesta, mientras un `GlobalGate` Docker está activo, sostiene el advisory lock de
sesión, así que el `pg_try_advisory_xact_lock` del `claim()` local falla de inmediato
(`GLOBAL_EXPERIMENT_BUSY`). Ambas direcciones quedaron cubiertas con pruebas reales
(`test_local_job_blocks_docker_gate_while_held`, `test_docker_gate_blocks_local_claim`).

## 2. Tabla de componentes (sección 3 del pedido)

| Componente existente | Reutilización prevista | Adaptación necesaria |
|---|---|---|
| `run_train_all_models.py` | Ninguna directa — sigue siendo el punto de entrada exclusivo del coordinador Docker | Ninguna; **no se ejecuta** como sustituto del worker local |
| `execution/campaign.py::run_child` | Referencia de contrato (handshake, subreaper, `process_evidence`) | El agente local no reutiliza este código — implementa su propio análogo (`agent.py`/`processes.py`) porque `/proc` y el subreaper Linux no existen en macOS |
| `execution/global_gate.py` (`GlobalGate`, `verify_retained_processes`, `process_table`, `managed_execution`) | Reutilizado tal cual desde `LocalBackend` para la exclusividad global | Ninguna en el código; **limitación estructural**: `process_table()`/`managed_execution` sólo ven procesos Linux visibles vía `/proc` del propio contenedor backend — no tienen visibilidad directa de nada en el Mac. La exclusividad real recae en el gate de PostgreSQL (advisory lock + `experiment_execution_gate`), no en el escaneo de procesos |
| `execution/controlled.py` (`ControlledRepository`, `validate_revision`) | Reutilizado sin cambios — `reserve`/`claim`/`finish`/`pause`/`put`/`records`/`session` son los mismos para Docker y local | Se extendió `validate_revision` (diff preexistente) para aceptar un entorno `local_python` explícito vía `local_execution/revision.py::valid_environment` sin exigir igualdad byte a byte con el entorno Docker |
| `execution/repository.py::ExecutionRepository` | Reutilizado para el modo `sequential` (`claim` auto-asigna el siguiente miembro elegible) | Ninguna en producción; se corrigió una llamada incorrecta en `backend.py` (`parent_pid=0` → `os.getpid()`, ver §7) |
| `execution/artifacts.py` (`verify_session`, `file_identity`, `keras_loader`) | Reutilizado sin cambios — la verificación de checkpoint/registro es idéntica para ambos modos | Ninguna |
| `execution/train.py::train(repository, session, descriptor)` | Reutilizado **sin modificar** — es la función de entrenamiento individual | Se le pasa un `Reports` (adaptador nuevo) en vez de `ExecutionRepository`; `train()` no distingue el origen |
| Carga del dataset (dentro de `train()`) | Reutilizada sin cambios | El agente valida el manifiesto (hashes) antes de invocar `train()`, vía `storage.verify_samples` |
| Persistencia de progreso/resultados (`put`/`records`/`finish`) | Interfaz reutilizada; implementación nueva (`local_execution/transport.py::Reports`) que reporta por HTTP en vez de escribir directo a PostgreSQL | Nuevo adaptador, mismo contrato exacto (`put(run,owner,kind,phase,key,payload)`, `records(run)`, `finish(run,owner,state,...)`) |
| Generación de checkpoints | Reutilizada (misma lógica de `train.py`/adaptadores) | El agente calcula el hash **después** de cerrar el archivo (`storage.identity`) y lo reporta; el backend re-verifica hash/ruta antes de aceptar |
| Dependencia de PostgreSQL / rutas internas Docker | Ninguna en el agente | El agente **nunca** importa `psycopg`/`SQLAlchemy`; toda persistencia pasa por la API HTTP del backend |

## 3. Contrato agente–backend

Ruta única `POST /execution/local/{operation}` (`backend_api/app/routes/local_execution.py`),
exige `Permission.SYSTEM_ADMIN` y `CAPSTONE_LOCAL_EXECUTION_ENABLED=1` explícito.
Operaciones: `dry-run`, `claim`, `heartbeat`, `record`, `records`, `calculation-ended`,
`exit`, `status`. `claim` es idempotente por `request_id` (hash del payload completo);
`heartbeat`/`record` toleran reintentos/duplicados sin efecto adicional. El propietario
de un trabajo se fija por la tripleta `(job_id, agent_id, owner)` — cualquier mezcla
incorrecta se rechaza con `LOCAL_OWNER_FENCED`. El vencimiento de heartbeat (60 s sin
señal) reporta `communication='uncertain'` pero **nunca** libera la reserva por sí
mismo — sólo una salida con `absence_proven=true` y sin PIDs restantes libera la
exclusividad.

## 4. Entorno local y dependencias

Verificado **realmente en este Mac** (no simulado): Python 3.12.13, `macOS-26.5.2-arm64-arm-64bit`,
TensorFlow 2.17.1, NumPy 1.26.4, sin dispositivos GPU/Metal (`tf.config.list_physical_devices()`
sólo reporta CPU). Venv dedicado en `malaria_dl_local_project/.venv-local-train`
(gitignored), pines exactos en `requirements-local-train.txt`. No se tocó el Python
global. Comandos y salida real en `comandos.md`.

## 5. Correspondencia de almacenamiento

`LocalBackend`/`storage.py` usan identificadores de raíz (`dataset_root_id`,
`artifact_root_id`) mapeados a rutas absolutas locales vía `CAPSTONE_LOCAL_STORAGE_ROOTS`
(JSON `{root_id: ruta}`) — nunca rutas absolutas del Mac guardadas como referencia
universal en los contratos, que sólo llevan `{root_id, relative_path}`. `storage.resolve`
rechaza rutas absolutas, `..`, símlinks y fuga de la raíz; `storage.identity` calcula el
hash **después** de cerrar el archivo y rechaza `.partial`/no-archivo;
`storage.verify_samples` rechaza la partición `test` explícitamente. Verificado con
pruebas reales de fuga de ruta, símlink, hash incorrecto y partición prohibida.

## 6. Pruebas y resultados

`malaria_dl_local_project/tests/test_local_execution_postgres.py` (nuevo, 21 casos,
opt-in `RUN_LOCAL_EXECUTION_POSTGRES_TESTS=1`, PostgreSQL real en esquema desechable
`capstone_test_e4_<uuid>`, sin mockear los repositorios cuyo comportamiento
transaccional se valida): reserva local vs. Docker concurrente (ambas direcciones), dos
agentes locales compitiendo, idempotencia y propiedad de la reserva, heartbeat vencido
sin liberar, reconexión y reportes duplicados, campaña pausada (controlado vs.
secuencial), ejecución única sin encadenamiento, secuencia de dos experimentos en modo
secuencial, fallo de subproceso (marca `failed` y pausa la campaña), fallo de
comunicación/persistencia (trigger SQL de rechazo, sin registro falso), hash
incorrecto y rutas inválidas, liberación de exclusividad únicamente en `exit`, y
despacho/autenticación de la ruta HTTP. **20/21 verificados en Linux (contenedor
`backend`), 3 corridas consecutivas sin fallos intermitentes.** El caso restante —
recorrido mínimo real API → agente → subproceso TRAIN → checkpoint → API → PostgreSQL
— se verificó **realmente en macOS nativo** (ver `comandos.md`): TensorFlow real,
checkpoint real, hash y carga reales, `completed`→`verified` confirmado desde una
conexión PostgreSQL nueva. Ninguna prueba tocó la campaña o el dataset reales.

Dos defectos reales de producción se destaparon y corrigieron (detalle en
`manifiesto.json`): `canonical(session)` fallaba siempre por UUID/datetime crudos
(toda reserva local era imposible antes de esta corrección), y el modo `sequential`
pasaba `parent_pid=0` violando el CHECK de la tabla (toda reserva secuencial era
imposible). Ambos se corrigieron en `backend.py`, no en las pruebas.

## 7. Revisión técnica — preparada, no registrada

Se construyó y validó (contra `validate_revision`/`valid_environment`, en esquema
desechable) un payload de ejemplo para `campaign_technical_revisions` con
`execution_mode='local_python'`:

```json
{
  "execution_mode": "local_python", "platform": "Darwin", "machine": "arm64",
  "device": "CPU", "precision": "float32",
  "packages": {"tensorflow": "2.17.1", "numpy": "1.26.4"},
  "determinism_environment": {"PYTHONHASHSEED": "42"},
  "python": "3.12.13", "tensorflow": "2.17.1",
  "source_sha256": "<sha256 real del árbol de fuentes>"
}
```

**No se insertó contra la base persistente real** — sólo se validó en esquemas de
prueba. Diferencias de entorno documentadas: mismo Python 3.12 y TensorFlow 2.17.1 en
ambos lados; Linux (contenedor) vs. Darwin/arm64 (Mac); CPU en ambos lados (sin GPU ni
Metal en ninguno). **No se afirma equivalencia numérica exacta entre plataformas sin
evidencia adicional** — glibc vs. libc de macOS, BLAS/LAPACK del sistema y el
scheduler de hilos de TensorFlow pueden diferir en el último bit incluso con semillas
fijas. Qué resultados siguen siendo comparables conforme a E7 y qué limitaciones deben
registrarse es una decisión científica pendiente, no resuelta por este cambio de
ejecutor. El cambio de ejecutor **no modifica** la meta de sensibilidad ni autoriza
ajustar el threshold durante TRAIN.

## 8. Auditoría y manifiesto

Ver `manifiesto.json` (hashes de archivos, estado real antes/después, defectos
corregidos) y `comandos.md` (transcripción real de cada comando ejecutado).

## 9. Requisitos pendientes de instalación

- La migración `20260915_01_local_execution` sigue **sin aplicar** sobre la base
  persistente real (`alembic current` = `20260914_02`, verificado antes y después).
  Aplicarla requiere una decisión explícita y separada.
- `CAPSTONE_LOCAL_EXECUTION_ENABLED`/`CAPSTONE_LOCAL_STORAGE_ROOTS` no están definidas
  en ningún compose/entorno real — la ruta HTTP permanece deshabilitada por defecto.
- Ningún inicio automático del agente está configurado en ninguna parte.

## 10. Procedimiento para el futuro intento controlado (no ejecutado aquí)

1. Decisión explícita y documentada de aplicar la migración `20260915_01_local_execution`
   sobre la base persistente (fuera de este fix).
2. Registrar contra la campaña real una revisión técnica `local_python` vía
   `ControlledRepository.register_revision`, con hashes reales de los archivos tocados
   en esta sesión (ver `manifiesto.json`) y evidencia (esta auditoría + resultados de
   pruebas).
3. Habilitar `CAPSTONE_LOCAL_EXECUTION_ENABLED=1` y `CAPSTONE_LOCAL_STORAGE_ROOTS` sólo
   en el momento de ejecutar, no de forma persistente.
4. Preparar `agent_config.json` con el `request_id` nuevo, `member_id`/`previous_attempt_id`
   del miembro fallido en cuestión, y los `root_id` mapeados a las rutas reales del Mac.
5. `agent dry-run` primero (cero escrituras) para confirmar conectividad y elegibilidad.
6. `agent start` para el único intento controlado; seguimiento con `agent status`.
7. Verificación oficial (`verify_session`/`verify_retained_processes`) antes de
   considerar el intento cerrado — no declarar `completed` sólo porque el agente
   reportó éxito.

## Distinción de estado

| | Implementado | Verificado en aislamiento | Verificado en macOS | Instalado | Pendiente |
|---|---|---|---|---|---|
| Código `local_execution/` + ruta HTTP + migración | ✅ | ✅ (20 pruebas, Linux) | ✅ (1 recorrido real) | Código sí; migración NO aplicada a la base real | — |
| Entorno Python local (venv, deps, smoke test) | ✅ | — | ✅ | ✅ (venv dedicado, no global) | — |
| Revisión técnica `local_python` | ✅ (payload preparado y validado) | ✅ (esquema de prueba) | — | ❌ NO registrada contra la campaña real | Registro real (paso 2 arriba) |
| Runbook operativo | ✅ (README §10) | — | ✅ (comandos ejecutados tal cual documentados) | — | — |
| TRAIN completo real contra la campaña/dataset reales | — | — | — | — | **Pendiente**; requiere autorización separada |

**Cierre:** campaña real `3acf89b7-dc42-4b7a-8e2a-ca6ea024c344` permanece `paused`, run
`79f39931-...` permanece `failed`, `blocked_reason=NEW_CONTAINER_OOM_PAUSE` intacto,
`alembic current`=`20260914_02` sin cambios, cero reservas nuevas contra la campaña
real. No se declara resuelto el OOM ni aprobada E9.3 por completar este fix.
