"""Render the final report from retained evidence, without rerunning science."""
import json
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parent
E='capstone_image_trace_1b_2_r2_evidence'
ARCHES=['custom_cnn','vgg16','densenet121']
def read(name):return json.loads((ROOT/name).read_text())
repro=read('reproduction_performance.json');final=read('final_performance.json')
state=read('state_comparison.json');receipts=read('receipt_verification.json')
capacity=read('capacity_allocation.json');profiles=read('profile_summary.json')
causal=read('causal_analysis.json');native=read('xplane_summary.json')
duration=[json.loads(line) for line in (ROOT/'duration_30_epochs/epoch_memory.jsonl').read_text().splitlines()]
gc=[json.loads(line) for line in (ROOT/'memory_gc.jsonl').read_text().splitlines()]
closeout=read('closeout.json')
recovery_profile=read('recovery_profile.json')['recovery']
verdict='FAIL' if any(not final[a]['passed'] for a in ARCHES) else 'NO DEMOSTRADO'

def summary(data):
    s='| Arquitectura | Total mediano | Peor p95 global | Peor p95 warm | Cumple rendimiento |\n|---|---:|---:|---:|---|\n'
    for a in ARCHES:
        d=data[a];s+=f"| {a} | {d['total_median_percent']:.2f}% | {d['worst_full_p95_percent']:.2f}% | {d['worst_warm_p95_percent']:.2f}% | {'Sí' if d['passed'] else 'No'} |\n"
    return s

def pairs(data):
    s='| Arquitectura/par | Orden | Total A/B (s) | Overhead total | Overhead p95 global | Overhead p95 warm |\n|---|---|---:|---:|---:|---:|\n'
    for a in ARCHES:
        for p in data[a]['pairs']:
            s+=f"| {a}/{p['pair']} | {p['order']} | {p['arms']['a']['total']:.3f} / {p['arms']['b']['total']:.3f} | {p['total_percent']:.2f}% | {p['full_p95_percent']:.2f}% | {p['warm_p95_percent']:.2f}% |\n"
    return s

def resources(data):
    s='| Arquitectura/par | Throughput A/B (participaciones/s) | Pico RSS A/B (GiB) | Eventos/bloques B | Máximo evento (bytes) | Escritura B (ms) |\n|---|---:|---:|---:|---:|---:|\n'
    for a in ARCHES:
        for p in data[a]['pairs']:
            x,y=p['arms']['a'],p['arms']['b'];o=y['observer']
            s+=f"| {a}/{p['pair']} | {x['throughput']:.2f} / {y['throughput']:.2f} | {x['rss_peak_bytes']/2**30:.3f} / {y['rss_peak_bytes']/2**30:.3f} | {o['events']}/{o['blocks']} | {o['max_event_bytes']} | {o['write_seconds']*1000:.3f} |\n"
    return s

host='| Arquitectura | Métricas numpy: llamadas / total ms | Tokens numpy: total ms | Agregar: total / máximo ms | Store.put: total / máximo ms | fsync: total / máximo ms |\n|---|---:|---:|---:|---:|---:|\n'
lookup='| Arquitectura | Lookup mediana/p95/máximo (µs) | Lectura/decode p95/máximo (µs) | IteratorGetNext p95/máximo (ms) |\n|---|---:|---:|---:|\n'
for a in ARCHES:
    p=profiles[f'diagnostic_{a}_full']['components'];m=p['numpy/observer.py:execute:96'];t=p['numpy/observer.py:execute:93'];g=p['Aggregator.add'];w=p['Store.put'];f=p['os.fsync']
    host+=f"| {a} | {m['count']} / {m['total']*1000:.3f} | {t['total']*1000:.3f} | {g['total']*1000:.3f} / {g['maximum']*1000:.3f} | {w['total']*1000:.3f} / {w['maximum']*1000:.3f} | {f['total']*1000:.3f} / {f['maximum']*1000:.3f} |\n"
    p=native[f'diagnostic_{a}_full_xplane']['components'];l=p['lookup'];r=p['read_decode'];d=p['delivery']
    lookup+=f"| {a} | {l['median']*1e6:.1f} / {l['p95']*1e6:.1f} / {l['maximum']*1e6:.1f} | {r['p95']*1e6:.1f} / {r['maximum']*1e6:.1f} | {d['p95']*1e3:.3f} / {d['maximum']*1e3:.3f} |\n"

science='| Arquitectura | A/A | A/B | Referencia exacta x/y/tokens + scores/gradientes |\n|---|---:|---:|---:|\n'
for a in ARCHES:
    aa,ab,ref=(read(a+n) for n in ['_aa.json','_ab.json','_reference_exact.json'])
    science+=f"| {a} | {aa['total']}/{aa['total']-aa['failed']} | {ab['total']}/{ab['total']-ab['failed']} | {ref['total']}/{ref['total']-ref['failed']} |\n"
violations=[f"{a}, par {p['pair']}: global {p['full_p95_percent']:.2f}%, warm {p['warm_p95_percent']:.2f}%" for a in ARCHES for p in final[a]['pairs'] if not p['p95_pass']]
drains={a:read(f'{a}_drain_probe/drain_measurement.json')['max_confirmed_to_durable_seconds'] for a in ARCHES}
env=read('custom_cnn_b/environment.json')

text=f'''# CAPSTONE-IMAGE-TRACE.1B.2-R2 — Diagnóstico y validación Metal

Fecha: 2026-10-20. **Dictamen: {verdict}. No recomendar TRACE.1B.3.** Se reprodujo la variabilidad de R1, se localizó el costo del host y se ensayó una reducción de materializaciones. El candidato conserva la equivalencia observada y los recibos, pero no acredita estabilización suficiente del p95. Sólo laboratorio sintético; sin integración operativa.

Se leyeron TRACE.1A, TRACE.1B.1, TRACE.1B.2 y R1 y se inspeccionaron sus arneses, comparadores, tiempos y verificadores. [Diseño previo]({E}/design.md), [decisión basada en mediciones]({E}/optimization_decision.md), [límites del profiling]({E}/profiling_limitations.md).

## A. Reproducción R1 sin cambios

Se ejecutaron 15 pares nuevos, 30 procesos independientes, orden AB, BA, AB, BA, AB por arquitectura. Se invocó directamente `experiment_benchmarked.py` de R1 con su observer.py y ledger.py originales; fuentes y comandos quedaron sellados antes de iniciar. VGG16 y DenseNet121 incluyen base y fine-tuning. Todas las comparaciones A/B pasaron. Las comprobaciones posteriores contra la ciencia histórica R1 y entre brazos A repetidos también pasan (`historical_*_science.json`, `reproduction_aa_*_science.json`).

{summary(repro)}
{pairs(repro)}
Se reprodujo un incumplimiento global en Custom CNN y warm en DenseNet121; también apareció uno warm en VGG16. No son exactamente los mismos porcentajes de R1 y no se presentan como idénticas realizaciones de un mecanismo interno. Fuente completa: [reproduction_performance.json]({E}/reproduction_performance.json), incluidos throughput, RSS y journal por brazo. Todos los pares permanecen retenidos.

## B. Perfilado y cobertura

Se ejecutaron 15 diagnósticos R1: baseline, transporte solo, agregación en memoria, agregación con serialización sin disco y observador durable completo, para las tres arquitecturas. Los 15 pasan comparación de configuración, manifiesto, registros científicos, checkpoints y estados guardados frente a A de reproducción. Transporte solo no agrega recibos; memoria y serialización conservan costos residuales de hashing/capacidad de Aggregator.emit. **Las variantes no durables son exclusivamente aislamientos, nunca candidatos.** Hay una corrida por variante en orden fijo: sus diferencias de tiempo total no aíslan causalmente efectos de orden/cache.

Se capturaron reloj monotónico, funciones científicas por batch, contadores de trazado, cada materialización numpy, agregación, construcción/sellado, canonical/hash, escritura, fsync, rename, apertura/cierre y verificación. cProfile conserva tiempos propios/acumulados y llamadas de Counter/deep_size/serialización. XPlane conserva lectura/decode, lookup, operadores de preprocessing/augmentation y eventos shuffle/batch/prefetch/entrega. JSON incluye cantidad, total, mediana, p95 y máximo; ver [profile_summary.json]({E}/profile_summary.json), [causal_analysis.json]({E}/causal_analysis.json), [xplane_summary.json]({E}/xplane_summary.json) y protobuf/timelines originales.

Un perfil adicional exclusivamente de recibos midió 12 recuperaciones exactas de pending: mediana {recovery_profile['median']*1000:.3f} ms, p95 {recovery_profile['p95']*1000:.3f} ms y máximo {recovery_profile['maximum']*1000:.3f} ms. `recovery_profile.json` conserva cada duración y verifica bytes, prefijo, batch y estado parcial. Son simulaciones de journal, no entrenamientos ni benchmark de aceptación.

Mediciones inclusivas del observador R1 completo, **bajo profiling**, sin sumarlas como categorías independientes:

{host}
Ejemplos de intervalos host de XPlane; incluyen las pasadas adicionales que TRAIN ya realiza y no equivalen a tiempo exclusivo por batch:

{lookup}
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

Tres perfiles adicionales del candidato pasan ciencia y verifican una materialización de token por batch y cero llamadas del bucle eliminado. La reducción de llamadas es verificable; no se atribuye toda diferencia entre series a ese cambio. `ledger.py` conserva exactamente los bytes de R1: mismos límites 256 KiB/8192 pares/128 batches, mismo drenaje máximo al retorno disponible después de 5 s, mismo fsync/rename/recovery. No se añadieron colas ni tareas asíncronas. [candidate_v1.json]({E}/candidate_v1.json) y sellos de campañas fijan fuentes antes de medir.

El resultado posterior limita la justificación inicial: las lecturas de métricas del arnés costaban 0,506/0,973/0,900 ms cuando R1 ya las había materializado; con R2 cuestan 38,836/71,818/79,660 ms. Por tanto, gran parte del costo inicialmente localizado en el observador se desplaza al arnés. No se demuestra un ahorro neto de 40–82 ms. La diferencia de tiempo fuera de la función científica entre perfiles es sólo unos 4–5 ms por corrida e incluye overhead del propio profiler; tampoco prueba ahorro causal limpio. [optimization_outcome.md]({E}/optimization_outcome.md) conserva este resultado sin reescribir la decisión previa. No se presume una implementación interna concreta de caché/copia.

El arnés final reutiliza la firma no-shuffle corregida que ya estaba en R1; esa rama está inactiva en ambos brazos del benchmark. El camino baseline ejecutado conserva la ciencia original. La copia exacta experiment_benchmarked.py se conserva y se usa en reproducción/perfiles. No se cambió el código medido durante cada campaña.

## E. Equivalencia científica

Todos los conteos siguientes son comprobaciones, no entrenamientos. Totales/aprobadas:

{science}
Se repitieron controles de interferencia frente a las ejecuciones sin captura, no-augment, no-shuffle, bytes duplicados, dos fases, últimos batches, EarlyStopping y selección. Identidades, orden, x/y, augmentation y decisiones discretas coinciden exactamente en las capturas aplicables. Scores, gradientes, pérdidas, métricas y variables comparadas cumplen atol=1e-7, rtol=1e-6; no se ampliaron tolerancias.

`state_comparison.json` pasa **{state['total']}** comprobaciones de pesos y optimizador iniciales/finales y restauración directa contra EarlyStopping.best_weights. Máxima diferencia absoluta observada: 0. Checkpoints y decisiones se comparan sin reinferencia. Los seis controles A/B de estados capturan scores y gradientes efectivamente retornados en **GPU:0** (16 pasos por brazo CNN y 32 por brazo transfer). No se atribuye observación a logits pre-sigmoid, todos los estados RNG/TF, cada peso/optimizador intermedio ni kernels internos.

## F. Identidad, recibos y fallos

Se reejecutó la matriz R1 completa, sin eliminar pruebas: 15 unitarias de ledger; identidad explícita; 56 registros con dos muestras distintas de bytes idénticos; manifiestos/hash/cadena, multiplicidad, fases/épocas; replay/idempotencia, conflictos, gaps/solapamiento; recuperación de pending completo/truncado; capacidad; prefetch sin consumo; fallos antes/durante/después; escritura fallida y SIGKILL; estrés y duración de 30 épocas.

La verificación final de recibos pasa **{receipts['total']}** comprobaciones. Los aislamientos declarados no durables se excluyen de este verificador de candidatos, sin excluir ninguna prueba R1. Fallos before/during/after: 0/0/1 batches confirmados, siempre parcial. Durante el paso, efectos científicos desconocidos; cero recibos no acredita cero procesamiento.

El fallo después de fsync y antes de rename dejó un pending y cero bloques finales; recuperación exacta conservó 5 batches y cierre parcial, sin repetir ciencia. SIGKILL tras el primer bloque conservó 5 batches y ámbito abierto. El journal truncado conserva el prefijo y la cola desconocida. Prefetch preparó 8 imágenes y confirmó cero batches/eventos. La identidad ausente se rechazó sin inventar un token.

Sondas de primer batch confirmado→bloque durable: CNN {drains['custom_cnn']:.3f} s, VGG16 {drains['vgg16']:.3f} s, DenseNet121 {drains['densenet121']:.3f} s. No confundir con max_drain_seconds, que incluye tiempo anterior a la primera confirmación. No hay atomicidad GPU–journal, garantía de pérdida eléctrica, transporte E10 ni persistencia SQL acreditados por este laboratorio.

## G. Benchmark final limpio

15 pares nuevos, 30 procesos independientes secuenciales, sin profiler. Mismos fixture, seeds/configuración y criterios. El total incluye construcción, pipeline, entrenamiento y pasadas originales, checkpoints, observador, serialización, durabilidad y verificación final; excluye arranque del intérprete y creación del fixture en ambos brazos. P95 usa numpy.percentile lineal como R1. Warm excluye sólo índices 0/5 CNN y 0/5/16/21 transfer; no excluye primeros batches incompletos. Throughput cuenta 112/224 participaciones TRAIN + VAL interna por total, aunque éste incluye las otras pasadas originales.

Umbrales inmutables: mediana total ≤5% por arquitectura; **cada par** p95 global y warm ≤10%; agregador ≤32 MiB. Overhead = 100×(B/A−1), calculado separadamente por par. Porcentajes negativos no prueban aceleración.

{summary(final)}
{pairs(final)}
Recursos y costo durable por par:

{resources(final)}
Fuentes: [final_performance.json]({E}/final_performance.json), timings/outcomes/environment/observer_summary de cada brazo, [comparación gráfica]({E}/performance_pairs.svg). JSON también conserva mediana/p95/máximo de batches, warm, recuperación y cierres. write_seconds se solapa con close_seconds; no sumarlos. Se conservan todos los pares desfavorables.

Incumplimientos p95 finales: {'; '.join(violations) if violations else 'ninguno en esta serie; mecanismo causal nativo aún no demostrado'}.

## H. Memoria, entorno e integridad

Capacidad aislada de 8192 pares: pico tracemalloc **{capacity['tracemalloc_peak_bytes']/2**20:.3f} MiB**, incremento de pico RSS **{capacity['process_rss_peak_increment_bytes']/2**20:.3f} MiB**, cota de objetos/reservas **{capacity['object_bound_bytes']/2**20:.3f} MiB**, evento máximo {capacity['max_event_bytes']} bytes. No se equiparan JSON, objetos Python y RSS. 1000 ámbitos/8000 batches, verificación incremental y sonda de asignaciones se conservaron. La enumeración pathlib/internado de nombres no se declara O(1) para historia arbitraria.

30 épocas GPU reales: agregador alcanzable {duration[0]['aggregator_live_bytes']} bytes al principio y {duration[-1]['aggregator_live_bytes']} al final, sin crecimiento observado de esa estructura; RSS del proceso puede crecer y no se atribuye al agregador. Mapa Python/payload aproximadamente 45 KiB para 56 identidades, reportado separadamente; overhead interno de tabla nativa no medido. API GPU allocator devuelve ceros, que **no son una medición confiable de memoria GPU**. No se extrapola a poblaciones clínicas grandes.

Entorno por proceso: {env['chip']}, {env['platform']}; Python .venv-metal, TensorFlow {env['packages']['tensorflow']}, Keras {env['packages']['keras']}, tensorflow-metal {env['packages']['tensorflow-metal']}, NumPy {env['packages']['numpy']}; execution_mode=local_python, GPU exigida y soft placement deshabilitado. CPU ejecuta entrada/host; la evidencia GPU del modelo se obtuvo del mismo forward/gradientes, no sólo de la sonda inicial. Sólo imágenes sintéticas 37 TRAIN/19 VAL, 32×32 RGB, batch 8, seed 42, generador 20261020, pesos none, float32; sin descargas.

Se verificaron por tamaño/SHA256 los **2336 archivos de TRACE.1B.2 y 12969 de R1**, antes de los diagnósticos y al cierre, y sus inventarios conservaron hash. Se verificaron los sellos de código/órdenes y 220 fuentes operativas/instaladas registradas antes de las campañas posteriores. [closeout.json]({E}/closeout.json) pasa {closeout['total']} comprobaciones de integridad/cobertura; esto **no convierte un FAIL de rendimiento en PASS**. Los hashes del arnés de reproducción sí se registraron antes del primer proceso; el snapshot ampliado de fuentes operativas se tomó después de reproducción y antes de diagnósticos, sin presentarlo como anterior a R2-A.

## I. Dictamen

**{verdict}.** La reducción de materializaciones conserva las dimensiones científicas observadas, identidad, recibos y memoria acotada en el fixture. No satisface todos los límites p95 finales. La causa nativa exacta de la variabilidad de primeras formas tampoco queda demostrada. No se sustituyen máximos individuales por medianas favorables, no se omiten pares y no se cambian tolerancias, baseline científico ni calentamiento.

## J. Recomendación y entregables

No considerar aprobado TRACE.1B.3. Para otra revisión experimental se necesita observabilidad nativa compatible con Metal que permita distinguir primera especialización de forma/compilación/ejecución y una nueva validación estricta completa. No cambiar el fixture, el warm-up ni la durabilidad para conseguir aprobación. La optimización local retenida es un resultado experimental, no una habilitación operativa.

Se crearon este informe y `{E}/`: diseños/sellos, fuentes, 30 pares de reproducción/final combinados, 18 perfiles válidos, dos intentos de marcadores inválidos, matriz R1 reejecutada, comparadores/verificadores, logs, fixtures, checkpoints sintéticos, NPZ, journals, XPlane, tablas y figura. [README]({E}/README.md) explica comandos y destinos inmutables. `inventory.json` registra los artefactos finales; no ejecutar los runners sobre esos destinos existentes.

Sin modificación de código operativo TRAIN/EVALUATE/TEST/EXPLAIN, PostgreSQL, campañas/RUN, datasets clínicos ni checkpoints históricos. No se pobló run_dataset_images. Sin instalaciones, Docker para entrenar, commit, push ni avance a TRACE.1B.3.
'''
path=ROOT.parent/'capstone_image_trace_1b_2_r2_metal.md'
with path.open('x') as stream:stream.write(text)
print(path,verdict)
