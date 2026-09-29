# E10.10.4 — Normalización JSONB y contratos científicos
> Actualización E10.10.5A: A-01 fue aprobada por el usuario. La sección final documenta la enmienda; el cuerpo original conserva su contexto histórico. Implementación y límites actuales: [e10_10_5_implementation.md](e10_10_5_implementation.md).

**Diseño propuesto. No modifica writers, algoritmos ni datos actuales.** [Arquitectura](e10_10_4_postgresql_v2_architecture.md) y [DDL conceptual](e10_10_4_target_schema.sql) forman el contrato conjunto.

## 1. Qué existe realmente

`runs.parameters.training_results` es la **clave** persistida. `training_results_v1` es el valor de `schema_version`, no una clave de primer nivel. Su hija `validation` tiene schema `validation_evaluation_v1`, role `training_validation_final`, split `val`, n_samples, threshold, confusion_matrix y metrics. La precisión de esta distinción evita una migración que busque claves inexistentes.

Escritor: `results/service.py:47` valida EVALUATION_COMPLETED, luego `persistence/result_repository.py:66` escribe una vez el JSON, en la transacción del ledger. Lector: `backend_api/app/services/training_summaries.py:77,309`, que da precedencia a esa validación final sobre fallbacks de run_metrics/clinical_metrics/matrices y fuerza `metrics_split='val'`.

Los runs capturados están vacíos. Por tanto **no existe un censo de claves de instancias pobladas** ni evidencia de cardinalidad de cada clave; el inventario es de contratos de código, argumentos CLI y snapshots. `args_to_parameters()` y APIs de tracking admiten mappings extensibles: no es posible afirmar una lista cerrada de todas las claves potenciales externas. La política v2 rechaza desconocidos en el núcleo estable y preserva extensiones con namespace/version/origen. No se elimina silenciosamente una clave desconocida al adoptar una copia.

## 2. Autoridad de cada representación

| Objeto | Autoridad | JSON que conserva |
| --- | --- | --- |
| runs | Identidad/ciclo de vida y entorno observado | parameters: anotaciones extensibles sin training_results; metadata: procedencia no científica; gpu_devices: inventario variable. |
| run_configurations | Columnas resueltas para filtros/reproducción y texto canónico para comprobar identidad | optimizer_extensions, extension_configuration, provenance_snapshot; no otro resultado científico. |
| execution_parameters.model_configuration_e2 | Evidencia congelada que los guards vigentes comparan | configuration/requested/resolved, runtime, dataset, execution, environment íntegros; no fuente de métricas para React. |
| train_execution_sessions.configuration / campaign_configurations.configuration | Contrato de reserva y campaña | Snapshot y canonical_configuration/hash preservados. No sustituir por referencia mutable. |
| train_execution_records.payload | Evidencia original E10 o registro legacy | canonical_event string exacto; no parsear/serializar para reescribir. |
| evaluations + run_clinical_metrics | Resultado científico consolidado | Protocolo, definición y razones; métricas estables en columnas. |
| assessment_identities/results/artifacts | Identidad, resultados por muestra y artefactos inmutables | Preservar payload; añadir proyección en writers de assessment, no cambiar documento firmado. |
| model_versions/deployments / inputs clínicos | Contrato de modelo/preprocesamiento congelado | Snapshots de class mapping, signatures y preprocessing mantienen su papel. |
| XAI | Configuración variable por algoritmo; archivos numéricos externos | Método versionado, ambiente/input contract, protocolo cuantitativo; no matrices grandes en JSONB. |

Duplicar evidencia original y proyección **no** crea dos fuentes científicas: la evidencia no se edita y la proyección se deriva atómicamente y es la fuente de lectura. Las columnas alias históricas de run_clinical_metrics son derivadas/controladas. La duplicación de `sensitivity_parasitized` respecto de recall se expone como un alias; el DTO usa `recall` y etiqueta «sensibilidad». Un futuro retiro de alias sólo se hará cuando no existan consumidores.

## 3. Matriz JSON → relacional

Rutas `RC` = run_configurations, `E` = evaluations, `M` = run_clinical_metrics. El dataset del TRAIN queda en runs.dataset_version_id. `resolved` abrevia `execution_parameters.model_configuration_e2.configuration.resolved`. El nombre del writer corresponde a módulos dentro de malaria_dl_local_project/src/malaria_dl salvo prefijo backend.

| JSON actual | Campo relacional | Tipo | Transformación | Escritor | Lector |
| --- | --- | --- | --- | --- | --- |
| parameters.training_results.schema_version | E.metric_definition + evidencia v1 | text | Mantener v1 original, proyectar binary_nullable_v2 | ResultService/PostgresResultRepository | training_summaries; completion |
| training_results.validation.schema_version | E.source_kind / source record | text + FK ledger | Validar validation_evaluation_v1, no copiar como otra tabla | results/training.py | DTO evaluación |
| validation.evaluation_role | E.evaluation_role | text CHECK | training_validation_final | ResultService | summaries, comparación |
| validation.split | E.split | text CHECK | val literal; no inferir del run_type | ResultService | summaries, RunDetail |
| validation.n_samples | M.sample_count | numeric entero derivado | Exigir igualdad exacta con suma conteos | ResultService | comparador |
| validation.threshold.value | E.threshold_used, alias M.threshold_used | numeric [0,1] | Default exige .5; calibration exige evidencia val | ResultService | evaluación/publicación informativa |
| validation.threshold.source | E.threshold_source | text CHECK | default / validation_calibration | ResultService | API clinical summary |
| validation.confusion_matrix.tn | M.tn | bigint >=0 | Entero estricto; prohibir bool/float coercion | ResultService | FN/FP, matriz |
| validation.confusion_matrix.fp | M.fp | bigint >=0 | Entero estricto | ResultService | matriz |
| validation.confusion_matrix.fn | M.fn | bigint >=0 | Entero estricto | ResultService | sensibilidad |
| validation.confusion_matrix.tp | M.tp | bigint >=0 | Entero estricto | ResultService | matriz |
| validation.metrics.recall | M.recall_parasitized | numeric nullable | Derivar TP/(TP+FN); validar recibido si definido | ResultService + trigger | ModelComparison |
| validation.metrics.specificity | M.specificity | numeric nullable | TN/(TN+FP) | ResultService + trigger | ModelComparison |
| validation.metrics.precision | M.precision_parasitized | numeric nullable | TP/(TP+FP) | ResultService + trigger | RunDetail |
| validation.metrics.f1 | M.f1_parasitized | numeric nullable | 2TP/(2TP+FP+FN) | ResultService + trigger | RunDetail |
| validation.metrics.f2 | M.f2_parasitized | numeric nullable | 5TP/(5TP+FP+4FN) | ResultService + trigger | comparador |
| validation.metrics.balanced_accuracy | M.balanced_accuracy | numeric nullable | Media si ambas tasas definidas | ResultService + trigger | comparador |
| validation.metrics.roc_auc | M.roc_auc_parasitized | numeric nullable | Copiar validado; jamás reconstruir desde matriz | ResultService | API resultados |
| validation.metrics.pr_auc | M.pr_auc_parasitized | numeric nullable | Copiar con protocolo/método AUC | ResultService | API resultados |
| resolved.model + configuration.model_id | RC.architecture | text CHECK | registry canonical custom_cnn/vgg16/densenet121; no UUID models.id | execution/repository, model_configuration | training_summaries |
| configuration.adapter_version | RC.adapter_version | text | Copiar versión efectiva | persist_model_configuration | gobernanza, XAI |
| resolved.optimizer.name | RC.optimizer | text CHECK | Nombre canónico adam/adamw/sgd/adadelta | configuración/reserva | ModelComparison |
| resolved.optimizer.parameters.learning_rate | RC.learning_rate | float8 finito >0 | Separar LR principal del fine tune | configuración/reserva | ModelComparison |
| resolved.optimizer.fine_tune_learning_rate | RC.fine_tune_learning_rate | float8 finito >0 | No reemplazar LR principal | configuración/reserva | RunDetail |
| resolved.optimizer.parameters.* restantes | RC.optimizer_extensions | JSONB object | beta/epsilon/momentum/etc: preserve registro validado por optimizers.py | resolve_config | reproducción |
| resolved.execution.batch_size | RC.batch_size | integer >0 | Valor efectivo, no CLI solicitado | reserva/TRAIN | comparación |
| resolved.execution.seed | RC.random_seed | bigint >=0 | Validar coincide runs.random_seed y miembro | reserva/TRAIN | comparación seeds |
| resolved.execution.max_epochs | RC.max_epochs | integer >0 | Épocas base solicitadas | TRAIN | curvas/config |
| resolved.execution.fine_tune_epochs | RC.fine_tune_epochs | integer >=0 | Total solicitado = suma, no completed_epochs | TRAIN | curvas/config |
| resolved.execution.early_stopping | RC.early_stopping | boolean | Sin conversión truthy de strings | TRAIN | RunDetail |
| resolved.execution.early_stopping_patience | RC.early_stopping_patience | integer >=0 | Exacto | TRAIN | RunDetail |
| resolved.execution.early_stopping_min_delta | RC.early_stopping_min_delta | float8 finito >=0 | Sin redondeo | TRAIN | RunDetail |
| resolved.selection.early_stopping_monitor/mode | RC.early_stopping_monitor/mode | text | Usar selección resuelta, no auto | TRAIN | RunDetail |
| resolved.execution.restore_best_weights | RC.restore_best_weights | boolean | Congelado | TRAIN | checkpoint |
| resolved.selection.monitor/mode | RC.checkpoint_monitor/mode | text | Monitor efectivo y sentido min/max | TRAIN | checkpoint |
| resolved.model.dropout/l2 | RC.dropout/l2 | float8 [0,1) | No habilitar L2 donde registry lo prohíbe | TRAIN | comparación/config |
| resolved.model.input_shape | RC.input_height/width/channels | integer | NHWC contrato externo; conservar batch axis en snapshot | TRAIN | reproducción/XAI |
| resolved.model.weights/fine_tune_layers | RC.weights/fine_tune_layers | text/integer | Respetar estrategias por arquitectura | TRAIN | detalle |
| resolved.model.preprocessing | RC.normalization | text CHECK | auto ya resuelto por descriptor | TRAIN | comparación/XAI |
| resolved.input_contract.internal | RC.internal_preprocessing + snapshot | text nullable | DenseNet interno real; no duplicar transformación | TRAIN | inferencia |
| resolved.recipe.loss / compile loss efectiva | RC.loss_function | text NOT NULL | Copiar recipe.loss y contrastar adapter/runtime; no inferir desde etiqueta binaria | TRAIN adapter | reproducción |
| resolved.execution.calibrate_threshold | RC.calibration_enabled | boolean default false | Fijar al crear run | TRAIN | calibración |
| resolved.execution.target_recall | RC.clinical_target_recall | numeric =.98 | Preservar decisión clínica aprobada | TRAIN | badge informativo |
| config_digest(resolved) | RC.configuration_hash/canonical_configuration | text SHA256 / text | Hash existente, mismos bytes canónicos, no JSONB reserializado | configuración/reserva | lineage/preflight |
| requested/provenance / cli_arguments | RC.provenance_snapshot | JSONB | Evidencia de resolución; no competir con columnas efectivas | tracking/model_configuration | auditoría |
| parameters.execution_parameters y aliases optimizer/model_name | RC + snapshot origen | tipos anteriores | Validar equivalencia; conflicto bloquea adopción | tracking/start_tracking_run | retirar cadena COALESCE summaries |
| parameters.checkpoint_dir/output_dir | artifacts.path/URI; snapshot | text | Conservar rutas físicas, sin mover archivos | checkpoint/tracking | gobernanza |
| parameters.checkpoint_policy_config | run_checkpoint_policy | columnas actuales + snapshot | Reutilizar monitor/policy y evidencia | callbacks/tracking | API checkpoint-policy |
| parameters.calibrate_threshold, target_recall/min_specificity | RC y run_threshold_calibration | bool/numeric | Sólo val; congelado antes TEST | training/trainer | clinical summary |
| execution_parameters.model_configuration_e2.dataset | runs.dataset_version_id + evidencia | uuid/JSONB | Verificar binding sin tocar materialización | execution/repository | preflight/assessment |
| execution_parameters.dataset_verification_evidence_id | Evidencia existente metadata/session | text/JSONB residual | No tratarlo como FK si no existe entidad con PK correspondiente | dataset_evidence | auditoría |
| execution_parameters.artifact_snapshot_dir | artifacts + snapshot | text | No inventar archivo por completar columna | trainer | recovery |
| execution_parameters.test_evaluation_policy/completed | E purpose/role y estado existente | text/estado | No convertir flag histórico en TEST verificado | trainer/completion | lineage |
| metadata.dataset_verification_evidence | Evidencia congelada residual | JSONB | No repetir hashes de imágenes | dataset_evidence | preflight |
| metadata.model_name/optimizer | RC / models join | text | Evitar fallback que mezcle distintas fuentes | tracking | summaries |
| metadata.tracking_version/label_mapping/raw_model_score_meaning | E protocolo / modelo snapshot | text/JSONB | Fijar parasitized=1, score domain | tracking | métricas/XAI |
| runs.configuration | Snapshot de inferencia conservado | JSONB | No equiparar configuration de INFERENCE a TRAIN | inference/traceable | inference_runs/view |
| runs.gpu_devices | Inventario observado residual | JSONB array | No normalizar cada atributo de driver | environment tracking | observabilidad |
| run_clinical_metrics.confusion_matrix/classification_report | Conteos + vistas/DTO | bigint/numeric | Matriz derivada; reporte class/macro/weighted calculado | proyección | runs/summary |
| run_threshold_calibration.default_threshold_metrics/selected_threshold_metrics | E referenciadas por default_evaluation_id/selected_evaluation_id | uuid FK | Misma población val/checkpoint, umbral .5/seleccionado | calibración | API threshold |
| assessment_results.payload | predictions.evaluation_id para scores; métricas agregado E/M | uuid/numeric | Preservar evidence, proyectar por sample_id/attempt | assessment/repository/service | comparador/evaluación |
| train_execution_records.payload epoch | training_history | numeric por train/val/fase/epoch | Mismo scope; misma clave rechaza contenido diferente | ResultService | curvas |
| explainability_results.explanation_parameters | xai_evidence | typed method/version/class + JSONB residual | Distinguir algoritmo y ruta real | tracking/case_gradcam | Explainability |
| cell_explanations.parameters_json | xai_evidence | typed + input snapshot | Conservar guard celular original | cell_classification service | CaseExplainabilityView |
| assessment explanation identity / artifact payload | xai_evidence/xai_artifacts | FK + URI/hash/dtype/shape | Reutilizar NPY/PNG, background TRAIN | assessment | comparador XAI |

## 4. Transacción y conflictos

El servicio mantiene READ COMMITTED, locks/fencing existentes y sesión autorizada. El estado de secuencia se lee en el mismo scope. INSERT del ledger y proyección E/M se comprometen juntos. La PK de evento se referencia completa; source_event_id se valida contra esa fila mediante trigger. Una evaluación final TRAIN tiene UNIQUE parcial por run, además de UNIQUE de origen. Dos eventos distintos que intenten finalizar la misma evaluación provocan rollback de la segunda aceptación.

La materialización final obtiene checkpoint del contrato de selección y artefacto registrado en la misma transacción, no del payload mínimo de ValidationEvaluationV1 (que no contiene checkpoint). Se verifica la evidencia de selección previa y el entorno congelado; si faltan, se rechaza el evento/proyección sin aceptar evidencia parcial. La versión puede nacer después de TRAIN completed, por lo que model_version_id de E es opcional; la versión se resuelve por TRAIN/checkpoint al leer, sin actualizar una evaluación inmutable. Para assessment, run_id puede ser el TRAIN propietario porque el subsistema usa attempts propios; no se crea un run EVALUATE ficticio para cada intento. Las publicaciones existentes conservan su run EVALUATE real.

Epoch: UPSERT sólo admite duplicado con valores iguales; no usar ON CONFLICT DO UPDATE para sobrescribir ciencia. Si una misma época tiene eventos parciales TRAIN/val, la proyección se completa durante sesión activa y se congela al cierre; el writer valida que valores ya presentes no cambien. No se agrega trigger de inmutabilidad total a training_history porque bloquearía esa composición. `loss/train_loss` y `accuracy/train_accuracy` históricos se resuelven por alias controlado, no dos series.

La adopción enumera todo JSON, separa namespaces y preserva payload original antes de transformar. No convierte texto vacío/NaN/boolean en número; rechaza contradicciones de split, cantidad, umbral, checkpoint y hashes. Si no existe suficiente procedencia, conserva evidencia en archivo de adopción auditado y marca resultado no comparable; no lo incorpora como científico v2 por defecto. No hay autorización para borrar filas no mapeables.

## 5. Tipos, API y validación

Los DTO v2 exponen `metric_definition`, valores nullable y `undefined_reason` calculado por denominador, y razón AUC específica. Para compatibilidad v1, conservar el payload E10 original, no reconstruir el cero desde un NULL sin anunciar contrato. Los serializers de métricas v2 no reutilizan `BinaryMetrics` v1. API de matrices conserva orden `[[TN,FP],[FN,TP]]` y labels `[uninfected,parasitized]`; los conteos se serializan como enteros JSON, incluso si sample_count SQL es numeric entero.

`classification_reports` ya no tiene una fila persistida con UUID propio por clase. Su clave de API v2 es `(evaluation_id,class_name)`. Las filas macro/weighted se calculan con política nullable documentada; no interpolar un valor ausente como cero. Interfaces antiguas que escriban o dependan de ese UUID dejan de ser compatibles y deben migrarse antes del corte. EAV de extensión no puede aceptar alias alternativos de una métrica reservada; la validación de nombres en aplicación complementa CHECK SQL, y las vistas legacy se redirigen a proyección con nombres esperados en E10.10.7.

## 6. Inventario exhaustivo de columnas JSONB actuales

130 columnas de tablas, excluidas las JSONB que son salidas de vistas. «Conservar evidencia» no significa conservar consultas de comparación sobre documentos heterogéneos. El CSV general identifica productores/lectores por tabla; las rutas normalizadas se detallan arriba. Columnas protegidas permanecen byte/lógicamente intactas en adopción. Los namespaces extensibles de metadata requieren catálogo versionado del writer, no expansión indiscriminada de columnas.

| Tabla.columna actual | Decisión v2 |
| --- | --- |
| `artifacts.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `assessment_artifacts.payload` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `assessment_attempts.verification` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `assessment_final_locks.evidence` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `assessment_identities.identity` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `assessment_results.payload` | Evidencia append-only; proyección atómica a métricas/épocas/predicciones/XAI según contrato, conservar bytes canónicos. |
| `audit_events.before_state` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `audit_events.after_state` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `audit_events.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `blood_samples.metadata_json` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `campaign_configurations.configuration` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `campaign_configurations.requests` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `campaign_technical_revisions.payload` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `cell_classification_events.metadata_json` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `cell_classification_runs.model_snapshot` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `cell_detection_events.metadata_json` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `cell_detection_runs.profile_snapshot` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `cell_explanations.parameters_json` | Extraer método/config/input/modelo a xai_evidence; conservar parámetros técnicos extensibles y contrato original. |
| `cell_predictions.raw_output` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `cell_predictions.preprocessing_snapshot` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `classification_reports.metadata` | MERGE: reporte derivado por clase; metadata de origen preservada en manifiesto de adopción. |
| `clinical_identities.metadata` | PROTECTED: sin cambios; mantener contrato científico/identidad actual. |
| `confusion_matrices.matrix` | MERGE: matriz y labels derivados de conteos/contrato binario; metadata preservada en medición/manifiesto de adopción. |
| `confusion_matrices.metadata` | MERGE: matriz y labels derivados de conteos/contrato binario; metadata preservada en medición/manifiesto de adopción. |
| `dataset_materialization_activations.metadata` | PROTECTED: sin cambios; mantener contrato científico/identidad actual. |
| `dataset_materializations.manifest_metadata` | PROTECTED: sin cambios; mantener contrato científico/identidad actual. |
| `dataset_materializations.metadata` | PROTECTED: sin cambios; mantener contrato científico/identidad actual. |
| `dataset_source_records.metadata` | PROTECTED: sin cambios; mantener contrato científico/identidad actual. |
| `dataset_split_assignments.metadata` | PROTECTED: sin cambios; mantener contrato científico/identidad actual. |
| `dataset_split_images.metadata` | PROTECTED: sin cambios; mantener contrato científico/identidad actual. |
| `dataset_split_statistics.details_json` | PROTECTED: sin cambios; mantener contrato científico/identidad actual. |
| `dataset_split_validation_checks.details_json` | PROTECTED: sin cambios; mantener contrato científico/identidad actual. |
| `dataset_splits.class_distribution` | PROTECTED: sin cambios; mantener contrato científico/identidad actual. |
| `dataset_splits.metadata` | PROTECTED: sin cambios; mantener contrato científico/identidad actual. |
| `dataset_versions.class_mapping` | PROTECTED: sin cambios; mantener contrato científico/identidad actual. |
| `dataset_versions.methodology_json` | PROTECTED: sin cambios; mantener contrato científico/identidad actual. |
| `datasets.class_distribution` | PROTECTED: sin cambios; mantener contrato científico/identidad actual. |
| `datasets.metadata` | PROTECTED: sin cambios; mantener contrato científico/identidad actual. |
| `deployed_model_versions.threshold_profile_snapshot` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `deployed_model_versions.preprocessing_profile_snapshot` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `deployed_model_versions.image_quality_policy_snapshot` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `deployed_model_versions.label_mapping_snapshot` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `deployed_model_versions.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `errors.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `execution_logs.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `experiment_execution_events.payload` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `experiment_execution_gate.process_evidence` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `experimental_campaigns.dataset_snapshot` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `experimental_campaigns.requested` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `experimental_campaigns.protocol` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `experimental_campaigns.environment` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `experimental_campaigns.registry_snapshot` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `experimental_campaigns.contract` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `experiments.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `explainability_results.explanation_parameters` | Extraer método/config/input/modelo a xai_evidence; conservar parámetros técnicos extensibles y contrato original. |
| `explainability_results.metadata` | Extraer método/config/input/modelo a xai_evidence; conservar parámetros técnicos extensibles y contrato original. |
| `identity_evidence.evidence_json` | PROTECTED: sin cambios; mantener contrato científico/identidad actual. |
| `image_analysis_jobs.quality_metrics` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `image_analysis_jobs.summary` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `image_analysis_jobs.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `image_connected_components.metrics_json` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `image_ingestion_batches.metadata_json` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `image_quality_assessments.warning_codes` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `image_quality_assessments.failure_codes` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `image_quality_assessments.metrics_json` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `local_execution_jobs.session` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `local_execution_jobs.process` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `local_execution_jobs.completion` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `local_execution_jobs.exit_proof` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `local_execution_jobs.result` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `microscopy_analysis_runs.quality_profile_snapshot` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `microscopy_images.metadata_json` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `model_governance_backfill_audit.before_values` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `model_governance_backfill_audit.after_values` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `model_governance_backfill_audit.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `model_versions.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `model_versions.preprocessing_profile_snapshot` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `model_versions.class_mapping` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `model_versions.input_signature` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `model_versions.output_signature` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `models.metadata` | PROTECTED: sin cambios; mantener contrato científico/identidad actual. |
| `predictions.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `research_subjects.metadata_json` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `run_checkpoint_policy.checkpoint_policy_config` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `run_checkpoint_policy.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `run_clinical_metrics.confusion_matrix` | Derivar de conteos/DTO; no escritura científica independiente. |
| `run_clinical_metrics.classification_report` | Derivar de conteos/DTO; no escritura científica independiente. |
| `run_clinical_metrics.prediction_distribution` | Derivar de conteos/DTO; no escritura científica independiente. |
| `run_clinical_metrics.prediction_collapse` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `run_clinical_metrics.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `run_dataset_images.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `run_image_predictions.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `run_io_records.input_parameters` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `run_io_records.output_results` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `run_io_records.output_artifacts` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `run_io_records.dataset_metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `run_io_records.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `run_io_records.model_metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `run_io_records.clinical_metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `run_lineage.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `run_metrics.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `run_model_deployments.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `run_threshold_calibration.default_threshold_metrics` | Normalizar a evaluaciones referenciadas; mantener snapshot de evidencia anterior sin usarlo como lectura canónica. |
| `run_threshold_calibration.selected_threshold_metrics` | Normalizar a evaluaciones referenciadas; mantener snapshot de evidencia anterior sin usarlo como lectura canónica. |
| `run_threshold_calibration.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `runs.gpu_devices` | Conservar array de inventario técnico variable. |
| `runs.parameters` | Normalizar training_results y configuración estable; prohibir namespace científico duplicado. |
| `runs.metadata` | Extraer aliases estables al contrato tipado; conservar procedencia y evidencia. |
| `runs.execution_parameters` | Normalizar campos resolved a run_configurations; conservar snapshot E10 inmutable para guards/hashes. |
| `runs.configuration` | Conservar contrato INFERENCE; no usar como TRAIN resuelto. |
| `schema_migrations.execution_metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `scientific_cases.metadata_json` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `scientific_validation_annotation_events.before_state` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `scientific_validation_annotation_events.after_state` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `scientific_validation_sessions.initial_snapshot` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `smear_analysis_summaries.per_image_summary` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `smear_analysis_summaries.aggregation_policy_snapshot` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `smear_slides.metadata_json` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `stage2_model_publication_events.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `stage2_model_publications.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `synthetic_data_runs.generation_parameters` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `synthetic_data_runs.quality_checks` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `synthetic_data_runs.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `train_execution_records.payload` | Evidencia append-only; proyección atómica a métricas/épocas/predicciones/XAI según contrato, conservar bytes canónicos. |
| `train_execution_sessions.configuration` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `train_execution_sessions.dataset` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `train_execution_sessions.environment` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `train_execution_sessions.completion` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `train_execution_sessions.verification` | Conservar evidencia/metadatos extensibles; sin GIN automático. |
| `training_history.metadata` | Conservar evidencia/metadatos extensibles; sin GIN automático. |

## 7. Claves observables en constructores y argumentos TRAIN

Inventario estático de nombres literales en los constructores de `execution_parameters`, `run_parameters`, snapshots, `args_to_parameters(extra=...)` y argumentos CLI que pueden entrar por `vars(args)`. Se enumeran sin ejecutar parsers, importar TensorFlow ni leer datos. Las expansiones `**dataset_info` se conservan según contrato de dataset; no se las presenta como una lista cerrada. Configuración `resolved` anidada se mapea en la sección 3. Flags de ejecución/diagnóstico no son hiperparámetros efectivos.

| Clave | Evidencia del constructor | Destino/política |
| --- | --- | --- |
| `all_epochs_collapsed` | training/trainer.py:1971 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `allow_collapsed_checkpoint` | training/cli.py:108 (CLI/vars(args)) | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `artifact_snapshot_dir` | training/trainer.py:1955 | artifacts/path + snapshot |
| `augment` | training/trainer.py:1009; training/trainer.py:1059; training/trainer.py:1953 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `base_max_epochs` | training/trainer.py:1012; training/trainer.py:1083; training/trainer.py:1988 | RC.max_epochs alias |
| `batch_size` | training/cli.py:50 (CLI/vars(args)) | RC.batch_size |
| `beta` | training/cli.py:96 (CLI/vars(args)) | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `calibrate_threshold` | training/cli.py:119 (CLI/vars(args)); training/trainer.py:1033; training/trainer.py:1076; training/trainer.py:1975 | RC.calibration_enabled |
| `checkpoint_dir` | training/trainer.py:1060 | artifacts/path + snapshot solicitado |
| `checkpoint_metric` | training/trainer.py:1080 | RC.checkpoint_monitor alias |
| `checkpoint_mode` | training/cli.py:141 (CLI/vars(args)); training/trainer.py:1018; training/trainer.py:1081; training/trainer.py:1986 | RC.checkpoint_mode |
| `checkpoint_monitor` | training/cli.py:70 (CLI/vars(args)); training/trainer.py:1079; training/trainer.py:1984 | RC.checkpoint_monitor |
| `checkpoint_monitor_configured` | training/trainer.py:1985 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `checkpoint_policy` | training/cli.py:81 (CLI/vars(args)); training/trainer.py:1067; training/trainer.py:1957 | run_checkpoint_policy |
| `checkpoint_policy_config` | training/trainer.py:1068; training/trainer.py:1958 | run_checkpoint_policy + evidencia congelada |
| `checkpoint_selection_source` | training/trainer.py:1019 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `checkpoint_warning` | training/trainer.py:1974 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `class_names` | training/trainer.py:1063 | Modelo/protocolo label_mapping existente |
| `cli_arguments` | training/trainer.py:1006 | RC.provenance_snapshot requested; nunca fuente efectiva si resolved existe |
| `clinical_threshold` | training/trainer.py:1977 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `config_digest` | training/cli.py:244 (CLI/vars(args)) | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `configuration` | execution/repository.py:191 | RC columnas + canonical_configuration; snapshot evidencia E10 |
| `configuration_json` | training/cli.py:237 (CLI/vars(args)) | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `configuration_origin_json` | training/cli.py:238 (CLI/vars(args)) | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `dataset` | execution/repository.py:192 | runs.dataset_version_id + snapshot protegido |
| `dataset_version_id` | training/cli.py:223 (CLI/vars(args)) | runs.dataset_version_id |
| `deterministic_ops` | training/cli.py:241 (CLI/vars(args)) | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `dry_run` | training/cli.py:240 (CLI/vars(args)) | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `early_stopping` | training/cli.py:149 (CLI/vars(args)); training/trainer.py:1024; training/trainer.py:1086; training/trainer.py:1991 | RC.early_stopping |
| `early_stopping_internal_monitor` | training/trainer.py:1026; training/trainer.py:1088 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `early_stopping_min_delta` | training/cli.py:176 (CLI/vars(args)); training/trainer.py:1029; training/trainer.py:1093; training/trainer.py:1995 | RC.early_stopping_min_delta |
| `early_stopping_mode` | training/cli.py:164 (CLI/vars(args)); training/trainer.py:1027; training/trainer.py:1091; training/trainer.py:1993 | RC.early_stopping_mode |
| `early_stopping_monitor` | training/cli.py:155 (CLI/vars(args)); training/trainer.py:1025; training/trainer.py:1087; training/trainer.py:1992 | RC.early_stopping_monitor |
| `early_stopping_patience` | training/cli.py:170 (CLI/vars(args)); training/trainer.py:1028; training/trainer.py:1092; training/trainer.py:1994 | RC.early_stopping_patience |
| `environment` | execution/repository.py:193 | Snapshot y environment_packages; inventario técnico |
| `epochs` | training/cli.py:42 (CLI/vars(args)) | RC.max_epochs; requested original en provenance |
| `epochs_legacy_requested` | training/trainer.py:1016 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `epochs_source` | training/trainer.py:1015 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `evaluate_best_on_test` | training/cli.py:188 (CLI/vars(args)); training/trainer.py:1031; training/trainer.py:1095; training/trainer.py:1997 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `execution_id` | training/trainer.py:1005 | runs.id/identidad de ejecución; validar equivalencia |
| `execution_parameters` | training/trainer.py:1058; training/trainer.py:1952 | Descomponer por mapa; preservar original como evidencia |
| `execution_type` | training/trainer.py:1057; training/trainer.py:1951 | runs.execution_type |
| `expected_dataset_evidence_id` | training/cli.py:234 (CLI/vars(args)) | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `fine_tune_epochs` | training/cli.py:48 (CLI/vars(args)) | RC.fine_tune_epochs |
| `fine_tune_learning_rate` | training/cli.py:53 (CLI/vars(args)) | RC.fine_tune_learning_rate |
| `fine_tune_max_epochs` | training/trainer.py:1013; training/trainer.py:1084; training/trainer.py:1989 | RC.fine_tune_epochs alias |
| `img_size` | training/cli.py:49 (CLI/vars(args)) | RC.input_height/input_width |
| `label_mapping` | persistence/tracking.py:523; training/trainer.py:1065 | Snapshot de contrato; parasitized=1 |
| `label_mapping_version` | persistence/tracking.py:522; training/trainer.py:1064 | Protocolo/modelo; no columna científica libre |
| `learning_rate` | training/cli.py:52 (CLI/vars(args)) | RC.learning_rate |
| `max_epochs` | training/cli.py:33 (CLI/vars(args)); training/trainer.py:1011; training/trainer.py:1082; training/trainer.py:1987 | RC.max_epochs |
| `max_epochs_requested` | training/trainer.py:1017 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `min_class_fraction` | training/cli.py:113 (CLI/vars(args)); training/trainer.py:1075 | run_checkpoint_policy + snapshot |
| `min_recall` | training/cli.py:90 (CLI/vars(args)) | run_checkpoint_policy criterio existente |
| `min_recall_required` | training/trainer.py:1071; training/trainer.py:1967 | run_checkpoint_policy criterio existente |
| `min_specificity` | training/cli.py:130 (CLI/vars(args)); training/trainer.py:1078 | run_threshold_calibration.min_specificity |
| `model` | training/cli.py:27 (CLI/vars(args)) | RC.architecture (alias registry) |
| `model_config` | training/cli.py:239 (CLI/vars(args)) | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `model_internal_preprocessing` | training/trainer.py:1034 | RC.internal_preprocessing |
| `no_augment` | training/cli.py:69 (CLI/vars(args)) | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `optimizer` | training/cli.py:63 (CLI/vars(args)); training/trainer.py:1008; training/trainer.py:1099; training/trainer.py:1999 | RC.optimizer |
| `output_dir` | training/cli.py:199 (CLI/vars(args)); training/trainer.py:1061; training/trainer.py:1954 | artifacts/path + snapshot solicitado |
| `policy_satisfied` | training/trainer.py:1962 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `positive_label` | training/cli.py:216 (CLI/vars(args)) | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `prediction_collapse_detected` | training/trainer.py:1968 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `preprocessing` | training/cli.py:207 (CLI/vars(args)) | RC.normalization |
| `preprocessing_mode` | training/trainer.py:1062; training/trainer.py:1956 | RC.normalization |
| `pretrained_weights` | training/cli.py:54 (CLI/vars(args)); training/trainer.py:1010 | RC.weights |
| `raw_model_score_meaning` | persistence/tracking.py:524; training/trainer.py:1066 | E protocolo/modelo score_domain |
| `reject_prediction_collapse` | training/cli.py:102 (CLI/vars(args)); training/trainer.py:1072 | run_checkpoint_policy + snapshot |
| `restore_best_weights` | training/cli.py:182 (CLI/vars(args)); training/trainer.py:1030; training/trainer.py:1094; training/trainer.py:1996 | RC.restore_best_weights |
| `seed` | training/cli.py:51 (CLI/vars(args)) | RC.random_seed |
| `selected_epoch` | training/trainer.py:1961 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `selected_metric` | training/trainer.py:1963 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `selected_metric_value` | training/trainer.py:1964 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `skip_final_test_evaluation` | training/cli.py:194 (CLI/vars(args)); training/trainer.py:1032; training/trainer.py:1096 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `target_recall` | training/cli.py:124 (CLI/vars(args)); training/trainer.py:1077 | RC.clinical_target_recall |
| `test_used_for_selection` | training/trainer.py:1998 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `threshold_calibration` | training/trainer.py:1976 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `threshold_calibration_path` | training/trainer.py:1978 | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `threshold_output_json` | training/cli.py:136 (CLI/vars(args)) | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |
| `total_max_epochs` | training/trainer.py:1014; training/trainer.py:1085; training/trainer.py:1990 | Derivar suma base+fine_tune; no escribir otro valor autoritativo |
| `track_db` | training/cli.py:229 (CLI/vars(args)) | Provenance snapshot / extensión versionada del contrato original; no métrica científica ni fuente de comparación. Resolver en mapper sin descartar. |

## Enmienda A-01 aprobada — 2026-09-29

**A-01 RESUELTA POR DECISIÓN ARQUITECTÓNICA — E10.10.5A PUEDE REANUDARSE.** Autorización explícita del usuario, limitada a diseño, baseline y validación estática; no autoriza B ni cutover. El texto anterior conserva la decisión original. Sus hashes y la definición original de evaluations están en [e10_10_5a_design_before_a01.json](e10_10_5a_design_before_a01.json); el bloqueo original se conserva en [e10_10_5a_initial_block.md](e10_10_5a_initial_block.md).

- `evaluations.split` admite `external` además de los tres splits oficiales. `external_validation` permanece intacto en el dataset protegido; no se crea un alias ni mapping automático.
- Ámbito (`split`), población (`population_hash` y manifiesto), origen (`dataset_origin_id`, `dataset_origin_role` y evidencia de procedencia), protocolo (`protocol_hash/version/snapshot`) y finalidad (`purpose`) son conceptos independientes.
- External exige `purpose=complementary`, `evaluation_role=external_complementary`, manifiestos de población/procedencia recuperables con SHA-256 y FK a la PK existente `(dataset_version_id,dataset_id,role)` del origen registrado en `dataset_version_sources`, sin añadir UNIQUE al dominio protegido. La versión evaluada puede diferir de la versión de entrenamiento; se conserva íntegro el linaje TRAIN/checkpoint/modelo. No se crean versiones ni fuentes ficticias para completar esa FK.
- `source_kind=external_record` identifica nuevas entradas externas; `legacy` permite adopción con evidencia suficiente. No se hace pasar una entrada externa por evento E10 ni por assessment cuyo contrato actual sólo admite splits oficiales.
- Se prohíbe usar external como calibración, selección de checkpoint/modelo, VALIDATION sustitutiva o agregado TEST oficial. Los roles y la finalidad lo impiden en evaluations, el par de calibración exige val, y `vw_v2_model_comparison` sólo contiene train/val/test. `vw_v2_external_evidence` expone evidencia complementaria sin agregación, con población, protocolo y procedencia. El catálogo pasa de 32 a **33 vistas**; mantiene **103 tablas**.
- `run_clinical_metrics.split_name` sigue representando `external`; su trigger lo deriva de la evaluación externa trazada. Se conservan el lector/escritor legacy en la aplicación operativa. Adaptar esos escritores al contrato transaccional v2 corresponde a E10.10.5E: esta enmienda no afirma compatibilidad binaria de INSERT antiguos que carezcan de evaluation_id.
- La existencia de un URI/hash no certifica disponibilidad o validez científica del manifiesto. La adopción abortará sin mapping si falta evidencia; los servicios deben verificar procedencia y políticas de selección. No se modifican imágenes, asignaciones ni hashes históricos.
