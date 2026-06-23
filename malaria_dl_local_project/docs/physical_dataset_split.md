# Split físico del dataset malaria

El flujo oficial del proyecto usa un split físico persistente para que `custom_cnn`, `vgg16`, evaluación, explicabilidad, TTA, ensemble y SVM trabajen sobre exactamente las mismas imágenes.

## Flujo oficial

```text
TFDS malaria original
  -> scripts/create_physical_dataset_split.py
  -> data/malaria_physical_split/
  -> train/evaluate/explain/tta/ensemble/svm_features
```

El script lee TensorFlow Datasets y exporta copias de las imágenes. No elimina, modifica ni sobrescribe el dataset original de TFDS.

## Convención de etiquetas

```text
0 = uninfected
1 = parasitized
raw_model_score = probability_parasitized
label_mapping_version = clinical_v1_parasitized_positive
```

TFDS puede entregar `0 = parasitized` y `1 = uninfected`; el split físico se exporta con la convención clínica del proyecto.

## Crear el split

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

## Estructura generada

```text
data/malaria_physical_split/
  metadata.json
  split_summary.csv
  files_manifest.csv
  train/
    uninfected/
    parasitized/
  val/
    uninfected/
    parasitized/
  test/
    uninfected/
    parasitized/
```

`metadata.json` documenta seed, ratios, conteos y mapping de etiquetas. `files_manifest.csv` permite trazar cada archivo exportado a su índice y etiqueta TFDS original.

## Uso en scripts

Por defecto, los scripts usan:

```text
--data-source physical
--dataset-dir data/malaria_physical_split
```

El fallback dinámico de TFDS queda disponible solo de forma explícita:

```bash
python -m src.train --model custom_cnn --data-source tfds
```

Ese modo se considera legacy/experimental para comparaciones, no el flujo oficial.

## Comandos principales

Entrenar `custom_cnn`:

```bash
python -m src.train \
  --model custom_cnn \
  --epochs 30 \
  --img-size 200 \
  --batch-size 64 \
  --track-db
```

Entrenar `vgg16`:

```bash
python -m src.train \
  --model vgg16 \
  --epochs 30 \
  --fine-tune-epochs 10 \
  --img-size 200 \
  --batch-size 64 \
  --track-db
```

Evaluar:

```bash
python -m src.evaluate \
  --checkpoint outputs/vgg16/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --track-db
```

Explicabilidad:

```bash
python -m src.explain \
  --checkpoint outputs/vgg16/best_model.keras \
  --method gradcam \
  --num-samples 20 \
  --positive-label parasitized \
  --track-db
```

Si falta `data/malaria_physical_split/`, los loaders fallan con un mensaje que indica ejecutar `python scripts/create_physical_dataset_split.py`.
