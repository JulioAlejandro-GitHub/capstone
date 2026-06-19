# Workflows del Proyecto

Este proyecto separa tres flujos operativos:

1. Entrenamiento
2. Evaluación experimental
3. Inferencia clínica experimental sobre imagen externa

## 0. Documentación Metodológica y Limitaciones

Esta sección resume las decisiones metodológicas que deben explicarse en una defensa académica o revisión técnica. El objetivo del proyecto es construir un pipeline experimental reproducible para clasificación de células sanguíneas en imágenes microscópicas, no entregar un diagnóstico médico definitivo.

### Dataset

El proyecto usa el dataset `malaria` de TensorFlow Datasets, correspondiente al conjunto NIH / NLM Malaria Cell Images.

Ruta local esperada:

```text
capstone/data/tensorflow_datasets/
```

Desde `capstone/malaria_dl_local_project`, el código lo resuelve con `src.data.get_tfds_data_dir()`:

- Si existe `TFDS_DATA_DIR`, usa esa ruta.
- Si no existe, usa `capstone/data/tensorflow_datasets`.

La descarga local se realiza con:

```bash
python scripts/download_malaria_dataset.py
```

El dataset no se versiona en Git. No se suben imágenes, shards de TFDS ni TFRecords al repositorio.

### Split Actual

TensorFlow Datasets entrega `malaria` como un único split llamado `train`. Este proyecto lo divide de forma determinística por slicing de TFDS:

```python
split=["train[:80%]", "train[80%:90%]", "train[90%:]"]
```

Interpretación operativa:

- `train[:80%]`: entrenamiento.
- `train[80%:90%]`: validación.
- `train[90%:]`: test.

La validación se usa para callbacks, selección de checkpoint y calibración. El test se reserva para evaluación experimental final.

### Limitación: No Hay Patient-Level Split

El split actual es por porcentaje del dataset expuesto por TFDS. No garantiza separación por paciente.

Limitación principal:

- Si imágenes de un mismo paciente quedaran distribuidas entre entrenamiento, validación y test, podría existir fuga de información a nivel paciente.
- Esa fuga puede inflar métricas como accuracy, AUC o recall porque el modelo podría beneficiarse de patrones visuales asociados al mismo origen de muestra.

Implicancia para Capstone:

- Los resultados deben presentarse como evaluación experimental sobre el split disponible en TFDS.
- No deben presentarse como estimación clínica definitiva de desempeño en pacientes independientes.
- Una versión más rigurosa debería reconstruir el dataset desde la fuente NIH/NLM original, conservar `Patient-ID` si está disponible y crear splits por paciente o por lámina.

### Clase Positiva Clínica

La clase positiva clínica del proyecto es:

```text
parasitized
```

El orden interno de clases es:

```python
CLASS_NAMES = ["parasitized", "uninfected"]
```

Por consistencia clínica, los reportes distinguen:

- `raw_model_score`: salida cruda del modelo.
- `probability_uninfected`: probabilidad asociada a `uninfected`.
- `probability_parasitized`: probabilidad clínica positiva.

Las métricas clínicas se calculan usando `probability_parasitized`, no asumiendo ciegamente que la salida sigmoid representa la clase positiva clínica.

Métricas clínicas principales:

- Sensibilidad / recall de `parasitized`.
- Especificidad.
- False negative rate.
- False positive rate.
- Balanced accuracy.
- AUC de `parasitized`.

Esta decisión es importante porque, en malaria, un falso negativo tiene mayor criticidad experimental que un falso positivo: representa una célula parasitada que el modelo no detecta.

### Umbral de Decisión

El umbral por defecto es:

```text
threshold = 0.5
```

La regla usada en evaluación e inferencia es:

```text
probability_parasitized >= threshold -> parasitized
probability_parasitized < threshold  -> uninfected
```

El umbral es configurable con `--threshold`. Cambiarlo modifica la sensibilidad y especificidad:

- Un umbral menor tiende a aumentar sensibilidad y reducir falsos negativos, pero puede aumentar falsos positivos.
- Un umbral mayor tiende a aumentar especificidad y reducir falsos positivos, pero puede aumentar falsos negativos.

El umbral actual debe interpretarse como criterio experimental inicial. Para uso clínico real se requeriría selección de umbral basada en validación clínica, análisis de costos de error y revisión experta.

### Calibración

La calibración se implementa con temperature scaling usando el validation set. El flujo recomendado es:

```bash
python -m src.calibrate \
  --checkpoint outputs/vgg16/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --preprocessing rescale_0_1 \
  --output-file outputs/vgg16/calibration.json
```

Luego la inferencia usa:

```bash
python -m src.predict_image \
  --checkpoint outputs/vgg16/best_model.keras \
  --image-path ruta/a/imagen.png \
  --calibration-file outputs/vgg16/calibration.json
```

El archivo `calibration.json` registra:

- Método de calibración.
- Temperatura.
- Split usado (`validation`).
- Métricas antes y después de calibrar.
- Clase positiva (`parasitized`).
- Nombre del score (`probability_parasitized`).

Limitaciones de calibración:

- La calibración mejora la interpretabilidad probabilística, pero no corrige errores sistemáticos del modelo.
- Debe generarse con el mismo checkpoint, `img_size` y modo de preprocesamiento usados en inferencia.
- Si cambia el dataset, el split, el preprocesamiento o el modelo, la calibración debe recalcularse.

### Explicabilidad

El proyecto soporta explicabilidad post hoc con:

- Grad-CAM.
- LIME.
- SHAP.

Uso típico:

```bash
python -m src.explain \
  --checkpoint outputs/vgg16/best_model.keras \
  --method all \
  --num-samples 50 \
  --positive-label parasitized
```

En inferencia individual:

```bash
python -m src.predict_image \
  --checkpoint outputs/vgg16/best_model.keras \
  --image-path ruta/a/imagen.png \
  --explain gradcam
```

Limitaciones de explicabilidad:

- Los mapas de calor muestran regiones que influyeron en el modelo, no prueba causal ni validación diagnóstica.
- Un mapa visualmente plausible no garantiza que la predicción sea correcta.
- Un mapa visualmente pobre puede indicar problemas de modelo, preprocesamiento, imagen o método de explicación.
- LIME y SHAP pueden ser sensibles a parámetros de muestreo y segmentación.
- Grad-CAM depende de la arquitectura y de la capa convolucional usada.

La revisión caso a caso debe considerar simultáneamente imagen real, predicción, score, calidad de imagen, explicación visual y contexto experimental del run.

### Advertencia de Uso

Este sistema debe describirse como:

```text
Herramienta experimental de apoyo para clasificación de imágenes microscópicas.
```

No debe describirse como:

```text
Sistema de diagnóstico clínico definitivo.
```

La respuesta estructurada de inferencia incluye el disclaimer:

```text
Resultado experimental de apoyo. No corresponde a diagnóstico clínico definitivo.
```

Para un uso clínico real se requeriría, como mínimo:

- Validación externa con datos independientes.
- Split por paciente o muestra.
- Revisión de expertos.
- Protocolo de control de calidad de imagen.
- Evaluación prospectiva.
- Gestión regulatoria y trazabilidad operacional.

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

Punto reusable para CLI y futura API:

```python
from src.predict_image import run_clinical_inference

result = run_clinical_inference(
    checkpoint="outputs/vgg16/best_model.keras",
    image_path="ruta/a/imagen.png",
    img_size=200,
    calibration_file="outputs/vgg16/calibration.json",
    track_db=True,
)
```

`run_clinical_inference(...)` ejecuta control de calidad, preprocesamiento, predicción, calibración, explicabilidad opcional y tracking opcional. No imprime, no guarda JSON y no escribe CSV; esas responsabilidades quedan en el wrapper CLI o en el backend.

Archivos de apoyo:

- `src/decision.py`
- `src/image_quality.py`
- `src/inference_pipeline.py`
- `src/calibration.py`
- `src/calibrate.py`
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

La calibración real se estima con el validation set y se guarda por checkpoint.
El archivo debe generarse con el mismo `--img-size` y `--preprocessing` usados por el modelo:

```bash
python -m src.calibrate \
  --checkpoint outputs/vgg16/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --preprocessing rescale_0_1 \
  --output-file outputs/vgg16/calibration.json \
  --track-db
```

Luego la inferencia usa ese archivo:

```bash
python -m src.predict_image \
  --checkpoint outputs/vgg16/best_model.keras \
  --image-path ruta/a/imagen.png \
  --positive-label parasitized \
  --calibration-file outputs/vgg16/calibration.json
```

Sin archivo, el método por defecto es `none`. `--calibration-temperature` se mantiene para pruebas manuales, pero el flujo recomendado es `--calibration-file`.

El resultado JSON, `external_predictions.csv` y tracking en PostgreSQL registran si la probabilidad fue calibrada, la temperatura usada, el archivo y la probabilidad no calibrada.

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
