# CAPSTONE-IMAGE-TRACE.1B.2-R1 — GPU Metal local

Fecha: 2026-10-20. **Dictamen final: FAIL por rendimiento p95; sin aprobación operativa.** TRACE.1B.2 conserva su FAIL y su evidencia no se modifica. Campaña y controles completados; evidencia nueva e independiente.

## A. Diagnóstico del candidato anterior

Se leyeron íntegramente TRACE.1A, TRACE.1B.1 y TRACE.1B.2, además de observer.py, experiment.py, reference.py y comparadores anteriores. `keys()` usa FarmHash64; `Observer.__init__` vuelve a decodificar imágenes para vincular contenido y token. `preprocess.detach` inserta cada transformación en MutableHashTable sin expiración. `execute` convierte imágenes completas a NumPy, calcula SHA256 y agrega cada batch a `rows`. Tabla y lista crecen con épocas. Una colisión o bytes idénticos impiden identidad científica inequívoca. No existen bloques durables, ámbitos, replay ni cierres contractuales.

Las copias x/y, hashes de tensores y captura de gradientes corresponden al diagnóstico. Lookup de identidad, confirmación del retorno y agregación son necesidades del observador anterior; no todos sus mecanismos son necesarios. El 7,13% anterior incluye ambas clases de trabajo. No hay un experimento factorial que permita atribuir porcentajes causales a cada operación; R1 no inventa ese desglose.

## B. Diseño R1

[Diseño registrado antes de medir](capstone_image_trace_1b_2_r1_evidence/design.md). Código exclusivamente en la [carpeta experimental](capstone_image_trace_1b_2_r1_evidence/). No se editaron módulos operativos.

La enumeración, indexación inicial y shuffle siguen siendo de Keras instalado. Un parche de proceso a `keras.src.utils.image_dataset_utils._load_image_tf` devuelve `{image: imagen_original, token: lookup(path)}`. El token se resuelve de la misma ruta pasada a la decodificación original, sin fingerprint del tensor ni iterador espejo. El dataset sigue siendo `(x,y)`, pero x es temporalmente un diccionario. Los mapas del preprocessing experimental aplican exactamente las funciones originales a `x.image` y transportan `x.token`; conservan su orden, augmentation y prefetch AUTOTUNE.

Se envuelven `train_step` y `test_step`, se extrae la imagen y se delega exactamente una vez al método enlazado original con `(image,y)`. No se implementan forward, loss, backward ni optimizador alternativos. La salida token depende de outputs y, en TRAIN, lectura de optimizer.iterations; `_make_function` envuelta materializa retorno y token antes de agregar consumo. Se exige steps_per_execution=1. No se pretende compatibilidad general con sample weights, estrategias distribuidas u otras versiones privadas de Keras.

`Model.predict` se envuelve sólo para extraer image del diccionario en las pasadas adicionales que ya realiza TRAIN, incluido el modelo cargado del checkpoint. No se añaden inferencias. `model.fit` añade al final un callback de fronteras; conserva orden relativo de los callbacks científicos. Época local 1-based, offset global según épocas realmente retornadas por fit, fase de compile_phase. La validación interna abre/cierra su propio ámbito. Las pasadas predict no generan recibos de keras_validation.

El diagnóstico A utiliza el mismo transporte explícito sin agregación ni recibos, para observar tokens/tensores en ambos brazos. Se compara además cada diagnóstico con su ejecución ordinaria para detectar interferencia en las salidas científicas disponibles. Esto no convierte en observados los estados internos que no se capturan.

## C. Identidad

El manifiesto canónico ordena por ruta completa y sella dataset_version, materialización, split, source_record sintético, ruta, etiqueta y SHA256. El entero sólo es un índice de ese manifiesto; el hash de contenido no define identidad. Cada recibo refiere el hash y el archivo token_manifest.json. El control `duplicate_b` conserva 56 identidades distintas con un par de registros de bytes/SHA256 idénticos; las dos identidades se confirman por separado. El control de identidad ausente falla al alcanzar el token no resuelto, conserva un batch previo de identidades válidas y cierra parcial: no atribuye consumo a la muestra sin resolver. El control de preparación obtiene 8 imágenes/tokens del pipeline y deja 0 batches confirmados y 0 eventos durables, sin invocar modelo. Los UUID de RUN/sesión son sintéticos y no acreditan RUN operativos. Las rutas son las del fixture generado y no se pretende que este resolver sustituya la gobernanza de datasets oficiales.

## D. Memoria

El agregador conserva sólo el ámbito activo, contador de tokens y batches del bloque activo; mantiene el orden dentro de ese bloque como extensión diagnóstica compacta. El historial se escribe en archivos por ámbito/secuencia. La recuperación verifica eventos secuencialmente sin cargar sus payloads históricos juntos. La enumeración de directorios mediante pathlib en Python 3.12 puede materializar nombres; no se declara memoria O(1) de esa enumeración para cantidades arbitrarias de ámbitos. No retiene imágenes, transformaciones ni scores. La tabla estática de identidad es O(N) y se reporta por separado.

deep_size recorre contenedores Python del agregador, no los internals de objetos de librerías; tracemalloc y la sonda RSS aislada complementan esa medida. La cota de objetos del agregador incluye listas, counters, estado del ámbito y reserva conservadora para cuatro serializaciones de 256 KiB. Es distinta del pico RSS del proceso TensorFlow. La medición tracemalloc de estrés excluye asignaciones nativas TensorFlow; los bytes Python y payload de la tabla no son una medición del overhead interno del hash table nativo. La memoria GPU no se mide confiablemente y no se reporta como cero.

Mediciones: 30 épocas reales Custom CNN, 240 batches y 60 ámbitos completos; tamaño calculado de sus estructuras Python 1427 bytes en épocas 1 y 30, cota de pico con reservas 1056264 bytes (~1,007 MiB). RSS pasó de 1713160192 a 1908916224 bytes; ese aumento del proceso no se atribuye al agregador. La telemetría y el repositorio sintético del arnés también conservan datos científicos/de medición y no se presentan como memoria del observador.

Estrés de 1000 ámbitos/8000 batches: tamaño calculado de sus estructuras Python 1455 bytes constante; tracemalloc alcanza 250107 bytes. Hubo un salto único de 207552 bytes alrededor del ámbito 625 y meseta hasta 1000. `allocation_probe.json` lo localiza en `pathlib.py:404`, internado de componentes de ruta; no se oculta como memoria nula ni se interpreta como retención de batches. La prueba de 8192 tokens midió cota de pico 2392760 bytes (~2,282 MiB), bajo 32 MiB. Una segunda sonda aislada del bloque de 8192 pares midió 2134990 bytes de pico tracemalloc (~2,036 MiB) y 6995968 bytes (~6,672 MiB) de incremento de pico RSS del proceso, incluyendo overhead del diagnóstico; ambos bajo 32 MiB. No se equiparan bytes JSON con RAM. El mapa Python/payload de identidad se informa por ejecución (~45 KiB); el overhead interno de la tabla nativa TensorFlow queda no medido.

## E. Recibos y durabilidad

Prototipo local distinto de E10 y PostgreSQL. Un evento canónico JSON lleva tipo scope_open/consumption_block/scope_close, ámbito completo, secuencia y hash previo. La clave del archivo se deriva del ámbito sin hash/ref del manifiesto y de la secuencia: cambiar manifiesto bajo la misma clave es conflicto. SHA256 excluye su propio campo. Canónico: sort_keys, separadores compactos, ensure_ascii=True, allow_nan=False.

El bloque contiene batches completos ordenados y pares token/multiplicidad ordenados; el verificador recalcula los conteos. Apertura/cierre forman parte de la cadena, una extensión respecto del encadenamiento sólo de bloques de TRACE.1B.1. El esquema experimental anida los campos de ámbito en scope; no es un evento E10 listo para enviar ni prueba de compatibilidad SQL/HTTP. Los totales de cierre y secuencias se verifican. Replay idéntico retorna sin aumentar conteos; contradicciones, gaps y reapertura científica bajo el mismo ámbito se rechazan.

Escritura a archivo pending exclusivo, flush/fsync, rename y fsync del directorio; se conserva cualquier pending ante fallo. Se verifican hash, secuencia, cierre y archivos truncados/pending. Garantía ensayada frente a muerte del proceso, no fallo eléctrico del dispositivo. No existe atomicidad GPU/almacenamiento. Las fronteras se interpretan así:

| Frontera | Evidencia admitida | Lo que no acredita |
|---|---|---|
| Preparada/prefetch | Tensor y token producidos por el pipeline | Ejecución del paso |
| Entregada | Argumento del paso original, capturado en diagnóstico cuando retorna | Finalización si la función falla |
| Paso completado | Retorno materializado de la función original, token del mismo batch | Durabilidad antes del journal |
| Recibo durable | Evento canónico completo, fsync y cadena verificable | Atomicidad con GPU ni consumo fuera de la ventana confirmada |

Un ámbito abierto o cierre parcial mantiene ventana desconocida; sólo los bloques completos son cota inferior durable. Ninguna recuperación repite ciencia.

Máximos 256 KiB/evento, 8192 pares, 128 batches. Se reserva espacio antes de agregar un batch al bloque; no se divide batch. Batch sobredimensionado produce error explícito, sin elevar límites. El prototipo sólo se activa en fixture de batch 8; configuraciones arbitrarias requieren preflight de capacidad o protocolo multipart aprobado. Drenaje al primer retorno disponible después de 5 segundos, frontera de ámbito o bloque lleno: no ofrece garantía durante un paso/compilación que tarda más de cinco segundos.

En sondas separadas y con controles de interferencia aprobados, la demora máxima desde el primer batch confirmado del bloque hasta escritura durable fue 0,535 s (Custom CNN), 0,321 s (VGG16) y 1,333 s (DenseNet121). El campo max_drain_seconds del resumen ordinario mide apertura/último flush→flush e incluye compilación anterior a una confirmación; no equivale a edad de evidencia pendiente. No se reclasifica un paso en curso como confirmado para cumplir el límite.

15 pruebas unitarias pasaron, incluidas recuperación de pending truncado y contradicción contra un evento final. Se ensayaron 128 batches y apertura del bloque siguiente, 8192 pares, rechazo de 8193 pares y de un batch/evento serializado sobredimensionado. El evento mayor de los controles de capacidad fue 112926 bytes; los eventos del fixture ordinario están alrededor de 1,2 KiB. Un batch sobredimensionado no se divide ni se registra parcialmente.

Fallos antes/durante/después, ejecutados en A y B independientes: B conservó respectivamente 0, 0 y 1 batches, siempre con cierre parcial; durante el paso los efectos científicos siguen desconocidos. En un TRAIN real sintético, el fallo entre fsync y rename dejó apertura + pending y 0 bloques finales; la recuperación verificó el pending completo y retransmitió exactamente su contenido, conservando 5 batches y cierre parcial, sin reinferencia. Un SIGKILL de otro TRAIN sintético tras su primer bloque dejó 5 batches durables y apertura sin cierre. El control separado de journal truncado identifica pending inválido y conserva el prefijo completo, sin inventar la cola.

Recuperación: 200 ámbitos/600 eventos en 0,049 s; 1000 ámbitos/3000 eventos en 0,205 s; 60 ámbitos de las 30 épocas GPU en 0,012 s. Son medidas locales de este almacenamiento experimental, no garantías de E10, PostgreSQL o tolerancia a pérdida eléctrica.

## F. Equivalencia

Las tres puertas A/A pasaron antes de interpretar A/B. A/A y A/B ordinarios dieron diferencia máxima absoluta 0 en las variables numéricas efectivamente comparadas:

| Arquitectura | Fases | A/A | A/B | Diagnóstico A/B de tokens/tensores/gradientes |
|---|---|---:|---:|---:|
| Custom CNN | base | 618/618 | 618/618 | 241/241 |
| VGG16 | base + fine_tuning | 1094/1094 | 1094/1094 | 301/301 |
| DenseNet121 | base + fine_tuning | 3370/3370 | 3370/3370 | 231/231 |

Los controles de interferencia de cada brazo diagnóstico frente al ordinario también pasaron. La captura de gradientes cubre las tres arquitecturas y sólo las variables con gradiente del optimizador original; no atribuye gradientes a capas congeladas. No se calcula otro forward para la referencia. Tolerancias inmutables atol=1e-7 y rtol=1e-6. Identidad, orden, labels, tensors, pasos y decisiones discretas se verifican exactamente. Los pesos/optimizador se observan en checkpoints y en capturas iniciales/finales por fase, no después de cada batch; logits pre-sigmoid y estado interno completo de RNG/TF no se capturan. Se conserva seed 42, float32, pesos none y fixture 37/19 de 32×32.

`state_comparison.json` pasa 6602 comprobaciones: pesos y variables de optimizador iniciales de cada fase, estado tras fit y correspondencia directa de los pesos restaurados con EarlyStopping.best_weights, para A y B de las tres arquitecturas. Las diferencias máximas observadas son 0, sin ampliar tolerancias. Los seis controles de interferencia de esa captura frente a los brazos ordinarios pasan. Los archivos step_devices.jsonl capturan el dispositivo de scores y gradientes efectivamente retornados del mismo paso: GPU:0 en A y B de las tres arquitecturas, además de la sonda inicial Metal. Esto no implica que decoding, lookup o todas las operaciones individuales se ejecuten en GPU.

Los controles no-augment, no-shuffle_verified y duplicate pasan A/B y comparación diagnóstica exacta; el caso no-shuffle_fixed_smoke valida también la firma corregida del arnés. `receipt_verification.json` pasa 3745 controles de identidad/hash, población, split, orden contra captura diagnóstica, etiquetas, multiplicidades, últimos batches 5/3, ámbitos/offsets de fase y ventanas parciales. No son 3745 entrenamientos, sino aserciones sobre los artefactos conservados.

## G. Rendimiento

| Arquitectura | Overhead total mediano | p95 global mediano | p95 tras calentamiento mediano | Peor p95 tras calentamiento |
|---|---:|---:|---:|---:|
| custom_cnn | 3.36% | 4.65% | -5.81% | 6.27% |
| vgg16 | 2.34% | 1.46% | 1.02% | 6.48% |
| densenet121 | 1.35% | -1.27% | 7.22% | 18.92% |

| Arquitectura / par | Orden | Total A (s) | Total B (s) | Overhead total | Overhead p95 global | Overhead p95 tras calentamiento |
|---|---|---:|---:|---:|---:|---:|
| custom_cnn / 1 | AB | 5.494 | 5.679 | 3.36% | 0.38% | 6.27% |
| custom_cnn / 2 | BA | 5.444 | 5.653 | 3.84% | 11.79% | -18.67% |
| custom_cnn / 3 | AB | 5.329 | 5.526 | 3.70% | 8.34% | -5.81% |
| custom_cnn / 4 | BA | 5.490 | 5.520 | 0.54% | 4.65% | -8.00% |
| custom_cnn / 5 | AB | 5.261 | 5.272 | 0.21% | 2.22% | 4.25% |
| vgg16 / 1 | AB | 7.121 | 7.262 | 1.98% | -2.51% | 1.02% |
| vgg16 / 2 | BA | 7.068 | 7.233 | 2.34% | -0.25% | -0.00% |
| vgg16 / 3 | AB | 6.996 | 7.258 | 3.75% | 2.37% | 5.31% |
| vgg16 / 4 | BA | 7.001 | 7.142 | 2.03% | 2.12% | -1.86% |
| vgg16 / 5 | AB | 7.025 | 7.249 | 3.18% | 1.46% | 6.48% |
| densenet121 / 1 | AB | 53.218 | 63.809 | 19.90% | 4.45% | 18.92% |
| densenet121 / 2 | BA | 54.060 | 54.789 | 1.35% | 2.56% | 7.22% |
| densenet121 / 3 | AB | 59.179 | 56.014 | -5.35% | -8.30% | 7.69% |
| densenet121 / 4 | BA | 54.906 | 56.434 | 2.78% | -1.27% | -0.90% |
| densenet121 / 5 | AB | 57.741 | 54.706 | -5.26% | -8.05% | -11.82% |

El overhead p95 de cada par es 100×(p95(B)/p95(A)−1). Las columnas de mediana agregan esos cinco overheads, no son un p95 de ratios individuales. “Global” incluye primeros pasos/compilación; se muestra también la variante tras calentamiento. El dictamen no usa una mediana favorable para ignorar un par por encima del límite.

Cinco pares AB, BA, AB, BA, AB por arquitectura, procesos independientes sin entrenamientos concurrentes. Total incluye construcción del observador, resolución de mapa, entrenamiento original, serialización, escritura/fsync, cierre y recuperación final; excluye arranque del intérprete y generación del fixture por igual. Se reporta p95 de todos los pasos y p95 sin primer paso de cada propósito/fase (compilación), sin ocultar esos pasos del total. Throughput usa sólo participaciones TRAIN + VAL interna, aunque el denominador incluye todas las pasadas originales.

| Arquitectura | Throughput A/B mediano (participaciones/s) | Pico RSS máximo A/B (GiB) | Bloques por B | Escritura B (ms, rango) |
|---|---:|---:|---:|---:|
| custom_cnn | 20.57 / 20.27 | 1.670 / 1.672 | 4 | 3.90–4.45 |
| vgg16 | 31.88 / 30.90 | 1.891 / 1.959 | 8 | 7.63–8.98 |
| densenet121 | 4.08 / 4.00 | 8.731 / 8.753 | 10 | 9.44–30.29 |

El campo close_seconds incluye flush y cierres de ámbito; write_seconds incluye esos mismos fsync, por lo que no se suman como costos independientes. Los valores por brazo de mediana/p95 de batch, throughput, RSS, cierre, recuperación, número de bloques y bytes máximos están en performance.json y timings.json. La mediana total Custom CNN baja del 7,13% previo al 3,36% aquí; no se atribuye causalmente toda la diferencia al transporte de tokens, porque también se separó la captura diagnóstica y existe variabilidad entre procesos. Los porcentajes negativos no demuestran aceleración. No se aisló causalmente el origen de la dispersión de p95 mediante un profiler de kernels; no se atribuye a temperatura, sincronización o compilación una fracción no medida del costo.

## H. Cobertura y limitaciones

Entorno registrado por proceso: Apple M4 Max, macOS 26.7.1 arm64; Python 3.12.13 de `.venv-metal`, TensorFlow 2.17.1, Keras 3.15.1, tensorflow-metal 1.2.0 y NumPy 1.26.4; `execution_mode=local_python`. No hubo instalaciones ni descargas de pesos.

No hay integración operativa, HTTP, SQL, E10 ni run_dataset_images. No se inspeccionan imágenes clínicas. Todos los entrenamientos exigen GPU visible, soft placement deshabilitado y multiplicación explícita con resultado en GPU:0. CPU sigue ejecutando operaciones de entrada/host compatibles; no se afirma que cada op corra en GPU. El sandbox devuelve GPU ausente; sólo se entrenó con acceso local a Metal fuera de ese aislamiento.

El primer control sin shuffle falló antes de entrenar por duplicar un argumento posicional/keyword. Se conserva `no-shuffle_a` como intento inválido y se repite con `no-shuffle_verified_*`; la firma se corrigió después de los 15 pares. `experiment_benchmarked.py` conserva la versión exacta medida; la corrección afecta sólo una rama no ejecutada en esos pares.

La primera carga de estrés de recibos (200×129 batches de 64 tokens con tracemalloc y medición recursiva por batch) se interrumpió por costo del propio diagnóstico. Se conserva storage_stress_interrupted.py, log y journal parcial; no se cuenta como prueba exitosa. Se ejecutó después estrés de 200 ámbitos × 8 batches de 8 tokens, y se mantienen controles específicos de bloque lleno. Ninguno es entrenamiento clínico.

## I. Dictamen

**FAIL.** Los tres overheads totales medianos cumplen ≤5%, pero no todos los pares satisfacen p95 ≤10%: DenseNet121 llega a 18,92% incluso excluyendo calentamiento; Custom CNN tiene un p95 global de 11,79% al incluir compilación. No se sustituye el límite por una mediana de p95 favorable ni se descartan pares para obtener PASS. La equivalencia y los otros controles positivos no compensan ese incumplimiento. TRACE.1B.3 no queda aprobado.

## J. Integración futura

No implementada. Primero se requiere otra revisión experimental del p95, con perfilado de compilación/sincronización y sin cambiar tolerancias ni descartar pares. No se inicia automáticamente. Sólo después de satisfacer todos los umbrales y recibir aprobación explícita: resolver tokens contra snapshot gobernado, sustituir el parche privado Keras por extensión explícita con versión soportada, validar capacidad antes de TRAIN, añadir recibos al canal aprobado E10 con owner/fencing y lectores incrementales, y proyectar run_dataset_images desde bloques verificados. Mantener separados los propósitos de las otras pasadas VAL. No reetiquetar resultados históricos ni modificar checkpoints anteriores.


## Archivos y reproducción

Se crearon este informe y `docs/audits/capstone_image_trace_1b_2_r1_evidence/`. No se modificó código operativo ni evidencia TRACE.1B.2: se verificaron los 2336 archivos del inventario original por tamaño y SHA256, todos intactos (`original_integrity.json`). La carpeta incluye:

- `design.md`, `README.md`: decisiones previas, alcance y comandos.
- `observer.py`, `ledger.py`, `recover_pending.py`: tokens, agregación y almacenamiento experimental.
- `experiment.py`, `experiment_benchmarked.py`, `reference.py`, `suite.py`, `extended.py`, `resume_controls.py`, `finish_suite.py`: arneses y versión exacta del benchmark.
- `test_ledger.py`, controles de almacenamiento/memoria, `write_failure.py`, `kill_training.py`, `drain_probe.py`, `state_probe.py`: controles sintéticos separados.
- Comparadores, `verify_results.py`, `summarize.py`, `inventory.py`, JSON de resultados, logs, manifiestos, fixtures PNG sintéticos, journals, NPZ diagnósticos y checkpoints sintéticos.

Comandos ejecutados con `.venv-metal/bin/python`: suite.py; extended.py (preserva su fallo de arnés); resume_controls.py → finish_suite.py; test_ledger.py; storage_stress.py; allocation_probe.py; capacity_allocation.py; inventory.py. Todos los entrenamientos fueron secuenciales en Metal; los controles de journal sin modelo no se presentan como ejecuciones GPU. Consultar README.md antes de reproducir: los destinos existentes se rechazan.

Sin commit/push, SQL, Docker, instalación de dependencias, descargas, edición de RUN/campañas/modelos/datasets oficiales ni ejecución automática de TRACE.1B.3. Los checksums finales describen los artefactos retenidos; no pretenden reconstruir hashes de código de arranques anteriores que no se capturaron.
