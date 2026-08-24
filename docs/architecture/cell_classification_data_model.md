# Modelo de datos de clasificación celular

La cadena lineal de Prompt 8 es:

1. `20260728_01`: introduce las entidades de clasificación, explicabilidad,
   agregado y revisión;
2. `20260728_02`: vuelve a declarar la validación de integridad del agregado
   para bases que alcanzaron la primera revisión durante el desarrollo;
3. `20260728_03`: alinea esa validación con el contrato canónico final de
   `per_image_summary`.

Por tanto, el contrato de Prompt 8 quedó completo por primera vez en
`20260728_03`; no basta con aplicar solamente `20260728_01`. Esa revisión es un
mínimo histórico, no el head operativo vigente. El head versionado actual es
`20260812_02` y operación debe comprobar siempre `current=head`.

La revisión base introduce:

| Tabla | Responsabilidad |
|---|---|
| `cell_classification_runs` | identidad, slot productivo, snapshots, estado y contadores |
| `cell_classification_inputs` | manifest tabular congelado, elegibilidad y exclusión |
| `cell_predictions` | resultado automático inmutable por crop |
| `cell_explanations` | lifecycle y metadata de artefactos Grad-CAM |
| `smear_analysis_summaries` | agregado automático inmutable por run |
| `cell_classification_events` | eventos append-only |
| `cell_classification_reviews` | decisiones humanas append-only |

La antigua vista `cell_predictions` pasa a llamarse
`legacy_cell_predictions`; la tabla legacy `predictions` no cambia.

Todas las relaciones científicas y de gobierno usan `ON DELETE RESTRICT`. Los
JSON snapshots deben ser objetos; SHA-256 usa 64 caracteres hexadecimales; los
contadores, probabilidades y dimensiones tienen checks. Triggers impiden
mutaciones de predicciones, inputs, summaries, eventos y reviews, protegen la
identidad del run y limitan transiciones de explicación.

`cell_predictions` conserva:

- `probability_parasitized` y `probability_uninfected`, con suma tolerada;
- label e índice canónicos;
- positive label/index;
- threshold y su fuente;
- margen y flag near-threshold;
- raw output y preprocessing snapshot;
- duración o error técnico.

El resumen revisado no es otra escritura: se calcula desde las últimas
revisiones efectivas de detección y clasificación.

## Contrato del resumen

`smear_analysis_summaries` conserva únicamente el resumen automático inmutable.
El trigger final de `20260728_03` verifica sus IDs de lineage, conteos,
probabilidades, outcome, policy y el desglose:

```json
{
  "images": [
    {
      "microscopy_image_id": "uuid",
      "image_sequence_number": 1,
      "eligible_cell_count": 0,
      "classified_cell_count": 0,
      "parasitized_candidate_count": 0,
      "uninfected_candidate_count": 0,
      "near_threshold_count": 0,
      "failed_prediction_count": 0
    }
  ]
}
```

El endpoint de summary devuelve un objeto con dos miembros:
`automatic_summary`, que representa esa fila persistida, y
`reviewed_summary`, una proyección derivada en lectura. La proyección revisada
no modifica la predicción automática, sus probabilidades ni el resumen
almacenado.
