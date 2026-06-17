# Malaria Parasite Detection — Entorno local con Python

Proyecto local para entrenar y evaluar modelos de Deep Learning sobre el dataset **NIH / NLM Malaria Cell Images** usando TensorFlow Datasets.

Incluye:
- Custom CNN
- Transfer Learning con VGG16
- Extracción de características CNN + SVM
- Ensemble simple
- Test Time Augmentation
- Evaluación con accuracy, precision, recall, F1, AUC y matriz de confusión
- Explicabilidad visual post hoc con LIME y SHAP

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

## 2. Entrenar modelos

### Custom CNN

```bash
python -m src.train --model custom_cnn --epochs 30 --img-size 200 --batch-size 64
```

### VGG16 con Transfer Learning

```bash
python -m src.train --model vgg16 --epochs 30 --fine-tune-epochs 10 --img-size 200 --batch-size 64
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

## Explicabilidad del modelo: LIME y SHAP

El proyecto permite explicar predicciones individuales de modelos Keras entrenados usando LIME y SHAP:

```bash
python -m src.explain --checkpoint outputs/custom_cnn/best_model.keras --method lime --num-samples 20
python -m src.explain --checkpoint outputs/vgg16/best_model.keras --method shap --num-samples 20
python -m src.explain --checkpoint outputs/vgg16/best_model.keras --method both --num-samples 20
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
  --output-dir outputs/explainability
```

LIME identifica superpíxeles relevantes para una predicción local del modelo. SHAP estima la contribución de regiones o píxeles a la predicción. Estas técnicas ayudan a revisar verdaderos positivos, verdaderos negativos, falsos positivos, falsos negativos y casos de baja confianza cercanos al umbral de clasificación.

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
  explanation_summary.csv
```

Cada imagen explicada se guarda como PNG con clase real, clase predicha y score en el nombre del archivo. El CSV `explanation_summary.csv` registra `case_id`, tipo de caso, clase real, clase predicha, score, umbral, método y ruta de imagen.

## Explicabilidad post hoc

La explicabilidad se incorpora para aportar trazabilidad visual al proceso de evaluación y facilitar el análisis de coherencia del modelo en un contexto de apoyo diagnóstico. No reemplaza métricas cuantitativas como AUC, recall o F1, pero permite inspeccionar si las regiones que influyen en una predicción son razonables desde el punto de vista visual.

LIME aporta una explicación local basada en superpíxeles: perturba regiones de una imagen y estima qué zonas sostienen la decisión del modelo para ese caso. SHAP estima contribuciones de entrada a la predicción usando un conjunto pequeño de imágenes de entrenamiento como background.

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

## 3. Exportar imágenes a carpetas

```bash
python -m src.export_dataset --output-dir data/malaria_images
```

Esto crea:

```text
data/malaria_images/
  parasitized/
  uninfected/
```

## 4. Estructura del proyecto

```text
malaria_dl_local_project/
  requirements.txt
  README.md
  src/
    __init__.py
    config.py
    data.py
    models.py
    metrics.py
    train.py
    evaluate.py
    svm_features.py
    ensemble.py
    export_dataset.py
    explain.py
    tta.py
  outputs/
    explainability/
```

## 5. Notas metodológicas

TensorFlow Datasets entrega el dataset `malaria` como un único split llamado `train`.
Este proyecto lo divide en:

- 80% entrenamiento
- 10% validación
- 10% test

Para un Capstone más riguroso, idealmente se debe revisar la fuente NIH/NLM original y separar por paciente si se dispone del mapeo `Patient-ID`, evitando fuga de información entre entrenamiento y prueba.

## 6. Dataset

TensorFlow Datasets:

https://www.tensorflow.org/datasets/catalog/malaria

Fuente NIH/NLM:

https://lhncbc.nlm.nih.gov/publication/pub9932
