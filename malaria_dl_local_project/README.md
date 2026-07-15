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

### Split físico oficial 80/10/10

El flujo oficial crea copias físicas estratificadas del dataset en:

```text
data/malaria_physical_split/
```

Esto no modifica el TFDS original. Todos los entrenamientos y evaluaciones usan por defecto este split físico con `0 = uninfected`, `1 = parasitized`.

Crear split:

```bash
python scripts/create_physical_dataset_split.py \
  --seed 42 \
  --train-ratio 0.8 \
  --val-ratio 0.1 \
  --test-ratio 0.1
```

Ver conteos sin escribir archivos:

```bash
python scripts/create_physical_dataset_split.py --dry-run
```

Regenerar:

```bash
python scripts/create_physical_dataset_split.py --overwrite --seed 42
```

Más detalle:

```text
docs/physical_dataset_split.md
```

## Preprocesamiento por arquitectura

El pipeline usa `src/preprocessing.py` como punto único de preprocesamiento y los scripts aceptan `--preprocessing`.

- `auto`: valor por defecto. Mantiene compatibilidad y resuelve a `rescale_0_1`.
- `rescale_0_1`: resize + `float32` + normalización `[0, 1]`. Úsalo para `custom_cnn` y checkpoints ya entrenados.
- `vgg16_imagenet`: resize + `tf.keras.applications.vgg16.preprocess_input`. Úsalo solo con VGG16 reentrenado con ese mismo modo.

DenseNet121 usa `auto`/`rescale_0_1` en el pipeline y conserva dentro del
modelo una capa serializable con la normalización ImageNet por canal
(media/desviación estándar) equivalente a
`tf.keras.applications.densenet.preprocess_input`. La combinación
`densenet121 + vgg16_imagenet` se rechaza explícitamente.

No mezcles modos entre entrenamiento e inferencia. Un checkpoint VGG16 histórico en `outputs/vgg16/` debe evaluarse con `rescale_0_1`. Para probar VGG16 con preprocesamiento ImageNet, reentrena en una carpeta separada:

```bash
python -m src.train \
  --model vgg16 \
  --max-epochs 30 \
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

### Política Max Epochs

`--max-epochs` define el máximo de la fase base y reemplaza a `--epochs` como
nombre recomendado. `--epochs` sigue funcionando como alias legacy; si se
entregan ambos, gana `--max-epochs`. En transfer learning,
`--fine-tune-epochs` continúa siendo el máximo independiente de la segunda
fase:

```text
base_max_epochs = max_epochs
fine_tune_max_epochs = fine_tune_epochs
total_max_epochs = max_epochs + fine_tune_epochs
```

Early stopping y selección de checkpoint usan únicamente `validation`. Por
defecto se restauran los mejores pesos y, al terminar, `test` se evalúa una
sola vez con `best_model.keras`. Para smoke tests puede omitirse esa evaluación
con `--skip-final-test-evaluation`.

### Custom CNN

```bash
python -m src.train --model custom_cnn --max-epochs 50 --img-size 200 --batch-size 64
```

Si `data/malaria_physical_split/` no existe, `src.train` falla con un mensaje indicando crear el split físico. El fallback dinámico de TFDS está disponible solo de forma explícita con `--data-source tfds`.

### VGG16 con Transfer Learning

```bash
python -m src.train --model vgg16 --max-epochs 30 --fine-tune-epochs 10 --img-size 200 --batch-size 64
```

### DenseNet121 con entrenamiento combinado

```bash
python -m src.train \
  --model densenet121 \
  --max-epochs 30 \
  --fine-tune-epochs 6 \
  --img-size 200 \
  --batch-size 64 \
  --learning-rate 0.001 \
  --fine-tune-learning-rate 0.00001 \
  --preprocessing auto \
  --checkpoint-policy auc_with_min_recall \
  --min-recall 0.98 \
  --target-recall 0.98 \
  --positive-label parasitized \
  --track-db
```

Los backbones usan pesos ImageNet por defecto. Para una prueba offline o una
inicialización aleatoria agrega `--pretrained-weights none`.

Con fine-tuning se registra `execution_type=train_combined`; sin él,
`execution_type=train_base`. Cada ejecución genera:

- `training_history.csv` con el historial canónico y métricas disponibles.
- `combined_training_history.csv` con épocas continuas y fases.
- `combined_accuracy.png`, `combined_loss.png` y `combined_training_curves.png`.
- `model_execution_summary.json` y `model_execution_summary.md`.
- `checkpoint_selection.json` con máximo, detención y mejor época de validation.
- Artefactos finales de test cuando esa evaluación está habilitada.
- Un snapshot auditable en `outputs/<model>/runs/<execution_id>/`.

Los archivos directos de `outputs/<model>/` se mantienen como salida/latest
compatible. PostgreSQL registra el snapshot por ejecución, incluyendo SHA-256,
para que un entrenamiento posterior no cambie los artefactos de runs previos.

### Selección del mejor checkpoint

Por defecto `best_model.keras` se selecciona con política clínica:

```text
--checkpoint-policy auc_with_min_recall
--min-recall 0.98
--reject-prediction-collapse
```

`auc_with_min_recall` selecciona el mayor `val_auc` entre los epochs que cumplen `val_recall_parasitized >= min_recall`. Si ningún epoch cumple la sensibilidad mínima, selecciona fallback por mejor recall y marca `policy_satisfied=false` con warning.
Cuando no se fuerza un monitor CLI, EarlyStopping sigue un score interno de
validation con el mismo orden de prioridad: primero alcanzar `min_recall` y
luego mejorar AUC.

Si no se informa ninguna de las dos banderas de épocas, los máximos base son
`custom_cnn=50`, `vgg16=30` y `densenet121=30`.

Ejemplo explícito:

```bash
python -m src.train \
  --model vgg16 \
  --max-epochs 30 \
  --fine-tune-epochs 10 \
  --img-size 200 \
  --batch-size 64 \
  --optimizer adam \
  --learning-rate 1e-4 \
  --checkpoint-policy auc_with_min_recall \
  --min-recall 0.98 \
  --track-db
```

También se puede seleccionar por `f2`, `balanced_accuracy` o `val_auc`:

```bash
python -m src.train \
  --model custom_cnn \
  --max-epochs 30 \
  --img-size 200 \
  --batch-size 64 \
  --checkpoint-policy f2 \
  --beta 2.0
```

No se usa `val_recall_parasitized` puro como default, porque un modelo puede aprender la solución trivial de predecir todo como `parasitized`: sensibilidad 1.0, especificidad 0.0 y balanced accuracy 0.5.

El criterio queda registrado en `outputs/<model>/checkpoint_policy_summary.json` y `outputs/<model>/checkpoint_selection.json`. La metadata clínica del modelo queda en `outputs/<model>/model_metadata.json`. Los logs quedan separados en `training_base_log.csv` y `fine_tuning_log.csv`; `training_log.csv` se mantiene como alias del entrenamiento base e incluye métricas clínicas de validation.

Más detalle:

```text
docs/checkpoint_policy.md
```

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
  --batch-size 64 \
  --track-db
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

### Métricas clínicas estándar

Los flujos `src.train`, `src.evaluate`, `src.tta`, `src.ensemble` y `src.svm_features` reutilizan `compute_clinical_metrics`. Las métricas se calculan con `parasitized` como clase positiva (`pos_label=1`) y el score usado por ROC-AUC/PR-AUC es siempre `probability_parasitized`.

Métricas reportadas:

- `accuracy`
- `precision_parasitized`
- `recall_parasitized` / `sensitivity_parasitized`
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

En este proyecto, la clase positiva clínica es `parasitized`. Por ello, las métricas clínicas priorizan la detección de células parasitadas. El F2-score pondera más el recall que la precisión, lo que resulta adecuado cuando los falsos negativos son más graves que los falsos positivos. Sin embargo, el sistema también reporta especificidad y distribución de predicciones para detectar modelos degenerados que predicen una sola clase.

Detalle: [docs/clinical_metrics.md](docs/clinical_metrics.md).

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

Calibrar threshold clínico con validation set:

```bash
python -m src.calibrate \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --target-recall 0.98 \
  --dataset-split val \
  --update-model-metadata \
  --track-db
```

Esto guarda `outputs/<model>/threshold_calibration.json` y, con `--update-model-metadata`, agrega `clinical_threshold` a `outputs/<model>/model_metadata.json`. El threshold se selecciona sobre validation para favorecer sensibilidad de `parasitized`; test no se usa para calibrar.

Entrenamiento con calibración integrada:

```bash
python -m src.train \
  --model custom_cnn \
  --max-epochs 30 \
  --img-size 200 \
  --batch-size 64 \
  --checkpoint-policy auc_with_min_recall \
  --min-recall 0.98 \
  --calibrate-threshold \
  --target-recall 0.98 \
  --track-db
```

Evaluación e inferencia usando threshold clínico:

```bash
python -m src.evaluate \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --threshold clinical

python -m src.predict_image \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --image-path ruta/a/imagen.png \
  --positive-label parasitized \
  --threshold clinical
```

La calibración probabilística por temperature scaling sigue disponible explícitamente:

```bash
python -m src.calibrate \
  --checkpoint outputs/vgg16/best_model.keras \
  --calibration-kind temperature_scaling \
  --output-file outputs/vgg16/calibration.json
```

Más detalle: `docs/threshold_calibration.md`.

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
python -m src.train --model custom_cnn --max-epochs 1 --img-size 200 --batch-size 64
```

## Explicabilidad del modelo: LIME, SHAP y Grad-CAM

El proyecto permite explicar predicciones individuales de modelos Keras entrenados usando LIME, SHAP y Grad-CAM:

```bash
python -m src.explain --checkpoint outputs/custom_cnn/best_model.keras --method all --num-samples 20 --track-db
python -m src.explain --checkpoint outputs/vgg16/best_model.keras --method shap --num-samples 20
python -m src.explain --checkpoint outputs/vgg16/best_model.keras --method both --num-samples 20
python -m src.explain --checkpoint outputs/vgg16/best_model.keras --method all --num-samples 20 --track-db
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

## 6. Trazabilidad de dataset en PostgreSQL

Para auditar qué imágenes físicas participaron en cada ejecución con `--track-db`,
registra el split físico en PostgreSQL:

```bash
python scripts/register_physical_split_in_db.py \
  --dataset-dir data/malaria_physical_split \
  --dataset-name malaria_physical_split \
  --dataset-source tensorflow_datasets/malaria \
  --execute
```

Guía completa y consultas SQL: [docs/database_dataset_tracking.md](docs/database_dataset_tracking.md).

El frontend incluye el menú **Dataset** para explicar el origen, el split físico
y explorar imágenes por split/clase desde PostgreSQL. Guía:
[docs/dataset_browser.md](docs/dataset_browser.md).

El tracking clínico de runs con `--track-db` registra IO, métricas clínicas,
política de checkpoint, calibración de threshold, artefactos y predicciones por
imagen en tablas incrementales de PostgreSQL. La convención registrada es siempre
`0 = uninfected`, `1 = parasitized` y `raw_model_score = probability_parasitized`.
Guía: [docs/postgresql_tracking.md](docs/postgresql_tracking.md).

El frontend incluye una vista **Evaluacion clinica** y un Run Detail clinico para
auditar F2, PR-AUC, sensibilidad, especificidad, checkpoint policy, threshold,
matriz de confusion, predicciones por imagen, artefactos y explicabilidad.
Guía: [docs/frontend_clinical_dashboard.md](docs/frontend_clinical_dashboard.md).

## 7. Estructura del proyecto

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

## 8. Notas metodológicas

Guía integrada de entrenamiento, evaluación, inferencia, threshold clínico y tracking:
[docs/training_evaluation_inference_workflow.md](docs/training_evaluation_inference_workflow.md).

TensorFlow Datasets entrega el dataset `malaria` como un único split llamado `train`.
El flujo oficial del proyecto primero crea un split físico persistente con:

```bash
python scripts/create_physical_dataset_split.py --seed 42
```

Ese split queda en `data/malaria_physical_split/` con 80% entrenamiento, 10% validación y 10% test, estratificado por clase. El TFDS original no se modifica.

Para un Capstone más riguroso, idealmente se debe revisar la fuente NIH/NLM original y separar por paciente si se dispone del mapeo `Patient-ID`, evitando fuga de información entre entrenamiento y prueba.

## 9. Dataset

TensorFlow Datasets:

https://www.tensorflow.org/datasets/catalog/malaria

Fuente NIH/NLM:

https://lhncbc.nlm.nih.gov/publication/pub9932
