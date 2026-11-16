# CAPSTONE-P3-04 — Informe ejecutivo y científico

Fecha: 16 de noviembre de 2026, America/Santiago. Datasource: `malaria`.

**HECHO VERIFICADO.** El identificador solicitado `00b8d407-c672-4b68-9814-53c092d034ba` no es una fila de `runs`: es `assessment_attempts.id`, tipo `evaluate`, split **TEST**, estado `verified`. Su identidad es `a981125c-a9b6-4bec-9fb7-2fa52b907147` y su TRAIN es `87b3eff7-e09a-41c8-945d-bf31b3541adb`. La auditoría conserva el UUID pedido como caso principal y utiliza su TRAIN únicamente para reconstruir el entrenamiento y sus descendientes. Evidencia: [consulta de identidad](sql/principal_identity.sql), [captura](evidence/principal_identity.json), [identidad completa](evidence/principal_full_identity.json).

Convenciones: **HECHO VERIFICADO** = código/registro/archivo observado; **CÁLCULO REPRODUCIDO** = cálculo independiente sobre evidencia existente; **INTERPRETACIÓN CIENTÍFICA** = lectura con límites; **HIPÓTESIS** = explicación no demostrada; **PENDIENTE** = no comprobado. La existencia de código, de un registro `verified` y de un archivo con checksum coincidente son tres evidencias diferentes.

## Resultado científico principal

**CÁLCULO REPRODUCIDO.** VGG16, SGD, semilla 47, checkpoint época 1, threshold `0.25116682052612305`: N=2.685 células de **20 identidades de paciente**. Matriz TEST `[[1145,223],[47,1270]]`. Sensibilidad **96,4313 %**, especificidad **83,6988 %**, precision **85,0636 %**, accuracy **89,9441 %**, F1 **0,90391459**, F2 **0,93921018**, ROC-AUC **0,97887832**, Average Precision (campo PR-AUC) **0,98082304**. La reproducción independiente de todos los conteos y tasas tiene diferencia máxima **0** frente a lo persistido. [Resultados](evidence/metric_reproduction.json), [scores](csv/principal_predictions.csv).

**INTERPRETACIÓN CIENTÍFICA.** Este TEST no alcanza la sensibilidad objetivo del 98 %. El umbral calibrado en VALIDATION sí alcanzó allí 98,0377 %, con especificidad 82,0175 %. No se debe transferir ese cumplimiento a TEST ni presentar una estimación por célula como sensibilidad de diagnóstico por paciente/frotis. No hay validación clínica externa acreditada por estas capturas.

## Capacidades realmente observadas

- Aprendizaje: 28 épocas registradas; 13 base y 15 fine-tuning. El checkpoint conservado pertenece a la fase base. El monitor explícito `val_f2_parasitized` tiene prioridad sobre el nombre de política `auc_with_min_recall`. Loss BCE y F2 cumplen funciones distintas.
- Clínico: el servicio atribuye métricas al intento seleccionado, con split, threshold y checkpoint. El frontend no vuelve a calcular sus tasas. En intentos VAL antiguos pueden faltar F1/AUC/BA por contrato, aun existiendo scores para calcularlas.
- Errores: matriz y scores reconciliados, filtros globales antes de paginar, acuerdo y errores compartidos sobre intersección de muestras. El oracle es una cota descriptiva, no un ensemble.
- XAI principal: nueve EXPLAIN verificados —tres métodos en tres células TEST—, 18 archivos mapa/overlay. Las magnitudes resaltadas no validan conceptos morfológicos ni diagnóstico.
- Arquitectura: VGG16 registrada por TRAIN, 15.241.025 parámetros; 526.337 entrenables en base y 7.605.761 en fine-tuning. No se cargó el checkpoint para contar parámetros: se reconstruyeron desde registros de configuración.
- Representaciones: matriz principal `(2685,512)` con PCA, varianza y UMAP persistidos e íntegros. Dos componentes explican 39,7531 %; 50 explican 87,9255 %. CKA se calcula al consultar, alineando sample_id.
- Trazabilidad: se reconstruyeron imagen, paciente, split, checkpoint y resultado para FN y células XAI. Los identificadores de checkpoint de TRAIN y assessment se derivan por mecanismos distintos y apuntan al mismo hash físico; no son una FK intercambiable.

## Hallazgos prioritarios

1. **HECHO VERIFICADO:** hay 5.386 referencias de archivos XAI que no se resuelven físicamente en las rutas comprobadas, todas de EXPLAIN `ceaa29af-cb60-4be2-8a67-01b9c9382cda`, TRAIN `bbbd5b60-afaa-4034-a504-a60ed642aafe`, marcado `verified`. Esto no afecta a los archivos comprobados del caso principal. No se infiere cuándo o por qué dejaron de estar disponibles.
2. **CÁLCULO REPRODUCIDO:** embeddings TEST de VGG16-SGD y VGG16-Adam semilla 47 son idénticos elemento a elemento y tienen CKA=1; sus errores difieren. **INTERPRETACIÓN:** la extracción es anterior a la cabeza y ambos checkpoints conservan el backbone base congelado. CKA no puede detectar diferencias aprendidas solo por la cabeza.
3. **HECHO VERIFICADO:** GET arquitectura ViT puede cargar una base y persistir una caché estructural. Se inspeccionó, pero no se ejecutó esa rama. Los botones generar XAI/REPRESENT/recorrido tienen efectos y no se usaron.
4. **HECHO VERIFICADO:** `runs.fine_tuning_start_epoch=13` en el principal; el primer evento `phase=fine_tuning` tiene época global 14. La gráfica usa los eventos. Documentar diferencia de índice/frontera, sin asignarle una época inexistente.
5. **HECHO VERIFICADO:** el servicio de métricas exige `population_hash` no nulo para destacar máximos conjuntos, pero la proyección de EVALUATE independiente devuelve `population_hash=None`. Sus métricas pueden estar disponibles sin highlights comparativos.

## Alcance y evidencia de verificación

Capturas PostgreSQL nuevas de esta fecha; no se reutilizan resultados históricos como si fueran actuales. El snapshot de cada consulta es REPEATABLE READ READ ONLY; no se afirma una única transacción global para todos los archivos. Inventario: 86 TRAIN, 2.425 épocas; 141 EVALUATE verificados, 77 EXPLAIN verificados y 2 fallidos, 6 REPRESENT verificados; `training_history=0`, `predictions=0`, `xai_evidence=0`. Las tablas vacías no significan ausencia de resultados: assessments y eventos contienen evidencia. [Conteos](evidence/table_counts.json), [matriz](csv/modality_counts.csv).

Se reprodujeron directamente los seis módulos del servicio de reporte, preflight y arquitectura Keras en el backend Docker, con transacción de solo lectura, sin el transporte HTTP. Los 59 archivos cotejados inicialmente entre workspace y backend coinciden; el inventario final amplía esa comprobación en [runtime_source_identity.csv](csv/runtime_source_identity.csv). No se afirma prueba de navegador ni render de la aplicación desplegada. Las figuras son derivadas de auditoría, no capturas UI.

15 pruebas Python de métricas/contratos REPRESENT y 15 pruebas frontend existentes pasaron. Las pruebas usan contratos/dobles y no certifican inferencia real, fidelidad XAI o validación clínica. [Logs](evidence/tests_python.txt), [frontend](evidence/tests_frontend.txt). No se modificó código productivo ni registros científicos; las modificaciones previas del usuario se conservaron.

## Lectura recomendada

El documento 05 explica matemáticas y siete opciones; el 06 reconstruye el caso principal; el 07 separa comparaciones y cobertura; el 08 detalla riesgos y recomendaciones. El catálogo 03 y sus CSV permiten navegar por funciones y líneas. El README contiene reproducción y límites del cierre.

## Hallazgo de acceso funcional confirmado al cierre

**HECHO VERIFICADO:** el catálogo actual de esta página excluye las tres modalidades BiomedCLIP. `CatalogService.models` conserva solo `model_type=classification` en vista traceability; PostgreSQL registra zero_shot, linear_probe y fine_tuning para esas modalidades. La respuesta real ofrece tres familias CNN, 44 TRAIN elegibles y capacidad máxima 4. La disponibilidad de código/evaluaciones BiomedCLIP no significa que puedan seleccionarse en esta UI. Este límite es prioritario para P3. [Respuesta](evidence/catalog_response.json), [matriz y alcance](CAPSTONE_P3_04_COMPARACION_Y_COBERTURA.md).

Hay además tres recorridos celulares existentes para el TRAIN principal, todos sobre EVALUATE VAL `811dd584-bb41-453d-b7e9-26bd61c9990a`. Sus ocho pasos por célula describen activaciones guardadas y no el TEST solicitado. No se recalcularon. [Resumen sin binarios embebidos](evidence/saved_traces_summary.json).
