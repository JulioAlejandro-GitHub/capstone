# SCC-PRE.1A — Contrato de Comparabilidad Científica

Estado documental: `CURRENT_DOC` — **cerrado documentalmente**, 2026-10-16.
Estado funcional: contrato para SCC-PRE.1B; este cierre no implementa ni certifica operativamente el Preflight.
Proyecto: Capstone. Página: Comparación Científica de Modelos de IA.

## 1. Alcance y autoridad de las fuentes

Este contrato establece las decisiones científicas aprobadas para determinar qué análisis están justificados por la evidencia de los TRAIN seleccionados. No decide cuál modelo es mejor, no modifica resultados experimentales y no impone un bloqueo global del reporte.

Se distinguen tres niveles:

- **Decisiones científicas aprobadas:** reglas normativas de las secciones 2–7.
- **Inventario técnico identificado:** fuentes y operaciones candidatas de las secciones 3 y 8, identificadas documentalmente o mediante lectura estática. Su mención no acredita cobertura por ejecución.
- **Pendientes de verificación:** disponibilidad real, campos, autorización, integridad y consistencia de lectura de la sección 9. No están certificados por este cierre.

Referencias revisadas:

- Propuesta SCC-PRE.1A y solicitud de cierre documental suministradas por el usuario; este documento consolida la propuesta.
- `Capstone - Inventario de datos existentes y su origen.md`, suministrado en `/Users/julio/Desktop/Capstone - Inventario de datos existentes y su origen.md`. No se encontró una copia documental equivalente en el repositorio. Es una fuente **descriptiva**, no normativa; no se modifica ni se convierte su declaración «Disponible» en evidencia verificada.
- [SCC-CORE.1](scc_core_1.md): lectura científica, identidades TRAIN/evaluación/intento y separación de predicciones históricas.
- [SCC-ART.1](scc_art_1.md): acceso a artefactos por identidad y distinción de errores de disponibilidad e integridad.
- [SCC-XAI.2](scc_xai_2.md): métodos, procedencia y servicios compartidos. Sus capacidades de generación en otros contextos no autorizan generación desde Comparación Científica.
- [CAPSTONE-CLI-01](../audits/capstone_cli_01_parameter_certification.md): contratos públicos de TRAIN, EVALUATE, TEST y EXPLAIN.
- [E6](../engineering/etapa_6_evaluate_explain_2026-09-11.md) y [E10.9](../engineering/e10_execution_refactor/e10_9_training_results.md): antecedentes de identidad exacta y resultados TRAIN. Sus ejemplos históricos no sustituyen los contratos públicos vigentes.

## 2. Principios obligatorios

1. La comparabilidad se determina por módulo y análisis, para un conjunto explícito de ejecuciones TRAIN.
2. El reporte siempre se muestra; cada módulo presenta los datos disponibles, aunque no pueda compararlos directamente.
3. Toda incompatibilidad incluye una explicación verificable: condición incumplida, ejecuciones afectadas y referencias a la evidencia.
4. Arquitecturas, semillas, preprocessing, augmentación y políticas de entrenamiento diferentes no implican automáticamente incompatibilidad. Deben describirse y limitar la interpretación cuando corresponda.
5. Ausencia de evidencia no equivale a incompatibilidad demostrada. Configuración declarada no equivale a resultado observado.
6. Los errores técnicos se representan por separado de los estados científicos. Ningún módulo impide visualizar los demás.
7. El reporte es exclusivamente de consulta y análisis. No escribe ni modifica resultados científicos.
8. **Nunca ejecutar automáticamente TRAIN, EVALUATE, TEST, EXPLAIN, extracción de embeddings ni otros procesos científicos desde Comparación Científica.** Esta prohibición rige para todos los módulos actuales y futuros, al abrir, seleccionar, consultar o refrescar el reporte y ante evidencia faltante o errores. El reporte no incorpora acciones de generación de otros visores.
9. El Preflight no recalcula ni persiste métricas o resultados experimentales; solo determina condiciones, cobertura y hallazgos sobre evidencia existente. Este contrato tampoco autoriza implementar o ejecutar PCA, UMAP o CKA.

## 3. Dimensiones A1–A6

Las condiciones siguientes se aplican al análisis y a la población declarados, no indiscriminadamente a toda la página. Las fuentes son conocidas o candidatas, no evidencia operativa certificada en esta entrega. Si un campo no existe o no es recuperable, se informa la limitación; no se inventa ni se exige crear datos para poder mostrar el reporte.

### A1 — Identidad del dataset

- **Evidencia requerida:** versión y procedencia del dataset de cada TRAIN y de la población efectivamente evaluada, cuando corresponda.
- **Fuente conocida:** `runs.dataset_version_id`, `dataset_versions`, configuración/snapshots persistidos y lectura de dataset gobernado.
- **Compatibilidad:** misma versión con relación acreditada; versiones diferentes solo pueden considerarse equivalentes para una población concreta si existe evidencia adicional que lo justifique.
- **Advertencias:** versiones distintas, diferencias de procedencia o de población de entrenamiento; no equivalen por sí solas a rechazo de toda comparación.
- **Incompatibilidad acreditable:** poblaciones demostrablemente distintas cuando el análisis requiere la misma población; referencias contradictorias que impiden atribuir los datos utilizados.
- **Insuficiencia:** identidad, procedencia o correspondencia no recuperable; una versión declarada sin relación verificable no acredita equivalencia.
- **Análisis afectados:** interpretación de curvas y métricas; procedencia de predicciones, XAI y representaciones. Se combina con A2/A3 para evaluar la población concreta.

### A2 — Identidad del split

- **Evidencia requerida:** partición TRAIN, VAL o TEST y población asociada a cada resultado seleccionado.
- **Fuente conocida:** identidad de evaluación/intento, dataset gobernado y particiones físicas referenciadas; evaluaciones y snapshots persistidos según su contrato.
- **Compatibilidad:** VAL con VAL o TEST con TEST y población acreditada. El nombre del split por sí solo no prueba identidad de muestras.
- **Advertencias:** cobertura parcial explícita o poblaciones distintas mostradas individualmente; una comparación descriptiva VAL–TEST debe identificarse como cambio entre particiones.
- **Incompatibilidad acreditable:** tratar VAL y TEST como la misma población, o poblaciones demostrablemente diferentes como idénticas en una comparación que exige igualdad.
- **Insuficiencia:** split o pertenencia poblacional desconocidos; no asignar un split por defecto.
- **Análisis afectados:** métricas directas, consenso/desacuerdo y cualquier comparación de XAI o representaciones dependiente de población.

### A3 — Identidad de muestras

- **Evidencia requerida:** identificadores individuales, etiquetas reales, población por ejecución, correspondencia entre fuentes y cobertura completa de los registros consultados.
- **Fuente conocida:** `assessment_results` por intento; `predictions` y `run_image_predictions` en sus contratos históricos. Sus identificadores no se consideran equivalentes por tener el mismo formato.
- **Compatibilidad:** alineación inequívoca y etiquetas coherentes para la población usada; una intersección parcial solo habilita el análisis explícito de esa intersección.
- **Advertencias:** muestras exclusivas/faltantes y cobertura parcial cuantificada por ejecución según P4.
- **Incompatibilidad acreditable:** etiquetas contradictorias o duplicados conflictivos que impiden una correspondencia única en el conjunto afectado; intersección vacía acreditada para un análisis pareado.
- **Insuficiencia:** claves sin correspondencia demostrada, páginas incompletas o etiquetas ausentes. No calcular consenso, desacuerdo ni complementariedad por célula sin alineación acreditada.
- **Análisis afectados:** consenso/desacuerdo, complementariedad, comparaciones XAI por muestra, PCA/UMAP conjuntos y CKA.

### A4 — Configuración experimental

- **Evidencia requerida:** arquitectura, semilla, preprocessing, augmentación, hiperparámetros relevantes, objetivo de optimización y políticas de entrenamiento efectivamente persistidas.
- **Fuente conocida:** configuración del TRAIN, `run_configurations`, `runs` y registros/snapshots de entrenamiento expuestos por las lecturas existentes; cobertura por comprobar.
- **Compatibilidad:** diferencias descritas y compatibles con la pregunta científica. No se exige misma arquitectura ni idénticos hiperparámetros.
- **Advertencias:** diferencias de semilla, preparación de entradas, augmentación o entrenamiento que limitan atribuir causalmente una diferencia de desempeño solo a la arquitectura; configuración incompleta limita reproducibilidad.
- **Incompatibilidad acreditable:** una comparación expresamente definida como controlada incumple una condición controlada con evidencia; no invalida la visualización descriptiva de esas ejecuciones.
- **Insuficiencia:** no puede recuperarse la configuración necesaria para la afirmación solicitada. No rellenarla con defaults actuales.
- **Análisis afectados:** curvas, convergencia, costos y atribución de diferencias de desempeño o representaciones.

### A5 — Checkpoint seleccionado

- **Evidencia requerida:** identidad del checkpoint, TRAIN de origen, época, política de selección, localizador gobernado y hash cuando existan; disponibilidad, integridad y linaje separados según P3.
- **Fuente conocida:** `artifacts`, versiones de modelo, política del checkpoint, registros TRAIN e identidades de assessments; acceso físico mediante mecanismos actuales.
- **Compatibilidad:** atribución inequívoca de los resultados al modelo seleccionado; integridad acreditada cuando la operación depende de los bytes.
- **Advertencias:** política o época incompleta limita reproducibilidad; ausencia física no invalida automáticamente métricas persistidas con linaje acreditado.
- **Incompatibilidad acreditable:** checkpoint atribuido a otro TRAIN, referencias contradictorias o discrepancia de contenido verificada para la evidencia que se pretende utilizar.
- **Insuficiencia:** linaje no verificable o integridad no comprobada cuando son necesarios. `not_checked` no prueba disponibilidad ni ausencia.
- **Análisis afectados:** atribución de métricas, XAI y representaciones; cualquier operación que requiera cargar un modelo necesita archivo accesible e íntegro, pero no está autorizada por este reporte.

### A6 — Protocolo de evaluación

- **Evidencia requerida:** evaluación e intento exactos, split, población, checkpoint, resultados, umbral, regla de decisión, semántica de scores/clases y definición de métricas cuando corresponda.
- **Fuente conocida:** `assessment_identities`, `assessment_attempts`, `assessment_results`; `evaluations`, predicciones y métricas persistidas según la fuente; calibración de umbral y lectura científica compartida.
- **Compatibilidad:** resultados atribuibles a la selección P2, con población y protocolos compatibles para la afirmación solicitada. Métricas agregadas y predicciones individuales son evidencias distintas.
- **Advertencias:** umbrales distintos permiten describir desempeño bajo reglas distintas, no afirmar que se usó una regla común; diferencias relevantes de inferencia deben exponerse.
- **Incompatibilidad acreditable:** definiciones o reglas demostrablemente incompatibles con la comparación solicitada, o mezcla de resultados de evaluaciones/intentos distintos sin atribución válida.
- **Insuficiencia:** protocolo, resultados o identidad incompletos. La configuración de una evaluación no demuestra que haya resultados observados.
- **Análisis afectados:** métricas VAL/TEST, consenso/desacuerdo y contextualización de errores y XAI asociados a una evaluación.

## 4. P1 — Estados por análisis y conjunto de ejecuciones

La unidad primaria de procedencia sigue siendo `runs.id` (`run_id`) del TRAIN. La unidad del dictamen es **el análisis solicitado y su conjunto explícito de TRAIN participantes**, con las selecciones de evidencia de P2. Un subconjunto comparable no representa automáticamente a la selección completa.

El reporte distingue:

- Hallazgos y estado de cada dimensión A1–A6 para el alcance examinado.
- Estado científico de cada análisis concreto y sus motivos.
- Cobertura: TRAIN solicitados, participantes con evidencia, excluidos o no evaluables y motivo por ejecución; además de cobertura de muestras cuando corresponda.
- Resumen informativo de cantidades de análisis por estado y motivos, con errores técnicos separados.

| Estado científico | Significado normativo |
|---|---|
| `COMPARABLE` | Evidencia necesaria acreditada para ese análisis y conjunto, sin diferencias que limiten su interpretación directa. |
| `COMPARABLE CON ADVERTENCIAS` | Análisis posible en el alcance declarado, con diferencias o limitaciones explícitas. |
| `NO COMPARABLE` | Incompatibilidad demostrada que impide la comparación solicitada en ese alcance. |
| `EVIDENCIA INSUFICIENTE` | No se puede acreditar compatibilidad ni incompatibilidad con la evidencia disponible. |

`ERROR DE CONSULTA` es una condición técnica separada, no un quinto estado científico ni una prueba de ausencia. Si impide emitir un dictamen, este queda no evaluado por ese error; no se fabrica una conclusión científica.

No existe precedencia artificial entre `NO COMPARABLE` y `EVIDENCIA INSUFICIENTE`. Si una petición reúne condiciones o poblaciones con estados distintos, se conservan sus hallazgos y se desglosan los análisis/alcances afectados. Una incompatibilidad comprobada no elimina una carencia de evidencia, ni viceversa. El resumen cuenta cada análisis concreto una vez y presenta su alcance; no colapsa el reporte mixto en una etiqueta única. La representación técnica de ese desglose queda para SCC-PRE.1B.

Ejemplo normativo: curvas disponibles con advertencias, comparación VAL–TEST incompatible como población única y CKA sin representaciones producen tres entradas con sus motivos. Todas siguen visibles; no hay un estado global que deshabilite módulos.

## 5. P2 — Identidad exacta de evaluación

Cada selección de evidencia debe fijar, según corresponda: TRAIN de origen, checkpoint atribuido, identidad de evaluación, intento, split, población evaluada y resultados utilizados. Un `run_id` de TRAIN por sí solo no identifica una evaluación científica específica.

No seleccionar implícitamente la última evaluación ni el último intento. Una futura selección predeterminada requiere política explícita, documentada, visible y científicamente justificable; este contrato no establece ninguna.

SCC-CORE.1 distingue identidad e intento de assessments de las evaluaciones/predicciones históricas. Documenta TEST como `kind='evaluate'` con split `test` y proyección `assessment_type='TEST'`. Estos son contratos identificados, no una certificación nueva del esquema operativo. SCC-PRE.1B debe verificar nombres, relaciones y campos reales; no suponer columnas universales ni fabricar equivalencias entre `sample_id`, `image_id` y `dataset_source_record_id`.

No concatenar resultados parciales de distintos intentos como una sola evaluación ni elegir resultados por mejor desempeño. Conservar fuente, identidad y estado originales. EXPLAIN independiente sin evaluación padre se declara como tal; no se inventa un vínculo y no habilita análisis que dependan de conocer aciertos/errores sin evidencia adicional.

## 6. P3–P5 — Evidencia específica

### P3 — Disponibilidad, integridad y linaje del checkpoint

| Concepto | Qué acredita | Consecuencia |
|---|---|---|
| Disponibilidad física | Archivo `.keras` accesible en el mecanismo gobernado | Necesaria para cargarlo; registro o ruta no prueban existencia. |
| Integridad | Contenido verificado frente a evidencia de hash/tamaño correspondiente | Hash almacenado sin comprobación no acredita bytes actuales. |
| Linaje científico | Atribución inequívoca de resultados al checkpoint y al TRAIN | Necesario para atribuir métricas, explicaciones y representaciones. |

`not_checked` se muestra como no comprobado. Si el archivo está ausente, pueden seguir mostrándose y comparándose métricas persistidas con linaje y protocolo acreditados. Del mismo modo, un artefacto XAI o embedding persistido puede ser utilizable sin cargar el checkpoint, si su propio contenido y procedencia satisfacen el análisis. Una contradicción de linaje afecta solo a las atribuciones dependientes; una falla de acceso no demuestra corrupción. No se reconstruyen ni regeneran archivos.

### P4 — Intersección de muestras

Para cada ejecución participante se informa tamaño de población, identificadores, muestras exclusivas/faltantes, duplicados y conflictos de etiquetas. Para el conjunto explícito se informa la intersección acreditada y su tamaño.

La cobertura para cada ejecución i es `n_intersección / n_población_i`, con numerador y denominador visibles. Si el denominador no se conoce, no se inventa un porcentaje; si es cero, la razón se declara no definida. El conteo de filas no sustituye al conteo de muestras únicas cuando existen duplicados. Las páginas recuperadas se distinguen de la población completa; una página no acredita por sí sola cobertura total.

Duplicados y etiquetas contradictorias se identifican y explican, sin corregir, deduplicar, descartar ni resolver silenciosamente. Si se propone un subconjunto limpio, su regla y exclusiones deben ser explícitas y su estado independiente; no representa el conjunto original.

La intersección parcial solo habilita análisis pareados sobre esa población común acreditada. Las métricas agregadas originales conservan su población de origen: no se presentan como recalculadas sobre la intersección. El Preflight no recalcula ni persiste resultados experimentales.

### P5 — XAI, embeddings y CKA

Para XAI se requiere, según el método y análisis: Grad-CAM/LIME/SHAP, clase objetivo, configuración, capa cuando aplique, referencia/background de SHAP, muestra explicada, checkpoint, evaluación de origen cuando exista e identidad del artefacto. Ausencia de evaluación padre se declara y limita los análisis que la necesitan. Tener dos archivos Grad-CAM no prueba equivalencia metodológica; métodos distintos pueden mostrarse individualmente sin afirmar que sus valores tienen la misma interpretación.

Para embeddings y representaciones se requiere, según el análisis: checkpoint, población y orden de muestras, capa de extracción, protocolo, preprocessing, dimensionalidad, transformaciones y parámetros, además de la alineación exigida por el método comparativo. Proyecciones independientes no acreditan por sí solas un sistema de coordenadas común.

No se exige que arquitecturas distintas usen capas con igual nombre o dimensionalidad idéntica. Las restricciones deben justificarse por el método concreto de comparación; no se declara CKA compatible por la mera presencia de embeddings. El inventario describe embeddings como por extraer y PCA/UMAP/CKA como por calcular: eso no certifica disponibilidad ni autoriza su generación desde el reporte.

## 7. Matriz normativa de análisis y estados ante limitaciones

Cada fila aplica los cuatro estados de P1 a análisis concretos y conjuntos explícitos; el módulo sigue visible en todos los estados.

| Módulo | Evidencia mínima/principal | Condiciones de comparación | Comportamiento ante limitaciones |
|---|---|---|---|
| Preflight | Evidencia recuperable de A1–A6 y referencias | Dictamen por análisis, alcance y selección P2 | Mostrar dimensiones, diferencias, ausencias, incompatibilidades y errores por separado; no aplicar bloqueo global. |
| Curvas TRAIN/VAL | Historial por época, nombres/definiciones de métricas y configuración A4 | Series con significado y eje identificados; A1/A2 contextualizan poblaciones | Mostrar curvas disponibles individualmente, huecos y diferencias; no inventar épocas o métricas ni afirmar equivalencia de protocolos. |
| Métricas VAL/TEST | Evaluaciones/resultados seleccionados, población, A1/A2/A5/A6 | Misma población acreditada y protocolos compatibles con la afirmación | Comparar solo resultados compatibles; mostrar los demás individualmente con split, origen y motivos. Checkpoint físicamente ausente no invalida por sí solo métricas trazables. |
| Consenso y desacuerdo | Predicciones individuales, etiquetas, A2/A3/A6 y linaje de origen | Alineación inequívoca; cobertura P4 y reglas de decisión explícitas | Sin alineación no calcular análisis pareados; mostrar registros disponibles y motivos. Intersección parcial se declara como alcance propio. |
| XAI | Artefactos existentes, A3/A5 y evidencia metodológica P5; A6 para contexto de evaluación | Muestra/clase/linaje y metodología compatibles con el análisis específico | Mostrar artefactos disponibles individualmente; explicar incompatibilidades y no inferir equivalencia por método/nombre de archivo. No generar explicaciones. |
| PCA/UMAP | Embeddings/proyecciones existentes, A3/A5 y extracción/transformaciones P5 | Población y transformaciones acreditadas para la comparación; coordenadas comunes solo si están justificadas | Mostrar evidencia existente y sus limitaciones. No iniciar extracción ni cálculos para completar ausencias. |
| CKA | Representaciones existentes, A3/A5, orden/alineación y protocolo P5 | Evidencia metodológica suficiente para el método y capas seleccionados | No calcular similitud sin esa evidencia; mostrar resultados existentes trazables, ausencias y motivos. Este cierre no implementa ni ejecuta CKA. |

| Situación | Presentación y consecuencia obligatorias |
|---|---|
| Datos parciales | Mostrar lo recuperado, población/cobertura y alcance; no presentarlo como completo ni ocultar resultados válidos. |
| Evidencia insuficiente | Mostrar `Sin evidencia` en el dato no acreditado y explicar qué falta para el análisis; no inferir que nunca se ejecutó el proceso. |
| Propiedad no aplicable | Mostrar `N/A` con el alcance correspondiente; no confundir con ausencia. |
| Incompatibilidad científica | Mostrar `NO COMPARABLE` para el análisis afectado, condición verificable y datos individuales disponibles. |
| Error HTTP o SQL | Mostrar `ERROR DE CONSULTA`, operación/alcance afectado y mensaje comprensible sin exponer información sensible; no convertirlo en colección vacía ni incompatibilidad. |
| Artefacto no disponible | Conservar metadatos y resultados restantes; distinguir no comprobado, ausencia comprobada, acceso fallido e integridad fallida. No regenerar. |
| Resultados contradictorios | Mostrar fuentes e identidades en conflicto; no sobrescribir ni escoger silenciosamente una. Delimitar qué atribuciones no pueden sostenerse y qué evidencia falta. |

En todos los casos se conserva la visualización del reporte y de los datos válidos restantes. Un 403, un fallo SQL o un almacenamiento inaccesible no certifican ausencia de evidencia científica. Las limitaciones pueden coexistir y deben conservarse en el resumen informativo.

## 8. Inventario de reutilización para SCC-PRE.1B

El catálogo HTTP/SQL de Capstone es **lógico y distribuido por dominios**. PostgreSQL es la fuente de verdad de resultados estructurados; los artefactos se consultan mediante sus mecanismos actuales. No crear repositorios SQL paralelos cuando existan operaciones de dominio semánticamente compatibles. Esta sección no autoriza refactorizaciones ni nuevas tablas/migraciones.

| Evidencia | Operación candidata | Alcance por verificar |
|---|---|---|
| Lectura científica del TRAIN | `GET /runs/{run_id}/scientific-results?view=traceability` | Campos, fuentes, relaciones y paginación de predicciones; no inferir disponibilidad física. |
| Configuración e historia | `GET /runs/{run_id}` | Configuración efectiva, historia por época y procedencia de métricas. |
| Dataset gobernado | `GET /api/datasets/{dataset_version_id}` | Procedencia, identidad de particiones y poblaciones recuperables. |
| Política de checkpoint | `GET /runs/{run_id}/checkpoint-policy` | Identidad, época, política y relación con el checkpoint realmente usado. |
| Calibración de umbral | `GET /runs/{run_id}/threshold-calibration` | Umbral/regla aplicables a la evaluación seleccionada; no confundir con calibración de probabilidades. |
| Predicciones paginadas | `GET /runs/{run_id}/image-predictions` | Fuente histórica, filtros, identidad, cobertura y correspondencia con la evaluación seleccionada. |
| Artefactos | `GET /runs/{run_id}/artifacts-summary` | Registro y pertenencia; no prueba de existencia o integridad. |
| Identidad e intentos | `GET /assessments?training_run_id=…&view=traceability` y `GET /assessments/{attempt_id}?view=traceability` | Selección exacta, población, protocolo y estados. |
| Resultados por intento | `GET /assessments/{attempt_id}/results?view=traceability` | Predicciones, etiquetas y cobertura de todas las páginas del intento. |
| Artefactos por intento | `GET /assessments/{attempt_id}/artifacts?view=traceability` | Identidad y procedencia; acceso de contenido según SCC-ART.1. |

Se revisó estáticamente [ScientificReadService](../../backend_api/app/services/scientific_results.py): compone repositorios compartidos, valida TRAIN de clasificación en la vista de trazabilidad y proyecta artefactos con `file_availability='not_checked'`. Esto describe código, no una prueba operativa ni disponibilidad de campos en todas las ejecuciones. El acceso de artefactos de SCC-ART.1 no habilita descarga de checkpoints `.keras`; no asumir que una operación de imágenes resuelve su comprobación física.

Identificar una operación no acredita su cobertura completa. Antes de reutilizar deben verificarse autorización, semántica de entradas/salidas/errores, consistencia de lectura, transacciones, paginación y evidencia realmente recuperable. Los consumidores deben preservar `run_id`, fuente, evaluación e intento, usando las proyecciones públicas de trazabilidad cuando existan.

`/models/comparison` no constituye una implementación de A1–A6 por su nombre: la revisión estática identificó una consulta de resumen clínico. Tampoco una lectura científica disponible equivale a un dictamen de comparabilidad ya implementado.

## 9. Pendientes concretos de SCC-PRE.1B

1. Mapear cada evidencia A1–A6 a campos y relaciones reales por dominio, diferenciando TRAIN, evaluaciones históricas y assessments. Verificar las poblaciones efectivamente recuperables sin equiparar claves por su nombre.
2. Comprobar autorización y errores HTTP/SQL de cada operación candidata; documentar campos ausentes y diferencias semánticas antes de decidir reutilización o adaptación en la capa existente.
3. Definir consistencia de lectura entre fuentes y páginas, límites y orden estable para acreditar cobertura sin mezclar cambios o intentos. Una consulta parcial no certifica ausencia global.
4. Formalizar el contrato de hallazgos, referencias, estados por dimensión/análisis, cobertura y resumen mixto; conservar simultáneamente incompatibilidades, carencias y errores técnicos sin precedencia artificial.
5. Implementar selección exacta y visible de evaluación/intento; si se propone un default, documentar su justificación científica antes de incorporarlo. No elegir «último» implícitamente.
6. Verificar cómo acreditar disponibilidad, integridad y linaje mediante mecanismos existentes, sin escaneos masivos ni carga/generación automática de modelos. Diferenciar lo no comprobado de lo ausente.
7. Verificar alineación completa, denominadores por ejecución, duplicados y conflictos de etiquetas; especificar presentación explícita de subconjuntos y exclusiones sin reparar resultados.
8. Comprobar cobertura metodológica de XAI y existencia real de representaciones/proyecciones. Documentar lo faltante; no crear embeddings ni resultados para satisfacer el contrato.
9. Validar presentación individual y aislamiento de fallos entre módulos, incluida la ausencia de llamadas de generación automática. La implementación futura deberá aportar evidencia de sus verificaciones; este documento no las sustituye.

## 10. Cierre documental y límites de la entrega

| Criterio de aceptación | Ubicación |
|---|---|
| A1–A6: evidencia, fuentes, compatibilidad, advertencias, incompatibilidad, insuficiencia y análisis afectados | Sección 3 |
| P1: estados por análisis/conjunto y resumen mixto sin bloqueo | Sección 4 |
| P2: identidad exacta de evaluación/intento | Sección 5 |
| P3: disponibilidad, integridad y linaje separados | Sección 6, P3 |
| P4: intersección y cobertura por ejecución, sin reparación silenciosa | Sección 6, P4 |
| P5: dependencias XAI, embeddings y CKA | Sección 6, P5 |
| Matriz normativa, datos individuales y separación de errores técnicos | Sección 7 |
| Prohibición transversal de ejecución automática | Sección 2 |
| Operaciones candidatas sin certificación inexistente y pendientes de implementación | Secciones 8–9 |

SCC-PRE.1A queda cerrado documentalmente con estas decisiones aprobadas. El cierre no significa que SCC-PRE.1B esté implementado ni que ejecuciones concretas sean comparables.

Esta entrega solo crea el contrato y actualiza su entrada en el índice documental. No modifica el inventario descriptivo, skills, Python, SQL, TypeScript, React, CSS, tablas o migraciones; no ejecuta procesos científicos, no recalcula métricas y no realiza commit ni push. La revisión de referencias y código es estática; no se ejecutaron consultas operativas ni se certificaron artefactos físicos.
