# `model.summary()` de las tres arquitecturas

Generado ejecutando `build_custom_cnn()` / `build_vgg16_transfer()` / `build_densenet121_transfer()`
de [`malaria_dl_local_project/src/malaria_dl/models/architectures.py`](../../malaria_dl_local_project/src/malaria_dl/models/architectures.py)
en el entorno del proyecto (**TensorFlow 2.17.1 / Keras 3.14.1**). Input `200×200×3` en todos.
Los `.txt` son tablas capa-por-capa (`name`, tipo, output shape, params, params entrenables); los
totales coinciden exactamente con `model.summary()`.

| Archivo | Contenido |
|---|---|
| [`custom_cnn_summary.txt`](custom_cnn_summary.txt) | Custom CNN completo, capa por capa (19 capas) |
| [`vgg16_summary.txt`](vgg16_summary.txt) | VGG16: tabla en fase base y en fase fine-tuning (backbone plano, se ve qué capas quedan entrenables) |
| [`densenet121_summary.txt`](densenet121_summary.txt) | DenseNet121: tabla compacta (backbone plegado como `Functional`) en ambas fases |
| [`densenet121_summary_expanded.txt`](densenet121_summary_expanded.txt) | Anexo: DenseNet121 con las ~430 capas del backbone expandidas |

## Conteo de parámetros (para las diapositivas)

### Custom CNN — `custom_cnn`

| | Params |
|---|---:|
| **Total** | **422.881** |
| Entrenables | 421.921 |
| No entrenables | 960 |

> Los 960 no entrenables = `moving_mean` + `moving_variance` de las 4 capas `BatchNormalization`
> (64+128+256+512 = 1.920 → la mitad son estadísticas no entrenables).
> Sin pesos preentrenados (init `glorot_uniform`).

Topología: `Conv(32)→BN→ReLU→MaxPool → Conv(64)→BN→ReLU→MaxPool → Conv(128)→BN→ReLU→MaxPool → Conv(256)→BN→ReLU → GAP → Dense(128,ReLU) → Dropout(0.4) → Dense(1,Sigmoid)`.
Todas las Conv: 3×3, `padding="same"`, `use_bias=False`, `kernel_regularizer=L2(1e-4)`.

### VGG16 transfer — `tl_vgg16_malaria`

| | Fase BASE (backbone congelado) | Fase FINE-TUNING (últimas 4 capas) |
|---|---:|---:|
| Total | 15.241.025 | 15.241.025 |
| **Entrenables** | **526.337** | **7.605.761** |
| No entrenables | 14.714.688 | 7.635.264 |

- Head añadido: `GlobalAveragePooling2D → Dense(1024, ReLU) → Dropout(0.5) → Dense(1, Sigmoid)`
  (526.337 params = 525.312 de `Dense(1024)` + 1.025 de `Dense(1)`).
- Fine-tuning descongela `block5_conv1`, `block5_conv2`, `block5_conv3` (`block5_pool` no tiene pesos)
  → +7.079.424 params entrenables (3 × 2.359.808).
- Preentrenado: ImageNet. **Preprocesamiento real en las 12 corridas: `rescale_0_1` (÷255), no `vgg16.preprocess_input`.**

### DenseNet121 transfer — `tl_densenet121_malaria`

| | Fase BASE (backbone congelado) | Fase FINE-TUNING (últimas 4 capas) |
|---|---:|---:|
| Total | 7.038.529 | 7.038.529 |
| **Entrenables** | **1.025** | **39.937** |
| No entrenables | 7.037.504 | 6.998.592 |

- Head añadido: `GlobalAveragePooling2D → Dropout(0.5) → Dense(1, Sigmoid)` — **sin capa densa
  intermedia** (a diferencia de VGG16). Solo 1.025 params entrenables en fase base (1024·1 + 1).
- Capa interna no entrenable `densenet_imagenet_normalization` (`layers.Normalization`) que aplica
  `(x − mean)/std` de ImageNet sobre la entrada en `[0,1]`.
- El backbone se invoca con `training=False`; en fine-tuning solo se descongelan `conv5_block16_2_conv`
  (36.864) y la BN final `bn` (4.096 → 2.048 entrenables) de las últimas 4 capas
  → ~38.912 params entrenables extra. Las BN del backbone no actualizan estadísticas.
- Preentrenado: ImageNet.
