# Ejemplos de visualización de modelos entrenados

Maquetas **aisladas** de XAI para comprender la arquitectura de los modelos del Capstone.
No están conectadas a la vista operativa (`frontend/`), a la API ni a la base de datos.

| Archivo | Qué muestra | Datos |
|---|---|---|
| `vgg16_arquitectura.html` | Flujo de tensores de VGG16 en vista isométrica, panel de detalle por capa, tabla equivalente y chequeos de coherencia automáticos | Constante `capasVGG16` copiada sin cambios desde `ej copy 4.html` |

Se abre con doble clic. No necesita servidor ni conexión: HTML + CSS + JS en un solo archivo, sin librerías externas.

## Hallazgos de la maqueta sobre `capasVGG16`

Los calcula la propia página a partir de los datos:

1. **Entrada 224 → Bloque 1 100**: con un MaxPool 2×2 debería dar 112. El resumen real (`docs/model_summaries/vgg16_summary.txt`) usa una entrada de **200×200×3**.
2. **«Dense 1 (Flatten)» = 512**: un Flatten de 6×6×512 daría 18.432. Que sean 512 coincide con el **GlobalAveragePooling2D** del modelo real, que además no tiene parámetros.
3. El tooltip de `ej copy 4.html` tenía valores fijos (`200×200×3 → 100×100×64`) para todas las capas. Aquí la entrada y la salida se calculan para cada capa.

## Próximo paso para conectarla a datos reales

Generar `capasVGG16` desde `model.summary()` o desde el `run_repository` (input_shape, output_shape, num_parameters, entrenable) en vez de mantener la constante a mano.
