# E10.4 — DockerRunReporter y composición explícita

## 1. Objetivo y referencias

Crear el reporter Docker y una factory de composición que hagan disponible la cadena
aprobada de resultados, sin cambiar el runtime productivo. Referencias leídas completas
en esta secuencia de trabajo: [baseline](baseline.md), [E10.1](e10_1_contracts.md),
[E10.2](e10_2_result_service.md) y [E10.3](e10_3_postgres_result_repository.md).
Se contrastaron los contratos y módulos actuales, execution/worker.py, campaign.py,
repository.py, global_gate.py, train.py, artifacts.py y consumidores de records.
Base inspeccionada: `7de9cde58c0a705964d672834d81d134353d373e`, árbol inicialmente limpio.

E10.1–E10.3 permanecen intactas. No se encontró una insuficiencia que requiera cambiar
el puerto o agregar migración. Esta entrega sólo compone y ejercita eventos sintéticos.

## 2. Arquitectura

```text
Synthetic RunEvent
       |
       v
DockerRunReporter
       |
       v
ResultService
       |
       | ResultRepository port
       v
PostgresResultRepository
       |
       v
PostgreSQL

train() ── X ── todavía no integrado
```

El núcleo científico, los workers y la coordinación no importan el nuevo reporter
ni el composition root. ResultService sigue importando únicamente el puerto abstracto.

## 3. Ubicación y archivos

Reporter: `malaria_dl_local_project/src/malaria_dl/execution/reporters/docker.py`.
El paquete reporters mantiene separados los adapters de reporte y los contratos.
Su `__init__.py` no carga composición ni persistencia.

Archivos creados:

- `malaria_dl_local_project/src/malaria_dl/execution/reporters/__init__.py`
- `malaria_dl_local_project/src/malaria_dl/execution/reporters/docker.py`
- `malaria_dl_local_project/src/malaria_dl/execution/composition.py`
- `malaria_dl_local_project/tests/test_docker_run_reporter.py`
- `malaria_dl_local_project/tests/test_docker_reporter_architecture.py`
- `malaria_dl_local_project/tests/test_docker_reporter_postgres.py`
- `docs/engineering/e10_execution_refactor/e10_4_docker_reporter.md`

No se modifica ningún archivo preexistente.

## 4. Composición

`execution/composition.py` expone:

```python
build_docker_run_reporter(
    context: ExecutionContext,
    *,
    execution_token: UUID,
    engine_factory: Callable[[], Engine] = get_engine,
) -> DockerRunReporter
```

Construcción exacta:

```python
repository = PostgresResultRepository(
    execution_token=execution_token, engine_factory=engine_factory,
)
return DockerRunReporter(context, ResultService(repository))
```

Sólo este borde nuevo conoce el adapter concreto. La factory no abre conexión,
no ejecuta SQL y no llama engine_factory hasta el primer report. El adapter aprobado
conserva propiedad de Engine, conexión y transacción por aceptación. No se pasa una
conexión ambient ni un savepoint. No se añade framework DI, singleton ni autoarranque.

El llamador entrega contexto y token global confiables. No se leen variables de entorno,
CURRENT/global_gate ni session para reconstruir identidades en la factory. El worker
actual recibe owner por argumento y usa attach_worker/gate; no se conecta esa ruta.
La transformación futura de datos de entrada hacia ExecutionContext queda explícitamente
pendiente. El token global no se confunde con context.owner.

## 5. API de DockerRunReporter

Implementa la ABC RunReporter aprobada:

```python
DockerRunReporter(context: ExecutionContext, result_service: ResultService)
report(event: RunEvent) -> None
```

Dependencias del reporter: API pública de execution.contracts y results, exclusivamente.
No conoce SQL, tablas, PostgreSQL, drivers, transporte, filesystem o transacciones.
No consulta identidades, genera UUID, asigna secuencias, establece timestamps,
interpreta payloads ni decide tipos de evento.

## 6. Delegación y aceptación

Cada report llama exactamente una vez a
`result_service.accept_event(self._context, event)`, pasando las mismas instancias.
No modifica, copia ni reemplaza el evento. Un retry vuelve a delegar; no se cachea ni
se deduplica localmente.

El recibo debe ser EventAcceptance con status ACCEPTED o DUPLICATE_ACCEPTED. Ambos
se traducen al retorno None del puerto existente. Una respuesta inesperada produce
RuntimeError(UNEXPECTED_EVENT_ACCEPTANCE), nunca éxito silencioso. No se modifica
RunReporter para retornar el recibo.

No hay catch de excepciones del servicio: EventIdConflict, SequenceConflict,
SequenceGap, WriterNotAuthorized, ResultPersistenceError y otros errores se propagan
sin transformación, logging con éxito ni retry automático.

## 7. Fencing

El reporter sólo transmite contexto/evento. La cadena aprobada valida owner, sesión
activa, run/attempt, metadatos y token global. La factory no cambia las reglas E10.3.
Los tests por composición real acreditan que owner incorrecto no inserta, y que una
sesión cerrada por el repositorio legacy rechaza incluso el retry de un evento previo.
No hay autorización específica de plataforma dentro del reporter.

## 8. Idempotencia

Primer reporte persiste; retry por la misma instancia o tras reconstruir por completo
reporter/service/repository no añade filas ni altera el evento existente. La comparación
incluye todo el canonical E10.2 preservado por E10.3. Mismo ID con payload distinto
propaga EventIdConflict. El reporter no tiene almacenamiento ni lógica de idempotencia.

## 9. Sequence

Los tests construyen explícitamente eventos con sequences 1 y 2. La cadena los acepta;
un evento nuevo en posición ocupada produce SequenceConflict y un salto produce
SequenceGap. No se renumera ni espera automáticamente.

HEARTBEAT del contrato sigue reservado para una integración con asignador común;
el heartbeat operativo actual permanece fuera del stream. Esta etapa no resuelve
la coordinación entre productores; se documenta para E10.6.

## 10. Tests PostgreSQL y regresión

Se reutiliza sin modificaciones la fixture `pg` de E10.3, que depende de
`test_campaigns_postgres.isolated`. Instala explícitamente la revisión
20260922_01_result_events en cada schema temporal y configura conexiones independientes.
El test no presupone que la migración exista en public.

Todos los tests nuevos PostgreSQL construyen la cadena mediante la factory real,
con token y engine_factory de la fixture. Casos:

- Siete tipos representativos: epoch, artifact prepared/created, selection,
  calibration, evaluation y training completed.
- Primer evento, segundo evento, retry exacto y recreación completa de objetos.
- Conflicto de ID, conflicto de secuencia y gap.
- Owner incorrecto y sesión no activa.
- INSERT real seguido de fallo controlado en commit: error propagado, sin fila,
  retry posterior exitoso.
- Lectura mixta legacy/E10 y comportamiento real del hash/verificador.

Snapshots completos de runs, campaign_attempts, campaign_members y
train_execution_sessions antes/después comprueban ausencia de cambios por el reporter,
incluido runs.parameters. Los tests de cierre de sesión usan una mutación legacy
explícita sólo sobre datos sintéticos para preparar el rechazo esperado.

Resultados: **298 pruebas aprobadas**.

| Grupo | Resultado |
| --- | --- |
| Unitarios y guardas nuevos E10.4 | 16 passed |
| Integración PostgreSQL nueva E10.4 | 13 passed |
| E10.1/E10.2 y guardas E10.3 | 169 passed |
| Integración PostgreSQL E10.3 | 49 passed |
| ExecutionRepository y ejecución controlada PostgreSQL | 32 passed |
| artifacts/verify_session y coordinación sintética | 19 passed |

Total nuevo: 29. Total regresión: 269. Se excluyó un test que inspecciona public;
en regresión de artifacts se excluyeron el test que invoca train con dobles y el de
inspección de migración. No se ejecutó entrenamiento real, TEST clínico ni campañas reales.

Comandos locales desde raíz con PYTHONPATH=malaria_dl_local_project,
PYTHONDONTWRITEBYTECODE=1 y PYTEST_DISABLE_PLUGIN_AUTOLOAD=1:

```sh
malaria_dl_local_project/.venv-local-train/bin/python -B -m pytest -p no:cacheprovider malaria_dl_local_project/tests/test_docker_run_reporter.py malaria_dl_local_project/tests/test_docker_reporter_architecture.py malaria_dl_local_project/tests/test_execution_contracts.py malaria_dl_local_project/tests/test_execution_contract_dependencies.py malaria_dl_local_project/tests/test_result_service.py malaria_dl_local_project/tests/test_result_dependencies.py malaria_dl_local_project/tests/test_result_postgres_architecture.py -q
malaria_dl_local_project/.venv-local-train/bin/python -B -m pytest -p no:cacheprovider malaria_dl_local_project/tests/test_campaign_executor_e5.py malaria_dl_local_project/tests/test_campaign_exit_diagnostics.py -k 'not test_train_uses_only_train_and_val_without_csv and not test_migration_has_no_accidental_binds' -q
```

PostgreSQL se ejecutó en el backend existente desde una copia temporal del código,
no desde la aplicación desplegada:

```sh
docker exec -w /tmp/capstone_e10_4_f341bbe1 \
  -e PYTHONPATH=/tmp/capstone_e10_4_f341bbe1/malaria_dl_local_project \
  -e PYTHONDONTWRITEBYTECODE=1 -e PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  -e RUN_E10_DOCKER_REPORTER_POSTGRES_TESTS=1 -e RUN_E10_POSTGRES_TESTS=1 \
  -e RUN_STAGE5_POSTGRES_TESTS=1 -e RUN_STAGE93_CONTROLLED_POSTGRES_TESTS=1 \
  capstone_backend python -B -m pytest -p no:cacheprovider \
  malaria_dl_local_project/tests/test_docker_reporter_postgres.py \
  malaria_dl_local_project/tests/test_result_repository_postgres.py \
  malaria_dl_local_project/tests/test_campaign_executor_postgres.py \
  malaria_dl_local_project/tests/test_controlled_train_postgres.py \
  -k 'not public' -x -q --tb=short
```

Resultado de ese comando: 94 passed, 1 deselected. Las fixtures eliminan sus schemas
capstone_test_e4_<uuid> y comprueban ausencia. Sólo copian definición de auditoría,
no datos científicos de public. La copia temporal se retira al terminar.

Guardas nuevas: allowlist de imports del reporter, ausencia de generación de eventos
por el reporter, ausencia de acoplamiento de contratos/servicio a reporter/persistencia,
ausencia de integración en train/worker/campaign y proceso -I -S -B que importa el
reporter sin infraestructura instalada. Las guardas E10.1–E10.3 siguen intactas.

## 11. Auditoría de readers y records_hash

### Cálculo actual

`ExecutionRepository.records()` devuelve todos los registros de un run con sólo
`kind, phase, record_key, payload`, ordenados por `kind, phase, record_key`.
No selecciona created_at, event_id o event_sequence como columnas independientes;
los eventos E10 sí llevan identidad y sequence dentro del canonical y su record_key.

`campaigns.contracts.digest(records)` es SHA-256 del UTF-8 de canonical(records).
canonical ordena claves JSON, preserva orden de listas y normaliza floats integrales.
No elimina IDs/timestamps. El canonical E10 es un string dentro del payload: no se
reinterpreta ni normaliza su contenido numérico al calcular el hash legacy.

`train.py` lee records tras calibration y construye completion.records_hash.
`verify_session()` vuelve a leer todo y compara el digest antes de verificar épocas,
fases, predicciones, selección y checkpoint. La lectura no congela por sí misma
el ledger; la prohibición posterior de escritura depende del cierre de sesión.

### Consumidores y comportamiento con E10

| Consumidor | Comportamiento |
| --- | --- |
| ExecutionRepository.records | Enumera todos los kinds; query válida con filas mixtas |
| train() | Incluye todos los records en completion.records_hash |
| verify_session | Hash de todos; exige evidencia legacy por claves, no rechaza kinds adicionales por sí solos |
| campaign.reconcile/execute_campaign | Llaman verify_session; heredan el requisito del hash |
| controlled.recover/execute_one | Igual requisito de verificación |
| standalone y LocalBackend.operation('exit') | Verifican por el mismo contrato vigente |
| Reports.records → LocalBackend records | Devuelve la lectura existente; no filtra eventos E10 |
| assessment.lineage.resolve | Revalida verify_session y proof almacenado; luego filtra calibration/val/selected |
| training_summaries | Consulta lateral filtra calibration/val/selected; E10 no sustituye ese payload |

Los ocho kinds legacy siguen siendo la evidencia requerida por verify_session.
El código selecciona epochs/artifacts y busca runtime/phase/calibration y evidencia
por época; no trata un E10 EPOCH_COMPLETED como sustituto de kind='epoch'. Tampoco
exige que el conjunto completo de kinds sea exactamente esos ocho.

La prueba de lectura ejecuta ExecutionRepository.records real y la consulta filtrada
de calibration sobre PostgreSQL. Acredita columnas y filas legacy sin cambios,
lectura del registro E10 y ausencia de mutaciones. No ejecuta el endpoint completo
de training_summaries ni una evaluación: la auditoría de esos consumidores es estática.

### Blocker para integrar TRAIN en E10.6

Añadir un evento E10 **cambia digest(records)**. La prueba construye evidencia legacy
sintética válida, verifica, inserta TRAINING_COMPLETED por la nueva cadena y acredita
TRAIN_RESULTS_INCOMPLETE con el hash anterior. Si el hash local sintético se recalcula
incluyendo todas las filas, el mismo verify_session pasa con loader falso; no se toca
completion persistido ni se carga un modelo.

Por tanto hay un **blocker de integración**, no un fallo de las consultas puramente
lectoras ni un bloqueo para entregar E10.4 aislada: acordar frontera de finalización,
conjunto de evidencia y orden de emisión/hash antes de insertar desde train real.
Un TRAINING_COMPLETED emitido después de calcular el hash puede invalidarlo; después
de cerrar sesión sería rechazado por fencing. Además, los eventos nuevos por sí solos
no satisfacen la verificación legacy. No se corrige silenciosamente verify_session,
records(), completion ni los consumidores de linaje.

## 12. Side effects explícitamente ausentes

EVALUATION_COMPLETED y TRAINING_COMPLETED sólo agregan evidencia E10. No modifican
runs.parameters, status, campos de progreso, campaign_attempts, campaign_members ni
train_execution_sessions. Los snapshots completos acreditan esto para los siete tipos.
La aceptación durable no equivale a completed/verified ni a liberación de gate/proceso.

## 13. Cambios no realizados

Sin cambios en train ni firma, Docker worker, execute_campaign/run_child, global_gate,
ExecutionRepository, verify_session, agentes/workers/backend/transport Local, FastAPI,
heartbeat, contratos E10.1/E10.2 o adapter E10.3. No hay HttpRunReporter, event factory,
asignador de sequence, spool, consolidación científica ni nuevas migraciones.
No cambian dependencias, VENV, Dockerfile o despliegue. No se aplica migración al esquema
operativo. No se crean commits; el diff contiene sólo reporter, composición, tests y
este documento. El esquema y datos operativos no se modificaron; DDL/DML de pruebas
se limitaron a schemas temporales de la infraestructura aprobada.

## 14. Gaps E10.5 / E10.6

**E10.5:** transporte HTTP del contrato, preservación del envelope en retries,
composición del lado servidor y traducción confiable de identidad/owner Local. Resolver
respuesta perdida y errores sin duplicar lógica del servicio ni asumir que el owner
público Local sea el owner interno requerido por el adapter.

**E10.6:** construcción de ExecutionContext desde entradas autorizadas; producer/event
factory con ID/timestamp estables y asignador común de sequence; resolver el blocker
records_hash/completion y evidencia legacy antes de integrar train/worker. Definir el
orden de eventos terminales frente a cierre/fencing/verificación. Mantener heartbeat
fuera del stream hasta acordar coordinación entre productores.

La eventual consolidación de resultados científicos y el gap de matriz siguen fuera
de E10.4. Esta entrega termina con revisión humana, sin integrar el worker Docker.
