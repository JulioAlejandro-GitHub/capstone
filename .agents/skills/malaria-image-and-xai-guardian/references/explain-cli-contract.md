# Contrato CLI EXPLAIN
**Estado:** inventario de parámetros acordado; defaults, obligatoriedad y exclusiones requieren auditoría de código.
**Fuente de verdad:** parser CLI de `src.explain`, wrappers `run_*`, tests correspondientes (localizar rutas exactas).

| Parámetro | Semántica | Verificación pendiente |
|---|---|---|
| `--method` | Método XAI | Opciones, default |
| `--layer` | Capa para método compatible | Compatibilidad, default |
| `--class-id` | Clase objetivo | Dominio y default |
| `--num-samples` | Cantidad de muestras | Rango y precedencia |
| `--max-images` | Límite de imágenes | Rango y exclusión con sample-id |
| `--sample-id` | Muestra a explicar | Exclusión con max-images |
| `--background-sample-id` | Referencia para SHAP | Obligatoriedad o selección automática |

**Regla de cambio:** verificar implementación actual; actualizar contrato y pruebas en conjunto. No declarar que `--sample-id` y `--max-images` son mutuamente excluyentes sin evidencia del parser y tests.
**Fecha de revisión documental:** 2026-10-16.
