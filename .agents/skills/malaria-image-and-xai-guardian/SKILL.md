---
name: malaria-image-and-xai-guardian
description: Preservar identidad de muestras linaje y artefactos en EXPLAIN Grad-CAM LIME SHAP y análisis de imágenes.
---

# malaria-image-and-xai-guardian

## Reglas invariantes
- Distinguir `training_run_id`, `assessment_identity_id`, `attempt_id`, `sample_id`, `background_sample_id` y `artifact_id`; nunca intercambiarlos.
- `sample_id` es la muestra explicada; `background_sample_id` es referencia de SHAP y no debe reemplazarla.
- Binarios de imágenes, crops, heatmaps y overlays fuera de PostgreSQL; metadatos y referencias dentro.
- Preservar checkpoint, TRAIN, muestra, método, intento y artefacto. Nunca sobrescribir ejecuciones anteriores.
- Recuperar artefactos mediante mecanismo HTTP autenticado existente; verificar autorización, pertenencia e integridad.
- No inferir diagnóstico clínico ni consenso científico a partir de imágenes XAI.
- Antes de modificar CLI/frontend/ejecución consultar `references/explain-cli-contract.md` y `references/explain-sample-selection.md`.
- **Acordado no significa verificado:** contrastar cada regla con código, BD y pruebas.

## Navegación
- `references/explain-cli-contract.md`: parámetros y compatibilidad.
- `references/explain-sample-selection.md`: muestras, background y determinismo.
- `references/xai-scientific-lineage.md`: linaje y persistencia.
- `references/xai-http-sql-operations.md`: recuperación y reutilización.
- `references/xai-assessment-artifacts.md`: estados, UI y evidencia.
- `references/legacy-original.md`: fuente histórica completa.
