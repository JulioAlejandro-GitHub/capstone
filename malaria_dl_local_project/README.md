# Malaria Parasite Detection — Entorno local con Python

Proyecto local para entrenar y evaluar modelos de Deep Learning sobre el dataset **NIH / NLM Malaria Cell Images** usando TensorFlow Datasets.

Incluye:
- Custom CNN
- Transfer Learning con VGG16
- Extracción de características CNN + SVM
- Ensemble simple
- Test Time Augmentation
- Evaluación con accuracy, precision, recall, F1, AUC y matriz de confusión
- Explicabilidad visual post hoc con LIME, SHAP y Grad-CAM

Guía de flujos:

```text
docs/workflows.md
```

Ese documento separa entrenamiento, evaluación experimental e inferencia clínica experimental con imagen externa.

## 1. Crear entorno virtual

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Si PowerShell bloquea la activación:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 2. Dataset local con TensorFlow Datasets

El dataset **NIH / NLM Malaria Cell Images** se gestiona con TensorFlow Datasets, pero la descarga debe quedar dentro de la raíz del repositorio `capstone/`:

```text
capstone/data/tensorflow_datasets/
```

Desde `capstone/malaria_dl_local_project`, esa ruta corresponde a:

```text
../data/tensorflow_datasets/
```

El código usa la función `get_tfds_data_dir()` en `src/data.py`:

- Si existe `TFDS_DATA_DIR`, usa esa ruta.
- Si no existe `TFDS_DATA_DIR`, usa por defecto `capstone/data/tensorflow_datasets`.

Descargar o validar el dataset:

```bash
cd capstone/malaria_dl_local_project
source .venv/bin/activate
python scripts/download_malaria_dataset.py
```

Validar que existe localmente:

```bash
ls ../data/tensorflow_datasets/malaria
```

También puedes validar desde Python:

```bash
python - <<'PY'
from src.data import get_tfds_data_dir
print(get_tfds_data_dir())
PY
```

La carpeta `capstone/data/tensorflow_datasets/` está ignorada por Git. No se deben versionar imágenes, shards ni archivos TFRecord del dataset.

## Preprocesamiento por arquitectura

El pipeline usa `src/preprocessing.py` como punto único de preprocesamiento y los scripts aceptan `--preprocessing`.

- `auto`: valor por defecto. Mantiene compatibilidad y resuelve a `rescale_0_1`.
- `rescale_0_1`: resize + `float32` + normalización `[0, 1]`. Úsalo para `custom_cnn` y checkpoints ya entrenados.
- `vgg16_imagenet`: resize + `tf.keras.applications.vgg16.preprocess_input`. Úsalo solo con VGG16 reentrenado con ese mismo modo.

No mezcles modos entre entrenamiento e inferencia. Un checkpoint VGG16 histórico en `outputs/vgg16/` debe evaluarse con `rescale_0_1`. Para probar VGG16 con preprocesamiento ImageNet, reentrena en una carpeta separada:

```bash
python -m src.train \
  --model vgg16 \
  --epochs 30 \
  --fine-tune-epochs 10 \
  --img-size 200 \
  --batch-size 64 \
  --preprocessing vgg16_imagenet \
  --output-dir outputs/vgg16_imagenet
```

Luego usa `--preprocessing vgg16_imagenet` en `src.evaluate`, `src.explain`, `src.tta`, `src.svm_features` y `src.predict_image` para ese checkpoint.

Nota: `src.ensemble` aplica un único modo de preprocesamiento a todos los modelos. No mezcles en el mismo ensemble checkpoints entrenados con modos distintos.

Los JSON de métricas y CSV de predicciones incluyen `preprocessing_mode` cuando el script genera esos artefactos.

## 3. Entrenar modelos

### Custom CNN

```bash
python -m src.train --model custom_cnn --epochs 30 --img-size 200 --batch-size 64
```

### VGG16 con Transfer Learning

```bash
python -m src.train --model vgg16 --epochs 30 --fine-tune-epochs 10 --img-size 200 --batch-size 64
```

### Selección del mejor checkpoint

Por defecto `best_model.keras` se selecciona con una métrica balanceada:

```text
--checkpoint-monitor val_auc
--early-stopping-monitor val_auc
```

`val_auc` evita seleccionar checkpoints solo por sensibilidad. También puedes usar `val_balanced_accuracy`, `val_recall_parasitized`, `val_recall`, `val_accuracy` o `val_loss`.

Ejemplo explícito:

```bash
python -m src.train \
  --model vgg16 \
  --epochs 30 \
  --fine-tune-epochs 10 \
  --img-size 200 \
  --batch-size 64 \
  --optimizer adam \
  --learning-rate 1e-4 \
  --checkpoint-monitor val_auc \
  --early-stopping-monitor val_auc \
  --monitor-mode max
```

No se recomienda seleccionar checkpoints usando solo `val_recall_parasitized`, porque un modelo puede aprender la solución trivial de predecir todo como `parasitized`: sensibilidad 1.0, especificidad 0.0 y balanced accuracy 0.5. Esa métrica queda disponible solo como opción explícita.

El criterio queda registrado en `outputs/<model>/checkpoint_selection.json` y la metadata clínica del modelo en `outputs/<model>/model_metadata.json`. Los logs quedan separados en `training_base_log.csv` y `fine_tuning_log.csv`; `training_log.csv` se mantiene como alias del entrenamiento base.

### SVM usando features del VGG16 entrenado

Primero entrena VGG16. Luego:

```bash
python -m src.svm_features --checkpoint outputs/vgg16/best_model.keras --img-size 200 --batch-size 64
```

### Ensemble entre Custom CNN y VGG16

```bash
python -m src.ensemble \
  --models outputs/custom_cnn/best_model.keras outputs/vgg16/best_model.keras \
  --weights 0.4 0.6 \
  --img-size 200 \
  --batch-size 64
```

### Test Time Augmentation

```bash
python -m src.tta --checkpoint outputs/vgg16/best_model.keras --img-size 200 --n-aug 8
```

### Evaluación directa de un modelo guardado

```bash
python -m src.evaluate --checkpoint outputs/vgg16/best_model.keras --img-size 200 --batch-size 64
```

### Inferencia estructurada de imagen externa

La clase clínica positiva por defecto es `parasitized`.

La convención oficial del proyecto es:

```text
0 = uninfected
1 = parasitized
raw_model_score = probability_parasitized
label_mapping_version = clinical_v1_parasitized_positive
```

La decisión clínica experimental aplica el umbral sobre `probability_parasitized`:

```text
probability_parasitized >= threshold -> parasitized
probability_parasitized < threshold  -> uninfected
```

TensorFlow Datasets entrega originalmente `0 = parasitized` y `1 = uninfected`, pero `src.data` remapea las etiquetas antes de entrenar, evaluar y explicar. Si necesitas usar un checkpoint antiguo entrenado con la convención TFDS previa, declara explícitamente:

```bash
--label-mapping legacy_tfds_parasitized_zero
```

Este flag está disponible en `src.predict_image`, `src.evaluate`, `src.explain`, `src.calibrate`, `src.tta` y `src.ensemble`.

`src.predict_image` reporta explícitamente:

- `probability_parasitized`
- `probability_uninfected`
- `raw_model_score_meaning`
- `label_mapping_version`
- `confidence_level`
- `decision`
- `human_readable_response`

### Cómo detectar colapso de predicción

Los reportes de evaluación incluyen distribución de predicciones y `prediction_collapse`. Ejemplo problemático:

```text
Confusion matrix:
[[0 1385]
 [0 1371]]
```

Interpretación: el modelo predijo todas las imágenes como `parasitized`. En ese caso la sensibilidad puede ser 1.0, pero la especificidad es 0.0 y la balanced accuracy es 0.5. Ese checkpoint no debe usarse como modelo clínico experimental sin reentrenamiento o revisión.

Inferencia simple:

```bash
python -m src.predict_image \
  --checkpoint outputs/vgg16/best_model.keras \
  --image-path ruta/a/imagen.png \
  --img-size 200 \
  --positive-label parasitized \
  --threshold 0.5
```

El CLI es un wrapper sobre la función reusable:

```python
from src.predict_image import run_clinical_inference

result = run_clinical_inference(
    checkpoint="outputs/vgg16/best_model.keras",
    image_path="ruta/a/imagen.png",
    img_size=200,
)
```

La futura API web debe reutilizar esa función para evitar duplicar lógica de preprocesamiento, calibración, explicabilidad y tracking.

Inferencia con Grad-CAM:

```bash
python -m src.predict_image \
  --checkpoint outputs/vgg16/best_model.keras \
  --image-path ruta/a/imagen.png \
  --img-size 200 \
  --positive-label parasitized \
  --threshold 0.5 \
  --explain gradcam \
  --output-json outputs/predictions/prediction_result.json
```

Inferencia con TTA y tracking en PostgreSQL:

```bash
python -m src.predict_image \
  --checkpoint outputs/vgg16/best_model.keras \
  --image-path ruta/a/imagen.png \
  --img-size 200 \
  --positive-label parasitized \
  --threshold 0.5 \
  --tta \
  --n-aug 8 \
  --track-db
```

Inferencia con ensemble:

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

Calibrar probabilidades con validation set:

```bash
python -m src.calibrate \
  --checkpoint outputs/vgg16/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --preprocessing rescale_0_1 \
  --output-file outputs/vgg16/calibration.json
```

Inferencia usando el archivo de calibración:

```bash
python -m src.predict_image \
  --checkpoint outputs/vgg16/best_model.keras \
  --image-path ruta/a/imagen.png \
  --positive-label parasitized \
  --calibration-file outputs/vgg16/calibration.json
```

`external_predictions.csv`, el JSON de salida y el tracking DB registran `calibration_applied`, temperatura, archivo de calibración y `uncalibrated_probability_parasitized`.

Cuando se usa `--track-db`, la imagen se copia y renombra en:

```text
../data/prediction_uploads/
```

La ruta registrada en `predictions.image_path` y `artifacts.path` queda con formato relativo al repo, por ejemplo:

```text
data/prediction_uploads/20260618_153012_a8f23c_imagen.png
```

Estas imagenes quedan ignoradas por Git y se pueden consultar desde el backend/frontend como “Predicciones subidas”.

Las explicaciones de imágenes externas se guardan en:

```text
outputs/explainability/external_predictions/
  gradcam/
  lime/
  shap/
```

Además, cada inferencia queda acumulada en:

```text
outputs/predictions/external_predictions.csv
```

Si conoces la clase real, puedes registrarla para calcular si fue TP, TN, FP o FN:

```bash
python -m src.predict_image \
  --checkpoint outputs/vgg16/best_model.keras \
  --image-path ruta/a/imagen.png \
  --true-label uninfected \
  --positive-label parasitized \
  --track-db
```

Ejemplo rápido usando la ruta local TFDS por defecto:

```bash
python -m src.train --model custom_cnn --epochs 1 --img-size 200 --batch-size 64
```

## Explicabilidad del modelo: LIME, SHAP y Grad-CAM

El proyecto permite explicar predicciones individuales de modelos Keras entrenados usando LIME, SHAP y Grad-CAM:

```bash
python -m src.explain --checkpoint outputs/custom_cnn/best_model.keras --method lime --num-samples 20
python -m src.explain --checkpoint outputs/vgg16/best_model.keras --method shap --num-samples 20
python -m src.explain --checkpoint outputs/vgg16/best_model.keras --method both --num-samples 20
python -m src.explain --checkpoint outputs/vgg16/best_model.keras --method all --num-samples 20
```

También se pueden controlar el tamaño de imagen, batch, umbral y carpeta de salida:

```bash
python -m src.explain \
  --checkpoint outputs/vgg16/best_model.keras \
  --method both \
  --img-size 200 \
  --batch-size 64 \
  --num-samples 20 \
  --threshold 0.5 \
  --positive-label parasitized \
  --preprocessing auto \
  --max-candidates 200 \
  --output-dir outputs/explainability
```

LIME identifica superpíxeles relevantes para una predicción local del modelo. SHAP estima la contribución de regiones o píxeles a la predicción. Grad-CAM genera mapas de calor usando los gradientes de la clase predicha sobre la última capa convolucional. Estas técnicas ayudan a revisar verdaderos positivos, verdaderos negativos, falsos positivos, falsos negativos y casos de baja confianza cercanos al umbral de clasificación.

En los reportes clínicos experimentales, la clase positiva debe ser `parasitized`. Bajo la convención oficial, `raw_model_score` equivale a `probability_parasitized`; los campos `raw_model_score_meaning` y `label_mapping_version` quedan guardados para evitar ambigüedad con checkpoints antiguos.

Las salidas se guardan en:

```text
outputs/explainability/
  lime/
    true_positive/
    true_negative/
    false_positive/
    false_negative/
    low_confidence/
  shap/
    true_positive/
    true_negative/
    false_positive/
    false_negative/
    low_confidence/
  gradcam/
    true_positive/
    true_negative/
    false_positive/
    false_negative/
    low_confidence/
  explanation_summary.csv
```

Cada imagen explicada se guarda como PNG con clase real, clase predicha y `prob-parasitized` en el nombre del archivo. El CSV `explanation_summary.csv` registra `case_id`, tipo de caso, clase real, clase predicha, probabilidad de la clase positiva, clase positiva, umbral, método, éxito, error, ruta de imagen, convención de etiquetas y, para Grad-CAM, la capa convolucional usada.

## Explicabilidad con Grad-CAM

Grad-CAM permite visualizar las regiones de una imagen que más influyeron en la decisión de una red convolucional. En el proyecto se utiliza para revisar si el modelo está enfocando su atención en zonas microscópicas clínicamente plausibles.

Comandos de ejemplo:

```bash
python -m src.explain --checkpoint outputs/custom_cnn/best_model.keras --method gradcam --num-samples 20

python -m src.explain --checkpoint outputs/vgg16/best_model.keras --method gradcam --num-samples 20

python -m src.explain --checkpoint outputs/vgg16/best_model.keras --method all --num-samples 20
```

La salida de Grad-CAM se guarda en:

```bash
outputs/explainability/gradcam/
```

## Explicabilidad post hoc

La explicabilidad se incorpora para aportar trazabilidad visual al proceso de evaluación y facilitar el análisis de coherencia del modelo en un contexto de apoyo diagnóstico. No reemplaza métricas cuantitativas como AUC, recall o F1, pero permite inspeccionar si las regiones que influyen en una predicción son razonables desde el punto de vista visual.

LIME aporta una explicación local basada en superpíxeles: perturba regiones de una imagen y estima qué zonas sostienen la decisión del modelo para ese caso. SHAP estima contribuciones de entrada a la predicción usando un conjunto pequeño de imágenes de entrenamiento como background.

## Grad-CAM — Gradient-weighted Class Activation Mapping

Grad-CAM es una técnica de explicabilidad visual para redes convolucionales. Calcula la importancia de los mapas de activación de la última capa convolucional usando los gradientes de la clase predicha. El resultado es un mapa de calor que permite observar qué zonas de la imagen influyeron más en la decisión del modelo.

En este proyecto se utiliza para:

- Explicar verdaderos positivos
- Explicar falsos negativos
- Revisar falsos positivos
- Analizar casos de baja confianza
- Evaluar si el modelo usa regiones visuales coherentes con patrones microscópicos relevantes

El script selecciona casos explicables de forma balanceada entre:

- Verdaderos positivos
- Verdaderos negativos
- Falsos positivos
- Falsos negativos
- Casos de baja confianza cercanos al umbral 0.50

KPI de explicabilidad:

| KPI                           | Meta                                                                    |
| ----------------------------- | ----------------------------------------------------------------------- |
| Casos explicados              | mínimo 20                                                               |
| Cobertura de errores críticos | revisar falsos positivos y falsos negativos disponibles                 |
| Trazabilidad                  | 100% de casos explicados con imagen, score, clase real y clase predicha |
| Comparación LIME/SHAP         | al menos 10 casos si se ejecuta `--method both`                         |
| Comparación completa          | LIME, SHAP y Grad-CAM si se ejecuta `--method all`                      |

## 4. Exportar imágenes a carpetas

```bash
python -m src.export_dataset --output-dir data/malaria_images
```

Esto crea:

```text
data/malaria_images/
  parasitized/
  uninfected/
```

## 5. Reset experimental seguro

Antes de reentrenar desde cero puedes purgar datos experimentales y limpiar `outputs/` con scripts seguros en `dry-run` por defecto.

```bash
python scripts/purge_db_data.py
python scripts/clean_training_outputs.py
```

Ejecución real con backup:

```bash
python scripts/reset_experimental_state.py \
  --execute \
  --confirm RESET_EXPERIMENTS \
  --backup-before
```

Guía completa: [docs/reset_experimental_state.md](docs/reset_experimental_state.md).

## 6. Estructura del proyecto

```text
capstone/
  data/
    tensorflow_datasets/     # ignorado por Git
  malaria_dl_local_project/
    requirements.txt
    README.md
    scripts/
      download_malaria_dataset.py
    src/
      __init__.py
      config.py
      data.py
      models.py
      metrics.py
      train.py
    evaluate.py
      predict_image.py
      svm_features.py
      ensemble.py
      export_dataset.py
      explain.py
      tta.py
    outputs/                 # ignorado por Git
      explainability/
```

## 7. Notas metodológicas

TensorFlow Datasets entrega el dataset `malaria` como un único split llamado `train`.
Este proyecto lo divide en:

- 80% entrenamiento
- 10% validación
- 10% test

Para un Capstone más riguroso, idealmente se debe revisar la fuente NIH/NLM original y separar por paciente si se dispone del mapeo `Patient-ID`, evitando fuga de información entre entrenamiento y prueba.

## 8. Dataset

TensorFlow Datasets:

https://www.tensorflow.org/datasets/catalog/malaria

Fuente NIH/NLM:

https://lhncbc.nlm.nih.gov/publication/pub9932
