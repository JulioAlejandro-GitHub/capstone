# Compatibilidad futura con RBCNet

> **Estado documental:** `OBSOLETE_DOC` — sustituido parcialmente por la implementación.
> **Uso operativo:** No; conserva restricciones históricas de compatibilidad futura.
> **Sustitución:** ADR-019, `cell_detection_pipeline.md` y `cell_detection_data_model.md`.

RBCNet es horizonte conceptual; Prompt 4 no descarga ni ejecuta MATLAB, modelos,
segmentación, detección, crops o clasificación. La identidad de todo resultado
futuro es `microscopy_images.id`.

Pipeline previsto: original → segmentación → componentes conectados → detección
→ boxes → crops → clasificación → agregación por imagen/muestra → revisión.

Coordenadas: `coordinate_space=original_image_pixels`,
`coordinate_origin=top_left`, `bounding_box_format=xywh`. Todo reescalado deberá
guardar su transformación inversa.

Contratos futuros:

- `analysis_runs`: imagen, estados queued…completed/failed, versiones, tiempos y error.
- `image_connected_components`: índice, box, área, máscara/crop y estado.
- `cell_detections`: componente, índice, xywh, score, label, estado y versión.
- `cell_crops`: detección, claves relativas, checksum, MIME, dimensiones y padding.
- `scientific_reviews`: detección, revisor, estado, comentario y tiempos.

La revisión (`pending_review`, `accepted`, `corrected`, `excluded`,
`needs_attention`) nunca borra el resultado original. El visor futuro resolverá
boxes, detecciones, crops, resultados, comentarios y relación sujeto/muestra.
Artefactos futuros (máscaras, crops, manifests, overlays y resumen) almacenarán
binarios fuera de PostgreSQL y referenciarán imagen, corrida, detección, tipo,
checksum y versión.
