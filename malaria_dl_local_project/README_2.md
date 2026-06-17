La arquitectura de malaria_dl_local_project está organizada como un pipeline local de ML para clasificación binaria de imágenes de malaria.
Vista General
El proyecto tiene un paquete principal src/ con módulos separados por responsabilidad:
malaria_dl_local_project/
  src/
    config.py
    data.py
    models.py
    train.py
    evaluate.py
    metrics.py
    svm_features.py
    ensemble.py
    tta.py
    explain.py
    export_dataset.py
  outputs/
  requirements.txt
  README.md
Flujo Principal
El flujo base es:
TensorFlow Datasets malaria
        ↓
src.data
        ↓
preprocesamiento + split train/val/test
        ↓
src.models
        ↓
entrenamiento con src.train
        ↓
evaluación con src.metrics / src.evaluate
        ↓
artefactos en outputs/
        ↓
explicabilidad con src.explain
Datos
[src/data.py (line 1)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/src/data.py:1) carga el dataset malaria desde TensorFlow Datasets.
Divide el único split train en:
80% entrenamiento
10% validación
10% test
También aplica:
resize a img_size, por defecto 200x200
normalización a [0, 1]
batching
prefetch
data augmentation opcional para entrenamiento
Las clases son:
["parasitized", "uninfected"]
Modelos
[src/models.py (line 1)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/src/models.py:1) define dos arquitecturas Keras:
custom_cnn
CNN secuencial propia:
Conv2D + Conv2D + MaxPooling
Conv2D + Conv2D + MaxPooling
Conv2D + Conv2D + MaxPooling
Conv2D + Conv2D + MaxPooling
Flatten
Dense 256
Dropout 0.5
Dense 256
Dropout 0.5
Dense 1 sigmoid
vgg16
Transfer learning con VGG16 preentrenada:
VGG16 include_top=False
GlobalAveragePooling2D
Dense 1024
Dropout 0.5
Dense 1 sigmoid
Ambos modelos usan:
loss="binary_crossentropy"
optimizer=Adadelta
metrics=["accuracy", Precision, Recall, AUC]
Entrenamiento
[src/train.py (line 1)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/src/train.py:1) es el orquestador principal.
Permite entrenar:
python -m src.train --model custom_cnn
python -m src.train --model vgg16
Durante entrenamiento usa callbacks:
ModelCheckpoint: guarda best_model.keras según val_accuracy
EarlyStopping: monitorea val_loss, con patience=10
CSVLogger: guarda training_log.csv
ReduceLROnPlateau: reduce learning rate si val_loss no mejora
Los modelos quedan en:
outputs/custom_cnn/
outputs/vgg16/
Evaluación
[src/metrics.py (line 1)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/src/metrics.py:1) centraliza métricas:
accuracy
precision macro
recall macro
F1 macro
AUC
classification report
matriz de confusión
CSV de predicciones
[src/evaluate.py (line 1)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/src/evaluate.py:1) carga un .keras ya entrenado y evalúa en test.
Módulos Adicionales
[src/svm_features.py (line 1)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/src/svm_features.py:1) usa un modelo CNN, idealmente VGG16, como extractor de características y entrena un SVM RBF.
[src/ensemble.py (line 1)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/src/ensemble.py:1) combina predicciones de varios modelos Keras mediante promedio ponderado.
[src/tta.py (line 1)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/src/tta.py:1) aplica Test Time Augmentation: predice la imagen original y varias versiones aumentadas, luego promedia los scores.
[src/export_dataset.py (line 1)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/src/export_dataset.py:1) exporta imágenes del dataset a carpetas por clase.
Explicabilidad
[src/explain.py (line 1)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/src/explain.py:1) agrega interpretabilidad post hoc:
LIME
SHAP
Grad-CAM
Selecciona casos:
verdaderos positivos
verdaderos negativos
falsos positivos
falsos negativos
baja confianza
Y guarda visualizaciones en:
outputs/explainability/
Resumen
El proyecto está bien separado por capas:
data.py          carga y preprocesa datos
models.py        define arquitecturas
train.py         entrena modelos
metrics.py       calcula métricas
evaluate.py      evalúa checkpoints
svm_features.py  CNN como extractor + SVM
ensemble.py      combinación de modelos
tta.py           robustez por aumentos en inferencia
explain.py       explicabilidad visual
config.py        rutas globales
La arquitectura general es modular: cada script puede ejecutarse desde consola con python -m src.<modulo>, y todos comparten las mismas funciones de carga de datos, modelos y métricas.



En este proyecto, la explicabilidad se ejecuta con:
python -m src.explain
Ese script actualmente explica casos del conjunto de test del dataset malaria, no una imagen externa individual. Usa un checkpoint .keras ya entrenado y selecciona automáticamente casos como TP, TN, FP, FN y baja confianza.
Parámetros de src.explain
python -m src.explain \
  --checkpoint RUTA_MODELO \
  --method METODO \
  --img-size 200 \
  --batch-size 64 \
  --num-samples 20 \
  --threshold 0.5 \
  --output-dir outputs/explainability \
  --positive-label uninfected \
  --max-candidates 200
Significado:
--checkpoint: ruta del modelo Keras entrenado, por ejemplo outputs/vgg16/best_model.keras.
--method: técnica de explicabilidad:lime: solo LIME.
shap: solo SHAP.
gradcam: solo Grad-CAM.
both: LIME + SHAP.
all: LIME + SHAP + Grad-CAM.

--img-size: tamaño al que se redimensionan las imágenes. Debe coincidir con el entrenamiento. Default: 200.
--batch-size: tamaño de batch para predecir el test set. Default: 64.
--num-samples: cantidad total de casos a explicar. Default: 20.
--threshold: umbral de clasificación binaria. Default: 0.5.
--output-dir: carpeta donde se guardan imágenes y CSV. Default: outputs/explainability.
--positive-label: clase positiva usada para interpretar el score sigmoid. En tu proyecto normalmente es uninfected, porque TFDS entrega ["parasitized", "uninfected"].
--max-candidates: máximo de imágenes candidatas retenidas por tipo de caso. Default: 200.
Custom CNN con explicabilidad
python -m src.explain \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --method gradcam \
  --img-size 200 \
  --batch-size 64 \
  --num-samples 20 \
  --threshold 0.5 \
  --positive-label uninfected
Para todas las técnicas:
python -m src.explain \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --method all \
  --img-size 200 \
  --batch-size 64 \
  --num-samples 20 \
  --positive-label uninfected
VGG16 con explicabilidad
python -m src.explain \
  --checkpoint outputs/vgg16/best_model.keras \
  --method gradcam \
  --img-size 200 \
  --batch-size 64 \
  --num-samples 20 \
  --threshold 0.5 \
  --positive-label uninfected
Con LIME + SHAP + Grad-CAM:
python -m src.explain \
  --checkpoint outputs/vgg16/best_model.keras \
  --method all \
  --num-samples 20 \
  --positive-label uninfected
Salida Generada
Los resultados quedan en:
outputs/explainability/
  lime/
  shap/
  gradcam/
  explanation_summary.csv
El CSV contiene:
case_id
case_type
true_label
predicted_label
score_positive_label
positive_label
threshold
method
success
error
image_path
last_conv_layer
Sobre Ensemble y SVM
El script src.explain funciona con modelos Keras .keras.
Por eso sí aplica directamente a:
outputs/custom_cnn/best_model.keras
outputs/vgg16/best_model.keras
Pero no aplica directamente a:
outputs/cnn_features_svm/svm_rbf.joblib
porque ese SVM no es un modelo Keras convolucional. Tampoco explica directamente el ensemble, porque ensemble.py combina predicciones de varios modelos en tiempo de ejecución y no guarda un modelo Keras único. Para explicabilidad, debes explicar cada modelo base por separado: custom_cnn y vgg16.
Imagen Nueva
Con el código actual, no existe todavía un parámetro tipo:
--image-path imagen.png
Por ahora src.explain toma imágenes desde el split de test de TensorFlow Datasets.
Para evaluar una imagen nueva individual, el flujo tendría que ser:
from pathlib import Path
import numpy as np
import tensorflow as tf
from PIL import Image

checkpoint = "outputs/vgg16/best_model.keras"
image_path = "ruta/a/imagen.png"
img_size = 200
threshold = 0.5
class_names = ["parasitized", "uninfected"]

model = tf.keras.models.load_model(checkpoint)

img = Image.open(image_path).convert("RGB")
img = img.resize((img_size, img_size))
x = np.asarray(img).astype("float32") / 255.0
x = np.expand_dims(x, axis=0)

score = float(model.predict(x, verbose=0).ravel()[0])
pred_idx = 1 if score >= threshold else 0

print("score:", score)
print("predicción:", class_names[pred_idx])
Si quieres explicabilidad sobre una imagen nueva, lo correcto sería extender src.explain.py con un parámetro nuevo:
--image-path ruta/a/imagen.png
y que genere LIME, SHAP o Grad-CAM para esa imagen específica. Actualmente esa entrada directa aún no está implementada.

5:07 PM