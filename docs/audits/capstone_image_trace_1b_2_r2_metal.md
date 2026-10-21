# CAPSTONE-IMAGE-TRACE.1B.2-R2 — Diagnóstico y validación Metal

Fecha: 2026-10-20. **Dictamen: FAIL. No recomendar TRACE.1B.3.** Se reprodujo la variabilidad de R1, se localizó el costo del host y se ensayó una reducción de materializaciones. El candidato conserva la equivalencia observada y los recibos, pero no acredita estabilización suficiente del p95. Sólo laboratorio sintético; sin integración operativa.

Se leyeron TRACE.1A, TRACE.1B.1, TRACE.1B.2 y R1 y se inspeccionaron sus arneses, comparadores, tiempos y verificadores. [Diseño previo](capstone_image_trace_1b_2_r2_evidence/design.md), [decisión basada en mediciones](capstone_image_trace_1b_2_r2_evidence/optimization_decision.md), [límites del profiling](capstone_image_trace_1b_2_r2_evidence/profiling_limitations.md).

## A. Reproducción R1 sin cambios

Se ejecutaron 15 pares nuevos, 30 procesos independientes, orden AB, BA, AB, BA, AB por arquitectura. Se invocó directamente `experiment_benchmarked.py` de R1 con su observer.py y ledger.py originales; fuentes y comandos quedaron sellados antes de iniciar. VGG16 y DenseNet121 incluyen base y fine-tuning. Todas las comparaciones A/B pasaron. Las comprobaciones posteriores contra la ciencia histórica R1 y entre brazos A repetidos también pasan (`historical_*_science.json`, `reproduction_aa_*_science.json`).

| Arquitectura | Total mediano | Peor p95 global | Peor p95 warm | Cumple rendimiento |
|---|---:|---:|---:|---|
| custom_cnn | 3.22% | 12.81% | 7.98% | No |
| vgg16 | 3.08% | 6.48% | 11.00% | No |
| densenet121 | -0.85% | 4.01% | 22.63% | No |

| Arquitectura/par | Orden | Total A/B (s) | Overhead total | Overhead p95 global | Overhead p95 warm |
|---|---|---:|---:|---:|---:|
| custom_cnn/1 | AB | 5.372 / 5.307 | -1.20% | 4.48% | -1.34% |
| custom_cnn/2 | BA | 4.807 / 5.033 | 4.70% | 12.81% | 0.00% |
| custom_cnn/3 | AB | 4.973 / 5.133 | 3.22% | 7.98% | -1.09% |
| custom_cnn/4 | BA | 5.091 / 5.161 | 1.38% | 0.58% | 7.17% |
| custom_cnn/5 | AB | 5.073 / 5.249 | 3.47% | 8.16% | 7.98% |
| vgg16/1 | AB | 7.028 / 7.282 | 3.62% | 6.48% | -10.88% |
| vgg16/2 | BA | 6.986 / 7.310 | 4.63% | 1.59% | 5.22% |
| vgg16/3 | AB | 7.080 / 7.075 | -0.07% | -4.52% | -9.44% |
| vgg16/4 | BA | 6.975 / 7.164 | 2.72% | -2.59% | -1.33% |
| vgg16/5 | AB | 6.947 / 7.161 | 3.08% | -2.21% | 11.00% |
| densenet121/1 | AB | 55.942 / 55.463 | -0.85% | -3.91% | -1.79% |
| densenet121/2 | BA | 56.841 / 55.566 | -2.24% | -5.91% | -12.18% |
| densenet121/3 | AB | 62.215 / 58.625 | -5.77% | -2.78% | 6.48% |
| densenet121/4 | BA | 56.080 / 57.920 | 3.28% | 4.01% | -3.69% |
| densenet121/5 | AB | 59.098 / 69.127 | 16.97% | 3.36% | 22.63% |

Se reprodujo un incumplimiento global en Custom CNN y warm en DenseNet121; también apareció uno warm en VGG16. No son exactamente los mismos porcentajes de R1 y no se presentan como idénticas realizaciones de un mecanismo interno. Fuente completa: [reproduction_performance.json](capstone_image_trace_1b_2_r2_evidence/reproduction_performance.json), incluidos throughput, RSS y journal por brazo. Todos los pares permanecen retenidos.

## B. Perfilado y cobertura

Se ejecutaron 15 diagnósticos R1: baseline, transporte solo, agregación en memoria, agregación con serialización sin disco y observador durable completo, para las tres arquitecturas. Los 15 pasan comparación de configuración, manifiesto, registros científicos, checkpoints y estados guardados frente a A de reproducción. Transporte solo no agrega recibos; memoria y serialización conservan costos residuales de hashing/capacidad de Aggregator.emit. **Las variantes no durables son exclusivamente aislamientos, nunca candidatos.** Hay una corrida por variante en orden fijo: sus diferencias de tiempo total no aíslan causalmente efectos de orden/cache.

Se capturaron reloj monotónico, funciones científicas por batch, contadores de trazado, cada materialización numpy, agregación, construcción/sellado, canonical/hash, escritura, fsync, rename, apertura/cierre y verificación. cProfile conserva tiempos propios/acumulados y llamadas de Counter/deep_size/serialización. XPlane conserva lectura/decode, lookup, operadores de preprocessing/augmentation y eventos shuffle/batch/prefetch/entrega. JSON incluye cantidad, total, mediana, p95 y máximo; ver [profile_summary.json](capstone_image_trace_1b_2_r2_evidence/profile_summary.json), [causal_analysis.json](capstone_image_trace_1b_2_r2_evidence/causal_analysis.json), [xplane_summary.json](capstone_image_trace_1b_2_r2_evidence/xplane_summary.json) y protobuf/timelines originales.

Un perfil adicional exclusivamente de recibos midió 12 recuperaciones exactas de pending: mediana 0.274 ms, p95 0.374 ms y máximo 0.429 ms. `recovery_profile.json` conserva cada duración y verifica bytes, prefijo, batch y estado parcial. Son simulaciones de journal, no entrenamientos ni benchmark de aceptación.

Mediciones inclusivas del observador R1 completo, **bajo profiling**, sin sumarlas como categorías independientes:

| Arquitectura | Métricas numpy: llamadas / total ms | Tokens numpy: total ms | Agregar: total / máximo ms | Store.put: total / máximo ms | fsync: total / máximo ms |
|---|---:|---:|---:|---:|---:|
| custom_cnn | 144 / 40.721 | 4.833 | 2.974 / 0.304 | 6.700 / 0.975 | 1.706 / 0.368 |
| vgg16 | 288 / 71.765 | 8.274 | 5.616 / 0.270 | 12.254 / 0.916 | 3.145 / 0.351 |
| densenet121 | 288 / 81.551 | 10.090 | 6.756 / 1.017 | 14.112 / 0.960 | 4.421 / 0.374 |

Ejemplos de intervalos host de XPlane; incluyen las pasadas adicionales que TRAIN ya realiza y no equivalen a tiempo exclusivo por batch:

| Arquitectura | Lookup mediana/p95/máximo (µs) | Lectura/decode p95/máximo (µs) | IteratorGetNext p95/máximo (ms) |
|---|---:|---:|---:|
| custom_cnn | 2.0 / 5.0 / 12.0 | 76.8 / 135.0 | 5.120 / 7.568 |
| vgg16 | 2.0 / 5.0 / 20.0 | 81.0 / 310.0 | 3.225 / 5.702 |
| densenet121 | 2.0 / 5.0 / 16.0 | 79.5 / 206.0 | 3.405 / 7.396 |

Shuffle, batch, prefetch y augmentation están desglosados en xplane_summary; son intervalos anidados de varios hilos. La categoría preprocessing cubre principalmente resize y no toda la normalización: operadores adicionales como RealDiv se conservan por nombre. La categoría automática forward_backward puede incluir el MatMul de la sonda inicial y **no mide el forward/backward completo del modelo**.

XPlane sólo expuso `/host:CPU` y `Task Environment`, sin plano de kernels GPU. `xcrun --find xctrace` devolvió 72; no se instaló software. Dos intentos de separar forward/backward/apply_gradients con marcadores en las llamadas originales fallaron en el primer Custom CNN A con `stream cannot wait for itself`, incluso ubicando explícitamente el marcador en CPU. Se preservan ambas versiones, sellos, logs y outcomes como **diagnósticos inválidos**, no como equivalencia o rendimiento exitosos. No retornó un batch completo; los efectos internos previos al error no se cuantifican. Separación de kernels, tiempo de compilación Metal individual y aplicación aislada del optimizador: **NO DEMOSTRADOS**. El intervalo de función científica sí está medido, pero incluye entrega, runtime y sincronización.

## C. Diagnóstico causal

| Hipótesis | Resultado respaldado y límite |
|---|---|
| H1: compilación/retrazado | Los primeros train/test muestran creación de trazas; TRAIN llega a 2 y test a 1 por fase en los perfiles observados. Los primeros batches incompletos permanecen lentos tras el calentamiento R1 y no aumentan esos contadores. Se localiza latencia de primera ejecución de forma dentro de la función original; no se demuestra que sea una compilación interna Metal concreta. |
| H2: materialización/sincronización | Se midieron 144/288 llamadas adicionales de métricas dentro del observador y se eliminaron. El perfil posterior muestra que casi todo su tiempo se desplaza a la primera lectura del arnés común, no que desaparezca. No explican los picos grandes; cada llamada tampoco prueba una sincronización GPU distinta. |
| H3: journal/I/O | Store.put, fsync y agregación tienen costos medidos pequeños frente a los batches de cientos de ms o segundos. Los batches lentos existen sin journal. No hay evidencia suficiente para atribuir esos picos a durabilidad; no se alteró el almacenamiento. |
| H4: identidad | Lookup host mediano de 2 µs y máximos de 12–20 µs en los perfiles completos. No se observó un lookup de magnitud comparable a los picos. No se extrapola a manifiestos grandes. |
| H5: variabilidad externa | Load average/vm_stat/pmset se capturaron antes/después. pmset no registró advertencias, pero no es termometría ni prueba de ausencia de throttling. No se atribuye causalmente a temperatura, memoria o carga externa una fracción no medida. |

En los tiempos históricos de R1, el batch warm más lento de los diez brazos por arquitectura corresponde a una primera forma incompleta (índices 4, 7, 20 o 23 según arquitectura/fase). En el diagnóstico DenseNet121 baseline, esos primeros batches tardaron aproximadamente 1,23–1,32 s frente a 0,037–0,055 s en repeticiones posteriores de su forma; no hubo nuevo trazado Python en aquéllos. El perfil completo R1 también presenta ese patrón. El máximo trabajo fuera de la función original, dentro del batch medido, fue aproximadamente 6,2 ms en ese perfil B. Esto localiza una parte importante de la variabilidad en la ejecución/runtime original, **sin identificar por completo el mecanismo nativo causal**. No se reclasifican los batches lentos como calentamiento para aprobar.

## D. Optimización experimental

Se quitó únicamente el bucle que llamaba numpy a cada métrica dentro de Observer.execute. Se mantiene la materialización del token del mismo batch y sus dependencias de todos los resultados originales y optimizer.iterations. La confirmación sigue después del retorno y de esa materialización. No cambian forward, loss, gradientes, optimizador, inicialización, seed, orden, augmentation, callbacks científicos, pasos ni checkpoints.

Tres perfiles adicionales del candidato pasan ciencia y verifican una materialización de token por batch y cero llamadas del bucle eliminado. La reducción de llamadas es verificable; no se atribuye toda diferencia entre series a ese cambio. `ledger.py` conserva exactamente los bytes de R1: mismos límites 256 KiB/8192 pares/128 batches, mismo drenaje máximo al retorno disponible después de 5 s, mismo fsync/rename/recovery. No se añadieron colas ni tareas asíncronas. [candidate_v1.json](capstone_image_trace_1b_2_r2_evidence/candidate_v1.json) y sellos de campañas fijan fuentes antes de medir.

El resultado posterior limita la justificación inicial: las lecturas de métricas del arnés costaban 0,506/0,973/0,900 ms cuando R1 ya las había materializado; con R2 cuestan 38,836/71,818/79,660 ms. Por tanto, gran parte del costo inicialmente localizado en el observador se desplaza al arnés. No se demuestra un ahorro neto de 40–82 ms. La diferencia de tiempo fuera de la función científica entre perfiles es sólo unos 4–5 ms por corrida e incluye overhead del propio profiler; tampoco prueba ahorro causal limpio. [optimization_outcome.md](capstone_image_trace_1b_2_r2_evidence/optimization_outcome.md) conserva este resultado sin reescribir la decisión previa. No se presume una implementación interna concreta de caché/copia.

El arnés final reutiliza la firma no-shuffle corregida que ya estaba en R1; esa rama está inactiva en ambos brazos del benchmark. El camino baseline ejecutado conserva la ciencia original. La copia exacta experiment_benchmarked.py se conserva y se usa en reproducción/perfiles. No se cambió el código medido durante cada campaña.

## E. Equivalencia científica

Todos los conteos siguientes son comprobaciones, no entrenamientos. Totales/aprobadas:

| Arquitectura | A/A | A/B | Referencia exacta x/y/tokens + scores/gradientes |
|---|---:|---:|---:|
| custom_cnn | 618/618 | 618/618 | 241/241 |
| vgg16 | 1094/1094 | 1094/1094 | 301/301 |
| densenet121 | 3370/3370 | 3370/3370 | 231/231 |

Se repitieron controles de interferencia frente a las ejecuciones sin captura, no-augment, no-shuffle, bytes duplicados, dos fases, últimos batches, EarlyStopping y selección. Identidades, orden, x/y, augmentation y decisiones discretas coinciden exactamente en las capturas aplicables. Scores, gradientes, pérdidas, métricas y variables comparadas cumplen atol=1e-7, rtol=1e-6; no se ampliaron tolerancias.

`state_comparison.json` pasa **6602** comprobaciones de pesos y optimizador iniciales/finales y restauración directa contra EarlyStopping.best_weights. Máxima diferencia absoluta observada: 0. Checkpoints y decisiones se comparan sin reinferencia. Los seis controles A/B de estados capturan scores y gradientes efectivamente retornados en **GPU:0** (16 pasos por brazo CNN y 32 por brazo transfer). No se atribuye observación a logits pre-sigmoid, todos los estados RNG/TF, cada peso/optimizador intermedio ni kernels internos.

## F. Identidad, recibos y fallos

Se reejecutó la matriz R1 completa, sin eliminar pruebas: 15 unitarias de ledger; identidad explícita; 56 registros con dos muestras distintas de bytes idénticos; manifiestos/hash/cadena, multiplicidad, fases/épocas; replay/idempotencia, conflictos, gaps/solapamiento; recuperación de pending completo/truncado; capacidad; prefetch sin consumo; fallos antes/durante/después; escritura fallida y SIGKILL; estrés y duración de 30 épocas.

La verificación final de recibos pasa **5593** comprobaciones. Los aislamientos declarados no durables se excluyen de este verificador de candidatos, sin excluir ninguna prueba R1. Fallos before/during/after: 0/0/1 batches confirmados, siempre parcial. Durante el paso, efectos científicos desconocidos; cero recibos no acredita cero procesamiento.

El fallo después de fsync y antes de rename dejó un pending y cero bloques finales; recuperación exacta conservó 5 batches y cierre parcial, sin repetir ciencia. SIGKILL tras el primer bloque conservó 5 batches y ámbito abierto. El journal truncado conserva el prefijo y la cola desconocida. Prefetch preparó 8 imágenes y confirmó cero batches/eventos. La identidad ausente se rechazó sin inventar un token.

Sondas de primer batch confirmado→bloque durable: CNN 0.389 s, VGG16 0.228 s, DenseNet121 0.975 s. No confundir con max_drain_seconds, que incluye tiempo anterior a la primera confirmación. No hay atomicidad GPU–journal, garantía de pérdida eléctrica, transporte E10 ni persistencia SQL acreditados por este laboratorio.

## G. Benchmark final limpio

15 pares nuevos, 30 procesos independientes secuenciales, sin profiler. Mismos fixture, seeds/configuración y criterios. El total incluye construcción, pipeline, entrenamiento y pasadas originales, checkpoints, observador, serialización, durabilidad y verificación final; excluye arranque del intérprete y creación del fixture en ambos brazos. P95 usa numpy.percentile lineal como R1. Warm excluye sólo índices 0/5 CNN y 0/5/16/21 transfer; no excluye primeros batches incompletos. Throughput cuenta 112/224 participaciones TRAIN + VAL interna por total, aunque éste incluye las otras pasadas originales.

Umbrales inmutables: mediana total ≤5% por arquitectura; **cada par** p95 global y warm ≤10%; agregador ≤32 MiB. Overhead = 100×(B/A−1), calculado separadamente por par. Porcentajes negativos no prueban aceleración.

| Arquitectura | Total mediano | Peor p95 global | Peor p95 warm | Cumple rendimiento |
|---|---:|---:|---:|---|
| custom_cnn | 2.37% | 7.86% | 11.77% | No |
| vgg16 | 3.72% | 3.74% | 3.61% | Sí |
| densenet121 | -0.36% | 10.40% | 11.13% | No |

| Arquitectura/par | Orden | Total A/B (s) | Overhead total | Overhead p95 global | Overhead p95 warm |
|---|---|---:|---:|---:|---:|
| custom_cnn/1 | AB | 4.165 / 4.292 | 3.05% | 6.24% | -2.32% |
| custom_cnn/2 | BA | 4.107 / 4.201 | 2.28% | 4.28% | 11.77% |
| custom_cnn/3 | AB | 4.137 / 4.261 | 3.01% | 7.86% | -6.81% |
| custom_cnn/4 | BA | 4.119 / 4.211 | 2.23% | 4.00% | 3.55% |
| custom_cnn/5 | AB | 4.127 / 4.225 | 2.37% | 4.49% | -4.93% |
| vgg16/1 | AB | 5.929 / 6.170 | 4.07% | 1.37% | 0.92% |
| vgg16/2 | BA | 6.041 / 6.266 | 3.72% | 3.74% | 3.61% |
| vgg16/3 | AB | 6.006 / 6.148 | 2.37% | -0.40% | -1.83% |
| vgg16/4 | BA | 5.939 / 6.179 | 4.04% | 3.51% | 1.68% |
| vgg16/5 | AB | 6.028 / 6.203 | 2.91% | 1.78% | 2.50% |
| densenet121/1 | AB | 44.056 / 42.418 | -3.72% | -2.91% | 1.33% |
| densenet121/2 | BA | 41.221 / 41.072 | -0.36% | 1.94% | -3.13% |
| densenet121/3 | AB | 40.811 / 43.333 | 6.18% | 10.40% | 11.13% |
| densenet121/4 | BA | 42.937 / 43.034 | 0.23% | 0.45% | 3.79% |
| densenet121/5 | AB | 42.550 / 42.189 | -0.85% | -2.53% | 8.93% |

Recursos y costo durable por par:

| Arquitectura/par | Throughput A/B (participaciones/s) | Pico RSS A/B (GiB) | Eventos/bloques B | Máximo evento (bytes) | Escritura B (ms) |
|---|---:|---:|---:|---:|---:|
| custom_cnn/1 | 26.89 / 26.09 | 1.668 / 1.664 | 12/4 | 1143 | 3.767 |
| custom_cnn/2 | 27.27 / 26.66 | 1.663 / 1.671 | 12/4 | 1143 | 3.894 |
| custom_cnn/3 | 27.08 / 26.29 | 1.670 / 1.663 | 12/4 | 1143 | 3.953 |
| custom_cnn/4 | 27.19 / 26.60 | 1.660 / 1.671 | 12/4 | 1143 | 3.858 |
| custom_cnn/5 | 27.14 / 26.51 | 1.663 / 1.666 | 12/4 | 1143 | 3.936 |
| vgg16/1 | 37.78 / 36.31 | 1.886 / 1.893 | 24/8 | 1145 | 7.774 |
| vgg16/2 | 37.08 / 35.75 | 1.887 / 1.962 | 24/8 | 1145 | 8.536 |
| vgg16/3 | 37.30 / 36.43 | 1.893 / 1.900 | 24/8 | 1145 | 7.672 |
| vgg16/4 | 37.72 / 36.25 | 1.881 / 1.895 | 24/8 | 1145 | 8.479 |
| vgg16/5 | 37.16 / 36.11 | 1.883 / 1.896 | 24/8 | 1145 | 8.380 |
| densenet121/1 | 5.08 / 5.28 | 8.662 / 8.742 | 24/8 | 1151 | 7.876 |
| densenet121/2 | 5.43 / 5.45 | 8.709 / 8.720 | 24/8 | 1151 | 8.734 |
| densenet121/3 | 5.49 / 5.17 | 8.714 / 8.720 | 24/8 | 1151 | 8.608 |
| densenet121/4 | 5.22 / 5.21 | 8.657 / 8.709 | 24/8 | 1151 | 9.332 |
| densenet121/5 | 5.26 / 5.31 | 8.703 / 8.725 | 24/8 | 1151 | 8.984 |

Fuentes: [final_performance.json](capstone_image_trace_1b_2_r2_evidence/final_performance.json), timings/outcomes/environment/observer_summary de cada brazo, [comparación gráfica](capstone_image_trace_1b_2_r2_evidence/performance_pairs.svg). JSON también conserva mediana/p95/máximo de batches, warm, recuperación y cierres. write_seconds se solapa con close_seconds; no sumarlos. Se conservan todos los pares desfavorables.

Incumplimientos p95 finales: custom_cnn, par 2: global 4.28%, warm 11.77%; densenet121, par 3: global 10.40%, warm 11.13%.

## H. Memoria, entorno e integridad

Capacidad aislada de 8192 pares: pico tracemalloc **2.036 MiB**, incremento de pico RSS **5.578 MiB**, cota de objetos/reservas **2.282 MiB**, evento máximo 112926 bytes. No se equiparan JSON, objetos Python y RSS. 1000 ámbitos/8000 batches, verificación incremental y sonda de asignaciones se conservaron. La enumeración pathlib/internado de nombres no se declara O(1) para historia arbitraria.

30 épocas GPU reales: agregador alcanzable 1427 bytes al principio y 1427 al final, sin crecimiento observado de esa estructura; RSS del proceso puede crecer y no se atribuye al agregador. Mapa Python/payload aproximadamente 45 KiB para 56 identidades, reportado separadamente; overhead interno de tabla nativa no medido. API GPU allocator devuelve ceros, que **no son una medición confiable de memoria GPU**. No se extrapola a poblaciones clínicas grandes.

Entorno por proceso: Apple M4 Max, macOS-26.7.1-arm64-arm-64bit; Python .venv-metal, TensorFlow 2.17.1, Keras 3.15.1, tensorflow-metal 1.2.0, NumPy 1.26.4; execution_mode=local_python, GPU exigida y soft placement deshabilitado. CPU ejecuta entrada/host; la evidencia GPU del modelo se obtuvo del mismo forward/gradientes, no sólo de la sonda inicial. Sólo imágenes sintéticas 37 TRAIN/19 VAL, 32×32 RGB, batch 8, seed 42, generador 20261020, pesos none, float32; sin descargas.

Se verificaron por tamaño/SHA256 los **2336 archivos de TRACE.1B.2 y 12969 de R1**, antes de los diagnósticos y al cierre, y sus inventarios conservaron hash. Se verificaron los sellos de código/órdenes y 220 fuentes operativas/instaladas registradas antes de las campañas posteriores. [closeout.json](capstone_image_trace_1b_2_r2_evidence/closeout.json) pasa 497 comprobaciones de integridad/cobertura; esto **no convierte un FAIL de rendimiento en PASS**. Los hashes del arnés de reproducción sí se registraron antes del primer proceso; el snapshot ampliado de fuentes operativas se tomó después de reproducción y antes de diagnósticos, sin presentarlo como anterior a R2-A.

## I. Dictamen

**FAIL.** La reducción de materializaciones conserva las dimensiones científicas observadas, identidad, recibos y memoria acotada en el fixture. No satisface todos los límites p95 finales. La causa nativa exacta de la variabilidad de primeras formas tampoco queda demostrada. No se sustituyen máximos individuales por medianas favorables, no se omiten pares y no se cambian tolerancias, baseline científico ni calentamiento.

## J. Recomendación y entregables

No considerar aprobado TRACE.1B.3. Para otra revisión experimental se necesita observabilidad nativa compatible con Metal que permita distinguir primera especialización de forma/compilación/ejecución y una nueva validación estricta completa. No cambiar el fixture, el warm-up ni la durabilidad para conseguir aprobación. La optimización local retenida es un resultado experimental, no una habilitación operativa.

Se crearon este informe y `capstone_image_trace_1b_2_r2_evidence/`: diseños/sellos, fuentes, 30 pares de reproducción/final combinados, 18 perfiles válidos, dos intentos de marcadores inválidos, matriz R1 reejecutada, comparadores/verificadores, logs, fixtures, checkpoints sintéticos, NPZ, journals, XPlane, tablas y figura. [README](capstone_image_trace_1b_2_r2_evidence/README.md) explica comandos y destinos inmutables. `inventory.json` registra los artefactos finales; no ejecutar los runners sobre esos destinos existentes.

Sin modificación de código operativo TRAIN/EVALUATE/TEST/EXPLAIN, PostgreSQL, campañas/RUN, datasets clínicos ni checkpoints históricos. No se pobló run_dataset_images. Sin instalaciones, Docker para entrenar, commit, push ni avance a TRACE.1B.3.
