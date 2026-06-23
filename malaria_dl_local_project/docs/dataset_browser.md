# Menú Dataset

El menú **Dataset** del frontend muestra el origen del dataset de malaria, la
convención de etiquetas, el proceso de split físico y una grilla paginada para
explorar imágenes de entrenamiento, validación y prueba.

La fuente principal de datos es PostgreSQL. `metadata.json` solo se usa como
fallback para campos descriptivos cuando no están registrados en la base.

## Fuente Original

Fuente principal:

```text
https://www.tensorflow.org/datasets/catalog/malaria
```

Fuente NIH/NLM documentada:

```text
https://lhncbc.nlm.nih.gov/publication/pub9932
```

El dataset original de TensorFlow Datasets no se modifica. El proyecto genera
un split físico local para asegurar reproducibilidad.

## Convención Clínica

```text
0 = uninfected
1 = parasitized
raw_model_score = probability_parasitized
```

## Split Físico

Estructura esperada:

```text
data/
└── malaria_physical_split/
    ├── metadata.json
    ├── split_summary.csv
    ├── files_manifest.csv
    ├── train/
    │   ├── uninfected/
    │   └── parasitized/
    ├── val/
    │   ├── uninfected/
    │   └── parasitized/
    └── test/
        ├── uninfected/
        └── parasitized/
```

Distribución oficial:

```text
train = 80 %
val = 10 %
test = 10 %
```

El split fijo evita que cada entrenamiento use una división aleatoria distinta.
Esto permite comparar modelos con los mismos subconjuntos de imágenes.

## Registrar Metadata En BD

```bash
python scripts/register_physical_split_in_db.py \
  --dataset-dir data/malaria_physical_split \
  --dataset-name malaria_physical_split \
  --dataset-source tensorflow_datasets/malaria \
  --source-url https://www.tensorflow.org/datasets/catalog/malaria \
  --description "Dataset de imágenes microscópicas de células sanguíneas para clasificación malaria/no malaria." \
  --execute
```

También se puede registrar al crear el split:

```bash
python scripts/create_physical_dataset_split.py \
  --seed 42 \
  --train-ratio 0.8 \
  --val-ratio 0.1 \
  --test-ratio 0.1 \
  --register-db
```

## Backend

Endpoints:

```text
GET /api/dataset
GET /api/dataset/summary
GET /api/dataset/split
GET /api/dataset/images
GET /api/dataset/images?split=train&class_name=parasitized&page=1&page_size=24
GET /api/dataset/images/{image_id}
GET /api/dataset/images/{image_id}/file
```

El endpoint de archivo usa `image_id`; no acepta rutas arbitrarias. La ruta se
resuelve desde PostgreSQL y se valida para permanecer dentro de
`data/malaria_physical_split/`.

## Frontend

Ejecutar backend:

```bash
cd backend_api
uvicorn app.main:app --reload
```

Ejecutar frontend:

```bash
cd frontend
npm install
npm run dev
```

Abrir el menú:

```text
Dataset
```

Tabs disponibles:

```text
Descripción | Split físico | Entrenamiento | Validación | Prueba
```

Filtros de imágenes:

```text
split: train, val, test
class_name: all, uninfected, parasitized
page_size: 12, 24, 48, 96
```

## Consultas SQL

Resumen:

```sql
SELECT *
FROM vw_dataset_browser_summary
ORDER BY split_name, class_index;
```

Imágenes paginables:

```sql
SELECT
    image_id,
    split_name,
    class_name,
    class_index,
    filename,
    relative_path
FROM vw_dataset_browser_images
WHERE split_name = 'train'
  AND class_name = 'parasitized'
ORDER BY relative_path
LIMIT 24 OFFSET 0;
```
