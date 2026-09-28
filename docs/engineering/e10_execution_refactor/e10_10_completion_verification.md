# E10.10 — Completion y verificación científica

## 1. Objetivo

Exigir evidencia científica durable coherente para completed y volver a validarla
antes de verified, conservando el contrato de los TRAIN históricos sin E10.

## 2. Auditoría de estados

Base actual: f373d87. Worktree limpio al comenzar; E10.0–E10.9 y los módulos de
execution, local_execution, results y result_repository son idénticos a 1b4b92f0,
la base previamente auditada. Referencias: baseline y documentos E10.1–E10.9 de
este directorio. No se recupera ni se presupone ningún borrador no persistido.

| Camino | Caller | completed | verify | verified |
|---|---|---|---|---|
| Campaña Docker | worker.run_scientific_train → train | train construye completion y llama ExecutionRepository.finish | campaign.execute_campaign después de retorno exitoso del child y preflight | mismo coordinator llama finish |
| Controlled Docker | controlled.execute_one → mismo worker | mismo train/finish | verify_session después del child y preflight | controlled.execute_one llama finish |
| Resume campaña | campaign.reconcile | no fabrica completion; nuevo intento ejecuta train | revalida verified; verifica completed existente | finish verified para completed existente |
| Recover controlled | ControlledRepository.recover | no relanza ni crea completion | preflight y verify_session si completed y procesos ausentes | finish verified |
| Local | worker → train → Reports | Reports.finish sólo manda calculation-ended; LocalBackend guarda job.completion. La transición real ocurre en exit, tras prueba de ausencia y exit_code=0 | LocalBackend.exit llama verify_session con loader backend | finish verified y release en la MISMA transacción exterior |
| Standalone legacy | train._standalone | train sin emitter → finish legacy | revalidación dataset y verify_session con keras_loader | finish verified legacy |
| Lectura de linaje assessment | assessment.lineage.resolve | no transiciona | verify_session con loader no-op sobre TRAIN ya verified; integridad/hash físico siguen comprobándose | no transiciona |

Completion actual de train: epochs, selection, records_hash y clinical_objective_met.
Se construye después de calibration legacy (también marcador disabled), evaluación
E10, lectura ordenada de records legacy y digest. Después emite TRAINING_COMPLETED
y llama finish. Verification actual: status=verified, records_hash, artifact y
selection. verify_session comprueba estructura legacy, artifact único, confinamiento,
SHA/bytes y carga del modelo antes de devolver esa evidencia.

Failed/interrupted: coordinadores registran fallo de child y excepción mientras la
sesión esté active; reconcile cierra active como interrupted tras probar ausencia;
standalone cierra active failed; Local exit no exitoso cierra failed. Se conservan
las guardas SQL existentes, incluidas las restricciones desde completed y estados
terminales. Repetir finish(completed) no es idempotencia de escritura: la política
actual rechaza completed→completed. Se preserva el rechazo sin reescribir evidencia.

Locking previo: finish bloquea campaña/member, luego actualiza sesión, attempt y
run en una transacción. Los writers legacy/E10 necesitan lock de sesión. Local
agrega locks gate/job y savepoints dentro de su transacción exterior. La ampliación
conserva esta frontera y hace explícitos attempt/session/run antes de leer ciencia.

Vínculo disponible: selection.selected_epoch → artifact del epoch (version_id,
SHA256, bytes, run y path) → predictions del mismo phase/key/epoch; la fila
calibration/val/selected contiene checkpoint_epoch y samples de la recarga final,
también con calibración OFF. TRAIN genera evaluation con esos labels/scores.
Puede verificarse la correspondencia estructural y recalcular métricas desde esos
samples sin ejecutar predict ni modificar TrainingResultsV1. No demuestra por sí
sola que scores arbitrarios hayan sido generados por una red: esa procedencia sigue
confiando en el productor autorizado; no se presenta como atestación criptográfica.

## 3. Regla E10 versus legacy

E10-governed: existen filas durables clasificadas por event_id IS NOT NULL,
leídas por read_result_events. Un sello training_completion_v1 ya persistido
conserva esa clasificación aunque alguien elimine ilegalmente todo el stream:
no puede degradarse a legacy para omitir la comprobación. El test puro cubre esto.
Sin eventos ni sello previo se aplican las reglas legacy. No se infiere de fecha,
campaign_id, nombre, parámetros científicos ni payload aportado por el caller.
Un stream corrupto falla cerrado en el reader, nunca se clasifica como legacy.
No hay backfill ni reinterpretación de evidencia histórica.

## 4. TrainingCompletionContractV1

Dataclass frozen, schema training_completion_v1. UUID canónicos, enteros positivos
estrictos, split val, hashes SHA-256 hexadecimales y evaluación anterior al terminal.
from_dict exige exactamente el conjunto de campos del contrato.

| Grupo | Campos |
|---|---|
| Identidad | run_id, attempt_id (nullable), dataset_version_id |
| Población | validation_split, validation_n_samples |
| Evaluación | evaluation_event_id, evaluation_sequence, evaluation_fingerprint |
| Resultado | training_results_hash |
| Terminal | terminal_event_id, terminal_sequence, terminal_fingerprint |
| Checkpoint | checkpoint_epoch, checkpoint_version_id, checkpoint_sha256, checkpoint_bytes, checkpoint_identity_hash |
| Contexto | dataset_snapshot_hash, configuration_hash, validation_predictions_hash |
| Evidencia legacy | records_hash |
| Versión | schema_version |

Se persiste en train_execution_sessions.completion.training_completion. Los campos
legacy se preservan; el caller no suministra el sello ni se muta su diccionario.
No contiene otra copia de matrix/métricas ni datos de Docker/Python/Local.
Verification añade training_completion_hash al proof existente.

## 5. Fuentes de evidencia

ExecutionRepository carga sesión, run, records legacy ordenados, eventos E10
ordenados y snapshot de campaña dentro de la conexión de transición. El validador
consume CompletionEvidence y no importa SQL, FastAPI, reporters, Local ni filesystem.
TrainingResultsV1 y ValidationEvaluationV1 se deserializan otra vez, sin modificar
sus contratos E10.9. La proyección y el payload deben ser canónicamente iguales.
No se elige una fuente ganadora ni se repara una inconsistencia automáticamente.

## 6. Evaluation fingerprint

SHA-256 de canonical_event(event). Incluye el sobre entero: identidad, sequence,
fecha y payload. Reutiliza la serialización E10 aprobada; un cambio de timestamp
con idéntica evaluación también invalida el sello. El terminal usa el mismo método.

## 7. Training results hash

Digest SHA-256 con campaigns.contracts.digest/canonical sobre TrainingResultsV1.
Esta canonicalización normaliza integral float/int, necesaria para JSONB, y
rechaza valores no finitos. Se usa también para comparar payload y projection.
El fingerprint del sobre E10 conserva su canonicalización original; no se mezclan
las dos representaciones ni se crea una tercera variante.

## 8. Dataset y población

run.id, run_type=training y dataset_version_id deben coincidir con la sesión.
Se compara el snapshot completo de sesión con execution_parameters.
model_configuration_e2.dataset del run y con el snapshot de campaña, si existe.
Así se vinculan patient_assignment, record_assignment, source_population,
clinical_identity y los demás campos persistidos, sin duplicarlos en el sello.
La configuración se compara con la original del run. counts.val debe ser entero
y coincidir con evaluation.n_samples y ambas colecciones de samples VAL.
Completion no recuenta directorios ni accede al dataset por red.

## 9. Threshold ON/OFF

ON exige source=validation_calibration, threshold_used y threshold_selected
coherentes con evaluation, y exactamente un CALIBRATION_COMPLETED anterior a la
evaluación cuyo payload coincide con la evidencia legacy actual. Comparación con
math.isclose, tolerancias relativa y absoluta METRIC_TOLERANCE=1e-12 de E10.9.
No se vuelve a calibrar.

OFF exige source=default y DEFAULT_THRESHOLD del helper vigente; no introduce
otro literal 0.5. No exige evento de calibración. El pipeline actual siempre
persiste calibration/val/selected, incluso OFF, con result.enabled=false y samples
de la recarga final: se utiliza para vincular predictions, no como calibración
calculada. También era requisito del verificador legacy. No se depende de una
fila que el pipeline OFF no produzca; los E2E reales ON/OFF prueban esta distinción.

## 10. Checkpoint linkage

La cadena durable es selection.selected_epoch → artifact único → phase/key de
artifact_prepared y predictions del epoch → calibration/val/selected.checkpoint_epoch
con los samples de la recarga final → evaluation. Se comprueban run, epoch, path
preparado, población y correspondencia de identificadores/labels VAL. La selección
final coincide con la del último epoch. Se recalculan confusion matrix y métricas
con el helper E10.9 a partir de los scores finales, sin predict ni recalibración.
Las métricas usan tolerancia 1e-12 y AUC None conserva su semántica.

Completed exige identidad/version/SHA/bytes esperados; no abre el archivo.
Verified añade existencia, ausencia de symlink/partial, confinamiento en artifact_root,
run correcto, hash/bytes físicos y carga real con validación input/output de Keras.
La identidad completa del artifact, incluido path, queda ligada por su digest.

Límite: es linaje estructural del productor autorizado, no prueba criptográfica de
que la red produjo cada score. No existe una atestación por inferencia en V1 y no
se promete. La evidencia existente sí permite este vínculo sin cambiar E10.9.

## 11. records_hash

Continúa digest(read_legacy_execution_records), con la misma ordenación y
exclusión event_id IS NOT NULL. No se incluyen eventos ni el nuevo completion en
ese digest. El hash legacy se compara con el terminal y el completion propuesto;
los golden E10.6–E10.9 permanecen intactos.

## 12. Validación de completed

finish(completed): locks → lectura durable → único validador → sello en completion
→ UPDATE de sesión, attempt/member y run. Exige stream contiguo desde 1, identidades
coherentes, una evaluación final y un único terminal TRAINING_COMPLETED al final,
posterior a la evaluación. Cualquier TRAINING_FAILED contradice éxito. Un retry
exacto de evento conserva una sola fila por las guardas E10 existentes.

Errores explícitos CampaignError: MISSING_TRAINING_EVALUATION,
TRAINING_RESULTS_MISMATCH, VALIDATION_POPULATION_MISMATCH,
TRAINING_THRESHOLD_MISMATCH, MISSING_TRAINING_TERMINAL_EVENT,
INVALID_TRAINING_EVENT_STREAM, SELECTED_CHECKPOINT_MISMATCH,
TRAINING_DATASET_SNAPSHOT_MISMATCH y COMPLETION_EVIDENCE_MISMATCH.
No se devuelve False ni se cambia estado al rechazar. Failed/interrupted no
entran en esta validación científica; conservan las transiciones SQL existentes.

## 13. Validación de verified

verify_session llama scientific_completion, reconstruye el contrato desde fuentes
actuales y exige igualdad con el sello. Luego conserva toda la verificación legacy
y el loader existente. Para E10 vuelve a medir hash/bytes después de cargar y
adjunta training_completion_hash al proof.

finish(verified) vuelve a cargar y validar bajo locks, compara el proof con el
contrato derivado, records_hash, artifact y selection, y comprueba otra vez el
archivo físico. Una prueba obtenida antes de manipular SQL o archivo no permite
la transición. La lectura de verificación no es por sí misma una transición ni
mantiene locks durante la carga Keras; el control definitivo ocurre en finish.
El loader sigue siendo responsabilidad del backend autorizado existente; no se
introduce una API para aportar pruebas arbitrarias desde el worker Local.

## 14. Atomicidad

Se conserva la transacción de ExecutionRepository.finish y su autorización de
owner. Orden: campaña → member → attempt → sesión → run. Los locks se adquieren
antes de clasificar E10/legacy y leer evidencia; también se bloquea la llegada de
un primer evento concurrente. Escritura del sello y estados se confirma o revierte
junta. La prueba de fallo durante UPDATE de runs comprueba rollback del sello.
Local conserva su transacción exterior y savepoints: si falla verify se revierte
completed, sello y release de ese exit. No se cambia el nivel de aislamiento.

## 15. Concurrencia e idempotencia

Conexiones independientes prueban dos finish simultáneos: uno tiene éxito, el otro
recibe rechazo y no reescribe el sello. finish versus writer E10 retiene los locks
mientras se valida: el writer NOWAIT es rechazado. El stream abierto sin terminal
no completa; después del terminal coherente sí. Se conserva la política SQL de
rechazar completed→completed, incluida repetición equivalente, y estados terminales
inmutables. No se introduce otra estrategia de locks ni un coordinador paralelo.

## 16. Tampering

Fixtures privilegiadas sólo en schemas temporales alteran projection, threshold,
matrix, sobre E10, artifact SHA/path, dataset_version, snapshot y sello. Se exige
rechazo tanto de verify_session como de finish(verified) con un proof anterior.
La fixture deshabilita/restituye triggers de usuario únicamente donde la guarda
existente impide fabricar la corrupción; no existe API de mutación nueva.
También se prueba cambio físico del checkpoint después del loader y restauración
del archivo sintético al terminar. El sello detecta modificaciones aun cuando el
JSON científico modificado sea formalmente válido.

## 17. Docker

Worker y train conservan su composición. TRAIN real de un epoch Keras, imágenes
sintéticas train/val, reporter y PostgreSQL reales prueban ON y OFF hasta verified,
con training_results_v1 y training_completion_v1. Tests del worker con ciencia
controlada cubren además fallos y la frontera común sin duplicar validación allí.

## 18. Local

E2E nativo Darwin: worker subprocess → journal → HTTP → backend → PostgreSQL.
ON/OFF alcanzan verified/released con el mismo contrato y hash de proof. Se prueba
fallo de calculation-ended y de carga/verify, además de reconcile del exit y
pending/ACK. La posición real de completed se conserva: calculation-ended guarda
la evidencia del job; exit con ausencia probada y código cero realiza completed,
verify, verified y release dentro de la transacción backend. No se adelanta a
calculation-ended ni se añade lógica científica de cierre al Mac.

## 19. Controlled y resume

Controlled usa el mismo worker/finish y obtiene sello para su nuevo run. Recover
revalida la sesión verificada sin relanzar ciencia. Resume cierra el intento previo,
crea otro run/attempt y su stream desde sequence=1; el test exige run_id propio en
el nuevo sello, diferente del anterior. No se hereda completion ni hay bypass.

## 20. Compatibilidad legacy

Sin eventos E10 ni sello previo: completed/verified siguen las reglas originales,
sin exigir training_results ni terminal E10. Prueba PostgreSQL real completa ambos
estados. Los test doubles históricos de records sin scientific_completion siguen
soportados por verify_session; los repositorios de producción implementan el hook.
El CLI standalone continúa sin emitter y usa esta excepción transitoria. No hay
conversión automática, backfill, nuevas obligaciones históricas ni cambio de firma.

## 21. Pruebas

Resultado (2026-09-28): **746 pruebas únicas aprobadas; 79 nuevas + 667 de
regresión**. No se suman reejecuciones ni los casos deseleccionados.

| Batería | Resultado | Nuevas | Regresión |
|---|---:|---:|---:|
| Host: contratos, servicios, arquitectura, TRAIN controlado, golden/readers, métricas, callbacks, summaries y completion puro | 477 passed | 51 | 426 |
| Docker: PostgreSQL real, TRAIN Keras ON/OFF, workers, HTTP, Local backend, campaign/controlled/global y foundation | 261 passed | 28 | 233 |
| Mac nativo: agent/subprocess, journal/HTTP/backend/PostgreSQL y reconcile | 8 passed | 0 | 8 |
| Total | 746 | 79 | 667 |

Las pruebas existentes de Docker real, Local y controlled/resume añaden aserciones
del sello. Dos pruebas antiguas que aceptaban un stream E10 incompleto ahora
acreditan rechazo sin modificar records_hash ni estados. No se eliminan casos.
Las dos fallas iniciales de fixture fueron guardas SQL impidiendo la manipulación
de dataset_version_id; se corrigió la fixture privilegiada temporal y toda la
batería PostgreSQL volvió a pasar. No quedó un fallo de producto pendiente.
Avisos preexistentes: deprecaciones Starlette/anyio/protobuf y shuffle de Keras
sobre tf.data.Dataset; ningún error.

Reproducción: interpreter host .venv-local-train/bin/python, PYTHONPATH apuntando a
malaria_dl_local_project y backend_api, PYTHONDONTWRITEBYTECODE=1,
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, pytest -p no:cacheprovider. KERAS_HOME y
MPLCONFIGDIR bajo /tmp. Batería host: test_training_completion, training_results,
execution_contracts/dependencies, result_service/dependencies/postgres_architecture,
docker_run_reporter/reporter_architecture, http_run_reporter/reporter_architecture,
run_event_emitter/event_emitter_architecture, docker_train_integration/architecture,
event_journal, local_event_runtime/journal_architecture, local_docker_event_parity,
campaign_executor_e5, clinical_metrics, metrics, threshold_calibration,
execution_record_readers, clinical_validation_callback, checkpoint_policy y
backend test_training_summaries_api.

Batería Docker en copia temporal del código: test_training_completion_postgres,
training_results_postgres/docker, docker_train_postgres, local_journal_postgres,
event_emitter_records_postgres, result_repository_postgres,
docker_reporter_postgres, http_reporter_postgres, campaign_executor_postgres,
controlled_train_postgres, local_execution_postgres, global_execution_postgres y
backend test_foundation_http/config. Activados los opt-ins RUN_E10_* correspondientes,
RUN_STAGE5_POSTGRES_TESTS, RUN_STAGE93_CONTROLLED_POSTGRES_TESTS,
RUN_LOCAL_EXECUTION_POSTGRES_TESTS y RUN_STAGE93_GLOBAL_POSTGRES_TESTS. Excluidos
los 8 casos nativos (ejecutados en Mac) y test_public_e5_revision_readonly (para no
hacer depender esta prueba aislada de la revisión instalada en public).

Batería Mac: test_local_journal_postgres y test_local_execution_postgres filtrados
por test_native_agent o test_minimal_real_calculation_through_http_agent_and_subprocess;
8 passed, 25 deselected. DB por loopback al servicio existente, sin mostrar ni
persistir credenciales; JWT sintético temporal. Todos los procesos científicos
nativos usan TensorFlow real y el backend carga el checkpoint real. Threads TF/OMP
limitados a 1 en ambas plataformas para las pruebas sintéticas.

Las nuevas pruebas puras usan evidencia generada por train común, cubren ON/OFF,
contrato, identidad, duplicados, stream, proyección, población, threshold, checkpoint,
hashes, sello y arquitectura. Las PostgreSQL prueban rollback, concurrencia,
manipulación antes/después del cierre, prueba obsoleta, archivo físico y legacy.

Fixtures crean capstone_test_e4_<uuid>, fijan search_path exclusivamente al schema
y pg_catalog, usan conexiones independientes y eliminan el schema al terminar.
Sólo se lee la definición de public.audit_events para construir su copia sintética.
No se escribe public operativo ni se cambian .env, dependencias o servicios.
La consulta final encontró 9 schemas sintéticos preexistentes con sesiones del
2026-09-15; se conservaron. Las fixtures de esta batería comprueban la eliminación
de su propio schema y terminaron sin errores de teardown.

## 22. Cambios no realizados

Ninguna tabla/columna/migración nueva. Ningún cambio de TrainingResultsV1,
ValidationEvaluationV1, TRAIN, firma, Reports, reporters, emitter, journal,
heartbeat, sequence/pending, reader de summaries, TEST, release_status,
productive_stage2, publicación, deployment o UI. Los E2E usan exclusivamente
imágenes sintéticas TRAIN/VAL; no ejecutan TEST clínico. Las guardas existentes
contra acceso a TEST siguen incluidas en regresión.

## 23. Gaps E10.11

Persisten repository legacy dentro de train, Reports de Local, firma transitoria,
records legacy y dependencia de la evidencia calibration/selected para muestras
finales (incluido marcador OFF). La eliminación de estos acoplamientos requiere
una etapa posterior y preservar los hashes/contratos acreditados. E10.11 no se
implementa aquí. Revisar humanamente E10.10 antes de continuar.

