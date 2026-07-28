# Agregación experimental por frotis

## Outcomes

- `suspicious_cells_detected`: existe al menos una predicción automática válida
  clasificada como `parasitized`.
- `no_suspicious_cells_detected`: no hay candidatos `parasitized`, todos los
  elegibles fueron clasificados y la política no detecta fallos ni cercanía
  relevante al threshold.
- `inconclusive`: no hay elegibles, hay cobertura insuficiente, fallos
  relevantes o condiciones técnicas incompatibles.

Se conservan conteos elegibles, clasificados, por label, near-threshold y
fallidos, además de fracción de candidatos, máximo, media y mediana de
`probability_parasitized` y desglose por imagen.

La fracción usa como denominador solamente predicciones válidas:

```text
parasitized_candidate_count / classified_cell_count
```

No representa parasitemia, prevalencia ni probabilidad de enfermedad.

## Automático y revisado

El resumen automático es inmutable. El resumen revisado se calcula al consultar,
aplicando la última revisión efectiva sin alterar probabilidades, label
automático o summary almacenado. La UI muestra ambos con una separación
explícita y conserva los disclaimers científicos.

La respuesta de
`GET /api/v1/cell-classification/classification-runs/{id}/summary` tiene este
envelope estable:

```json
{
  "automatic_summary": {
    "per_image_summary": {
      "images": []
    }
  },
  "reviewed_summary": {
    "kind": "reviewed_projection",
    "automatic_summary_unchanged": true
  }
}
```

La forma `{"images": [...]}` de `per_image_summary`, los conteos, las
probabilidades agregadas, el outcome y el snapshot exacto
`cell-candidate-aggregation-v1` son validados al insertar por la revisión
Alembic `20260728_03`. Un valor que no coincide con las predicciones inmutables
es rechazado por PostgreSQL.
