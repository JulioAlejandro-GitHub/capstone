# Revisiones de clasificación

La predicción automática es inmutable. `cell_classification_reviews` guarda una
historia append-only distinta de `scientific_reviews`, que revisa la región
detectada.

| Decisión | Regla |
|---|---|
| `confirmed` | label opcional; no cambia la predicción |
| `corrected` | label canónico y comentario obligatorios |
| `needs_attention` | comentario obligatorio |
| `comment_only` | comentario obligatorio y sin cambio efectivo |

La última fila que no sea `comment_only`, ordenada por `created_at,id`, determina
el estado humano mostrado. El resumen revisado aplica ese label sólo como vista
derivada.

La auditoría registra decisión, IDs, presencia y longitud del comentario, pero
no el texto libre. El comentario completo permanece en la tabla científica.
UPDATE y DELETE son rechazados por trigger.
