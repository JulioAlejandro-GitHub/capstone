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
Para evaluar una imagen nueva individual ahora existe:
python -m src.predict_image \
  --checkpoint outputs/vgg16/best_model.keras \
  --image-path ruta/a/imagen.png \
  --img-size 200 \
  --positive-label parasitized \
  --threshold 0.5

Con tracking en PostgreSQL:
python -m src.predict_image \
  --checkpoint outputs/vgg16/best_model.keras \
  --image-path ruta/a/imagen.png \
  --positive-label parasitized \
  --track-db

Si conoces la clase real, agrega:
--true-label uninfected

5:07 PM




Sí. Desde la raíz del proyecto Python:
cd capstone/malaria_dl_local_project
source .venv/bin/activate
Primero, si el dataset no está descargado:
python scripts/download_malaria_dataset.py
1. Entrenamiento
Custom CNN:
python -m src.train --model custom_cnn --epochs 30 --img-size 200 --batch-size 64
Custom CNN con tracking en BD:
python -m src.train --model custom_cnn --epochs 30 --img-size 200 --batch-size 64 --track-db
VGG16 transfer learning:
python -m src.train --model vgg16 --epochs 30 --fine-tune-epochs 10 --img-size 200 --batch-size 64
VGG16 con tracking:
python -m src.train --model vgg16 --epochs 30 --fine-tune-epochs 10 --img-size 200 --batch-size 64 --track-db
Ejecución rápida de prueba:
python -m src.train --model custom_cnn --epochs 1 --img-size 200 --batch-size 64
2. Evaluación
Evaluar Custom CNN:
python -m src.evaluate --checkpoint outputs/custom_cnn/best_model.keras --img-size 200 --batch-size 64
Evaluar VGG16:
python -m src.evaluate --checkpoint outputs/vgg16/best_model.keras --img-size 200 --batch-size 64
Con tracking:
python -m src.evaluate --checkpoint outputs/vgg16/best_model.keras --img-size 200 --batch-size 64 --track-db
3. Explicabilidad
Grad-CAM recomendado para reporte caso a caso:
python -m src.explain \
  --checkpoint outputs/vgg16/best_model.keras \
  --method gradcam \
  --num-samples 20 \
  --positive-label parasitized \
  --track-db
LIME:
python -m src.explain --checkpoint outputs/vgg16/best_model.keras --method lime --num-samples 20 --positive-label parasitized --track-db
SHAP:
python -m src.explain --checkpoint outputs/vgg16/best_model.keras --method shap --num-samples 20 --positive-label parasitized --track-db
LIME + SHAP:
python -m src.explain --checkpoint outputs/vgg16/best_model.keras --method both --num-samples 20 --positive-label parasitized --track-db
LIME + SHAP + Grad-CAM:
python -m src.explain --checkpoint outputs/vgg16/best_model.keras --method all --num-samples 50 --positive-label parasitized --track-db
4. SVM con features CNN
Usando VGG16 como extractor:
python -m src.svm_features \
  --checkpoint outputs/vgg16/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --gamma 0.1 \
  --track-db
5. Ensemble
Custom CNN + VGG16 con pesos iguales:
python -m src.ensemble \
  --models outputs/custom_cnn/best_model.keras outputs/vgg16/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --track-db
Custom CNN + VGG16 ponderado:
python -m src.ensemble \
  --models outputs/custom_cnn/best_model.keras outputs/vgg16/best_model.keras \
  --weights 0.4 0.6 \
  --img-size 200 \
  --batch-size 64 \
  --track-db
6. Test Time Augmentation
Sobre VGG16:
python -m src.tta \
  --checkpoint outputs/vgg16/best_model.keras \
  --img-size 200 \
  --n-aug 8 \
  --track-db
Sobre Custom CNN:
python -m src.tta \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --img-size 200 \
  --n-aug 8 \
  --track-db
Flujo recomendado completo para Capstone
python -m src.train --model custom_cnn --epochs 30 --img-size 200 --batch-size 64 --track-db

python -m src.train --model vgg16 --epochs 30 --fine-tune-epochs 10 --img-size 200 --batch-size 64 --track-db

python -m src.evaluate --checkpoint outputs/custom_cnn/best_model.keras --img-size 200 --batch-size 64 --track-db

python -m src.evaluate --checkpoint outputs/vgg16/best_model.keras --img-size 200 --batch-size 64 --track-db

python -m src.explain --checkpoint outputs/vgg16/best_model.keras --method all --num-samples 50 --positive-label parasitized --track-db

python -m src.ensemble --models outputs/custom_cnn/best_model.keras outputs/vgg16/best_model.keras --weights 0.4 0.6 --track-db

python -m src.tta --checkpoint outputs/vgg16/best_model.keras --n-aug 8 --track-db
Regla práctica: usa --track-db en toda ejecución que quieras ver luego en el backend/frontend. Para explicabilidad caso a caso, usa siempre --positive-label parasitized.
