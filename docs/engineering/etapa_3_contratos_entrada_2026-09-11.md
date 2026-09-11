# E3 — Contratos de entrada y VGG16

## Nuevos TRAIN

El registro E2 resuelve VGG16 (adaptador 1.1) a `vgg16_imagenet`, tanto por defecto como con `--preprocessing auto`. `rescale_0_1` se rechaza para nuevos TRAIN VGG16. Custom CNN y DenseNet121 conservan `rescale_0_1`. No cambian optimizadores, pérdidas, learning rates, umbrales ni políticas de selección.

La configuración conserva `requested`, `provenance` y `resolved`; el contrato efectivo está en `resolved.input_contract`. El snapshot obligatorio E2 lo persiste en `runs.execution_parameters.model_configuration_e2` antes de fit. Un fallo de persistencia impide continuar. El finalizador copia ese contrato a la versión correspondiente, sin completarlo con defaults. No hay nuevo sidecar de configuración ni fallback a archivos.

## Transformaciones

| Arquitectura | Entrada controlada | Transformación externa única | Grafo |
| --- | --- | --- | --- |
| Custom CNN | RGB 0–255, float32, resize bilinear | dividir por 255 | sin normalización de entrada adicional |
| VGG16 nuevo | RGB 0–255, float32, resize bilinear | `tf.keras.applications.vgg16.preprocess_input`: BGR menos [103.939,116.779,123.68] | sin Normalization/Rescaling adicional |
| DenseNet121 | RGB 0–255, float32, resize bilinear | dividir por 255 | Normalization ImageNet original, medias [.485,.456,.406], varianzas [.229²,.224²,.225²] |
| VGG16 histórico acreditado con rescale | según contrato persistido compatible | dividir por 255 | grafo validado contra contrato histórico |

`malaria_input_v1` declara arquitectura, versión de adaptador, forma NHWC, canales, dtype, decoder RGB, escala de origen, resize, transformación externa/version/ubicación, normalización interna/ubicación, mapping y salida sigmoid `probability_parasitized`. Sólo admite el recorrido declarado: decoder TensorFlow RGB y bilinear sin antialias. La escala procede del contrato; nunca del mínimo/máximo de píxeles.

TRAIN/VALIDATION/EVALUATE/EXPLAIN usan el loader físico común (decodificación y resize Keras/TensorFlow, interpolación bilinear explícita) y `apply_model_preprocessing`. Backend e inferencia trazable usan `transform_bytes`, que comparte la transformación externa y el resize TensorFlow. La aumentación VGG16 ocurre sobre RGB 0–255 antes de BGR/centrado; sus parámetros existentes permanecen: flip, rotación .07, traslación .2/.2, zoom .2 y contraste .3. VALIDATION/EVALUATE/inferencia no reciben esa aumentación. TTA y ensembles existentes quedan fuera de esta verificación.

EXPLAIN calcula scores sobre tensores del modelo; para visualización invierte el centrado y BGR y muestra RGB [0,1]. El callback de LIME convierte explícitamente esa imagen de visualización al dominio del modelo. No se generaron explicaciones científicas en E3.

## Consumo histórico

EVALUATE/EXPLAIN y la inferencia de checkpoint único exigen contrato acreditado de la versión. `--img-size` omitido hereda su tamaño; `auto` hereda su modo. Overrides incompatibles se rechazan antes de cargar/predecir. Los comandos masivos dejan de imponer tamaño/modo procedentes del inventario.

Un VGG16 histórico con contrato completo `rescale_0_1` sigue usando ese modo. No se consulta el JSON actual de VGG16 para reconstruirlo. Un snapshot parcial con sólo `mode` no acredita decoder, resize, escala y firma: la nueva ejecución se bloquea con `INPUT_CONTRACT_MISSING` o un conflicto identificable. No se escriben metadatos retrospectivos ni se modifican los resultados históricos consultables.

La comprobación del grafo valida forma, dtype, salida sigmoid y las capas Normalization/Rescaling de las arquitecturas soportadas. No constituye certificación de cualquier grafo Keras arbitrario. El fixture histórico es sintético: no acredita un checkpoint operativo concreto (D4).

## Verificación PostgreSQL pendiente

Desde la raíz del repositorio, en Compose autorizado:

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
  -e RUN_STAGE3_POSTGRES_TESTS=1 -e PYTHONDONTWRITEBYTECODE=1 \
  backend python -B -m pytest -q -p no:cacheprovider \
  tests/test_input_contract_postgres.py
```

Se esperan tres casos aprobados, uno por arquitectura. Reutilizan el aislamiento E2: tabla temporal `runs`, transacción externa, savepoints, fallo de identidad, lectura idéntica y ausencia posterior al rollback. No prueban durabilidad de un commit entre sesiones ni permisos/constraints completos de `public.runs`.

No iniciar E4 ni campañas a partir de estas pruebas. Dictamen y hashes: [auditoría E3](../audits/etapa_3_contratos_entrada_2026-09-11.md).
