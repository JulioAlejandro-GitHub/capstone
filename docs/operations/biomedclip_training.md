# BiomedCLIP Linear Probing y Fine-tuning

Estado: CURRENT_DOC. 2026-10-27. Complementa [incorporación Zero-Shot](zero_shot_incorporation.md).

## Modelos

| `public.models.name` | `model_type` | Encoder | Pregunta científica |
|---|---|---|---|
| `biomedclip_linear` | `linear_probe` | congelado; embeddings TRAIN/VAL extraídos una vez por RUN | calidad de las representaciones |
| `biomedclip_fine_tuning` | `fine_tuning` | fase `base`: cabeza; fase `fine_tuning`: últimos `fine_tune_layers` bloques ViT (1–12; 12 = total) | capacidad de adaptación a malaria |

Ambos usan `framework=pytorch_openclip` y una cabeza `Linear(512→1)` con sigmoide, BCE con logits, sobre el
embedding proyectado y normalizado L2 del encoder visual. La base es la versión `3fd16a84…` de
`biomedclip_zero_shot`: `recipe.base_model` identifica sus cinco archivos por SHA-256 y tamaño, y se
resuelven desde `artifacts` en cada carga. Configuración versionada: `configs/models/biomedclip_*.json`
(esquema `model_config_v1`); contrato de entrada `openclip_supervised_input_v1`, entrada fija 224.

## Ejecución local en GPU

Las campañas se crean desde la UI de campañas como cualquier modelo. TRAIN corre en el Mac con MPS:

```sh
cd malaria_dl_local_project
bash setup_venvs.sh torch            # una vez: .venv-torch, separado de .venv-metal
python -m src.train --campaign-id <campaña>
```

El coordinador puede ejecutarse desde `.venv-metal` o `.venv-torch`: cada TRAIN y cada carga de
verificación de checkpoint se lanza con el intérprete del entorno de su framework
(`local_launch.framework_python`). `.venv-torch` no instala TensorFlow ni `.venv-metal` PyTorch.
MPS es obligatorio (`TORCH_MPS_REQUIRED`, sin fallback a CPU). La lectura de imágenes usa un pool de
hilos con prefetch: el proceso TRAIN no deja procesos descendientes para la compuerta global.

## Evidencia

`execution/train_torch.py` emite los mismos registros y eventos E10 que el motor Keras (runtime, epoch,
artifact, selection, predictions, phase, calibration, completion), con las mismas políticas de selección,
EarlyStopping (semántica Keras 3, restauración al fin de fase), ReduceLROnPlateau sobre `val_loss` y
calibración VAL. TEST nunca se abre. Cada época guarda `outputs/campaign_runs/<run_id>/epoch_N.pt` con
**sólo** los parámetros entrenados y la identidad de la base (≈5 KB lineal; ≈115 MB con 4 bloques;
≈344 MB total). Optimizadores: los cuatro del catálogo con equivalencia explícita; opciones sólo-Keras
(`clipnorm`, EMA, `weight_decay` fuera de AdamW…) se rechazan si no tienen su valor por defecto.

EVALUATE/TEST/EXPLAIN usan los comandos habituales desde `.venv-torch` (umbral `auto`/`clinical` desde
la calibración del TRAIN; EXPLAIN `lime`/`shap`; `gradcam` no aplica a ViT). La activación para
clasificación celular registra la versión con `framework=pytorch_openclip` y el backend carga base y
cabeza en CPU.

## PostgreSQL

[biomedclip_trainable_models.sql](../../scripts/sql/biomedclip_trainable_models.sql): `models.name`
único; `run_configurations.architecture` pasa de lista cerrada a FK a `models(name)`; se retiran las
listas cerradas de pesos y normalización. [biomedclip_campaign_configuration_contract.sql](../../scripts/sql/biomedclip_campaign_configuration_contract.sql):
`campaign_configuration_valid` acepta el contrato supervisado con el mismo rigor; la rama Keras no cambia.
