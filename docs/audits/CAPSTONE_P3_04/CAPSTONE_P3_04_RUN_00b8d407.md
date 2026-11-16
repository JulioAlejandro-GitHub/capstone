# CAPSTONE-P3-04 — Caso principal 00b8d407

Fecha: 16 de noviembre de 2026, America/Santiago. Datasource: `malaria`.

**HECHO VERIFICADO.** El identificador solicitado `00b8d407-c672-4b68-9814-53c092d034ba` no es una fila de `runs`: es `assessment_attempts.id`, tipo `evaluate`, split **TEST**, estado `verified`. Su identidad es `a981125c-a9b6-4bec-9fb7-2fa52b907147` y su TRAIN es `87b3eff7-e09a-41c8-945d-bf31b3541adb`. La auditoría conserva el UUID pedido como caso principal y utiliza su TRAIN únicamente para reconstruir el entrenamiento y sus descendientes. Evidencia: [consulta de identidad](sql/principal_identity.sql), [captura](evidence/principal_identity.json), [identidad completa](evidence/principal_full_identity.json).

Convenciones: **HECHO VERIFICADO** = código/registro/archivo observado; **CÁLCULO REPRODUCIDO** = cálculo independiente sobre evidencia existente; **INTERPRETACIÓN CIENTÍFICA** = lectura con límites; **HIPÓTESIS** = explicación no demostrada; **PENDIENTE** = no comprobado. La existencia de código, de un registro `verified` y de un archivo con checksum coincidente son tres evidencias diferentes.

## Identidad experimental reconstruida

| Campo | Valor |
|---|---|
| UUID solicitado / naturaleza | 00b8d407-c672-4b68-9814-53c092d034ba / assessment_attempts, EVALUATE TEST |
| TRAIN asociado | 87b3eff7-e09a-41c8-945d-bf31b3541adb |
| Modelo | 998ae52c-0c6b-4673-9c70-70a44caee16a / VGG16 / tensorflow-keras / transfer learning |
| Versión lógica E5 | e8f94b69-1e92-4092-994b-898d6c66dd31, en train_execution_sessions.verification.artifact; no fila model_versions de este TRAIN |
| Campaña | eb7ae3da-c954-4f2f-8d19-0398824089c5 / all 1 |
| Dataset | 3f4058c7-5671-4c2f-a089-d1482d5661f4 |
| Versión dataset | d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 |
| Materialización | e15dc166-1c4b-558e-b77b-727b1783430c |
| Semilla / batch | 47 / 32 |
| Optimizador | SGD LR0.001, momentum0.9, nesterov false, weight_decay null; fine-tuning LR0.0001 |
| Regularización | Dropout0.5 en cabeza; L2=0; VGG16 sin BatchNorm |
| TRAIN estado y duración | completed; 2166.370553 segundos |
| TRAIN fechas UTC | 2026-10-29T13:55:01.710179+00:00 → 2026-10-29T14:31:08.080732+00:00 |
| TEST fechas UTC | 2026-10-29T22:37:35.383443+00:00 → 2026-10-29T22:38:01.478796+00:00; 26.095353 segundos |
| Épocas | máximo100+20; ejecutadas28; mejor1; 13 base +15 fine_tuning |
| Monitor efectivo | val_f2_parasitized max; early stopping paciencia12, min_delta0.0001, restore_best_weights true |
| Política nominal | auc_with_min_recall; sobreescrita para ranking por explicit_monitor; policy_satisfied=false en selección |
| Checkpoint físico | epoch_1.keras; 63.161.620 bytes |
| SHA-256 | b26f6e2c66fd5356028ba41eaee603f0c88a2a925b39cb6b21b0fafd79aa24fa |
| artifact_id en artifacts | 5406dae8-6a82-568c-a0e9-9ecff89d5f4e |
| checkpoint_artifact_id assessment | 3bbb3405-1db1-5811-b4b5-f208f9e64503 = UUIDv5(version_id, e5-selected-checkpoint) |
| Threshold selección / operativo | 0.5 / 0.25116682052612305 calibrado en VAL |
| Dominio score | probability_parasitized, sigmoid; calibrated_score=None; comparación >= |
| Framework observado | Python3.12.13, TF2.17.1, Keras3.15.1, NumPy1.26.4; Apple GPU/Metal1.2.0, Darwin arm64 |

Fuentes: [runs.json](evidence/runs.json), [sesiones](evidence/training_sessions.json), [calibración estructurada](evidence/principal_calibration_record.json), [inventario físico](csv/artifact_inventory.csv). Los timestamps se conservan en UTC para reproducción; en Chile eran 10:55–11:31 para TRAIN y 19:37–19:38 para TEST el 29 de octubre de 2026. La configuración de planificación registra Python3.12.14/SQLAlchemy2.0.52; runtime registra Python3.12.13/SQLAlchemy2.0.53. No mezclar entorno planeado y ejecutado. PYTHONHASHSEED registrado42 y seed de modelo47 son mecanismos distintos; no demuestran por sí solos igualdad bit a bit entre hardware.

## Aprendizaje

**HECHO VERIFICADO:** 28 eventos válidos, sin duplicación del eje en el servicio. Época1 seleccionada por F2 VAL0.9477320516671673 a threshold0.5; no por mínimo loss. TRAIN loss0.3414160 y VAL loss0.1831485 en esa época. Mínimo VAL loss0.138228 en época16; última época28: TRAIN loss0.1397561, VAL loss0.1515374. Configuración pedía100+20, no significa que se ejecutaran120.

**INTERPRETACIÓN CIENTÍFICA:** el ascenso de val_loss desde época16 a28 mientras disminuye TRAIN loss es compatible con deterioro de generalización de pérdida/confianza en ese tramo; no prueba causalidad ni diagnóstico global de sobreajuste. El checkpoint que realmente se evaluó es anterior. La brecha VAL–TRAIN en época1 es negativa y no prueba ausencia de sobreajuste (augmentación/dropout y modos de evaluación difieren). No inferir sobreajuste únicamente de VAL–TEST.

Reproducir: SQL epochs → eventos del TRAIN → módulo curves → CSV [principal_epochs](csv/principal_epochs.csv); cálculos [learning_reproduction](evidence/learning_reproduction.json), figura [aprendizaje](figures/principal_learning.png). `run_checkpoint_policy` está vacío para este TRAIN; la selección sí existe en eventos y sesión. Primera fase fine_tuning en eventos=14; campo `fine_tuning_start_epoch`=13 conserva una frontera/índice distinto.

## Desempeño clínico y umbral

| Métrica TEST | Cálculo independiente |
|---|---|
| count | 2685 |
| tn | 1145 |
| tp | 1270 |
| fp | 223 |
| fn | 47 |
| recall | 0.9643128321943811 |
| specificity | 0.8369883040935673 |
| precision | 0.8506363027461487 |
| accuracy | 0.8994413407821229 |
| f1 | 0.9039145907473309 |
| f2 | 0.9392101760094661 |
| balanced_accuracy | 0.9006505681439743 |
| roc_auc | 0.9788783208337217 |
| pr_auc | 0.9808230427256972 |

**CÁLCULO REPRODUCIDO:** diferencia máxima0 respecto a verification.metrics. [Reproducción](evidence/metric_reproduction.json). NPV calculado en auditoría=0.9605704698; no es indicador expuesto por esta vista. Matriz [figura](figures/principal_confusion.png). Las métricas son celulares y no tienen IC en el reporte principal.

Calibración independiente en memoria sobre los scores VAL del checkpoint seleccionado: 2.683 candidatos únicos incluyendo0/0.5/1; maximización lexicográfica de especificidad, precision, F2, BA y threshold entre los que satisfacen recall≥0.98. Resultado reproduce t=0.25116682052612305, TN1122, FP246, FN26, TP1299, N2693. A t0.5 VAL tenía TN1272, FP96, FN63, TP1262. Se reducen37 FN a costo de150 FP adicionales en VAL. Este contraste no recalibra ni modifica el umbral operativo. [Reproducción](evidence/threshold_reproduction.json).

## Errores y consenso

47 FN y223 FP, 270 errores. 31 errores con score extremo según definición ≥0.9 al predecir1 o ≤0.1 al predecir0; 118 células a distancia≤0.05 del umbral. No son medidas de incertidumbre calibrada. La galería puede recuperar original y abrir Explicabilidad mediante sample_id. La tabla filtra y ordena globalmente antes de paginar.

Con un único TRAIN no hay consenso entre modelos. Referencias secundarias VGG16-Adam47 y DenseNet121-Adam47 se comparan en documento 07, nunca se agregan al resultado principal. Los scores originales quedan en [CSV](csv/principal_predictions.csv), incluidos los47 FN.

## Explicabilidad

Nueve intentos verificados, sobre **tres células únicas** TEST; no equivale a explicar2.685. Grad-CAM, LIME1000 y SHAP1000/clase1 para cada una. SHAP utiliza una célula uninfected TEST distinta como background; su sample_id no sustituye al target. Los18 mapas/overlays existen, se hash-verificaron y sus9 mapas numéricos son finitos. [Estadísticos de mapas](csv/principal_xai_maps.csv). Cobertura3/2685=0.1117318 %. No hay validación morfológica experta acreditada por estas ejecuciones.

| Tipo | Attempt | Split | Estado | N | Método |
|---|---|---|---|---|---|
| evaluate | 811dd584-bb41-453d-b7e9-26bd61c9990a | val | verified | 2693 | — |
| evaluate | 00b8d407-c672-4b68-9814-53c092d034ba | test | verified | 2685 | — |
| explain | 43960c4e-6f7c-4115-894a-0b641028ff7e | test | verified | 1 | gradcam |
| explain | e180e01f-3e4b-43d5-b2c9-b64b1f59e3ba | test | verified | 1 | lime |
| explain | 4aebe1ef-8c03-433c-9e39-b1b27156fe2b | test | verified | 1 | shap |
| explain | 8067df83-eba2-40b1-8f97-ba3629b7d008 | test | verified | 1 | gradcam |
| explain | 25f87c2b-3151-4c7c-99b7-99239b99906f | test | verified | 1 | lime |
| explain | 40847cc1-99b6-4f25-84f7-8751c06c2cc3 | test | verified | 1 | shap |
| represent | d6f269de-ba63-4a17-9df8-3bd2ce1871b2 | test | verified | 2685 | — |
| explain | 4b5fe111-681f-4d68-a36f-4a96c949abd2 | test | verified | 1 | gradcam |
| explain | 87bd4dfc-5f2a-43f8-b6dd-9443bf4dac76 | test | verified | 1 | lime |
| explain | 6eb43d52-05a3-425c-a46b-a1b51a0c1117 | test | verified | 1 | shap |

## Arquitectura

Entrada RGB200×200×3; VGG16 preprocess ImageNet BGR en loader, no aplicar además rescale por intuición. Backbone ImageNet, cinco bloques convolucionales/pooling → GAP512 → Dense 1024 ReLU → Dropout0.5 → Dense1 sigmoid. 15.241.025 parámetros: base526.337 entrenables y14.714.688 congelados; fine-tuning7.605.761 entrenables y7.635.264 congelados. El checkpoint seleccionado es **fase base**, aunque se consulten estados entrenables de fine-tuning en Arquitectura.

Reproducción desde `train_execution_records kind=runtime record_key=configuration` y `normalize_keras`; resultado [architecture.json](evidence/architecture.json), fuentes [runtime_records](evidence/runtime_records.json). Sin inferencia ni deserialización del modelo.

## Representaciones

REPRESENT `d6f269de-ba63-4a17-9df8-3bd2ce1871b2`, misma población/decisión/modelo TEST que el intento solicitado. Embeddings2685×512 float32; PCA2685×2; varianza50; UMAP2685×2. Las cuatro matrices tienen SHA/bytes concordantes y son finitas. Sin normalización L2 en Keras; media de norma91.94138, no equiparar directamente con encode_image_l2 de OpenCLIP.

PCA2 explica39.753147 %, PCA50 explica87.925476 %, 25 componentes alcanzan80 %. PCA se ajustó una sola vez al generar REPRESENT; la auditoría lee sus matrices, no las vuelve a ajustar. [Reproducción numérica](evidence/representation_reproduction.json), [figuras](figures/principal_representations.png). CKA con otro RUN solo aparece como comparación separada en documento 07. No hay clustering aprendido, TCAV ni comparación de todas las capas implementados en este contrato REPRESENT.

## Trazabilidad: cinco pruebas concretas

1. Métrica: intento `00b8d407-c672-4b68-9814-53c092d034ba` → identidad `a981125c-a9b6-4bec-9fb7-2fa52b907147` → verification.metrics.recall y 2.685 assessment_results → 1270/(1270+47). El objeto `evaluations` histórico de TRAIN no es la fuente de ese TEST.
2. Predicción celular: sample `014d8b8e-3397-5ae8-88fd-8cef2a2d6c64`, real0, score0.6909072995185852, pred1 a t0.25116682. `dataset_source_records.id` → clinical_identity `d4b8e72c-782e-570d-a4df-5e6c618b9a35` (`C139P100ThinF`) → assignment TEST de versión d8c0… → imagen `test/uninfected/C139P100ThinF_IMG_20151005_182822_cell_142.png`, SHA `9155ff4224d8b5e413cfaff4e9a70785fd78a2156b9d440c0773e8ca130d3301`.
3. FN: los47 joins reales con fuente/paciente/split están en [principal_sample_lineage.json](evidence/principal_sample_lineage.json). Un FN se selecciona determinísticamente como primera fila label1/pred0 de principal_predictions; su imagen y SHA se verifican en [original_verification](evidence/original_verification.json). No se inventa un frotis físico completo a partir del nombre del crop.
4. Archivo XAI: intento Grad-CAM `4b5fe111-681f-4d68-a36f-4a96c949abd2` → sample014d8… → dos assessment_artifacts map/overlay → paths/hash en inventario → mismo checkpoint y target clase1 de su identidad. sample SHAP background0005c2… es referencia distinta.
5. Representación: mismo sample_id → assessment_results del REPRESENT d6f269… → result.row → fila de embeddings/pca/umap; artefactos poblacionales se registran con sample_id de la primera muestra por contrato, **no significan que solo esa muestra tenga representación**.

Cadena de checkpoint común: sesión TRAIN.verification.artifact.version_id e8f94… → UUIDv5 lógico3bbb… en assessment → path y SHA b26f…; proyección registral artifacts5406… → misma ruta,63.161.620 bytes y hash comprobados. La versión E5 no requiere una fila model_versions nueva en este flujo; tabla vacía para el TRAIN no es pérdida automática de linaje. [malaria_dl_local_project/src/malaria_dl/assessment/lineage.py:25](../../../malaria_dl_local_project/src/malaria_dl/assessment/lineage.py#L25).

## Límites específicos

No se ejecutaron modelos, nuevas explicaciones, representaciones ni calibraciones productivas. No se comprobó una cadena hasta imagen de frotis completo ni registro de paciente clínico asistencial; existe identidad PATIENT de origen del dataset. No se acreditan ROI, conceptos expertos, evaluación clínica externa, presupuesto monetario, consumo eléctrico o IC del principal desde esta UI. No hay que escribir «No implementado» para XAI/REPRESENT: ambos tienen evidencia de ejecución para este caso.

## Evidencia complementaria de archivo y recorridos

**HECHO VERIFICADO:** se inspeccionó `config.json` y `metadata.json` del ZIP Keras del checkpoint elegido, sin cargar el modelo ni deserializar pesos. El manifiesto interno y firmas de capas se conservan en [checkpoint_zip_inspection.json](evidence/checkpoint_zip_inspection.json); la comparación por fase distingue los flags trainable del checkpoint y del ajuste fino. Se inventariaron 28 checkpoints de época presentes en la carpeta del TRAIN; solo el elegido se verificó contra hash registral. Las épocas restantes no sustituyen la selección operativa.

Arquitectura dispone de tres recorridos celulares ya guardados: muestras `29e26d17-5e6d-5fb3-b493-bb9bc4a5a07a`, `a39fc40f-7738-5c90-8dc6-c3b31856b360`, `db9fbbd3-e025-524a-ad04-ba5cde0e2f3d`. Todos citan EVALUATE VAL `811dd584-bb41-453d-b7e9-26bd61c9990a`, el mismo SHA de checkpoint y `consistent=true`, con ocho pasos cada uno. Se verificó lectura del JSON y su hash actual; no se repitió el forward para recertificar consistent. No se presentan como activaciones de las células TEST. [Resumen](evidence/saved_traces_summary.json), [inventario](csv/local_auxiliary_files.csv).

**Versiones XAI/REPRESENT observadas:** LIME0.2.0.1, SHAP0.49.1, sklearn1.9.1, scikit-image0.26.0, umap-learn0.5.12, Pillow12.3.0, matplotlib3.11.2 según identity.code.inference_packages de los respectivos intentos; no todas figuran en el TEST anterior. La fuente es cada ejecución, no la versión actual de una página web.

### Ejemplo FN explícito reproducible

Muestra `028644ea-4c04-5b98-b3fd-45eeef3d76e6` → paciente `e942ac07-b9b2-5ef9-994b-6320a352b354` → `test/parasitized/C144P105ThinF_IMG_20151015_155004_cell_305.png`. Real1, score `0.08094331622123718`, t `0.25116682052612305`, pred0. SHA original `01c9f512c077b70c4254c6377b42277e09b4aa04e5e76df2c4e9638af40fad96` coincide con el archivo leído en original_verification.json. La misma muestra conserva su fila de REPRESENT si se localiza por sample_id en case_related_scores.json; no se obtiene su fila usando el orden de una página UI.
