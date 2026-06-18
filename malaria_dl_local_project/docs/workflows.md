# Workflows del Proyecto

Este proyecto separa tres flujos operativos:

1. Entrenamiento
2. Evaluación experimental
3. Inferencia clínica experimental sobre imagen externa

## 1. Entrenamiento

Responsabilidad: entrenar modelos con el dataset `malaria` de TensorFlow Datasets.

Archivos principales:

- `src/train.py`
- `src/data.py`
- `src/models.py`

Comandos:

```bash
python -m src.train --model custom_cnn --epochs 30 --img-size 200 --batch-size 64 --track-db

python -m src.train --model vgg16 --epochs 30 --fine-tune-epochs 10 --img-size 200 --batch-size 64 --track-db
```

Salidas esperadas:

```text
outputs/custom_cnn/
outputs/vgg16/
best_model.keras
final_model.keras
training_log.csv
training_base_log.csv
fine_tuning_log.csv
checkpoint_selection.json
test_metrics.json
test_predictions.csv
test_confusion_matrix.csv
```

### Selección Del Mejor Checkpoint

`best_model.keras` se guarda con `ModelCheckpoint` usando una métrica configurable. El valor por defecto es clínico:

```text
--checkpoint-metric val_recall_parasitized
```

Esto representa sensibilidad/recall de la clase `parasitized`, tratada como clase positiva clínica. También se puede seleccionar:

- `val_auc`
- `val_recall`
- `val_accuracy`
- `val_loss`
- `val_recall_parasitized`

Importante: `val_recall` es la métrica Keras estándar sobre la clase índice 1 (`uninfected`) en este proyecto. Para criterio clínico sobre malaria usa `val_recall_parasitized`.

Ejemplo:

```bash
python -m src.train \
  --model vgg16 \
  --epochs 30 \
  --fine-tune-epochs 10 \
  --img-size 200 \
  --batch-size 64 \
  --checkpoint-metric val_recall_parasitized \
  --track-db
```

El modo de comparación se resuelve automáticamente: `min` para `val_loss`, `max` para el resto. El criterio usado se guarda en:

```text
outputs/<model>/checkpoint_selection.json
```

Además, el entrenamiento base y el fine-tuning tienen logs separados:

```text
training_base_log.csv
fine_tuning_log.csv
```

`training_log.csv` se mantiene como alias histórico del entrenamiento base.

## 2. Evaluación Experimental

Responsabilidad: evaluar modelos ya entrenados sobre el test set y generar métricas, explicabilidad, TTA o ensemble experimental.

Archivos principales:

- `src/evaluate.py`
- `src/metrics.py`
- `src/explain.py`
- `src/tta.py`
- `src/ensemble.py`
- `src/svm_features.py`

Comandos:

```bash
python -m src.evaluate --checkpoint outputs/vgg16/best_model.keras --img-size 200 --batch-size 64 --track-db

python -m src.explain --checkpoint outputs/vgg16/best_model.keras --method all --num-samples 50 --positive-label parasitized --track-db

python -m src.tta --checkpoint outputs/vgg16/best_model.keras --n-aug 8 --track-db

python -m src.ensemble \
  --models outputs/custom_cnn/best_model.keras outputs/vgg16/best_model.keras \
  --weights 0.4 0.6 \
  --track-db
```

Salidas esperadas:

```text
outputs/vgg16/evaluation/
outputs/custom_cnn/evaluation/
outputs/ensemble/
outputs/explainability/
```

Métricas clínicas:

Los reportes experimentales calculan las métricas principales usando `parasitized`
como clase positiva clínica. En los CSV se mantienen columnas históricas por
compatibilidad, pero quedan diferenciadas:

- `raw_model_score`: salida cruda del modelo sigmoid, asociada a la clase índice 1 de TFDS.
- `probability_uninfected`: probabilidad de `uninfected`.
- `probability_parasitized`: probabilidad clínica positiva.
- `y_score`: alias compatible de `raw_model_score`.
- `y_pred`: clase predicha con `probability_parasitized >= threshold`.

Los JSON de métricas incluyen:

- `sensitivity_parasitized`
- `recall_parasitized`
- `specificity`
- `false_negative_rate`
- `false_positive_rate`
- `balanced_accuracy`
- `auc_parasitized`

El umbral clínico se puede ajustar en evaluación, ensemble, TTA y SVM:

```bash
python -m src.evaluate \
  --checkpoint outputs/vgg16/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --threshold 0.5 \
  --track-db
```

## Preprocesamiento Por Arquitectura

El preprocesamiento está centralizado en `src/preprocessing.py` y se pasa de forma explícita con `--preprocessing` en entrenamiento, evaluación, explicabilidad, TTA, ensemble, SVM e inferencia individual.

Modos disponibles:

- `auto`: modo por defecto. Resuelve a `rescale_0_1` para mantener compatibilidad con checkpoints ya entrenados.
- `rescale_0_1`: resize + `float32` + normalización `[0, 1]`. Es el modo esperado para `custom_cnn` y para los checkpoints históricos del proyecto.
- `vgg16_imagenet`: resize + `float32` + `tf.keras.applications.vgg16.preprocess_input`. Debe usarse solo con modelos VGG16 entrenados con ese mismo modo.

Impacto operativo:

- No se debe evaluar un checkpoint entrenado con `[0,1]` usando `vgg16_imagenet`, porque cambia la distribución de entrada.
- No se debe evaluar un checkpoint entrenado con `vgg16_imagenet` usando `[0,1]`.
- Para probar VGG16 con preprocesamiento ImageNet, reentrena y guarda el modelo en una carpeta separada para no sobrescribir `outputs/vgg16/`.
- `src.ensemble` aplica un único modo a todos los modelos. No mezcles en el mismo ensemble checkpoints entrenados con modos distintos.
- Los JSON de métricas y CSV de predicciones incluyen `preprocessing_mode` cuando se generan desde estos scripts.

Ejemplo conservador para checkpoints existentes:

```bash
python -m src.evaluate \
  --checkpoint outputs/vgg16/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --preprocessing rescale_0_1
```

Ejemplo para nuevo VGG16 reentrenado con preprocesamiento ImageNet:

```bash
python -m src.train \
  --model vgg16 \
  --epochs 30 \
  --fine-tune-epochs 10 \
  --img-size 200 \
  --batch-size 64 \
  --preprocessing vgg16_imagenet \
  --output-dir outputs/vgg16_imagenet \
  --track-db
```

Luego usa el mismo modo en todos los pasos posteriores:

```bash
python -m src.evaluate \
  --checkpoint outputs/vgg16_imagenet/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --preprocessing vgg16_imagenet \
  --track-db

python -m src.explain \
  --checkpoint outputs/vgg16_imagenet/best_model.keras \
  --method all \
  --num-samples 50 \
  --positive-label parasitized \
  --preprocessing vgg16_imagenet \
  --track-db

python -m src.predict_image \
  --checkpoint outputs/vgg16_imagenet/best_model.keras \
  --image-path ruta/a/imagen.png \
  --img-size 200 \
  --positive-label parasitized \
  --threshold 0.5 \
  --preprocessing vgg16_imagenet
```

## 3. Inferencia Clínica Experimental

Responsabilidad: procesar una imagen externa individual y devolver una respuesta estructurada, trazable y explicable.

Archivo principal:

- `src/predict_image.py`

Archivos de apoyo:

- `src/decision.py`
- `src/image_quality.py`
- `src/inference_pipeline.py`
- `src/calibration.py`
- `src/prediction_uploads.py`
- `src/run_tracker.py`
- `src/tracking_integration.py`
- `src/explain.py`

Flujo:

```text
Imagen nueva
   ↓
control de calidad de imagen
   ↓
preprocesamiento por arquitectura
   ↓
modelo base
   ↓
TTA opcional
   ↓
ensemble opcional
   ↓
calibración de probabilidad
   ↓
decisión según umbral clínico
   ↓
Grad-CAM / LIME / SHAP
   ↓
respuesta estructurada
   ↓
registro en PostgreSQL
   ↓
visualización en frontend
```

La clase clínica positiva es `parasitized`. La salida incluye explícitamente:

- `probability_parasitized`
- `probability_uninfected`
- `confidence_level`
- `decision`
- `human_readable_response`

No se usa lenguaje de diagnóstico definitivo. La respuesta incluye el disclaimer:

```text
Resultado experimental de apoyo. No corresponde a diagnóstico clínico definitivo.
```

### Inferencia Simple

```bash
python -m src.predict_image \
  --checkpoint outputs/vgg16/best_model.keras \
  --image-path ruta/a/imagen.png \
  --img-size 200 \
  --positive-label parasitized \
  --threshold 0.5
```

### Inferencia con Grad-CAM

```bash
python -m src.predict_image \
  --checkpoint outputs/vgg16/best_model.keras \
  --image-path ruta/a/imagen.png \
  --img-size 200 \
  --positive-label parasitized \
  --threshold 0.5 \
  --explain gradcam
```

### Inferencia con TTA

```bash
python -m src.predict_image \
  --checkpoint outputs/vgg16/best_model.keras \
  --image-path ruta/a/imagen.png \
  --img-size 200 \
  --positive-label parasitized \
  --threshold 0.5 \
  --tta \
  --n-aug 8
```

### Inferencia con Ensemble

```bash
python -m src.predict_image \
  --ensemble \
  --models outputs/custom_cnn/best_model.keras outputs/vgg16/best_model.keras \
  --weights 0.4 0.6 \
  --image-path ruta/a/imagen.png \
  --img-size 200 \
  --positive-label parasitized \
  --threshold 0.5
```

Para explicar un ensemble se debe indicar un modelo Keras concreto:

```bash
python -m src.predict_image \
  --ensemble \
  --models outputs/custom_cnn/best_model.keras outputs/vgg16/best_model.keras \
  --weights 0.4 0.6 \
  --explain-model outputs/vgg16/best_model.keras \
  --image-path ruta/a/imagen.png \
  --positive-label parasitized \
  --explain gradcam
```

### Inferencia con Calibración

Sin parámetros calibrados, el método por defecto es `none`.

```bash
python -m src.predict_image \
  --checkpoint outputs/vgg16/best_model.keras \
  --image-path ruta/a/imagen.png \
  --positive-label parasitized \
  --calibration-method none
```

Temperature scaling requiere informar una temperatura:

```bash
python -m src.predict_image \
  --checkpoint outputs/vgg16/best_model.keras \
  --image-path ruta/a/imagen.png \
  --positive-label parasitized \
  --calibration-method temperature_scaling \
  --calibration-temperature 1.5
```

### Inferencia con Tracking en PostgreSQL

```bash
python -m src.predict_image \
  --checkpoint outputs/vgg16/best_model.keras \
  --image-path ruta/a/imagen.png \
  --img-size 200 \
  --positive-label parasitized \
  --threshold 0.5 \
  --explain gradcam \
  --track-db \
  --output-json outputs/predictions/prediction_result.json
```

Con `--track-db`, la imagen se copia y renombra en:

```text
capstone/data/prediction_uploads/
```

Ejemplo de nombre:

```text
data/prediction_uploads/20260618_153012_a8f23c_imagen.png
```

Las imágenes subidas quedan ignoradas por Git. Solo se versiona `data/prediction_uploads/.gitkeep`.

### Salidas de Inferencia Externa

```text
outputs/predictions/external_predictions.csv
outputs/predictions/prediction_result.json
outputs/explainability/external_predictions/gradcam/
outputs/explainability/external_predictions/lime/
outputs/explainability/external_predictions/shap/
```

### Consulta SQL

Después de aplicar las migraciones:

```sql
SELECT
    image_id,
    image_stored_path,
    predicted_label,
    probability_parasitized,
    confidence_level,
    created_at
FROM vw_clinical_inference_predictions
ORDER BY created_at DESC;
```

## Aplicar Cambios de Base de Datos

Desde `capstone/malaria_dl_local_project`:

```bash
source .venv/bin/activate
python scripts/init_db.py
```

El script ejecuta los archivos `db/init/*.sql`, incluido `010_clinical_inference_tracking.sql`, de forma incremental mediante `CREATE IF NOT EXISTS` y `CREATE OR REPLACE VIEW`.
