

Run paso a paso


```bash
cd malaria_dl_local_project
source .venv/bin/activate
```

1. Verificar PostgreSQL y migraciones
```bash
python scripts/init_db.py
```

2. Purga limpia de datos experimentales
Esto limpia outputs experimentales y datos de tracking según el script de reset.
```bash
python scripts/reset_experimental_state.py \
  --execute \
  --confirm RESET_EXPERIMENTS \
  --backup-before
```

3. Crear o validar split físico

```bash
python scripts/create_physical_dataset_split.py \
  --seed 42 \
  --train-ratio 0.8 \
  --val-ratio 0.1 \
  --test-ratio 0.1 \
  --overwrite \
  --register-db
```

Si el split ya existe, registra sus imágenes en BD:

```bash
python scripts/register_physical_split_in_db.py \
  --dataset-dir data/malaria_physical_split \
  --dataset-name malaria_physical_split \
  --dataset-source tensorflow_datasets/malaria \
  --source-url https://www.tensorflow.org/datasets/catalog/malaria \
  --description "Dataset de imágenes microscópicas de células sanguíneas para clasificación malaria/no malaria." \
  --execute
```

4. Entrenar Custom CNN
```bash
python -m src.train \
  --model custom_cnn \
  --epochs 30 \
  --img-size 200 \
  --batch-size 64 \
  --track-db
```

5. Entrenar VGG16
```bash
python -m src.train \
  --model vgg16 \
  --epochs 30 \
  --fine-tune-epochs 10 \
  --img-size 200 \
  --batch-size 64 \
  --track-db
```

6. Evaluar ambos modelos
```bash
python -m src.evaluate \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --track-db
```

```bash
python -m src.evaluate \
  --checkpoint outputs/vgg16/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --track-db
```

7. Calibrar modelos

```bash
python -m src.calibrate \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --track-db
```

```bash
python -m src.calibrate \
  --checkpoint outputs/vgg16/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --track-db
```

8. Ejecutar SVM con features CNN
```bash
python -m src.svm_features \
  --checkpoint outputs/vgg16/best_model.keras \
  --img-size 200 \
  --batch-size 64 \
  --gamma 0.1 \
  --track-db
```

9. Ejecutar ensemble

```bash
python -m src.ensemble \
  --models outputs/custom_cnn/best_model.keras outputs/vgg16/best_model.keras \
  --weights 0.4 0.6 \
  --img-size 200 \
  --batch-size 64 \
  --track-db
```

10. Ejecutar TTA

```bash
python -m src.tta \
  --checkpoint outputs/vgg16/best_model.keras \
  --img-size 200 \
  --n-aug 8 \
  --track-db
```

11. Ejecutar explicabilidad

```bash
python -m src.explain \
  --checkpoint outputs/vgg16/best_model.keras \
  --method all \
  --num-samples 50 \
  --positive-label parasitized \
  --track-db
```

```bash
python -m src.explain \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --method all \
  --num-samples 50 \
  --positive-label parasitized \
  --track-db
```

12. Levantar visualización
Backend:
```bash
cd ../backend_api
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Frontend:
```bash
cd ../frontend
npm run dev
```
