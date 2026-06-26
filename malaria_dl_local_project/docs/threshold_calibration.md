# Calibración de Umbral Clínico

Este proyecto separa dos conceptos:

- `probability_parasitized`: score continuo producido por el modelo.
- `threshold`: umbral operativo usado para convertir el score en decisión binaria.

La convención clínica oficial es:

```text
0 = uninfected
1 = parasitized
raw_model_score = probability_parasitized
```

La decisión se toma siempre así:

```text
probability_parasitized >= threshold -> parasitized
probability_parasitized < threshold  -> uninfected
```

## Por Qué No Asumir 0.5

Un threshold de `0.5` no necesariamente entrega el mejor balance clínico. En malaria, el costo experimental relevante es reducir falsos negativos:

```text
real parasitized -> predicho uninfected
```

Bajar el threshold suele aumentar sensibilidad para `parasitized`, pero también puede aumentar falsos positivos. Por eso el threshold clínico se elige con validation y queda documentado junto al modelo.

## Selección

`find_threshold_for_target_recall` evalúa candidatos de threshold sobre el validation set y busca cumplir:

```text
recall_parasitized >= target_recall
```

Default recomendado:

```text
target_recall = 0.98
beta = 2.0
```

Entre thresholds que cumplen el target, selecciona por:

1. mayor `specificity`
2. mayor `precision_parasitized`
3. mayor `f2_parasitized`
4. mayor `balanced_accuracy`
5. threshold más alto

Si ningún threshold alcanza el target, se selecciona el de mayor recall posible y se guarda:

```json
{
  "target_recall_satisfied": false,
  "warning": "No threshold reached target_recall on validation set."
}
```

## Sin Leakage

La calibración usa exclusivamente el validation set. El test set no se permite para calibrar threshold:

```bash
python -m src.calibrate \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --dataset-split test
```

Ese comando falla con:

```text
No se permite calibrar threshold usando test set. Use validation set.
```

El test se usa después, una vez fijado el threshold, para estimar desempeño final.

## Calibrar Un Checkpoint

```bash
python -m src.calibrate \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --target-recall 0.98 \
  --dataset-split val \
  --output-json outputs/custom_cnn/threshold_calibration.json \
  --update-model-metadata \
  --track-db
```

El archivo default es:

```text
outputs/<model>/threshold_calibration.json
```

Si se usa `--update-model-metadata`, también se actualiza:

```text
outputs/<model>/model_metadata.json
```

con la clave:

```json
{
  "clinical_threshold": {
    "enabled": true,
    "threshold_source": "validation_calibration",
    "threshold_selected": 0.32,
    "target_recall": 0.98
  }
}
```

## Entrenar Y Calibrar

```bash
python -m src.train \
  --model custom_cnn \
  --epochs 30 \
  --img-size 200 \
  --batch-size 64 \
  --checkpoint-policy auc_with_min_recall \
  --min-recall 0.98 \
  --calibrate-threshold \
  --target-recall 0.98 \
  --track-db
```

Flujo:

1. Se entrena y se selecciona `best_model.keras`.
2. Se predice validation con el mejor checkpoint.
3. Se calibra el threshold clínico con validation.
4. Se guarda `threshold_calibration.json`.
5. Se escribe `clinical_threshold` en `model_metadata.json`.
6. Se evalúa test usando el threshold ya fijado.

## Usar Threshold Clínico

Evaluación:

```bash
python -m src.evaluate \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --threshold clinical
```

Inferencia individual:

```bash
python -m src.predict_image \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --image-path ruta/a/imagen.png \
  --threshold clinical
```

TTA y ensemble:

```bash
python -m src.tta \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --threshold clinical

python -m src.ensemble \
  --models outputs/custom_cnn/best_model.keras outputs/vgg16/best_model.keras \
  --threshold clinical
```

TTA promedia `probability_parasitized` antes de aplicar threshold. Ensemble combina `probability_parasitized` antes de aplicar threshold.

Si no existe threshold clínico en metadata, `--threshold clinical` falla con un error claro y se debe calibrar primero o usar un threshold numérico.

## Relación Con Temperature Scaling

`src.calibration.py` mantiene calibración probabilística por temperature scaling. Eso ajusta la interpretación del score continuo.

La calibración de este documento selecciona el umbral operativo para tomar una decisión binaria. No reemplaza métricas clínicas, política de checkpoint ni calibración probabilística existente.
