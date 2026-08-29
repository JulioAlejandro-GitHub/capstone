# Guía de Entrenamiento y Evaluación con Patient-Disjoint Split

> **Estado documental: CURRENT_DOC / GUÍA CIENTÍFICA.** Toda ejecución ocurre dentro
> del servicio Compose `backend`, que recibe `DATABASE_URL` hacia `db:5432`.
> El contrato operativo canónico es [PostgreSQL Docker-only](engineering/postgresql_docker_single_instance.md).

Esta guía detalla el flujo para entrenar, evaluar y explicar modelos de Deep Learning
con el split gobernado **`Malaria Patient Split v1`**
(`d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`). La versión está `FROZEN`, es entrenable y
garantiza separación patient-disjoint. No debe rematerializarse ni modificarse.

---

## 1. Configuración del Entorno

Asegúrate de que el runtime Docker-only esté disponible:

```bash
docker compose up -d
docker compose ps
make db-status
```

> [!IMPORTANT]
> Backend, ML y CLI de split reciben la misma `DATABASE_URL` desde Compose. Los
> comandos Python mostrados más abajo describen argumentos científicos y deben
> ejecutarse dentro del servicio `backend`, nunca con Python del host.

---

## 2. Verificar el Dataset Gobernado Activo

Antes de entrenar, verifica desde Python que PostgreSQL exponga la versión gobernada
oficial como entrenable:

```bash
python - <<'PY'
from src.malaria_dl.data.governed_dataset import list_trainable_dataset_versions, resolve_governed_dataset

versions = list_trainable_dataset_versions()
print("Versiones entrenables activas en BD:", versions)

snapshot = resolve_governed_dataset()
print("\nSnapshot del dataset resuelto:")
print(f"  ID Versión: {snapshot.dataset_version_id}")
print(f"  Ruta física: {snapshot.dataset_root}")
print(f"  Distribución en disco: {snapshot.counts}")
PY
```

**Resultado esperado:**
* El ID de versión resuelto automáticamente debe ser `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`.
* La ruta física debe apuntar a la materialización del nuevo split: `data/malaria_dataset_versions/d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`.

---

## 3. Entrenamiento de Modelos

Puedes entrenar modelos individuales o ejecutar la grilla completa de experimentos
en lote. Con `--track-db`, cada ejecución registra parámetros, curvas de aprendizaje,
checkpoints, métricas y `dataset_version_id` en `malaria_experiments`.

### Opción A: Entrenar un Modelo Individual

Usa el script `src.train` especificando el ID del split gobernado mediante `--dataset-version-id`:

* **Custom CNN**:
  ```bash
  python -m src.train \
    --model custom_cnn \
    --max-epochs 50 \
    --img-size 200 \
    --batch-size 64 \
    --calibrate-threshold \
    --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 \
    --track-db
  ```

* **VGG16 con Transfer Learning & Fine-tuning**:
  ```bash
  python -m src.train \
    --model vgg16 \
    --max-epochs 30 \
    --fine-tune-epochs 10 \
    --img-size 200 \
    --batch-size 64 \
    --calibrate-threshold \
    --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 \
    --track-db
  ```

* **DenseNet121**:
  ```bash
  python -m src.train \
    --model densenet121 \
    --max-epochs 30 \
    --fine-tune-epochs 6 \
    --img-size 200 \
    --batch-size 64 \
    --calibrate-threshold \
    --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 \
    --track-db
  ```

> [!IMPORTANT]
> Para máxima reproducibilidad se recomienda declarar `--dataset-version-id`. Si se
> omite, el resolver ML v1 exige `FROZEN`, materialización `READY/PASS` y los 12 checks
> requeridos más recientes en `PASS`; selecciona la versión elegible más reciente,
> persiste su UUID en el TRAIN y falla si no existe ninguna. La lista de 12 checks es
> explícita y no incorpora automáticamente checks bloqueantes futuros ajenos a ella.
> Nunca usa `malaria_physical_split` como fallback silencioso.

### Opción B: Entrenamiento en Lote (Orquestador de Grilla)

Para ejecutar de manera secuencial los entrenamientos de todos los modelos (`custom_cnn`, `vgg16`, `densenet121`) combinados con todos los optimizadores configurados (`adam`, `adamw`, `sgd`, `adadelta`), utiliza el script orquestador:

```bash
python run_train_all_models.py \
  --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2
```

El orquestador activa internamente `--calibrate-threshold`; en los comandos
individuales el flag es explícito porque la calibración no está habilitada por
defecto.

---

## 4. Evaluación de Modelos y Linaje de Datos

Una vez completados los entrenamientos, evalúa los modelos resultantes sobre la
partición de prueba (`test`). El threshold se calibra antes, exclusivamente con
`validation`, durante TRAIN cuando se usa `--calibrate-threshold`. EVALUATE consume
ese threshold clínico persistido y calcula en `test` sensibilidad (Recall),
especificidad y F2-score; no recalibra con muestras de prueba.

Para evaluar de manera automática todos los entrenamientos exitosos registrados en la base de datos, ejecuta:

```bash
python run_evaluate_all_trainings.py \
  --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2
```

> [!NOTE]
> El filtro anterior limita el inventario a TRAIN vinculados a v1. Por cada run, el
> evaluador vuelve a resolver `runs.dataset_version_id` y rechaza una identidad
> distinta. No omitas el filtro en este runbook: sin él, el wrapper también inventariaría
> TRAIN históricos con `dataset_version_id IS NULL`, que no acreditan linaje gobernado.

---

## 5. Generación de Explicabilidad Visual (LIME, SHAP y Grad-CAM)

El último paso del flujo experimental es generar mapas de explicabilidad para las
predicciones en los casos de prueba (verdaderos positivos, falsos positivos, falsos
negativos y casos de baja certeza).

Para procesar y exportar las explicaciones visuales de todos los modelos completados:

```bash
python run_explain_all_trainings.py \
  --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2
```

Las imágenes explicadas y los mapas de calor de Grad-CAM se exportarán a la estructura del sistema de archivos en:
```text
outputs/explainability/
  gradcam/
  lime/
  shap/
```

`outputs/explainability/` es un workspace compartido de última ejecución, no un
reporte consolidado del batch. Cada subproceso vuelve a escribir
`explanation_summary.csv` y puede reemplazar archivos homónimos de un modelo anterior.
No usar ese directorio como evidencia acumulativa.

Cuando sea necesario conservar evidencia separada por TRAIN, ejecutar el CLI de un
run con IDs gobernados y un output exclusivo:

```bash
TRAIN_UUID=00000000-0000-4000-8000-000000000000
MODEL_VERSION_UUID=00000000-0000-4000-8000-000000000000

python -m src.explain \
  --model-version-id "$MODEL_VERSION_UUID" \
  --source-training-run-id "$TRAIN_UUID" \
  --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 \
  --method all \
  --threshold clinical \
  --output-dir "outputs/explainability/$TRAIN_UUID" \
  --track-db \
  --require-lineage
```

Sustituir ambos UUID de ejemplo por el par real del mismo TRAIN antes de ejecutar.

---

## 6. Monitoreo en el Dashboard Web

Una vez que los comandos de entrenamiento, evaluación y explicabilidad hayan
finalizado dentro del servicio `backend`, abra la URL publicada por el servicio
Compose `frontend`. El valor de desarrollo habitual es:

```text
http://localhost:5173/
```

No asumas el puerto 80 de Nginx/Compose para la operación local canónica.

Desde el panel de administración web podrás:
1. Comparar las curvas de entrenamiento, pérdidas y precisión de cada ejecución.
2. Analizar el impacto de la separación de pacientes y verificar que no haya solapamiento.
3. Auditar la matriz de confusión, el F2-score calibrado y los artefactos/checkpoints inmutables (`.keras`).
4. Visualizar casos e imágenes explicados mediante Grad-CAM como evidencia experimental, no diagnóstica.
