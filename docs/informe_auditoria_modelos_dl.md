# Informe de auditoría del código de modelos de Deep Learning

**Repositorio:** `capstone` — sistema de diagnóstico de malaria por visión computacional
**Fecha:** 2026-09-03
**Alcance:** Custom CNN, VGG16, DenseNet121 × {Adam, AdamW, SGD, Adadelta}
**Método:** lectura directa del código fuente. Cada dato se cita con archivo y línea. Lo que no está
explícito se marca como *"no encontrado"* o *"default de librería, no sobrescrito"*.

> **Resumen para la presentación (léase primero).**
> 1. **No existen notebooks (`.ipynb`) en el repositorio.** Toda la implementación es código Python
>    productivo/de investigación bajo `malaria_dl_local_project/src/`.
> 2. **Hay una sola implementación de cada arquitectura**, en
>    `malaria_dl_local_project/src/malaria_dl/models/architectures.py`. El backend (`backend_api`) no
>    redefine modelos: solo carga los `.keras` ya entrenados e infiere.
> 3. **El conteo de 422.881 parámetros de la Custom CNN es correcto** (verificado capa por capa).
> 4. **El EarlyStopping y el checkpoint NO monitorean Recall directamente.** Monitorean
>    `val_f2_parasitized` (F2 con β=2, calculado a threshold 0.5). El objetivo "Recall ≥ 98 %" se
>    aplica *después*, en la calibración del umbral sobre validation. Esto es la inconsistencia
>    principal a explicar.
> 5. **La tabla de 12 configuraciones vive en PostgreSQL** (`--track-db`), además de snapshots
>    inmutables por corrida en `outputs/<modelo>/runs/<uuid>/`.
> 6. **Los números exactos de la presentación (VGG16+SGD: threshold 0,210794, F2 96,01 % / 94,61 %)
>    no se reproducen con ningún artefacto actualmente presente en el filesystem.** El más cercano es
>    una corrida SGD con threshold 0,2233 y F2 val 95,34 % / test 95,91 %. Ver §6 y "Discrepancias".

---

## 1. Localización del código

### 1.1 Estructura de proyectos

| Carpeta | Rol | Contenido de modelos |
|---|---|---|
| `malaria_dl_local_project/` | **Proyecto de investigación / entrenamiento** (código productivo) | Implementación real de las 3 arquitecturas, entrenamiento, evaluación, calibración |
| `malaria_dl_local_project/src/*.py` (planos) | **Adaptadores legacy** | Solo re-exportan desde `src/malaria_dl/…` |
| `malaria_dl_local_project/src/malaria_dl/` | **Paquete canónico refactorizado** | Aquí está toda la lógica |
| `backend_api/` | API FastAPI productiva | **No define modelos**; hace `sys.path.insert` a `malaria_dl_local_project` y carga `.keras` |
| `backend_api/malaria_dl_local_project/` | vacía | placeholder (0 archivos) |

```txt
# backend_api/malaria_dl_local_project — carpeta vacía
$ ls backend_api/malaria_dl_local_project
(vacío)
```

### 1.2 Archivos que DEFINEN las arquitecturas

**Único archivo de definición:**

```python
# malaria_dl_local_project/src/malaria_dl/models/architectures.py:203-349
def build_custom_cnn(input_shape=(200, 200, 3), learning_rate=1e-4, optimizer_name="adam", l2_weight=1e-4): ...
def build_vgg16_transfer(input_shape=(200, 200, 3), ..., trainable_backbone=False, weights="imagenet"): ...
def build_densenet121_transfer(input_shape=(200, 200, 3), ..., trainable_backbone=False, weights="imagenet", dropout_rate=0.5): ...
def unfreeze_last_layers(base_model, n_layers=4): ...
```

**Adaptadores legacy (solo redirección, sin lógica):**

```python
# malaria_dl_local_project/src/models.py:1-5
"""Legacy adapter for canonical model architectures."""
from importlib import import_module
import sys
_implementation = import_module("src.malaria_dl.models.architectures")
sys.modules[__name__] = _implementation
```

```python
# malaria_dl_local_project/src/malaria_dl/models/registry.py:7-11
MODEL_REGISTRY = {
    "custom_cnn": build_custom_cnn,
    "vgg16": build_vgg16_transfer,
    "densenet121": build_densenet121_transfer,
}
```

### 1.3 Archivos que ENTRENAN

| Archivo | Rol |
|---|---|
| `malaria_dl_local_project/src/malaria_dl/training/trainer.py` (2.573 líneas) | Motor de entrenamiento: parseo CLI, construcción de modelo, callbacks, fases base/fine-tuning, calibración de threshold, evaluación final, tracking DB |
| `malaria_dl_local_project/src/train.py` | Adaptador legacy → `trainer.main()` |
| `malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py` (697 líneas) | Política de checkpoint + callbacks clínicos + `early_stopping_score` |
| `malaria_dl_local_project/src/malaria_dl/training/trainer.py:354-373` | `ValidationEarlyStopping` (subclase de `tf.keras.callbacks.EarlyStopping`) |
| `malaria_dl_local_project/run_train_all_models.py` | **Orquestador de las 12 combinaciones** (3 modelos × 4 optimizadores) |
| `malaria_dl_local_project/src/malaria_dl/evaluation/evaluator.py` | Evaluación standalone (`src.evaluate`) |
| `malaria_dl_local_project/run_evaluate_all_trainings.py` | Re-evalúa todas las corridas registradas en la DB |
| `malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py` | Búsqueda del umbral que logra `recall ≥ target` |
| `malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py` (689 líneas) | `compute_clinical_metrics`, F2, matriz de confusión, `collect_predictions` |
| `malaria_dl_local_project/src/malaria_dl/data/loaders.py` | Carga de splits, augmentation |
| `malaria_dl_local_project/src/malaria_dl/data/preprocessing.py` | Modos de preprocesamiento |

### 1.4 Código productivo (backend) que consume los modelos

```python
# backend_api/app/services/productive_model.py:306-318
... capstone_root / "malaria_dl_local_project"
return tf.keras.models.load_model(path, compile=False)
```

```python
# backend_api/app/routes/governance.py:14-21
CAPSTONE_ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(CAPSTONE_ROOT/"malaria_dl_local_project"))
from src.malaria_dl.inference.traceable import ModelCache,TraceableInferenceService
```

**No hay doble implementación de arquitecturas.** La única diferencia investigación/producción es:
la investigación *construye y entrena* la topología; el backend *carga el `.keras` serializado* y
solo hace inferencia (`compile=False`).

---

## 2. Arquitectura exacta de cada modelo

### 2.0 Convención de clases (común a los tres)

```python
# malaria_dl_local_project/src/malaria_dl/config/settings.py:11-17
NEGATIVE_LABEL = "uninfected"      # índice 0
POSITIVE_LABEL = "parasitized"     # índice 1
CLASS_NAMES = ["uninfected", "parasitized"]
# La salida sigmoid = probability_parasitized (cercano a 1 ⇒ parasitized)
```

Todos los modelos se compilan con la misma función:

```python
# malaria_dl_local_project/src/malaria_dl/models/architectures.py:166-186
def compile_binary_model(model, learning_rate=1e-4, optimizer_name="adam"):
    optimizer = build_optimizer(optimizer_name=optimizer_name, learning_rate=learning_rate)
    model.compile(
        optimizer=optimizer,
        loss="binary_crossentropy",
        metrics=["accuracy", Precision, Recall, ParasitizedRecall, Specificity,
                 BalancedAccuracy, AUC(curve="ROC"), AUC(curve="PR")],
    )
```

- **Loss:** `binary_crossentropy` (string de Keras, `from_logits=False` porque la salida ya es
  sigmoid). Sin label smoothing. **Sin `class_weight`** (ver §3.5).

### 2.1 Custom CNN

```python
# malaria_dl_local_project/src/malaria_dl/models/architectures.py:189-243
def conv_bn_relu(filters, l2_weight):
    return [
        layers.Conv2D(filters, (3, 3), padding="same", use_bias=False,
                      kernel_regularizer=regularizers.l2(l2_weight) if l2_weight else None),
        layers.BatchNormalization(),
        layers.Activation("relu"),
    ]

def build_custom_cnn(input_shape=(200, 200, 3), learning_rate=1e-4, optimizer_name="adam", l2_weight=1e-4):
    model = models.Sequential([
        layers.Input(shape=input_shape),
        *conv_bn_relu(32, l2_weight),
        layers.MaxPooling2D((2, 2)),
        *conv_bn_relu(64, l2_weight),
        layers.MaxPooling2D((2, 2)),
        *conv_bn_relu(128, l2_weight),
        layers.MaxPooling2D((2, 2)),
        *conv_bn_relu(256, l2_weight),
        layers.GlobalAveragePooling2D(),
        layers.Dense(128, activation="relu",
                     kernel_regularizer=regularizers.l2(l2_weight) if l2_weight else None),
        layers.Dropout(0.4),
        layers.Dense(1, activation="sigmoid"),
    ], name="custom_cnn")
    return compile_binary_model(model, learning_rate=learning_rate, optimizer_name=optimizer_name)
```

**Definición capa por capa (input 200×200×3):**

| # | Capa | Filtros/Unidades | Kernel | Stride | Padding | Activación | Bias | Regularización |
|---|---|---|---|---|---|---|---|---|
| 1 | Conv2D | 32 | 3×3 | 1 | same | — | **no** (`use_bias=False`) | L2(1e-4) |
| 2 | BatchNormalization | — | — | — | — | — | — | — |
| 3 | Activation | — | — | — | — | **ReLU** | — | — |
| 4 | MaxPooling2D | — | 2×2 | 2 (default) | valid (default) | — | — | — |
| 5-7 | Conv2D+BN+ReLU | 64 | 3×3 | 1 | same | ReLU | no | L2(1e-4) |
| 8 | MaxPooling2D | — | 2×2 | 2 | valid | — | — | — |
| 9-11 | Conv2D+BN+ReLU | 128 | 3×3 | 1 | same | ReLU | no | L2(1e-4) |
| 12 | MaxPooling2D | — | 2×2 | 2 | valid | — | — | — |
| 13-15 | Conv2D+BN+ReLU | 256 | 3×3 | 1 | same | ReLU | no | L2(1e-4) |
| 16 | GlobalAveragePooling2D | — | — | — | — | — | — | — |
| 17 | Dense | 128 | — | — | — | **ReLU** | sí (default) | L2(1e-4) |
| 18 | Dropout | rate = **0.4** | — | — | — | — | — | — |
| 19 | Dense (salida) | **1** | — | — | — | **Sigmoid** | sí | — |

> Nota: los `MaxPooling2D((2,2))` no pasan `strides` explícito ⇒ Keras usa `strides = pool_size = (2,2)`
> y `padding="valid"` por defecto.

**Conteo de parámetros — verificación de 422.881:**

El código llama a `model.summary()` en tiempo de ejecución
(`trainer.py:1494`), pero **esa salida no se persiste en ningún archivo de `outputs/`**
(iría a stdout / `execution_logs` de la DB si `--track-db`). Se verificó **ejecutando
`build_custom_cnn().summary()`** en el entorno del proyecto (TF 2.17.1 / Keras 3.14.1):

```txt
Total params:         422,881
Trainable params:     421,921
Non-trainable params:      960
```

Desglose analítico que reproduce ese número:

| Bloque | Cálculo | Params |
|---|---|---|
| Conv2D(32), sin bias | 3·3·3·32 | 864 |
| BatchNorm(32) | 4·32 | 128 |
| Conv2D(64) | 3·3·32·64 | 18.432 |
| BatchNorm(64) | 4·64 | 256 |
| Conv2D(128) | 3·3·64·128 | 73.728 |
| BatchNorm(128) | 4·128 | 512 |
| Conv2D(256) | 3·3·128·256 | 294.912 |
| BatchNorm(256) | 4·256 | 1.024 |
| Dense(128) | 256·128 + 128 | 32.896 |
| Dense(1) | 128·1 + 1 | 129 |
| **Total** | | **422.881** ✅ |

- **Trainable params:** 421.921 (se restan `moving_mean` + `moving_variance` de las 4 BN =
  (64+128+256+512)/2 = 960 no entrenables).
- **Non-trainable params:** 960.

> **El conteo 422.881 de la presentación es exacto y reproducible.**
> El `model.summary()` literal de las tres arquitecturas (Custom CNN, VGG16 y DenseNet121, en fase
> base y fase fine-tuning) está generado en
> [`docs/model_summaries/`](docs/model_summaries/) — ver `README.md` de esa carpeta para las tablas
> de parámetros listas para diapositiva.

**Inicialización de pesos (Custom CNN):**
No se especifica ningún `kernel_initializer` en ninguna capa ⇒ **defaults de Keras, no sobrescritos**:

- `Conv2D` / `Dense`: `glorot_uniform` (Glorot/Xavier uniforme). **No es He.**
- `BatchNormalization`: `gamma = ones`, `beta = zeros`, `moving_mean = zeros`, `moving_variance = ones`.
- No hay pesos preentrenados: `build_custom_cnn` no acepta `weights` y `run_train_all_models.py:68`
  pasa `pretrained_weights = "none"` para `custom_cnn`.

### 2.2 VGG16 (transfer learning)

```python
# malaria_dl_local_project/src/malaria_dl/models/architectures.py:246-285
def build_vgg16_transfer(input_shape=(200, 200, 3), learning_rate=1e-4, optimizer_name="adam",
                         trainable_backbone=False, weights="imagenet"):
    base_model = VGG16(include_top=False, weights=weights, input_shape=input_shape)
    for layer in base_model.layers:
        layer.trainable = trainable_backbone          # ⇒ False por defecto (backbone CONGELADO)
    x = base_model.output
    x = layers.GlobalAveragePooling2D(name="global_avg_pool")(x)
    x = layers.Dense(1024, activation="relu", name="feature_dense_1024")(x)
    x = layers.Dropout(0.5, name="dropout_50")(x)
    output = layers.Dense(1, activation="sigmoid", name="binary_output")(x)
    model = models.Model(inputs=base_model.input, outputs=output, name="tl_vgg16_malaria")
    model = compile_binary_model(model, learning_rate=learning_rate, optimizer_name=optimizer_name)
    return model, base_model
```

- **Backbone:** `VGG16(include_top=False)`, pesos **ImageNet** (`weights="imagenet"`;
  `run_train_all_models.py:66-68` pasa `"imagenet"` para vgg16).
- **Congelado en fase base:** `trainable_backbone=False` (el trainer nunca lo cambia al construir,
  `trainer.py:1479-1485`). Todas las capas convolucionales de VGG16 con `trainable = False`.
- **Head de clasificación añadido:**
  `GlobalAveragePooling2D` → `Dense(1024, ReLU)` → `Dropout(0.5)` → `Dense(1, Sigmoid)`.
- **Fine-tuning parcial** (ver §2.4): tras la fase base se descongelan las **últimas 4 capas** del
  backbone y se recompila con `fine_tune_learning_rate`.
- **Init del head:** `Dense` sin initializer explícito ⇒ `glorot_uniform` (default, no sobrescrito).

### 2.3 DenseNet121 (transfer learning)

```python
# malaria_dl_local_project/src/malaria_dl/models/architectures.py:288-336
def build_densenet121_transfer(input_shape=(200, 200, 3), learning_rate=1e-4, optimizer_name="adam",
                               trainable_backbone=False, weights="imagenet", dropout_rate=0.5):
    base_model = DenseNet121(include_top=False, weights=weights, input_shape=input_shape)
    for layer in base_model.layers:
        layer.trainable = bool(trainable_backbone)     # ⇒ False (backbone CONGELADO)
    inputs = layers.Input(shape=input_shape, name="image")
    normalized = layers.Normalization(
        axis=-1, mean=[0.485, 0.456, 0.406],
        variance=[0.229**2, 0.224**2, 0.225**2],
        name="densenet_imagenet_normalization")(inputs)
    features = base_model(normalized, training=False)   # backbone invocado en modo inferencia
    pooled = layers.GlobalAveragePooling2D(name="global_avg_pool")(features)
    dropped = layers.Dropout(dropout_rate, name="dropout_50")(pooled)
    outputs = layers.Dense(1, activation="sigmoid", name="binary_output")(dropped)
    model = models.Model(inputs=inputs, outputs=outputs, name="tl_densenet121_malaria")
    model = compile_binary_model(model, learning_rate=learning_rate, optimizer_name=optimizer_name)
    return model, base_model
```

- **Backbone:** `DenseNet121(include_top=False)`, pesos **ImageNet**.
- **Congelado en fase base:** `trainable_backbone=False`.
- **Capa de normalización interna:** `layers.Normalization` con media/varianza de ImageNet
  (modo "torch" de `densenet.preprocess_input`). El pipeline entrega tensores en `[0,1]` y esta capa
  aplica `(x − mean) / std`. **VGG16 NO tiene esta capa** (ver Discrepancia D-3).
- **Head de clasificación añadido:**
  `GlobalAveragePooling2D` → `Dropout(0.5)` → `Dense(1, Sigmoid)`.
  **No hay capa densa intermedia** (a diferencia de VGG16, que tiene `Dense(1024)`).
- `base_model(normalized, training=False)`: el backbone se invoca como sub-modelo anidado en modo
  inferencia; sus BatchNorm quedan siempre en modo inferencia incluso tras descongelar (ver §2.4).

### 2.4 Fine-tuning parcial (VGG16 y DenseNet121)

```python
# malaria_dl_local_project/src/malaria_dl/models/architectures.py:339-349
def unfreeze_last_layers(base_model, n_layers=4):
    for layer in base_model.layers:
        layer.trainable = False
    for layer in base_model.layers[-n_layers:]:
        layer.trainable = True
    return base_model
```

```python
# malaria_dl_local_project/src/malaria_dl/training/trainer.py:1537-1568
if base_model is not None and args.fine_tune_epochs > 0:
    print(f"Iniciando fine-tuning parcial de {args.model}...")
    unfreeze_last_layers(base_model, n_layers=4)
    model = compile_binary_model(model, learning_rate=fine_tune_learning_rate,
                                 optimizer_name=args.optimizer)
    checkpoint_callback.set_phase("fine_tuning", epoch_offset=len(history.epoch))
    fine_tune_callbacks = build_phase_callbacks(... early_stopping_patience=args.early_stopping_patience ...)
    fine_tune_history = model.fit(ds_train, validation_data=ds_val,
                                  epochs=args.fine_tune_epochs, callbacks=fine_tune_callbacks)
```

- **Cuándo:** después de completar (o detener por EarlyStopping) la fase base, y solo si
  `--fine-tune-epochs > 0`. `run_train_all_models.py:66-68` fija **20** épocas de fine-tuning para
  vgg16 y densenet121, **0** para custom_cnn.
- **Qué se descongela:** las **últimas 4 capas** de `base_model.layers`
  (para VGG16 ≈ `block5_conv1/conv2/conv3` + `block5_pool`; `block5_pool` no tiene pesos).
- **LR distinto:** sí, se recompila con `fine_tune_learning_rate`
  (`trainer.py:1255-1259`, default `1e-5` si hay fine-tuning; valores reales por optimizador en §3).
- **Optimizador:** el mismo que la fase base (se re-instancia con el nuevo LR).
- **`custom_cnn` + `--fine-tune-epochs > 0` está prohibido** (`trainer.py:328-332`).
- **DenseNet121:** como el backbone se llamó con `training=False`, las BatchNorm del backbone no
  actualizan estadísticas ni en fine-tuning; solo los kernels de conv de las últimas 4 capas.

### 2.5 Métricas custom registradas en el modelo

```python
# malaria_dl_local_project/src/malaria_dl/models/architectures.py:9-147
@tf.keras.utils.register_keras_serializable(package="malaria")
class ParasitizedRecall(tf.keras.metrics.Metric):   # TP / (TP + FN), threshold configurable (default 0.5)
class Specificity(tf.keras.metrics.Metric):          # TN / (TN + FP)
class BalancedAccuracy(tf.keras.metrics.Metric):     # (ParasitizedRecall + Specificity) / 2
```

---

## 3. Configuración de entrenamiento por optimizador

### 3.1 Fuente de la verdad: `run_train_all_models.py`

```python
# malaria_dl_local_project/run_train_all_models.py:27-28
DEFAULT_MODELS = ["custom_cnn", "vgg16", "densenet121"]
DEFAULT_OPTIMIZERS = ["adam", "adamw", "sgd", "adadelta"]
```

```python
# malaria_dl_local_project/run_train_all_models.py:46-68
def optimizer_learning_rates(optimizer):     # (base_lr, fine_tune_lr)
    if optimizer == "sgd":       return "1e-3", "1e-4"
    if optimizer == "adadelta":  return "1.0", "1.0"
    return "1e-4", "1e-5"                     # adam y adamw

def model_training_params(model):            # (fine_tune_epochs, pretrained_weights)
    if model in {"vgg16", "densenet121"}: return "20", "imagenet"
    return "0", "none"                        # custom_cnn
```

```python
# malaria_dl_local_project/run_train_all_models.py:85-115  (comando construido por combinación)
"-m", "src.train", "--model", model,
"--max-epochs", str(max_epochs),             # default 100  (run_train_all_models.py:141)
"--fine-tune-epochs", fine_tune_epochs,       # 20 (TL) / 0 (custom_cnn)
"--img-size", "200",                          # run_train_all_models.py:142
"--batch-size", "64",                         # run_train_all_models.py:143
"--seed", "42",                               # run_train_all_models.py:144
"--learning-rate", learning_rate,
"--fine-tune-learning-rate", fine_tune_learning_rate,
"--pretrained-weights", pretrained_weights,
"--optimizer", optimizer,
"--checkpoint-monitor", "val_f2_parasitized", "--checkpoint-mode", "max",
"--early-stopping", "--early-stopping-monitor", "val_f2_parasitized", "--early-stopping-mode", "max",
"--early-stopping-patience", str(early_stopping_patience),   # default 12  (run_train_all_models.py:146)
"--early-stopping-min-delta", "0.0001",
"--restore-best-weights",
"--reject-prediction-collapse", "--min-class-fraction", "0.05",
"--calibrate-threshold", "--target-recall", str(target_recall),   # default 0.98 (line 145)
"--evaluate-best-on-test",
"--preprocessing", "auto",
"--positive-label", "parasitized",
"--track-db",
```

### 3.2 Hiperparámetros del optimizador (12 combinaciones)

```python
# malaria_dl_local_project/src/malaria_dl/models/architectures.py:150-163
def build_optimizer(optimizer_name="adam", learning_rate=1e-4):
    if optimizer_name == "adam":     return tf.keras.optimizers.Adam(learning_rate=learning_rate)
    if optimizer_name == "adamw":    return tf.keras.optimizers.AdamW(learning_rate=learning_rate)
    if optimizer_name == "sgd":      return tf.keras.optimizers.SGD(learning_rate=learning_rate, momentum=0.9)
    if optimizer_name == "adadelta": return tf.keras.optimizers.Adadelta(learning_rate=learning_rate)
```

**Solo se sobrescriben `learning_rate` y (para SGD) `momentum`. Todo lo demás es default de Keras.**
Valores confirmados contra el entorno instalado: **TensorFlow 2.17.1 / Keras 3.14.1**
(`malaria_dl_local_project/.venv`).

| Optimizador | LR base | LR fine-tuning | Otros hiperparámetros (defaults, NO sobrescritos en el código) |
|---|---|---|---|
| **Adam** | `1e-4` | `1e-5` | `beta_1=0.9`, `beta_2=0.999`, `epsilon=1e-7`, `amsgrad=False`. Sin `weight_decay`. |
| **AdamW** | `1e-4` | `1e-5` | `beta_1=0.9`, `beta_2=0.999`, `epsilon=1e-7`, **`weight_decay=0.004`** (default de `tf.keras.optimizers.AdamW` en Keras 3 — **se aplica aunque el código no lo declare**). |
| **SGD** | `1e-3` | `1e-4` | **`momentum=0.9`** (explícito, `architectures.py:160`), `nesterov=False` (default). Sin `weight_decay`. |
| **Adadelta** | `1.0` | `1.0` | `rho=0.95`, `epsilon=1e-7`. |

> `epsilon`, `rho`, `betas` y el `weight_decay=0.004` de AdamW **no aparecen en el código** — son los
> defaults de Keras 3.14.1. En particular, **AdamW sí ejerce weight decay de 0.004** por defecto, lo
> que lo diferencia de Adam más allá del nombre.

### 3.3 Batch size y épocas

| Parámetro | Valor | Cita |
|---|---|---|
| `batch_size` | **64** | `run_train_all_models.py:143`; default también en `trainer.py:104` |
| `img_size` | **200** (→ input 200×200×3) | `run_train_all_models.py:142` |
| `seed` | **42** (`tf.keras.utils.set_random_seed`) | `run_train_all_models.py:144`, `trainer.py:1404` |
| `max_epochs` fase base | **100** | `run_train_all_models.py:141` |
| fine-tune epochs | **20** (vgg16, densenet121) / **0** (custom_cnn) | `run_train_all_models.py:67-68` |
| Máx. total | **120** (TL) / **100** (custom_cnn) | `trainer.py:1290` |

> ⚠️ `trainer.py:73-77` define `DEFAULT_MAX_EPOCHS_BY_MODEL = {custom_cnn: 50, vgg16: 30, densenet121: 30}`,
> pero **solo aplica si NO se pasa `--max-epochs` ni `--epochs`** (`trainer.py:287-298`). Como
> `run_train_all_models.py` siempre pasa `--max-epochs 100`, **el cap real es 100 (+20)**, no 30/50.

### 3.4 Learning rate scheduler — `ReduceLROnPlateau`

```python
# malaria_dl_local_project/src/malaria_dl/training/trainer.py:410-421
callbacks.extend([
    *csv_loggers,
    tf.keras.callbacks.ReduceLROnPlateau(
        monitor="val_loss",
        factor=0.5,
        patience=4,
        min_lr=1e-6,
        verbose=1,
    ),
])
```

| Parámetro | Valor |
|---|---|
| Métrica monitoreada | **`val_loss`** (no la métrica clínica) |
| `factor` | **0.5** |
| `patience` | **4** |
| `min_lr` | **1e-6** |
| `mode` | `auto` (default) ⇒ `min` para `val_loss` |
| `cooldown` | 0 (default, no sobrescrito) |

- **Idéntico para las 12 configuraciones** y se instancia por fase (una en base, otra en fine-tuning).
- Coincide con lo que dice la presentación ("ReduceLR factor 0,5 / patience 4"). ✅

### 3.5 Función de pérdida y balanceo de clases

```python
# malaria_dl_local_project/src/malaria_dl/models/architectures.py:172-174
model.compile(optimizer=optimizer, loss="binary_crossentropy", metrics=[...])
```

- **Pérdida:** `binary_crossentropy` estándar, sin ponderación.
- **`class_weight`:** ✱ **no encontrado.** `grep -rn "class_weight" src/` no devuelve ninguna
  ocurrencia funcional. Las llamadas `model.fit(...)` en `trainer.py:1528-1533` y `1563-1568`
  **no pasan `class_weight` ni `sample_weight`**.
- **Balanceo por muestreo:** no hay oversampling/undersampling. El split físico gobernado tiene
  train ≈ 22.180 imágenes (≈ balanceado 50/50 según `dataset.counts`), val 2.693, test 2.685
  (`outputs/vgg16/threshold_calibration.json` → `dataset.counts`).
- El desbalance de costo (FN ≫ FP) se aborda **solo** vía: (a) métrica de selección F2 (β=2), y
  (b) calibración del umbral a `recall ≥ 0.98`. No a nivel de loss.

---

## 4. EarlyStopping + Checkpoint — decisión de diseño

### 4.1 Cómo se arman los callbacks (cadena real)

```python
# malaria_dl_local_project/src/malaria_dl/training/trainer.py:1514-1533  (fase base)
checkpoint_callback.set_phase("training_base", epoch_offset=0)
base_callbacks = build_phase_callbacks(
    output_dir=output_dir,
    checkpoint_callback=checkpoint_callback,
    clinical_validation_callback=clinical_validation_callback,
    phase="training_base",
    early_stopping_monitor="val_early_stopping_score",   # <-- HARDCODE
    early_stopping_mode="max",                           # <-- HARDCODE
    early_stopping_patience=args.early_stopping_patience,
    early_stopping_enabled=args.early_stopping,
    early_stopping_min_delta=args.early_stopping_min_delta,
    restore_best_weights=args.restore_best_weights,
    early_stopping_value_monitor=early_stopping_monitor, # "val_f2_parasitized" (resuelto)
)
history = model.fit(ds_train, validation_data=ds_val, epochs=args.max_epochs, callbacks=base_callbacks)
```

```python
# malaria_dl_local_project/src/malaria_dl/training/trainer.py:394-422
callbacks = [clinical_validation_callback, checkpoint_callback]
if early_stopping_enabled:
    callbacks.append(ValidationEarlyStopping(
        monitor=early_stopping_monitor,          # "val_early_stopping_score"
        value_monitor=early_stopping_value_monitor,  # "val_f2_parasitized"
        patience=early_stopping_patience,
        min_delta=early_stopping_min_delta,
        restore_best_weights=restore_best_weights,
        mode=early_stopping_mode,                 # "max"
        verbose=1,
    ))
callbacks.extend([*csv_loggers, ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=4, min_lr=1e-6)])
```

### 4.2 EarlyStopping

| Aspecto | Valor real | Cita |
|---|---|---|
| Clase | `ValidationEarlyStopping(tf.keras.callbacks.EarlyStopping)` | `trainer.py:354-373` |
| **Métrica monitoreada (Keras)** | **`val_early_stopping_score`** | `trainer.py:1520`, `1555` |
| Qué es `val_early_stopping_score` | transformación monótona creciente de **`val_f2_parasitized`**: `BOUND · tanh(f2 / BOUND)` con `BOUND = 1e6`, menos un offset grande si el epoch colapsó | `checkpoint_policy.py:98-123`, `579-590` |
| `mode` | **`max`** | `trainer.py:1521` |
| `patience` | **12** (`run_train_all_models.py:146`); **default en `trainer.py:228` es 10** | `trainer.py:225-229` |
| `min_delta` | **0.0001** | `run_train_all_models.py:104`, `trainer.py:231-235` |
| `restore_best_weights` | **True** | `run_train_all_models.py:105`, `trainer.py:236-241` |
| Aplicación | **una instancia por fase** (base y fine-tuning), ambas con los mismos parámetros | `trainer.py:1515-1527`, `1550-1562` |
| `val_f2_parasitized` se calcula a threshold | **0.5** (fijo durante el entrenamiento) | `trainer.py:1218` (`threshold=0.5` en `CheckpointPolicyConfig`), `checkpoint_policy.py:518-530` |

**Conclusión:** el EarlyStopping **detiene el entrenamiento cuando `val_f2_parasitized` (a
threshold 0,5) deja de mejorar por 12 epochs consecutivos** (con protección anti-colapso). **No
monitorea `val_recall` / sensibilidad directamente.**

### 4.3 Checkpoint (`ClinicalCheckpointCallback`)

```python
# malaria_dl_local_project/src/malaria_dl/training/trainer.py:1506-1512
checkpoint_callback = ClinicalCheckpointCallback(
    output_dir=output_dir,
    config=checkpoint_policy_config,
    monitor=checkpoint_monitor if explicit_checkpoint_selection else None,  # -> "val_f2_parasitized"
    mode=checkpoint_mode,                                                    # -> "max"
    verbose=1,
)
```

```python
# malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py:654-681
def _select_best(self):
    if self.monitor:
        return select_best_epoch_by_monitor(self.records, self.config, monitor=self.monitor, mode=self.mode)
    return select_best_epoch_from_history(self.records, self.config)
...
def on_epoch_end(self, epoch, logs=None):
    ...
    if selected_is_current:
        self.model.save(self.checkpoint_path, overwrite=True)   # modelo COMPLETO, formato .keras
```

| Aspecto | Valor real | Cita |
|---|---|---|
| Métrica para "mejor modelo" | **`val_f2_parasitized`** máximo (con exclusión de epochs colapsados) | `run_train_all_models.py:98-99`; `trainer.py:1223-1234`, `1509`; `checkpoint_policy.py:420-453` |
| Qué guarda | **modelo completo** (`model.save(path)` en `.keras`), no solo pesos | `checkpoint_policy.py:672` |
| Ruta | `outputs/<modelo>/best_model.keras` (alias "latest") | `checkpoint_policy.py:616` |
| Versionado | el alias `best_model.keras` **se sobrescribe** cada vez que aparece un mejor epoch; además se copia a un **snapshot inmutable** `outputs/<modelo>/runs/<uuid>/best_model.keras` al final | `trainer.py:672`, `2043-2047`, `783-815` |
| `--checkpoint-policy` configurada | `auc_with_min_recall` (default, `trainer.py:135-143`) **pero NO se usa** para la selección porque `--checkpoint-monitor` explícito activa `select_best_epoch_by_monitor` (F2 puro) | `trainer.py:347-351`, `1223-1227` |
| `--min-recall 0.98` | se pasa a `CheckpointPolicyConfig` pero **queda inerte** para la selección de checkpoint (solo se usaría en el fallback `select_best_epoch_from_history`) | `checkpoint_policy.py:70-96`, `370-417` |

### 4.4 Justificación de la métrica de monitoreo (¿por qué no Recall directo?)

```txt
# malaria_dl_local_project/docs/checkpoint_policy.md
No se usa `val_recall_parasitized` puro como default porque puede seleccionar modelos
degenerados que predicen todo como positivo: recall 1.0, especificidad 0.0.
```

El código y la doc justifican **no** monitorear Recall puro (produce modelos colapsados con
sensibilidad 1,0 / especificidad 0,0). La solución elegida:

1. Durante entrenamiento/checkpoint/early-stopping: **`val_f2_parasitized`** (F2, β=2), que pondera
   recall 4× más que precisión pero penaliza el colapso, + filtro explícito de colapso
   (`--reject-prediction-collapse`, `--min-class-fraction 0.05`).
2. Después, **una sola vez**: calibración del umbral sobre validation para forzar
   `recall_parasitized ≥ 0.98` (`--target-recall 0.98`), y recién ahí se evalúa test.

> **Inconsistencia a explicar en la presentación:** si la presentación afirma que el EarlyStopping
> "monitorea Recall ≥ 98 %", eso **no es lo que hace el código**. El EarlyStopping y el checkpoint
> monitorean **F2 a threshold 0,5** (métrica proxy). El "Recall ≥ 98 %" es una **restricción
> post-hoc de calibración del umbral**, no un criterio de parada ni de selección de epoch. F2 es un
> proxy razonable (favorece recall), pero no es una garantía dura de sensibilidad durante el
> entrenamiento.

### 4.5 ¿Callbacks idénticos para las 12 configuraciones?

**Sí, salvo el learning rate.** `run_train_all_models.py` construye el comando con los mismos flags
de EarlyStopping / checkpoint / ReduceLR / calibración para las 12 combinaciones
(`build_train_command`, `run_train_all_models.py:71-115`). Lo único que varía por combinación:
`--learning-rate`, `--fine-tune-learning-rate`, `--fine-tune-epochs`, `--pretrained-weights`
(y `--optimizer`).

---

## 5. Cálculo del F2-score

### 5.1 Función que lo calcula

```python
# malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py:1-16, 234-325
from sklearn.metrics import (classification_report, confusion_matrix, roc_auc_score,
    average_precision_score, accuracy_score, precision_score, recall_score, f1_score, fbeta_score)

def compute_clinical_metrics(y_true, y_scores, threshold: float = 0.5) -> dict:
    y_true = np.asarray(y_true).astype(int).reshape(-1)
    probability_parasitized = np.asarray(y_scores, dtype=np.float32).reshape(-1)
    ...
    y_pred = clinical_predictions_from_probabilities(probability_parasitized,
                                                    class_names=class_names, threshold=threshold)
    cm = confusion_matrix(y_true, y_pred, labels=[negative_idx, positive_idx])
    tn, fp, fn, tp = [int(value) for value in cm.ravel()]
    ...
    metrics = {
        ...
        "f2_parasitized": float(
            fbeta_score(
                y_true,
                y_pred,
                beta=2.0,
                pos_label=positive_idx,   # positive_idx = 1 (parasitized)
                zero_division=0,
            )
        ),
        ...
    }
```

```python
# malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py:93-106
def clinical_predictions_from_probabilities(probability_parasitized, class_names=None, threshold=0.5):
    ...
    return np.where(probability_parasitized >= float(threshold), positive_idx, negative_idx).astype(int)
```

### 5.2 Fórmula usada

**Se usa `sklearn.metrics.fbeta_score(y_true, y_pred, beta=2.0, pos_label=1, zero_division=0)`**,
sobre predicciones ya binarizadas al `threshold` dado. Es equivalente a:

```
F2 = (1 + 2²) · P · R / (2² · P + R) = 5 · P · R / (4 · P + R)
```

con `P = precision_parasitized`, `R = recall_parasitized`. **Coincide** con la fórmula que cita la
presentación. No hay implementación manual: siempre pasa por scikit-learn.

Segunda copia idéntica (mismo `fbeta_score`, `beta=2.0`, `pos_label=1`) en
`clinical_metrics.py:399-407` (`clinical_metric_summary`, usada por trazabilidad DB).

### 5.3 ¿Sobre qué threshold se calcula?

| Momento del pipeline | Threshold usado | Cita |
|---|---|---|
| Monitoreo por epoch en validation (`val_f2_parasitized` para checkpoint / early-stopping) | **0.5 fijo** | `trainer.py:1218`, `checkpoint_policy.py:518-530` |
| Calibración del umbral (búsqueda) | cada candidato (todos los scores únicos de validation + {0, 0.5, 1}) | `threshold_calibration.py:63-80`, `185-192` |
| **F2 "Validation" reportado** (tabla presentación) | **el threshold calibrado**, leído de `threshold_calibration.json` → `selected_metrics.f2_parasitized` | `trainer.py:1743-1789`, `threshold_calibration.py:241-257` |
| **F2 "Test" reportado** | el mismo threshold calibrado, en `test_metrics.json` → `f2_parasitized` | `trainer.py:1799-1821`, `clinical_metrics.py:662-689` |
| `src.evaluate` standalone | `--threshold` (default `0.5`, o `clinical` desde `model_metadata.json`) | `evaluator.py:31-35`, `247-248` |

**Flujo (trainer.py, con `--calibrate-threshold`):**

```python
# malaria_dl_local_project/src/malaria_dl/training/trainer.py:1734-1821  (resumido)
if args.calibrate_threshold:
    y_val_true, _, y_val_score = collect_predictions(evaluation_model, ds_val, threshold=0.5, ...)
    threshold_calibration = find_threshold_for_target_recall(
        y_true=y_val_true, y_scores=y_val_score,
        target_recall=args.target_recall,      # 0.98
        min_specificity=args.min_specificity,  # None
        beta=args.beta)                        # 2.0
    test_threshold = float(threshold_calibration["threshold_selected"])
...
metrics = evaluate_selected_checkpoint_once(model=evaluation_model, dataset=ds_test,
    checkpoint_path=best_model_path, threshold=test_threshold, ...)
```

### 5.4 ¿Es reproducible F2 = 96,01 % (val) / 94,61 % (test) para VGG16+SGD?

**Con los artefactos presentes en el filesystem: NO exactamente.** No hay ningún
`threshold_calibration.json` ni `test_metrics.json` con esos valores ni con threshold ≈ 0,210794.
Corridas VGG16 presentes (todas con `preprocessing_mode = "rescale_0_1"`):

| run (uuid corto) | optimizador | threshold sel. | val Recall | val F2 | val Spec | test F2 | test Recall | colapso |
|---|---|---|---|---|---|---|---|---|
| `291d3e64` | **sgd** | **0,223342** | 0,9804 | **0,9534** | 0,8389 | **0,9591** | 0,9848 | no |
| `4aae05df` | sgd | 0,131334 | 0,9804 | 0,9540 | 0,8472 | 0,9357 | 0,9590 | no |
| `b6c1e2b9` | adam | 0,197669 | 0,9804 | 0,9591 | 0,8694 | 0,9651 | 0,9869 | no |
| `19b11953` | adamw | 0,206043 | 0,9819 | 0,9575 | 0,8549 | 0,9611 | 0,9862 | no |
| `f19ca708` | adam | 0,101585 | 0,9804 | 0,9585 | 0,8706 | 0,9467 | 0,9628 | no |
| `48746621` | adadelta | 0,380429 | 0,9804 | 0,9180 | 0,6408 | 0,9206 | 0,9775 | no |
| `ede474d8` | adadelta | 0,0 | 1,0 | 0,8289 | 0,0 | 0,8280 | 1,0 | **sí (colapso)** |

(Fuente: `outputs/vgg16/runs/*/threshold_calibration.json` y `*/model_execution_summary.json`.)

- La combinación SGD más cercana (`291d3e64`) da **threshold 0,2233 / val F2 95,34 % / test F2 95,91 %**,
  no 0,210794 / 96,01 % / 94,61 %.
- El alias "latest" `outputs/vgg16/best_model.keras` corresponde en realidad a una corrida
  **`adadelta` colapsada** (threshold 0,0, especificidad 0,0, `prediction_collapse_detected: true`) —
  ver `outputs/vgg16/model_execution_summary.json` y `outputs/vgg16/threshold_calibration.json`.
- **Interpretación:** los números canónicos de la presentación provienen de una corrida concreta
  registrada en **PostgreSQL** (tablas `runs` / `run_clinical_metrics` / `run_threshold_calibration`),
  cuyo snapshot de filesystem o bien fue sobrescrito por corridas posteriores o bien es un snapshot
  de formato antiguo que solo conserva `model_execution_summary.md`. Para reproducir exactamente hay
  que: (a) consultar la DB, o (b) re-entrenar VGG16+SGD con `seed=42` y el comando de
  `run_train_all_models.py`.

### 5.5 ¿Difiere el F2 entre notebook de evaluación y backend productivo?

**No hay notebook.** Y el backend **no recalcula F2**: solo lee `f2_parasitized` / `f2_score` desde
la DB (columnas persistidas por el pipeline de investigación):

```sql
-- backend_api/app/services/training_summaries.py:41-52, 115-116
-- backend_api/app/services/run_lineage.py:44, 73
COALESCE(clinical.f2_parasitized, generic.f2_score) AS f2_score
```

`grep -rn "fbeta\|f2" backend_api/app` solo devuelve lecturas SQL y campos de schema Pydantic,
ninguna implementación de cálculo. **Existe una única implementación de F2 en todo el repo**
(`clinical_metrics.py`, `sklearn.fbeta_score`, β=2).

---

## 6. Trazabilidad de resultados

### 6.1 Dónde viven las métricas de las 12 configuraciones

**(a) PostgreSQL** — fuente primaria (`--track-db` en `run_train_all_models.py:114`).
Tablas relevantes (DDL vía `INSERT` en `src/malaria_dl/persistence/run_repository.py`):

| Tabla | Contenido | Cita |
|---|---|---|
| `runs` | una fila por ejecución (training/evaluation), `execution_parameters` jsonb con todos los hiperparámetros | `run_repository.py:375` |
| `models`, `model_versions` | modelo lógico + versión inmutable con `best_model_path`, `artifact_sha256` | `run_repository.py:312`, `1608` |
| `run_metrics` | métricas escalares genéricas por epoch/final | `run_repository.py:670` |
| `training_history` | curva por epoch | `run_repository.py:765` |
| **`run_clinical_metrics`** | **`threshold_used, recall_parasitized, sensitivity_parasitized, specificity, f1_parasitized, f2_parasitized, roc_auc_parasitized, pr_auc_parasitized, balanced_accuracy, tn, fp, fn, tp, confusion_matrix, ...`** por `split_name` | `run_repository.py:1153-1173` |
| **`run_threshold_calibration`** | **`threshold_selected, target_recall, target_recall_satisfied, validation_recall_at_threshold, validation_specificity_at_threshold, validation_f2_at_threshold, ...`** | `run_repository.py:1337-1362` |
| `run_checkpoint_policy` | política, epoch seleccionado, métricas del epoch | `run_repository.py:1233` |
| `confusion_matrices`, `classification_reports`, `predictions` | detalle de evaluación | `run_repository.py:811, 852, 895` |

El backend expone esto en:
`backend_api/app/routes/runs.py:234, 309, 335`, `app/services/training_summaries.py`,
`app/services/run_lineage.py`, `app/services/lineage_children.py`, `app/routes/governance.py:345-350`.

**(b) Snapshots inmutables en filesystem** — uno por corrida:
`outputs/<modelo>/runs/<run_uuid>/` con:

```txt
best_model.keras, final_model.keras
checkpoint_selection.json, checkpoint_policy_summary.json
threshold_calibration.json          # threshold + métricas de validation al threshold
test_metrics.json                   # Recall, FN, F2, Specificity, matriz de confusión en TEST
test_predictions.csv, test_confusion_matrix.csv, classification_report.json
model_metadata.json, model_execution_summary.{json,md}
training_history.csv, combined_training_history.csv
```

Generados por `trainer.py`: `write_model_execution_summary` (`trainer.py:662-780`),
`snapshot_execution_artifacts` (`trainer.py:783-815`), `evaluate_selected_checkpoint_once`
(`trainer.py:1145-1188`), `write_threshold_calibration` (`threshold_calibration.py:275-282`).

**(c) Alias "latest"** — `outputs/<modelo>/*.json` (sin subcarpeta `runs/`): siempre la **última**
corrida de ese modelo (se sobrescribe). ⚠️ Hoy contienen corridas `adadelta` (la última del loop),
y en VGG16 una corrida **colapsada** — no sirven como referencia de la presentación.

Los reportes agregados generados: `run_evaluate_all_trainings.py` consulta la DB
(`fetch_training_inventory`, `run_evaluate_all_trainings.py:57-118`) para re-evaluar todos los
`model_versions` de trainings `completed`.

### 6.2 Algoritmo de calibración del threshold (Recall ≥ 98 %)

Está en un módulo separado: `malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py`.

```python
# malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py:63-80
def build_threshold_candidates(y_scores, include_default=True):
    scores = np.asarray(y_scores, dtype=np.float64).reshape(-1)
    scores = scores[np.isfinite(scores)]
    scores = np.clip(scores, 0.0, 1.0)
    candidates = {0.0, 1.0}
    candidates.update(float(value) for value in np.unique(scores))   # TODOS los scores distintos
    if include_default:
        candidates.add(DEFAULT_THRESHOLD)                            # 0.5
    return sorted(candidates)
```

```python
# malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py:154-230  (resumido)
def find_threshold_for_target_recall(y_true, y_scores, target_recall=0.98, min_specificity=None, beta=2.0):
    candidates = build_threshold_candidates(y_scores, include_default=True)
    records = [{"threshold": t, "metrics": evaluate_threshold(y_true, y_scores, t, beta=beta)}
               for t in candidates]
    target_valid = [r for r in records
                    if (r["metrics"].get("recall_parasitized") or 0.0) >= target_recall]
    # (min_specificity es None en el pipeline de las 12 corridas)
    if target_valid:
        selected = max(target_valid, key=_selection_key)
    else:
        selected = max(records, key=_fallback_key)   # mejor recall posible; warning
```

```python
# malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py:126-146
def _selection_key(record):     # entre los que cumplen recall>=target, se maximiza en este orden:
    m = record["metrics"]
    return (m.get("specificity") or 0.0,             # 1º  mayor especificidad
            m.get("precision_parasitized") or 0.0,   # 2º  mayor precisión
            m.get("f2_parasitized") or 0.0,          # 3º  mayor F2
            m.get("balanced_accuracy") or 0.0,       # 4º  mayor balanced accuracy
            float(record["threshold"]))              # 5º  threshold más alto
```

**Características del algoritmo:**

- **Tipo:** búsqueda exhaustiva (grid) sobre **todos los valores de score únicos** de validation
  (más `{0.0, 0.5, 1.0}`). **No es búsqueda binaria** ni grilla de paso fijo.
- **Resolución:** data-driven — tantos candidatos como probabilidades distintas prediga el modelo en
  validation (ej. `candidate_count: 58` en `outputs/vgg16/threshold_calibration.json`).
- **Objetivo:** el threshold más alto entre los que logran `recall_parasitized ≥ 0.98` en
  **validation**, priorizando especificidad. **El F2 es el 3.er criterio de desempate, no el
  objetivo de la calibración.**
- **Sin leakage:** `validate_calibration_split` (`threshold_calibration.py:54-60`) **prohíbe usar
  test** (`--dataset-split test` lanza error). Solo validation.
- Si ningún threshold logra el target: se elige el de mayor recall y se marca
  `target_recall_satisfied: false` + `warning`.
- Warning adicional si `threshold_selected < 0.05` ("puede producir demasiados falsos positivos").

```txt
# malaria_dl_local_project/docs/threshold_calibration.md
Entre thresholds que cumplen el target, selecciona por:
1. mayor specificity   2. mayor precision_parasitized   3. mayor f2_parasitized
4. mayor balanced_accuracy   5. threshold más alto
```

---

## Discrepancias encontradas

| # | Afirmación de la presentación | Lo que hace el código | Severidad |
|---|---|---|---|
| **D-1** | EarlyStopping con **patience 12** | ✅ Correcto **si se usa `run_train_all_models.py`** (`--early-stopping-patience 12`, línea 146). Pero el default de `src/train.py` es **10** (`trainer.py:228`). Si alguna corrida se lanzó a mano sin el flag, fue con patience 10. | Baja — verificar en la DB (`runs.execution_parameters->>'early_stopping_patience'`) para las 12. |
| **D-2** | ReduceLR **factor 0,5 / patience 4** | ✅ Correcto, hardcodeado en `trainer.py:413-419`. Métrica monitoreada: `val_loss` (no la métrica clínica); `min_lr = 1e-6`. | OK |
| **D-3** | (implícito) VGG16 usa preprocesamiento **ImageNet** | ❌ Con `--preprocessing auto` (lo que usa `run_train_all_models.py:112`), `resolve_preprocessing_mode` devuelve **`rescale_0_1`** para *todos* los modelos, incluido VGG16 (`preprocessing.py:25-37`). VGG16 recibe RGB en `[0,1]` **sin** `vgg16.preprocess_input` ni resta de media. Confirmado en `outputs/vgg16/threshold_calibration.json` → `"preprocessing_mode": "rescale_0_1"`. Solo DenseNet121 aplica normalización tipo ImageNet, vía su capa interna `Normalization`. | **Alta** — mismatch de dominio para el backbone VGG16. |
| **D-4** | EarlyStopping / checkpoint garantiza **Recall ≥ 98 %** | ❌ Parcial. EarlyStopping monitorea `val_early_stopping_score` = transformación monótona de **`val_f2_parasitized`** (F2 a threshold 0,5). El checkpoint selecciona **máximo `val_f2_parasitized`**. El "Recall ≥ 98 %" se impone **solo después**, en la calibración del umbral sobre validation (`--target-recall 0.98`). No es criterio de parada ni de selección de epoch. | **Alta** — es la métrica proxy a explicar. |
| **D-5** | `--checkpoint-policy auc_with_min_recall` + `--min-recall 0.98` | ❌ Configurada pero **inerte**. `--checkpoint-monitor val_f2_parasitized` (`run_train_all_models.py:98`) activa `uses_explicit_metric_checkpoint → select_best_epoch_by_monitor` (F2 puro). `min_recall` solo se usaría en el fallback `select_best_epoch_from_history`, que no se ejecuta. Aun así, `model_metadata.json` / `checkpoint_policy_summary.json` reportan `policy = "auc_with_min_recall"` y `policy_satisfied = true` — **metadata engañosa** (`outputs/custom_cnn/checkpoint_selection.json`). | Media — el metadato dice una cosa y el algoritmo hace otra. |
| **D-6** | VGG16+SGD: **threshold 0,210794**, F2 **96,01 %** (val) / **94,61 %** (test) | ❌ **No reproducible con los artefactos actuales.** No hay `threshold_calibration.json` / `test_metrics.json` con esos valores. La corrida SGD presente más parecida (`outputs/vgg16/runs/291d3e64…`) da threshold **0,223342**, val F2 **95,34 %**, test F2 **95,91 %**. Los números canónicos deben estar en PostgreSQL. El alias `outputs/vgg16/` "latest" es hoy una corrida **adadelta colapsada**. | **Alta** — pedir el `run_id` exacto y verificar contra `run_clinical_metrics` / `run_threshold_calibration`. |
| **D-7** | (implícito) F2 val vs F2 test se calculan igual | ✅ Misma función (`sklearn.fbeta_score`, β=2, `pos_label=1`), mismo threshold calibrado. La única diferencia es el split. **F2 en val** sale de `threshold_calibration.json → selected_metrics`, **F2 en test** de `test_metrics.json`. | OK |
| **D-8** | (implícito) Máximo de épocas 30/50 | ⚠️ `run_train_all_models.py` pasa `--max-epochs 100` ⇒ el cap real es **100 base (+20 fine-tuning para VGG16/DenseNet, total 120)**. Los defaults 50/30/30 de `trainer.py:73-77` no aplican bajo el orquestador. | Baja — usar el valor real (100/120) en la presentación. |
| **D-9** | (implícito) Fine-tuning con LR reducido | ✅ Sí: se recompila con `fine_tune_learning_rate` (Adam/AdamW `1e-5`, SGD `1e-4`, Adadelta `1.0`) y se descongelan las **últimas 4 capas** del backbone (`unfreeze_last_layers(base_model, 4)`). Nota: para DenseNet121 el backbone se invoca con `training=False`, así que sus BatchNorm no se actualizan ni en fine-tuning. | OK — precisar "últimas 4 capas". |
| **D-10** | (implícito) balanceo de clases / class weights | ❌ **No hay `class_weight` ni `sample_weight` ni oversampling.** Loss = `binary_crossentropy` plano. El desbalance de costo se maneja solo con F2 + calibración de umbral. | Media si la presentación afirma lo contrario. |
| **D-11** | Init Custom CNN (He / Glorot) | Ninguna capa fija `kernel_initializer` ⇒ **Glorot uniform** (default Keras) para Conv2D y Dense. **No es He.** Custom CNN entrena desde init aleatoria (`pretrained_weights = "none"`). | Baja — corregir si se afirma "He". |
| **D-12** | Head de VGG16 y DenseNet121 iguales | ❌ Distintos. VGG16: `GAP → Dense(1024, ReLU) → Dropout(0.5) → Dense(1, Sigmoid)`. DenseNet121: `GAP → Dropout(0.5) → Dense(1, Sigmoid)` (**sin** densa intermedia). Custom CNN: `GAP → Dense(128, ReLU) → Dropout(0.4) → Dense(1, Sigmoid)`. | Baja — describir cada head por separado. |

### Recomendación de verificación

Para cerrar D-1 y D-6 con precisión, ejecutar contra la DB (o pedir el dump):

```sql
SELECT r.run_name,
       r.execution_parameters->>'optimizer'                AS optimizer,
       r.execution_parameters->>'early_stopping_patience'  AS patience,
       r.execution_parameters->>'preprocessing'            AS preprocessing,
       tc.threshold_selected, tc.validation_recall_at_threshold, tc.validation_f2_at_threshold,
       cm.f2_parasitized AS test_f2, cm.recall_parasitized AS test_recall, cm.fn AS test_fn,
       cm.specificity AS test_specificity
FROM runs r
LEFT JOIN run_threshold_calibration tc ON tc.run_id = r.id
LEFT JOIN run_clinical_metrics cm ON cm.run_id = r.id AND cm.split_name = 'test'
WHERE r.run_type = 'training' AND r.status = 'completed'
ORDER BY r.run_name;
```
