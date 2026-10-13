# HALLAZGOS B1 — 12 entrenamientos históricos

Estado documental: `HISTORICAL_AUDIT` — evidencia histórica B1; no autoriza entrenamientos ni comparación causal CPU/GPU.

Snapshot de PostgreSQL: `2026-10-04T12:56:54.183938+00:00`. Fuentes: [SQL_B1.md](SQL_B1.md); datos sin redondeo de presentación en los cuatro CSV. Las tablas Markdown redondean sólo para lectura.

## A. Resumen ejecutivo

Se reconstruyó la campaña **Campaña 1**, `b54ea684-1b0c-421d-a4b2-9f12667bd619`, finalizada, para caracterizar duración, aprendizaje y resultados VALIDATION de las 12 combinaciones de `custom_cnn`, `densenet121`, `vgg16` con `adam`, `adamw`, `sgd`, `adadelta`. Una ejecución por combinación y una única semilla **47**: no hay réplicas que permitan estimar variabilidad entre semillas.

Dataset **Malaria Patient Split v1**, versión `1.0.0`, estado `FROZEN`, ID `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`. El contrato registrado informa 27.558 imágenes: 22.180 TRAIN, 2.693 VAL y 2.685 reservadas TEST, agrupadas por paciente (161/20/20 respectivamente). La reconstrucción utilizó las 2.693 predicciones VAL de cada checkpoint: 1.325 parasitized y 1.368 uninfected. Las asignaciones de pacientes son evidencia del contrato persistido, no una nueva auditoría de las imágenes.

Entorno runtime registrado: **MacBook-Pro-de-Julio.local, Darwin, arm64, local_python; Python 3.12.13, TensorFlow 2.17.1, Keras 3.15.1, NumPy 1.26.4**. La CPU exacta, RAM física y número de núcleos no constan en estos registros. La etiqueta `cpu_historical` identifica esta línea base; `gpu_available=false` y `gpu_devices=[]` no certifican el dispositivo que ejecutó cada operación. No hay medición de utilización CPU/GPU ni benchmark Metal.

Se completaron **396 épocas: 263 base y 133 fine-tuning**. La suma de duración de RUNS es **138403.693539 s (38.445470 h)**. Desde `2026-10-02T14:39:10.252544+00:00` hasta `2026-10-04T05:06:36.518014+00:00` transcurrieron **138446.26547 s (38.457296 h)**, incluidos **42.571931 s** entre RUNS. No hay solapamientos temporales entre los 12 RUNS. Desde la creación de la campaña al último término: 148003.634255 s; esta cifra incluye espera previa y no es tiempo de entrenamiento.

La menor duración corresponde a **custom_cnn / adamw** (2644.406622 s, 14 épocas), la mayor a **vgg16 / adadelta** (22565.108516 s, 30 épocas). VGG16 presenta mayor tiempo medio por época que las otras arquitecturas. Ninguna configuración supera el objetivo de sensibilidad **estrictamente > 0,98**, al umbral histórico 0,5. El mayor recall es **0.948679** (vgg16 / sgd), con specificity **0.913743**.

## B. Metodología

Auditoría retrospectiva, descriptiva, sin entrenar, cargar checkpoints, ejecutar inferencia, TEST ni EXPLAIN. PostgreSQL es la fuente de resultados; todos los SELECT finales se ejecutaron en una única transacción `REPEATABLE READ READ ONLY`, terminada con `ROLLBACK`. Q01–Q17 describen la extracción; [report.md](report.md) concentra el procedimiento reproducible y las comprobaciones.

**Selección.** Se identificó la única campaña y se conservaron todos sus miembros, intentos y RUNS. Los 12 son `training/completed`, con intento aceptado y sesión `verified`. No se excluyó ninguna combinación ni se filtró por desempeño clínico. Para métricas finales se exige `evaluations.split='val'` y `evaluation_role='training_validation_final'`; otras fases y eventos de métricas no se mezclan con ese resultado.

**Identificación semántica.** `run_configurations.architecture` y `.optimizer` coinciden en los 12 casos con `campaign_configurations.configuration.model_id` y `.resolved.optimizer.name`, con `runs.execution_parameters.model_configuration_e2.configuration` y con la configuración compilada del runtime (Q04/Q12). `models.architecture` contiene etiquetas descriptivas, como “Custom CNN”; `models.name` coincide con el identificador canónico. El `model_id` JSON es un nombre de arquitectura, mientras `runs.model_id` es un UUID de catálogo. `campaign_members` aporta semilla, posición y hash, no nombres de arquitectura/optimizador. El JOIN de configuración de campaña utiliza **campaign_id + configuration_hash**.

Los hashes de configuración de miembro y RUN son diferentes en los 12 casos: no deben equipararse ni usarse como JOIN entre esas tablas. Se comprobó que el SHA-256 del `run_configurations.canonical_configuration` coincide con su hash y que ese JSON es el `resolved` del RUN; la configuración de ejecución coincide con la de campaña al quitar únicamente la semilla 47 del miembro. Se preservan ambos hashes y snapshots en `runs.csv`.

**Duración.** `wall_seconds = EXTRACT(EPOCH FROM finished_at-started_at)` coincide exactamente con `runs.duration_seconds` en 12/12 casos. Es tiempo de pared del RUN: incluye inicialización, entrenamiento, validación, checkpoints, persistencia y cierre. `seconds_per_epoch = wall_seconds / número de registros kind='epoch'`. Es un promedio amortizado, no tiempo de kernel ni de `model.fit` aislado. Las divisiones se calculan con Decimal de 50 cifras significativas; los numeradores y denominadores se conservan para recuperar precisión arbitraria.

**Épocas y fases.** Se cuentan `train_execution_records(kind='epoch')` por RUN y fase, comprobando unicidad, secuencia global 1…N y local 1…N_fase. Los eventos canónicos `e10_event` no se vuelven a contar como épocas. Los conteos coinciden con los cierres `kind='phase'` y `train_execution_sessions.completion.epochs`. `training_history`, `run_metrics` y `run_checkpoint_policy` están vacíos. En **5/12 RUNS** `runs.completed_epochs=0` contradice la evidencia de épocas; en los otros 7 coincide. `runs.total_epochs`, `best_epoch`, `stopped_epoch` y `fine_tuning_start_epoch` están ausentes en los 12. Se informa la discrepancia sin reparar el histórico.

**EarlyStopping y selección.** Máximo base 100; fine-tuning 0 para Custom CNN y 20 para DenseNet121/VGG16. EarlyStopping activado, paciencia 12, min_delta 0,00001, restauración de mejores pesos. El monitor científico declarado es `val_f2_parasitized`; el callback compilado monitoriza `val_early_stopping_score`. Los índices `best_epoch` y `stopped_epoch` de los cierres de fase son locales y base cero, mientras que `payload.epoch` y `artifacts.metadata.epoch` son globales y base uno. `stopped_epoch=0` en las tres fases que completan 20 épocas significa que no se activó la detención. No se usa ese cero como cero épocas. La selección final se verifica por ID de artefacto, hash, época y evento de evaluación; no se asume que sea la última época ni que el mejor epoch local determine por sí solo el checkpoint final.

**Validación de métricas.** Q08 enlaza `run_clinical_metrics → evaluations → artifacts`; Q17 recupera las predicciones VAL persistidas de la época seleccionada. Se reconstruyeron las 12 matrices de confusión al umbral 0,5 y se recalcularon recall, specificity, F1, F2, ROC-AUC y PR-AUC como **average precision no interpolada**, sin nueva evaluación del modelo. Los 12 conjuntos contienen las mismas identidades y etiquetas VAL. Error absoluto máximo frente al dato publicado: **5.3632491064677406109093255710395155E-16**, menor que 1e-12. Además se cotejaron las métricas clínicas con la época seleccionada. `val_auc`/`val_pr_auc` de Keras (200 umbrales interpolados) no sustituyen los valores clínicos `val_roc_auc_parasitized`/`val_pr_auc_parasitized` ni las métricas finales. No se calcularon intervalos de confianza ni significancia.

## C. Resultados

| Arquitectura | Optimizador | Épocas | Base | FT | Total s | s/época* | Recall | Specificity | F1 | F2 | ROC-AUC | PR-AUC (AP) | Checkpoint / fase |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| custom_cnn | adadelta | 26 | 26 | 0 | 5009.463818 | 192.672 | 0.929057 | 0.979532 | 0.952786 | 0.938405 | 0.990210 | 0.990202 | epoch_14.keras / base |
| custom_cnn | adam | 16 | 16 | 0 | 2966.682787 | 185.418 | 0.898868 | 0.969298 | 0.931196 | 0.911526 | 0.984671 | 0.980174 | epoch_4.keras / base |
| custom_cnn | adamw | 14 | 14 | 0 | 2644.406622 | 188.886 | 0.939623 | 0.958333 | 0.947849 | 0.942896 | 0.986015 | 0.980626 | epoch_2.keras / base |
| custom_cnn | sgd | 31 | 31 | 0 | 5615.894749 | 181.158 | 0.916226 | 0.976608 | 0.944380 | 0.927284 | 0.989231 | 0.985345 | epoch_19.keras / base |
| densenet121 | adadelta | 40 | 21 | 19 | 7810.819420 | 195.270 | 0.932830 | 0.915205 | 0.923422 | 0.929044 | 0.970491 | 0.968836 | epoch_28.keras / fine_tuning |
| densenet121 | adam | 67 | 47 | 20 | 12753.488465 | 190.351 | 0.784151 | 0.956140 | 0.857261 | 0.811846 | 0.957899 | 0.956364 | epoch_35.keras / base |
| densenet121 | adamw | 50 | 30 | 20 | 9587.082939 | 191.742 | 0.784906 | 0.952485 | 0.855967 | 0.811866 | 0.955174 | 0.953579 | epoch_18.keras / base |
| densenet121 | sgd | 42 | 22 | 20 | 7937.861624 | 188.997 | 0.904906 | 0.904971 | 0.903542 | 0.904360 | 0.958598 | 0.957563 | epoch_10.keras / base |
| vgg16 | adadelta | 30 | 17 | 13 | 22565.108516 | 752.170 | 0.946415 | 0.934211 | 0.939678 | 0.943709 | 0.979244 | 0.978639 | epoch_5.keras / base |
| vgg16 | adam | 26 | 13 | 13 | 19955.289508 | 767.511 | 0.933585 | 0.970029 | 0.950442 | 0.940255 | 0.987239 | 0.987785 | epoch_14.keras / fine_tuning |
| vgg16 | adamw | 27 | 13 | 14 | 20981.853366 | 777.106 | 0.934340 | 0.970029 | 0.950845 | 0.940872 | 0.987990 | 0.988810 | epoch_15.keras / fine_tuning |
| vgg16 | sgd | 27 | 13 | 14 | 20575.741725 | 762.065 | 0.948679 | 0.913743 | 0.931111 | 0.941573 | 0.979533 | 0.979349 | epoch_1.keras / base |

Nota: promedio de pared del RUN dividido por épocas observadas. No mide velocidad computacional aislada. UUID originales, checkpoints completos, matrices, valores y procedencia están en `runs.csv`; métricas de cada época en `epochs.csv`.

| Arquitectura | Épocas | Horas RUN acumuladas | s/época ponderados* | Rango recall | Rango specificity |
| --- | --- | --- | --- | --- | --- |
| custom_cnn | 87 | 4.510 | 186.626 | 0.898868–0.939623 | 0.958333–0.979532 |
| densenet121 | 199 | 10.580 | 191.403 | 0.784151–0.932830 | 0.904971–0.956140 |
| vgg16 | 110 | 23.355 | 764.345 | 0.933585–0.948679 | 0.913743–0.970029 |

El menor promedio amortizado es **custom_cnn / sgd**, 181.158 s/época; el mayor es **vgg16 / adamw**, 777.106 s/época. Estos extremos no coinciden necesariamente con los de duración total. Custom CNN/AdamW termina antes principalmente porque ejecuta 14 épocas, frente a 31 de Custom CNN/SGD. No se interpreta esa diferencia como superioridad de velocidad de AdamW.

## D. Hallazgos científicos

### Arquitecturas y optimizadores

Custom CNN acumula 4.510 h; DenseNet121, 10.580 h; VGG16, 23.355 h. Los promedios ponderados son 186.626, 191.403 y 764.345 s/época, respectivamente. DenseNet121 y Custom CNN tienen costos por época cercanos en este registro, pero usan distinto preentrenamiento y régimen de fases; esto no prueba equivalencia de complejidad ni de rendimiento puro. VGG16 presenta aproximadamente 4.10 veces el promedio ponderado de Custom CNN bajo estas configuraciones.

Dentro de Custom CNN, AdamW obtiene el mayor recall y F2, mientras Adadelta obtiene el mayor F1, specificity, ROC-AUC y AP. En DenseNet121, Adadelta supera descriptivamente a los otros optimizadores en recall, F1, F2, ROC-AUC y AP; Adam tiene la mayor specificity. En VGG16, SGD obtiene el mayor recall, Adadelta el mayor F2 y AdamW el mayor F1, ROC-AUC y AP; Adam y AdamW empatan en specificity. No hay un optimizador ganador para todas las métricas y arquitecturas.

Las tasas iniciales también cambian: Adadelta 1 (base/FT), Adam/AdamW 0,0001 y 0,00001, SGD 0,001 y 0,0001. Custom CNN no usa pesos preentrenados; DenseNet121/VGG16 usan ImageNet y configuración de 4 capas para fine-tuning. Batch 64 e imágenes 200×200×3 en todos. Hay augmentation y ReduceLROnPlateau. Por tanto, la comparación caracteriza recetas completas, no un efecto causal aislado del optimizador. Orden fijo de campaña, una semilla, ausencia de réplicas y estado térmico/carga desconocidos limitan las inferencias.

### EarlyStopping, variabilidad de épocas y fine-tuning

Las ejecuciones duran entre 14 y 67 épocas. EarlyStopping se activa en **17 de 20 fases**: las 12 base y 5 de las 8 de fine-tuning. DenseNet121 con Adam, AdamW y SGD consume las 20 épocas de fine-tuning; las otras fases se detienen antes del máximo. En las 17 fases detenidas, el cierre registra 12 épocas entre best y stopped. El ahorro en número de épocas no identifica por sí solo mayor velocidad ni mejor generalización.

Los tres checkpoints finales de fine-tuning son DenseNet121/Adadelta y VGG16/Adam y AdamW. Los otros cinco modelos con fine-tuning conservan un checkpoint base. Para esos cinco, el costo FT no produjo un checkpoint preferido por el criterio registrado; esto no demuestra inutilidad general de fine-tuning. DenseNet121/Adam invierte 67 épocas y 12753.488465 s, pero selecciona época 35 base y recall 0,784151. La mayor duración no garantiza una mejor métrica final.

| Arquitectura | Optimizador | Fase | Épocas / máximo | Best (0-based) | Stopped (0-based) | EarlyStopping | Intervalo fase s | s/época fase* |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| custom_cnn | adadelta | base | 26 / 100 | 13 | 25 | sí | 4985.644 | 191.756 |
| custom_cnn | adam | base | 16 / 100 | 3 | 15 | sí | 2944.362 | 184.023 |
| custom_cnn | adamw | base | 14 / 100 | 1 | 13 | sí | 2621.985 | 187.285 |
| custom_cnn | sgd | base | 31 / 100 | 18 | 30 | sí | 5594.133 | 180.456 |
| densenet121 | adadelta | base | 21 / 100 | 8 | 20 | sí | 4102.885 | 195.375 |
| densenet121 | adadelta | fine_tuning | 19 / 20 | 6 | 18 | sí | 3666.488 | 192.973 |
| densenet121 | adam | base | 47 / 100 | 34 | 46 | sí | 8890.279 | 189.155 |
| densenet121 | adam | fine_tuning | 20 / 20 | 19 | 0 | no; límite | 3821.867 | 191.093 |
| densenet121 | adamw | base | 30 / 100 | 17 | 29 | sí | 5743.786 | 191.460 |
| densenet121 | adamw | fine_tuning | 20 / 20 | 19 | 0 | no; límite | 3804.666 | 190.233 |
| densenet121 | sgd | base | 22 / 100 | 9 | 21 | sí | 4130.568 | 187.753 |
| densenet121 | sgd | fine_tuning | 20 / 20 | 19 | 0 | no; límite | 3769.760 | 188.488 |
| vgg16 | adadelta | base | 17 / 100 | 4 | 16 | sí | 11904.622 | 700.272 |
| vgg16 | adadelta | fine_tuning | 13 / 20 | 0 | 12 | sí | 10576.106 | 813.547 |
| vgg16 | adam | base | 13 / 100 | 0 | 12 | sí | 9479.726 | 729.210 |
| vgg16 | adam | fine_tuning | 13 / 20 | 0 | 12 | sí | 10395.173 | 799.629 |
| vgg16 | adamw | base | 13 / 100 | 0 | 12 | sí | 9550.765 | 734.674 |
| vgg16 | adamw | fine_tuning | 14 / 20 | 1 | 13 | sí | 11350.195 | 810.728 |
| vgg16 | sgd | base | 13 / 100 | 0 | 12 | sí | 9384.465 | 721.882 |
| vgg16 | sgd | fine_tuning | 14 / 20 | 1 | 13 | sí | 11112.534 | 793.752 |

Nota: intervalos entre `phase_started` y `phase_completed`; incluyen entrenamiento, validación, callbacks y persistencia dentro de la fase, pero no toda la inicialización/cierre del RUN. Los tiempos FT no deben extrapolarse a base: cambian capas entrenables y se reinicia el estado del optimizador, según Q12.

### Tiempo y objetivo clínico

El mayor recall (vgg16 / sgd, 0.948679) coexiste con specificity 0.913743; el mayor F2 corresponde a vgg16 / adadelta (0.943709) y el mayor F1 a custom_cnn / adadelta (0.952786). La diferencia entre objetivos impide declarar un único mejor modelo sin una regla explícita.

**0/12 cumplen sensibilidad >0,98** al umbral 0,5; con 1.325 positivos se necesitarían al menos 1.299 verdaderos positivos (como máximo 26 falsos negativos), frente a 1257 TP y 68 FN en el mejor recall observado. El umbral no se recalibró. La campaña registra `clinical_objective_met=false` en los 12, aunque `selection.policy_satisfied=true`: ese flag técnico no acredita sensibilidad objetivo. No se afirma que otro umbral tampoco pudiera alcanzarla; eso exigiría otro análisis de selección, con su compromiso en specificity.

Son resultados exploratorios en VAL, reutilizada para EarlyStopping, selección y comparación, con posible optimismo por selección. No constituyen validación clínica externa ni desempeño confirmado en TEST. Las células del mismo paciente no son réplicas independientes y 12 configuraciones no equivalen a 12 réplicas del mismo experimento.

## E. Hallazgos técnicos

### Proceso local y costo observado

La evidencia runtime atribuye las 12 ejecuciones al mismo host local Darwin/arm64. La campaña registra Python 3.12.14/SQLAlchemy 2.0.52, pero el runtime informa **3.12.13/2.0.53**; también difieren hashes de código y `git_commit` (nulo en campaña, `8411be7e71944370d017c96cc277e2b844c3de6e` en runtime). No se sustituyó el entorno ejecutado por el declarado. Los campos planos de versión/plataforma de `runs` son nulos: se conservó la procedencia JSON explícita.

El costo medible es 38.445470 horas de pared acumuladas. No hay watts, kWh, tarifa, tiempo CPU de proceso ni GPU activo: no se puede calcular costo energético o monetario. Los 396 artefactos por época suman **16110910533 bytes** declarados; los 12 seleccionados suman **510240359 bytes**. Son tamaños registrados, no medición del espacio físico actual ni prueba de que todos esos archivos sigan disponibles.

### Validación, checkpoints y límites de temporización

Hay 396 eventos de epoch, artifact_prepared, artifact_created, selection y predictions, además de 20 aperturas y 20 cierres de fase. El código histórico del commit registrado (`execution/train.py`, `PersistEpoch.on_epoch_end`) persiste la época, guarda el checkpoint, selecciona y recoge de nuevo predicciones VAL. Es consistente con la secuencia observada; no se usaron los cambios locales sin confirmar como prueba de comportamiento histórico.

Los intervalos **artifact_prepared → artifact_created** suman **71.878033 s** (0.052% de la suma de RUNS). Incluyen serialización/guardado, identidad de archivo y envío/persistencia entre las marcas; no aíslan escritura a disco. Los intervalos **selection_completed → predictions_completed** suman **11093.763624 s** (8.016%). Incluyen la recolección adicional de predicciones VAL y persistencia posterior, pero **no toda la validación**: la validación de fit y el callback clínico ocurren antes del evento epoch. Las marcas proceden del reloj del emisor, no de un profiler monotónico. Se conservan los endpoints y diferencias por época en `epochs.csv`; no se atribuye el residual a entrenamiento puro ni se suman intervalos solapados para estimar overhead total.

### Persistencia, trazabilidad e instrumentación

La cadena miembro → intento aceptado → RUN → evaluación VAL → checkpoint es íntegra en las comprobaciones de Q14. Se verificaron las 12 combinaciones únicas y las 396 épocas sin duplicar la representación legacy/canónica. `artifacts` cataloga 12 checkpoints seleccionados; `train_execution_records(kind='artifact')` conserva evidencia de los 396. `artifacts.csv` contiene 396 filas, con el ID de catálogo sólo cuando existe (12); no se inventan IDs para el resto.

La cobertura incompleta de proyecciones (`completed_epochs`, tablas vacías, campos nulos) obliga a reconstruir resultados desde eventos y sesiones. `gpu_available=false` y `gpu_devices=[]` no incluyen método de detección ni trazas de colocación de operaciones. Los 12 RUNS carecen de `peak_cpu_memory_bytes` y `peak_gpu_memory_bytes`; tampoco hay uso de CPU/GPU, RAM máxima acreditada, temperaturas, energía ni duración de batch. No se certifica uso exclusivo de CPU ni ausencia efectiva de Metal con estos registros.

## F. Conclusiones

### Hallazgos demostrados

- Existen las 12 configuraciones esperadas, con una semilla 47, 396 épocas reconciliadas y 12 evaluaciones finales VAL trazables a su checkpoint.
- Las duraciones almacenadas coinciden exactamente con inicio/término. La suma es 138403.693539 s; el intervalo global incluye 42.571931 s entre ejecuciones.
- Se verificaron las seis métricas solicitadas desde scores históricos; 0/12 alcanzan sensibilidad estrictamente >0,98 al umbral 0,5.
- Se documentaron 17 fases detenidas por EarlyStopping, tres fases FT agotadas y sólo tres checkpoints finales FT.
- VGG16 presenta mayor costo amortizado por época en estas ejecuciones; cinco proyecciones de épocas completadas son inconsistentes con sus registros fuente.

### Inferencias razonables

- La distinta cantidad de épocas explica parte importante de las diferencias de duración total; el régimen FT y la arquitectura probablemente también contribuyen, sin aislar efectos.
- Guardar un checkpoint y persistir predicciones cada época añade costo observable; su impacto total requiere instrumentación dedicada.
- El runtime local arm64 y los flags sin GPU son compatibles con una línea base CPU, pero no suficientes para certificarla.

### Aspectos no demostrados

No se ha demostrado aceleración Metal, utilización efectiva de CPU/GPU, efecto causal de arquitectura/optimizador, consumo energético, significancia estadística, estabilidad entre semillas, mejora general por fine-tuning ni desempeño clínico fuera de VAL. Tampoco se revalidó la integridad física de checkpoints y dataset ni la equivalencia temporal del entorno de campaña y ejecución.

### Datos necesarios para la comparación GPU Metal

Conservar UUID/hashes de dataset, población y configuración, arquitectura/optimizador, semilla, versiones, augmentation, precisión numérica, batch, preprocesamiento, política de checkpoint y EarlyStopping. Registrar chip/núcleos/RAM, macOS, TensorFlow y tensorflow-metal, dispositivos visibles y colocación efectiva, threads, carga concurrente, temperatura, memoria y energía. Usar tiempos monotónicos para carga/preprocesamiento, entrenamiento por batch/época, validación, checkpoints, persistencia e inicio/cierre; separar calentamiento y sincronización del dispositivo.

La comparación de **velocidad** necesita presupuestos y fases equivalentes, calentamiento y repeticiones con orden alternado; la comparación de **tiempo hasta criterio** debe mantener la política y reportar cantidad de épocas/métricas, pues Metal puede cambiar trayectorias numéricas. Calcular speedup = tiempo_CPU / tiempo_Metal sólo con trabajos equivalentes y dispositivo acreditado, separando base y FT, y mostrar dispersión. Mantener TEST reservado según el protocolo. Este B1 sirve como referencia histórica reproducible, con limitación explícita de certificación CPU; puede requerir una línea base CPU futura instrumentada para una comparación controlada. No se inició ninguna de esas ejecuciones.
