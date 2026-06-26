# Política avanzada de checkpoint

La política por defecto del proyecto es `auc_with_min_recall`.

Esta política selecciona el checkpoint con mayor AUC entre los epochs que cumplen una sensibilidad mínima para la clase `parasitized`. Esto evita aceptar modelos con buen AUC global pero sensibilidad insuficiente, y también reduce el riesgo de seleccionar modelos degenerados que predicen todas las imágenes como `parasitized`.

Convención clínica obligatoria:

```text
0 = uninfected
1 = parasitized
raw_model_score = probability_parasitized
```

El threshold se aplica sobre `probability_parasitized`.

## Políticas disponibles

- `auc_with_min_recall`: selecciona el mayor `val_auc` entre epochs con `val_recall_parasitized >= min_recall`.
- `f2`: selecciona el mayor `val_f2_parasitized`.
- `balanced_accuracy`: selecciona el mayor `val_balanced_accuracy`.
- `val_auc`: mantiene compatibilidad con selección por `val_auc`.

No se usa `val_recall_parasitized` puro como default porque puede seleccionar modelos degenerados que predicen todo como positivo: recall 1.0, especificidad 0.0.

## Default clínico

```text
--checkpoint-policy auc_with_min_recall
--min-recall 0.98
--beta 2.0
--reject-prediction-collapse true
--min-class-fraction 0.05
```

Con `auc_with_min_recall`, los candidatos deben cumplir:

```text
val_recall_parasitized >= min_recall
```

Luego se selecciona el mayor `val_auc`. En empate, se prioriza:

```text
1. mayor val_f2_parasitized
2. mayor val_specificity
3. menor val_loss
```

Si ningún epoch cumple `min_recall`, el sistema selecciona un fallback por mayor `val_recall_parasitized` y marca:

```json
{
  "policy_satisfied": false,
  "warning": "No epoch reached min_recall. Selected fallback by best recall."
}
```

Ese checkpoint queda explícitamente marcado como no satisfactorio para la política clínica.

## Colapso de predicción

Cada epoch calcula métricas clínicas sobre validation y registra `val_prediction_collapse_detected`.

Si `--reject-prediction-collapse` está activo, los epochs colapsados se excluyen de la selección. Si todos los epochs están colapsados, se selecciona fallback pero se marca:

```json
{
  "all_epochs_collapsed": true,
  "warning": "All candidate epochs showed prediction collapse. Checkpoint is not clinically reliable."
}
```

Para permitirlo explícitamente:

```bash
python -m src.train \
  --model custom_cnn \
  --allow-collapsed-checkpoint
```

## Uso desde CLI

Default clínico:

```bash
python -m src.train \
  --model custom_cnn \
  --epochs 30 \
  --img-size 200 \
  --batch-size 64
```

F2:

```bash
python -m src.train \
  --model custom_cnn \
  --epochs 30 \
  --img-size 200 \
  --batch-size 64 \
  --checkpoint-policy f2 \
  --beta 2.0
```

VGG16 con política clínica:

```bash
python -m src.train \
  --model vgg16 \
  --epochs 30 \
  --fine-tune-epochs 10 \
  --img-size 200 \
  --batch-size 64 \
  --checkpoint-policy auc_with_min_recall \
  --min-recall 0.98
```

Compatibilidad por AUC:

```bash
python -m src.train \
  --model custom_cnn \
  --checkpoint-policy val_auc
```

`val_auc` no garantiza sensibilidad mínima; úsalo solo cuando esa restricción no sea parte del criterio del experimento.

## Artefactos

El entrenamiento guarda:

```text
outputs/<model>/best_model.keras
outputs/<model>/checkpoint_policy_summary.json
outputs/<model>/checkpoint_selection.json
outputs/<model>/model_metadata.json
outputs/<model>/training_log.csv
```

`checkpoint_policy_summary.json` contiene la política, configuración, epoch seleccionado, métricas seleccionadas, estado de `policy_satisfied`, diagnóstico de colapso y warning si existe.
