# Registro de modelos y configuración E2

TRAIN y `run_train_all_models.py` consumen `src/malaria_dl/models/registry.py`. Los IDs canónicos son `custom_cnn`, `vgg16` y `densenet121`; `vgg16_transfer_learning` es alias explícito de `vgg16`. Los nuevos TRAIN registran el ID canónico. No se renombran registros históricos.

## Cómo agregar y habilitar un modelo

1. Crear un adaptador con `build(resolved)` y `set_phase(built, resolved, phase)`, usando `AdapterResult`. `build` devuelve un modelo **sin compilar**, backbone opcional, contratos y fases soportadas. La salida es sigmoid binaria `probability_parasitized`; entrada RGB NHWC float32.
2. Crear una configuración JSON versionada con el esquema `model_config_v1`, tomando una de `configs/models/`. Declarar parámetros realmente soportados; extender la validación del contrato cuando se incorpore una capacidad distinta, no aceptar kwargs arbitrarios.
3. Añadir un `ModelDescriptor` mediante `register`: ID único, aliases no ambiguos, enabled/trainable, versión del adaptador, import diferido `modulo:Clase`, archivo de configuración, contratos, estrategias y optimizadores admitidos. Declarar modos de preprocesamiento y normalización interna cuando corresponda. Este es el único catálogo de modelos entrenables.
4. Ejecutar la prueba de contrato del adaptador: firma, fases/capas, cuatro optimizadores si se declaran, paso sintético, guardado `.keras` y recarga. El registro por sí solo no certifica esas capacidades.
5. Habilitarlo únicamente tras pasar esas pruebas. Aparece automáticamente en TRAIN y en la matriz predeterminada sin editar trainer ni ejecutor. `test_discovery_and_descriptor_errors` demuestra este flujo con un adaptador sintético sin añadir arquitectura productiva.

No se incorporan SVM, weighting, focal loss ni ensembles en E2. Un modelo deshabilitado/no entrenable se excluye del descubrimiento; solicitarlo explícitamente falla. El descubrimiento y la CLI diferidos no importan TensorFlow, construyen redes, consultan BD ni descargan pesos.

## Resolución y precedencia

`defaults versionados < JSON seleccionado < overrides CLI explícitos`. El parser no aplica sus defaults sobre el JSON seleccionado. `--max-epochs` tiene prioridad sobre el alias legacy `--epochs`. La configuración se valida antes de construir, y el motor recibe el mismo objeto resuelto que se registra.

Secciones del JSON:

- `schema_version`: `model_config_v1`.
- `model`: input_shape cuadrada RGB (mínimo 32), preprocessing, weights, dropout, L2, head_units, batch_normalization, fine_tune_layers.
- `optimizer`: nombre, parámetros específicos y LR de fine-tuning. La fábrica y los nombres admitidos están en `models/optimizers.py`; momentum pertenece a SGD, beta_1/beta_2 a Adam/AdamW, rho a Adadelta. Se fijan defaults explícitos y se contrastan con `optimizer.get_config()`.
- `execution`: épocas, batch, seed, determinismo, augmentation habilitada, checkpoint, colapso, calibración y Early Stopping.
- `recipe`: BCE, definición de métricas, augmentation y ReduceLROnPlateau existentes, umbral de selección 0.5 y semántica de fallback. E2 conserva esta receta: modificarla se rechaza para no cambiar silenciosamente ciencia.
- `batch`: perfil versionado del ejecutor; no es una campaña persistida.

Dataset UUID, evidencia fijada y raíz/snapshot E1 permanecen separados. No se permite reemplazarlos mediante JSON del modelo. Pesos `none` evitan descargas en pruebas técnicas. Head/BN y L2 no aplicable se validan contra las capacidades actuales; no son opciones libres ignoradas. Fine-tuning admite 1–4 últimas capas en transfer y está prohibido en custom. Un adaptador que devuelve un modelo ya compilado o una firma no binaria se rechaza.

Ejemplo de archivo de configuración de desarrollo (válido para custom):

```json
{
  "model": {"dropout": 0.3},
  "optimizer": {"name": "sgd", "parameters": {"learning_rate": 0.001, "momentum": 0.9}},
  "execution": {"max_epochs": 8, "batch_size": 16}
}
```

Inspección sin BD ni entrenamiento, usando un UUID designado explícitamente:

```sh
python -m src.train --model custom_cnn --dataset-version-id "$DATASET_VERSION_ID" \
  --model-config path/to/development-config.json --dry-run
python run_train_all_models.py --dataset-version-id "$DATASET_VERSION_ID" --dry-run
```

El dry-run muestra configuración/matriz y **no acredita integridad operativa**. El ejecutor valida toda la matriz antes del preflight y del primer subprocess. Sin `--models` usa habilitados entrenables; con `--models` conserva el subconjunto explícito. Sin `--optimizers` usa capacidades del descriptor; con ese argumento no omite combinaciones incompatibles. La configuración se transmite inline con digest verificado por el hijo y procedencia de resolución, sin archivo generado de configuración ni defaults contradictorios.

La base actual produce **3 × 4 × 1 = 12** combinaciones, incluida VGG16+SGD. Se conserva el perfil masivo: 100 épocas base, hasta 20 de fine-tuning para transfer, F2 explícito y paciencia12. LR masivos Adam/AdamW 1e-4/1e-5, SGD 1e-3/1e-4, Adadelta 1/1. Individual conserva 50/30/30 épocas base y fine-tuning0; LR inicial1e-4 y FT1e-5. No hay campaign_id, ledger ni reanudación.

## Compilación, parámetros y persistencia

El motor común es el único compilador del nuevo flujo. Compila al iniciar base y recompila al pasar a fine-tuning con **un optimizador nuevo**, reiniciando su estado como antes. Los constructores legacy siguen compilando por defecto para sus consumidores históricos; los adaptadores llaman `compile_model=False`.

Antes de cada `fit`, `persist_model_configuration` exige run training y dataset coincidentes, actualiza `runs.execution_parameters.model_configuration_e2` y verifica lectura posterior completa. Conserva fases anteriores en el snapshot. Guarda requested/resolved, procedencia, versión de esquema/adaptador, configuración real de arquitectura/compilación/optimizador, callbacks, augmentation, dataset e identidad disponible de código y entorno. El snapshot final incluye selección y model_version_id; si no existe esa identidad o falla la persistencia, no se completa normalmente.

Los nuevos TRAIN siempre requieren tracking; `--track-db` permanece como opción compatible y redundante. La ausencia de BD sólo admite inspección/dry-run y pruebas técnicas aisladas, no TRAIN científico sin registro. El error público de persistencia es sanitizado. El código nuevo no tiene fallback de archivos; la configuración E2 se excluye del payload destinado a los JSON legacy. Los JSON de desarrollo y los checkpoints de prueba no son resultados estructurados alternativos.

Se conservan los escritores legacy de historias/predicciones de TRAIN, cuya migración integral corresponde a E5–E6; **no se afirma que todo TRAIN esté libre de CSV**. E2 no añade escritores CSV y sus pruebas técnicas no los ejecutan. Los nuevos snapshots E2 viven en PostgreSQL. La prueba PostgreSQL usa una tabla TEMP `runs` que oculta la operativa sólo en su sesión, comprueba esa resolución, usa savepoints y revierte la transacción externa; no verifica todos los constraints ni permisos de UPDATE de la tabla operativa. No demuestra durabilidad de commit entre sesiones.

## Métricas y compatibilidad científica

F2 siempre significa beta=2; otro beta falla, en lugar de ignorarse. Se conserva el callback clínico común que calcula F2. El monitor explícito prevalece sobre la política; Early Stopping se resuelve con esa precedencia. El snapshot identifica umbral, colapso, warning/fallback y cumplimiento de recall por separado de la finalización técnica. Completar no significa alcanzar el objetivo clínico ni autoriza publicación.

**VGG16 actual en E2:** auto resuelve a `rescale_0_1`; se conserva la opción explícita `vgg16_imagenet`. **Objetivo E3:** nuevos TRAIN VGG16 con contrato ImageNet obligatorio y prueba de transformación sin doble preprocesamiento. E2 no cambia los inputs históricos. DenseNet mantiene normalización interna ImageNet y backbone llamado con `training=False`; custom conserva BN entrenable, filtros32/64/128/256, dense128, dropout.4 y L2=1e-4; VGG conserva dense1024 y dropout.5; DenseNet GAP/dropout.5/sigmoid.

Hash/tamaño/ownership de checkpoint y finalización de versión existentes se conservan. El cierre integral de consumidores, reintentos y selección de versiones pertenece a E5–E6. La publicación de Producción Etapa 2 sigue siendo manual. E2 no inicia E3 ni una campaña científica.
