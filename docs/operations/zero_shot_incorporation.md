# Incorporación de modelos Zero-Shot

Estado: CURRENT_DOC. Verificado el 2026-10-27. Contrato complementario a
[artefactos y persistencia](../architecture/capstone_scientific_artifacts_and_persistence.md).
Evidencia: [CAPSTONE-BIOMEDCLIP-STORAGE-01](../audits/CAPSTONE-BIOMEDCLIP-STORAGE-01.md).

## Identidad y ciclo de vida

Usar `models → runs → artifacts → model_versions`, sin tablas ni identificadores alternativos.
`models.model_type='zero_shot'` indica modalidad; `framework` selecciona adaptador;
`metadata.training_mode='logical'` omite el cálculo TRAIN. `scientific_origin` declara
repositorio y revisión fijada, sin rutas físicas. El registro lógico usa `run_type='training'`,
`status='completed'`, `training_performed=false`, cero épocas y dataset NULL.
No produce métricas, épocas ni evaluaciones. La versión queda `candidate`.

Publicación, evaluación, explicación, TEST y sustitución son operaciones distintas.
Una publicación técnica no acredita calibración ni validación clínica. Los comandos
públicos continúan siendo `python -m src.train`, `src.evaluate`, `src.explain`, `src.test`.
El servicio de registro administrativo no es un quinto comando científico.

## Procedimiento

1. Consultar modelos, versiones y artefactos con
   [SQL de auditoría](../../scripts/sql/zero_shot_storage_audit.sql). Confirmar identidad,
   revisión, clases, prompts, transformaciones y dependencias del modelo externo.
2. Preparar el manifiesto del servicio existente
   `src.malaria_dl.pretrained.registration.register_external_model`:
   `name`, `model_type`, `framework`, `architecture`, `metadata`, `files`,
   `preprocessing`, `class_mapping`, `input_signature`, `output_signature`.
   Cada archivo lleva `role`, `path`, `sha256`, `bytes`; exactamente un `checkpoint`.
   Los roles deben ser únicos. La procedencia debe incluir revisiones fijadas del
   modelo y de dependencias externas. No resolver referencias remotas flotantes.
3. Verificar todos los archivos mediante `verified_file`: existencia, archivo regular,
   sin enlaces simbólicos, tamaño y SHA-256. No descargar durante la carga.
4. Tras aprobación de escritura, invocar el servicio existente dentro de su transacción:
   bloqueo asesor por nombre → identidad del modelo → TRAIN lógico → incorporación
   física → artefactos → versión → cierre del RUN. Los repositorios comparten conexión
   mediante `transaction_scope`; un fallo SQL revierte las filas.
5. La incorporación física copia, sin sobrescribir, a
   `malaria_dl_local_project/outputs/train_runs/<run_id>/`, conservando la estructura
   relativa común de los archivos. Los originales permanecen intactos. Los roles del
   perfil se vinculan a los IDs y rutas finales. No se añade una raíz especial.
6. Repetir un manifiesto idéntico reutiliza identidad y verifica roles/checksums/clases;
   no crea otro RUN. Conflictos de metadatos, artefactos, firmas o clases se rechazan.
   Esta operación no es un mecanismo de sustitución de versiones existentes.
7. Verificar carga offline e imagen sintética en cada entorno que consumirá el modelo.
   Confirmar el dispositivo real del modelo. Consultar publicación aparte y utilizar
   el servicio de activación existente sólo con autorización para cambiar producción.

Los [SQL preparados](../../scripts/sql/zero_shot_incorporation.sql) documentan los campos
reales y el orden de FK; se validaron con PREPARE/DEALLOCATE dentro de READ ONLY.
No ejecutan INSERT ni reemplazan el escritor transaccional existente.

## Ubicaciones y conservación

| Ubicación | Uso |
|---|---|
| Caché externa | Fuente descargada fijada por revisión; no basta como almacenamiento accesible desde Docker |
| `outputs/train_runs/<run_id>` | TRAIN por referencia e incorporaciones lógicas nuevas |
| `outputs/campaign_runs/<run_id>` | Ejecución coordinada de campañas; no intercambiable con TRAIN por referencia |
| `artifacts/assessments/<attempt_id>` | Evidencia de un intento científico independiente; EVALUATE/TEST actuales no generan binarios aquí |
| `artifacts.path`, `checksum`, `file_size_bytes` | Ubicación e integridad registradas; no deducirlas del nombre del modelo |

Mientras un modelo registrado conserve `artifacts.path` en la caché externa,
`docker-compose.override.yml` monta `CAPSTONE_EXTERNAL_MODEL_ROOT` (definida en `.env`)
en solo lectura y en la misma ruta absoluta. Sin ese montaje la publicación sigue activa
en PostgreSQL, pero el backend responde `MODEL_DEPENDENCY_INVALID` y el estado Stage 2
la muestra como publicada y no disponible para inferencia.

`local_scientific_path` resuelve los tres árboles compartidos entre Mac y Docker.
El resolvedor productivo aplica además sus raíces permitidas. Las dependencias se
seleccionan por rol registrado, contrastando el perfil congelado y verificando los
bytes; una ruta antigua del perfil no sustituye `artifacts`. El perfil histórico no
se reescribe: la ubicación resuelta se mantiene sólo en memoria.

Un rollback SQL puede dejar archivos nuevos sin referencias. Se conservan para
reconciliación: no borrarlos automáticamente ni reutilizarlos por nombre. Respaldar
BD y binarios juntos. Antes de limpiar consultar también bases aisladas y evidencia
histórica. Un archivo duplicado por hash puede pertenecer a una ejecución válida.

Para el BiomedCLIP actual, los triggers impiden cambiar la ruta del checkpoint y
el payload de la versión gobernada. La
[propuesta pendiente](../../scripts/sql/zero_shot_storage_pending_corrections.sql)
exige una sustitución trazable, sin UPDATE de identidad ni desactivación de triggers.
No se aplicó ninguna corrección a PostgreSQL real.

## Framework y preprocesamiento

| Framework / modo | Contrato verificado |
|---|---|
| TensorFlow/Keras | Adaptador existente; se preservan Custom CNN, VGG16 y DenseNet121 |
| `rescale_0_1` | Float32, división por 255 después del resize contractual |
| `rescale` | Alias aceptado por el resolvedor productivo y normalizado allí; no es una opción universal de `data.preprocessing` |
| `vgg16_imagenet` | Transformación Keras VGG16: RGB→BGR y resta de medias; no equivalente a rescale |
| `pytorch_openclip` / `openclip_original` | Configuración registrada, RGB, tensor CHW float32, resize/crop/normalización OpenCLIP; texto tokenizado desde archivos locales |

BiomedCLIP observado: imagen 224×224; media `[0.48145466,0.4578275,0.40821073]`,
desviación `[0.26862954,0.26130258,0.27577711]`; texto con contexto 256,
PubMedBERT y dos prompts congelados. Score = softmax de similitudes coseno
escaladas; no probabilidad clínicamente calibrada. El adaptador usa CPU/fp32,
`eval()` e `inference_mode()`. Detectar MPS no significa utilizarlo.

El adaptador OpenCLIP actual admite configuración visual y encoder HF local con
roles `model_config`, `text_config`, `tokenizer_config`, `vocabulary`. Un futuro
modelo compatible cambia su configuración y artefactos, no condiciones por nombre.
Otros tokenizadores/frameworks necesitan su adaptador y pruebas; no se promete
soporte automático. Las dimensiones se obtienen de la configuración, no del nombre
BiomedCLIP. Los paquetes están fijados en `requirements-biomedclip-registration.txt`.

## EVALUATE, TEST y EXPLAIN sobre un TRAIN lógico

Los comandos públicos son los mismos; `assessment/openclip.py` aporta contrato, decisión
y runtime, y `runtime_for` elige el runtime por el contrato congelado de la identidad
(nunca por el nombre). Ejecutar dentro del backend Docker, que tiene PyTorch/OpenCLIP:

```sh
docker exec -w /app/malaria_dl_local_project capstone_backend python -m src.evaluate \
  --source-training-run-id <run> --dataset-version-id <dataset> --seed 42 --batch-size 32
# src.test: mismos argumentos.  src.explain: además --method lime|shap [--max-images N]
```

| Regla | Comportamiento |
|---|---|
| Dataset | `--dataset-version-id` obligatorio: el TRAIN lógico no hereda dataset. En un TRAIN convencional debe coincidir con el suyo |
| Seed / batch | Obligatorios: no existe perfil de ejecución que heredar |
| `--threshold auto` | 0,5 `>=` (`zero_shot_two_prompt_argmax_v1`): argmax de los dos prompts implícito en la salida softmax registrada. Fijado antes de VAL/TEST; TEST no exige EVALUATE previo |
| `--threshold clinical` | Umbral calibrado en VAL (`zero_shot_val_calibration_v1`, ver abajo). Sin referencia única → `CALIBRATION_REFERENCE_REQUIRED`/`_AMBIGUOUS` |
| EXPLAIN | `lime` y `shap`. `gradcam` → `EXPLANATION_METHOD_UNSUPPORTED_FOR_FRAMEWORK` (ViT sin capas convolucionales) |
| SHAP | Expected gradients en bloques de 100 muestras con semillas derivadas y media ponderada; el resultado registra `shap_chunk_size`/`shap_chunks` |

### Umbral calibrado en VAL

`--threshold clinical` no recalibra scores: elige el umbral con `find_threshold_for_target_recall`
(la misma función de Keras) sobre las filas persistidas del **único** EVALUATE VAL verificado
con `auto` del mismo modelo y dataset. Política fija `zero_shot_val_calibration_v1`: recall
objetivo 0,98, especificidad mínima 0, beta 2 (la de las campañas Keras); cambiarla es otra
versión. La referencia se re-verifica (filas y SHA-256) y la decisión registra
`evaluation_attempt_id`, `rows_sha256`, política y hash del resultado, sin marca de tiempo:
el umbral se reconstruye sólo desde PostgreSQL. TEST nunca es fuente de calibración.

Orden: `src.evaluate` (auto, referencia) → `src.evaluate --threshold clinical` (métricas VAL
optimistas, mismos datos) → `src.test --threshold clinical` (resultado final).

Clasificación celular: para un modelo zero-shot la activación prefiere el EVALUATE VAL
calibrado más reciente (los demás modelos conservan la evaluación completada más reciente).
Si la versión activa sirve otra decisión, el panel ofrece «Aplicar umbral calibrado en VAL»,
que publica un deployment nuevo con `threshold_source=assessment_decision`; publicaciones y
snapshots anteriores quedan como historia. `threshold_value` se envía como `Decimal` exacto:
un `float8` se redondea a 15 dígitos y el trigger de referencia lo rechaza.

El contrato `openclip_input_v1` identifica transformación, prompts, mapping, firmas y bytes
de dependencias sin rutas; las rutas verificadas viajan en `model.dependencies` como el
checkpoint. Tiempos en CPU del backend: ~0,1 s por imagen al predecir, ~100 s por imagen
con LIME (1000 muestras) y ~190 s con SHAP (1000 muestras). Los scores siguen siendo
similitudes relativas, no probabilidades calibradas.

`CAPSTONE_LOCAL_TRAIN` es una señal del lanzador local ya existente: permite loopback
al PostgreSQL Docker y exige GPU TensorFlow fuera de Docker. No elige framework ni
rutas. No utilizarla como selección de PyTorch/MPS. El backend sigue en Docker.

## PostgreSQL vigente

Alembic no es requisito de ejecución, instalación ni CI. Se retiraron sus comandos
operativos de migración, consultas de revisión y gates de purga/reset. Se conserva
el historial en disco y `alembic_version` en BD; PK/FK/CHECK/triggers/transacciones
siguen intactos. La reconstrucción antigua de `limpiar-experimentos-bd` y
`limpiar-experimentos` queda retirada antes de detener servicios; dependía de DDL
legacy y una revisión fija. No se ejecutó ninguna limpieza.
