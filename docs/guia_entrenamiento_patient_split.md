# Guía de Entrenamiento y Evaluación con Patient-Disjoint Split

Esta guía detalla el flujo de trabajo para entrenar, evaluar y explicar los modelos de Deep Learning utilizando el nuevo split gobernado **`Malaria Patient Split v1`** (`d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`), el cual garantiza la separación de pacientes disjuntos (patient-disjoint) para evitar fugas de datos (data leakage).

---

## 1. Configuración del Entorno

Asegúrate de estar en el directorio correcto y con el entorno virtual activo:

```bash
# Cambiar al directorio del proyecto de Deep Learning
cd malaria_dl_local_project

# Activar el entorno virtual
source .venv/bin/activate

# Configurar las variables de entorno para que apunten al PostgreSQL de Docker
export PYTHONPATH=src
export DATABASE_URL='postgresql+psycopg://julio:root@127.0.0.1:5432/malaria_experiments'
```

> [!IMPORTANT]
> Para que el puerto `5432` enrute correctamente al contenedor de Docker (`capstone_db`), la instancia de Postgres local de macOS (Homebrew) debe estar apagada. Si no lo has hecho, detenla con:
> ```bash
> launchctl unload ~/Library/LaunchAgents/homebrew.mxcl.postgresql@17.plist
> ```

---

## 2. Verificar el Dataset Gobernado Activo

Antes de entrenar, puedes verificar desde Python que la base de datos de Docker exponga correctamente el split que acabamos de congelar como la versión entrenable activa:

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

Puedes entrenar modelos individuales o ejecutar la grilla completa de experimentos en lote. Al usar `--track-db`, cada ejecución registrará sus parámetros, curvas de aprendizaje, checkpoints y métricas en la base de datos PostgreSQL de Docker.

### Opción A: Entrenar un Modelo Individual

Usa el script `src.train` especificando el ID del split gobernado mediante `--dataset-version-id`:

* **Custom CNN**:
  ```bash
  python -m src.train \
    --model custom_cnn \
    --max-epochs 50 \
    --img-size 200 \
    --batch-size 64 \
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
    --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2 \
    --track-db
  ```

> [!TIP]
> Si omites la bandera `--dataset-version-id`, el sistema resolverá de forma automática la versión `FROZEN` más reciente registrada en la base de datos (que corresponderá al nuevo split de pacientes).

### Opción B: Entrenamiento en Lote (Orquestador de Grilla)

Para ejecutar de manera secuencial los entrenamientos de todos los modelos (`custom_cnn`, `vgg16`, `densenet121`) combinados con todos los optimizadores configurados (`adam`, `adamw`, `sgd`, `adadelta`), utiliza el script orquestador:

```bash
python run_train_all_models.py \
  --dataset-version-id d8c0cab5-09dd-597f-9de7-7ca01aee2ec2
```

---

## 4. Evaluación de Modelos y Linaje de Datos

Una vez completados los entrenamientos, debes evaluar los modelos resultantes sobre la partición de prueba (`test`). El pipeline clínico requiere el cálculo de sensibilidad (Recall), especificidad, F2-score y la calibración del umbral.

Para evaluar de manera automática todos los entrenamientos exitosos registrados en la base de datos, ejecuta:

```bash
python run_evaluate_all_trainings.py
```

> [!NOTE]
> **Trazabilidad Garantizada**: El script `run_evaluate_all_trainings.py` consulta la base de datos y recupera el dataset exacto con el que fue entrenado cada modelo (`dataset_version_id`). La evaluación se realiza utilizando rigurosamente ese mismo linaje de datos de forma automática.

---

## 5. Generación de Explicabilidad Visual (LIME, SHAP y Grad-CAM)

El último paso del flujo de modelado clínico es la generación de mapas de explicabilidad para las predicciones en los casos de prueba (Verdaderos Positivos, Falsos Positivos, Falsos Negativos y casos de baja certeza).

Para procesar y exportar las explicaciones visuales de todos los modelos completados:

```bash
python run_explain_all_trainings.py
```

Las imágenes explicadas y los mapas de calor de Grad-CAM se exportarán a la estructura del sistema de archivos en:
```text
outputs/explainability/
  gradcam/
  lime/
  shap/
```
Y el reporte consolidado se guardará en `outputs/explainability/explanation_summary.csv` con tracking en base de datos.

---

## 6. Monitoreo en el Dashboard Web

Una vez que los comandos de entrenamiento, evaluación y explicabilidad hayan finalizado, abre tu navegador en:

```text
http://localhost/
```

Desde el panel de administración web podrás:
1. Comparar las curvas de entrenamiento, pérdidas y precisión de cada ejecución.
2. Analizar el impacto de la separación de pacientes y verificar que no haya solapamiento.
3. Auditar la matriz de confusión, el F2-score clínico calibrado, y descargar los artefactos/checkpoints inmutables (`.keras`).
4. Visualizar los frotis explicados mediante Grad-CAM para validar las zonas celulares de atención de la IA.
