# CAPSTONE-DB-02C — Ejecución de campañas independiente de Alembic

Estado documental: `CURRENT_DOC` — **implementación y validación técnica completadas en rama; pendiente de integración y cierre operativo autorizado**.

Fecha: 2026-10-12. Base: `a4c11f4`, comprobada mediante `git fetch origin main`.
Rama: `fix/capstone-db-02c`. Worktree: `/private/tmp/capstone-db-02c`.
El checkout operativo continúa en `main`. No se ejecutaron TRAIN, EVALUATE, EXPLAIN,
migraciones ni DDL/DML contra PostgreSQL operativo. No se modificó `campaign_guard()`
ni los SQL, fixtures, pruebas o documentación de DB-02B.

## Causa exacta y diagnóstico

La condición que produce el incidente está en
`malaria_dl_local_project/src/malaria_dl/execution/schema.py::require_e10_schema()`:

1. Busca `alembic_version` mediante `pg_class`, `pg_namespace` y `to_regclass`.
2. Ejecuta `SELECT version_num FROM alembic_version`.
3. Exige exactamente una revisión perteneciente a `('20260922_01', 'pg_v2_baseline')`.
   Una revisión distinta, varias revisiones o la ausencia de esa tabla generan
   `E10SchemaNotReady(['unsupported_alembic_revision'])`.
4. Incluso con una revisión aceptada, compara columnas, expresión de CHECK,
   índices y MD5 del cuerpo de `train_event_guard`. Para `pg_v2_baseline` llama
   además a `persistence/schema_contract.py::require_v2_capabilities()`, que
   compara funciones, triggers, constraints e índices con un JSON histórico.

La excepción es un `CampaignError`; `run_train_all_models.main()` la imprime como
`STOP E10_SCHEMA_NOT_READY: unsupported_alembic_revision`. No se reprodujo el
comando operativo: se identificó la causa por lectura del código y el incidente
aportado. No se necesitó consultar ni cambiar la revisión operativa.

Ruta normal antes del cambio:

```text
run_train_all_models.py → bootstrap local (fuera de Docker)
 → execution.campaign.main → repo.get(campaign_id)
 → repo.preflight_e10_schema → require_e10_schema → STOP
 → [si pasaba] GlobalGate → execute_campaign(resume=True)
 → preflight_e10_schema → get/preflight científico → reconcile/resume
 → claim → require_e10_schema → _create_run → require_e10_schema
 → sesión TRAIN → run_child → subprocess.Popen(sys.executable, ...worker...)
```

El mismo control bloqueaba CPU, Metal, Docker y Python local antes de elegir o
iniciar la carga científica. No dependía del dispositivo. La creación de campañas
no llamaba directamente al guard Alembic; DB-02B resolvió otro problema distinto.

## Clasificación y alcance

| Comprobación encontrada | Decisión |
|---|---|
| Lista de revisiones Alembic y tabla `alembic_version` | Retiradas de todos los llamadores operativos |
| Contrato histórico E10/v2 de columnas, funciones, triggers e índices | Desconectado del runtime, sin sustituto |
| `to_regclass` en reserva, gate global, revisiones técnicas y finalización | Eliminado; SQL directo sobre las tablas vigentes |
| `SELECT ... LIMIT 0` para compatibilidad de sesiones/eventos | Eliminado; las consultas funcionales usan columnas vigentes |
| Versión PostgreSQL como condición de compatibilidad | No se encontró otra en los flujos operativos inspeccionados |
| `persistence.database.test_connection(): SELECT version()` | Conservado: diagnóstico informativo, no autoriza ni bloquea por versión |
| Conectividad, identidad de base y permisos de persistencia | Conservados |
| Existencia/estado de campaña, miembros elegibles, presupuesto y orden | Conservados |
| Evidencia, snapshot, hashes y archivos TRAIN/VAL | Conservados |
| Configuración, adaptador, semillas, hiperparámetros y prohibición de TEST | Conservados |
| Ownership, locks, idempotencia, stream existente y recursos | Conservados |
| PK/FK/UNIQUE/CHECK/NOT NULL/triggers PostgreSQL | Intactos |

Consumidores corregidos: ejecución normal, `--plan`, `--dry-run`, reanudación,
reserva controlada, reserva del backend local, consulta del stream local,
creación de runs standalone, aceptación/proyección de eventos, lectura científica
y `/ready`. EVALUATE/EXPLAIN no tenían otra llamada directa al guard encontrado;
comparten el gate global y el lector de resultados corregidos. No se ejecutaron.

Las **revisiones técnicas de campaña** no son revisiones de esquema: conservan
su validación de identidad científica, entorno, hashes y asociación a la campaña.
Sólo se retiraron sus sondeos previos de existencia de tablas.

## Cambios y SQL posterior al bloqueo

- Se eliminó `ExecutionRepository.preflight_e10_schema()` y sus llamadas; no se
  dejó una función vacía, un flag de omisión, una captura para ignorar la excepción
  ni una validación equivalente.
- `_create_run()` siempre proyecta a `run_configurations`; el writer siempre usa
  las proyecciones científicas vigentes. Se retiró el despacho a persistencia
  histórica por revisión Alembic y la escritura alternativa en `runs.parameters`.
- La referencia `runs.campaign_id` se persiste directamente en campañas. La
  selección sigue ordenando miembros pendientes primero y luego por posición,
  con el mismo presupuesto, configuración y semilla.
- Los lectores de los dos tipos de registros usan `record.event_id` y
  `record.event_sequence` directamente. Se conserva la lectura de evidencia
  histórica almacenada en la estructura actual y sus bytes/hashes; no la
  compatibilidad con tablas antiguas sin esas columnas.
- `preflight_result_events()` mantiene el rechazo
  `E10_ACTIVE_STREAM_RECOVERY_UNSUPPORTED`; ya no inspecciona el catálogo.
- `/ready` conserva conexión, identidad de base y acceso a storage. Ya no publica
  un componente `migrations`. Plan/gate/controlado tampoco presentan comprobaciones
  de esquema ni el indicador `installed`.
- `CampaignRepository.transaction()` conserva los códigos científicos `P0001`
  y su logging seguro. Propaga `OperationalError` y los errores SQL de programación
  que no son `P0001`, en vez de ocultarlos bajo el error genérico. El CLI puede así
  informar `DATABASE_UNREACHABLE` cuando falla la conexión; tabla/columna inexistente
  conserva su excepción y SQLSTATE real. La suite DB-02B confirma sus rechazos.

Tras la barrera eliminada se ejecutan las lecturas de campaña, configuraciones,
miembros e intentos; la verificación de evidencia/dataset; el gate con advisory
lock y control de recursos; la selección con `FOR UPDATE`; inserciones en
`campaign_attempts`, `runs`, `run_configurations`, `train_execution_sessions`,
y actualizaciones de vínculo/estado dentro de la misma reserva transaccional.
Después se recupera la sesión y se prepara el proceso hijo con el intérprete activo.
Ninguna de esas operaciones de escritura se ejecutó sobre la campaña operativa.

### SQL obsoleto descubierto en el lector compartido

La prueba real de `read_scientific_results()` descubrió `UndefinedColumn`:
`xai_quantitative_evaluations.evidence_id` ya no existe. Se corrigió usando la
relación vigente, sin adaptar el esquema:

```sql
SELECT * FROM xai_quantitative_evaluations
WHERE id IN (
  SELECT evaluation_id FROM xai_evaluation_members
  WHERE xai_evidence_id IN (SELECT id FROM xai_evidence WHERE run_id=:run)
)
ORDER BY evaluated_at,id;
```

El `IN` no duplica evaluaciones con varios miembros. La prueba demuestra que el
SQL se ejecuta sobre el DDL vigente y devuelve listas vacías para un run sin XAI;
no demuestra resultados de EXPLAIN ni genera artefactos XAI.

## Herramientas administrativas e históricas

Se conservan `execution/schema.py`, `persistence/schema_contract.py` y
`v2_runtime_contract.json` para los diagnósticos explícitos que aún los importan.
Sus módulos indican ahora **uso administrativo/histórico, nunca operativo**.
No son dependencias de ningún flujo en `src` o `backend_api/app`; una prueba
estática impide reintroducir sus símbolos o sondeos estructurales en esos llamadores.

Quedan fuera del alcance las herramientas `scripts/db/probe_v2_*`, certificaciones
`swv21*`/`swv22*`, `scripts/reset/*`, `scripts/maintenance/database.py` y los
rehearsals de calibración que invocan el diagnóstico por decisión administrativa.
No se ejecutaron. Algunos rehearsals históricos, como
`scripts/reset/reset3/functional_probe.py`, llaman al método operativo retirado;
no deben utilizarse como prueba del runtime actual. Las suites PostgreSQL antiguas
basadas en migraciones legacy tampoco certifican el DDL vigente: su adaptación
sería una intervención independiente, no una razón para reintroducir compatibilidad.

Se retiró `test_e10_preclaim_schema_postgres.py`, cuya expectativa era bloquear por
revisión histórica y permitir ejecución después de migrar. Su obligación operativa
se reemplaza por las pruebas DB-02C contra PostgreSQL vigente sin tabla Alembic.
Las pruebas directas de los diagnósticos administrativos permanecen.

## Pruebas y evidencia demostrada

Comandos ejecutados desde el worktree, mediante Makefile:

```sh
make test-db02c
make test-db02b
```

- **DB-02C: 348 PASS**, 2 advertencias de deprecación de protobuf para Python 3.14.
- **DB-02B: 49 PASS**, suite original sin modificaciones.
- `git diff --check`: PASS.

`docker-compose.db02c-test.yml` levanta PostgreSQL 17.9 desechable en tmpfs,
red interna y sin puertos publicados. El contenedor de pruebas monta el worktree
sólo para lectura y las imágenes sintéticas en otro tmpfs. Usa la imagen disponible
`capstone-malaria-backend`, Python 3.12.14, Linux amd64 bajo Docker del Mac arm64.
El target destruye sus contenedores y red al terminar, incluso si hay un fallo.
No monta credenciales, datasets ni storage operativos.

La fixture instala el DDL ya registrado por DB-02B y su corrección cerrada en esa
base aislada; no ejecuta Alembic. Retira **sólo allí** la tabla Alembic. Construye
pacientes, splits, archivos PNG, hashes, materialización, evidencia real y campaña
sintéticos con las restricciones activas. El usuario SQL de pruebas es `postgres`;
esto no certifica los permisos efectivos del rol operativo.

| Caso solicitado | Evidencia |
|---|---|
| 1. Independencia de Alembic | Reserva y writer reales sin tabla Alembic; observador rechaza consultas Alembic y sondeos estructurales; comprobación estática de callers |
| 2. Campaña válida | Campaña persistida llega a `launch`, con primer miembro, configuración, dataset, entorno y run verificados |
| 3. Campaña inexistente | `CAMPAIGN_NOT_FOUND`, también desde preparación local |
| 4. Base inaccesible | Conexión real a puerto cerrado genera `OperationalError`; `/ready` devuelve 503 |
| 5. Dataset inválido | Archivo VAL alterado o eliminado causa rechazo antes de crear intentos |
| 6. SQL incompatible | PostgreSQL devuelve `42P01` y `42703` sin convertirlos en éxito; stream sin tabla también falla |
| 7. Regresión | Selección/semilla/configuración exactas, identidad run/intento/campaña, proyección, heartbeat idempotente, fencing, checkpoints/completion y contratos científicos |
| 8. Ejecución local | Bootstrap de los entornos locales, URL loopback a PostgreSQL Docker y argv con `sys.executable`, sin crear el proceso |

La integración ejecuta realmente preflight, gate, reserva y proyección, con y sin
la opción `resume`. **Sólo sustituye `launch`** por un doble que lanza una excepción
exclusiva del test antes de crear el hijo. Se comprueban `child_pid IS NULL`, cero
artifacts/evaluations/registros científicos antes de escribir un heartbeat de prueba.
El heartbeat posterior prueba el writer compartido, idempotencia y rechazo de owner
ajeno; no representa cálculo de TRAIN. El intento sintético se cierra como interrumpido.
El gate de cada fixture comienza limpio para no reutilizar el PID del mismo pytest
como si fuera otro coordinador. No se omiten controles de recursos ni triggers.

El `dry-run` real identifica dos miembros elegibles y el primero con semilla 11;
no emite INSERT/UPDATE/DELETE/DDL y deja la campaña sintética idéntica.

Durante el desarrollo las pruebas detectaron y permitieron corregir: preparación
incompleta del fixture, una expectativa antigua de descubrimiento de modelos sin
catálogo, el SQL XAI obsoleto y la necesidad de distinguir `P0001` de otros
`ProgrammingError`. Los resultados anteriores son los de las ejecuciones finales.

### Campaña operativa: observación de solo lectura

Se usó `psql` dentro de `capstone_db`, con `BEGIN READ ONLY` y `COMMIT`.
La observación inicial y la comprobación final coincidieron; al finalizar sólo
seguían los tres contenedores operativos, sin contenedores de pruebas:

| Dato | Valor observado |
|---|---|
| Campaña | `4b5a9626-ddb7-4f48-a93e-b29b8085b349` |
| Estado | `frozen` |
| Dataset | `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2` |
| Configuraciones / miembros pendientes | 1 / 1 |
| Intentos / runs de campaña | 0 / 0 |

No se ejecutó el comando operativo, ni siquiera su `dry-run`, contra esa campaña.

## Límites y riesgos residuales

- La preparación de TRAIN queda demostrada en la base aislada. Un entrenamiento
  completo, GPU Metal real, EVALUATE/EXPLAIN y la publicación de checkpoints quedan
  pendientes de autorización; no se presentan como validados.
- Las restricciones y SQL posteriores pueden revelar problemas reales de datos
  o infraestructura. Ahora deben diagnosticarse como tales, sin comprobar stamps
  ni agregar fallbacks. No se halló otro bloqueo de esquema en los callers revisados.
- `/ready` y reportes de planificación pierden campos de compatibilidad de esquema.
  No se encontraron consumidores frontend de esos campos; clientes externos deben
  revisar esa diferencia de respuesta.
- La validación usa el DDL capturado por DB-02B, no un contrato comparado en runtime.
  No se afirma equivalencia exhaustiva con cambios futuros de la base operativa.
- Los diagnósticos/rehearsals históricos indicados arriba siguen pendientes de
  una revisión independiente. No se afirma PASS para toda la suite histórica del repo.

## Archivos para revisión

Rutas relativas a `malaria_dl_local_project/src/malaria_dl/`:

- `campaigns/plan.py`, `campaigns/repository.py`.
- `execution/campaign.py`, `execution/controlled.py`, `execution/global_gate.py`,
  `execution/repository.py`, `execution/schema.py`.
- `local_execution/backend.py`, `local_execution/event_backend.py`.
- `persistence/execution_record_readers.py`, `persistence/result_repository.py`,
  `persistence/schema_contract.py`.

Otros archivos:

- `backend_api/app/routes/health.py`, `backend_api/app/routes/runs.py`,
  `backend_api/app/services/scientific_results.py`.
- `Makefile`, `docker-compose.db02c-test.yml`.
- `tests/db02c/conftest.py`, `tests/db02c/test_execution.py`,
  `tests/db02c/test_shared_flows.py`.
- `malaria_dl_local_project/tests/test_campaign_cli_plan_swv22.py`,
  `test_campaigns_e4.py`, `test_e02_projection_routing.py`, `test_local_train_launcher.py`
  (los cuatro bajo el mismo directorio de tests).
- Eliminado: `malaria_dl_local_project/tests/test_e10_preclaim_schema_postgres.py`.
- Este informe y `docs/README.md`.

## Propuesta de integración y validación operativa posterior

1. Revisar el commit de `fix/capstone-db-02c` con `git diff main...fix/capstone-db-02c`
   y `git log main..fix/capstone-db-02c`. La rama no se publicó ni integró.
2. En la ventana autorizada, confirmar ausencia de procesos científicos y controlar
   la recarga automática del backend antes de actualizar el checkout operativo.
3. Actualizar `main`; si mantiene la base verificada, integrar con fast-forward.
   Si avanzó, reconciliar en una rama aislada y repetir ambos targets antes de integrar.
4. Aplicar el código mediante el flujo Docker/Compose del proyecto para el backend;
   mantener Python local como execution plane de Mac. **No hay migración ni DDL que aplicar.**
5. Comprobar `/ready`, lectura de campaña y que siga `frozen`, 1 pendiente, 0 intentos
   y 0 runs antes de autorizar la primera ejecución.
6. Sólo con autorización posterior, ejecutar el comando solicitado en el entorno
   local permitido. Criterios: no consulta/bloqueo Alembic; preflight científico real;
   miembro/configuración/dataset esperados; entorno observado; reserva única y
   lanzamiento normal; resultados/checkpoint/estado según el protocolo congelado.
7. Para revertir código, revertir el commit en una ventana sin procesos activos.
   No cambiar revisiones ni datos PostgreSQL. Revertir reintroduciría el bloqueo
   anterior y no deshace eventuales ejecuciones futuras.

El cierre operativo permanece pendiente. La evidencia actual habilita revisión e
integración del cambio, no acredita un TRAIN completado de la campaña real.
