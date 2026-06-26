# Métricas clínicas

En este proyecto, la clase positiva clínica es `parasitized`.

Convención oficial:

```text
0 = uninfected
1 = parasitized
raw_model_score = probability_parasitized
```

La decisión binaria aplica siempre el umbral sobre `probability_parasitized`:

```text
probability_parasitized >= threshold -> parasitized
probability_parasitized < threshold  -> uninfected
```

El threshold operativo puede calibrarse con validation set para alcanzar sensibilidad mínima de `parasitized`; ver `docs/threshold_calibration.md`. No se calibra con test.

## Falsos negativos

En imágenes microscópicas de malaria, el error clínicamente más sensible es:

```text
real parasitized -> predicho uninfected
```

Ese caso es un falso negativo. Por eso los reportes priorizan `recall_parasitized` o `sensitivity_parasitized`, que miden cuántas células realmente parasitadas fueron detectadas como `parasitized`.

## Métricas reportadas

Todos los flujos de evaluación usan `compute_clinical_metrics` y reportan:

- `accuracy`
- `precision_parasitized`
- `recall_parasitized`
- `sensitivity_parasitized`
- `specificity`
- `f1_parasitized`
- `f2_parasitized`
- `roc_auc_parasitized`
- `pr_auc_parasitized`
- `balanced_accuracy`
- `confusion_matrix`
- `classification_report`
- `prediction_distribution`
- `prediction_collapse`

## F2-score

`f2_parasitized` se calcula con `sklearn.metrics.fbeta_score`, `beta=2.0` y `pos_label=1`.

F2 pondera más el recall que la precisión. Esto es útil cuando los falsos negativos son más graves que los falsos positivos, porque penaliza más perder casos `parasitized`.

## PR-AUC

`pr_auc_parasitized` se calcula con `average_precision_score(y_true, probability_parasitized)`.

PR-AUC complementa ROC-AUC porque resume la relación entre precisión y recall de la clase positiva. Es especialmente útil cuando importa la calidad de detección de `parasitized` y no solo la separación global entre clases.

## Especificidad

`specificity` mide:

```text
TN / (TN + FP)
```

Representa cuántas células realmente `uninfected` fueron correctamente clasificadas como `uninfected`. Se reporta junto a sensibilidad para detectar modelos que ganan recall prediciendo demasiados casos como `parasitized`.

## Matriz de confusión

La matriz usa siempre `labels=[0, 1]`:

```text
                  Pred uninfected     Pred parasitized
Real uninfected        TN                  FP
Real parasitized       FN                  TP
```

El formato guardado es:

```text
[[TN, FP],
 [FN, TP]]
```

## Colapso de predicción

`prediction_collapse` diagnostica modelos que predicen una sola clase o casi una sola clase. Por ejemplo, un modelo que predice todo como `parasitized` puede tener sensibilidad 1.0, pero especificidad 0.0 y balanced accuracy 0.5.

Durante entrenamiento, la política de checkpoint usa este diagnóstico para excluir epochs colapsados cuando `--reject-prediction-collapse` está activo.

Los flujos `evaluate`, `predict_image`, `tta`, `ensemble`, `svm_features` y `explain` reportan el threshold realmente usado con:

```text
threshold_used
threshold_source
threshold_mode
```

`threshold_source = fixed_cli` indica un umbral numérico de CLI. `threshold_source = validation_calibration` indica un threshold clínico leído desde `model_metadata.json`.

Más detalle:

```text
docs/checkpoint_policy.md
docs/training_evaluation_inference_workflow.md
```
