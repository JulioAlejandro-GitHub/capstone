# U2 — U-Net Segmenter sobre pseudo-máscaras derivadas de tinción

```
U2 estado:   IMPLEMENTADO · VERIFICADO · SMOKE (PIPELINE VERIFICATION) APROBADO · NO ENTRENADO
TEST:        NO UTILIZADO
```

**No hay resultados científicos de U2 en este informe.** Hay una campaña activa: el worker usa ≈ 13,5 de los 16 núcleos del M4 Max, y este TensorFlow (2.17.1) no tiene GPU Metal, solo CPU. Según el punto 28 del brief, se preparó y verificó todo el ciclo, pero no se lanzó el entrenamiento completo. Las cifras de la sección "Smoke — PIPELINE VERIFICATION" solo verifican el pipeline; **no son resultados de U2**.

Pregunta científica: ¿puede una U-Net reproducir en VAL la representación espacial de `stain_morph` v2? No se pretende segmentación clínica del parásito.

## A. Dataset

- `dataset_version_id = d8c0cab5-09dd-597f-9de7-7ca01aee2ec2` (Malaria Patient Split v1).
- **TRAIN = 22.180** para entrenamiento y **VAL = 2.693** para seleccionar el checkpoint y evaluar en desarrollo.
- TEST (2.685) **no se lee**: `load_pseudo_mask_rows` rechaza `test` con `SPLIT_NOT_ALLOWED_IN_U2`, y ni siquiera carga esas filas del manifiesto en memoria.

## B. Pseudo-máscaras (identidad U1C, verificada por el loader en cada carga)

```
method stain_morph · version 2 · stain_delta 0.20
implementation_sha256  65603c61c4925345d83ca305e5d097514679e54b1aea0159e63bfac7f9be24e9
spec_sha256            4a84ad75d71dacf8f3d9c79d9de668ed57db176b09d2b265fd55c00ebbca078b
manifest_sha256        b79d701753b35e183e28316251f0b72268607cba3a86b231cd16e6c746548f7c
root                   data/derived/pseudo_masks/d8c0cab5-09dd-597f-9de7-7ca01aee2ec2/stain_morph_v2
git                    U1B 49f8618 · U1B.1 dc97fb1 · U1C f720d9f
```

El loader falla si no coinciden la versión del dataset, la identidad del generador (`generator.json`), el SHA-256 del manifiesto o los conteos de TRAIN y VAL. En modo completo también verifica el SHA-256 de cada máscara y de cada RGB contra el manifiesto.

## C. Arquitectura (`src/malaria_dl/models/unet/`)

```
blocks.py    conv_block(x, f)              (Conv2D 3x3 sin bias → BN → ReLU) × 2, nombres estables
             unet_encoder(x, (32,64,128), 256) → (bottleneck, skips)      200→100→50→25
             unet_decoder(bottleneck, skips)    ConvTranspose 2x2 s2 + concat(skip) + conv_block, ×3
builders.py  build_unet_segmenter()        Input(200,200,3) → encoder → decoder → Conv2D(1,1,sigmoid) "pseudo_mask"
losses.py    DiceLoss (registrada, serializable) + segmentation_report (métricas por imagen)
```

- Parámetros: **1.929.825**. Salida `(None, 200, 200, 1)`.
- `unet_encoder` devuelve `(bottleneck, skips)` para reutilizarse tal cual en el clasificador de encoder y en Multi-Task, sin una segunda U-Net.
- Los nombres de capa (`enc1_conv1`, …, `bottleneck_*`, `dec*`) son estables, para transferir pesos por nombre y apuntar Grad-CAM.
- Sin attention gates, residuales ni encoder preentrenado.
- No se modificó `architectures.py`, `registry.py`, `adapters.py` ni `loaders.py`.

## D. Loader (`src/malaria_dl/data/pseudo_mask_loader.py`)

- Pares tomados del manifiesto U1C, una fila por `source_record_id`. La máscara se resuelve por `source_record_id` y nunca por la clase.
- **RGB:** `decode_png(3)` → resize **bilinear** a 200×200 → `float32 / 255`. Es el mismo contrato que `rescale_0_1`. Sin preprocessing ImageNet ni DenseNet.
- **Máscara:** `decode_png(1)` → resize **nearest** a 200×200 → `float32 ∈ {0,1}`. Verificado: solo aparecen {0, 1}, y las 232 máscaras no vacías de 512 pares siguen no vacías tras el resize.
- **Augmentation pareada (solo TRAIN):** flip horizontal, flip vertical y `rot90` con k ∈ {0,1,2,3}, aplicados al tensor `concat([image, mask])`. Por construcción, la geometría es idéntica para ambos. Usa semillas *stateless* derivadas de `random_seed`. Sin transformaciones fotométricas.

## E. Loss (fórmula exacta)

```
D = (2 · Σ_b,i y·p + ε) / (Σ_b,i y + Σ_b,i p + ε)        L = 1 − D        ε = 1.0
```

- Las sumas recorren **todos los píxeles de todas las imágenes del batch** (Dice de batch, no por imagen).
- Un target vacío no aporta al numerador ni a Σy, pero cada probabilidad que predice suma a Σp. Los falsos positivos sobre targets vacíos se penalizan, y un target vacío nunca recibe un Dice de 1 gratis.
- ε = 1 píxel es despreciable frente a los ≈ 390 píxeles de foreground de un target no vacío típico.
- Comportamiento verificado: vacío/vacío = 0,000; vacío con 100 px de falso positivo = 0,995; perfecto = 0,000; no vacío frente a todo negro = 0,998.

## F. Configuración de entrenamiento (`train_u2.py`, constante `CONFIG`)

| Parámetro | Valor |
|---|---|
| input_size | 200 |
| filters / bottleneck_filters | (32, 64, 128) / 256 |
| batch_size | 16 |
| optimizer / learning_rate | Adam / 1e-3 |
| max_epochs / early_stopping_patience | 40 / 8 (restore_best_weights) |
| loss | DiceLoss (batch, ε = 1) |
| prediction_threshold / regla de predicción vacía | 0,5 / 0 píxeles ≥ 0,5 |
| checkpoint_monitor / mode | `val_dice_pooled_pixels` / max |
| early_stopping_monitor | `val_dice_pooled_pixels` |
| augmentation | pareada: flips H/V + rot90 |
| pseudo-máscara | stain_morph v2, manifest b79d7017…f7c (completo en B) |
| dataset_version_id / random_seed | d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 / 42 |

Es una configuración única, sin sweep. Cada corrida escribe `config.json` con estos valores, más el número de parámetros y los registros efectivos.

## G. Selección de checkpoint

**Monitor: `val_dice_pooled_pixels`**, el Dice duro (umbral 0,5) acumulado sobre todos los píxeles de VAL: `2·Σ(T∧P) / (ΣT + ΣP)`. Lo calcula un callback que predice VAL al final de cada época y escribe el valor en los logs **antes** de `ModelCheckpoint` y `EarlyStopping`.

Por qué no `val_dice_nonempty`, que era la sugerencia del brief: la primera corrida de smoke, con ese monitor, **seleccionó una época que marcaba foreground en el 100 % de las imágenes** (63/63 targets vacíos con falso positivo). `dice_nonempty` no ve las imágenes vacías y premia "pintar todo".

El Dice acumulado sigue favoreciendo la calidad sobre targets no vacíos, porque solo ellos aportan al numerador, y a la vez penaliza cada píxel predicho en una imagen vacía. Todo negro da 0 y todo positivo da ≈ 0. `dice_nonempty` se mantiene como **métrica principal reportada**.

**Regla:** el monitor (`val_dice_pooled_pixels`, mode `max`) queda aprobado y fijado antes del entrenamiento completo. No se cambiará después de observar ese entrenamiento, salvo que se demuestre un error de implementación. El monitor solo selecciona el checkpoint. No reemplaza las métricas del informe:

- resultados principales: `dice_nonempty` e `iou_nonempty`;
- siempre acompañados de `dice_all`, `iou_all`, `dice_pooled_pixels`, `target_empty_count`, `target_nonempty_count`, `predicted_empty_count`, `empty_target_correct_empty`, `empty_target_false_positive` y `nonempty_target_predicted_empty`.

El checkpoint se guarda en formato `.keras` y se **recarga con `safe_mode` por defecto (True)** antes de evaluar. `DiceLoss` está registrada con `register_keras_serializable(package="malaria_unet")`. Al final se registran ruta, SHA-256, época seleccionada, monitor y valor.

## H. Resultados VAL

**Pendientes: el entrenamiento no se ejecutó.** `results.json` producirá esta tabla:

| Métrica | Resultado |
|---|---:|
| Dice ALL / IoU ALL (por imagen; vacío∧vacío = 1) | pendiente |
| Dice NON-EMPTY / IoU NON-EMPTY (por imagen) | pendiente |
| Dice / IoU acumulados sobre píxeles | pendiente |
| Target empty / non-empty | 1.451 / 1.242 (conocidos por U1C) |
| Predicted empty | pendiente |
| Correct empty / Empty false positive | pendiente |
| Non-empty predicted empty / Non-empty con solapamiento 0 | pendiente |

## I. Baseline all-black — VAL (CONGELADO antes del entrenamiento)

```
ALL-BLACK BASELINE — VAL
target empty:                 1451
target non-empty:             1242
correct empty:                1451 / 1451
Dice ALL:                     0.539
Dice NON-EMPTY:               0
Dice pooled pixels:           0
non-empty predicted empty:    1242 / 1242
```

Queda fijado antes de observar cualquier resultado del entrenamiento U2.

Se calcula con los conteos sellados de U1C (VAL: 1.451 vacías, 1.242 no vacías):

| Métrica | All-black |
|---|---:|
| Correct empty | 1.451 / 1.451 (100 %) |
| Dice ALL (por imagen) | 1.451 / 2.693 = **0,539** |
| Dice NON-EMPTY / IoU NON-EMPTY | **0 / 0** |
| Dice acumulado (monitor) | **0** |
| Non-empty predicted empty | 1.242 / 1.242 |

Un Dice ALL de 0,54 sin aprender nada muestra por qué ese número solo engaña. La U-Net solo aporta algo si **Dice NON-EMPTY ≫ 0** con pocos falsos positivos en targets vacíos. `train_u2.py` recalcula este baseline sobre las mismas predicciones de VAL (`val_baseline_all_black`).

## J. Visualización

- `val_panel.png` de cada corrida, con 2 ejemplos por categoría: vacío→vacío, vacío→falso positivo, no vacío→localizado (mejor Dice) y no vacío→fallado (peor Dice). Columnas: RGB, TARGET, PRED y OVERLAY.
- Panel del smoke: `results/u2/smoke/val_panel.png`. Muestra el ciclo, no un resultado.

## Smoke — PIPELINE VERIFICATION (no es un experimento científico)

- 256 imágenes TRAIN y 128 VAL, 2 épocas, 2 hilos, `nice 19`.
- Funcionó todo el ciclo: fit, callback de VAL, checkpoint, recarga `safe_mode`, evaluación, baseline y panel.
- Velocidad bajo la campaña: **≈ 6 s por paso (batch 16)**. Una época completa (1.387 pasos) llevaría ≈ 2,3 h, así que entrenar ahora no es viable sin competir con la campaña.
- Sin la campaña, con los 16 hilos, la estimación gruesa es de decenas de minutos por época. Se medirá al lanzar.
- **Qué permitió detectar:** con `val_dice_nonempty` como monitor, el smoke seleccionó una época con foreground en el 100 % de las imágenes (63/63 targets vacíos con falso positivo). Esa debilidad se corrigió **antes** del entrenamiento completo, cambiando el monitor a `val_dice_pooled_pixels` (sección G).
- Evidencia en `results/u2/smoke/`: `results.json`, `config.json`, `history.csv` y `val_panel.png`. Corresponde a la corrida final con `val_dice_pooled_pixels`; la corrida anterior con `val_dice_nonempty` solo queda documentada aquí.

Verificaciones funcionales (punto 27): `scripts/experiments/unet_segmenter/verify_u2.py`. Salida en `results/u2/verify_u2.txt`, **12/12 PASS**:

- el modelo construye, con salida `(None,200,200,1)`;
- el loader rechaza TEST;
- el manifiesto está sellado y los conteos son correctos;
- imagen `float32 (B,200,200,3)` ∈ [0,1];
- máscara `float32 (B,200,200,1)` ∈ {0,1};
- la augmentation pareada mantiene la alineación (40 semillas);
- forward y backward funcionan;
- save/reload en `safe_mode` da predicciones idénticas;
- el monitor acumulado da 0 con todo negro y penaliza marcar foreground en todas las imágenes.

## K. Persistencia

Por ahora todo queda en archivos. Cada corrida escribe en su directorio `config.json`, `history.csv`, `best.keras`, `results.json` y `val_panel.png`. La evidencia pequeña se versiona; el checkpoint (≈ 23 MB) no.

Propuesta de reutilización en PostgreSQL, sin migraciones, **después** de la campaña:

1. **`public.models`:** una fila `name = unet_segmenter`, `model_type = segmentation`, `architecture = U-Net`, `framework = tensorflow/keras`. `model_type` es texto libre. `registered_models()` lee esta tabla, así que la fila **no se inserta durante la campaña**. Tampoco se registra en `MODEL_REGISTRY` ni en los adapters: el contrato `(None,1) sigmoid` de `compile_phase` no aplica a un segmentador.
2. **`runs`:** una fila `run_type = training` con `model_id` hacia esa fila, `dataset_version_id`, `checkpoint_monitor`, `best_epoch`, `best_validation_value`, `parameters` (el `CONFIG`) y `git_commit`.
3. **`run_metrics`** (EAV): `dice_nonempty`, `iou_nonempty`, `dice_all`, `iou_all`, `dice_pooled_pixels`, `predicted_empty_count`, `empty_target_false_positive`, `nonempty_target_predicted_empty`, …, con `split_name = 'val'`. El check `ck_v2_extension_only` solo prohíbe nombres clínicos binarios, así que estos nombres son válidos sin migración.
4. **`artifacts`:** el checkpoint como `artifact_type = model_checkpoint` **con `run_id`**. Es la semántica actual de la tabla (todos sus registros son checkpoints de un run), así que no se rompe.
5. **No usar `evaluations` ni `run_clinical_metrics`:** están atadas a métricas binarias de clasificación (`metric_definition = binary_nullable_v2`).

## L. Git

Commit de preparación sobre `f720d9f` (U1C), en la rama `exp/u2-unet-segmenter`. `main` no se modificó.

## M. TEST

**TEST NO UTILIZADO.** No se leyeron filas, imágenes ni pseudo-máscaras de TEST. No se calcularon métricas ni predicciones sobre TEST. El loader lo impide por diseño.

## N. Decisión

**¿U-Net aprendió una representación espacial no trivial de `stain_morph` v2? NO DETERMINADO.** Esta conclusión solo podrá establecerse después del entrenamiento completo.

Criterio fijado **antes** del entrenamiento. La evaluación considerará conjuntamente:

- Dice NON-EMPTY;
- IoU NON-EMPTY;
- Dice acumulado sobre píxeles;
- `nonempty_target_predicted_empty`;
- `empty_target_false_positive`;
- el baseline all-black congelado (sección I).

**No se definirá después un único umbral de Dice** para convertir el resultado en éxito. La conclusión dependerá de si existe aprendizaje espacial **claramente superior a las soluciones degeneradas documentadas**: todo negro (Dice NON-EMPTY 0; 1.242/1.242 no vacías predichas vacías) y foreground en todas partes (falsos positivos en casi todos los targets vacíos; Dice acumulado ≈ 0).

**El entrenamiento completo no se iniciará mientras la campaña activa use la CPU de forma intensiva.** No se modificará la afinidad, la prioridad ni los recursos de la campaña.

Para lanzar el entrenamiento, una vez que la campaña termine o libere CPU:

```bash
python scripts/experiments/unet_segmenter/train_u2.py \
  --data-root malaria_dl_local_project/data --out <run dir fuera del árbol de la campaña>
```
