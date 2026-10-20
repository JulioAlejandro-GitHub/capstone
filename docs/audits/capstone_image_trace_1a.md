# CAPSTONE-IMAGE-TRACE.1A — Auditoría de cargadores y persistencia de imágenes

Fecha: 2026-10-20. Alcance: inspección estática de los flujos operativos F1–F4. Única escritura: este documento. No se ejecutaron TRAIN, EVALUATE, pruebas con efectos secundarios, instalaciones, SQL, migraciones, commit ni push. No se inspeccionó la generación de particiones ni se recorrieron imágenes.

## Dictamen y alcance de la evidencia

El TRAIN operativo usa `execution/train.py`, no el `training/trainer.py` que conserva las llamadas históricas a `record_run_dataset_images`. El cargador entrega solamente imágenes y etiquetas a Keras: no transporta identidad por batch. No existe observación individual persistida de la optimización ni de la validación interna de `fit`.

Las predicciones VAL de `train_execution_records.payload.samples` proceden de una **pasada adicional** al terminar cada época. Hay otra pasada adicional para métricas clínicas y otra al finalizar TRAIN con el checkpoint seleccionado. Las muestras persistidas no son un registro del consumo interno de `fit`.

EVALUATE VAL y TEST comparten selección, cargador e inserción por intento. `assessment_results` acredita resultados por muestra y permite cobertura sobre la población declarada. No cuenta inferencias que terminaron pero cuyo resultado no llegó a persistirse. No hay TTA en este recorrido.

Se acepta como evidencia externa aportada por el solicitante que `run_dataset_images` está vacía y que existen registros VAL por época y resultados EVALUATE VAL/TEST. **No se hizo una nueva consulta a PostgreSQL**: no se atribuyen cantidades, identificadores de ejecuciones ni estados concretos adicionales. El esquema se contrastó con el baseline versionado; no se afirma que éste sustituya una inspección del catálogo efectivo antes de implementar TRACE.1B. La desconexión del productor explica la ausencia de filas en las entradas actuales, pero no demuestra toda la historia causal de la tabla.

En las referencias siguientes, `M/` significa `malaria_dl_local_project/src/malaria_dl/`; las líneas corresponden al checkout auditado. Los estados acreditan contratos y evidencias disponibles, no la ejecución exitosa de cualquier RUN arbitrario.

## A. Mapa de ejecución

| Flujo | Punto de entrada confirmado | Cargador / selección | Ruta efectiva | Iterador y operación | Persistencia |
|---|---|---|---|---|---|
| F1 TRAIN, optimización | `malaria_dl_local_project/src/train.py:2` → `M/execution/operations.py:44`, `standalone` → `M/execution/train.py:37`; campañas: `M/execution/campaign.py:136` lanza worker → `M/execution/worker.py:44`; agente local: `M/local_execution/worker.py:17` | `make_image_dataset_from_directory`, `M/data/loaders.py:367`; enumera Keras por directorio/clases | `local_dataset_root(session['dataset']['dataset_root']) / 'train'`, `M/execution/train.py:78` | `tf.data` preprocesado → `model.fit(datasets['train'])`, línea 246; paso de entrenamiento Keras con optimizador compilado | Métricas por época, configuración, fases y checkpoints en `train_execution_records`; no consumo individual TRAIN |
| F2 TRAIN, VAL interna | Las mismas entradas y la misma invocación a `train` | Mismo cargador, `shuffle=False`, sin augmentation | Mismo root / `val`, líneas 79–96 | `validation_data=datasets['val']`, línea 248; paso de evaluación de Keras, sin optimización | `val_*` en registro `epoch`; `predictions` es otra pasada y no certifica directamente este iterador |
| F3 EVALUATE VAL | `malaria_dl_local_project/src/evaluate.py:3` → `M/assessment/cli.py:55,78` → `prepare`, `run`, `execute_reserved` | `lineage.dataset_samples`, `M/assessment/lineage.py:151`; selección SQL de identidades → `KerasRuntime.images` | `local_dataset_root(identity.dataset.dataset_root) / sample.relative_path`, `M/assessment/runtime.py:22,38` | Lista ordenada de muestras, slices de `batch_size` → `runtime.predict(batch)` → `model(..., training=False)` | `assessment_identities`, `assessment_attempts`, `assessment_results`; verificación de población y métricas |
| F4 EVALUATE TEST | `malaria_dl_local_project/src/test.py:2` → misma CLI, `kind='test'` | Exactamente el mismo selector/cargador de F3, con split TEST | Mismo cálculo de ruta, `relative_path` comienza con `test` | Mismo bucle y misma inferencia de F3 | Mismas tablas; propósito `final`, protocolo TEST y métricas TEST adicionales |

Otras entradas: `M/training/cli.py:377` dirige al mismo `standalone`. `M/evaluation/evaluator.py:199` delega en la CLI de assessments. La API de campañas configura/consulta y remite a la CLI (`backend_api/app/routes/campaigns.py:1`); no debe suponerse que llama al entrenador histórico. El transporte local `M/local_execution/transport.py:62` envía los mismos registros por HTTP. `backend_api/app/repositories/assessments.py:11,32,42` consulta identidades, intentos y resultados; el worker HTTP de `explain_worker.py` es EXPLAIN y no constituye una entrada adicional de EVALUATE auditada aquí.

### F1: construcción, batches y punto de consumo

1. `standalone` verifica el dataset gobernado para TRAIN/VAL (`M/execution/train.py:338` en adelante); campañas/agente suministran una sesión con snapshot. La resolución del root traduce prefijos Docker/host al montaje local, no usa automáticamente una carpeta genérica `data/train` (`M/data/governed_dataset.py:262`, `local_dataset_root`). La ruta absoluta concreta depende de la sesión y del entorno; no puede fijarse a partir del repositorio solamente.
2. El wrapper de Keras infiere etiquetas con `CLASS_NAMES`, RGB, tamaño del contrato, interpolación bilinear y batch configurado. TRAIN tiene shuffle y seed; VAL no. Keras enumera los archivos físicos: la población efectiva se deriva de esa enumeración, cuya consistencia con el snapshot se verifica operativamente, no de insertar todas las filas de un registro histórico.
3. `preprocess_physical_dataset` (`M/data/loaders.py:391`) normaliza etiquetas, aplica preprocessing y, si corresponde, augmentation mediante `map(..., AUTOTUNE)`; termina con `prefetch(AUTOTUNE)`. VGG16 recibe augmentation antes de preprocessing; otros modos después. `build_augmentation`, línea 487, contiene flip, rotación, traslación, zoom y contraste. Una transformación no crea otra identidad de muestra ni demuestra una segunda optimización.
4. En esta cadena no hay `.repeat()`, `.cache()`, generador Python, `Sequence`, `flow_from_directory`, ni rebatching explícito. No se pasan `steps_per_epoch`, `validation_steps`, `validation_freq` ni `drop_remainder`. Se usa el recorrido finito/default de Keras y se espera conservar el último batch incompleto. Son propiedades de configuración; no son mediciones del número ejecutado. No confundir con las funciones TFDS/otros loaders existentes en el mismo archivo.
5. `compile_phase` (`M/models/adapters.py:92`) configura capas entrenables y optimizador por fase. `model.fit` delega la actualización de pesos al entrenamiento Keras; el repositorio no añade un `train_step` que registre IDs ni un callback que confirme muestras por batch. La confirmación adecuada sería después de completar el paso de optimización, con las identidades del batch realmente recibido. En el estado actual ese punto no se observa individualmente.
6. `raw.file_paths` sólo se conserva para VAL (líneas 87–91). Incluso conservarlo para TRAIN no reconstruiría por sí solo la permutación efectiva ni qué batches terminaron. Los elementos que llegan a `fit` son pares `(images, labels)`, sin `image_id` ni `sample_id`.
7. Hay fases `base` y opcional `fine_tuning`, cada una con `fit` propio (líneas 209–252). Época global = offset acumulado + época local + 1. Early Stopping usa `val_early_stopping_score`; puede restaurar pesos según configuración. Restore no revierte el consumo ya ocurrido. Una interrupción puede dejar una época parcialmente optimizada sin registro `epoch`.

### F2: cuatro usos distintos de VAL dentro de TRAIN

| Operación | Punto real | Momento | Evidencia y límites |
|---|---|---|---|
| Validación interna Keras | `fit(validation_data=...)`, `M/execution/train.py:246` | En épocas que alcanzan validación, frecuencia default al no especificar otra | Métricas Keras en logs; no IDs/batches consumidos |
| Métricas clínicas adicionales | `ClinicalValidationMetricsCallback.on_epoch_end`, `M/training/checkpoint_policy.py:550` | Primer callback de cierre de cada época | `collect_predictions` recorre VAL y genera métricas `val_f2_*`, recall, specificity, collapse y score de selección/parada; no persiste allí predicción individual |
| Predicciones individuales por época | `PersistEpoch.on_epoch_end`, `M/execution/train.py:146,192` | Después de métricas clínicas, EarlyStopping, ReduceLROnPlateau, registro de época y guardado de checkpoint/selección | `kind='predictions'`, fase, clave época local, `payload.epoch` global, `role='val'`, `samples=[sample,label,score]` |
| Predicción del checkpoint seleccionado | `M/execution/train.py:285–305` | Después de todas las fases, carga checkpoint seleccionado y recorre VAL | `kind='calibration', phase='val', key='selected'`, checkpoint_epoch y samples; la inferencia ocurre incluso si la calibración está deshabilitada |

`collect_predictions` (`M/evaluation/clinical_metrics.py:430`) itera todos los batches y llama a `model.predict(images, verbose=0)` para cada uno; convierte resultados a numpy y recoge etiquetas. Esa conversión y retorno confirman inferencia, no sólo lectura. PersistEpoch exige `len(scores)==len(sample_paths)` y guarda todos los pares, sin muestreo ni límite. El verificador `M/execution/artifacts.py:56–65` exige cardinalidad VAL esperada e identidades de ruta distintas por época. No compara allí cada identidad contra el manifiesto de asignaciones: es una comprobación de cantidad/unicidad, además del contrato del loader.

**Equivalencia de población:** los tres recorridos por época reciben exactamente el mismo objeto `datasets['val']`, finito, sin shuffle, augmentation, repeat ni límite de steps. Bajo archivos estables y ejecución completa, el código sustenta la misma población prevista y el orden para asociar `file_paths` con predicciones. No son las mismas ocurrencias de consumo. Un registro persistido acredita la pasada de PersistEpoch; no es un log individual de `test_step` de Keras. Interrupciones entre pasadas rompen cualquier equivalencia de consumo completado.

**Equivalencia de métricas/modelo:** `val_loss`/métricas compiladas provienen de `fit`; las métricas clínicas `val_*` se agregan desde otra pasada y alimentan EarlyStopping y selección. No hay garantía general de igualdad exacta de scores entre pasadas o de snapshot de pesos en una época de parada: depende del comportamiento de restauración de EarlyStopping de la versión Keras usada. El callback de persistencia va después de EarlyStopping. No atribuir automáticamente las predicciones al estado que produjo todos los logs. El runtime/configuración persistidos permiten contextualizar la versión; esta auditoría no ejecutó Keras.

Si se completan E épocas y la pasada final, el código programa **3E+1 participaciones VAL por imagen** (E internas, E clínicas, E persistidas y una final). Es un recuento derivado del recorrido, no un contador observado universal. Los samples persistidos permiten contar E+1 ocurrencias acreditadas de las pasadas que guardan resultados, verificando fase/época/registro y deduplicando reenvíos; no permiten sumar automáticamente todas las demás ni usar E planificadas tras Early Stopping.

### F3/F4: selección, checkpoint, inferencia y fallos

`assessment/cli.py:82` fija VAL/development para EVALUATE y TEST/final para TEST. El protocolo `exec1` fija split, propósito y umbrales permitidos; `contracts.validate_split_protocol` (línea 88) exige esa coherencia. La configuración persistida TRAIN resuelve seed y batch cuando no se proporcionan (`service.inference_options`, línea 60); puede existir perfil de operación. TEST agrega F1, balanced accuracy, ROC AUC y PR AUC en `contracts.verify_rows:205`; el cargador y la persistencia no cambian.

`lineage.resolve:24` exige TRAIN verificado, revalida registros/checkpoint y liga training_run_id, model_version_id, checkpoint_artifact_id, hash, bytes, contrato de entrada y época. El fallback histórico exige artefacto registrado y procedencia completa; no elige el último archivo de una carpeta.

`lineage.dataset_samples:151` hereda versión/materialización del TRAIN, verifica sólo el split solicitado y obtiene registros mediante una consulta conjunta (`M/data/sample_repository.py:30`). Construye `sample_id=source_record_id`, paciente, etiqueta, split, ruta materializada y SHA-256. Maneja nombres colisionantes mediante `materialized_relative_path`; verifica hash y cantidad contra snapshot. **sample_id no es image_id de dataset_split_images.** `contracts.identity:108` ordena por sample_id y rechaza identidades duplicadas. EVALUATE selecciona toda la población del split: las opciones de limitar targets pertenecen a EXPLAIN.

`runtime.images:27` comprueba autorización, split, confinamiento de ruta, archivo no symlink y hash; decodifica RGB, resize bilinear y preprocessing. Es carga/preparación, todavía no inferencia. `runtime.predict:57` llama al modelo con `training=False` y convierte su salida a numpy; la respuesta válida confirma inferencia del batch. `service.execute_reserved:289` recorre slices incluyendo el último incompleto, valida scores y escribe cada batch. No hay tf.data, prefetch, caché, augmentation, repetición ni TTA en este recorrido. El archivo `inference/tta.py` existe, pero no es llamado aquí; no inferir TTA de su existencia.

`reserve_execution` agrega execution_id nuevo y reserva identidad/intento (`service.py:272`). `AssessmentRepository.reserve:22` liga intento a identidad, owner, host, pid y ordinal. No reutilizar RUN como clave de intento ni asumir que ordinal crece globalmente entre todas las ejecuciones: se calcula dentro de una identidad.

`write_batch` (`repository.py:123`) usa una transacción por batch, comprueba owner/estado y acepta replay sólo si el resultado existente es idéntico. PK `(attempt_id,sample_id)` en `alembic_v2/baseline/05_keys.sql:14`. Esto evita duplicación de resultados, **no mide cuántas veces se invocó inferencia**. El bucle normal predice una vez por muestra; repetir ejecución genera otro intento/identidad. La recuperación marca el intento interrumpido y pide reiniciar completo (`repository.recover:197`), no completar sólo las filas faltantes.

`service.verify:211` revalida checkpoint, filas y artefactos. EVALUATE exige **cero assessment_artifacts**; estos artefactos son para EXPLAIN. `contracts.verify_rows:205` exige coincidencia exacta del conjunto esperado, cardinalidad y reconstrucción de cada resultado; calcula hash y métricas. Después se persiste `verified` y se relee el estado. El vínculo de muestra está en payload/clave de resultado y manifiesto JSON de identidad; el baseline no declara una FK sample_id → dataset_split_images.

Si falla después de inferir pero antes del commit, el batch procesado no tiene resultados durables. Si falla en un batch posterior, quedan los anteriores. `execute_reserved` intenta marcar `failed`; si ese guardado también falla, conserva el error y no acredita la transición. Un proceso muerto puede quedar `active` hasta recuperación. Cero filas no demuestra cero inferencias. Un intento failed puede incluso tener todos los resultados y fallar en la verificación final: distinguir cobertura de resultados de verificación integral.

## B. Matriz de evidencia

`ACREDITADO` se refiere a evidencia disponible bajo el contrato y, para cobertura completa EVALUATE, a un intento cuya verificación se haya completado. `PARCIAL` exige conservar las limitaciones descritas; no significa cobertura de 100%.

| Evidencia | TRAIN optimización | VAL interna | EVALUATE VAL | EVALUATE TEST |
|---|---|---|---|---|
| Ruta efectiva | ACREDITADO: sesión + root local + train (`execution/train:78`) | ACREDITADO: mismo root + val (`train:79`) | ACREDITADO: identidad/ruta + resolución runtime (`assessment/runtime:22–38`) | ACREDITADO: mismo contrato con TEST (`assessment/cli:82`) |
| Identidad de imagen consumida | NO ACREDITADO: `(images,labels)` sin ID (`data/loaders:391`) | PARCIAL: file_paths + samples de otra pasada (`train:87,192`) | ACREDITADO: sample_id, hash/ruta en identidad, resultado por muestra (`lineage:151`, `contracts:166`) | ACREDITADO: mismo mecanismo (`lineage:151`, `contracts:166`) |
| Imagen procesada | NO ACREDITADO individualmente: fit sin recibo de paso (`train:246`) | PARCIAL: logs agregados y pasada adicional; no recibo de validación interna (`checkpoint_policy:550`, `train:192`) | ACREDITADO para cada resultado válido persistido: predict antes de write_batch (`service:308`) | ACREDITADO con igual límite (`service:308`) |
| Cantidad única | NO ACREDITADO consumida: counts snapshot son previstos (`train:78,246`) | PARCIAL: únicas de predicciones, no observación interna (`execution/artifacts:61`) | ACREDITADO para resultados por intento (`contracts:205`, PK citada) | ACREDITADO para resultados por intento (mismas referencias) |
| Frecuencia real total | NO ACREDITADO: no captura por paso (`train:246`) | PARCIAL: épocas/pasadas persistidas; otras inferidas (`train:192,285`) | PARCIAL: una pasada normal; ventana inferencia→commit y replay (`service:308`, `repository:123`) | PARCIAL: misma ventana (`service:308`, `repository:123`) |
| Época o intento | PARCIAL: fase/época de métricas, no por imagen (`train:146`) | PARCIAL: época de predicción adicional y logs (`train:146,192`) | ACREDITADO: attempt_id → identity → TRAIN (`repository:22,125`) | ACREDITADO: mismo contrato (`repository:22,125`) |
| Cobertura consumida | NO ACREDITADO individualmente (`train:246`) | PARCIAL: misma población prevista; sólo pasada adicional acreditada por muestras (`train:192`, `artifacts:61`) | ACREDITADO sobre resultados de intento verificado; PARCIAL si falla (`service:211`, `contracts:205`) | ACREDITADO/PARCIAL con idéntica condición (`service:211`, `contracts:205`) |

Época en F3/F4 y assessment_attempt en F1/F2: **NO APLICA** como eje de esa operación. No confundir campaign_attempt de TRAIN con assessment_attempt; el primero puede contextualizar el RUN, el segundo identifica la evaluación independiente.

### Contadores: qué puede publicarse ahora y qué falta

| Contador | Definición operativa sin equivalencias falsas | Disponibilidad |
|---|---|---|
| Previstas | Cardinalidad de manifiesto seleccionado por versión/materialización/split; contrastar TRAIN con enumeración efectiva | Snapshot TRAIN; `identity.samples` EVALUATE. No acredita consumo |
| Únicas procesadas | DISTINCT identidad entre recibos de operación completada | TRAIN/F2 ausente; pasadas VAL persistidas sí; EVALUATE DISTINCT sample_id por intento en resultados válidos, cota inferior si incompleto |
| Procesamientos totales | Suma de multiplicidades de recibos, sin contar replay de transporte | Ausente para optimización/VAL interna; resultados EVALUATE sólo equivalen bajo recorrido normal sin inferencias no persistidas ni reinvocación |
| Por época | Recibos agrupados por fase, época global y local | Sólo evidencia adicional VAL actual; métricas epoch no sustituyen recibos |
| Por propósito | Separar optimización, validación Keras, métricas clínicas, predicción de auditoría, calibración y evaluación independiente | Los registros existentes permiten separar parcialmente; no sumar todos como “validation_data” |
| Por intento | Agregar dentro de assessment_attempt; TRAIN usar RUN/sesión y campaign_attempt cuando exista | EVALUATE ya lo resuelve; no agregar sólo por training_run_id |
| Cobertura | `|IDs confirmados ∩ IDs previstos| / |IDs previstos|`, además reportar extras y duplicados | EVALUATE verificado acredita 1 para resultados del intento; fallido acredita fracción inferior, no ausencia de consumo fuera de ella. TRAIN/F2 desconocida, no 0 |

Un recuento observado de resultados es exacto para **resultados persistidos**; puede ser una cota inferior de **procesamientos**. `n_batches × batch_size` sobrecuenta el batch final; `N × max_epochs` ignora EarlyStopping e interrupciones. Un porcentaje debe indicar universo, propósito, intento/época y nivel de evidencia.

## C. Análisis de run_dataset_images

### Productores y consumidores

Existe productor: `M/persistence/tracking.py:1386`, `record_run_dataset_images`, y repositorio SQL `M/persistence/run_repository.py:1486`, `log_run_dataset_images`. El servicio registra/busca imágenes físicas y construye filas; el SQL hace INSERT/UPSERT por `(run_id,image_id,usage_context)`, sobrescribe índices/flags y fusiona metadata. Itera filas dentro de una transacción, no es un contador de eventos.

Llamadores localizados: `M/training/trainer.py:1854–1874` al finalizar el recorrido histórico con `track_db` y contexto; `M/feature_engineering/svm_features.py:231,239`; `M/inference/tta.py:242`. Estos últimos no son los cuatro recorridos operativos solicitados. `src/train.py` conserva alias de importación hacia trainer para compatibilidad, pero su rama ejecutable llama `execution.operations`. La presencia de tests/imports del alias no demuestra su uso en campañas actuales.

El flujo actual `execution/train.train` usa `repository.put` y event emitter; `assessment.execute_reserved` usa `write_batch`. Ninguno invoca el productor de `run_dataset_images`. Ésta es una causa verificable de que **ejecutar esas entradas no pueble esa tabla**. No se puede demostrar sin historial SQL que cada ausencia anterior obedeciera a la misma causa. Además, el productor histórico omite contextos sin RUN, fuentes no físicas o registro fallido (`tracking:1397–1438`), y el repositorio captura errores devolviendo cero (`run_repository:1550`). No afirmar que uno de estos fallos ocurrió sin evidencia.

Consumidores: `backend_api/app/repositories/scientific_results.py:183` expone `count(*)` como `consumed_images`; con tabla vacía, ese 0 sólo significa ausencia de filas en este índice, no cero entrenamiento. `malaria_dl_local_project/db/init/018_visual_audit_views.sql:386,429` consulta/vincula la tabla. Los consumidores de predicciones VAL usan `train_execution_records` (`scientific_results.py:212`), de forma independiente.

### Identidad y costo de resolución

`data.registry.load_registered_split_images:562` ya permite una consulta masiva por dataset_dir y splits, ordenada por clase/ruta, con image_id, relative_path y filename. `tracking.build_run_dataset_image_rows:1340` calcula sample_index/batch_index sobre ese orden de registro, **no sobre el shuffle consumido**. Reusar esos índices como posiciones reales de TRAIN sería incorrecto.

Los cargadores F1/F2 no retienen image_id. F3/F4 sí retienen sample_id gobernado, que es otro UUID. El baseline de `dataset_split_images` incluye dataset_version_id y dataset_materialization_id (`alembic_v2/baseline/03_tables.sql:62`), pero no demuestra una correspondencia poblada y completa con source_record_id. En TRACE.1B debe leerse de una vez el manifiesto gobernado y el registro de imágenes de esa versión/materialización, unir por ruta materializada normalizada y comprobar unicidad, clase y hash. Si sólo hay dataset_dir, normalizar el prefijo host/Docker y exigir pertenencia al snapshot; jamás unir sólo por filename ni intercambiar UUIDs. Si falta registro o hay ambigüedad, declarar identidad no resuelta; no llamar silenciosamente al registrador histórico dentro del entrenamiento. No hace falta una consulta por imagen.

### Columnas y restricciones

La UNIQUE actual es **adecuada para un índice de imágenes únicas por RUN y propósito**. No debe eliminarse: permite asociar una imagen a train/validation separadamente. La FK exige image_id real de dataset_split_images; no acepta conceptualmente sample_id de source_records como sustituto aunque ambos sean UUID.

`usage_context` admite train, validation, evaluation, explainability, tta, ensemble, svm_features e inference; baseline `06_constraints.sql:664`. No admite nombres nuevos de subpropósito sin extender contrato. `_usage_flags` (`tracking:1331`) pone training si contexto=train **o split=train**, validation si contexto=validation **o split=val**, test si split=test. Esos flags mezclan población y propósito: una inferencia sobre TRAIN podría figurar used_for_training. No son prueba de optimización.

Sin alterar tabla se pueden guardar identidad/ruta/clase, propósito principal y metadata de procedencia, además de una proyección agregada de consumo confirmado. `batch_index`, `sample_index`, `created_at` únicos no representan historia por época, múltiples batches ni tiempo de cada consumo. El UPSERT no incrementa automáticamente frecuencia ni preserva versiones anteriores del agregado.

Para frecuencia/época se necesita **extensión del contrato de evidencia**, no necesariamente una tabla nueva: recibos inmutables por propósito/fase/época o bloques de batches, con multiplicidad por identidad y semántica de confirmación. Metadata podría contener un resumen, pero no sustituye por sí sola el historial verificable. Los registros de TRAIN existentes ofrecen un contenedor JSONB reutilizable; su integración debe respetar owner, inmutabilidad, secuencia, hash final y transporte. No hay necesidad demostrada de modificar UNIQUE ni de duplicar assessments aquí.

## D. Propuesta quirúrgica para TRACE.1B (no implementada)

### Reutilización de persistencia existente

| Archivo o tabla | Cambio propuesto | Evidencia que agrega | Riesgo / condición |
|---|---|---|---|
| `assessment_identities/attempts/results`; lectores backend | Calcular población, DISTINCT, cobertura y estado dentro del intento usando resultados actuales | Cobertura de resultados verificados y cota inferior de parciales | No llamar “procesamientos totales” al count sin condiciones; no cambiar EVALUATE |
| `execution/train.py`, registros `predictions` y `calibration` | Etiquetar prospectivamente el origen de cada pasada en payload/contrato; conservar registros históricos intactos | Diferencia entre VAL de auditoría, calibración y validación interna | No mover ni eliminar pasadas; no reconstruir historia como si fuera observada |
| `data/sample_repository.py`, `data/registry.py` | Reutilizar lecturas masivas para un mapa inmutable versión/materialización/ruta→identidades, validado al inicio | Población prevista con IDs y ruta | No registrar ni regenerar particiones; declarar faltantes |
| `run_dataset_images` y servicio de tracking | Proyección opcional al cierre, sólo de IDs confirmados de TRAIN/validación; escritura agregada fuera del batch | Índice de únicos por propósito con procedencia | No usar el registrador histórico para declarar toda la población consumida; corregir semántica de flags en el productor nuevo |

### Instrumentación faltante

| Archivo o tabla | Cambio propuesto | Evidencia que agrega | Riesgo / condición |
|---|---|---|---|
| `data/loaders.py` y enlace de `execution/train.py` | Mantener un token de identidad en la misma corriente y permutación que cada tensor, desde enumeración hasta entrega al paso | Asociación exacta ID↔batch, incluso con shuffle/prefetch | Un iterador paralelo “espejo” no basta. Debe preservarse el mismo RNG, transformaciones y orden; no enumerar nuevamente sólo para contar |
| Adaptación de ejecución de pasos Keras, sin cambiar arquitectura ni compile/config | Capturar confirmación al retornar correctamente el paso de optimización o de validación, vinculada a sus tokens y propósito | Participación real por imagen/época, no prefetch | Un callback `on_train_batch_end` solo no recibe IDs; `on_test_batch_end` tampoco. Evaluar un wrapper mínimo que delegue al paso original; demostrar equivalencia antes de adoptarlo |
| Agregador en ejecución / callbacks existentes | Acumular tokens y multiplicidades en memoria/buffers; descargar bloques en fronteras ya existentes; diferenciar fase y época global/local | Recuentos observados, batches completos y parciales | No `.numpy()` por imagen ni SQL por batch TRAIN; evitar sincronización GPU/CPU adicional y marcar el tramo no confirmado tras fallo |
| `execution/repository.py`, emitter/reporters y `train_execution_records` | Persistir recibos agregados e idempotentes antes del cierre de sesión, reutilizando transporte y hash de registros | Historia durable de confirmaciones con identidad de RUN/intento y secuencia | Actualizar validadores, lectores y canales HTTP/E10 conjuntamente; no introducir un kind/evento sin validar contratos |

No hay actualmente un mecanismo listo que satisfaga simultáneamente IDs exactos, shuffle intacto y confirmación posoptimización. La instrumentación de tokens/pasos es el mínimo conceptual; su viabilidad sin interferencia debe demostrarse en TRACE.1B. No se recomienda sustituir el loader por uno “equivalente” sin prueba: puede cambiar permutaciones, RNG o augmentation.

**Límite de durabilidad:** agregación fuera del camino crítico deja una ventana entre operación completada y recibo durable. Una caída abrupta puede perder el último bloque. El diseño debe reportar último bloque confirmado, estado parcial e intervalo de consumo desconocido; no prometer exactitud total ante kill arbitrario. El journal E10 existente (`M/execution/journal.py:39`) conserva eventos pendientes, no recibe hoy identidades de batches ni hace atómica una actualización GPU con PostgreSQL. Reintentar entrega de evidencia debe ser idempotente y nunca repetir el paso científico para “reponer” el contador.

### Extensiones PostgreSQL estrictamente necesarias

No se demuestra necesidad de una nueva tabla ni de alterar columnas/UNIQUE para el primer incremento: `train_execution_records` ya soporta payload JSONB por clave y recibos inmutables; su PK está en `05_keys.sql:174`, guard de owner/inmutabilidad en `04_functions.sql:1087`, y metadatos E10 en `06_constraints.sql:806`. Extender prospectivamente el contrato de payload/eventos puede cubrir época, propósito, manifest hash, multiplicidad, bloques confirmados y estado de cobertura.

Antes de implementar, verificar catálogo efectivo y validadores para escoger representación compatible. Si una exigencia posterior requiere FK relacional por ocurrencia y consultas masivas por imagen, justificar entonces una tabla hija de recibos; no es una necesidad acreditada en esta auditoría. No almacenar listas crecientes con UPSERT como única prueba histórica. No modificar assessment_results ni replicarlo en run_dataset_images para resolver un problema que ya cubre por intento.

### Pruebas de validación propuestas (sin ejecutar)

- Fixture sintético pequeño, tamaño no divisible por batch: comparar orden/IDs, tensors/augmentation, logits, pérdidas, pesos y checkpoint seleccionado con/sin instrumentación, mismas seeds/configuración; probar shuffle, no-augment y VGG16.
- Confirmar que prefetch puede cargar más que lo procesado y que esas lecturas no incrementan consumo; incluir batch final y fallos antes/después del paso y antes/después de persistencia.
- Dos fases, EarlyStopping, restauración y épocas locales/globales: distinguir los tres consumos VAL por época y la pasada final, manteniendo métricas/selección originales.
- Replay de transporte y rechazo de recibos contradictorios: ninguna duplicación de frecuencia, sin reiniciar ciencia. Recuperación de journal y caída abrupta dejan cobertura parcial explícita.
- Identidades: paths colisionantes, montaje Docker/host, registro faltante, sample_id distinto de image_id, versión/materialización equivocada; una lectura masiva y ninguna consulta por muestra en entrenamiento.
- EVALUATE sin cambio: verificado, fallo entre predict y write_batch, rollback de batch, fallo en finalización, intento interrumpido y nueva ejecución. Reutilizar pruebas en `tests/test_assessment_e6.py`, `test_assessment_postgres.py`, `test_train_run_persistence.py`, `test_pipeline_faults_postgres.py` del proyecto local, ampliándolas sin operar datos científicos reales.
- Medir memoria, latencia, sincronizaciones y tráfico: demostrar que buffers/reporting no cambian comportamiento ni fuerzan GPU→CPU por muestra. Si la igualdad o costo falla, no habilitar instrumentación como observación fiable.

## E. Riesgos científicos y reglas de interpretación

| Riesgo | Evidencia que lo motiva | Prevención |
|---|---|---|
| Lectura = procesamiento | map paralelo/prefetch; hash/lectura de EVALUATE antes del modelo | Confirmar después del paso/inferencia, separar prepared de completed |
| Población prevista = consumida | Registro histórico enumera todas las filas | No poblar evidencia de uso a partir de inventario; mantener estado desconocido |
| VAL interna = EVALUATE | Mismo split, motores y claves diferentes | Separar RUN/época de assessment_attempt y checkpoint independiente |
| Duplicar o esconder pasadas VAL | Clinical callback, PersistEpoch y calibración | Etiquetar propósito y pasada; no usar samples como log de fit |
| Repetidas = únicas | Épocas, fases, nuevos intentos y replay | DISTINCT por identidad para únicos; multiplicidad por recibo para frecuencia |
| RUN = intento | Identidad EVALUATE referencia TRAIN, pero tiene intentos propios | Agregar por attempt_id; no unir todas las evaluaciones del RUN como una sola |
| Cobertura completa sin evidencia | Epoch logs no tienen IDs; fallos inferencia→commit | Cobertura acreditada sólo sobre recibos/resultados; reportar ventanas desconocidas |
| Instrumentación altera modelo | Shuffle/RNG/augmentation y sincronización | Delegar pasos existentes; no cambiar seeds/configuración/arquitectura; pruebas de equivalencia |
| Métricas/checkpoint/predicciones no coinciden en estado exacto | Orden de callbacks y restauración de pesos | Conservar orden; registrar procedencia y no afirmar equivalencia numérica no verificada |
| Cero en UI interpretado como cero consumo | `scientific_results.consumed_images` cuenta una tabla vacía | Exponer disponibilidad/nivel de evidencia; distinguir 0 observado de desconocido |

## Verificación realizada y cierre

Se usaron búsquedas `rg -n` de los símbolos solicitados y sus llamadores en Python/SQL, lectura de entradas CLI, workers, loaders, callbacks, repositorios, lectores backend y baseline versionado; `git status --short` inicial no mostró cambios. Las skills aplicadas fueron malaria-image-and-xai-guardian, dataset-governance-guardian, postgres-schema-guardian y testing-audit-guardian. No se ejecutaron las pruebas listadas ni consultas de runtime/BD; no se presenta una prueba estática como resultado experimental.

Los cuatro puntos de consumo quedan localizados: optimización delegada a fit, validación delegada a fit, inferencia explícita de assessment VAL y la misma de TEST. Queda identificada la persistencia disponible, la desconexión operativa de run_dataset_images y el mínimo de instrumentación aún faltante. No es posible acreditar retrospectivamente IDs/frecuencia exactos de optimización o VAL interna con los registros actuales. TRACE.1A entrega el diagnóstico y propuesta; TRACE.1B queda pendiente de revisión y aprobación, sin implementación.
