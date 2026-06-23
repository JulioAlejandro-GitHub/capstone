# Trazabilidad de Dataset Físico en PostgreSQL

Este proyecto registra el split físico imagen por imagen para auditar qué datos
participaron en cada entrenamiento, evaluación e inferencia experimental.

Convención clínica guardada en los registros:

```text
0 = uninfected
1 = parasitized
raw_model_score = probability_parasitized
```

## Tablas

`dataset_split_images` guarda una fila por imagen física del split:

```text
dataset_dir, split_name, class_name, class_index, relative_path, filename,
original_tfds_label, project_label, label_mapping_version, dimensiones,
tamaño, checksum_sha256 opcional y metadata JSONB.
```

`run_dataset_images` vincula un `run_id` con las imágenes usadas:

```text
run_id, image_id, split_name, usage_context, class_name, class_index,
relative_path, sample_index, batch_index, flags de uso y metadata JSONB.
```

`run_io_records` guarda entrada/salida de cada comando:

```text
script_name, command, input_parameters, output_results, output_artifacts,
dataset_metadata, label_mapping_version y raw_model_score_meaning.
```

## Registrar El Split

Dry-run:

```bash
python scripts/register_physical_split_in_db.py \
  --dataset-dir data/malaria_physical_split \
  --dataset-name malaria_physical_split \
  --dataset-source tensorflow_datasets/malaria
```

Registro real:

```bash
python scripts/register_physical_split_in_db.py \
  --dataset-dir data/malaria_physical_split \
  --dataset-name malaria_physical_split \
  --dataset-source tensorflow_datasets/malaria \
  --execute
```

Al crear el split físico también se puede registrar:

```bash
python scripts/create_physical_dataset_split.py \
  --seed 42 \
  --train-ratio 0.8 \
  --val-ratio 0.1 \
  --test-ratio 0.1 \
  --register-db
```

## Ejecuciones Con Tracking

Con `--track-db`, estos comandos registran parámetros, resultados, artefactos e
imágenes usadas:

```bash
python -m src.train --model custom_cnn --epochs 30 --img-size 200 --batch-size 64 --track-db
python -m src.evaluate --checkpoint outputs/custom_cnn/best_model.keras --img-size 200 --batch-size 64 --track-db
python -m src.explain --checkpoint outputs/custom_cnn/best_model.keras --method gradcam --num-samples 20 --positive-label parasitized --track-db
python -m src.tta --checkpoint outputs/vgg16/best_model.keras --n-aug 8 --track-db
python -m src.ensemble --models outputs/custom_cnn/best_model.keras outputs/vgg16/best_model.keras --weights 0.4 0.6 --track-db
python -m src.svm_features --checkpoint outputs/vgg16/best_model.keras --img-size 200 --batch-size 64 --gamma 0.1 --track-db
```

`src.predict_image` mantiene el tracking de imagen externa en `predictions` y
`artifacts`, y además registra su IO en `run_io_records`.

## Consultas

Resumen del split físico:

```sql
SELECT *
FROM vw_dataset_split_images_summary
ORDER BY split_name, class_name;
```

Uso de dataset por run:

```sql
SELECT *
FROM vw_run_dataset_usage_summary
WHERE run_id = '00000000-0000-0000-0000-000000000000';
```

Parámetros y resultados:

```sql
SELECT
    run_id,
    script_name,
    input_parameters,
    output_results
FROM vw_run_io_summary
ORDER BY created_at DESC
LIMIT 10;
```

Imágenes usadas por un entrenamiento:

```sql
SELECT
    rdi.run_id,
    rdi.split_name,
    rdi.class_name,
    rdi.filename,
    rdi.relative_path
FROM run_dataset_images rdi
WHERE rdi.run_id = '00000000-0000-0000-0000-000000000000'
ORDER BY rdi.split_name, rdi.class_name, rdi.filename;
```

## Migración

La migración nueva es:

```text
db/init/012_dataset_split_image_tracking.sql
```

Se usa `012` porque `011_label_mapping_clinical_v1.sql` ya existe. Las tablas y
vistas son idempotentes para que `python scripts/init_db.py` pueda ejecutarse más
de una vez.
