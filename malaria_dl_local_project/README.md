# Malaria Parasite Detection — Entorno local con Python

Proyecto local para entrenar y evaluar modelos de Deep Learning sobre el dataset **NIH / NLM Malaria Cell Images** usando TensorFlow Datasets.

Incluye:
- Custom CNN
- Transfer Learning con VGG16
- Extracción de características CNN + SVM
- Ensemble simple
- Test Time Augmentation
- Evaluación con accuracy, precision, recall, F1, AUC y matriz de confusión

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
    tta.py
  outputs/
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
