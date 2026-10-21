# Capstone — TRACE.*: lecciones aprendidas y cierre arquitectónico

**Documento:** `docs/architecture/capstone_image_trace_lessons_learned.md`  
**Fecha de consolidación:** 2026-10-21  
**Estado:** CIERRE DOCUMENTAL DE LA LÍNEA EXPERIMENTAL  
**Decisión:** no integrar el observador por batch; TRACE.1B.3 no autorizado.  
**Ámbito:** Sistema de Apoyo al Diagnóstico Parasitológico mediante Visión Computacional — Malaria.

> **Principio rector.** Primero, desarrollar y validar modelos predictivos de excelencia; segundo, estudiar rigurosamente qué y cómo aprenden, sin comprometer la integridad del entrenamiento. La observabilidad debe ser proporcional a su valor científico y no convertirse en un requisito que degrade injustificadamente TRAIN.

## 0. Cómo leer este documento y nivel de certeza

Este documento **consolida decisiones y conocimientos**, no sustituye las auditorías ni los artefactos de evidencia. Diferencia:

- **Demostrado en código:** comportamiento identificado mediante inspección estática de los recorridos efectivos.
- **Demostrado experimentalmente:** resultado de controles sintéticos A/A, A/B, identidad, recibos, interrupciones y benchmarks en el entorno declarado.
- **Reportado para R2:** resultado comunicado al cierre de R2; su informe y carpeta local no estaban disponibles para inspección directa al redactar esta consolidación.
- **No demostrado:** afirmaciones que exceden el alcance del código inspeccionado o de las mediciones.
- **Decisión arquitectónica:** política de Capstone para trabajo futuro; no debe confundirse con funcionalidad implementada.

Las rutas y líneas citadas proceden del checkout auditado en TRACE.1A. Deben verificarse contra el commit y el código vigente antes de cualquier modificación. **No se afirma que este documento implemente nuevos registros, SQL, pruebas o cambios operativos.**

## 1. Pregunta original y resultado de la investigación

### 1.1 Pregunta

¿Podemos demostrar **qué imágenes concretas procesó realmente cada modelo, cuántas veces, cuándo y para qué propósito** durante la optimización TRAIN, la validación interna y las evaluaciones independientes, sin modificar su aprendizaje?

Se buscó separar cuatro hechos que no son equivalentes:

1. **Población asignada:** una imagen pertenece a la versión/split gobernado.
2. **Imagen preparada:** el loader la leyó, decodificó o adelantó por `prefetch`.
3. **Paso confirmado:** una muestra participó en un paso de cómputo que retornó satisfactoriamente, bajo la semántica específica del propósito.
4. **Evidencia durable:** el hecho quedó respaldado por un resultado o recibo persistido y verificable.

### 1.2 Conclusión

Se demostró **viabilidad experimental parcial** de transportar identidades explícitas y conservar recibos verificables, manteniendo equivalencia en las dimensiones científicas comparadas. **No se demostró idoneidad operativa**: el candidato no satisfizo los umbrales de rendimiento p95 en R1 ni R2; tampoco se integró con PostgreSQL, E10 o los datasets clínicos oficiales. Se abandona **esta estrategia de observación exhaustiva por batch**, no el objetivo de trazabilidad ni la investigación XAI.

## 2. Mapa del código investigado

En la tabla, `M/` = `malaria_dl_local_project/src/malaria_dl/`. Los puntos de observación experimentales no equivalen a hooks implementados en el código operativo.

| Flujo | Código / punto de entrada auditado | Operación efectiva | Evidencia existente / límite |
|---|---|---|---|
| TRAIN, entrada | `malaria_dl_local_project/src/train.py` → `M/execution/operations.py` → `M/execution/train.py`; campañas mediante `M/execution/campaign.py` y `M/execution/worker.py` | Inicialización de sesión y ejecución del entrenamiento | RUN, sesión, eventos, métricas y artefactos; no consumo individual de optimización |
| Dataset físico | `M/data/loaders.py`, `make_image_dataset_from_directory` y `preprocess_physical_dataset` | Enumeración, etiquetas, shuffle TRAIN, augmentation/preprocessing y `prefetch(AUTOTUNE)` | Keras recibe `(images, labels)`; identidad individual no acompaña al batch |
| Optimización | `M/execution/train.py`, `model.fit(datasets['train'], ...)`; `train_step` interno Keras | Forward, loss, gradientes y actualización del optimizador | No se persisten IDs por batch del paso de optimización |
| VAL interna | `M/execution/train.py`, `validation_data=datasets['val']`; `test_step` interno Keras | Evaluación interna en `fit`, sin actualización de pesos | Métricas agregadas `val_*`, no consumo individual certificado |
| VAL clínica adicional | `M/training/checkpoint_policy.py`, `ClinicalValidationMetricsCallback.on_epoch_end` | Inferencia adicional para métricas clínicas y selección | Métricas; no recibos individuales de esa pasada |
| VAL predicciones por época | `M/execution/train.py`, `PersistEpoch.on_epoch_end` | Otra inferencia sobre VAL por época | `train_execution_records`, `kind='predictions'`, `payload.samples`; **no** evidencia directa de VAL interna |
| VAL checkpoint elegido | `M/execution/train.py`, evaluación final del checkpoint seleccionado | Inferencia adicional de VAL al concluir TRAIN | `kind='calibration'`, `phase='val'`, `key='selected'` |
| EVALUATE VAL / TEST | `malaria_dl_local_project/src/evaluate.py` / `src/test.py` → `M/assessment/cli.py` → `M/assessment/service.py` y `M/assessment/runtime.py` | Selección gobernada, carga, predicción e inserción por intento | `assessment_identities`, `assessment_attempts`, `assessment_results`; filas acreditan resultados persistidos, no toda inferencia posible |
| Registrador histórico | `M/persistence/tracking.py`, `M/persistence/run_repository.py`, productor en `M/training/trainer.py` | Registro histórico en `run_dataset_images` | **No forma parte del recorrido TRAIN operativo auditado** |
| Lectura backend | `backend_api/app/repositories/scientific_results.py` | Consulta `run_dataset_images` como conteo de consumo | Si la tabla está vacía, `count(*)=0` **no demuestra cero imágenes procesadas** |

**Hallazgo de código decisivo:** el TRAIN efectivo no invoca el productor histórico de `run_dataset_images`. La auditoría TRACE.1A registró la tabla vacía como evidencia proporcionada, **sin consultar de nuevo PostgreSQL**. Por tanto, no atribuir automáticamente su vacío a un fallo general de TRAIN ni convertirlo en un conteo real de cero.

### 2.1 Recorrido de la imagen y puntos donde se intentó observar

```text
Dataset gobernado / materialización / split
    ↓
Enumeración de archivos y etiquetas en loader Keras
    ↓
shuffle → preprocessing → augmentation → prefetch
    ↓
Batch efectivo (images, labels)
    ├── TRAIN: Keras train_step → optimizador → pesos
    └── VAL interna: Keras test_step → métricas agregadas

Fuera de esas pasadas de fit:
    ├── callback de métricas clínicas sobre VAL
    ├── predicciones VAL por época
    └── predicción VAL del checkpoint seleccionado

EVALUATE independiente:
    identidad de assessment → muestras gobernadas → runtime.predict
    → assessment_results por (attempt_id, sample_id)
```

No debe reconstruirse el orden real de entrenamiento mediante un **iterador espejo** ni suponerse que `file_paths` representa el shuffle efectivo. El prefetch puede preparar muestras que no llegan al modelo. La augmentation cambia el tensor, no la identidad científica de la muestra.

## 3. Propósitos científicos: no confundir usos de VAL

| Propósito conceptual | ¿Actualiza pesos? | ¿Qué acredita la evidencia disponible? |
|---|---|---|
| `weight_optimization` | Sí, en TRAIN | Épocas y estados agregados; no identidad por paso operativo |
| `keras_validation` | No | Métricas internas de `fit`; no IDs por batch |
| `clinical_validation` | No | Métricas clínicas de una pasada adicional |
| `epoch_prediction` | No | Predicciones individuales persistidas por época, si existen |
| `selected_checkpoint_prediction` | No | Predicciones VAL asociadas al checkpoint elegido, si existen |
| `independent_evaluation` | No | Resultados por muestra e intento de assessment, sujetos a estado/verificación |

Estos nombres son **propósitos conceptuales del diseño TRACE.1B.1**, **no** nuevos valores permitidos automáticamente en `run_dataset_images.usage_context`. El split (`train`, `val`, `test`) y el propósito son ejes distintos. EVALUATE VAL/TEST independiente no equivale a la validación interna de TRAIN.

## 4. Evolución de las estrategias de observación

### 4.1 TRACE.1A — Auditoría sin instrumentación

**Qué se hizo:** inspeccionar el recorrido efectivo de TRAIN, VAL, EVALUATE VAL y TEST, sus loaders, callbacks y persistencia.

**Resultado:** identificación de la desconexión del registrador histórico; reconocimiento de múltiples pasadas VAL y de los límites probatorios de `predictions` y `assessment_results`.

**Limitación:** inspección estática; no midió consumo individual real ni verificó nuevamente el catálogo efectivo de PostgreSQL.

### 4.2 TRACE.1B.1 — Contrato conceptual

**Qué se diseñó:** identidad gobernada, ámbitos por RUN/fase/época/propósito, manifiesto sellado, multiplicidad, bloques de recibos, cierres, replay, hash y evidencia parcial; separación entre índice de imágenes y ledger de consumos.

**Resultado:** reglas de evidencia reutilizables. **No es implementación**, no acredita compatibilidad E10/SQL ni atomicidad GPU/almacenamiento.

### 4.3 TRACE.1B.2 — Huellas de tensores (FAIL)

**Dónde:** arnés experimental `observer.py`, `experiment.py`, `reference.py` y evidencia de TRACE.1B.2; intervención alrededor de los pasos Keras y el flujo de `tf.data`, sin editar TRAIN operativo.

**Cómo:** FarmHash64 de tensores y tabla lateral para resolver identidad; diagnóstico con copias de tensores a host/NumPy y registros crecientes; interceptación controlada de métodos para comparar tensores, etiquetas, scores y gradientes.

**Qué funcionó:** comparaciones A/A y A/B de las dimensiones disponibles, incluidas pruebas con Custom CNN, VGG16 y DenseNet121.

**Qué falló:** identidad ambigua para contenidos idénticos o colisiones; memoria de tabla/log sin cota; `receipts.json` no durable ni ledger; overhead total mediano de **7,13%**, superior al criterio de 5%. No se aprobó integración.

### 4.4 TRACE.1B.2-R1 — Tokens explícitos y recibos durables (FAIL)

**Dónde:** carpeta experimental `docs/audits/capstone_image_trace_1b_2_r1_evidence/`, principalmente `observer.py`, `ledger.py`, `recover_pending.py`, suites y comparadores. Parche **de proceso experimental** sobre la función privada de Keras `keras.src.utils.image_dataset_utils._load_image_tf`.

**Cómo se observó:** token derivado de la **ruta efectiva entregada al loader**, transportado junto con el tensor por los mapas; wrappers de `train_step` y `test_step` que extraen token, delegan una sola vez al paso original y confirman después del retorno. `predict` se adaptó sólo a las pasadas que ya existían. No se duplicaron forward/backward/inferencia.

**Cómo se preservó:** manifiesto canónico de identidades y hash; recibos locales `scope_open`, `consumption_block`, `scope_close`; pares token/multiplicidad; secuencias y cadena SHA-256; serialización JSON canónica; escritura `pending` exclusiva, `flush/fsync`, `rename`, `fsync` del directorio; replay idempotente y rechazo de conflictos/gaps. No hubo escritura a PostgreSQL ni E10.

**Qué funcionó:** distinción de identidades con bytes idénticos; comprobaciones A/A y A/B en tres arquitecturas, incluidas dos fases para VGG16 y DenseNet121; controles de recibos, SIGKILL y fallos; memoria del agregador acotada bajo el umbral experimental de 32 MiB, **sin afirmar medición de memoria nativa GPU**.

**Qué falló:** aunque los overheads totales medianos cumplieron, al menos un par excedió el p95 permitido: Custom CNN **11,79% global** y DenseNet121 **18,92% tras calentamiento**. El parche privado de Keras tampoco constituye un punto de extensión operativo estable demostrado.

### 4.5 TRACE.1B.2-R2 — Perfilado de rendimiento (FAIL, cifras comunicadas)

**Propósito:** investigar el origen del p95 y reducir el costo de observación sin relajar los umbrales ni modificar la ciencia.

**Resultado comunicado por el equipo al cierre de R2:**

| Arquitectura | Overhead total mediano | Peor p95 global | Peor p95 tras calentamiento |
|---|---:|---:|---:|
| Custom CNN | +2,37% | +7,86% | **+11,77%** |
| VGG16 | +3,72% | +3,74% | +3,61% |
| DenseNet121 | −0,36% | **+10,40%** | **+11,13%** |

Se comunicaron **A/A y A/B aprobados, 6.602 comprobaciones de estados, 5.593 de recibos, 15 pruebas del ledger y memoria aislada del agregador menor a 32 MiB**. Se localizaron latencias elevadas en primeras formas incompletas; no se observó retrazado adicional de TensorFlow. Reducir llamadas repetidas a NumPy desplazó costo hacia el arnés, pero **no estabilizó el p95**. La causa interna exacta de Metal **no fue demostrada**.

**Procedencia:** datos aportados en el cierre de R2. Revisar el informe original `docs/audits/capstone_image_trace_1b_2_r2_metal.md` y `docs/audits/capstone_image_trace_1b_2_r2_evidence/` en el repositorio local antes de citar sus archivos de evidencia o sus hashes; **no se inspeccionaron directamente aquí**. Se comunicó la conservación intacta de **15.305 archivos históricos**, sin cambios operativos, SQL, instalaciones, commit ni push.

## 5. Qué intentamos preservar y qué garantía ofrece cada nivel

| Mecanismo | Información preservada | Garantía válida | Lo que NO demuestra |
|---|---|---|---|
| Snapshot/version/split gobernado | Población prevista e identidad | Linaje de asignación | Participación real en optimización |
| Token explícito + manifiesto | Identidad de registro, separada de contenido | Correspondencia en el fixture ensayado | Consumo confirmado sin retorno del paso |
| Confirmación tras retorno Keras | Tokens del batch observado y propósito | Paso retornado en condiciones ensayadas | Recibo durable o atomicidad con GPU |
| Bloque con multiplicidades | Conteos por identidad y ámbito | Cota inferior confirmada del ámbito | Exhaustividad ante interrupciones |
| Cadena SHA + fsync + replay | Integridad, orden, rechazo de contradicción | Durabilidad experimental frente a fallos ensayados | Resistencia demostrada a fallo eléctrico ni integración E10 |
| `predictions` de época | Scores individuales de pasada adicional VAL | Resultado persistido de esa pasada | VAL interna de `fit` o backprop |
| `assessment_results` | Resultado por `(attempt_id, sample_id)` | Evidencia por muestra en intento específico | Inferencias no persistidas o consumo de TRAIN |

### 5.1 Ventana de incertidumbre irreducible

No hay transacción atómica entre una actualización de pesos en GPU y la escritura durable del recibo. Una interrupción entre ambas deja un intervalo **desconocido**. Un ledger con 0 recibos **no** demuestra 0 imágenes procesadas. Un ámbito parcial conserva únicamente una **cota inferior** de consumo demostrado. La recuperación de evidencia nunca debe volver a ejecutar pasos científicos para llenar huecos.

### 5.2 `run_dataset_images`: índice, no contador

La restricción `UNIQUE (run_id, image_id, usage_context)` permite **una fila por combinación**, no frecuencias por época, intento o batch. `batch_index`/`sample_index` únicos en una fila no constituyen historial temporal. Las flags `used_for_training`, `used_for_validation` y `used_for_test` tampoco prueban, por sí solas, la ejecución efectiva de backprop.

**Decisión:** no poblar `used_for_training=true` a partir de pertenencia a TRAIN ni inferir consumo efectivo a partir de `count(*)`. Cualquier proyección futura requerirá un contrato explícito que distinga `ASIGNADA`, `RESULTADO_PERSISTIDO` y `CONSUMO_CONFIRMADO`; estos nombres son **propuesta conceptual**, no valores implementados en el esquema actual. No alterar tablas en este cierre.

## 6. Resultados y criterios experimentales

### 6.1 Criterios utilizados

- A/A antes de A/B para establecer variabilidad de referencia.
- Igualdad exacta para identidades, etiquetas, orden y decisiones discretas; tolerancias numéricas previamente fijadas donde correspondía (`atol=1e-7`, `rtol=1e-6` en pruebas reportadas).
- Overhead total mediano **≤5%** por arquitectura.
- Overhead p95 **≤10% en cada par**, tanto global como tras calentamiento; una mediana favorable no rescata un par que incumple.
- Memoria del agregador experimental **≤32 MiB**, medida separadamente de tabla de identidad, RSS general y memoria nativa GPU.
- Integridad y replay de recibos, fallos e incertidumbre explícita.

### 6.2 Síntesis de dictámenes

| Investigación | Hallazgo positivo | Motivo de no aprobación |
|---|---|---|
| TRACE.1A | Mapa real y límites de persistencia | Auditoría, no integración |
| TRACE.1B.1 | Contrato de identidad/consumo y evidencia | Diseño, no implementación |
| TRACE.1B.2 | A/A y A/B favorables en dimensiones observadas | Overhead mediano 7,13%; identidad/memoria/durabilidad insuficientes |
| TRACE.1B.2-R1 | Tokens, ledger local, memoria acotada, equivalencia ensayada | p95 de pares por encima del límite; API privada Keras |
| TRACE.1B.2-R2 | Equivalencia y controles comunicados; mejora de mediana | p95 11,77% Custom CNN y 11,13% DenseNet121 tras calentamiento; DenseNet121 10,40% global |

Los porcentajes negativos de overhead **no demuestran aceleración causal**. La mejora entre revisiones tampoco se atribuye íntegramente a una operación aislada: cambiaron mecanismos diagnósticos y existe variabilidad entre procesos.

### 6.3 Alcance de las pruebas

Pruebas sintéticas, modelos Custom CNN/VGG16/DenseNet121, ejecución local Apple Silicon con TensorFlow/Keras y Metal; R1 utilizó fixture sintético de 32×32 y controles de fases. Las comparaciones cubrieron estados, métricas, checkpoints y diagnósticos especificados, **no** cada estado RNG, kernel, tensor interno o logit pre-sigmoid. No se demostró comportamiento equivalente a escala clínica operativa, compatibilidad con todas las variantes de Keras, memoria GPU completa ni funcionamiento con datasets oficiales y PostgreSQL/E10. No extrapolar PASS experimental a garantía universal.

## 7. Lecciones científicas y arquitectónicas permanentes

### 7.1 Identidad científica ≠ bytes

`image_id`, `sample_id`, ruta, etiqueta y SHA-256 tienen papeles distintos. Dos registros pueden compartir bytes/SHA y seguir siendo identidades científicas diferentes. El mapeo entre identidad de dataset y assessment debe respetar versión, materialización, split, ruta normalizada, clase e integridad, con unicidad demostrada; no unir por `filename` solamente.

### 7.2 Asignación ≠ preparación ≠ consumo ≠ evidencia durable

Los cuatro niveles deben mostrarse separadamente en reportes y APIs. Ausencia de evidencia no significa ausencia de procesamiento. `prefetch` no acredita optimización. Un resultado individual persistido prueba su propia pasada, no una anterior.

### 7.3 Una imagen VAL puede participar en varios propósitos

Keras valida internamente; callbacks clínicos y de predicciones realizan inferencias adicionales; al final puede ejecutarse otra pasada del checkpoint elegido. Sumar filas o inferir multiplicidad de `épocas × población` sin recibos reales produce una **estimación conceptual**, no un conteo medido.

### 7.4 La observabilidad puede interferir aunque no cambien pesos observados

Instrumentar `tf.data`, materializar tensores, sincronizar GPU/CPU, serializar, hashear y escribir introduce latencia, memoria y puntos de fallo. A/A y A/B detectan interferencia en las dimensiones comparadas; no prueban invariancia absoluta. La causa precisa de los picos Metal sigue abierta.

### 7.5 APIs privadas y puntos de extensión

El parche experimental a `_load_image_tf` sirvió para estudiar el problema, pero depende de un detalle interno de Keras. No adoptarlo operativamente sin contrato soportado, compatibilidad de versión y pruebas específicas.

### 7.6 El observador también debe observarse

Separar costo del arnés, instrumentación diagnóstica, trabajo científico, compilación/calientamiento, serialización y durabilidad. No atribuir variaciones a GPU, temperatura, retrazado o fsync sin prueba causal. Conservar los pares fallidos, no sólo medianas.

### 7.7 Fallo parcial es un estado científico legítimo

Los recibos durables de un prefijo pueden ser correctos aunque la ejecución total sea incompleta. Mantener estado parcial, identidad del intento, hashes, owner/fencing cuando aplique y ventanas desconocidas. No reetiquetar un fallo como cero consumo ni inventar éxito.

### 7.8 La persistencia tiene semánticas diferentes

`run_dataset_images` puede ser inventario; `train_execution_records` contiene métricas/predicciones/eventos de TRAIN; `assessment_results` contiene resultados de evaluaciones por intento. No sustituir uno por otro ni confundir validación de desarrollo con TEST independiente.

### 7.9 El resultado FAIL es conocimiento reutilizable

Una solución puede pasar equivalencia experimental y controles de integridad, y aun así ser rechazada por rendimiento y riesgo de integración. Conservar decisiones, límites, benchmark exacto y evidencia negativa evita repetir estrategias descartadas sin hipótesis nueva.

## 8. Decisiones arquitectónicas de cierre

| ID | Decisión | Estado |
|---|---|---|
| TRACE-CLOSE-01 | Abandonar la instrumentación exhaustiva por imagen/batch ensayada en TRACE.1B.2/R1/R2 | **APROBADA como orientación documental** |
| TRACE-CLOSE-02 | No avanzar a TRACE.1B.3 ni integrar parche privado Keras, recibos experimentales o cambios SQL | **BLOQUEADO** |
| TRACE-CLOSE-03 | Priorizar desempeño predictivo, generalización, reproducibilidad y validación clínica de modelos | **PRIORIDAD 1** |
| TRACE-CLOSE-04 | Investigar aprendizaje mediante historial, checkpoints, predicciones, errores, Grad-CAM, embeddings y comparación representacional | **PRIORIDAD 2** |
| TRACE-CLOSE-05 | Conservar auditorías, arneses y evidencia histórica sin reescribirla | **POLÍTICA DE PRESERVACIÓN** |
| TRACE-CLOSE-06 | Mostrar `NO DEMOSTRADO` / `EVIDENCIA INSUFICIENTE` cuando falta consumo individual directo | **REGLA DE PRESENTACIÓN** |
| TRACE-CLOSE-07 | No usar población prevista ni predicciones adicionales para afirmar participación individual en backprop | **REGLA DE INFERENCIA** |

**Alcance de «cierre»:** finalización de la investigación y su documentación. No significa eliminar archivos, cambiar código, marcar automáticamente estados en PostgreSQL, alterar TRAIN, retirar capacidades de EVALUATE ni modificar el esquema. Ninguna ejecución nueva se autoriza por este documento.

## 9. Consecuencias para los dos reportes científicos

**Reporte A — Aprendizaje del Modelo (un RUN):** estudiar evolución temporal, checkpoint, desempeño, distribución de confianza, errores, explicaciones espaciales y representaciones intermedias. Cada conclusión debe declarar su evidencia y distinguir visualización, interpretación e hipótesis. Grad-CAM por sí solo no prueba reconocimiento biológico del parásito.

**Reporte B — Comparación Científica (varios RUNs):** comparar únicamente resultados con preflight de población, split, protocolo, checkpoint e intento; distinguir TRAIN VAL de EVALUATE independiente y TEST; analizar errores complementarios, similitud representacional y evidencia visual. No declarar superioridad clínica basándose sólo en VAL de desarrollo.

Ambos reportes pueden avanzar sin la instrumentación TRACE por batch. No prometer reconstrucción de multiplicidad real de cada imagen en optimización si no existe evidencia.

## 10. Preguntas abiertas (no bloquean el cierre)

1. ¿Cómo exponer con claridad en UI/API la diferencia entre población asignada, resultados individuales y consumo confirmado, sin alterar esquema?
2. ¿Qué garantías de linaje e integridad ya disponibles permiten auditorías por RUN y checkpoint sin instrumentar Keras?
3. ¿Qué experimentos XAI/embeddings aportan mayor valor para estudiar el reconocimiento de parásitos?
4. ¿Qué parte de la variabilidad p95 proviene del entorno Metal y qué parte del arnés? **Sin atribución causal demostrada.**
5. ¿En qué circunstancias científicas futuras justificaría reconsiderar instrumentación directa? Sólo con nueva necesidad, arquitectura soportada, presupuesto de interferencia y autorización explícita.

Estas preguntas son agenda de investigación, **no un plan implícito de TRACE.1B.3 ni de R3**.

## 11. Índice de fuentes y evidencia

**Documentos originales del repositorio (rutas previstas):**

| Fuente | Ruta | Función |
|---|---|---|
| Auditoría TRACE.1A | `docs/audits/capstone_image_trace_1a.md` | Código efectivo, loaders, pasadas VAL, persistencia y límites |
| Contrato TRACE.1B.1 | `docs/contracts/capstone_image_trace_1b_1.md` | Modelo conceptual de identidad, recibos, ámbitos y garantías |
| Experimento inicial | `docs/audits/capstone_image_trace_1b_2_metal.md` | A/A, A/B, huellas, memoria y rendimiento inicial |
| Evidencia inicial | `docs/audits/capstone_image_trace_1b_2_evidence/` | Arnés, comparaciones y logs sintéticos |
| Experimento R1 | `docs/audits/capstone_image_trace_1b_2_r1_metal.md` | Tokens, ledger durable local, equivalencia, fallos, p95 |
| Evidencia R1 | `docs/audits/capstone_image_trace_1b_2_r1_evidence/` | Código experimental, manifests, recibos, verificadores y benchmarks |
| Experimento R2 | `docs/audits/capstone_image_trace_1b_2_r2_metal.md` | Profiling y resultados R2; **pendiente de cotejo directo** |
| Evidencia R2 | `docs/audits/capstone_image_trace_1b_2_r2_evidence/` | Evidencia R2; **pendiente de cotejo directo** |

**Regla de conservación:** los informes de cada iteración y sus evidencias son fuentes primarias inmutables para este cierre; este documento es un índice interpretativo y de decisión. Antes de publicar un inventario verificable de integridad, calcular y registrar los SHA-256 desde el repositorio local; **no inventar hashes ni afirmar haber verificado archivos no accesibles**.

## 12. Criterios de aceptación del cierre documental

- [x] Propósito original y dictamen separados.
- [x] Mapa del código y puntos de observación descritos.
- [x] Evolución TRACE.1A → TRACE.1B.1 → TRACE.1B.2 → R1 → R2.
- [x] Métodos de identidad, agregación, durabilidad, replay y fallos documentados.
- [x] Resultados positivos, FAIL y límites de evidencia diferenciados.
- [x] Decisiones explícitas: no integración y no TRACE.1B.3.
- [x] Vinculación con objetivos predictivos y XAI.
- [ ] Cotejar informe y evidencia R2 contra los archivos del repositorio local.
- [ ] Verificar rutas, referencias de código y hashes contra el checkout actual antes de aprobar un cierre documental auditado en Git.

**Dictamen de consolidación:** contenido documental preparado; **cierre experimental decidido**, con cotejo local de R2 y de integridad de fuentes pendiente. No se atribuye a este archivo aprobación de código operativo ni un commit.
