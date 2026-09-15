# E9.3 — Desarrollo de memoria y contrato, 2026-09-14

**A — Memoria: PARCIAL (diagnóstico insuficiente para una corrección causal). B — Contrato operativo: APROBADO en desarrollo y pruebas aisladas; instalación operativa pendiente.** No está preparado todavía el intento operativo, porque A no cumple aceptación. E9.2 sigue parcial; E9 no aprobada.

Snapshot final 2026-09-14 23:26:23.193775+00:00 UTC / America/Santiago UTC−3. Campaña paused, 36 experimentos:31 pendientes y5 fallidos;0 activos/completados/verificados;5 intentos. Sin coordinador ni worker TRAIN. No hubo reservas/registro de revisiones operativos, migración persistente, --resume ni reinicios.

Dataset obligatorio `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`: coincide en campaña, matriz y las cinco sesiones/experimentos con intento. Se conservaron materialización e15dc166-1c4b-558e-b77b-727b1783430c, sello/split y fingerprints. dataset_train.json conserva freeze_contract,64 muestras de TRAIN con source_record_id/path/hash; las dos ramas del diagnóstico usaron exactamente esas mismas muestras. Fingerprints canónicos de población y asignaciones coinciden con el sello. No se leyó contenido de archivos TEST, sólo metadatos de integridad de particiones. No se regeneró el split.

## A — Diagnóstico

Límites predefinidos por hijo:150s, RSS3GiB, cgroup5GiB;2 pasos train_on_batch,12 pases de predicción y1 checkpoint temporal. Dos procesos separados, limitador supervisa sólo su propio hijo cada0,1s; puede terminar únicamente ese diagnóstico. No se alcanzó ningún límite. OOM del cgroup permaneció5; no se provocó OOM nuevo. GPU enumerada vacía. Son fixtures técnicos sobre un subconjunto real de TRAIN, no experimentos ni métricas científicas. No se insertó TRAIN, no se guardaron métricas científicas. Checkpoint temporal exclusivamente diagnóstico eliminado al salir de TemporaryDirectory.

Muestras:32 por clase, nombres ordenados,64 total. Arquitectura/configuración del representante real, batch64, resolución200, optimizador/semilla congelados. El diagnóstico usa tensor fijo de ese subconjunto y dos pasos, sin reproducir shuffle/aumentación ni todas las callbacks/épocas del flujo científico. Es una simplificación técnica declarada, no una modificación del experimento; no acredita reproducibilidad del TRAIN completo. La inferencia alternativa conserva sublotes32 usados por predict y difiere sólo en evitar el adaptador repetido de predict.

| Medida | Antes: predict | Alternativa: predict_on_batch |
|---|---:|---:|
| Duración(s) | 13.87 | 13.00 |
| Pico RSS supervisor(MiB) | 2985.6 | 2900.9 |
| RSS al terminar paso2(MiB) | 1446 | 1462 |
| RSS primer pase(MiB) | 1573 | 1534 |
| RSS pase12(MiB) | 2056 | 1909 |
| RSS después de checkpoint(MiB) | 2089 | 1963 |
| Máxima diferencia absoluta de salidas | 0 | 0 |

smaps_rollup registra RSS/PSS, páginas compartidas/privadas; incluye memoria nativa de TensorFlow, no sólo Python. Pico muestreado cada0,1s, no máximo absoluto garantizado. memory.current incluye memoria/caché del cgroup y no se equipara a RSS del worker. Hay reducción observada pero crecimiento en ambas ramas: sin réplicas/ventana larga ni aislamiento de allocator/grafos/caché no se demuestra fuga o causa del OOM. **No se aplicó la alternativa como solución de memoria.** No se estima un mínimo suficiente de RAM a partir de esta ventana.

Inspección: datos físicos usan map/prefetch AUTOTUNE sin cache explícita; la función TFDS tiene shuffle pero no es la ruta de esta campaña. El modelo se crea una vez por hijo; cada intento ya tiene proceso separado. collect_predictions llama predict por lote; callback clínico y persistencia hacen dos recorridos VAL adicionales por época. Historial retiene escalares por época; scores locales no se añaden como tensores al historial; PostgreSQL recibe arrays estructurados. Se guarda checkpoint por época. La carga del modelo seleccionado ocurre después de phase, que ninguno de los cinco fallidos alcanzó: esa carga final no explica por sí sola esos fallos. No se observó supervivencia de hijos entre intentos; no se justificó clear_session periódico, GC ni aumento de RAM.

Siguiente diagnóstico requerido: separar buffers AUTOTUNE y asignaciones/caché de predicción en una ventana acotada más larga, con el mismo TRAIN identificado y medición de memoria nativa. No repetir TRAIN completo para obtener una atribución. Retener como probable RAM por intento hasta disponer de PID víctima/evento; cinco OOM del cgroup están confirmados, GPU OOM no.

## B — Implementación y pruebas

controlled.py implementa revisión explícita, dry-run sin reserva, registro explícito, reserva única, ejecución de un hijo y recuperación sin relanzamiento. worker.py resuelve sólo la revisión registrada ligada al intento; repository.py crea campaign_id explícito después de instalar extensión. El parche de exit code previo se conserva. La migración nueva no reescribe revisiones antiguas; tabla de revisiones y solicitudes append-only, FKs, triggers de identidad/pausa y binding diferido. Detalles, comandos y límites en operacion.md.

La fuente del contrato original y de los cinco intentos permanece d8569d8faaa80eca42b130e6096203d851e2c663b4cdb8cd599dda950fbe6430. La nueva huella propuesta es 75d0b162d4cd13daaee24b8fe745c7108a91e6c6b1fb3e9beef222602e510865. No se escribieron esos hashes en registros históricos ni se registró operativamente la propuesta. Fuente antigua recuperable desde HEAD inicial y campaign_original.py.txt de recuperación previa; manifiesto registra archivos actuales.

Ejecutado en Compose: **55 passed,1 deselected,2 warnings de deprecación protobuf**. Incluye19 pruebas PostgreSQL nuevas,13 regresiones PostgreSQL E5 y23 controles locales afectados. La prueba pública E5 se excluyó explícitamente; no se declara ejecutada. Casos: idempotencia, requests concurrentes iguales/distintas, revisión desconocida/hash incorrecto, contrato científico y entorno incompatible, dataset/miembro incorrectos, activo/budget, dry-run sin reserva, FK campaign_id, immutabilidad, pausa/resume bloqueado, éxito/fallo sin encadenar, fallo de lanzamiento, recuperación exige ausencia y enlace worker. La prueba de presupuesto se apoya en la regresión E5; no se presenta una prueba nueva específica de agotamiento controlado.

Esquemas sintéticos E4 con rollback/savepoints; los casos de concurrencia hacen visible sólo ese esquema y usan conexiones distintas. Limpieza confirmada:0 esquemas capstone_test_e4_* al cierre. No se probaron reservas sobre campaña real. SQL offline generado por Alembic para20260912_02:20260914_01; es evidencia separada de las pruebas PostgreSQL, no instalación. Primera prueba de registro detectó reutilización de parámetro JSON/texto; se corrigió con parámetros independientes y la suite final pasó.

Dry-run real dio writes0, next_ordinal2, installedfalse, revision_registeredfalse, execution_readyfalse; controles de dataset/miembro sí pasaron. Rechazó primero PYTHONHASHSEED ausente; repetición correcta con42 sin cambiar contrato. Propuesta no equivale a autorización de reserva ni a solución de memoria.

## Cierre

Migración persistente sigue20260912_02; nuevas tablas ausentes. /ready devuelve503 exclusivamente por migrations:not_ready al estar preparado un head nuevo; database/storage ready. Es un impacto real del desarrollo, documentado para instalación autorizada; no se ocultó el validador ni se reinició servicio.

Publicación81d69942-17eb-4999-a6bd-2b05779a65a4 y deploymentcf2f20d3-a1e0-499c-b5ab-501b7c1ae198 idénticos antes/después. Matriz, dataset e intentos operativos sin cambios. TEST cerrado, sin EVALUATE/EXPLAIN/ensembles ni E9.4. Campaña permanece paused. No se declara E9 aprobada ni OOM resuelto.
