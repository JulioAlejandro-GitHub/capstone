# Cobertura real del profiling

Los tiempos de los perfiles son diagnósticos intrusivos y no se usan para
aceptación. Hay una corrida por variante y arquitectura, en orden fijo; sus
diferencias totales no son un estimador causal libre de efectos de orden/cache.
Las atribuciones locales se basan en intervalos/call counts de operaciones
observadas y en su relación con el retorno del paso original.

- XPlane sólo entrega `/host:CPU` y `Task Environment`, sin plano de kernels
  GPU. Las categorías de `parse_xplane.py` son filtros por nombre: consultar
  `named_intervals` y protobuf originales. Son intervalos inclusivos, anidados
  y de múltiples hilos; no sumarlos como fracciones exclusivas de wall time.
- `read_decode` incluye ReadFile/DecodeImage; lookup observa LookupTableFindV2.
  `preprocessing` es cobertura parcial (principalmente ResizeBilinear), no el
  tiempo integral de toda normalización. Operaciones adicionales, como
  `truediv:RealDiv`, están en named_intervals. Augmentation conserva nombres
  de las capas originales. Shuffle/batch/prefetch/IteratorGetNext incluyen
  actividades y esperas solapadas de las pasadas ya existentes de TRAIN.
- La categoría automática `forward_backward` NO mide todo el modelo: el
  MatMul explícito visible del host puede corresponder a la sonda inicial.
  `scientific_function` mide la función original completa, incluida entrega,
  ejecución/runtime y sincronización. No separa kernels forward/backward/apply.
- Se intentó separarlos mediante marcadores `tf.py_function` en las llamadas
  originales. Las versiones v1 y v2 (marcadores CPU explícitos) fallaron en el
  primer Custom CNN A con `stream cannot wait for itself`. Se retienen fuentes,
  sellos, logs, outcomes y timelines; son diagnósticos inválidos, sin ciencia
  completa ni tiempos admitidos. No se atribuye cero efecto científico sólo
  porque no retornó un paso. No se cambió TRAIN para hacerlos pasar.
- `numpy` mide materialización host de tensores, con su espera/copia y el
  overhead de profiling; no es una medición aislada de bus ni kernel GPU.
- `Store.put`, emit, flush y close son inclusivos y se solapan. Fsync y rename
  se miden directamente; los nombres del módulo os también pueden incluir
  renames de checkpoints originales. La relación con los intervalos Store.put
  permite distinguirlos; no sumar todas las categorías.
- El perfil de CPU conserva llamadas propias/acumuladas de construcción de
  recibos, Counter, canonical, hashes y deep_size. La instrumentación aumenta
  sus tiempos; no se extrapolan a los benchmarks limpios.
- Los contadores de trazado pertenecen a funciones TF de las corridas
  diagnosticadas. No observan compilaciones internas Metal ni prueban que
  todas las ejecuciones limpias tengan la misma conducta interna.
- `pmset -g therm` no registra advertencias en las capturas. Esto no mide
  temperatura GPU ni demuestra ausencia de throttling. Load average y vm_stat
  son snapshots, no una atribución de carga externa. No hay evidencia para
  culpar temperatura, presión de memoria o procesos ajenos.
- GPU allocator current/peak=0 no es una medición confiable de memoria física
  Metal. Mapa nativo de identidad también queda sin medición interna. RSS,
  objetos Python del mapa y memoria aislada del agregador se reportan separados.

No se instaló Instruments: `xcrun --find xctrace` devuelve código 72 y sólo
hay CommandLineTools seleccionado. La ejecución científica real GPU se
verifica independientemente mediante scores y gradientes del mismo paso en
los controles de estado; ausencia de plano GPU del profiler no es fallback.
