# Selección de muestras EXPLAIN
**Acordado para evaluar:** si SHAP no recibe `background_sample_id`, seleccionar una muestra elegible de VALIDATION en orden determinista; persistir el ID efectivo. No asumir que está implementado.
**Identidades:** `sample_id` = imagen explicada; `background_sample_id` = referencia de SHAP.
**Por verificar:** reglas SQL de elegibilidad, criterio ORDER BY estable, obligatoriedad CLI, exclusión `--sample-id`/`--max-images`, tests y persistencia.
**No usar TEST como origen de entrenamiento o VALIDATION.**
**Fecha:** 2026-10-16.
