# CAPSTONE-IMAGE-TRACE.1B.1 — Contrato científico de consumo de imágenes

Fecha: 2026-10-20. Estado: **propuesta para revisión y aprobación; no implementada**.

Fuente principal: [auditoría TRACE.1A](../audits/capstone_image_trace_1a.md). Validación de esta fase: inspección estática del checkout y del DDL versionado. No se ejecutó SQL ni se inspeccionó el catálogo de una instancia; la compatibilidad declarada es con las definiciones actuales del repositorio, no una certificación de despliegue. No se ejecutaron TRAIN, EVALUATE ni pruebas experimentales. La única escritura de esta fase es este documento.

En las referencias, `M/` significa `malaria_dl_local_project/src/malaria_dl/`. Los símbolos son puntos de navegación; las líneas citadas corresponden al checkout inspeccionado.

## A. Decisiones aprobables

### A.1 Principio y niveles de evidencia

**Intervención quirúrgica: añadir evidencia científica sin cambiar el experimento que estamos intentando observar.** La instrumentación futura debe preservar tensores, etiquetas, orden efectivo, shuffle, semillas y estados aleatorios, augmentation, preprocessing, batching, forward, gradientes, actualización de pesos, métricas, callbacks, Early Stopping y selección/restauración de checkpoints. No introduce épocas, etapas ni inferencias. La equivalencia es una condición experimental de aceptación en TRACE.1B.2, no una propiedad demostrada por este diseño.

Se separan cuatro hechos:

1. **Población prevista:** manifiesto de identidades elegibles para un ámbito. No demuestra lectura ni procesamiento.
2. **Lectura/preparación:** archivo abierto, decodificado o tensor preparado, incluido prefetch. No demuestra participación en un paso completado. No se propone persistir telemetría individual de lecturas.
3. **Procesamiento confirmado:** retorno correcto del paso científico y asociación verificada con las identidades del batch realmente entregado. Una confirmación en RAM aún puede perderse.
4. **Resultado/evidencia persistidos:** confirmación o resultado comprometido en su almacén. Una fila de predicción acredita su propia pasada; no otras pasadas sobre la misma población.

Una consulta debe declarar `evidence_basis`, propósito, ámbito, población prevista y estado de completitud. Ausencia de recibos no se publica como cero consumo. Los registros anteriores no se convierten retrospectivamente en recibos de optimización o validación interna.

### A.2 Vocabulario de propósitos

Los seis valores siguientes pertenecen al nuevo contrato de consumo, no a las etapas del motor ni al catálogo SQL `usage_context`:

| `usage_purpose` | Confirmación exigida | Evidencia reutilizada / contexto principal |
|---|---|---|
| `weight_optimization` | Paso TRAIN completado, incluida actualización del optimizador | Nuevo recibo; `usage_context='train'` |
| `keras_validation` | Paso de validación interna de `fit` completado | Nuevo recibo independiente; `usage_context='validation'` |
| `clinical_validation` | Inferencia de la pasada clínica existente retornó correctamente | Nuevo recibo sin scores duplicados; contexto `validation` |
| `epoch_prediction` | Predicción adicional por época y resultados individuales válidos persistidos | Registro `predictions`, contexto `validation` |
| `selected_checkpoint_prediction` | Predicción final existente con checkpoint seleccionado | Registro `calibration/val/selected`, contexto `validation` |
| `independent_evaluation` | Inferencia de EVALUATE por muestra/intento | `assessment_*`; no proyección automática a `run_dataset_images` |

Búsqueda estática de los seis nombres en `M/`, backend y baseline: no existe este enum de consumo. Aparece el símbolo de callback clínico, que no constituye un valor persistido del contrato. EVALUATE mantiene `kind='evaluate'`, `purpose='development'` para VAL y `purpose='final'` para TEST: esos valores se conservan y no se sustituyen por `independent_evaluation`.

El CHECK de `run_dataset_images.usage_context` admite `train`, `validation`, `evaluation`, `explainability`, `tta`, `ensemble`, `svm_features`, `inference` (`alembic_v2/baseline/06_constraints.sql:664`). **Ninguno de los seis nuevos valores se inserta en esa columna.** El subpropósito vive en el recibo o en la interpretación explícita de la evidencia existente.

### A.3 Identidad: nivel A

Reutilizar `public.run_dataset_images` como índice de identidad por RUN/contexto principal. Conservar `UNIQUE(run_id,image_id,usage_context)` y las FK a `runs` y `dataset_split_images`. No crear otra tabla de identidad.

La identidad científica de referencia es la tupla `(dataset_version_id, dataset_materialization_id, split, normalized_relative_path)` asociada al hash de contenido y, cuando existe, `source_record_id`/`sample_id`. La ruta se normaliza respecto de la materialización, con separadores POSIX y sin escapes; no se reducen mayúsculas ni directorios para resolver colisiones. `sample_id` de assessments corresponde a `source_record_id`; **no es `image_id`**.

Mapeo propuesto, fuera del procesamiento por batch:

- Reutilizar lectura gobernada de asignaciones/source records y registro físico de imágenes, por versión/materialización y split. Contrastar con la enumeración real del loader sin volver a decodificar imágenes para contar.
- Resolver por ruta materializada completa, versión y materialización; exigir unicidad, split, clase y hash coherentes con evidencia de verificación del dataset. Un hash idéntico no fusiona dos muestras científicas distintas.
- Conservar `image_id` sólo con correspondencia verificada. No unir por filename, ordinal de registro o igualdad aparente de UUID.
- Si no hay correspondencia, conservar token científico en el manifiesto gobernado, marcar `identity_resolution='unresolved'` y no insertar una FK ficticia en `run_dataset_images`. La cobertura por `image_id` queda incompleta aunque pueda conocerse por identidad científica. No invocar silenciosamente el registrador histórico dentro de TRAIN.

La fila reutilizada contiene RUN, image_id, split, etiqueta y ruta; `metadata` puede referenciar versión/materialización, sample_id, origen resoluble `(root_ref, relative_path)`, hash de manifiesto y estado de resolución. No se necesita repetir rutas absolutas host/Docker en cada recibo. `sample_index` y `batch_index` históricos no son posiciones de consumo; no se usan para reconstruir shuffle. Los flags históricos tampoco certifican optimización: `_usage_flags` mezcla split y uso.

El manifiesto previsto se obtiene del snapshot/gobernanza existente, con referencia estable y hash. El índice `run_dataset_images` se proyectará con IDs confirmados, fuera del batch, y nunca se contará como historial de uso. No requiere insertar de antemano toda la población prevista. La proyección es regenerable desde evidencia durable y su retraso no reduce el consumo acreditado.

Para tokens compactos, definir un orden canónico de manifiesto por identidad científica completa, independiente del orden del loader. Un token entero es únicamente un índice en **ese manifiesto sellado**, nunca el índice de entrega a Keras. El hash obliga a conservar el orden y la resolución. Si la fuente gobernada no permite reconstruirlo de manera inmutable, usar bloques `image_trace_manifest` en el mismo ledger de TRAIN, guardando sólo el enlace token→referencia existente y excepciones de resolución; no duplicar rutas/etiquetas ya resolubles. Nunca persistir contadores cuyos tokens no puedan resolverse. Decidir esa necesidad con los datos del entorno en 1B.2.

### A.4 Multiplicidad, frecuencia y cobertura

Ámbito TRAIN: `(run_id, session_run_id, campaign_attempt_id|null, usage_purpose, phase, epoch_local|null, epoch_global|null, pass_ordinal)`. La sesión existente se identifica por su `run_id`: no se inventa un UUID de sesión. Un nuevo intento científico usa la identidad que ya crea el motor, no reutiliza una ejecución finalizada. Ámbito EVALUATE: `assessment_attempt_id`, unido a su identidad; el RUN de origen no sustituye el intento.

Épocas locales y globales son **1-based**; global = épocas realmente completadas de fases anteriores + local. Una época interrumpida puede tener recibos sin registro `epoch` completado. El checkpoint final tiene época de selección como procedencia, no una nueva época de entrenamiento: `epoch_local/global=null` para esa pasada y `checkpoint_epoch` separado. `pass_ordinal=1` para cada pasada normal; sólo aumenta ante otra invocación real autorizada por el motor, nunca ante replay de transporte.

Para un ámbito S, sea P el conjunto previsto y `m(i)` la suma de multiplicidades confirmadas de i en recibos durables válidos, deduplicados por clave. Cuando hay referencias a resultados, se cuenta cada resultado canónico una sola vez, no también su espejo E10.

| Medida | Definición y límites |
|---|---|
| Previstas | `|P|`, no `N * max_epochs` |
| Únicas confirmadas | `|C|`, con `C={i:m(i)>0}`; informar también `|C∩P|` |
| Procesamientos confirmados | `Σ m(i)`; cota inferior si hay ventana desconocida |
| Frecuencia por época/intento | `m(i)` agrupada por ámbito; suma de bloques, no de reenvíos |
| Sin evidencia | `P\C`; no significa no procesadas |
| Faltantes acreditados | Subconjunto de `P\C` cuya no participación se demuestra por cierre exhaustivo del ámbito y ausencia de ventanas; de lo contrario, no cuantificable como ausencia física |
| Inesperadas | `C\P`; error de integridad/selección que impide declarar cobertura válida completa |
| Repeticiones | `Σ max(m(i)-1,0)`; legítimas si el recorrido las acredita, aunque no se esperan dentro de una pasada finita actual; repetición de recibo aporta cero |
| Cobertura acreditada | `|C∩P|/|P|`; si `|P|=0`, no aplicable, nunca 100% por convención |
| Parcial | Hay evidencia durable de parte del ámbito; mostrar fracción y límite inferior, además del estado del cierre |
| Desconocida | No hay mapeo/manifiesto fiable o existe intervalo no observado; puede coexistir con una cota inferior conocida |

100% de identidades cubiertas no demuestra multiplicidad total exacta: pueden existir procesamientos adicionales no persistidos. Un ámbito sólo se considera exhaustivamente trazado si tiene apertura, todos los bloques sin huecos, cierre válido y ninguna ventana desconocida. No derivar pasos a partir de batches por tamaño configurado: el último batch puede ser incompleto. No inferir épocas ejecutadas desde `runs.max_epochs` ni `runs.total_epochs` configurados.

## B. Mapa de reutilización y evidencia estática

| Estructura / servicio actual | Responsabilidad propuesta | Hecho contrastado / limitación |
|---|---|---|
| `runs` | Identidad RUN, configuración, versión y estado operativo | `_create_run`, `_finish_run` en `M/execution/repository.py`; no tiene consumo individual |
| `run_dataset_images` | Índice de identidades verificadas por contexto | DDL `03_tables.sql:138`, claves `05_keys.sql:292`, FK `06_constraints.sql:1096`; UPSERT histórico no es ledger |
| `dataset_split_images`, asignaciones y materialización gobernada | Resolver identidad y población prevista | `M/data/sample_repository.py:30`, `registry.load_registered_split_images`; no prueban mapeo completo en una instancia |
| `train_execution_sessions` | Sesión/owner/intento y fencing | `run_id` liga recibos; estado active exigido para insertar |
| `train_execution_records` | Contenedor principal de bloques y referencias | PK `(run_id,kind,phase,record_key)`; JSONB objeto; guard append-only |
| `ExecutionRepository.put` y `Reports.put` | Canal legacy existente para registros | Reenvío idéntico aceptado, discrepante rechazado; no journal E10 automático |
| `RunEventEmitter`, `ResultService`, reporters HTTP/Docker | Entrega E10 idempotente, ordenada, con fencing | Enum cerrado y secuencia global por RUN; extensión de software necesaria |
| `SQLiteEventJournal` local | Retener evento pendiente exacto para replay | Sólo eventos E10; no confirma procesamiento previo a creación del evento |
| Registros `predictions` / `calibration` | Reutilizar muestras de pasadas existentes | `M/execution/train.py:192,285`; no copiar scores a recibos |
| `assessment_identities` | Manifiesto y checkpoint de evaluación | Identidad canónica/hash y FK al TRAIN |
| `assessment_attempts` | Unidad de ejecución independiente | Owner, ordinal por identidad, estado y verificación |
| `assessment_results` | Resultado individual persistido | PK `(attempt_id,sample_id)`; no contador de inferencias físicas |
| `assessment.repository/service/contracts` | Inserción/verificación/recuperación | Mantener transacciones y reglas existentes |
| Backend `scientific_results.py` | Futuro lector de medidas con semántica | Su `consumed_images=count(run_dataset_images)` actual no certifica consumo |

## C. Diseño del recibo compacto

**El siguiente JSON es sólo una propuesta ilustrativa, con marcadores no válidos para producción. No es evidencia de ninguna ejecución.** Se muestra el payload; el envoltorio E10 conserva event_id, RUN, intento, secuencia, timestamp y schema_version existentes.

```json
{
  "contract_version": "image_trace_v1",
  "record_type": "consumption_block",
  "run_id": "<run_uuid>",
  "session_run_id": "<run_uuid>",
  "campaign_attempt_id": null,
  "usage_purpose": "weight_optimization",
  "phase": "base",
  "epoch_local": 1,
  "epoch_global": 1,
  "pass_ordinal": 1,
  "manifest_ref": "<resolvable_governed_manifest_ref>",
  "manifest_sha256": "<64_hex>",
  "block_sequence": 1,
  "batch_first": 1,
  "batch_last": 2,
  "confirmed_batches": 2,
  "counts": [[0, 2], [1, 1], [2, 1]],
  "unique_images": 3,
  "total_processings": 4,
  "confirmation_state": "confirmed",
  "confirmation_basis": "completed_train_step",
  "previous_block_sha256": null,
  "receipt_sha256": "<64_hex>"
}
```

`counts` son pares `[manifest_token, positive_integer_multiplicity]`, ordenados por token, sin tokens duplicados en el bloque. `unique_images=len(counts)`, `total_processings=sum(counts[*][1])`; únicos del ámbito se calculan por unión, no sumando únicos de bloques. El ejemplo admite repetición para ilustrar la semántica, sin afirmar que el loader actual la produzca.

Un bloque sólo abarca batches completos y contiguos de **un** ámbito; `confirmed_batches=batch_last-batch_first+1`. No mezcla fase, época, propósito o intento. Mantener una huella incremental del orden de tokens por batch es una extensión opcional para 1B.2; una multiplicidad por bloque no permite reconstruir el orden completo, y este contrato no promete hacerlo retrospectivamente. El arnés de equivalencia sí compara la secuencia efectiva íntegra en fixtures sintéticos.

Tipos complementarios dentro del mismo contrato: `scope_open` (población y frontera inicial), `scope_close` (último bloque, batches y totales, motivo de cierre, exhaustividad) y, si es necesario, `manifest_block`. Son evidencia de trazabilidad, no nuevas operaciones científicas. Una apertura sin cierre nunca acredita completitud. Un cierre sin todos los bloques referenciados es inválido.

Para `epoch_prediction` y `selected_checkpoint_prediction` no se generan listas `counts` equivalentes a `samples`: el lector deriva multiplicidad 1 por resultado individual validado y resuelve su identidad con el manifiesto. Puede conservarse una referencia compacta al registro `(run_id,kind,phase,record_key)` y su hash; referencias y muestras no suman dos consumos. Para `calibration` conservar checkpoint_epoch, referencia al `artifact` seleccionado y su hash/identidad; no basta el nombre de archivo. Comprobar cardinalidad y correspondencia exacta de rutas/etiquetas con el manifiesto antes de acreditar exhaustividad. Los registros históricos que sólo pasan cantidad/unicidad no reciben garantías adicionales sin validación.

## D. Claves de idempotencia y sellado

Identidad lógica de bloque: `(contract_version, run_id, campaign_attempt_id|null, usage_purpose, phase, epoch_local|null, epoch_global|null, pass_ordinal, block_sequence)`. El manifiesto es contenido protegido, no parte variable de la clave: cambiarlo bajo la misma clave debe producir conflicto. `block_sequence` empieza en 1 dentro del ámbito y crece sin huecos; aperturas/cierres usan su `record_type` para no colisionar. Un bloque sellado no se amplía ni se reemplaza.

Para E10, derivar `event_id` con UUIDv5 usando `run_id` como namespace y la codificación canónica de `(image_trace_v1, record_type, ámbito, block_sequence)` como nombre. **No incluir hash de contenido ni timestamp en esa identidad:** una contradicción debe colisionar. La secuencia E10 es otra secuencia, global del RUN, asignada por el único emitter entre los eventos científicos existentes. Nunca reutilizar `block_sequence` como `event.sequence`.

Conservar el evento completo antes del envío y retransmitir exactamente los mismos bytes canónicos, event_id, sequence y occurred_at. Aunque el ID sea derivable, no reconstruir un evento perdido con timestamp o secuencia nuevos. Un payload contradictorio bajo la misma clave se rechaza y se informa como conflicto; no se incrementa frecuencia ni se ejecuta ciencia para corregirlo.

`receipt_sha256` = SHA-256 de UTF-8 canónico del payload sin ese campo. Para este contrato usar las opciones de `results/identity.canonical_event`: claves ordenadas, separadores `(',', ':')`, `ensure_ascii=True`, `allow_nan=False`, sin coerción float/int. No intercambiar este serializador con `campaigns/contracts.canonical`, que convierte floats integrales a enteros y usa `ensure_ascii=False`; el hash legacy conserva su algoritmo actual. Tokens y cantidades son enteros positivos/no negativos según campo, sin booleanos, NaN o infinitos. `previous_block_sha256` encadena bloques del ámbito; cierre referencia hash del último bloque y total de bloques. El manifiesto tiene hash de entradas canónicas ordenadas y sus referencias de versión/materialización, calculable incrementalmente. Un hash acredita integridad respecto de contenido, no autenticidad del productor ni consumo físico por sí solo.

El canal legacy alternativo usa `kind='image_trace'`, fase científica y `record_key` derivada del mismo ámbito/tipo/secuencia. Es una alternativa técnica, **no un segundo espejo de los mismos recibos**. El RUN debe declarar un único canal de trazabilidad para evitar doble conteo.

## E. Confirmación, estados y fallos

### E.1 Fronteras científicas

- **TRAIN:** capturar identidad junto al tensor que realmente alcanza el paso y confirmar sólo al completar el paso original, incluida aplicación de gradientes. Un wrapper que sólo agenda trabajo GPU sin observar su finalización no basta. El mecanismo concreto de confirmación y su sincronización deben probarse en 1B.2. `on_train_batch_end` por sí solo no entrega IDs; un iterador espejo tampoco acredita el shuffle real.
- **VAL interna:** mismo criterio en el paso de validación original; usar propósito explícito y no interpretar cualquier `test_step` o `predict` como validación interna. No inferir desde `predictions`.
- **Clínica:** `ClinicalValidationMetricsCallback.on_epoch_end` recibe `y_true, y_score` de `collect_predictions` antes de computar métricas (`M/training/checkpoint_policy.py:550`). El bucle existente llama `model.predict(images)` y convierte a NumPy (`M/evaluation/clinical_metrics.py:430`): el retorno válido acredita inferencia de ese batch. El retorno total sólo entrega arrays, no IDs; asociarlos requiere el manifiesto VAL sin shuffle y una vinculación verificada al recorrido. Para bloques acotados, observar ese retorno por batch dentro de la misma llamada sin repetirla. Si sólo se observa retorno total y ocurre interrupción antes de él, la pasada queda desconocida, no cero.
- **Por época:** `PersistEpoch` persiste resultados después de clínica, EarlyStopping y ReduceLROnPlateau. No mover callbacks ni asumir que esos resultados usan exactamente los pesos de validación interna, especialmente ante restauración de EarlyStopping.
- **Checkpoint seleccionado:** reutilizar la única pasada final y la calibración existente incluso cuando calibración esté deshabilitada. No inferir nuevamente para acreditar consumo.
- **EVALUATE:** `runtime.predict` retorna salida NumPy antes de `write_batch`; son fronteras distintas. Mantener `assessment_attempt_id` y PK de resultados; replay idéntico de persistencia no implica nueva inferencia. `verified` exige conjunto esperado y verificación integral, `failed`/`interrupted` pueden conservar resultados. Cero resultados no demuestra cero procesamiento. No se cambia el motor ni se duplican resultados en el índice de TRAIN.

### E.2 Estados independientes

`confirmed` describe una operación completada. `journal_durable` significa evento pendiente guardado localmente, aún no comprometido en PostgreSQL. `persisted` significa commit confirmado o replay idéntico aceptado; se deriva del almacén, no de un booleano autoafirmado en payload. `partial` describe alcance de evidencia y `unknown_window` el intervalo no acreditado. `verified` de sesión o assessment es estado operacional/científico existente; no equivale automáticamente a cobertura exhaustiva del nuevo contrato.

Los recibos confirmados son inmutables: no se actualizan de pending a persisted. La aceptación/transacción indica durabilidad y los cierres agregan información. Lectores remotos sólo acreditan PostgreSQL; un pendiente local puede recuperarse bajo autorización, pero no se cuenta dos veces ni se presenta como ya recibido.

| Fallo/situación | Evidencia y conducta |
|---|---|
| Antes de procesar | Apertura/previstas no agregan consumo; si no existe evidencia de que nunca empezó, no atribuir cero |
| Durante batch | No emitir confirmación completa; puede haber efectos parciales o trabajo asíncrono, ventana desconocida |
| Tras completar batch, antes de agregar/sellar | Procesamiento posible sin evidencia durable; desconocido desde última frontera durable |
| Antes de persistir, bloque sólo en RAM | Caída pierde bloque; nunca repetir paso para recuperar contador |
| Journal durable, respuesta de servidor perdida | Replay exacto del evento pendiente; no reinferencia |
| Transacción fallida / commit incierto | Rollback o estado incierto; reenvío idéntico bajo owner vigente resuelve si se había comprometido |
| Mismo recibo reenviado | Aceptación idempotente, incremento cero |
| Recibo contradictorio | Error explícito; mantener evidencia previa y no sobrescribir |
| Worker interrumpido | Conservar bloques persistidos; ámbito sin cierre queda parcial/desconocido; owner/estado pueden impedir replay tardío |
| Early Stopping | Cerrar ámbitos realmente observados; no crear recibos para épocas no ejecutadas |
| Base → fine-tuning | Sellar ámbito de base; nuevo ámbito local y offset global real; no reiniciar identidad RUN |
| Restauración checkpoint | No resta consumo pasado; anotar procedencia del modelo para pasadas posteriores |
| Fallo de EVALUATE antes de commit | Resultados anteriores son cota inferior; recuperación marca interrupted y nuevo intento sigue reglas actuales |

No hay transacción atómica GPU–journal–PostgreSQL. La ventana comienza después del último batch durable y termina en el último punto conocido o en la interrupción; si se desconoce el último batch ejecutado, su cota superior se declara desconocida. Una fracción completa de resultados puede coexistir con intento fallido por verificación posterior. No se modifica la política actual de errores de transporte de TRAIN (fatal); demostrar igualdad de todas las decisiones bajo fallos arbitrarios de almacenamiento no es posible. La equivalencia científica se exige bajo entrega exitosa; los escenarios de fallo deben conservar ciencia ya ejecutada y límites honestos, sin prometer terminación idéntica.

## F. Diseño de persistencia y compatibilidad

### F.1 Dictamen sobre el esquema

El DDL actual permite almacenar el contrato sin nuevas tablas, columnas, CHECK ni migraciones. `train_execution_records` tiene payload objeto sin enum SQL de kinds legacy; para E10 exige `kind='e10_event'`, `phase='run_event_v1'`, key=event_id y payload con **sólo** `canonical_event` string (`06_constraints.sql:806`). Nunca insertar el JSON del ejemplo directamente como payload SQL de un evento E10: lo serializa el adaptador existente.

El trigger `train_record_guard` (`04_functions.sql:1087`) impide UPDATE/DELETE y exige sesión active/owner autorizado. La FK llega a `train_execution_sessions`. Mantener claves, restricciones y transacciones existentes. `run_dataset_images.image_id` es NOT NULL: una identidad sin resolver no puede insertarse allí. `assessment_results` tiene FK al intento, pero no FK desde sample_id a `dataset_split_images`; no inventar esa relación.

No se afirma que el contrato esté implementado por el software actual. La extensión mínima es **de software y payload**, descrita abajo. No se propone preflight de revisión histórica, dependencia Alembic ni compatibilidad legacy de esquema. La comprobación futura de integridad del catálogo efectivo se hará sobre restricciones reales, sin bloquear por historial de migraciones.

### F.2 Canal principal propuesto y límites reales

Preferir E10: agregar prospectivamente `IMAGE_TRACE_RECORDED='image_trace_recorded'` al enum de eventos, con payload `image_trace_v1` y validación estricta de los tipos indicados. Mantener envoltorio `run_event_v1` y su representación SQL; su forma no cambia. Este valor **no existe hoy** en `execution/contracts/events.py` y debe incorporarse coordinadamente en decodificadores, servicio, reporters, journal, lectores y validación de cierre antes de emitirlo. No disfrazar recibos como epoch_completed, predictions_completed o heartbeat.

`ResultService.accept_event` compara RUN/intento, esquema, event_id canónico y secuencia; acepta duplicados idénticos y rechaza gaps/conflictos. Los índices únicos parciales `train_event_id_unique` y `train_event_sequence_unique` protegen event_id global y `(run_id,event_sequence)` (`07_indexes.sql:416–418`). `PostgresResultRepository` protege autorización y commit; los reporters HTTP/Docker no deben regenerar identidad. Conservar estas propiedades y validar además el nuevo payload, manifiesto, ámbito y no solapamiento de batches. La idempotencia de transporte sola no impide que dos claves diferentes reclamen los mismos batches: el validador debe detectarlo.

Local: `SQLiteEventJournal` conserva estado/pending completo mediante transición durable; el emitter sólo mantiene un pendiente y no permite saltarlo. Reutilizar ese journal ya existente, sin crear otro archivo binario. Docker: `RunEventEmitter` documenta estado en memoria si no se inyecta journal; muerte del proceso puede perder pending. No prometer la durabilidad local para Docker ni introducir un archivo nuevo para simularla. Reducir la ventana mediante bloques acotados no la elimina.

Existen rutas sin emitter (`train` documenta ruta legacy local/standalone). Para habilitar trazabilidad deberán integrar el emitter aprobado o adoptar explícitamente el canal legacy, con menor garantía: `ExecutionRepository.put` bloquea sesión, valida owner y compara payload canónico; `Reports.put` lo transporta por HTTP, pero **no usa el journal E10**. No habilitar silenciosamente una garantía uniforme entre rutas. La opción preferida es unificar recibos en E10; su alcance por entrada queda como criterio de 1B.2. No se elimina ni reordena el dual reporting científico existente.

### F.3 Hash final, recuperación y consultas

`read_legacy_execution_records` excluye `event_id IS NOT NULL`, ordena por kind/phase/key y carga lista completa; `records_hash=digest(records)` sella esa familia. `read_result_events` decodifica la familia E10 separada. **Un recibo sólo E10 no queda incluido en el records_hash legacy.** Añadir al contrato de cierre un `trace_root_hash` y referencias de manifiesto/cierres, verificables desde los eventos, sin cambiar bytes ni hashes históricos. Si se elige canal legacy, sus nuevos registros sí entran en records_hash; no filtrar recibos después de calcularlo. Adaptar `TrainingCompletionValidator` y verificador de artifacts para validar ambas responsabilidades sin contar recibos como épocas.

No agregar recibos tras terminal/cierre de sesión para “completar” trazabilidad: owner/estado lo impiden. Intentar drenar pendientes antes del terminal y sellar sólo bloques aceptados. Una recuperación sólo reenvía evidencia bajo autorización vigente; `preflight_result_events` rechaza reiniciar stream ya existente y el journal no es un mecanismo para reanudar entrenamiento. Si el estado terminal impide reenvío, declarar la laguna; no relajar fencing.

Para consulta incremental, extender los lectores existentes con paginación por clave, sin nuevo endpoint duplicado: E10 por `(run_id,event_sequence)` con cursor y techo de secuencia capturado; legacy por PK y ámbito; assessments por `(attempt_id,sample_id)`. Validar referencia/hash y resolver únicamente los bloques/manifiestos necesarios. El payload E10 es texto canónico dentro de JSONB: no afirmar que `payload->>'usage_purpose'` sea indexable directamente. Un lector puede recorrer páginas E10 del RUN y filtrar, con costo lineal; indexación especializada sólo si mediciones posteriores la justifican.

El cálculo exacto de únicos necesita conjunto de tokens o bitset del manifiesto, O(N), aunque el historial se lea en O(tamaño de página). Frecuencias completas pueden necesitar O(N) contadores; para una imagen se acumula en O(1) extra por página. No cargar toda la historia para un contador. El cierre actual sí carga listas completas: su mejora incremental manteniendo exactamente el serializador/hash, y la validación E10 por streaming, son trabajo necesario antes de declarar soporte de RUN grandes. No se presenta como capacidad actual.

## G. Costos y límites propuestos

Límites iniciales aprobables, sujetos a medición en 1B.2: máximo **256 KiB de bytes UTF-8 del evento serializado completo**, máximo **8.192 pares** por bloque y máximo **128 batches completos** acumulados; sellar al alcanzar el primero, en cambio de ámbito o cierre. Medir tamaño real incluyendo escape de `canonical_event` para persistencia; no confiar en tamaño comprimido TOAST. El presupuesto SQL puede requerir un bloque menor que el HTTP. Configurar umbral temporal de drenaje de hasta 5 segundos, sin nuevas pasadas científicas; no es garantía de durabilidad frente a un batch de duración superior.

No dividir un batch entre bloques en v1. Si un batch de identidades excede el límite, rechazar la activación del observador antes de ejecutar ese fixture/configuración o diseñar y aprobar un protocolo multipart con commit lógico; no aumentar el límite indefinidamente ni cambiar batch_size científico. Reservar tamaño antes de incorporar el próximo batch. Backpressure debe ser acotado; no cola sin límite ni descarte silencioso. E10 con un pendiente requiere ACK antes de avanzar, por lo que persistencia puede añadir latencia aun fuera del cálculo del modelo.

Estimación ilustrativa de escala, **no medición**: Ntrain=1.000.000, Nval=200.000, 50 épocas realmente ejecutadas, batch=32, una aparición por pasada. Con 128 batches/bloque se agrupan 4.096 participaciones. Por época: aproximadamente 245 bloques TRAIN + 49 Keras VAL + 49 clínica = 343; 17.150 bloques en 50 épocas, más aperturas/cierres/manifiesto. Predicciones por época y calibración reutilizadas no generan otros arreglos de IDs.

Un par compacto de token de hasta siete dígitos y multiplicidad pequeña cuesta aproximadamente 12–20 bytes serializados. Los 70 millones de participaciones de esos tres propósitos implican aproximadamente 0,84–1,4 GB de pares sin compresión; agregar envelopes, JSONB, índices, WAL y réplica. No es una estimación de bytes físicos PostgreSQL. Frente a UUIDs de 36 caracteres por aparición, el manifiesto compartido evita varios GB adicionales. Un manifiesto de un millón de entradas, si necesita mapa explícito de 60–120 bytes por entrada, cuesta aproximadamente 60–120 MB una vez, en bloques; reutilizar referencias gobernadas puede reducirlo.

Memoria del agregador: hasta 8.192 pares más un batch y un pendiente de hasta 256 KiB serializado. Objetos Python y serializaciones duplicadas pueden multiplicar ese tamaño; medir RSS, no equiparar bytes JSON a RAM. El mapa completo identidad→token puede costar cientos de MB con un millón de entradas Python; preferir índices compactos y lecturas paginadas, reportar ese costo O(N) explícitamente. Bitset de un millón de tokens: ~125 KB, sin overhead; contadores uint64: ~8 MB. No cargar todos los recibos ni mantener arrays de scores adicionales.

Persistencia: una aceptación/transacción por bloque y por apertura/cierre, cero INSERT por imagen/batch para consumo. Proyección `run_dataset_images`: una fila por imagen/contexto resuelto, no por época; puede costar O(N) filas y debe hacerse en lotes fuera del camino científico, no invocando el UPSERT histórico por muestra durante fit. Las predicciones y manifiestos EVALUATE existentes ya pueden ser grandes; este contrato no afirma haber resuelto ese costo ni autoriza duplicarlos. Las restricciones reales HTTP/proxy y latencia de journal/commit requieren medición: 256 KiB es un límite propuesto, no un límite de infraestructura verificado.

## H. Riesgos de interferencia y alternativas descartadas

| Punto de riesgo | Consecuencia | Condición de aceptación |
|---|---|---|
| Añadir IDs al pipeline o sustituir loader | Cambia grafo, shuffle, RNG, autotuning o orden | Misma corriente de identidad/tensor; pruebas exactas de secuencia y tensors |
| Iterador paralelo de IDs | Permutación aparente diferente a entrega real | Descartado como prueba de identidad |
| Wrapper train/test step | Retracing, compilación distinta, pérdida de sample weights o actualización extra | Delegación única al paso original; medir gradientes/pesos y número de llamadas |
| `.numpy()`, py_function, callbacks de host | Sincronización GPU/CPU y overhead | Evitar por imagen; justificar cualquier frontera necesaria con medición |
| Cambio de orden de callbacks | Cambia métricas, LR, restauración y selección | Conservar orden exacto y decisiones |
| Escrituras/journal/colas | Bloqueo, memoria, fallos de I/O nuevos | Límites de bloque y política explícita; medir entrega local/Docker |
| Resolver IDs leyendo de nuevo el dataset | E/S extra, carreras con archivos y consumo de RNG | Usar manifiesto/snapshot; no repetir inferencia ni reconstruir loader |
| Inferir pasado desde índices/flags o max_epochs | Cobertura ficticia | Descartado; distinguir previsto, preparado y confirmado |
| Un JSONB por RUN creciente o fila por imagen/batch | Reescritura, contención o explosión de filas | Bloques inmutables acotados |
| Copiar scores, assessments o crear tabla duplicada | Dos fuentes de verdad y doble conteo | Referencias y lectores del resultado existente |
| Persistencia después del cierre | Viola ownership y hash sellado | No relajar guards ni reabrir ejecución |

No se elige todavía una técnica concreta de side-channel TensorFlow: ninguna inspección estática demuestra que pueda transportar tokens y confirmar pasos sin alterar el experimento. Tampoco se eliminan pasadas VAL existentes para reducir costo: cambiaría lo observado.

## I. Protocolo experimental TRACE.1B.2 (sin implementar ni ejecutar)

### I.1 Preparación y comparación A/B

Usar únicamente imágenes sintéticas con identidades únicas y etiquetas conocidas. Fijar dataset, bytes/hash, arquitectura, pesos iniciales, estado del optimizador, semillas Python/NumPy/TF, versiones, hardware, determinismo, preprocessing, augmentation, batch_size, épocas máximas y callbacks científicos. Ejecutar A original y B instrumentada en procesos aislados desde el mismo estado, sin reutilizar RNG ya consumido. No descargar pesos durante la medición; VGG16 usa los mismos pesos locales o inicialización sintética explícita en ambos brazos.

El arnés de prueba puede observar tensores, pasos y gradientes en **ambos** brazos mediante el mismo observador de referencia, sin usar el ledger B como verdad del orden. Comparar además ejecuciones sin ese observador de referencia para detectar su propia interferencia. Capturar datos del mismo forward/backward; no ejecutar un segundo forward para obtener logits o gradientes. Si esa captura no es viable sin cambiar el algoritmo, declarar dimensión no observada y bloquear su afirmación de equivalencia; no fabricar evidencia.

Primera puerta: fixture CPU determinista y float32, exigir igualdad bit a bit de secuencia, etiquetas, tensores y augmentation; exigir inicialmente igualdad exacta de logits, pérdidas, gradientes, métricas y pesos. Hacer A/A con reinicio idéntico para comprobar repetibilidad antes de atribuir discrepancias a B.

Perfil GPU, sólo si A/A demuestra limitación numérica documentada: comparar elemento a elemento con `abs(A-B) <= atol + rtol*abs(A)`. Máximos propuestos: logits/pérdidas/métricas `atol=1e-7, rtol=1e-6`; gradientes/pesos `atol=1e-7, rtol=1e-6`. No admitir NaN/Inf nuevos ni discrepancias de forma. Tensores de entrada, etiquetas, IDs y augmentation siguen siendo exactos en el perfil controlado. Si el ruido A/A supera estos máximos, el perfil queda no demostrado: investigar determinismo/precisión, no ampliar tolerancia después de ver B. Mixed precision requiere protocolo separado aprobado; no queda cubierto por estas tolerancias.

### I.2 Matriz mínima

| Caso | Configuración / evidencia requerida |
|---|---|
| Último batch | 37 TRAIN y 19 VAL, batch 8; confirmar batches finales de 5 y 3, sin `N_batches*8` |
| Shuffle | Varias épocas, con/sin shuffle; comparar secuencia efectiva completa por propósito |
| Augmentation/preprocessing | Activado/desactivado bajo seeds fijas; tensores exactos y mismo estado RNG |
| Custom CNN | Forward, loss, métricas, gradientes y pesos desde inicialización idéntica |
| VGG16 | Cuando está habilitada por registro/config; preprocessing propio y mismas capas congeladas; no sustituir por CNN |
| Dos fases | Base y fine_tuning, optimizador/configuración iguales por fase, offset por épocas reales |
| Early Stopping | Fixture que active parada y restore_best_weights; igualdad de stopped/best/selected epoch y LR |
| Prefetch | Activado según pipeline original; corte controlado con preparación adelantada, sin contar prefetched como procesado |
| Interrupciones | Antes/durante/después de paso; antes de journal, antes/durante commit y después de commit antes de ACK |
| Reenvío | Mismo evento, contradicción, gap y solapamiento; cero procesamiento adicional y cero doble conteo |
| Owner/recuperación | Worker muerto, sesión cerrada, pending local y Docker sin journal; mantener fencing y lagunas |
| Identidad | filenames colisionantes, montajes host/Docker, UUID distintos, mapeo ausente/ambiguo y materialización equivocada |
| EVALUATE | Verificado, parcial, cero filas tras inferencia, fallo de verificación con todas las filas, nuevo intento; sin cambiar su lógica |

Comparar por paso: IDs y orden, tensor de entrada, etiquetas, tamaños/contenido de batches, logits del forward existente, loss, métricas, gradientes cuando observables, variables del optimizador y pesos. Comparar decisiones discretas **exactamente**, aunque valores numéricos estén dentro de tolerancia: checkpoint seleccionado, Early Stopping, LR, número de pasos y épocas, callbacks y sus llamadas. La parada puede ocurrir antes del máximo, pero debe hacerlo igual en A y B.

Para fallos, inyectar en fronteras equivalentes y comparar prefijo científico completado; la entrega de recibos nunca debe repetir ciencia. Simular el fallo durante paso no acredita batch completo aunque haya pesos parcialmente afectados. En EVALUATE validar semántica de resultados/intento sin añadir reintentos de inferencia para recuperar contadores.

Rendimiento: al menos cinco pares A/B con orden alternado después de warm-up equivalente; medir wall time de TRAIN completo, tiempo por paso mediana/p95, throughput, pico RSS/GPU, bytes/filas, latencia de serialización/journal/commit, sincronizaciones host/device y tamaño máximo pendiente. Informar dispersión y hardware. Umbrales iniciales: overhead mediano total ≤5%, p95 por paso ≤10%, memoria incremental agregador ≤32 MiB excluyendo mapa de identidad (reportado separadamente) y ausencia de crecimiento con épocas. Fallar estos umbrales exige rediseño o nueva aprobación explícita; no ocultar costo excluyendo flush final o journal.

Criterio de aprobación: todas las dimensiones aplicables pasan, sin decisiones científicas distintas, sin consumo de prefetch, sin doble conteo, con identidad exacta y ventanas desconocidas correctas. Un caso no ejecutado se marca pendiente. La aprobación documental de 1B.1 no equivale a aprobar la instrumentación de 1B.2.

## J. Plan de intervención quirúrgica posterior

Ninguno de estos archivos se modifica en esta fase. Son puntos previstos, sujetos a elegir y aprobar el mecanismo experimental.

| Archivos concretos (prefijo M salvo indicación) | Intervención futura | Riesgo |
|---|---|---|
| `data/loaders.py`, `execution/train.py` | Enlace de tokens a corriente real, ámbito y confirmación delegada sin reemplazar algoritmo | Alto: orden, RNG, grafo y pasos |
| `training/checkpoint_policy.py`, `evaluation/clinical_metrics.py` | Observar retorno existente por batch clínico sin otra pasada ni mover callback | Alto: sincronización, métricas y selección |
| `data/sample_repository.py`, `data/registry.py`, `data/governed_dataset.py` | Reutilizar lectura masiva y resolución de materialización; mapa verificable | Medio: colisiones, memoria y rutas |
| `persistence/tracking.py`, `persistence/run_repository.py` | Proyección de identidad confirmada en `run_dataset_images`; semántica de flags explícita | Medio: no reutilizar índices como orden real |
| `execution/contracts/events.py`, `results/service.py` | Tipo de evento y validador estricto de payload/ámbito | Medio: compatibilidad de productores/consumidores activos |
| `execution/emitter.py`, `execution/journal.py`, `local_execution/event_journal.py` | Verificar que el nuevo payload conserva estado y replay, sin otro journal | Medio: estado incierto y un solo pending |
| `execution/reporters/http.py`, `execution/reporters/docker.py`, `local_execution/transport.py` | Transporte íntegro y tamaño; cubrir rutas sin emitter | Medio: latencia y garantías divergentes |
| `persistence/result_repository.py`, `execution/repository.py` | Reutilizar fencing/transacciones; validar secuencia y ámbito; ningún bypass de guard | Medio: aceptación y cierre |
| `persistence/execution_record_readers.py`, `execution/completion.py`, `execution/artifacts.py` | Lectura paginada, trace_root_hash y cierre exhaustivo; preservar records_hash histórico | Medio: memoria y semántica de sellado |
| `backend_api/app/repositories/scientific_results.py` | Exponer contadores con nivel de evidencia y desconocido, reutilizando lectura existente | Medio: interpretación; sin cambio frontend en esta fase |
| `assessment/repository.py`, `assessment/service.py`, `assessment/contracts.py` | Sólo puntos de reutilización para lectura y pruebas; sin cambio de inferencia previsto | Bajo si se respeta intento/resultados |
| `malaria_dl_local_project/tests/test_train_run_persistence.py`, `test_pipeline_faults_postgres.py`, `test_event_journal.py`, `test_http_run_reporter.py`, `test_docker_run_reporter.py`, `test_assessment_e6.py`, `test_assessment_postgres.py` | Ampliar cobertura pertinente y arnés A/B sintético específico en 1B.2 | Pruebas futuras; no ejecutadas ahora |

Secuencia propuesta: aprobar contrato → validar identidad y límites de transporte → arnés A/A y A/B sintético → probar candidato de observación → recibos/transporte/fallos y lectura → medir costo → revisión antes de habilitación de producción. No instrumentar producción ni cambiar el experimento para hacer pasar el arnés.

## K. Decisiones pendientes y cierre de diseño

No resoluble sólo por inspección estática:

- Correspondencia completa entre identidades gobernadas y `dataset_split_images` de las materializaciones efectivas; necesidad del mapa tokenizado auxiliar en ledger.
- Técnica TensorFlow/Keras para transportar tokens y confirmar finalización real preservando RNG/grafo/tensores; comportamiento concreto de restauración según versión instalada.
- Igualdad numérica y decisiones A/B, incluyendo VGG16, dos fases, prefetch y Early Stopping.
- Cobertura efectiva del emitter en todas las entradas local/standalone/Docker y aceptación coordinada del nuevo enum; estrategia para entradas legacy que permanezcan sin emitter.
- Tamaño máximo real del transporte, RSS del mapa, costo de journal/commit y viabilidad de límites propuestos; mejora incremental de lectores/cierre actuales.
- Catálogo efectivo de PostgreSQL y disponibilidad/inmutabilidad de referencias de manifiesto; ninguna comprobación de revisión histórica es requisito.
- Política de activación cuando la trazabilidad no puede cumplir identidad/tamaño: no bloquear silenciosamente un experimento ya iniciado ni ejecutarlo afirmando observación completa. Definir habilitación antes del arranque y error explícito de trazabilidad.

Respuestas de cierre: se registran participaciones confirmadas y referencias a resultados existentes; se conservan en el ledger TRAIN y assessments por intento; cada imagen se resuelve con versión/materialización/ruta/hash, manteniendo separados sample_id e image_id; propósito, fase, época e intento delimitan la frecuencia. La suma de multiplicidades deduplicadas da procesamientos, la unión da únicos. Claves estables, contenido inmutable y fencing evitan duplicación; journal/commit conservan lo durable y los cierres incompletos declaran lagunas. El costo se limita por bloques y debe medirse. La invariancia científica sólo se acreditará con el protocolo A/B.

**Validación documental realizada:** contraste de TRACE.1A con rutas operativas de TRAIN, callback clínico, lectura gobernada, repositorio de ejecución, contratos E10, emitter/journal, reporters, servicio/adaptador de resultados, lectores y DDL actual versionado. Se revisaron separaciones legacy/E10, hash final, CHECK de usage_context, PK/FK y estados. No se generó evidencia ficticia ni se realizó SQL, entrenamiento, evaluación, instalación, cambio de código/modelos/callbacks/frontend/esquema, commit o push. TRACE.1B.1 queda listo para revisión documental; TRACE.1B.2 y la instrumentación requieren aprobación posterior.
