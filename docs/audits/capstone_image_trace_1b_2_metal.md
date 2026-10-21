# CAPSTONE-IMAGE-TRACE.1B.2 — GPU Metal local

Fecha: 2026-10-20. Experimento exclusivamente sintético. **Dictamen: FAIL del candidato por rendimiento y crecimiento de memoria; equivalencia integral NO DEMOSTRADA. No aprobar TRACE.1B.3.**

Se leyeron [TRACE.1A](capstone_image_trace_1a.md) y [TRACE.1B.1](../contracts/capstone_image_trace_1b_1.md). La instrucción específica de esta fase reemplaza la puerta CPU propuesta en el contrato: sólo se entrenó con GPU Metal. Ningún resultado parcial constituye aprobación operacional.

## 1. Entorno y aislamiento

Python local `malaria_dl_local_project/.venv-metal/bin/python`; macOS 26.7.1, arm64, Apple M4 Max, 48 GB de memoria unificada según el plugin Metal. Python 3.12.13, TensorFlow 2.17.1, Keras 3.15.1, NumPy 1.26.4, tensorflow-metal 1.2.0.

Dentro del sandbox, `tf.config.list_physical_devices('GPU')` devolvió `[]` y `No supported GPU was found`. Se repitió la comprobación con ejecución autorizada fuera del sandbox: GPU visible `/physical_device:GPU:0`. Antes de cada experimento se exigió GPU visible y se ejecutó un producto de matrices explícitamente en `/GPU:0`, materializando su resultado. `environment.json` guarda el dispositivo efectivo del resultado. Se deshabilitó soft placement en ambos brazos; no hubo sustitución por un entrenamiento CPU. Esto no implica que decoding, lookup o todas las operaciones individuales se ejecuten en GPU.

Se invocó la función operativa `execution.train.train`, con adaptadores, resolución de configuración, compilación, callbacks y selección originales. `runtime/configuration` conserva el `execution_mode=local_python` real. Se sustituyeron exclusivamente los adaptadores de acceso a datos de control por un catálogo Python conocido y un repositorio de auditoría en archivos: no se consultó PostgreSQL ni se reservó un RUN operativo. Los UUID del fixture son sintéticos, no identifican ejecuciones existentes. Este arnés no acredita el transporte HTTP ni el journal operacional.

## 2. Fixture y criterios fijados

37 PNG TRAIN y 19 PNG VAL, RGB 32×32, batch 8; clases originales. Bytes generados con `default_rng(20261020)` y manifiesto de ruta relativa, etiqueta y SHA-256. No hay TEST ni imágenes clínicas. Cada proceso genera los mismos bytes en un directorio nuevo. Semilla científica 42, determinismo TensorFlow activado, shuffle TRAIN, augmentation original y prefetch AUTOTUNE. Float32; pesos `none`, sin descargas; preprocessing y congelamiento de cada adaptador conservados.

La resolución 32×32 es una configuración sintética admitida por el resolver, no cobertura de todos los tamaños operativos. Máximo tres épocas, EarlyStopping con patience 1, min_delta 1 y restauración activada. La configuración exacta completa está en cada `configuration.json`. La fase base ejecutó dos épocas. Además se ejecutaron réplicas independientes con dos épocas base y dos de fine-tuning en VGG16 y DenseNet121, conservando la política original de congelamiento y el reinicio de optimizador por fase.

Tolerancias fijas: `abs(A-B) <= 1e-7 + 1e-6*abs(A)`, finitud y formas iguales. Etiquetas y tensores exigen igualdad exacta; decisiones discretas, nombres de checkpoints, épocas y claves se comparan exactamente. No se ampliaron tolerancias. No se comparan hashes del ZIP `.keras` como sustituto de pesos: se comparan datasets numéricos de `model.weights.h5`, incluyendo variables del optimizador.

## 3. A/A y A/B

Los resultados verificables se conservan en [evidencia](capstone_image_trace_1b_2_evidence/): `aa_comparison.json`, `ab_comparison.json`, `vgg16_*_comparison.json`, `densenet121_*_comparison.json` y cinco `perf_*_comparison.json`. Cada comparación desglosa nombre, resultado y diferencia máxima cuando corresponde.

Custom CNN: A/A y primer A/B pasaron 618 comprobaciones cada uno. Los cinco pares A/B alternados también pasaron las comparaciones de registros y variables disponibles. VGG16 pasó A/A y A/B (582 comprobaciones por comparación); DenseNet121 también (1.726 por comparación). Las comprobaciones incluyen métricas de época, selección, parada, predicciones de las pasadas existentes, calibración, pesos guardados y estado del optimizador guardado. No se ejecutó inferencia adicional para efectuar estas comparaciones. En las comparaciones iniciales A/A y A/B de las tres arquitecturas, y en la captura diagnóstica Custom CNN, la diferencia absoluta máxima registrada fue 0; el criterio de aceptación continuó siendo el predefinido, sin generalizar igualdad bit a bit a dimensiones no observadas.

La comparación de las predicciones existentes NO se usa para acreditar consumo de validación interna. Sólo confirma conservación de esas salidas científicas. Inicialización y RNG se restablecen mediante procesos independientes, configuración y seed iguales; el baseline sin referencia no captura directamente cada estado RNG ni los pesos iniciales.

Las pruebas adicionales de dos fases pasaron A/A antes de B y A/B: 1.094 comprobaciones por comparación en VGG16 y 3.370 en DenseNet121. Evidencia: `vgg16_phases_*_comparison.json` y `densenet121_phases_*_comparison.json`. Los logs B contienen 32 batches retornados por arquitectura, pero carecen todavía de claves explícitas de ámbito: su verificación experimental no los convierte en recibos contractuales.

## 4. Candidatos investigados

| Alternativa | Evaluación |
|---|---|
| Iterador espejo de identidades | Descartado: no acredita orden efectivo; no se implementó. |
| IDs como tercer elemento de `tf.data` | No se delegan directamente: Keras los interpretaría como sample weights. Requiere desempaquetado explícito. |
| Diccionario de imagen/token como entrada del modelo | Requiere adaptar el paso y preservar compatibilidad de las otras pasadas; no se ensayó como candidato final. |
| Tokens junto a tensores en maps, con tabla lateral de huellas al entregar `(x,y)` | Candidato implementado en `observer.py`; conserva la estructura que usan todas las pasadas existentes y delega una sola vez en train_step/test_step. |

La tabla inicial vincula huellas del tensor sintético sin augmentation a tokens de manifiesto. Los tokens viajan junto a imagen/etiqueta por las transformaciones. Antes de entregar `(x,y)`, se asocia huella del tensor transformado al token. El paso real consulta la huella de SU tensor recibido; no hay iterador espejo. Las entradas preparadas por prefetch no son recibos.

El wrapper llama una vez al paso original y devuelve tokens/tensores auxiliares junto a sus resultados. Fuera de la función compilada se materializan resultados y se retiran esas claves antes de entregarlas a Keras/callbacks. Sólo entonces se agrega el registro del batch. No se duplican forward, backward ni apply_gradients. No se reordenan callbacks ni se cambian pesos, optimizador o arquitectura. Las pasadas clínica, por época y del checkpoint seleccionado siguen ejecutándose mediante el código original, sin recibos propios añadidos.

**Límites del candidato:** huella FarmHash64, no identidad criptográfica; riesgo de colisión y dependencia de unicidad del contenido sintético. El manifiesto conserva SHA-256, pero el lookup no compara todo el contenido en cada acceso. La tabla de transformaciones y la lista de registros crecen con el recorrido. La copia de tensores completos hacia host es diagnóstica y costosa. El candidato no sirve como implementación operacional del contrato.

## 5. Identidades, tensores, gradientes y pesos

`receipts.json` es un log experimental del retorno de batches, no un ledger durable conforme a TRACE.1B.1. Registra propósito, tokens del batch, hash del tensor, etiquetas y tiempo. El verificador contrasta multiplicidad con el manifiesto, orden entre épocas y últimos batches de 5 TRAIN y 3 VAL. No se asigna consumo a una entrada de la tabla de preparación.

La captura simétrica `reference.py` intercepta argumentos/resultados de las llamadas originales `compute_metrics` y `apply_gradients`, y devuelve imágenes, etiquetas, scores sigmoid y gradientes del mismo paso. No llama al modelo otra vez. Sus archivos NPZ pasaron 225 comprobaciones A/B (tensores/etiquetas exactos; scores/gradientes dentro de tolerancia). Los dos controles de interferencia pasaron las 618 comprobaciones disponibles por brazo frente a las ejecuciones sin referencia. Sus archivos NPZ se comparan directamente; además se compara cada brazo diagnóstico con su versión sin referencia para detectar interferencia observable. Los logits anteriores a sigmoid no se capturan ni se reconstruyen para afirmar observación directa.

Los pesos y optimizador se contrastan en cada checkpoint existente, no tras cada batch. No se acredita igualdad de todos los estados intermedios, RNG interno, kernels o logits. La captura diagnóstica sólo cubre Custom CNN; no extenderla a VGG16 ni DenseNet121.

## 6. Interrupciones, multiplicidad y evidencia parcial

Las inyecciones son excepciones controladas, no SIGKILL ni fallos de almacenamiento. `before` falla antes de invocar la función científica; `during` hace fallar la función compilada tras programar el paso original, por lo que sus efectos se consideran desconocidos; `after` falla tras retornar el paso y antes de los callbacks. Se ejecutaron en procesos A/B separados. Los seis casos corregidos terminaron con la excepción inyectada esperada. B conservó respectivamente 0, 0 y 1 batches confirmados (8 imágenes en el último caso). `receipt_verification.json` pasó 95 comprobaciones de tamaños, multiplicidad, etiquetas, shuffle, vínculo con tensores diagnósticos y fallos.

El log se guarda al capturar la excepción. Ese guardado no demuestra durabilidad ante muerte abrupta. Cero recibos durante un fallo no significa cero procesamiento; los batches anteriores confirmados constituyen una cota inferior. No se repite ciencia para recuperar evidencia.

Los controles separados de `identity_probe.py` rechazaron dos rutas distintas con contenido idéntico (identidad ambigua para este mecanismo) y una entrada sin mapeo. Una preparación explícita mediante el pipeline con prefetch, sin entregar ningún batch al modelo, dejó entradas preparadas y cero batches confirmados. Este iterador aislado es un control negativo de preparación, no un espejo usado para reconstruir el orden de TRAIN. Ver `identity_verification.json`.

Pendientes: protocolo de claves de ámbito/fase/época, replay idempotente, rechazo de contradicciones de recibos, límites por bloque, cierres y ventanas durables. No se inventan eventos E10 ni se publica este log como `run_dataset_images`. El candidato no satisface todavía el contrato completo de identidad, idempotencia y evidencia parcial.

## 7. Rendimiento

Cinco pares independientes con orden AB, BA, AB, BA, AB; sin concurrencia entre entrenamientos. Todos con la misma configuración. [performance.json](capstone_image_trace_1b_2_evidence/performance.json) incluye cada tiempo total, mediana/p95 de batch, throughput y pico RSS.

**Overhead total mediano: 7,13%; FAIL frente a ≤5%.** El total incluye construcción/entrenamiento, callbacks científicos, checkpoints y serialización final del observador; excluye arranque del intérprete y generación del fixture en ambos brazos. B incluye construcción de su mapa de identidad. La captura de tensores del candidato sigue activa: el costo medido corresponde a ese candidato concreto, no a una futura versión optimizada.

Para percentiles por batch se excluye el primer paso de cada propósito en ambos brazos. No es un benchmark de estado estacionario: sólo dos épocas, batches finales de distinta forma y posibles retrazados. La mediana del overhead de p95 entre pares fue −2,16%; no se interpreta como aceleración demostrada ni como aprobación de todos los pasos. Los cinco overheads p95 individuales fueron −3,36%, −4,39%, −2,16%, +5,90% y +3,13%. Los datos crudos están en `timings.json`.

Corrección del arnés: el primer etiquetado de métodos enlazados de A usaba `is`, clasificando todos sus pasos como validación. Se corrigió a igualdad de métodos. Los tiempos brutos y el total son válidos; `summarize.py` reconstruye sólo las fronteras de warm-up de los 16 pasos mediante el recorrido finito verificado de 5 TRAIN + 3 VAL por época, excluyendo índices 0 y 5. No usa ese cálculo para acreditar identidades. El primer `fault_before_a` no activó la inyección y queda conservado como prueba inválida en `diagnostics.log`; `faults.py` repitió los seis casos con nombres `fault_verified_*`. No se ocultó ni contó como éxito ese intento.

Throughput: participaciones TRAIN + VAL interna por segundo total, excluyendo del numerador las otras pasadas existentes. RAM: pico RSS del proceso y diferencia B−A; no aísla el agregador de TensorFlow, mapa de identidad o copias de tensores. **Umbral de 32 MiB del agregador: NO DEMOSTRADO.** Memoria GPU: no medida de forma fiable; la memoria unificada del host y el mensaje de 0 MB de TensorFlow no constituyen esa medición.

En Custom CNN completo se observaron 93 entradas preparadas: 74 transformaciones TRAIN de dos épocas y 19 VAL. No se eliminan entradas por época y el log acumula batches. El diseño carece de cota independiente de la duración; no cumple el requisito de evitar crecimiento sostenido. `receipt_cost.json` mide bytes y una serialización posterior, separada del costo científico; no representa commit SQL ni journal.

## 8. Matriz de cobertura y limitaciones

| Requisito | Estado / límite |
|---|---|
| GPU Metal real, Python local, versiones | Verificado; prueba explícita GPU y logs por proceso. |
| A/A antes de A/B, tolerancias fijas | Ejecutado por arquitectura; no relajadas. |
| Batch incompleto, shuffle, augmentation, prefetch | Ensayados con fixture 37/19; verificación de tokens y tamaños. |
| EarlyStopping y mejores pesos | Callbacks originales; decisiones y checkpoints comparados. |
| Dos fases | Ejecutadas base + fine-tuning en VGG16 y DenseNet121; A/A y A/B pasaron las dimensiones comparadas. |
| Augmentation desactivada / shuffle desactivado en TRAIN | PENDIENTE como controles específicos. |
| Gradientes/tensores por paso | Diagnóstico sólo Custom CNN; ver sus resultados. |
| Logits anteriores a sigmoid / pesos por paso | NO OBSERVADOS directamente. |
| Interrupciones | Excepciones antes/durante/después; no muerte abrupta ni commit incierto. |
| Identidad ambigua | Rechazo verificado para dos rutas con contenido idéntico y entrada sin mapeo; no cubre todas las colisiones/materializaciones del contrato. |
| Idempotencia, cierre, bloques acotados | NO IMPLEMENTADOS; no hay recibos operativos válidos. |
| Cinco pares de rendimiento | Custom CNN; no extrapolar rendimiento a otras arquitecturas. |
| Memoria agregador/GPU | No aislada / no medida confiablemente. |

## 9. Reproducción y archivos

Desde la raíz del repositorio, con acceso real a Metal:

```sh
malaria_dl_local_project/.venv-metal/bin/python docs/audits/capstone_image_trace_1b_2_evidence/experiment.py /private/tmp/trace-aa-new --deterministic
malaria_dl_local_project/.venv-metal/bin/python docs/audits/capstone_image_trace_1b_2_evidence/experiment.py /private/tmp/trace-b-new --deterministic --observer
malaria_dl_local_project/.venv-metal/bin/python docs/audits/capstone_image_trace_1b_2_evidence/compare.py /private/tmp/trace-aa-new /private/tmp/trace-b-new /private/tmp/trace-comparison.json
```

Los destinos deben ser nuevos: el arnés rechaza sobrescribir evidencia. `--architecture vgg16|densenet121`, `--two-phases`, `--reference` y `--interrupt before|during|after` reproducen las variantes. `suite.py`, `diagnostics.py`, `faults.py` y `two_phases.py` documentan la secuencia completa original y usan nombres fijos: no ejecutarlos encima de evidencia existente. Cada directorio guarda configuración, manifiesto, entorno, registros y outcome; los completados guardan checkpoints y, según variante, tiempos, logs de batches o NPZ diagnósticos.

`inventory.json` enumera los archivos retenidos con bytes y SHA-256; permite verificar integridad local. Los hashes del arnés corresponden a su versión final, no a un registro retrospectivo del código en cada arranque.

Sólo se escribieron archivos de auditoría. Sin cambios de TRAIN operativo, PostgreSQL, campañas, RUN existentes, EVALUATE, TEST o EXPLAIN. Sin instalación de dependencias, descargas de pesos, commit ni push.

## 10. TRACE.1B.3 y recomendación

No avanzar. Rediseñar primero el transporte de tokens y la agregación con memoria acotada, identidad verificable sin dependencia de huella débil, ámbitos explícitos y confirmación/durabilidad separadas. Repetir A/A y A/B, completar los casos pendientes y validar los ámbitos de ambas fases, y demostrar costo dentro de los límites originales.

Si una nueva técnica supera TRACE.1B.2, los puntos previstos de intervención son `malaria_dl_local_project/src/malaria_dl/data/loaders.py`, `execution/train.py`, resolución gobernada en `data/sample_repository.py` y `data/governed_dataset.py`; después, contratos/eventos, emitter/journal, transportes, lectores y validadores de cierre citados en TRACE.1B.1. Ninguno se modificó. No hay razón demostrada para alterar esquema PostgreSQL. Las otras pasadas VAL conservarían su comportamiento.
