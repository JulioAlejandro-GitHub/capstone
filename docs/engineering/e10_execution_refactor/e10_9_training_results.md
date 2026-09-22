# E10.9 — Resultado científico final de TRAIN

## 1. Objetivo y alcance

Contrato científico versionado para la evaluación final VAL del checkpoint seleccionado,
evento común `EVALUATION_COMPLETED` y proyección transaccional en `runs.parameters`.
Aplica a TRAIN E10 Docker/Local. La firma transitoria y los ocho kinds legacy se
conservan. No se implementa E10.10 ni E10.11.

Referencias revisadas: baseline y documentos E10.1–E10.8 de este directorio,
contratos/emitter, ResultService/port/adapter PG, TRAIN/repository/verify_session,
helpers clínicos/calibración/checkpoint y lectores de parameters. Base de trabajo:
`de0e6b07` (E10.7/E10.8), worktree limpio al iniciar.

## 2. Gap inicial

TRAIN de campaña dejaba `parameters={}`. El callback calculaba más información de
la que registraba en logs. La matriz final existía dentro de calibration sólo si
la calibración estaba habilitada. `verify_session` podía aprobar una ejecución
sin una matriz persistida. E10.9 corrige la generación y persistencia para TRAIN
E10 nuevo; no cambia la política de aceptación de ejecuciones históricas/legacy.

## 3. Auditoría científica previa

Rutas bajo `malaria_dl_local_project/src/malaria_dl` salvo indicación explícita.
`src.metrics` es un adaptador del módulo canónico `evaluation/clinical_metrics.py`.

| Resultado | Función actual | Fuente | Split | Momento | Persistencia anterior a E10.9 |
|---|---|---|---|---|---|
| Scores VAL por época | `clinical_metrics.collect_predictions`, llamado por `PersistEpoch.on_epoch_end` | `model.predict(images)`, salida sigmoid probability_parasitized; salida vectorial se convierte con helper existente | val | Después de guardar artifact/selection de cada época | `predictions.samples[].score` legacy |
| Scores definitivos | `train`, `collect_predictions(selected, datasets['val'])` | `load_model(epoch_selected.keras, compile=False)` | val | Después de todas las fases, antes de calibración | `calibration.samples[].score`, también con calibración OFF |
| Labels verdaderos | `collect_predictions` | Labels del dataset, acumulados desde `labels.numpy()` | val | Mismas llamadas | `predictions/calibration.samples[].label` |
| Threshold de selección | `CheckpointPolicyConfig` y `ClinicalValidationMetricsCallback` | TRAIN pasa explícitamente `threshold=0.5` | val | Cada época/selección | Configuración/checkpoint y métricas de época; no es el threshold calibrado final |
| Threshold calibrado | `find_threshold_for_target_recall` | Candidates de scores VAL, política target_recall, min_specificity y desempates existentes | val | Checkpoint seleccionado | `calibration.result.threshold_used/threshold_selected`; source `validation_calibration` |
| Threshold OFF | Rama `else` de `train` y `collect_predictions(... threshold=0.5)` | Marcador existente `{'enabled': False, 'threshold': 0.5}` | val | Evaluación del checkpoint seleccionado | `calibration.result.threshold` |
| TN/FP/FN/TP | `compute_clinical_metrics` | `sklearn.confusion_matrix` con labels `[0,1]`, clases obtenidas con `>= threshold` | val | Callback por época y cada candidate de calibración | Sólo selected/default metrics de calibration ON; logs del callback omiten matriz |
| Recall/sensibilidad | `compute_clinical_metrics`, `_safe_divide` | TP/(TP+FN) | val | Callback/calibración | `epoch.val_recall_parasitized`, selection y calibration ON |
| Specificity | Mismo helper | TN/(TN+FP) | val | Callback/calibración | `epoch.val_specificity`, selection y calibration ON |
| Precision | `compute_clinical_metrics`, sklearn `precision_score(zero_division=0)` | Labels/clases VAL | val | Callback/calibración | `calibration.result.selected_metrics/default_threshold_metrics` ON |
| F1 | Mismo helper, `f1_score(zero_division=0)` | Labels/clases VAL | val | Callback/calibración | Calibration ON; no log final común |
| F2 | Mismo helper, `fbeta_score(beta=2.0, pos_label=1, zero_division=0)` | Labels/clases VAL | val | Callback/calibración | `epoch.val_f2_parasitized`, selection, calibration ON |
| Balanced accuracy | `compute_clinical_metrics` | (sensibilidad+specificity)/2 | val | Callback/calibración | `epoch.val_balanced_accuracy`, calibration ON |
| ROC-AUC | `_safe_roc_auc` → sklearn `roc_auc_score` | Scores float32, labels binarios | val | Callback/calibración | Logs val_roc_auc_parasitized/val_auc y calibration ON |
| PR-AUC | `_safe_pr_auc` → sklearn `average_precision_score` | Scores float32, labels binarios | val | Callback/calibración | Logs val_pr_auc_parasitized y calibration ON |
| Loss/val_loss | Keras `fit` → logs de `PersistEpoch` | Loss del entrenamiento/validación de cada época | train/val | Durante fit | `epoch` y, donde corresponde, datos de selección; no evaluación compilada final del checkpoint |

`clinical_predictions_from_probabilities` usa `score >= threshold`; positivo=1
parasitized, negativo=0 uninfected. El registry actual declara sigmoid
probability_parasitized. No se cambian estas convenciones ni el dtype float32
empleado por los helpers clínicos.

## 4. Punto único de evaluación

`evaluation/validation.py::evaluate_validation_predictions(labels, scores,
ThresholdResult)` produce `ValidationEvaluationV1`. Usa exactamente
`compute_clinical_metrics`, sin implementación alternativa de ciencia por runtime.
Valida vectores unidimensionales, población no vacía, mismo largo, labels 0/1,
scores finitos en [0,1]. TRAIN comprueba además el largo contra sample_paths VAL.

Se reutilizan los scores definitivos ya calculados al cargar el checkpoint
seleccionado. No hay nuevo `model.predict`, `model.evaluate`, carga de TEST ni
recalibración. El helper de evaluación no conoce SQL, HTTP, Docker ni Local.

## 5. Effective threshold

La variable explícita `effective_validation_threshold` contiene valor y source.
ON: `calibration['threshold_used']` y `calibration['threshold_source']`, cuyo valor
actual es `validation_calibration`. OFF: `calibration['threshold']`, exactamente
0.5, source `default`, consistente con `DEFAULT_THRESHOLD` y el uso real de TRAIN.
El contrato rechaza `source=default` con valor distinto de 0.5; no crea un modo
configured que no existe en este flujo.

## 6. Calibración ON/OFF

ON conserva candidates, objetivo, desempates, fallback y evento calibration.
OFF conserva el marcador legacy disabled y no emite CALIBRATION_COMPLETED.
Ambos emiten evaluación final. La fixture OFF utiliza un protocolo congelado con
`calibration.algorithm=none`, además del flag, respetando `VARIANT_PROTOCOL_CONFLICT`.
La evaluación final no sustituye las métricas de selección calculadas a 0.5.

## 7. TrainingResultsV1

Tipos pequeños frozen/slots: `TrainingResultsV1`, `ValidationEvaluationV1`,
`ThresholdResult`, `ConfusionMatrix`, `BinaryMetrics`. Ubicación:
`results/training.py`, sólo stdlib y helper puro `evaluation/binary_counts.py`.
No dependencia de SQLAlchemy, TensorFlow, sklearn, FastAPI o filesystem en el contrato.

Esquema exacto de salida, con ejemplo manual de cuatro muestras:

```json
{
  "training_results": {
    "schema_version": "training_results_v1",
    "validation": {
      "schema_version": "validation_evaluation_v1",
      "evaluation_role": "training_validation_final",
      "split": "val",
      "n_samples": 4,
      "threshold": {"value": 0.5, "source": "default"},
      "confusion_matrix": {"tn": 1, "fp": 1, "fn": 0, "tp": 2},
      "metrics": {
        "recall": 1.0,
        "specificity": 0.5,
        "precision": 0.6666666666666666,
        "f1": 0.8,
        "f2": 0.9090909090909091,
        "balanced_accuracy": 0.75,
        "roc_auc": 0.75,
        "pr_auc": 0.8333333333333333
      }
    }
  }
}
```

Ejemplo: labels `[0,0,1,1]`, scores `[0.1,0.8,0.6,0.9]`. El ejemplo es sintético,
no representa un modelo clínico. `to_dict` devuelve objetos separados en orden
estable; la identidad del evento sigue usando la canonicalización E10.2.

## 8. Confusion matrix

Cuatro enteros Python estrictos, no bool ni float, todos >=0. La suma debe ser
exactamente n_samples, entero positivo. No se duplican supports: positive_support
es TP+FN, negative_support TN+FP. Orden de presentación `[[TN,FP],[FN,TP]]`.

## 9. Métricas y loss

Recall, specificity, precision, F1, F2, balanced_accuracy, ROC-AUC y PR-AUC.
PR-AUC conserva la semántica existente de average precision, no integración
trapezoidal. AUC se obtiene desde scores, nunca desde la matriz.
Loss se omite deliberadamente: la loss disponible es por época; el checkpoint se
carga sin compilación y el flujo no produce una única loss final con semántica
inequívoca. No se renombra una loss de época como resultado final.
No se duplican completed_epochs/best_epoch/checkpoint_monitor u otras columnas.

## 10. Validaciones y cross-check

Claves exactas en cada objeto, versiones/role/split exactos. Campos desconocidos o
faltantes se rechazan. Métricas finitas en [0,1], sin clipping ni NaN→null implícito.
No se aplica `train.clean` al nuevo payload para ocultar valores no finitos.

`metrics_from_counts` realiza la validación independiente, de tamaño constante:

- recall = TP/(TP+FN), specificity = TN/(TN+FP), precision = TP/(TP+FP).
- F1 = 2TP/(2TP+FP+FN).
- F2 = 5TP/(5TP+FP+4FN), equivalente al helper existente sklearn beta=2.
- balanced_accuracy = (recall+specificity)/2.

Tolerancia explícita `METRIC_TOLERANCE=1e-12`, tanto absoluta como relativa.
Las fórmulas de chequeo no reemplazan los helpers científicos existentes; goldens
las contrastan con sklearn. El argumento beta de calibración no redefine F2:
el código existente lo conserva por compatibilidad, pero expone F2 beta=2.

Divisor cero produce 0.0, conforme `_safe_divide`/sklearn zero_division=0. Si falta
una clase real, ROC-AUC y PR-AUC son null, tal como ambos helpers `_safe_*` actuales.
Con ambas clases deben ser numéricas; con una clase deben ser null. La población
vacía se rechaza. No se recalculan AUC desde conteos.

## 11. EVALUATION_COMPLETED

Después del put legacy calibration (incluido disabled) y su evento si aplica,
antes de leer records/calcular completion/hash y emitir TRAINING_COMPLETED.
EVALUATION debe recibir ACK antes de avanzar; fallo conserva pending y aborta
TRAIN, sin finish(completed), conforme emitter E10.6/journal E10.8.

## 12. Payload y secuencia

Payload = `ValidationEvaluationV1.to_dict()` directamente, sin envelope artificial
legacy_record. Una época/una fase: sequence 8 evaluación y 9 completed con OFF;
9 evaluación y 10 completed con ON. El número depende de las épocas/fases, no se
codifica como constante en producción.

No existe `kind=evaluation` legacy: los ocho kinds históricos se preservan y el
resultado nuevo vive exclusivamente en E10 + namespace científico.

## 13. Atomicidad evento/proyección

ResultService conserva autorización, identidad y secuencia como primeras decisiones.
Para un evento nuevo EVALUATION_COMPLETED deserializa/valida el contrato; solicita
`scope.append()` y `scope.project_training_result(TrainingResultsV1)`.
No conoce tablas, columnas, jsonb ni SQL. La ampliación del port tiene default
fail-closed para adapters antiguos sin proyección; los demás eventos no la invocan.

El adapter PG usa la misma Connection y transacción raíz READ COMMITTED E10.3.
Tras insertar el evento ejecuta UPDATE sobre runs. COMMIT ocurre únicamente al
salir correctamente del scope. Cualquier fallo de proyección revierte también
INSERT. Un trigger temporal de prueba que rechaza UPDATE demuestra rollback con
conexiones reales independientes; no es sólo un fake de atomicidad.

## 14. runs.parameters

`runs` sigue siendo entidad canónica. `execution_parameters` sigue siendo input;
`parameters` recibe output. Nada toca input, completion, verification ni sus estados.
No tablas nuevas, no segunda identidad de resultado ni backfill.

## 15. Namespace y compatibilidad

Auditoría de lectores: training_summaries/run_lineage/lineage_children y
`governed_dataset` leen keys legacy (model, optimizer, cli_arguments, configuración);
case_gradcam y otros lectores consultan información de linaje/modelo/preprocessing.
No hay licencia para reemplazar todo parameters.

El adapter exige JSON object y ausencia de la key `training_results`, luego realiza
merge superficial `parameters || jsonb_build_object(...)`. Preserva todas las otras
keys, incluso objetos anidados. Namespace preexistente, incluyendo null o versión
desconocida, y parameters no-object se rechazan con FINAL_EVALUATION_CONFLICT.
No se reinterpreta ni limpia contenido histórico.

## 16. Idempotencia y errores

Retry mismo event_id/envelope exacto → DUPLICATE_ACCEPTED, sin nuevo INSERT/UPDATE.
Mismo id distinto contenido → EVENT_ID_CONFLICT antes de interpretar el payload.
Gap/conflict de secuencia, owner/fencing inválido o payload científico inválido
no modifica ninguno de los dos stores. Errores científicos usan
INVALID_SCIENTIFIC_RESULT (HTTP 422); conflictos 409, writer 403 y storage 503.

Una pérdida de ACK después de COMMIT deja ambos objetos durables. Retry exacto
recupera receipt sin cambiar parameters. El journal no implementa ciencia especial.

## 17. Concurrencia e inmutabilidad

Se retiene el lock exclusivo de train_execution_sessions y los locks de autorización
E10.3 hasta commit. Además UPDATE condiciona ausencia del namespace. Dos writers
con conexiones independientes no pueden crear dos finales: uno acepta; el otro
recibe conflicto de secuencia o storage NOWAIT retryable. Un segundo evento nuevo
con secuencia siguiente, aun con ciencia idéntica, obtiene FINAL_EVALUATION_CONFLICT.
Regla V1: una evaluación final VAL por run (`training_validation_final`).

Garantía dentro del port autorizado; no pretende resistir modificaciones SQL
arbitrarias de administradores fuera del flujo de aplicación. No se necesita DDL.

## 18. Docker

Reporter/composición existentes, mismo ResultService/adapter. Test Docker real
con custom_cnn, entrada 32x32, batch 2, 2 TRAIN + 2 VAL sintéticos, una época,
checkpoint Keras real. Ambas ramas ON/OFF validan resultado reconstruido desde
samples definitivos, secuencia, hash y verify_session con keras_loader real.
También regresión worker.main/campaign resume/controlled de E10.7 con dobles.

## 19. Local

Agente y worker reales en Mac/Darwin con venv existente. SQLite real, HTTP con JWT,
PostgreSQL temporal, checkpoint y verificación reales, una época ON/OFF. Secuencia:
pending durable → HTTP → evento+proyección atómicos → ACK → journal confirm.
Prueba separada pierde ACK después de commit, reabre journal y compara evento,
parameters y hash idénticos tras retry. No hay fork de ciencia por runtime.

La regresión conserva fallos de calculation-ended/verify y retención pending; no
convierte un evento terminal en prueba de finalización del proceso. No modifica
heartbeat, Reports, agent, worker Local, journal ni transporte. Las limitaciones de
recuperación científica y exit proof descritas en E10.8 siguen vigentes.

## 20. records_hash / TEST

Hash legacy sigue leyendo sólo filas legacy; ni el evento EVALUATION ni parameters
participan. Golden de readers y comparación contra TRAIN pre-E10.7 preservados.
No se carga TEST; los datasets sintéticos sólo crean carpetas train/val.
`evaluate_best_on_test=false`, `TEST_FORBIDDEN` y candidate lock permanecen intactos.

## 21. Readers

training_summaries selecciona namespace, lo valida mediante TrainingResultsV1 y
prefiere los campos del checkpoint final: recall, specificity, F2, ROC-AUC y matriz,
con metrics_split=val. Conserva contrato HTTP público y fallback SQL legacy cuando
no hay versión reconocida. V1 reconocida corrupta falla cerrado; no muestra matriz
inconsistente ni la esconde detrás del fallback.

No mezcla prediction_collapse de otra época con la nueva evaluación: devuelve null
para ese campo, que no integra V1. No se inventa un criterio de colapso ni se cambia UI.
El namespace completo no se expone como campo extra en TrainingSummary.

## 22. Legacy compatibility

train sin emitter conserva salida previa; misma firma transitoria. Legacy put,
Reports, hash, repository.finish y verify_session no cambian. Fixtures antiguas
con EVALUATION opaco fueron reemplazadas por contrato válido cuando corresponde;
las pruebas de eventos opacos sin efectos usan otros tipos. EVALUATION deja de ser
opaco deliberadamente, por requerimiento E10.9. RunEvent mantiene su envelope v1.

## 23. Pruebas y estado

**ESTADO E10.9: LISTA PARA REVISIÓN. 667 pruebas únicas aprobadas: 72 nuevas y 595 de regresión.**

| Grupo de ejecución final | Aprobadas |
|---|---:|
| Contratos/resultados/reporters/emitter/TRAIN/journal/paridad/ciencia + API summaries, host | 397 |
| Readers/hash golden + callback clínico + checkpoint policy, host | 29 |
| PG transaccional + Docker real + regresión Docker/Local/control/global/backend, contenedor | 233 |
| Agente/worker Mac real ON/OFF + fallos + pending + prueba Local preexistente | 8 |
| **Total único** | **667** |

Nuevas: 46 science/contrato/ResultService, 16 PG/HTTP/journal, 2 TRAIN Docker real,
4 readers summaries, 1 fallo de entrega EVALUATION, 3 escenarios nativos OFF
adicionales. Las dos pruebas de paridad preexistentes se amplían para comparar
estructuralmente payload y proyección científica Docker/Local. Se conservan como
regresión, no se cuentan dos veces.

Evidencia científica manual: TN=1, FP=1, FN=0, TP=2, recall=1, specificity=0.5,
precision=2/3, F1=0.8, F2=10/11, balanced_accuracy=0.75, ROC-AUC=0.75,
PR-AUC=5/6 para los labels/scores del ejemplo. La igualdad con sklearn F2 se prueba
con cinco matrices, incluidos casos de divisor cero. Ambos TRAIN reales comparan
el JSON contra los samples definitivos persistidos del checkpoint seleccionado.

Atomicidad: trigger temporal rechaza UPDATE y también desaparece el INSERT del
evento. Concurrencia: dos conexiones con barrera dejan una evaluación; nuevo intento
con sequence siguiente tampoco reemplaza resultado. Lost ACK: se acepta en PG,
se pierde la respuesta, se reabre SQLite y se confirma el mismo evento sin cambios.
Rechazos HTTP malformed/writer/gap/id conflict conservan ambos stores.

El comando PG amplio terminó con 232 passed y un error de setup en una fixture
secuencial que una edición de pruebas había alcanzado accidentalmente. Se restauró
esa sección legacy y se ejecutó el caso pendiente: 1 passed. La prueba de ACK se
repitió tras exigir EventTransportFailure específicamente: 1 passed, ya incluido
en los 233. No se suma nuevamente. Las 9 exclusiones del comando Docker son las
8 pruebas nativas ejecutadas en Mac y una inspección histórica public fuera de alcance.

Durante preparación hubo errores de colección por auxiliares ausentes en la copia
/tmp (configs del registry, script batch y paquete malaria_split); se completó esa
copia, sin instalar paquetes. Las fixtures OFF inicialmente contrariaban el protocolo
congelado threshold_grid; se corrigieron a algorithm=none, manteniendo las guardas.
Un golden de F2 vacío se cambió por una población negativa válida; el evaluador
rechaza población vacía explícitamente. No quedan fallos pendientes.

Warnings existentes de protobuf, Starlette/httpx/anyio y Keras shuffle de tf.data;
no cambian el resultado. Comprobación adicional: repository/finish, artifacts/
verify_session, agent, worker Local, Reports/transporte, journal, emitter y helpers
clinical_metrics/threshold_calibration son byte-idénticos a HEAD. Alembic: 29
revisiones, único head 20260922_01. `git diff --check` pasa.

Reproducción: venv existente, `python -B -m pytest -p no:cacheprovider`,
PYTHONPATH=malaria_dl_local_project:backend_api, PYTHONDONTWRITEBYTECODE=1,
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, KERAS_HOME/MPLCONFIGDIR en /tmp.
El grupo host usa tests E10.1–E10.8 más `test_training_results`,
`test_campaign_executor_e5`, `test_clinical_metrics`, `test_metrics`,
`test_threshold_calibration` y `backend_api/tests/test_training_summaries_api`.
Grupo adicional: `test_execution_record_readers`, `test_clinical_validation_callback`,
`test_checkpoint_policy`.

PG/Docker usa copia temporal `/tmp/capstone_e10_9_e116`, runtime existente del
backend, RUN_E10_POSTGRES_TESTS, RUN_E10_TRAIN_POSTGRES_TESTS,
RUN_E10_LOCAL_JOURNAL_POSTGRES_TESTS, RUN_E10_EMITTER_POSTGRES_TESTS,
RUN_E10_HTTP_POSTGRES_TESTS, RUN_E10_DOCKER_REPORTER_POSTGRES_TESTS,
RUN_STAGE5_POSTGRES_TESTS, RUN_STAGE93_CONTROLLED_POSTGRES_TESTS,
RUN_LOCAL_EXECUTION_POSTGRES_TESTS y RUN_STAGE93_GLOBAL_POSTGRES_TESTS, todos 1.
Se ejecutan los tests PG correspondientes, los dos nuevos archivos
`test_training_results_postgres`/`test_training_results_docker` y
backend `test_foundation_http`/`test_foundation_config`.

Mac: selección `test_native_agent or test_minimal_real_calculation_through_http_agent_and_subprocess`
en `test_local_journal_postgres` y `test_local_execution_postgres`, con opt-ins Local.
DATABASE_URL se deriva en memoria con host db y hostaddr=127.0.0.1, puerto publicado
5432; JWT efímero aleatorio, STORAGE_ROOT=/tmp. Credenciales no se imprimen ni
persisten. TF_NUM_INTEROP_THREADS/TF_NUM_INTRAOP_THREADS/OMP_NUM_THREADS=1.


## 24. Cambios no realizados

Sin migraciones (head permanece 20260922_01), tablas nuevas, backfill o escrituras
en runs históricos. Sin cambios de requirements, venv, Dockerfile/Compose,
persistencia de entorno, datos oficiales, TEST, candidate lock ni publicación.
Sin commit, despliegue ni modificación de la BD operativa fuera de los schemas
transitorios de fixtures, eliminados al terminar.

## 25. Requisitos concretos para E10.10

1. Definir cuándo completed/verified exigen presencia de evaluación final y proyección,
   distinguiendo runs E10 de históricos y standalone legacy.
2. Comprobar consistencia del contrato científico con evidencia seleccionada,
   population/threshold/checkpoint, no sólo la consistencia interna de su JSON.
3. Integrar dicha exigencia en finish/verify_session y errores de Completion Contract,
   preservando fencing y atomicidad; todavía no implementado.
4. Definir conducta ante proyección/evento ausente o alterado y ante commit incierto,
   sin rehacer ciencia ni inventar backfill.
5. Mantener distinción entre TRAINING_COMPLETED, finalización/verificación legacy,
   prueba de salida del proceso y release del job/gate.

E10.9 valida internamente el payload recibido; no reconsulta predictions legacy para
recalcular AUC ni acreditar procedencia en el backend. El productor común sí usa el
checkpoint seleccionado y samples definitivos, acreditado end-to-end.

## Anexo: archivos y Git al cierre

7 archivos creados: contrato científico, evaluador, validador puro de conteos,
3 archivos de pruebas E10.9 y este documento. 21 archivos modificados: integración
TRAIN, servicio/port/adapter/errores, route HTTP, reader summaries y pruebas/fixtures
de regresión. No cambios previos ajenos al turno: HEAD de0e6b07 ya incluía E10.7/E10.8.

`git status --short` (sin commit):

```text
 M backend_api/app/routes/local_execution.py
 M backend_api/app/services/training_summaries.py
 M backend_api/tests/test_training_summaries_api.py
 M malaria_dl_local_project/src/malaria_dl/execution/train.py
 M malaria_dl_local_project/src/malaria_dl/persistence/result_repository.py
 M malaria_dl_local_project/src/malaria_dl/results/errors.py
 M malaria_dl_local_project/src/malaria_dl/results/repository.py
 M malaria_dl_local_project/src/malaria_dl/results/service.py
 M malaria_dl_local_project/tests/result_repository_fake.py
 M malaria_dl_local_project/tests/test_docker_reporter_architecture.py
 M malaria_dl_local_project/tests/test_docker_reporter_postgres.py
 M malaria_dl_local_project/tests/test_docker_train_integration.py
 M malaria_dl_local_project/tests/test_docker_train_postgres.py
 M malaria_dl_local_project/tests/test_event_emitter_records_postgres.py
 M malaria_dl_local_project/tests/test_http_reporter_postgres.py
 M malaria_dl_local_project/tests/test_local_docker_event_parity.py
 M malaria_dl_local_project/tests/test_local_execution_postgres.py
 M malaria_dl_local_project/tests/test_local_journal_postgres.py
 M malaria_dl_local_project/tests/test_result_dependencies.py
 M malaria_dl_local_project/tests/test_result_repository_postgres.py
 M malaria_dl_local_project/tests/test_result_service.py
?? docs/engineering/e10_execution_refactor/e10_9_training_results.md
?? malaria_dl_local_project/src/malaria_dl/evaluation/binary_counts.py
?? malaria_dl_local_project/src/malaria_dl/evaluation/validation.py
?? malaria_dl_local_project/src/malaria_dl/results/training.py
?? malaria_dl_local_project/tests/test_training_results.py
?? malaria_dl_local_project/tests/test_training_results_docker.py
?? malaria_dl_local_project/tests/test_training_results_postgres.py
```

Resumen del diff: 10 archivos productivos (7 modificados + 3 nuevos), 17 de pruebas
(14 modificados + 3 nuevos) y 1 documento nuevo. El cambio productivo agrega
contrato/evaluador, emisión antes de completed, proyección atómica y reader compatible.
No elimina componentes legacy.
