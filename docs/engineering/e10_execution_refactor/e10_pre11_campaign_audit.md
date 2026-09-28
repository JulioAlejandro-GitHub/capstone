# E10.PRE11 — Auditoría integral de campañas

Fecha: 2026-09-28. Checkout: `2798d1d0dfff8974550d3de6b5cde3f08e49ada1`.
Campaña: `3acf89b7-dc42-4b7a-8e2a-ca6ea024c344`.

## 1. Alcance, método y conclusión principal

Auditoría exclusivamente estática y mediante SELECT autorizados. No se ejecutó
TRAIN, TEST, pytest, preflight operativo, resume, claim, verificación Keras,
migración ni corrección. No se modificó código productivo. El único entregable
versionable es este documento; los snapshots de trabajo se guardaron en /tmp.
No se invocaron servicios de inspección que también escriben auditoría, como
verify_dataset_for_execution, ni el CLI science compare, que persiste informes.

La campaña define inequívocamente 36 miembros y los siete runs existentes conservan
su configuración científica coherente. Docker y Local llaman al mismo TRAIN.
**Esto no significa que la campaña operativa haya ejecutado E10.10:** PostgreSQL
operativo está en `20260915_01`, sin columnas E10; sus siete runs son legacy.
Sólo un miembro está verified, y no existen evaluaciones E6 de estos runs para
alimentar directamente los consumidores actuales E7/E8.

Se distinguen tres evidencias: código actual del checkout; filas operativas
observadas; pruebas históricas documentadas en E10.0–E10.10. Las 746 pruebas de
E10.10 son antecedentes, no pruebas ejecutadas nuevamente ni acreditación del
schema operativo. La vigencia física de checkpoints/dataset no se comprobó aquí.

Convenciones: `S/` = malaria_dl_local_project/src/malaria_dl/;
`M/` = malaria_dl_local_project/; `B/` = backend_api/; `A/` = alembic/versions/.
Las referencias indican archivos y funciones, evitando depender de números de
línea históricos. Las consultas reproducibles están en §11.

## 2. Referencias E10 contrastadas con el código actual

| Referencia de este directorio | Qué conserva / qué dejó de describir el presente |
|---|---|
| baseline.md (E10.0) | Matriz, configuración, records, diferencias operativas y límites de entorno siguen aplicando. Su ausencia de salida en runs.parameters ya no describe TRAIN E10 actual. |
| e10_1_contracts.md | ExecutionContext/RunEvent/RunReporter; modo identifica transporte, no cambia ciencia. |
| e10_2_result_service.md | Idempotencia/fencing/secuencia. El payload de evaluación ya no es opaco: E10.9 lo valida. |
| e10_3_postgres_result_repository.md | Envelope canónico y migración 20260922_01. Pruebas en schemas temporales no implicaron upgrade de public. |
| e10_4_docker_reporter.md | Delegación al servicio; integración y separación de hash llegaron después. |
| e10_5_http_reporter.md | Identidad Local autoritativa en backend, JWT/job/agent y revalidación transaccional. |
| e10_6_event_emitter_records_hash.md | Records legacy y eventos son familias distintas; hash legacy excluye E10. |
| e10_7_docker_train_integration.md | Doble escritura y referencias legacy. Su ausencia de evaluación final fue superada por E10.9. |
| e10_8_local_train_journal.md | Journal operacional, pending/ACK, mismo TRAIN. Local dejó de ser legacy en el camino actual con emitter. |
| e10_9_training_results.md | Evaluación final y proyección científica ON/OFF; no pretende sustituir evaluaciones E6. |
| e10_10_completion_verification.md | Cierre científico y verificación común, clasificación histórica, sin backfill. |

En particular, el docstring actual de train todavía dice que sin emitter se conserva
«Local/standalone legacy». El worker Local actual sí compone emitter; esa frase no
es evidencia de que hoy omita E10. No se corrigió documentación/código anterior.

## 3. Contrato experimental y congelación

### 3.1 Construcción de la matriz

`S/campaigns/contracts.py::expand_matrix` valida exactamente models, optimizers,
seeds, variants y exclusions. models=None usa enabled_models; si se especifican,
resolve_descriptor normaliza aliases y exige enabled/trainable. Se ordenan y
eliminan duplicados de modelos, optimizadores y semillas; variantes se ordenan por
nombre y sus nombres deben ser únicos. El registry actual habilita custom_cnn,
vgg16 (alias vgg16_transfer_learning) y densenet121; los tres admiten adam, adamw,
sgd y adadelta (`S/models/registry.py`, `optimizers.py`). La tabla models aporta
UUID relacional; no es el mecanismo de discovery de la matriz.

Cada combinación modelo × optimizador × variante se resuelve con
`resolve_config(..., batch=True)`. Precedencia efectiva: defaults versionados y
perfil batch → variant.selected → variant.by_model y optimizador de matriz →
política del protocolo al congelar. Conflictos explícitos con la política se
rechazan, no se silencian. No se permite seed dentro de las variantes.

Exclusión identifica (model,optimizer,variant) y exige razón; afecta todas sus
semillas. El miembro se conserva con state=excluded y cuenta en expected_count.
Una exclusión sin correspondencia se rechaza. Variantes que producen el mismo
hash+seed se rechazan como duplicación experimental. max_members incluye excluidos;
se rechaza una matriz completamente excluida.

`scientific_configuration` conserva schema/model/adapter/resolved y retira seed.
`configuration_hash = SHA256(canonical(configuration))`; canonical ordena claves,
normaliza float integral a int y conserva orden de listas. No equivale a hashear
el JSON solicitado ni al config_digest de otro módulo. Las semillas identifican
miembros distintos bajo una misma configuración científica.

### 3.2 Freeze e identidad relacional

`S/campaigns/service.py::freeze` vuelve a comprobar dataset y entorno de planificación.
Congela protocolo, matriz, registry, configuración resuelta, solicitudes/provenance,
dataset/fingerprints, entorno y referencia de acreditación. `CampaignRepository.freeze`
inserta configuraciones/miembros y contrato canónico/hash en una transacción.
`get` vuelve a validar contrato, hashes y concordancia con las tablas materializadas.
No re-resuelve una campaña congelada desde los defaults actuales.

Cadena de identidad:

```text
experimental_campaigns.id + contract_hash
  → campaign_configurations.(campaign_id, configuration_hash)
  → campaign_members.(id, configuration_hash, seed, position)
  → campaign_attempts.(id, member_id, ordinal, training_run_id)
  → runs.id ↔ train_execution_sessions.(run_id, attempt_id)
```

Cada nuevo intento crea un run distinto. `member_configuration` copia el snapshot
y añade la semilla del miembro. `_create_run` exige un único models.id para el nombre
canónico e inserta configuration/dataset/environment en
`runs.execution_parameters.model_configuration_e2`, además de random_seed y
referencia de evidencia del dataset. `runs.parameters` es otra columna: salida.

### 3.3 Reintentos, estados y guardas

`ExecutionRepository.claim`: campaña frozen/active; miembros pending, failed o
interrupted bajo presupuesto; prioridad pending, luego posición. Ordinal creciente;
failed/interrupted no se borran. `ControlledRepository.reserve` admite un intento
explícito de campaña paused con revisión registrada, intento previo fallido y
presupuesto. No reanuda la cola. Resume/reconcile conserva historia y no reinicia
TensorFlow dentro de un run consumido.

Estados de sesión/intento: active→completed→verified, o active→failed/interrupted.
Un completed no se transforma en failed. `campaign_attempt_state` actualiza el
miembro y fija accepted_attempt_id al primer verified; no selecciona el mejor de
varios intentos. Verified técnico no equivale a objetivo clínico ni a release.

PostgreSQL operativo tiene habilitados campaign_guard, campaign_configuration_guard,
campaign_member_guard, campaign_attempt_guard, campaign_run_identity_guard,
train_session_guard y train_record_guard. Sus definiciones se consultaron con
pg_get_functiondef. Impiden cambiar configuración congelada, identidad/seed/run,
snapshot de sesión e historia append-only; al vincular intento contrastan el
resolved sin seed y la semilla del miembro. Revisiones técnicas permiten un entorno
diferente autorizado, no una configuración científica diferente. No se probó ninguna
mutación: la evidencia es la definición instalada y los datos leídos.

## 4. Configuración que llega realmente al modelo

Origen estable: campaign_configurations.configuration.resolved, más seed de
campaign_members. Destinos: snapshot de run/sesión, modelo compilado, dataset
prebatcheado y argumentos de fit. `train` no vuelve a invocar resolve_config.

| Elemento | Origen | Destino real y evidencia |
|---|---|---|
| Arquitectura | configuration.model_id / adapter_version, resolved.model | registry→adapter.build→architectures.build_*; runtime.architecture=model.get_config() |
| Optimizador | resolved.optimizer.name/parameters | compile_phase→compile_binary_model→build_optimizer→model.compile; runtime.optimizer/class y compile |
| Learning rate | optimizer.parameters.learning_rate; fine_tune_learning_rate | Factory float para JSONB integral; nueva instancia por fase; ReduceLROnPlateau modifica LR durante fit; epoch.learning_rate registra valor observado al persistir |
| Semilla | members.seed→resolved.execution.seed | tf.keras.utils.set_random_seed y seed del loader TRAIN; runs.random_seed |
| Batch size | execution.batch_size | image_dataset_from_directory(batch_size=...), antes de fit; no argumento batch_size redundante en fit |
| Épocas | max_epochs y fine_tune_epochs | phases; model.fit(epochs=epochs), con contadores por fase y offset global; EarlyStopping puede reducirlas |
| Dropout/L2 | model.dropout/l2 | adapters pasan parámetros a builders; custom CNN aplica L2 a conv/dense. Transfer no admite L2 distinto de cero. head_units/BN son knobs fijos validados, no valores ignorados libremente |
| Fine-tuning | model.fine_tune_layers, execution.fine_tune_epochs | set_phase congela backbone en base y habilita últimas N capas en fine_tuning; recompila con optimizador nuevo y LR de fase |
| EarlyStopping | execution.* y resolved.selection | Callback clínico transforma monitor/mode a val_early_stopping_score; Keras recibe monitor=ese score, mode=max, patience/min_delta/restore configurados |
| Checkpoint monitor | execution.checkpoint_*→selection | Monitor explícito usa select_best_epoch_by_monitor; si no, política. PersistEpoch guarda cada epoch y selecciona sobre historia acumulada |
| Preprocesamiento | model.preprocessing/input_contract | loader físico: custom rescale_0_1; VGG vgg16_imagenet; DenseNet rescale externo y normalización interna mean/std, backbone training=False |
| Augmentation | execution.no_augment y recipe fija validada | build_augmentation usa flip/rotation/translation/zoom/contrast fijos coincidentes con receta; cambios de recipe se rechazan. Sólo TRAIN; orden distinto para VGG |
| Calibración | execution.calibrate_threshold, target_recall/min_specificity/beta | selected checkpoint recargado→scores VAL→threshold helper si ON; OFF usa marcador disabled y threshold 0.5 |
| Dataset version | campaña/snapshot→run.dataset_version_id y session.dataset | Sólo directorios train/val; preflight y manifest Local vinculan materialización/fingerprints |

La llamada concreta en `S/execution/train.py::train` es:

```python
model.fit(datasets['train'], validation_data=datasets['val'],
          epochs=epochs, callbacks=callbacks)
```

No basta comparar nombres: optimizer se construye y compile_phase contrasta
get_config con opciones solicitadas (tolerancia 1e-6 relativa/1e-12 absoluta).
Input/output se comprueban contra el modelo construido; runtime persiste arquitectura,
compile, capas entrenables y contratos. Recipe de loss/metrics es fija: binary cross
entropy y métricas de compile_binary_model, no strings interpretados libremente.

**Matiz científico vigente:** monitor explícito val_f2_parasitized prevalece sobre
el nombre auc_with_min_recall. Su selección no impone el recall mínimo; el resultado
puede llevar policy_satisfied=true por el default de _selection_result y, a la vez,
clinical_objective_met=false. Esto ocurre en la campaña observada. EarlyStopping
usa score normalizado y penalización por colapso; no es una comparación directa
sin transformación del F2 nominal. El criterio E7 es sensibilidad estrictamente
>0.98; completion usa >=min_recall a threshold de selección, incluso si luego se
calibra. No intercambiar estos indicadores.

## 5. Docker y Local: mismo contrato, garantías distintas

**Docker:** campaign.execute_campaign→claim→run_child→worker.main. El hijo recibe
IDs/owner, vuelve a leer sesión, usa effective_row para revisión técnica, compara
configuración esperada y dataset/entorno, y ejecuta preflight. Compone
DockerRunReporter→ResultService→PostgresResultRepository y llama train común.
El terminal E10 precede al finish(completed). Padre espera salida, verifica checkpoint
y llama finish(verified); GlobalGate retiene propiedad durante cálculo/verificación.

**Local:** agent→HTTP claim→LocalBackend.prepare/claim→reserve o claim común. Backend
construye la sesión; sustituye sólo owner público y referencias de roots. Agente y
worker comprueban manifest TRAIN/VAL, resuelven paths y llaman al mismo train con
Reports + emitter/HttpRunReporter + journal. Backend resuelve contexto E10 desde DB,
no acepta del Mac una nueva configuración congelada. calculation-ended sólo almacena
completion del job. Tras exit proof, backend realiza completed→verify→verified y
release dentro de una transacción exterior. Los bytes del checkpoint se comparten
por filesystem; HTTP transmite referencias y evidencia, no el archivo.

Exclusividad: advisory lock global (120994,1), singleton experiment_execution_gate,
token/fencing y guards de sesiones/intentos. Docker retiene lock de conexión y
pruebas de procesos; Local usa lock transaccional en claim y job retenido. Heartbeat
15 s/uncertain 60 s no libera por expiración. Identidad job/agent/run/attempt es
explícita; PID sin instante/host no basta. Journal recupera transporte, no fit.

**Límites que deben conservarse visibles:**

- Las filas congeladas no son modificables por el flujo autorizado. Esto no prueba
  que un proceso remoto arbitrario ejecute exactamente lo declarado: agent/worker
  Local no miden automáticamente su source hash, Python ni paquetes antes de fit.
  prepare compara environment recibido con revisión y preflight mide source del
  backend. Registry Local tampoco repite todo el contraste de descriptor Docker.
- `storage.verify_samples` comprueba cada archivo enumerado, pero no rechaza archivos
  extra en los directorios Local. train carga el directorio completo. Por inspección,
  un extra en TRAIN podría consumirse sin estar en manifest; uno en VAL también
  afectaría el count y el cierre E10 debería rechazarlo. No se fabricó ese escenario.
- El entorno persistido no incluye scikit-learn, aunque interviene en métricas; no
  es un lock exhaustivo de dependencias. E7 agrupa/selecciona por environment_hash;
  mezclar revisiones/plataformas puede excluir una comparación, incluso compartiendo
  configuración. Diferencia operacional no equivale a igualdad numérica.
- No se ejecutó experimento Linux/macOS aquí y no se afirma equivalencia numérica.
  La prueba de salida Local cubre descendientes observados, no hijos escapados.
- Local sequential no llama finalize_terminal al agotar la cola; NO_ELIGIBLE_MEMBER
  no equivale a la finalización normal del coordinador Docker.

## 6. Inventario completo de salida TRAIN y persistencia

A = resultado íntegro en PostgreSQL para el objeto indicado; B = evidencia/referencia
estructurada en PostgreSQL; C = bytes externos con referencia/hash; D = calculado
pero no persistido como tal. «Recuperable» no significa expuesto por toda API ni ya
existente en una ejecución fallida o anterior a E10.9.

| Resultado | Se calcula | Destino BD / campo | Clase y recuperación |
|---|---|---|---|
| Loss por época | Sí, TRAIN y VAL de Keras | records kind=epoch, payload.loss/val_loss; EPOCH_COMPLETED copia row | A; por fase/epoch. No loss final del checkpoint recargado |
| Métricas por época | Sí, Keras + callback clínico | epoch.payload: accuracy, precision, recall, specificity, balanced_accuracy, auc/pr_auc y val_*; selection.selected_record | A para logs emitidos; no todo el objeto clínico calculado |
| Runtime de cada fase | Sí, introspección del modelo | runtime/configuration: optimizer, compile, architecture, loss, layers, input/output, callbacks | A para introspección guardada; PHASE_STARTED sólo B por referencia |
| Learning rate efectivo | Sí | epoch.learning_rate, runtime.optimizer inicial | A en esas fronteras; no historial por batch ni todas las iteraciones |
| Checkpoints por época y seleccionado | Sí, archivos .keras | artifact_prepared; artifact.path/version_id/SHA/bytes/epoch; selection y verification.artifact | B+C. Pesos/estado serializado fuera de PostgreSQL |
| Predicciones VAL por época | Sí | predictions.payload.samples[{sample,label,score}], role, epoch | A. PREDICTIONS_COMPLETED sólo referencia legacy/role/epoch |
| Predicciones finales del seleccionado | Sí, tras recarga | calibration/val/selected.payload.samples y checkpoint_epoch, ON y OFF | A. No incluidas como arrays en TrainingResults ni evento calibration |
| Calibración | ON sí; OFF marcador | calibration.payload.result: threshold, objetivo, selected/default metrics, candidate_count, warnings, versión | A para resumen devuelto; D para grid completo de métricas de candidatos |
| Confusion matrix final / TP TN FP FN | Sí en E10 ON/OFF | EVALUATION_COMPLETED payload.confusion_matrix; runs.parameters.training_results.validation.confusion_matrix | A. Legacy OFF no la persiste explícitamente |
| Recall final | Sí | training_results.validation.metrics.recall y evento | A; threshold/split vinculados |
| Specificity final | Sí | metrics.specificity | A |
| Precision final | Sí | metrics.precision | A |
| F1 final | Sí | metrics.f1 | A |
| F2 final | Sí | metrics.f2 | A |
| Balanced accuracy final | Sí | metrics.balanced_accuracy | A |
| ROC-AUC final | Sí si ambas clases | metrics.roc_auc; null si no estimable según contrato | A; calculado desde scores, no desde matriz |
| PR-AUC final | Sí si ambas clases | metrics.pr_auc | A; semántica average_precision, distinta del AUC PR aproximado de Keras |
| Selección por época | Sí | selection.payload íntegro: selected_record/metrics/epoch, collapse, warning, policy | A+B; no sustituye objetivo clínico |
| Fase / EarlyStopping | Sí | phase/completed.payload.epochs y early_stopping stopped_epoch/best_epoch | A para resumen; no serializa estado completo del callback |
| Eventos E10 | Sí con emitter | records kind=e10_event, event_id/event_sequence y payload.canonical_event | A envelope; payloads referenciales no contienen toda la evidencia legacy |
| Completion | Sí al terminar | sessions.completion, y job.completion Local | B: epochs, selection, clinical flag, records_hash y sello E10 |
| Verification | Sí por backend/coordinador | sessions.verification | B: status/hash/selected artifact/selection y hash de contrato E10 |
| Classification report completo / métricas por clase | Sí en compute_clinical_metrics | No se copia classification_report(_dict) a logs ni V1 | D; recalculable desde labels/scores, no texto original recuperable por SELECT |
| Matriz/F1 clínicos por época | Sí en callback | No proyectados como tales a logs; labels/scores de otra recolección se guardan | D como objeto del callback; reconstrucción posterior posible bajo su semántica, no evidencia de igualdad de ambas inferencias |
| Accuracy/distribución/FPR/FNR finales y alias del helper | Sí al evaluar E10 | V1 conserva sólo matriz + ocho métricas; algunos subconjuntos en calibración ON | D para campos omitidos; derivables, no nuevas salidas almacenadas |
| Batch logs, activaciones/gradientes, estado RNG/callback | Cómputo interno de fit | Sin ledger BD de estos valores | D como traza; checkpoints no acreditan resume científico completo |
| Failure y coordinación | Según punto de fallo | session/attempt.cause, campaign/global events; TRAINING_FAILED sólo si emisor autorizado y sin pending | B; terminal failed puede faltar tras crash/entrega fallida |

Fuentes: `S/execution/train.py::put/PersistEpoch/train`, `models/adapters.py::compile_phase`,
`training/checkpoint_policy.py::ClinicalValidationMetricsCallback.on_epoch_end`,
`evaluation/clinical_metrics.py::compute_clinical_metrics`,
`evaluation/threshold_calibration.py::find_threshold_for_target_recall`,
`evaluation/validation.py`, `results/training.py`, `results/service.py`,
`persistence/result_repository.py::_PostgresScope`.

El helper de calibración evalúa todos los candidatos en memoria, pero retorna sólo
selected/default metrics y candidate_count. No hay un grid completo oculto en BD.
TRAIN no escribe CSV/JSON científicos laterales ni las tablas legacy training_history,
run_metrics, run_clinical_metrics o confusion_matrices. No confundir esos writers
alternativos de persistence/run_repository.py con el recorrido de campañas.
`clean` transforma no finitos legacy a null; la evaluación V1 rechaza no finitos.

## 7. Validación E10 actual y compatibilidad

Para completed E10, `ExecutionRepository.finish` adquiere locks, carga fuentes
actuales y llama `TrainingCompletionValidator`. Exige stream contiguo, un
EVALUATION_COMPLETED válido, TrainingResultsV1 deserializable, proyección igual,
población/dataset/configuración coherentes, un TRAINING_COMPLETED posterior y
terminal, sin TRAINING_FAILED contradictorio, hash legacy y checkpoint único
vinculado a selección/muestras finales. Persiste training_completion_v1 junto al
completion anterior en la misma transacción que estados de sesión/intento/run.

`verify_session` revalida sello contra fuentes actuales y conserva controles de
records/fases/selección, archivo/hash/bytes, confinamiento y loader. finish(verified)
revalida otra vez bajo locks, contrasta proof y checkpoint físico. Un evento terminal
solo no implica sesión verified, fin del proceso, release ni despliegue.

ON exige calibración y evento coherentes con threshold; OFF exige default y genera
igualmente matriz/ocho métricas finales, sin CALIBRATION_COMPLETED. OFF conserva
calibration/val/selected con muestras; el validador depende de esa evidencia.

Clasificación: eventos con event_id no NULL; sello previo impide downgrade si se
elimina ilegalmente el stream. Reader premigración usa to_jsonb(record)->>'event_id',
por lo que ausencia de columna significa legacy. Sin eventos/sello, se conserva la
verificación histórica; standalone sin emitter sigue allí. No hay backfill.
La coherencia estructural no atestigua criptográficamente que la red generó los scores.

En public NO se observaron runs E10 de esta campaña: no existe schema de eventos.
Esto no invalida retroactivamente su verified legacy, ni permite atribuirle sello,
matriz final V1 o las nuevas verificaciones. No se ejecutó verify_session sobre
artefactos operativos; sólo se comprobó el digest de sus registros exportados.

## 8. Recuperación experimental E7/E8/E9

Puede recuperarse por SELECT la configuración, historia disponible, muestras,
selección, referencias físicas y estados, siguiendo campaña→miembro→intento→run.
`ExecutionRepository.records/legacy_records/result_events` separan familias;
`CampaignRepository.get` recupera la matriz completa, incluidos faltantes.
`training_summaries._summary_row` usa V1 cuando existe y expone sólo un subconjunto;
no convierte resultados inválidos en válidos por status. Legacy OFF puede mostrar
métricas seleccionadas sin matriz. El inventario completo requiere readers/SQL,
no exclusivamente el resumen de UI.

**TRAIN V1 no es un reemplazo de E6 para E7/E8.**
`science/comparison.py::read_evaluation` exige assessment_attempt verified, identidad,
model binding, muestras con sample_id/patient_id, decision/protocol y results E6.
Revalida lineage y checkpoint físico. `compare/select_candidate` exige matriz
original completa, semillas compartidas, población y entorno compatibles; reporta
faltantes y rechaza referencias ambiguas. `science/ensemble.py::align/prepare/evaluate`
consume estas mismas evaluaciones, scores por muestra y alineación de identidad.
Los informes E7/E8 se persisten mediante ScienceRepository/ensemble_repository
en audit_events; exports gráficos/tabulares son derivados externos.

TRAIN conserva paths relativos/labels/scores, pero no patient_id/sample_id de E6 en
cada fila. La identidad clínica procede del dataset gobernado y del mapping de
`assessment/lineage.py::dataset_samples`. No basta entregar una matriz agregada a
bootstrap por paciente, curvas, comparación pareada o ensemble. Tampoco hay una
conversión automática de TrainingResultsV1 a assessment_results.

En la campaña auditada hay **cero assessment_identities vinculadas a sus siete runs**.
No puede producirse hoy la comparación completa ni selección E7 de 36 miembros.
Eso es ausencia de ejecuciones/evaluaciones requeridas, no pérdida de resultados
E6 que se haya demostrado. No se ejecutaron esas etapas en esta auditoría.
Con calibración OFF, threshold='clinical' de E6 se rechaza por ausencia de calibración;
se necesita una decisión numérica explícita autorizada por su protocolo, no inventar
calibración histórica. El protocolo E7 de esta campaña pospone selección de threshold.

## 9. Campaña operativa observada

Snapshot principal: **2026-09-28 15:49:44.809166 UTC**, base malaria_experiments,
transaction_read_only=on, aislamiento repeatable read. Consultas complementarias
posteriores también READ ONLY. No es certificación de ausencia de cambios futuros.

- Nombre: E9 capstone_science_e7_v1 2026-09-14 corrección numérica.
- Estado paused; freeze 2026-09-14 11:46:48.763897 UTC; expected_count=36.
- Contract hash: `02a63b0c76dc600bcb17c7163699abf7dd4e5579643b6adbc783f50d30fcf1ba`.
- Dataset `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`; materialización
  `e15dc166-1c4b-558e-b77b-727b1783430c`; counts TRAIN=22180, VAL=2693, TEST=2685.
- Una variante capstone_science_e7_v1; semillas 11/29/47; exclusiones=[];
  12 configuraciones × 3 semillas; presupuesto 3 intentos/miembro.
- Miembros: pending=31, active=0, failed=4, interrupted=0, completed=0,
  verified=1, excluded=0. Intentos: failed=6, verified=1; siete runs/sesiones.
- 359 records legacy: 70 epoch, 70 artifact_prepared, 70 artifact, 70 selection,
  70 predictions, 7 runtime, 1 phase, 1 calibration. No eventos E10.
- Alembic instalado: **20260915_01**. Checkout contiene sucesora
  **20260922_01_result_events**, no instalada en public. Se confirmó ausencia de
  event_id/event_sequence y de a_train_event_guard, no sólo el texto de alembic_version.

El próximo candidato por orden estático sería posición 5 (pending, custom_cnn/adam/47).
Esto no declara readiness ni solicita ejecutarlo: campaña paused, esquema E10 ausente
y revisión de código/entorno requieren su propio procedimiento autorizado.

### 9.1 Valores científicos efectivos comunes

Todos: input 200×200×3; batch 64; base hasta 50 epochs; augment ON; determinism ON;
loss binary_crossentropy; selección F2 explícita max a 0.5; early stopping ON,
patience 12, min_delta 0.0001, restore_best_weights=true; ReduceLR monitor val_loss,
factor 0.5, patience 4, min_lr 1e-6; calibración OFF; target/min recall .98,
min_specificity 0; reject_prediction_collapse=true, min_class_fraction .05;
evaluate_best_on_test=false.

| Modelo | Arquitectura resuelta / preprocessing | Fine-tuning |
|---|---|---|
| custom_cnn | conv 32/64/128/256 + GAP + Dense128, dropout .4, L2 .0001, BN train, weights none, rescale_0_1 | 0 epochs / 0 capas |
| densenet121 | ImageNet, GAP→dropout .5→sigmoid, L2 0, BN inference, rescale_0_1 + normalización interna | hasta 20 epochs / últimas 4 capas |
| vgg16 | ImageNet, GAP→Dense1024→dropout .5→sigmoid, L2 0, BN absent, vgg16_imagenet | hasta 20 epochs / últimas 4 capas |

Optimizadores completos se recuperan del JSON congelado: Adam beta1=.9/beta2=.999,
epsilon=1e-7/amsgrad=false; AdamW igual con weight_decay=.004; SGD momentum=.9,
nesterov=false; Adadelta rho=.95/epsilon=1e-7. EMA/clipping/acumulación mantienen
los defaults explícitos del snapshot. La tabla siguiente liga los 12 hashes y LR.

| Modelo | Optimizador | LR base / fine-tuning | configuration_hash |
|---|---|---|---|
| custom_cnn | adadelta | 1 / 1 | `9caaac5ec278e315c7af400729920b93e348af752ae24eedff40cb72893bb2b0` |
| custom_cnn | adam | 0.0001 / 1e-05 | `8186ad70d6d0426cbdeca79ed2f2ba440c7a1bae77fe80381b9d1cc4037a51df` |
| custom_cnn | adamw | 0.0001 / 1e-05 | `ee248704e9bcd7fe011c5cdba0cf46044e68480740f06fbb70f49ac2add6947f` |
| custom_cnn | sgd | 0.001 / 0.0001 | `f9341377ddd1dc334f6a307e131c9df3784d7a621b9a24a11d61770b27a8aa8e` |
| densenet121 | adadelta | 1 / 1 | `dd022b0b646fb88d6271c31e685bfabf3dfac41464140255c64f9460edb0c3c3` |
| densenet121 | adam | 0.0001 / 1e-05 | `eec0b6c18a17904eb089f761850805fdf8a70fb723f995cd5c572c2feb6fd8eb` |
| densenet121 | adamw | 0.0001 / 1e-05 | `f40beedcd9496e20b13bdcb2669e188bced8d57e974c15e2afd2911aea4a4d34` |
| densenet121 | sgd | 0.001 / 0.0001 | `f52eb6b3ad40b1f571e02cfa4adf6874aae67560d26430ce0f23bc7c3d815219` |
| vgg16 | adadelta | 1 / 1 | `7d982b2ee53e8868955660c20fcc942ecf80201f6e5b608b215b4ee55575103b` |
| vgg16 | adam | 0.0001 / 1e-05 | `7c4b969b0b2a45c6b5fa71e2901ac5347cc4d5a44b43c222dd29efc7f6ac5a1c` |
| vgg16 | adamw | 0.0001 / 1e-05 | `a74f108be74b2c151678f9801782489099f51cf7445b9f1c7ae5ea16b6a370f9` |
| vgg16 | sgd | 0.001 / 0.0001 | `cbb96f7ac059cf71953c87d7234471394afa829ee0c5289adfee6a77f6e20d87` |

### 9.2 Miembros completos (posición base cero)

| Pos. | Member ID | Modelo / optimizador / seed | Estado | Intentos |
|---|---|---|---|---|
| 0 | `2fbd5862-b68b-4845-9445-a30d7ec61382` | custom_cnn / adadelta / 11 | verified | 3 |
| 1 | `48f036da-ad4e-47e1-af82-c1624ee042d6` | custom_cnn / adadelta / 29 | failed | 1 |
| 2 | `ae6cc2bb-c48d-4c76-b9c5-90502afac7fe` | custom_cnn / adadelta / 47 | failed | 1 |
| 3 | `effa8851-52ce-419f-8c72-59aa8ac739f4` | custom_cnn / adam / 11 | failed | 1 |
| 4 | `6be69e51-c956-4a2a-97b8-0293e4780dbe` | custom_cnn / adam / 29 | failed | 1 |
| 5 | `e1ceb448-195a-4b80-9c96-a4e67734e16a` | custom_cnn / adam / 47 | pending | 0 |
| 6 | `da652973-fb5c-4cfe-92a7-393c92010bff` | custom_cnn / adamw / 11 | pending | 0 |
| 7 | `481c1b88-83d2-40c0-9209-c10c226d36f4` | custom_cnn / adamw / 29 | pending | 0 |
| 8 | `46bcb7fa-ee2f-457f-95fa-3d71c5d1de92` | custom_cnn / adamw / 47 | pending | 0 |
| 9 | `332d0f6d-cd5c-46a4-be01-e1b9aab6c116` | custom_cnn / sgd / 11 | pending | 0 |
| 10 | `2adccda7-a9ee-40f7-8704-67a202e0a80c` | custom_cnn / sgd / 29 | pending | 0 |
| 11 | `111f7197-e4f7-49bb-a5da-58cd1461cbd2` | custom_cnn / sgd / 47 | pending | 0 |
| 12 | `555d58d4-4821-4cb6-b43a-1d9f66e36c6c` | densenet121 / adadelta / 11 | pending | 0 |
| 13 | `3898b92d-f3d7-4863-93b2-4fb054c542b7` | densenet121 / adadelta / 29 | pending | 0 |
| 14 | `305c153b-821d-4c31-a6aa-cc4c0bd1ec94` | densenet121 / adadelta / 47 | pending | 0 |
| 15 | `cfe368f3-3adc-4def-b893-0ac23cfd4c82` | densenet121 / adam / 11 | pending | 0 |
| 16 | `b0ffb6fe-53e2-4420-9759-870eb8e2fa77` | densenet121 / adam / 29 | pending | 0 |
| 17 | `1587e852-dff5-4c64-a6e2-c57f86457d33` | densenet121 / adam / 47 | pending | 0 |
| 18 | `0cd9cfc3-d5f4-44aa-9036-b9f7c549fba6` | densenet121 / adamw / 11 | pending | 0 |
| 19 | `6ef48d0e-40df-496b-a19b-da45ea19a7f4` | densenet121 / adamw / 29 | pending | 0 |
| 20 | `a591fbc3-bd32-421b-bb2f-b3dc5217e99c` | densenet121 / adamw / 47 | pending | 0 |
| 21 | `1799d954-1042-4096-8208-c18e6ba5f06c` | densenet121 / sgd / 11 | pending | 0 |
| 22 | `ac84826f-0d5b-48f3-a511-192ac4e1da50` | densenet121 / sgd / 29 | pending | 0 |
| 23 | `1477c7f5-884d-45ad-8ac5-ca694125eb41` | densenet121 / sgd / 47 | pending | 0 |
| 24 | `cda79eea-7313-44b9-9a20-07188f6cf603` | vgg16 / adadelta / 11 | pending | 0 |
| 25 | `33921d5b-53f5-4899-8246-0efae7573f82` | vgg16 / adadelta / 29 | pending | 0 |
| 26 | `e6d0d9a6-96cc-43bd-a0fe-c50a285febc6` | vgg16 / adadelta / 47 | pending | 0 |
| 27 | `2e5bada2-a3df-41ef-ad0f-724f22ae2f38` | vgg16 / adam / 11 | pending | 0 |
| 28 | `af6c53e1-fd81-4b6e-bc33-a218f3419b46` | vgg16 / adam / 29 | pending | 0 |
| 29 | `c4741856-79f8-414a-9262-f632ef578b73` | vgg16 / adam / 47 | pending | 0 |
| 30 | `3021aa82-713d-4c67-a37a-f127623e6c4f` | vgg16 / adamw / 11 | pending | 0 |
| 31 | `eb8ba6dc-00bf-4f4d-8b9c-9d1665019ccc` | vgg16 / adamw / 29 | pending | 0 |
| 32 | `3ce3b53d-6f24-4976-9c75-09674d581325` | vgg16 / adamw / 47 | pending | 0 |
| 33 | `4905eb35-085c-4fbc-870d-f23b149e167d` | vgg16 / sgd / 11 | pending | 0 |
| 34 | `9bf0572c-ff6c-42f7-9cad-88de4339c65d` | vgg16 / sgd / 29 | pending | 0 |
| 35 | `229d6d38-1ce5-406f-b99c-46dc1d9e6ae8` | vgg16 / sgd / 47 | pending | 0 |

### 9.3 Intentos, runs y evidencia

| Pos. / ordinal | Attempt ID | Run ID | Estado | Epochs persistidos | Causa |
|---|---|---|---|---|---|
| 0 / 1 | `8279db36-7bfe-4e22-8bf3-872ac215eae2` | `a5f36df1-3341-43fd-94b9-ee1cedb834c5` | failed | 4 | CHILD_EXIT_OR_INCOMPLETE_RESULTS |
| 0 / 2 | `4cd0cf3f-37df-4490-9f26-eb2763f3b4e6` | `79f39931-ac71-4bc1-a317-149a975d1f74` | failed | 5 | CONTROLLED_CHILD_EXIT_-9 |
| 0 / 3 | `c0a559fa-b2d8-4c0c-9175-78c91e2b3057` | `d1a1413b-760c-43a2-89ee-7913e780e87a` | verified | 27 | — |
| 1 / 1 | `e2d9e27d-ab91-4b60-be33-3cb77ef18a33` | `8ebbd308-2cec-4275-93b7-ad56fa9e6931` | failed | 6 | CHILD_EXIT_OR_INCOMPLETE_RESULTS |
| 2 / 1 | `78fd6177-12d5-4246-a803-1f216f2d5fb6` | `3894deef-252f-424e-a4ad-d6cd555e063e` | failed | 7 | CHILD_EXIT_OR_INCOMPLETE_RESULTS |
| 3 / 1 | `ecb39496-fd59-48a1-af1a-36dde09a1e62` | `61bf6d6d-9db9-498e-a9ee-c26e94e46f2d` | failed | 9 | CHILD_EXIT_OR_INCOMPLETE_RESULTS |
| 4 / 1 | `0b7c53f9-ac99-4308-a90c-b947f601ef6a` | `ec0975b2-b355-4d5c-a4ec-beac31da72dd` | failed | 12 | CHILD_EXIT_OR_INCOMPLETE_RESULTS |

Todos los runs son custom_cnn. La configuración nominal coincide **7/7** entre
configuración congelada+seed, session.configuration y
runs.execution_parameters.model_configuration_e2.configuration. Dataset y entorno
coinciden entre run/sesión **7/7**; random_seed coincide con miembro **7/7**.
Los 12 configuration_hash y el contract_hash se recalcularon con canonical/digest
aprobados sobre el snapshot SELECT: coincidencia; canonical text también coincide.
Los 36 miembros materializados coinciden con los miembros del contrato congelado.

Además del JSON nominal, se contrastó evidencia real: **7/7 runtime.optimizer**
coinciden con las opciones solicitadas con tolerancia 1e-6/1e-12; input_contract
coincide 7/7. runtime.architecture registra las conv 32/64/128/256, Dense128,
L2 .0001, dropout .4 y salida sigmoid esperadas. Adam registra LR
0.00009999999747378752 frente al nominal .0001 (representación float32);
Adadelta registra 1. No se califica esa diferencia como cambio de hiperparámetro.
La reducción posterior de LR queda en epoch.learning_rate; no cambia el snapshot
inicial. No hay runtime de vgg16/densenet121 ni fase fine_tuning en estos siete runs.
No se atribuye evidencia experimental a los modelos todavía pendientes.

No existe un registro literal de todos los kwargs efectivos de fit ni una medición
por batch. Batch/epochs/seed se acreditan por snapshots + código invocado, no por
una traza independiente de fit. Las epochs realizadas sí tienen evidencia durable.

En los siete runs, parameters={}, configuration=NULL, completed_epochs=0 y
best_epoch/checkpoint_monitor/platform/host_name de runs son NULL. Esas columnas
legacy no describen el progreso del motor de campañas: usar session/records.
Se conservaron resultados parciales de los seis fallidos; ninguno tiene completion
ni verification. Una fila epoch no equivale por sí sola a una fase completada.

### 9.4 Único verified y clasificación del executor

Run `d1a1413b-760c-43a2-89ee-7913e780e87a`, miembro posición 0, tercer intento,
accepted_attempt_id=`c0a559fa-b2d8-4c0c-9175-78c91e2b3057`.
Sesión/attempt/member verified; runs.status=completed. Realizó 27 epochs y seleccionó
la 15. calibration.result={enabled:false,threshold:0.5}, checkpoint_epoch=15,
2693 muestras finales. Completion y verification conservan el mismo records_hash,
recalculado satisfactoriamente sobre sus 138 registros legacy:
`26ddc6680b16e07c65f7ee30146abca007b7981cf97a49a633276ee6fd6beb30`.

Artifact registrado: version_id=`939928f8-01e5-4f4b-855f-1be3c5b19b60`,
5,150,117 bytes, SHA256=`6fa921295a276a061f9a874d19814337bb1906de1067eb7ffcaa657ef7737015`,
path `/app/var/local_artifacts/d1a1413b-760c-43a2-89ee-7913e780e87a/epoch_15.keras`.
Se informa la referencia registrada; no se abrió ni cargó el archivo hoy.

Métricas **de selection.selected_metrics**, no evaluación final V1: recall
0.9479245283018868; specificity 0.9627192982456141; F2 0.9505070379900106;
balanced_accuracy 0.9553219132737505; ROC-AUC clínico 0.9905881054838355;
PR/AP 0.9894598445933798. val_auc Keras es 0.9905922412872314, una fuente diferente.
clinical_objective_met=false. No se inventó matriz/F1/precision final ni se
recalculó un resultado científico para rellenar la ausencia histórica.

Local **demostrable**: environment.execution_mode=local_python,
platform=Darwin/machine=arm64/device=CPU; job
`7ec42a65-e5f1-42b0-8a33-60ca9e4e0f08` está released, process/exit_proof registran
Darwin, exit_code=0 y ausencia de descendientes observados. La revisión
`ce8ba23c-fff5-4f41-8c88-5f8ba8659d2f` está enlazada al attempt/run mediante
campaign_controlled_requests; no mediante train_execution_revisions (vacía para
esta campaña). Esa distinción impide concluir erróneamente «sin revisión».

El segundo intento de posición 0 se liga a revisión técnica Docker
`3ec6fa57-be3f-5433-8557-8c12c3eea740`; falló CONTROLLED_CHILD_EXIT_-9. Su texto de
revisión y el de Local describen SIGKILL/OOM previo; la causa raíz de OOM no se
redemostró aquí. Los otros cinco intentos fallidos conservan entorno original.
Los seis son compatibles con la ruta Docker histórica; no tienen execution_mode
ni platform explícitos en su snapshot. El host con aspecto de ID de contenedor y
la ausencia de job Local no bastan solos para una atestación física retrospectiva.
La atribución Docker de sus fallos está documentada en la revisión; Local posee
además el vínculo estructurado inequívoco citado.

Entorno original: Python 3.12.14, TF 2.17.1, Keras 3.15.1, NumPy 1.26.4,
SQLAlchemy 2.0.52, psycopg 3.3.5. Local registrado: Python 3.12.13 y SQLAlchemy
2.0.53, mismas versiones declaradas de TF/Keras/NumPy/psycopg; source hash distinto,
revisión autorizada y contrato científico inalterado. No se presentan las versiones
declaradas como una auditoría exhaustiva del proceso remoto.

## 10. Hallazgos y límites antes de E10.11

| ID | Hallazgo y evidencia | Consecuencia / condición de revisión |
|---|---|---|
| H1 | Public en 20260915_01, sin columnas/trigger E10; worker.preflight_result_events exige 20260922_01 y event-state Local comprueba columnas | Código E10 disponible no implica despliegue operativo listo. Tratar rollout por separado, con autorización; no corregido aquí. |
| H2 | PREDICTIONS_COMPLETED omite samples; PHASE_STARTED omite arquitectura/compile; CALIBRATION_COMPLETED omite samples y OFF no existe | Quitar put/records sin trasladar esos contenidos perdería evidencia y rompería CompletionValidator/verify/assessment. E10.11 debe conservarla con un diseño explícito; no basta el stream actual. |
| H3 | E7/E8 requieren assessment_results/identities/attempts verified; cero identidades vinculadas; matriz 1/36 verified | No afirmar que todos los resultados experimentales están disponibles sólo porque TRAIN guarda V1. La cola incompleta no es un defecto de persistencia. |
| H4 | Local mide archivos del manifest, no exhaustividad del directorio ni entorno real del worker | Garantía del flujo confiable y de identidad DB; riesgo residual de archivos extra/código remoto distinto. No afirmar una garantía anti-manipulación del proceso. |
| H5 | Callback clínico descarta report completo/matriz/F1 de época; calibración descarta grid; V1 omite otros campos calculados | Hay D explícitos; preservar samples/fuentes y semántica para reconstrucción. No decir «todo resultado calculado se almacena íntegro». |
| H6 | Snapshot de entorno incompleto, plataformas/revisiones distintas; E7 exige environment_hash homogéneo para candidato | Revisión técnica autoriza ejecución, no comparabilidad numérica ni elegibilidad automática del conjunto. |
| H7 | Legacy OFF sin matriz final; runs.completed_epochs=0 aun con 27 epochs verificadas | Readers generales deben distinguir stores; no rellenar/backfill ni ocultar ausencia con estado completed. |
| H8 | policy_satisfied=true puede coexistir con recall<.98; completed/verified no implican objetivo clínico | Mantener diferenciación entre monitor explícito, umbral seleccionado, criterio E7 estricto y éxito técnico. |
| H9 | Checkpoints/imágenes externos; lineage.resolve los vuelve a exigir; Local no finaliza automáticamente campaña agotada | BD sola no permite cargar/revalidar modelo; retención física y cierre operativo son obligaciones separadas. |
| H10 | Escrituras legacy/E10 son secuenciales; fallos conservan evidencia parcial, no atomicidad distribuida | No reinterpretar terminal como verified ni reconstruir ciencia al recuperar journal. |

H1 impide considerar listo el entorno operativo para TRAIN E10 actual. El guard
de esquema Docker corre en el hijo después de claim; Local consulta event-state
después de reservar el job. Intentar ejecutar para comprobar compatibilidad podría
consumir un intento antes de fallar, por lo que no se utilizó ese método de sondeo. H2 es una
condición obligatoria del diseño de desacoplamiento. Los otros hallazgos delimitan
qué está acreditado y qué requiere decisión/revisión; no se implementó su corrección.

## 11. Consultas SELECT reproducibles

Todas las consultas se ejecutan sobre public con una conexión READ ONLY. El snapshot
principal usó REPEATABLE READ; se comprobó transaction_read_only='on'. Parámetro
`:campaign_id` = `3acf89b7-dc42-4b7a-8e2a-ca6ea024c344`. No se ejecutaron funciones
productivas que escriben auditoría ni SELECT con locks de filas/advisory.

```sql
-- Q1: versión, esquema y campaña; no deducir instalación desde archivos Alembic.
SELECT now(), current_database(), current_setting('transaction_read_only'),
       current_setting('transaction_isolation');
SELECT version_num FROM public.alembic_version;
SELECT column_name,data_type FROM information_schema.columns
 WHERE table_schema='public' AND table_name='train_execution_records';
SELECT id,name,state,expected_count,requested,protocol,dataset_snapshot,
       environment,contract,canonical_contract,contract_hash,frozen_at
 FROM public.experimental_campaigns WHERE id=:campaign_id;

-- Q2: matriz y TODOS sus miembros, incluidos los que no tienen run.
SELECT m.position,m.id,m.configuration_hash,m.seed,m.state,m.accepted_attempt_id,
       c.configuration,c.canonical_configuration,c.requests
 FROM public.campaign_members m JOIN public.campaign_configurations c
 ON c.campaign_id=m.campaign_id AND c.configuration_hash=m.configuration_hash
 WHERE m.campaign_id=:campaign_id ORDER BY m.position;
SELECT state,count(*) FROM public.campaign_members
 WHERE campaign_id=:campaign_id GROUP BY state;

-- Q3: todos los intentos; evita inferir parentesco por nombre/fecha/carpeta.
SELECT m.position,a.*,r.status,r.random_seed,r.dataset_version_id,
       r.execution_parameters,r.parameters,r.configuration,
       r.completed_epochs,r.best_epoch,r.checkpoint_monitor,
       s.configuration AS session_configuration,s.dataset,s.environment,
       s.state AS session_state,s.completion,s.verification
 FROM public.campaign_members m JOIN public.campaign_attempts a ON a.member_id=m.id
 LEFT JOIN public.runs r ON r.id=a.training_run_id
 LEFT JOIN public.train_execution_sessions s ON s.run_id=r.id
 WHERE m.campaign_id=:campaign_id ORDER BY m.position,a.ordinal;

-- Q4: ambos stores, compatible también con esquema anterior a E10.
SELECT t.run_id,t.kind,t.phase,t.record_key,t.payload,
       to_jsonb(t)->>'event_id' AS event_id,
       to_jsonb(t)->>'event_sequence' AS event_sequence
 FROM public.train_execution_records t
 JOIN public.campaign_attempts a ON a.training_run_id=t.run_id
 JOIN public.campaign_members m ON m.id=a.member_id
 WHERE m.campaign_id=:campaign_id
 ORDER BY t.run_id,t.kind,t.phase,t.record_key;
-- Para records_hash: por cada run, sólo kind/phase/record_key/payload,
-- filtro (to_jsonb(t)->>'event_id') IS NULL, mismo ORDER BY legacy,
-- digest() canónico aprobado en Python. No hash de repr ni de texto JSONB SQL.

-- Q5: revisión técnica y prueba de executor.
SELECT * FROM public.campaign_technical_revisions WHERE campaign_id=:campaign_id;
SELECT * FROM public.campaign_controlled_requests WHERE campaign_id=:campaign_id;
SELECT * FROM public.train_execution_revisions WHERE campaign_id=:campaign_id;
SELECT id,campaign_id,run_id,state,agent_id,process,exit_proof
 FROM public.local_execution_jobs WHERE campaign_id=:campaign_id;

-- Q6: existencia real de resultados E6 consumidos por E7/E8.
SELECT i.id,i.training_run_id,i.kind,i.identity->>'split' AS split,
       a.id AS attempt_id,a.state,
       (SELECT count(*) FROM public.assessment_results ar WHERE ar.attempt_id=a.id) AS n_results
 FROM public.assessment_identities i
 JOIN public.campaign_attempts ca ON ca.training_run_id=i.training_run_id
 JOIN public.campaign_members m ON m.id=ca.member_id
 LEFT JOIN public.assessment_attempts a ON a.identity_id=i.id
 WHERE m.campaign_id=:campaign_id;

-- Q7: guardas realmente instaladas, no sólo migraciones versionadas.
SELECT cl.relname,t.tgname,t.tgenabled,p.proname,pg_get_functiondef(p.oid)
 FROM pg_trigger t JOIN pg_class cl ON cl.oid=t.tgrelid
 JOIN pg_namespace n ON n.oid=cl.relnamespace JOIN pg_proc p ON p.oid=t.tgfoid
 WHERE n.nspname='public' AND NOT t.tgisinternal AND cl.relname IN
 ('experimental_campaigns','campaign_configurations','campaign_members',
  'campaign_attempts','runs','train_execution_sessions','train_execution_records');
```

La salida de Q4 se leyó sin created_at/run_id en el cálculo de records_hash.
Q3 y Q4 permiten verificar el contraste nominal/runtime descrito. No se incluyen
credenciales en el documento. Los snapshots /tmp son auxiliares de auditoría,
no un nuevo ledger científico ni fuente necesaria para reproducir las consultas.

## 12. Respuestas finales A–F y dictamen

**A. ¿Sabemos exactamente qué debe ejecutar la campaña?** Sí: contrato/matriz
congelados, doce configuraciones y tres semillas; tablas completas en §9 y Q1–Q3.
El orden/reintentos están definidos. Saber qué ejecutar no acredita readiness del
entorno operativo ni autoriza reanudar.

**B. ¿Podemos recuperar la configuración completa recibida por cualquier RUN?**
Sí para los siete runs de esta campaña: snapshot de run/sesión y miembro coinciden.
También existe evidencia runtime de arquitectura/optimizer/compile. Para un run
arbitrario ajeno o previo a este motor hay que comprobar esos stores; no se promete
retroactivamente. Snapshot nominal no equivale a capturar todas las condiciones
físicas, kwargs por batch, estado RNG o entorno real remoto.

**C. ¿Docker y Local obedecen el mismo contrato experimental?** Sí en el flujo
productivo compartido y la identidad persistida: mismo train/configuración/semilla,
reglas TRAIN/VAL y CompletionValidator. Las revisiones cambian entorno/operación,
no el contrato científico. Con los límites de §5, no queda demostrada igualdad
numérica ni atestación completa del proceso/dataset Local contra modificaciones
externas. Las filas congeladas sí están protegidas por las guardas instaladas.

**D. ¿Todos los resultados necesarios para E7/E8/E9 quedan persistidos y recuperables?**
No como afirmación absoluta. TRAIN E10 guarda los resultados finales V1, scores,
historia y referencias requeridas para trazabilidad, pero sigue dependiendo de
records legacy. E7/E8 consumen E6 separado; esta campaña no tiene esas evaluaciones
ni matriz de entrenamiento completa. Hay cálculos D no materializados y archivos
externos indispensables. Lo existente sí es recuperable con los readers/joins
indicados; falta de ejecución no se transforma en resultado científico.

**E. ¿Qué queda deliberadamente fuera de PostgreSQL?** Bytes de imágenes/materialización,
checkpoints .keras, estado/journal operacional del agente, entorno Python instalable,
y exports/figuras derivados. BD guarda identidades/hashes/snapshots/referencias;
no los bytes de esos artefactos. No hay CSV/JSON de resultados que sustituya BD.

**F. ¿Existen pérdidas, inconsistencias o riesgos antes de E10.11?** Sí, detallados
H1–H10: resultados calculados no materializados, dependencia referencial legacy,
schema operativo anterior a E10, lectores distintos, límites Local/entorno y
semánticas de éxito que no deben confundirse. No se detectó discrepancia en los
hashes/configuraciones de los siete runs examinados; no se verificaron binarios
ni se diagnosticó de nuevo la causa de los fallos históricos.

El dictamen permite avanzar a la revisión/diseño de E10.11 con estas observaciones
explícitas; no permite borrar evidencia legacy sin preservar sus contenidos y
consumidores, ni considera autorizado/listo el despliegue o la ejecución operativa.
Sólo se creó este documento. No se implementó E10.11. Espera revisión humana.

**APROBADO CON OBSERVACIONES**
