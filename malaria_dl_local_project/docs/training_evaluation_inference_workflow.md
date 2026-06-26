# Workflow Integrado de Entrenamiento, Evaluación e Inferencia

Este flujo integra métricas clínicas, política de checkpoint, calibración de threshold y tracking PostgreSQL.

Convención obligatoria:

```text
0 = uninfected
1 = parasitized
raw_model_score = probability_parasitized
```

La decisión binaria siempre aplica el threshold sobre `probability_parasitized`:

```text
probability_parasitized >= threshold -> parasitized
probability_parasitized < threshold  -> uninfected
```

## 1. Crear Split Físico

```bash
python scripts/create_physical_dataset_split.py --seed 42
```

Opcionalmente registrar el split físico en PostgreSQL:

```bash
python scripts/register_physical_split_in_db.py \
  --dataset-dir data/malaria_physical_split \
  --dataset-name malaria_physical_split \
  --dataset-source tensorflow_datasets/malaria \
  --execute
```

## 2. Entrenar Con Política Clínica

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

El entrenamiento guarda:

```text
outputs/<model_name>/best_model.keras
outputs/<model_name>/final_model.keras
outputs/<model_name>/training_log.csv
outputs/<model_name>/test_metrics.json
outputs/<model_name>/test_predictions.csv
outputs/<model_name>/test_confusion_matrix.csv
outputs/<model_name>/checkpoint_policy_summary.json
outputs/<model_name>/threshold_calibration.json
outputs/<model_name>/model_metadata.json
```

Si `--calibrate-threshold` está activo, el threshold se calibra solo con validation. Test se usa después para evaluación final.

## 3. Evaluar Con Threshold Clínico

```bash
python -m src.evaluate \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --threshold clinical \
  --track-db
```

`--threshold clinical` lee `clinical_threshold.threshold_selected` desde `model_metadata.json`. Si no existe, el comando falla con:

```text
No clinical threshold found in model metadata. Run calibration first or use --threshold 0.5.
```

Para compatibilidad, el threshold numérico sigue funcionando:

```bash
python -m src.evaluate \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --threshold 0.5
```

## 4. Inferir Una Imagen

```bash
python -m src.predict_image \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --image-path path/to/image.png \
  --threshold clinical \
  --explain gradcam \
  --track-db
```

La salida incluye `raw_model_score`, `probability_parasitized`, `probability_uninfected`, `threshold_used`, `threshold_source`, `target_recall`, `expected_specificity`, `clinical_threshold` y la advertencia experimental.

## 5. TTA, Ensemble, SVM y Explicabilidad

TTA promedia `probability_parasitized` y recién después aplica threshold:

```bash
python -m src.tta \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --threshold clinical
```

Ensemble combina probabilidades y recién después aplica threshold. Para `clinical` requiere metadata calibrada del ensemble:

```bash
python -m src.ensemble \
  --models outputs/custom_cnn/best_model.keras outputs/vgg16/best_model.keras \
  --threshold 0.5
```

SVM usa `svm.predict_proba(X)[:, index_of_class_1]` como `probability_parasitized`. `--threshold clinical` requiere metadata calibrada del SVM.

Explicabilidad calcula `case_type` con el threshold resuelto y guarda `threshold_used` y `threshold_source` en `explanation_summary.csv`:

```bash
python -m src.explain \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --method gradcam \
  --threshold clinical \
  --track-db
```

## 6. Tracking PostgreSQL

Con `--track-db`, los flujos registran en JSONB:

```text
checkpoint_policy
checkpoint_policy_config
checkpoint_selection
clinical_threshold
threshold_used
threshold_source
target_recall
target_recall_satisfied
expected_specificity
f2_parasitized
pr_auc_parasitized
recall_parasitized
specificity
balanced_accuracy
prediction_collapse_detected
```

No se requiere migración para estas claves mientras se usen los campos JSONB existentes.
