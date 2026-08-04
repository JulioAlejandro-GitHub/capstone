# Pipeline de IA y linaje científico

El producto separa el ciclo experimental de modelos del análisis técnico de
frotis. Ambos comparten trazabilidad, pero publicar un modelo no ejecuta
inferencia y una inferencia nunca modifica el experimento que originó el
checkpoint.

## Ciclo experimental

1. **Dataset:** se registra procedencia y se materializa un split físico
   estratificado 80/10/10. La convención es `0 = uninfected` y
   `1 = parasitized`.
2. **TRAIN:** crea un run, congela configuración y produce artefactos con
   checksum y metadatos de preprocessing.
3. **EVALUATE:** usa el checkpoint del TRAIN mediante linaje explícito; genera
   métricas, predicciones y evidencia de calibración.
4. **EXPLAIN:** agrega explicabilidad experimental sin ser requisito para la
   elegibilidad de publicación de Etapa 2.
5. **Versión/publicación:** inventaría un artefacto inmutable y lo hace
   disponible mediante una acción explícita y auditable.

Detalles: [workflow ML](../malaria_dl_local_project/docs/training_evaluation_inference_workflow.md),
[split físico](../malaria_dl_local_project/docs/physical_dataset_split.md),
[política de checkpoints](../malaria_dl_local_project/docs/checkpoint_policy.md),
[métricas](../malaria_dl_local_project/docs/clinical_metrics.md),
[calibración](../malaria_dl_local_project/docs/threshold_calibration.md) y
[linaje de evaluación/explicabilidad](evaluation_and_explainability_lineage.md).

## Análisis técnico de frotis

```text
identidad pseudonimizada
  → lote e imágenes originales inmutables
  → quality gate técnico
  → run de análisis congelado
  → detección y crops
  → clasificación por publicación Stage 2 activa
  → Grad-CAM bajo demanda y revisión humana
  → resumen automático + resumen revisado
```

- La ingesta calcula identidad y checksum en backend, valida formato y límites,
  y guarda claves relativas; no confía en metadata técnica del navegador.
- El quality gate es técnico y terminal para imágenes no elegibles; no evalúa
  contenido clínico.
- Detección y clasificación son etapas separadas, con contratos y revisiones
  independientes.
- La clasificación congela modelo, mapping, preprocessing, threshold e inputs.
  No usa el modelo “más reciente” ni un threshold `0.5` implícito.
- Grad-CAM se genera por acción explícita y sus archivos se sirven sólo por
  endpoints autenticados.
- Los resultados automáticos son inmutables; las decisiones humanas se agregan
  como evidencia separada.

Fuentes vigentes: [ingesta](architecture/microscopy_image_ingestion.md),
[quality gate](architecture/microscopy_quality_gate.md),
[detección](architecture/cell_detection_pipeline.md),
[clasificación](architecture/cell_classification_pipeline.md),
[workspace de revisión](architecture/cell_review_workspace.md) y
[agregación](architecture/smear_analysis_aggregation.md).

## Límites científicos

El sistema sirve investigación y validación técnica. Accuracy, precision,
recall, F1, AUC, matrices de confusión, mapas de calor y recuentos celulares no
equivalen a una validación clínica. No se debe inferir diagnóstico, gravedad o
parasitemia fuera del alcance y dataset documentados. La compatibilidad futura
con RBCNet se mantiene como diseño explícito en
[`architecture/rbcnet_future_compatibility.md`](architecture/rbcnet_future_compatibility.md),
no como capacidad presente.
