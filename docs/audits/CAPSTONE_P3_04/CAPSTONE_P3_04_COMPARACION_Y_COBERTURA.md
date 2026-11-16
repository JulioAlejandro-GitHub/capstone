# CAPSTONE-P3-04 — Comparación y cobertura

Fecha: 16 de noviembre de 2026, America/Santiago. Datasource: `malaria`.

## Motor y disponibilidad de la página

**HECHO VERIFICADO:** el catálogo de esta página ofrece custom_cnn, DenseNet121 y VGG16, con 44 TRAIN elegibles de 59 registrados en esas familias: 16/23, 14/18 y 14/18 respectivamente. La capacidad es cuatro participantes. `CatalogService.models(traceability=True)` filtra `model_type=classification`; los modelos BiomedCLIP usan zero_shot, linear_probe y fine_tuning y quedan excluidos del selector, aunque tengan TRAIN y evaluaciones. [Respuesta real](evidence/catalog_response.json), [código](../../../backend_api/app/services/catalog.py#L18).

La admisión exige TRAIN completado, checkpoint acreditado y EVALUATE finalizado/verificado con resultados y binding coherente. EXPLAIN es opcional. Esta regla de admisión al reporte no es un prerrequisito de TEST. Tampoco acredita comparabilidad científica ni presencia continua de todos los archivos.

## Matriz funcional por modalidad

| Modalidad | Aprendizaje | Clínico | Errores/consenso | XAI | Arquitectura | Representaciones | Trazabilidad |
|---|---|---|---|---|---|---|---|
| Custom CNN | Implementado y verificado | Implementado y verificado | Implementado y verificado | Disponible con limitaciones¹ | Implementado y verificado² | Disponible con limitaciones³ | Disponible con limitaciones¹ |
| VGG16 | Implementado y verificado | Implementado y verificado | Implementado y verificado | Implementado y verificado | Implementado y verificado | Implementado y verificado | Disponible con limitaciones⁴ |
| DenseNet121 | Implementado y verificado | Implementado y verificado | Implementado y verificado | Implementado y verificado | Implementado y verificado² | Implementado y verificado | Disponible con limitaciones⁴ |
| BiomedCLIP Zero-shot | Parcial⁵ | Parcial⁵ | Parcial⁵ | Parcial⁵ | Parcial⁵ | Implementado, sin datos para el RUN⁵ | Parcial⁵ |
| BiomedCLIP Linear | Parcial⁵ | Parcial⁵ | Parcial⁵ | Implementado, sin datos para el RUN⁵ | Parcial⁵ | Implementado, sin datos para el RUN⁵ | Parcial⁵ |
| BiomedCLIP Fine-tuning | Parcial⁵ | Parcial⁵ | Parcial⁵ | Implementado, sin datos para el RUN⁵ | Parcial⁵ | Implementado, sin datos para el RUN⁵ | Parcial⁵ |

1. Custom CNN tiene EXPLAIN verificados y dos fallidos. Un EXPLAIN verificado conserva 5.386 referencias sin archivos localizables; no generalizar esa ausencia a todos los RUN.
2. Factories, registros de arquitectura y renderers CNN están implementados. El replay completo de arquitectura se ejecutó para VGG principal; Custom/DenseNet tienen revisión estática y evidencia registral, sin prueba del render de navegador.
3. Custom tiene un REPRESENT; disponibilidad depende del EVALUATE exacto y no se hereda automáticamente de otro split.
4. Linaje registral disponible, con límites de hashing global y sin cadena acreditada a frotis completo.
5. BiomedCLIP es parcial por exclusión de UI. Zero-shot no tiene épocas propias por diseño, pero registra seis EVALUATE y dos EXPLAIN (LIME/SHAP). Linear/fine-tuning tienen curvas y 24/25 EVALUATE respectivamente, sin EXPLAIN ni REPRESENT persistidos. Los runtimes de explicación y extracción existen; ausencia de ejecución no significa «No implementado». Grad-CAM ViT no está soportado. No se ejecutó la rama de estructura ViT que podría generar caché.

«Implementado y verificado» significa código y evidencia observada para al menos un caso; no certifica cada RUN ni validación clínica. El render final en navegador y la revisión morfológica experta son **No verificable en esta auditoría**. Clustering aprendido, kernel CKA y TCAV son **No implementado en el contrato de esta pestaña**.

## Conteos registrales actuales

| Modalidad | TRAIN | Completados | Épocas | EVALUATE verificados | EXPLAIN verificados | EXPLAIN fallidos | REPRESENT verificados |
|---|---|---|---|---|---|---|---|
| biomedclip_fine_tuning | 13 | 12 | 365 | 25 | 0 | 0 | 0 |
| biomedclip_linear | 13 | 12 | 380 | 24 | 0 | 0 | 0 |
| biomedclip_zero_shot | 1 | 1 | 0 | 6 | 2 | 0 | 0 |
| custom_cnn | 23 | 22 | 392 | 32 | 21 | 2 | 1 |
| densenet121 | 18 | 18 | 762 | 27 | 6 | 0 | 2 |
| vgg16 | 18 | 18 | 526 | 27 | 48 | 0 | 3 |

Las épocas son eventos, no células. Los intentos no son pacientes ni RUN únicos. Los seis REPRESENT corresponden a cuatro TRAIN y dos splits; no se mezclan sus poblaciones. [CSV](csv/modality_counts.csv).

## RUN principal

El UUID solicitado `00b8d407-c672-4b68-9814-53c092d034ba` es un **intento EVALUATE TEST** del TRAIN VGG16-SGD47 `87b3eff7-e09a-41c8-945d-bf31b3541adb`. Sus resultados propios son N=2.685, errores=270, FN=47, FP=223, sensibilidad=96,4313 %, especificidad=83,6988 %, threshold=0,25116682 y checkpoint de época 1, fase base. [Ficha completa](CAPSTONE_P3_04_RUN_00b8d407.md).

## Referencias secundarias

| Referencia | TRAIN | Intento TEST | REPRESENT TEST |
|---|---|---|---|
| VGG16-Adam47 | 910051e5-a00c-44c4-9d23-77598af470f7 | d1ce1424-c7c3-4ee8-816d-3b91090b42cf | 2e2c20ac-9014-4e2b-9d6c-7d820bed4f2f |
| DenseNet121-Adam47 | b1b39079-658f-4300-b159-52619f981035 | 521219d9-7865-428f-9bcf-1491dd754a5e | f23e286f-3ce7-473f-8a81-dc2952f0dad0 |

Se eligieron para mostrar comparación pareada y CKA, no para sustituir resultados ausentes del principal. Cada EVALUATE utiliza su threshold persistido; no se impuso un nuevo umbral común. Los scores y etiquetas se obtuvieron por SELECT sin ejecutar modelos.

## Comparación entre RUNs: errores sobre la misma población

| Intento A | Intento B | N | Acuerdos | Errores A | Errores B | Comunes | FN comunes | FP comunes | Solo A | Solo B | Oracle |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 00b8d407-c672-4b68-9814-53c092d034ba | d1ce1424-c7c3-4ee8-816d-3b91090b42cf | 2685 | 2569 | 270 | 290 | 222 | 35 | 187 | 48 | 68 | 0.91731844 |
| 00b8d407-c672-4b68-9814-53c092d034ba | 521219d9-7865-428f-9bcf-1491dd754a5e | 2685 | 2210 | 270 | 639 | 217 | 20 | 197 | 53 | 422 | 0.91918063 |
| d1ce1424-c7c3-4ee8-816d-3b91090b42cf | 521219d9-7865-428f-9bcf-1491dd754a5e | 2685 | 2234 | 290 | 639 | 239 | 18 | 221 | 51 | 400 | 0.91098696 |

**CÁLCULO REPRODUCIDO:** 2.685 sample_id comunes, etiquetas coincidentes y decisiones persistidas. Principal/VGG-Adam coinciden en 2.569 decisiones (95,6797 %) y comparten 222 errores; hay 48 errores solo del principal y 68 solo de Adam. El oracle es 91,7318 %. Principal/DenseNet comparte 217 errores y tiene oracle 91,9181 %. Son cotas descriptivas que requieren saber qué modelo acierta en cada célula; no son ensembles implementados ni estimaciones de un predictor desplegable. [Cálculo](evidence/pairwise_errors.json), [SQL](sql/comparison_test_scores.sql).

## Comparación entre RUNs: representaciones

| TRAIN A | TRAIN B | Split | N común | CKA lineal |
|---|---|---|---|---|
| 87b3eff7-e09a-41c8-945d-bf31b3541adb | 910051e5-a00c-44c4-9d23-77598af470f7 | test | 2685 | 1.0 |
| 87b3eff7-e09a-41c8-945d-bf31b3541adb | b1b39079-658f-4300-b159-52619f981035 | test | 2685 | 0.730825699543623 |
| 910051e5-a00c-44c4-9d23-77598af470f7 | b1b39079-658f-4300-b159-52619f981035 | val | 2693 | 0.6794049651011471 |
| 910051e5-a00c-44c4-9d23-77598af470f7 | b1b39079-658f-4300-b159-52619f981035 | test | 2685 | 0.730825699543623 |

**CÁLCULO REPRODUCIDO:** GAP TEST de VGG-SGD y VGG-Adam es idéntico elemento a elemento, diferencia máxima 0, CKA=1. La extracción ocurre antes de Dense1024; los checkpoints base conservan el extractor ImageNet congelado. Las cabezas pueden producir errores diferentes sobre el mismo vector. Esto no demuestra igualdad de aprendizaje global ni conceptos médicos compartidos. [Comparación exacta](evidence/vgg_embedding_identity.json).

CKA TEST de cualquiera de esos VGG con DenseNet es 0,7308257. En VAL, VGG-Adam/DenseNet tiene 0,679405. No interpretar esa diferencia VAL/TEST como cambio interno del modelo: cambia la población. No se midió incertidumbre de CKA ni se compararon todas las capas o semillas.

## Preguntas del Capstone

| Pregunta | Clasificación | Evidencia y límite |
|---|---|---|
| ¿Cuál aprendió mejor? | Respondible parcialmente | Curvas y objetivo sobre poblaciones alineadas; menor loss no implica mayor sensibilidad clínica. |
| ¿Cuál generaliza mejor? | Respondible parcialmente | TEST describe poblaciones concretas; superioridad requiere incertidumbre y comparación pareada. |
| ¿Cuál tiene mayor sensibilidad? | Respondible con evidencia actual | Tasas de intentos y thresholds identificados; no ganador universal. |
| ¿Cuál tiene más FN? | Respondible con evidencia actual | Conteos con el mismo N positivo; de otro modo comparar también tasas. |
| ¿Se equivocan en las mismas células? | Respondible con evidencia actual | Intersección por sample_id y etiquetas reconciliadas; ejemplos entregados. |
| ¿Tienen errores complementarios? | Respondible con evidencia actual | Errores exclusivos y compartidos; no prueba beneficio de un ensemble. |
| ¿Hay señales de sobreajuste? | Respondible parcialmente | Evolución temporal TRAIN/VAL y checkpoint, no solo brecha VAL–TEST. |
| ¿Qué regiones usan? | Respondible parcialmente | XAI por célula/checkpoint; conceptos morfológicos requieren nuevas anotaciones de expertos. |
| ¿Qué tan similares son sus representaciones? | Respondible parcialmente | Seis REPRESENT; ampliar cobertura requiere nuevas evaluaciones REPRESENT, no necesariamente nuevos TRAIN. |
| ¿Relación arquitectura, embeddings y errores? | Respondible parcialmente | IDs permiten cruzar; GAP idéntico con errores distintos está demostrado; causalidad requiere estudios controlados. |
| ¿Estabilidad entre semillas y optimizadores? | Requiere nuevos cálculos sobre datos existentes | Hay cohorte de 60 TRAIN; separar media/SD entre semillas de bootstrap por paciente. P3-03 es referencia histórica. |
| ¿Cómo orientar el siguiente experimento? | Respondible parcialmente | Revisar FN/FP, extractor/cabeza y calidad; predefinir objetivo, población y recursos antes de ejecutar. |

Ninguna comparación acredita validación externa o superioridad clínica/estadística. No se entrenaron modelos ni se cambió el campeón activo.
