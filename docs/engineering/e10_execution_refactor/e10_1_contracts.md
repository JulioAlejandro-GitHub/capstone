# E10.1 — Contratos comunes de ejecución

## 1. Objetivo

Definir la frontera mínima entre un núcleo científico futuro y sus reporters:
`ExecutionMode`, `ExecutionContext`, `RunEventType`, `RunEvent` y `RunReporter`.
E10.1 no conecta estos contratos al flujo productivo.

```text
Scientific Core
       |
       | futuro
       v
  RunReporter
       |
       | RunEvent
       v
  [infraestructura futura]
```

## 2. Baseline e inspección

Referencia: [E10.0](baseline.md), leído completo antes de editar. Código contrastado
sobre HEAD `0e8588f5dd8ac9ba5c961687f8586e43ee63e90d`.

Se inspeccionaron `execution/`, `local_execution/`, las dataclasses/enums de
`governance/entities.py`, los contratos/canonicalización de `campaigns/contracts.py`,
`common/serialization.py`, `common/types.py`, Dockerfile backend, CI, Makefile y tests.
Las rutas Python de este documento son relativas a
`malaria_dl_local_project/src/malaria_dl/` salvo indicación contraria.

Docker y Local llaman al mismo `execution/train.py::train(repository, session,
descriptor)`. Local reporta por HTTP; agente y worker no ejecutan SQL directo.
`runs` sigue siendo la identidad canónica; `train_execution_records` conserva la
evidencia incremental append-only. TRAIN no consolida resultados en `runs.parameters`.
La verificación actual puede aprobar evidencia sin matriz de confusión cuando no
hay calibración. Estos hechos no se corrigen ni alteran en E10.1.

Docker backend y CI usan Python 3.12; el venv existente usa 3.12.13. No se encontró
un mínimo propio declarado para el paquete ML; el pyproject del paquete vecino
no establece su mínimo. Se usa `str, Enum`, coherente con el repositorio, y
sintaxis/dataclasses disponibles desde 3.10, sin exigir `StrEnum` de 3.11.
La validación efectiva de esta entrega se realiza en 3.12.13.

## 3. Archivos creados

- `malaria_dl_local_project/src/malaria_dl/execution/contracts/__init__.py`
- `malaria_dl_local_project/src/malaria_dl/execution/contracts/context.py`
- `malaria_dl_local_project/src/malaria_dl/execution/contracts/events.py`
- `malaria_dl_local_project/src/malaria_dl/execution/contracts/_json.py`
- `malaria_dl_local_project/src/malaria_dl/execution/contracts/reporter.py`
- `malaria_dl_local_project/tests/test_execution_contracts.py`
- `malaria_dl_local_project/tests/test_execution_contract_dependencies.py`
- `docs/engineering/e10_execution_refactor/e10_1_contracts.md`

No se modifican archivos preexistentes.

## 4. Ubicación

`execution/contracts/` mantiene los contratos junto al dominio de ejecución sin
reorganizar módulos. Su API pública se exporta en su propio `__init__.py`.
Los inicializadores padres actuales no importan infraestructura. Los ejecutores
actuales no importan el nuevo paquete. Todos sus imports son de biblioteca estándar
o relativos a otros módulos del propio paquete.

## 5. ExecutionMode

`DOCKER = "docker"` y `LOCAL_PYTHON = "local_python"`. Identifica el runtime físico;
no equivale al modo de campaña `controlled`/`sequential` y no decide lógica científica.

## 6. ExecutionContext

Dataclass `frozen=True, slots=True, kw_only=True`, sin rutas ni objetos de runtime.
Los UUID se exigen como objetos UUID; convertir las cadenas de transporte será
responsabilidad del futuro ensamblador del contexto.

| Campo | Tipo | Fuente actual / decisión |
| --- | --- | --- |
| run_id | UUID | `session['run_id']`, requerido |
| owner | UUID | Identidad de ownership de la frontera de reporte, requerida |
| execution_mode | ExecutionMode | Runtime conocido por el entrypoint, requerido |
| dataset_version_id | UUID | `session['dataset']['dataset_version_id']`, requerido |
| model_id | str | `session['configuration']['model_id']`, requerido; clave del registry, no UUID de tabla models |
| adapter_version | str | `session['configuration']['adapter_version']`, requerido |
| attempt_id | UUID o None | Sesión de campaña; ausente en `ExecutionRepository.standalone()` |
| campaign_id | UUID o None | Docker recupera campaña; no llega al worker Local en su sesión pública |
| member_id | UUID o None | Docker recupera miembro; no llega al worker Local en su sesión pública |
| configuration_hash | str o None | Digest de configuración científica del miembro; no llega al worker Local |
| contract_hash | str o None | Digest del contrato de campaña; no llega al worker Local |

Docker usa el owner de la sesión. `local_execution/backend.py::claim` reemplaza
el owner de la sesión pública por el token UUID del job remoto; no es el owner
interno de la sesión de BD. El contexto representa ese owner de reporte sin
confundirlos ni incluir JWT. Su eventual uso requiere conservar el fencing actual.

Los campos opcionales se omiten con `None`, sin UUID ficticios ni hashes calculados
por aproximación. No se exige que estén todos presentes juntos: Local dispone de
attempt_id sin los demás metadatos. Los hashes presentes deben tener 64 caracteres
hexadecimales minúsculos. No se usa `models.configuration.config_digest` como sustituto.
`scientific_configuration()` excluye seed; no corresponde hashear directamente la
configuración resuelta del intento para fabricar `configuration_hash`.

No se incluye snapshot de entorno, conexión, repositorio, cliente HTTP, dataset
cargado, modelo, checkpoint ni rutas absolutas.

## 7. RunEventType

Vocabulario Python nuevo, sin modificar `train_execution_records.kind`.
Los siguientes son puntos de correspondencia para diseño posterior, no traducciones
implementadas:

| Enum / valor JSON | Evidencia actual |
| --- | --- |
| HEARTBEAT / heartbeat | Heartbeat de coordinación/agente; no lo emite hoy el núcleo científico |
| EPOCH_COMPLETED / epoch_completed | `put('epoch', ...)` en callback de TRAIN |
| PHASE_STARTED / phase_started | Reporte `runtime` antes de `fit`; no se duplica con otro enum RUNTIME |
| PHASE_COMPLETED / phase_completed | Reporte `phase` al terminar fase |
| ARTIFACT_PREPARED / artifact_prepared | Registro previo al guardado del checkpoint |
| ARTIFACT_CREATED / artifact_created | Reporte `artifact` después de guardar |
| PREDICTIONS_COMPLETED / predictions_completed | Reporte `predictions` |
| SELECTION_COMPLETED / selection_completed | Reporte `selection` |
| CALIBRATION_COMPLETED / calibration_completed | Reporte `calibration` |
| EVALUATION_COMPLETED / evaluation_completed | Cálculo de métricas de validación/calibración existente; no hay un kind autónomo equivalente en el ledger TRAIN |
| TRAINING_COMPLETED / training_completed | `finish(..., 'completed', completion)` tras cómputo |
| TRAINING_FAILED / training_failed | Fallos terminales gestionados por orquestación; no es un put del train actual |

Desviación del conjunto esperado: se añade únicamente ARTIFACT_PREPARED porque
el orden preparación → guardado → evidencia de artefacto ya existe y es verificado.
EVALUATION_COMPLETED reserva la representación de evaluación ya existente, sin
introducir ejecución TEST, nuevas métricas o afirmar que hoy se persiste ese evento.
Su payload y punto de emisión precisos quedan pendientes. TRAINING_COMPLETED no
implica verificación, liberación del gate ni ausencia confirmada del proceso Local.
No se crea un evento VERIFIED.

## 8. RunEvent

Dataclass inmutable con:

| Campo | Contrato |
| --- | --- |
| event_id | UUID requerido explícitamente; el productor deberá conservarlo en reintentos |
| run_id | UUID requerido, identidad de ejecución |
| attempt_id | UUID opcional; None para ejecución standalone |
| sequence | int >= 1, sin aceptar bool; orden lógico dentro de run_id |
| event_type | RunEventType requerido |
| schema_version | Literal `run_event_v1`, única versión aceptada |
| occurred_at | datetime requerido timezone-aware, normalizado a UTC |
| payload | Objeto JSON recursivamente tipado, validado, copiado y congelado |

Ordenar eventos de una misma ejecución se expresa con
`sorted(events, key=lambda event: event.sequence)`. No hay comparación total
artificial entre ejecuciones ni asignador global de secuencias. No se valida
unicidad, continuidad entre eventos ni concordancia con un contexto externo.
No se generan UUID o timestamps implícitos que cambien la identidad en reintentos.

## 9. RunReporter

ABC con un solo método abstracto `report(self, event: RunEvent) -> None`.
Se eligió ABC por la preferencia solicitada y porque no se encontró una convención
consistente que justificara Protocol. Obliga a implementar report antes de instanciar.
No contiene almacenamiento, transporte, estados de entrega ni operaciones sobre tablas.
`InMemoryRunReporter` vive exclusivamente en tests, preserva referencias y orden de
recepción; no deduplica ni inventa políticas de entrega.

## 10. Serialización

Único par público: `RunEvent.to_dict()` / `RunEvent.from_dict()`.

```python
wire = json.dumps(event.to_dict(), allow_nan=False)
restored = RunEvent.from_dict(json.loads(wire))
assert restored == event
```

UUID → cadena, enum → valor estable, datetime → ISO-8601 UTC con offset explícito.
El decoder exige exactamente los ocho campos, incluido attempt_id (null permitido),
y rechaza versiones desconocidas. No acepta timestamps naive. El instante se
preserva; el offset original se normaliza a UTC y no se guarda como metadato.

El payload admite null, bool, int, float finito, str, objetos con claves string y
arrays. Se copia profundamente: objetos → MappingProxyType; arrays → tuple.
Se aceptan tuplas y mappingproxy como entrada interna para reconstruir un evento
inmutable; la salida siempre usa dict/list. Cada `to_dict()` devuelve una copia
mutable independiente. No hay coerción de float integral a int.

Se rechazan ciclos, claves no string, NaN/Infinity, Path, bytes, sets, excepciones,
UUID/datetime dentro del payload y objetos arbitrarios (incluidos tensores/ndarrays).
Quien produce los datos debe normalizarlos explícitamente antes de crear el evento.
Se usa un alias JSON recursivo, sin diez clases de payload ni `dict[str, Any]` libre.
No se valida todavía la semántica particular de cada tipo de evento.

No se reutiliza `common.serialization.json_safe`: convierte paths/claves e intenta
`.item()`, y puede dejar objetos desconocidos sin rechazar. Tampoco se reutiliza la
canonicalización de campañas, que tiene otra responsabilidad y normaliza números.
No se añaden dependencias. No se ofrece serialización de ExecutionContext en esta etapa.

## 11. Invariantes y límites

- Inmutabilidad de campos y payload anidado; cambios al input o a una salida JSON
  no alteran el evento.
- Identidad UUID explícita, tipo de evento cerrado, versión única y tiempo aware.
- Sequence positiva ordena dentro de una ejecución; no acredita entrega o persistencia.
- No hay acceso a BD, filesystem, red, TensorFlow, entorno ni registry en los contratos.
- El contrato no conoce nombres de tablas o columnas de resultados.
- No se garantiza idempotencia persistente, exactly-once, fencing o verificación:
  esas responsabilidades siguen fuera de E10.1.

## 12. Pruebas

Entorno existente `.venv-local-train`, Python 3.12.13, pytest 8.4.2; sin instalar
ni actualizar paquetes. Comandos desde la raíz del repositorio:

```sh
PYTHONPATH=malaria_dl_local_project PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 malaria_dl_local_project/.venv-local-train/bin/python -B -m pytest -p no:cacheprovider malaria_dl_local_project/tests/test_execution_contracts.py malaria_dl_local_project/tests/test_execution_contract_dependencies.py -q

PYTHONPATH=malaria_dl_local_project PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLCONFIGDIR=/tmp/e10_1_mpl malaria_dl_local_project/.venv-local-train/bin/python -B -m pytest -p no:cacheprovider malaria_dl_local_project/tests/test_campaign_executor_e5.py malaria_dl_local_project/tests/test_campaign_exit_diagnostics.py malaria_dl_local_project/tests/test_label_mapping.py malaria_dl_local_project/tests/test_decision.py malaria_dl_local_project/tests/test_image_quality.py -k 'not test_train_uses_only_train_and_val_without_csv and not test_migration_has_no_accidental_binds' -q
```

Nuevas pruebas: **88 passed**, incluidas dos guardas. Cubren enums exactos, identidad,
campos opcionales, validación, inmutabilidad profunda, round-trip de los doce tipos
con/sin intento, tiempo UTC, payloads inválidos/cíclicos, ABC, orden y reintentos sin
cambio de identidad. La primera invocación desde raíz sin PYTHONPATH falló en colección;
se corrigió el comando conforme a la estructura existente, sin modificar imports del proyecto.

Regresión: **36 passed, 2 deselected**, con dos DeprecationWarning de protobuf
(`google._upb._message`) sobre compatibilidad futura con Python 3.14. Se excluyen explícitamente
el test que llama a train (aunque use dobles) y el de inspección de migración. Los tests
de coordinación usan repositorio y launcher falsos; no lanzan ni reanudan campañas.
La regresión habitual de Makefile/CI (label mapping, decision, image quality) usa
constantes/entradas sintéticas, sin evaluar el conjunto TEST clínico.

No se ejecuta discovery completo: el repositorio incluye tests de integración con
PostgreSQL/migraciones y tests con model.fit. No se ejecuta TRAIN ni acceso a datos
persistentes reales. La verificación sintética de artefactos escribe sólo en tmp_path.

## 13. Guardas de dependencia

AST: recorre todos los nodos de todos los módulos del paquete, incluso imports
locales y bajo TYPE_CHECKING. Sólo permite una lista explícita de módulos stdlib e
imports relativos directos entre contratos; prohíbe llamadas a __import__/eval/exec.
Esto impide imports de SQLAlchemy, psycopg, FastAPI, backend_api, requests/httpx,
repositorios concretos, TensorFlow y cualquier otra dependencia no autorizada.

Import guard: proceso nuevo `python -I -S -B`, sin site-packages, añade únicamente
la raíz ML. Un MetaPathFinder bloquea módulos ajenos a stdlib, contratos y sus
paquetes padres. Importa los cinco contratos, construye contexto/evento y hace
round-trip JSON. Evita falsos positivos por infraestructura ya cargada en pytest.
Las guardas controlan dependencias; no son un sandbox contra código malicioso.

## 14. Cambios deliberadamente no realizados

No cambia train ni su firma; no se conecta RunReporter. No hay DockerRunReporter,
HttpRunReporter, ResultService ni adapters temporales productivos. Docker, Local,
endpoints, transporte, agente y coordinación permanecen intactos. No hay SQL,
migraciones, tablas, triggers, índices, writes a runs.parameters ni cambios de
completed/verified o gobernanza TRAIN/VAL/TEST. No se cambia persistencia de entorno,
requirements, Dockerfile, venv, lockfiles ni Compose. No se crean commits.

## 15. Gaps para E10.2

1. Definir el ensamblaje del contexto por entrypoint y la propagación fiable de
   campaign_id/member_id/hashes al worker Local; conservar None hasta disponer de ellos.
2. Resolver explícitamente owner remoto frente a owner interno sin debilitar fencing.
3. Definir productor/alcance de sequence entre núcleo, heartbeat y orquestador,
   además de event_id estable en reintentos y reinicios; el ledger actual no los provee.
4. Especificar payloads mínimos y correspondencias kind/phase/record_key; preservar
   artifact_prepared y la evidencia de runtime previa a cada fase.
5. Precisar EVALUATION_COMPLETED y evidencia científica faltante, incluida matriz
   de confusión sin calibración, sin cruzar la gobernanza TRAIN/VAL/TEST.
6. Diseñar integración futura de report, tratamiento de errores y entrega/idempotencia.
   No confundir cómputo completed con verificación o liberación del proceso Local.
7. Diseñar en la fase autorizada la consolidación de resultados y adapters/servicio
   de resultados, manteniendo runs canónico y evidencia incremental append-only.

Estos gaps son documentación pendiente; no autorizan ni implementan E10.2.
