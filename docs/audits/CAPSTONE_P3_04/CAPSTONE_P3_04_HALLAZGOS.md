# CAPSTONE-P3-04 — Hallazgos y recomendaciones

Fecha: 16 de noviembre de 2026, America/Santiago. Datasource: `malaria`.

El UUID solicitado es un intento EVALUATE TEST, no un TRAIN. Su TRAIN asociado es `87b3eff7-e09a-41c8-945d-bf31b3541adb`. Las recomendaciones siguientes no se implementaron.

## Hallazgos priorizados

| ID | Prioridad | Evidencia y conclusión | Fuente | Recomendación |
|---|---|---|---|---|
| H01 | Alta | HECHO VERIFICADO: el filtro `model_type=classification` excluye del selector los tres modos BiomedCLIP, aunque tengan evaluaciones. | [Catálogo real](evidence/catalog_response.json); CatalogService.models | Revisar el contrato de admisión en una fase de implementación autorizada. |
| H02 | Alta | HECHO VERIFICADO: EXPLAIN `ceaa29af-cb60-4be2-8a67-01b9c9382cda` está verified y sus 5.386 archivos no se encuentran en las rutas comprobadas. | [Inventario físico](csv/artifact_inventory.csv); [intentos](evidence/assessments.json) | Separar disponibilidad actual de verificación histórica; investigar recuperación sin regenerar silenciosamente. |
| H03 | Alta | CÁLCULO REPRODUCIDO: principal TEST tiene sensibilidad 96,4313 %, 47 FN y 223 FP; no alcanza 98 %. | [Métricas](evidence/metric_reproduction.json) | Mostrar split, población, threshold y checkpoint; no trasladar cumplimiento VAL a TEST. |
| H04 | Media | CÁLCULO REPRODUCIDO: dos VGG tienen embeddings GAP idénticos, pero 48/68 errores exclusivos entre ellos. | [Features](evidence/vgg_embedding_identity.json); [errores](evidence/pairwise_errors.json) | Estudiar también representaciones de cabeza/logits; CKA de GAP no captura toda la adaptación. |
| H05 | Media | HECHO VERIFICADO: GET arquitectura ViT puede iniciar un proceso y guardar caché cuando falta estructura. | backend_api/app/services/vit_structure.py:37 | Separar consulta y generación en un cambio futuro; la auditoría evitó esta rama. |
| H06 | Media | HECHO VERIFICADO: checkpoint lógico E5 3bbb… y artifact genérico 5406… tienen IDs diferentes y el mismo archivo/hash. | [Sesiones](evidence/training_sessions.json); [checkpoint](evidence/checkpoint_zip_inspection.json) | Conservar namespaces y comprobar identidad por contenido; no forzar una FK inexistente. |
| H07 | Media | HECHO VERIFICADO: verify_rows amplía F1/BA/AUC/AP solo para TEST; los intentos VAL pueden carecer de esos campos. | malaria_dl_local_project/src/malaria_dl/assessment/contracts.py:203 | Mostrar ausencia explícita; no completar resultados históricos con otra evaluación. |
| H08 | Media | HECHO VERIFICADO: assessment_metrics proyecta population_hash=None; la lógica de highlights exige un hash no nulo. | [Respuesta clínica](evidence/report_metrics.json); ScientificReportService.read | Explicar por qué hay métricas disponibles sin destacados comparativos; estudiar el contrato en otra fase. |
| H09 | Media | HECHO VERIFICADO: el PNG overlay LIME/SHAP usa magnitud absoluta; el NPY y la vista canvas Superposición conservan el signo. | [Estadísticos XAI](csv/principal_xai_maps.csv); attribution_overlay | Distinguir el PNG persistido del canvas: este último sí usa rojo positivo y azul negativo para LIME/SHAP. |
| H10 | Baja | HECHO VERIFICADO: campo fine_tuning_start_epoch=13; primer evento de esa fase es época global 14. | [Épocas](csv/principal_epochs.csv); [RUN](evidence/runs.json) | Documentar la frontera/índice y usar los eventos al graficar. |
| H11 | Media | HECHO VERIFICADO: texto de REPRESENT describe GAP para todos; runtime OpenCLIP extrae encode_image_l2. No hay REPRESENT Torch persistido en esta captura. | scientific_representations.DEFINITIONS; assessment/openclip.py | Adaptar la definición a layer/framework antes de presentar resultados Torch. |
| H12 | Media | INTERPRETACIÓN CIENTÍFICA: los nueve XAI principales cubren tres células y no acreditan conceptos morfológicos ni validación clínica. | [Identidades](evidence/case_identities.json); [resultados](evidence/case_related_scores.json) | Evaluar fidelidad, estabilidad y ROI/conceptos con especialistas en estudios futuros. |
| H13 | Baja | HECHO VERIFICADO: ModelComparison usa los eventos de época correctos; P3-03 describió otra fuente en RunDetail. | [Curvas actuales](evidence/report_curves.json); informe P3-03 | Identificar vista y contrato antes de extrapolar el hallazgo histórico. |
| H14 | Media | HECHO VERIFICADO: tres recorridos principales guardados describen VAL, mientras el intento solicitado es TEST. | [Recorridos](evidence/saved_traces_summary.json) | Conservar intento y split al relacionar activaciones con errores. |

Las prioridades expresan riesgo de interpretación o reproducibilidad, no una incidencia clínica demostrada. No se infiere causa de desaparición de archivos ni responsabilidad de un actor. Los archivos y líneas exactas de funciones se localizan en el catálogo de fuentes.

## Contraste con P3-03

P3-03 registró 86 TRAIN, 2.425 épocas y 140 EVALUATE. Esta captura tiene los mismos TRAIN/épocas y 141 EVALUATE: un aumento temporal no es una contradicción. Sus cifras del campeón DenseNet no se transfieren al principal VGG16. El problema histórico de `training_history=0` no impide que ModelComparison lea `train_execution_records` correctamente.

## Estudios futuros propuestos

1. Medir fidelidad y estabilidad XAI con perturbaciones controladas y ROI de especialistas; comparar mapas firmados bajo el mismo target/checkpoint.
2. Preparar conceptos expertos para probes o TCAV: anillo, cromatina, tinción, fondo y negativos controlados. Son hipótesis de estudio, no conceptos ya validados.
3. Comparar GAP, cabeza y logits entre checkpoints y relacionarlos con errores y calidad de imagen.
4. Estimar incertidumbre mediante bootstrap por paciente y diferencias pareadas; separar esa variación de la variabilidad entre semillas.
5. Evaluar generalización externa y unidades clínicas de paciente/frotis; medir prevalencia y costos reales de FN/FP y revisión humana.
6. Analizar cohortes alineadas de optimizadores/semillas con los datos existentes antes de proponer nuevas campañas.

## Límites verificados

No se comprobó navegador, bundle servido, autenticación HTTP ni todas las variantes visuales. El replay usa servicios de lectura y fuentes del contenedor cotejadas por hash. No se ejecutó inferencia ni se generaron explicaciones, representaciones o recorridos.

Se comprobó existencia de 35.341 referencias; 43 artefactos relevantes tienen SHA concordante. Se verificaron aparte cuatro originales y se calcularon hashes de cuatro JSON auxiliares existentes. No se verificó SHA de todos los checkpoints globales. El inventario de funciones es estático y amplio: llamadas textuales y pruebas nominales no certifican ejecución de cada función.

No se acreditan validación clínica externa, ROI morfológicas ni sensibilidad por paciente/frotis desde las tasas celulares. Las capacidades del motor BiomedCLIP y su exclusión de la página se documentan por separado.

**No se implementaron modificaciones funcionales, de esquema, registros, umbrales ni modelo activo.**
