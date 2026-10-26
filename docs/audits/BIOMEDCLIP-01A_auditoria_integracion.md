# BIOMEDCLIP-01A — Auditoría técnica, arquitectónica y científica

Fecha: 2026-10-26. Estado: auditoría completada; integración **no implementada ni certificada**.
Repositorio observado: `bd612af6d4f4d3946d847e05c90343cc605596f2`. PostgreSQL: `malaria_experiments`, contenedor `capstone_db`, consultas con `default_transaction_read_only=on` y comprobación `transaction_read_only=on`.

## 1. Resumen ejecutivo

Es viable diseñar la integración conservando PostgreSQL y los mecanismos científicos existentes, pero **ninguna de las tres arquitecturas funciona hoy con los contratos actuales**. No se trata sólo de registrar nombres o escribir tres constructores.

- Los nombres propuestos `biomedclip_zero_shot`, `biomedclip_linear` y `biomedclip_fine_tuning` satisfacen la convención del registro. Deben ser tres filas distintas de `models`, con identidad UUID propia y familia compartida en metadatos. Actualmente sólo existen Custom CNN, VGG16 y DenseNet121.
- TRAIN, validación de entrada, serialización, verificación y runtime de inferencia están acoplados a TensorFlow/Keras. La persistencia por registros, hashes, muestras e intentos ofrece componentes reutilizables.
- **Zero-shot necesita una ampliación explícita del contrato de origen**: `assessment_identities.training_run_id` es NOT NULL, su trigger exige un RUN training y `model_versions` impide un checkpoint gobernado sin TRAIN. No se debe crear un TRAIN vacío ni reutilizar el de otra arquitectura.
- Linear puede conservar el encoder original y entrenar una cabeza Keras, pero el checkpoint de la cabeza solo no reconstruye el modelo completo. Necesita identidad compuesta verificable y adaptación de los contratos de entrada, ejecución y carga.
- Fine-tuning requiere un ejecutor PyTorch y serializador propios que emitan evidencia equivalente a TRAIN. No necesita simular un objeto Keras `history.history`.
- El host es **Apple M4 Max, 48 GiB, macOS 26.7.1**. El entorno efectivo `.venv-metal` tiene Python 3.12.13, PyTorch 2.14.1 y torchvision 0.29.1; `torch.backends.mps.is_built()` e `is_available()` devolvieron `True`. **OpenCLIP, Transformers y timm no están instalados**. No se cargó BiomedCLIP ni se midió throughput, memoria o entrenamiento.
- El documento arquitectónico obligatorio está parcialmente desactualizado: ya existen REPRESENT, PCA/UMAP persistidos, CKA calculada al consultar, EXPLAIN TEST mediante el servicio de generación y evidencia de GPU Metal. Deben reutilizarse esas capacidades, no crear persistencia paralela.

**Recomendación:** mantener una capa científica común y separar ejecutores/serializadores Keras, PyTorch e híbrido. Aprobar primero el diseño de origen preentrenado y modelo compuesto; implementar por fases sólo tras autorización de 01B. Mantener TEST dependiente de TRAIN para arquitecturas entrenables, con una excepción gobernada exclusivamente para Zero-shot.

## 2. Lectura completa, alcance y criterio de evidencia

Se leyó íntegramente [Capstone — Mapa de persistencia y trazabilidad de artefactos científicos](../architecture/capstone_scientific_artifacts_and_persistence.md), desde el encabezado hasta el cierre de §8 y su nota complementaria, **antes de analizar código o emitir propuestas**. Se usa como referencia arquitectónica principal; sus hechos históricos se contrastan con implementación y esquema efectivos.

Convenciones: `M/` = `malaria_dl_local_project/src/malaria_dl/`; `B/` = `backend_api/app/`; `F/` = `frontend/src/`; `C§` = sección del documento obligatorio. Las rutas abreviadas de las tablas son relativas a estas raíces. Los símbolos de función permiten localizar la evidencia con `rg -n` sin depender de números de línea cambiantes.

Estados:

- **VERIFICADO:** observado en código, esquema/filas o documentación oficial; se especifica el tipo. Verificación estática no equivale a ejecución exitosa.
- **INFERIDO:** diseño o consecuencia razonada de la evidencia; requiere implementación/validación.
- **PENDIENTE DE PRUEBA:** comportamiento operativo no medido o contrato propuesto no ejecutado.

Sólo se creó este documento. No se modificaron producción, esquema, datos, `.env` o dependencias; no se crearon campañas ni ejecuciones; no se descargaron checkpoints; no se entrenó; no se hicieron commits/merges. No se consultaron versiones ni revisiones Alembic. La consulta de disponibilidad MPS no creó tensores, modelos ni operaciones científicas. No se recorrieron imágenes ni se revalidaron masivamente binarios históricos.

## 3. Inventario y catálogo de arquitecturas/campañas

### 3.1 Catálogo PostgreSQL observado

| `models.name` | `models.id` | `architecture` | `model_type` / `framework` |
|---|---|---|---|
| `custom_cnn` | `976fef0d-6d98-4ed7-a7c5-5983efee5294` | Custom CNN | classification / tensorflow/keras |
| `densenet121` | `30354220-10ac-4ac8-a5f5-0d16b13ddbcd` | DenseNet121 | classification / tensorflow/keras |
| `vgg16` | `998ae52c-0c6b-4673-9c70-70a44caee16a` | VGG16 | classification / tensorflow/keras |

**VERIFICADO, SQL y `M/models/registry.py:model_catalog`.** `models` dispone de `pretrained`, `pretrained_source`, `metadata`, firmas y framework; `runs.model_id` y `model_versions.model_id` son FK. No se necesitan tablas nuevas para registrar la familia. `vgg16_transfer_learning` es alias Python de `vgg16`, no una cuarta fila. El registro acepta `[a-z][a-z0-9_]*`; los tres identificadores propuestos son compatibles sintácticamente. Impacto: registrar tres identidades nuevas y descripciones inequívocas; no reemplazar nombres históricos (C§3.1, §6).

### 3.2 Componentes y adaptación necesaria

Todas las observaciones de esta tabla son **VERIFICADAS por inspección estática**; las adaptaciones son **INFERIDAS** y no implementadas.

| Componente y símbolo | Contrato/evidencia actual | Impacto y recomendación |
|---|---|---|
| `M/models/registry.py:ModelDescriptor`, `register`, `resolve_descriptor` | Catálogo desde SQL; implementación lazy; flags `enabled`, `trainable`. `executable=True` exige ambos. Registro exige estrategias y optimizadores no vacíos aun para no entrenables | Separar descubrimiento, inferencia y TRAIN. Zero-shot necesita descriptor consultable sin estrategia/optimizador ficticios |
| `M/models/adapters.py:AdapterResult`, `compile_phase`, `BaseAdapter.set_phase` | `.layers`, `.trainable`, firma NHWC, sigmoid, compilación Keras; `serialization='keras_v3'` | Conservar adaptadores actuales; interfaz de capacidades y dispatch de ejecutor/serializador para los nuevos |
| `M/models/architectures.py:build_custom_cnn`, `build_vgg16_transfer`, `build_densenet121_transfer` | Constructores concretos Keras | No convertir BiomedCLIP a estas arquitecturas ni cambiar modelos existentes |
| `malaria_dl_local_project/configs/models/{custom_cnn,vgg16,densenet121}.json`; `M/models/configuration.py:resolve_config`, `merge_strict` | Configuración estricta `model_config_v1`, pesos sólo none/imagenet, receta fija, forma imagen RGB | Añadir perfiles explícitos de encoder HF, dimensión/normalización de embedding, bloques entrenables y formato; evitar campos ignorados |
| `M/campaigns/configuration.py:_registry`, `_catalog_models`, `_parameter`, `catalog`, `normalize` | `_registry` usa `resolve_descriptor` entrenable para **cada** fila SQL; formulario deriva parámetros/valores permitidos de defaults; enum de pesos none/imagenet | Agregar Zero-shot sin corregir esto puede romper todo el catálogo. Publicar `trainable` y motivo; omitir parámetros TRAIN no aplicables y rechazar selección en backend |
| `M/campaigns/contracts.py:expand_matrix`; `M/campaigns/configuration.py:build_request`, `resolve` | Modelos × optimizadores × variantes, configuraciones por hash × semillas | Linear y Fine-tuning participan normalmente. Zero-shot visible, excluido de miembros TRAIN y del total; no generar combinaciones vacías/ficticias |
| `B/routes/campaigns.py`, `B/services/campaign_configuration.py`; `F/pages/CampaignConfiguration.tsx` | Selector usa `catalog.models.map`; checkbox de modelo sin flag de capacidad; hiperparámetros desde catálogo | Reutilizar endpoints/preview/guardado; extender schemas y `F/types/campaign.ts`. Mostrar deshabilitado: «No requiere entrenamiento local» |
| `M/execution/operations.py:main`, `training_plan`; `selection.py:select_trainings` | Campaña sin referencia va al coordinador; referencia crea nuevo TRAIN con configuración heredada; selección SQL `run_type='training'` | Mantener identidades nuevas y selección congelada. Zero-shot requiere entrada por origen/model_version, no por `source_training_run_id` |
| `M/execution/campaign.py:execute_campaign`, `run_child`; `worker.py:run_scientific_train` | Coordinador, claims, worker, eventos E10, cierre científico; loader Keras por defecto | Reutilizar lifecycle, owner y gate; elegir ejecutor y verificador por formato/framework |
| `M/execution/train.py:train`, `PersistEpoch.on_epoch_end` | `tf.data`, callbacks, `.fit`, `.save`, `.keras`, recarga Keras | Separar ciclo PyTorch y entrada de embeddings de Linear; conservar evidencia por época y contratos de cierre (C§3.1) |
| `M/execution/artifacts.py:verify_session`, `file_identity`, `keras_loader`; `process_verification.py:isolated_keras_loader` | Hash y ownership genéricos; verificación semántica del loader Keras | Reutilizar hashes/ownership; loader por formato y verificación compuesta para Linear |
| `M/assessment/{cli,lineage,service,runtime,contracts,repository}.py` | Identidades/intentos/muestras/métricas comunes, runtime por defecto Keras | Reutilizar orquestación/persistencia; adaptar origen, preprocesamiento y runtime; detalles en §§7–11 |
| `M/data/{governed_dataset,sample_repository,input_contract}.py` | Gobierno de versión/paciente; transformación rígida TensorFlow | Reutilizar muestras y splits, reemplazar sólo adaptador de transformación del nuevo modelo |
| `M/persistence/model_configuration.py`; `execution/repository.py` | Captura de entorno importa TF y usa campos TensorFlow/Keras | Registrar PyTorch/OpenCLIP/timm/Transformers/MPS efectivos en evidencia existente; no etiquetar PyTorch como Keras |
| `B/services/{scientific_results,scientific_report,scientific_preflight,scientific_representations}.py` | Reportes vinculados a TRAIN; representaciones esperan especificación GAP | Extender selección/origen y definición de representación, conservar consultas y estados de evidencia |

### 3.3 Restricciones SQL efectivas que impiden una incorporación sólo Python

**VERIFICADO, `pg_constraint` y `pg_proc`, 2026-10-26.**

| Objeto vigente | Restricción | Impacto/recomendación |
|---|---|---|
| `run_configurations`, CHECK `v2_run_configurations_check_cf7585e198d6` | `architecture IN ('custom_cnn','vgg16','densenet121')` | Linear/Fine-tuning requieren ampliar el dominio explícitamente |
| CHECK `v2_run_configurations_check_63e4a55e1de0` | Combinaciones cerradas arquitectura/normalización/internal_preprocessing para esas tres | Ampliar con transformaciones originales verificadas; metadata no elude el CHECK |
| CHECK `v2_run_configurations_check_4face7ed3946` | `weights IN ('none','imagenet')` | Añadir significado real de pesos BiomedCLIP; no falsear `imagenet` |
| CHECKs de `max_epochs`, optimizer, dimensiones | Épocas >0; adam/adamw/sgd/adadelta; RGB cuadrado >=32 | TRAIN normal reutilizable con adaptación. No codificar Zero-shot como cero épocas |
| `v2_configuration_guard()` | Compara JSON canónico, configuración del RUN y columnas normalizadas | Actualizar productor/configuración coherentemente; conservar trigger y hash |
| `assessment_identities` | `training_run_id NOT NULL`, FK `runs`; igualdad con `identity.model.training_run_id` | Zero-shot no cabe hoy |
| `assessment_identity_guard()` | Exige RUN de tipo training | Una FK nullable aislada no resolvería el problema |
| `model_versions` | `chk_model_versions_artifact_requires_training`, `chk_model_versions_resolved_training`; FK compuesta `(checkpoint_artifact_id,training_run_id)` a `artifacts(id,run_id)` | Origen externo gobernado exige cambiar restricciones de manera explícita, sin retirar protección a entrenables |
| `enforce_model_version_governance()` | Verifica tipo TRAIN cuando existe y protege identidad de versiones gobernadas | Mantener inmutabilidad y validar rama externa |
| `assessment_result_guard()` | Score numérico [0,1], `calibrated_score=null`, predicción consistente con umbral | Coseno bruto no puede insertarse como `raw_score`; declarar transformación y significado |

## 4. Matriz de compatibilidad por arquitectura

`V` = VERIFICADO estáticamente como soporte existente o bloqueo; `I` = INFERIDO como adaptación; `P` = PENDIENTE DE PRUEBA operativa. Referencias: inventario §3 y contrato C§1–3, §6.

| Capacidad | Zero-shot | Linear híbrido | Fine-tuning PyTorch |
|---|---|---|---|
| Identidad individual SQL | V: ausente; I: fila propia | V: ausente; I: fila propia | V: ausente; I: fila propia |
| Visible en campañas | I: sí, TRAIN deshabilitado | I: sí, TRAIN habilitado | I: sí, TRAIN habilitado |
| TRAIN local | N/A; debe rechazarse | I/P: embeddings congelados + cabeza Keras | I/P: encoder parcial + cabeza Torch |
| Ejecutor actual sin cambios | V: incompatible | V: incompatible | V: incompatible |
| GPU local | P: encoders/similitudes MPS | P: extracción MPS y cabeza TF Metal | P: forward/backward MPS |
| Checkpoint | I: original fijado y verificable | I: original + cabeza + identidad compuesta | I: original preservado + estado ajustado |
| EVALUATE/TEST | V: bloqueados por origen; I: excepción gobernada | I: runtime compuesto | I: runtime PyTorch |
| EXPLAIN | I/P: objetivo de similitud/score | I/P: LIME; gradientes requieren puente | I/P: gradientes PyTorch |
| Curvas de aprendizaje | N/A | I: de la cabeza | I: de fases realmente ejecutadas |
| Representaciones/CKA | I: adaptar productor y especificación | I: encoder congelado; identificar espacio | I: encoder ajustado; identificar espacio |
| Compatibilidad certificada | No | No | No |

## 5. PyTorch/OpenCLIP y GPU local

### 5.1 Evidencia oficial del modelo

**VERIFICADO documentalmente.** La [ficha oficial de Microsoft](https://huggingface.co/microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224) propone Python 3.10, `open_clip_torch==2.23.0` y `transformers==4.35.2`; carga mediante `create_model_from_pretrained`, tokenizer HF y checkpoint `open_clip_pytorch_model.bin`. Su ejemplo selecciona CUDA o CPU, no MPS: no acredita este host. El modelo usa preentrenamiento imagen-texto biomédico; su alcance declarado es investigación y su encoder textual es inglés. Esto no constituye validación clínica de malaria.

**VERIFICADO documentalmente**, [configuración oficial](https://huggingface.co/microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224/raw/main/open_clip_config.json): dimensión proyectada 512; visual `vit_base_patch16_224`, entrada 224; proyección visual lineal; encoder/tokenizer `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract`, proyección textual MLP, pooling CLS y contexto 256. Media RGB `[0.48145466,0.4578275,0.40821073]`, desviación `[0.26862954,0.26130258,0.27577711]`. No confundir vector proyectado multimodal con activación interna previa a proyección.

**VERIFICADO documentalmente**, [transformaciones OpenCLIP 2.23.0](https://raw.githubusercontent.com/mlfoundations/open_clip/v2.23.0/src/open_clip/transform.py): inferencia por resize bicúbico al lado corto, center crop, RGB, tensor y normalización; tensor de modelo NCHW. Persistir la transformación efectiva completa y su versión. El resize bilineal sin antialias y rescale `[0,1]` actuales no son equivalentes. Impacto: ampliar `M/data/input_contract.py:validate_input_contract`; no declarar una transformación TF que nunca se aplicó.

Las [dependencias de OpenCLIP 2.23.0](https://raw.githubusercontent.com/mlfoundations/open_clip/v2.23.0/requirements.txt) incluyen torch, torchvision, timm, Hugging Face Hub, sentencepiece, protobuf, regex y ftfy. El modelo añade Transformers. **PENDIENTE DE PRUEBA:** resolver una combinación bloqueada para Python 3.12, NumPy 1.26.4 y Torch 2.14.1. No copiar los pins de Python 3.10 suponiendo compatibilidad transitiva; revisar especialmente tokenizers, timm y APIs de carga. No se instaló nada.

### 5.2 Host y entornos inspeccionados

| Evidencia local | Resultado | Estado e implicación |
|---|---|---|
| `sw_vers`; `sysctl -n machdep.cpu.brand_string hw.memsize` | macOS 26.7.1; Apple M4 Max; 51.539.607.552 bytes = 48 GiB | VERIFICADO, hardware/SO |
| `M/execution/local_launch.py:ALLOWED_VENVS`, `environment_problem` | Sólo `.venv-metal`, Python 3.12; exige TF/Keras y dependencias comunes | VERIFICADO, necesita selección de requisitos por runtime |
| `.venv-metal`, `importlib.metadata` | Python 3.12.13 arm64; torch 2.14.1; torchvision 0.29.1; TF 2.17.1; Metal 1.2.0; Keras 3.15.1; NumPy 1.26.4; SHAP 0.49.1 | VERIFICADO, entorno efectivo; coinstalación no prueba interoperabilidad |
| `.venv-metal`, consulta de capacidades Torch | `mps.is_built=True`, `mps.is_available=True` | VERIFICADO, backend disponible; ningún forward/backward ejecutado |
| `.venv-metal`, metadata OpenCLIP/Transformers/timm | No instalados | VERIFICADO, bloquea carga actual |
| `.venv`, inspección comparativa | Python 3.12.13; no torch/torchvision; Keras 3.14.1 | VERIFICADO, no confundir este entorno con el permitido por bootstrap |
| `requirements-cpu.txt`, `requirements-gpu.txt`, `requirements-local-train.txt`, `requirements.txt` | Base TF/Keras; no contrato OpenCLIP completo | VERIFICADO, falta reproducibilidad de nueva pila |
| `docker-compose.yml`, `local_launch.py`, `accelerator.py` | Backend Linux/amd64; GPU local por host; Docker considerado CPU | VERIFICADO; ejecutar MPS en proceso macOS, conservar control/API/BD en Docker |

La [documentación Apple](https://developer.apple.com/metal/pytorch/) y [PyTorch MPS](https://docs.pytorch.org/docs/2.14/notes/mps.html) respaldan aceleración en Apple Silicon. **INFERIDO:** M4 Max es candidato razonable; **PENDIENTE DE PRUEBA:** todas las operaciones de este modelo, determinismo, estabilidad numérica, precisión mixta y rendimiento. El canario TensorFlow existente no certifica PyTorch. No se debe activar fallback CPU silencioso para afirmar uso GPU.

### 5.3 Memoria y limitaciones esperadas

**INFERIDO, estimación de diseño, no medición:** un sistema visual/textual del orden de 200 millones de parámetros FP32 requiere aproximadamente 0,8 GB sólo en pesos; el valor exacto se contará tras carga. Para `N` parámetros entrenables, pesos+gradientes+dos momentos Adam FP32 son aproximadamente `16*N` bytes, excluyendo pesos congelados, activaciones, buffers, allocator y datos. Atención y activaciones crecen con batch/tokens; SHAP multiplica carga por referencias/muestras. No se promete un batch por disponer de 48 GiB.

Linear reduce memoria de entrenamiento del encoder; conviene liberar objetos Torch entre extracción y fit Keras cuando sea posible. Compartir memoria unificada no implica compartir tensores ni pools de allocator. Para 27.558 imágenes ×512×4 bytes, una matriz FP32 sería aproximadamente 53,8 MiB, sin índices/metadatos; es una estimación, **no** una propuesta de extraer TEST durante TRAIN. Fine-tuning y XAI requieren presupuestos separados. Comenzar FP32; AMP, attention fusion y determinismo estricto son pruebas posteriores.

## 6. Cumplimiento del contrato de artefactos científicos y persistencia

### 6.1 Reglas conservadas

**VERIFICADO en C§1–6 y código citado.** PostgreSQL conserva identidad, configuración, resultados, linaje, transacciones e historial. Checkpoints/mapas/matrices grandes quedan fuera con referencia, bytes y SHA-256. La raíz efectiva es la registrada, no una convención reconstruida. Cada ejecución independiente tiene identidad/intento propios; registros históricos no se sobrescriben. El dataset se resuelve por versión y muestras gobernadas. Un archivo ausente no se repara alterando el intento histórico.

`M/execution/artifacts.py:file_identity`, `verify_checkpoint_file` y `verify_session` reutilizan hashing/ownership, pero `verify_session` exige épocas y calibración de TRAIN: **no es un verificador de origen Zero-shot**. `keras_loader` sí es específico. El contrato describe `.keras` como implementación vigente, no como motivo científico para convertir pesos Torch a Keras. Se propone serializador equivalente con verificación de reconstrucción y conservación de todas las épocas (C§3.1, §5–6).

### 6.2 Discrepancias explícitas entre documento e implementación vigente

| Documento | Evidencia actual | Estado, impacto y recomendación |
|---|---|---|
| C§2: `storage_paths` sólo traslada train_runs/assessments | `M/execution/storage_paths.py:ALLOWED_TREES` incluye `outputs/campaign_runs` | VERIFICADO código. Reutilizar traslado actual; no abrir rutas arbitrarias |
| C§3.2: `kind` sólo evaluate/explain; artifacts sólo EXPLAIN | CHECK SQL permite `represent`; `assessment_attempt_guard` exige 4 artefactos para REPRESENT | VERIFICADO SQL. Reutilizar almacenamiento de matrices |
| C§3.3.2, §3.3.3, §3.3.5, §7: sin productor/almacén de embeddings/PCA/UMAP | `M/assessment/runtime.py:represent`, `save_arrays`; `representation.py:project`; `service.py:represent_reserved`; `B/services/representation_generation.py:RepresentService` | VERIFICADO código y 5 intentos verified (3 VAL, 2 TEST), 5 artefactos de cada rol embeddings/pca/pca_variance/umap. Adaptar, no crear otro almacén |
| C§3.3.4: CKA no existe | `representation.py:linear_cka`; `B/services/scientific_representations.py:cka_matrix` | VERIFICADO código. CKA se deriva en lectura sobre IDs comunes; no es artefacto persistido |
| C§3.3.3: EXPLAIN sólo VAL, errores TEST sin productor | CLI sigue VAL; `B/services/explain_generation.py:prepare` conserva split/purpose del contexto y admite TEST | VERIFICADO código y 6 intentos explain/test verified. No equiparar restricciones de CLI con servicio HTTP |
| C§3.3.4/§7: dispositivo no persiste | `train.py:train` incorpora `accelerator` a `runtime_environment`; SQL contiene GPU y tensorflow_metal | VERIFICADO código y fila observada. Extender captura a MPS; no afirmar que todas las ejecuciones antiguas la tienen |
| C§4: 15/16 checkpoints registrados; CLI siempre sin proyección | Código `operations.main` distingue campaña/coordinador y referencia/standalone; SQL: 23 sesiones, 22 verified, 22 con artifact model_checkpoint | VERIFICADO. Cifras históricas no vigentes; no extrapolar H-01 a toda CLI. Brecha standalone todavía visible en código |
| C§5: cifras de checkpoints/XAI del 21 de octubre | SQL actual: 492 registros artifact y epoch; 17.589 map +17.589 overlay | VERIFICADO sólo filas. No se rehicieron hashes/existencia de todos los archivos; no declarar resuelta la pérdida histórica de 5.386 archivos |

El contrato obligatorio conserva primacía en sus invariantes. Sus inventarios operativos requieren actualización posterior, **no realizada aquí**. No se inicia un sistema de persistencia paralelo basándose en esas omisiones.

### 6.3 Matriz de artefactos por arquitectura y operación

Soporte actual común **VERIFICADO** en C§3/§5/§6, `execution/train.py`, `execution/artifacts.py`, `assessment/service.py`, `runtime.py` y triggers. Cada celda de BiomedCLIP indica una propuesta **INFERIDA / PENDIENTE DE PRUEBA**, no soporte certificado.

| Operación/evidencia | Soporte real existente | Zero-shot | Linear | Fine-tuning |
|---|---|---|---|---|
| Origen/configuración | models, model_versions, runs, sesiones, JSON canónico; origen gobernado exige TRAIN | Original + revisión/hash/config/tokenizer/prompts; ampliar origen | TRAIN y referencia al original + cabeza | TRAIN y referencia al original + configuración de bloques |
| TRAIN checkpoints por época | `train_execution_records` artifact_prepared/artifact; archivos `.keras`; SHA/bytes/version_id | N/A | Cabeza `.keras` y binding compuesto verificable por época | Estado Torch por época, formato explícito y parámetros de reconstrucción |
| TRAIN historial | epoch/runtime/phase/selection; no depende de fichero history.json | N/A | Métricas reales de cabeza, LR y selección | Métricas reales de loop Torch, grupos LR, congelamiento y parada |
| TRAIN predicciones VAL/calibración | predictions y calibration/val/selected; selección y umbral ligados al checkpoint | N/A; si se ajusta umbral, evidencia VAL separada del TRAIN | Reutilizar con inferencia compuesta | Reutilizar con inferencia Torch |
| TRAIN resultado de campaña | Eventos E10, artifacts, evaluations, run_clinical_metrics, completion | N/A | Emitir contrato común | Emitir contrato común |
| EVALUATE VAL / TEST | identities/attempts/results, scores por sample_id, métricas y confusión en verification; sin binarios de evaluación | Tras ampliar origen; score softmax declarado; conservar similitudes en payload con contrato explícito | Reutilizar después de reconstruir pipeline | Reutilizar después de cargar estado |
| EXPLAIN | 2 binarios por muestra, map NPY + overlay PNG; payload método/capa; hashes y owner | Objetivo explícito de score/similitud; ampliar metadatos semánticos | LIME compuesto; gradientes condicionados al puente | Gradientes Torch/ViT; mismos roles binarios |
| REPRESENT | 4 matrices NPY por intento; resultados enlazan row→sample_id; trigger fija roles y muestra ancla | Embedding proyectado del original | Embedding del encoder original, no confundir con cabeza | Embedding del encoder ajustado; especificación distinta |
| Activaciones/token maps/conceptos | No productor genérico inspeccionado para esos contenidos; schema REPRESENT no admite roles arbitrarios | Adaptación futura explícita | Adaptación futura explícita | Adaptación futura explícita |
| Manifiesto/reconstrucción | Configuración, completion, verification y metadatos SQL existentes; no manifiesto universal multicomponente | Inventario del original dentro de identidad gobernada | Inventario original+cabeza+transformaciones, hash compuesto | Inventario estado+config+original/tokenizer si se usan |

**Recomendación de reconstrucción (INFERIDA):** ampliar el contrato del artefacto para describir formato y componentes en metadatos PostgreSQL, cada componente con hash/tamaño/ruta/rol. Un hash de manifiesto debe vincular el conjunto; verificar también cada binario al cargar, no sólo el JSON. Si se elige un paquete único para conservar `path/sha256/bytes`, debe incluir una receta verificable y validar las referencias externas al original. La opción exacta se decide en 01B antes de escribir datos. Reutilizar `artifacts`, metadatos y records; no crear una tabla nueva por framework ni un historial JSON autoritativo paralelo. El cache HF global por sí solo no garantiza recuperación histórica.

## 7. Zero-shot sin TRAIN

**VERIFICADO:** `M/assessment/lineage.py:resolve` exige `training_run_id` o `model_version_id`, pero este último resuelve sesión TRAIN o el resolvedor gobernado histórico; no elimina dependencia de TRAIN. `prepare` hereda dataset, seed y batch del TRAIN. CLI y selección SQL también lo exigen. Restricciones SQL de §3.3 y reportes de §12 impiden una excepción sólo en UI.

**Propuesta INFERIDA, sujeta a aprobación de 01B:** ampliar el origen del modelo con discriminante conceptual `trained` / `pretrained_external` dentro de la gobernanza existente. Para el primero, conservar TRAIN, checkpoint elegido, dataset heredado y sus verificaciones. Para el segundo, exigir `model_id` Zero-shot, `model_version_id`, checkpoint original, revisión inmutable del repositorio, SHA-256/bytes, configuración, tokenizer y transformaciones verificables; `training_run_id` ausente. Dataset/version/split/protocolo/seed/batch serán explícitos de la ejecución, no heredados de un TRAIN inventado.

Reutilizar `model_versions`, `artifacts` (su `run_id` ya admite NULL) y assessments, ampliando CHECKs y triggers para validar **exactamente una rama de origen**. La FK compuesta actual no verifica ownership de un origen sin RUN: la rama externa debe comprobar explícitamente artifact/model/version y contenido, no confiar en el comportamiento de NULL de la FK. Ampliar `assessment_identities` y su identidad canónica, resolvedor, DTOs y consultas que hacen JOIN obligatorio a runs. Mantener versiones entrenables sin relajaciones. No usar `discovered`/`unresolved` para eludir la gobernanza. No se recomienda crear nuevas tablas en esta auditoría.

Prompts reproducibles: congelar idioma inglés, texto exacto, orden de clases `uninfected=0/parasitized=1`, templates, tokenizer/revisión, truncación/contexto 256, política de ensemble y normalización. No seleccionar prompts mirando TEST. Ejemplos de templates sólo serán candidatos de un protocolo, no afirmaciones de rendimiento.

**Regla propuesta INFERIDA:** embeddings normalizados, cosenos por clase, logits con el `logit_scale` del modelo, softmax entre las dos clases y score positivo; decisión `score>=t` consistente con el sistema. Con `t=0,5`, documentar desempate positivo. Conservar cosenos/logits y regla, sin intentar insertar cosenos [-1,1] como probabilidades. El softmax es un score relativo a prompts/clases, **no una probabilidad clínicamente calibrada**. `calibrated_score` sigue NULL. Cambiar prompts cambia identidad de la evaluación aunque pesos sean iguales.

EVALUATE será VAL/development; TEST test/final, ambos con identidad independiente y configuración fijada. EXPLAIN puede explicar score positivo o similitud concreta, distinguiendo objetivos en el protocolo. Para un primer alcance mínimo usar umbral fijo predeclarado; si se optimiza en VAL, añadir evidencia de selección de umbral vinculada a intento VAL y origen, sin fabricar calibration TRAIN. Mantener TEST sin requisito de EVALUATE cuando no se deriva un umbral de éste. Historial, early stopping y curvas: **N/A**.

## 8. Linear híbrido PyTorch + Keras

**INFERIDO** a partir de la interfaz OpenCLIP y del engine actual; **PENDIENTE DE PRUEBA** completa. Flujo recomendado: muestras gobernadas → transform original → encoder visual congelado en `eval`/sin gradientes → embedding proyectado 512 con normalización declarada → cabeza Keras `Dense(1, sigmoid)` sin capas ocultas. La frontera imagen/embedding es explícita: el input de la cabeza no es NHWC. `compile_phase` y `validate_model_input` actuales rechazan esa firma, por lo que un adaptador superficial no sirve.

TRAIN alimenta exclusivamente optimización; VAL calcula selección/parada/umbral y métricas; TEST sólo se extrae en operación TEST independiente. Si se añade un escalador de embeddings, ajustar exclusivamente con TRAIN y persistir parámetros; preferible comenzar sin él. Conservar encoder y su hash sin mutaciones. Cabeza y embedding deben ser reconstruibles con la misma normalización y orden de muestras. Usar transform determinista para baseline; augmentation exige definir si se vuelve a extraer por época y no puede ocultarse tras una matriz fija.

**Checkpoint completo:** original y revisión verificables + cabeza entrenada + receta de embedding/preprocesamiento + clase positiva + configuración resuelta. Guardar cabeza por época, selección y artefactos inmutables (C§3.1). El historial corresponde a la cabeza; no afirmar que se entrenó el encoder. La transferencia Torch→CPU/NumPy→Keras introduce copia y rompe autograd entre frameworks: aceptable para encoder congelado, relevante para XAI (§11).

**Cálculo bajo demanda/caché:** para 01B preferir extracción dentro de la ejecución con matrices en memoria de TRAIN y VAL separadas, sin persistencia nueva. Medir si merece una caché durable antes de diseñarla. La operación REPRESENT existente necesita contexto de evaluación/modelo y genera también PCA/UMAP: no reutilizarla como supuesto almacén de embeddings TRAIN pre-cabeza. Una caché futura tendría que vincular sample_id, hash de imagen, dataset/split, revisión/hash encoder, transform, dimensión, normalización, dtype y orden; invalidar cambios y separar augmentation. Esta auditoría no crea tal caché.

## 9. Fine-tuning PyTorch

**INFERIDO; PENDIENTE DE PRUEBA.** Conservar original completo inmutable. Derivar estado visual y cabeza binaria propia, manteniendo encoder textual y proyecciones originales disponibles. Propuesta mínima: fase base de cabeza con visual congelado y fase de ajuste de últimos bloques visuales, con lista de nombres y número de parámetros entrenables explícitos. No traducir «capas Keras» a bloques ViT sin definición. Si se ajusta proyección visual, registrarlo; si se usa activación preproyección para la cabeza, identificarla como otro espacio.

Usar BCE con logits para entrenamiento y sigmoid para salida clínica. Optimizador inicial candidato AdamW; LR de cabeza y visual separados, weight decay distinto de regularización L2. Preservar límites/configuración normalizada y registrar grupos, betas, eps, scheduler, estado y política de reset al cambiar fase. No asumir equivalencia numérica entre AdamW Keras y Torch con igual etiqueta. Hiperparámetros concretos se fijarán mediante TRAIN/VAL, no TEST.

Reutilizar políticas de selección clínica `M/training`/`M/evaluation` consumiendo arrays de labels/scores; producir loss/métricas TRAIN/VAL reales, LR, fase y época. Early stopping, min_delta, paciencia, monitor, desempates y restore deben corresponder a lo ejecutado. Recargar el checkpoint **seleccionado**, no el último estado ni sólo pesos restaurados en memoria. Guardar estado por época con identidad/hash; para reanudación exacta incluir optimizer/scheduler/RNG y configuración, diferenciándola de una simple recarga para inferencia.

**VERIFICADO**, `M/execution/train.py:PersistEpoch` ya persiste filas epoch desde logs y el engine sólo usa `h.epoch` para contar la fase. C§3.1 exige registros científicos, no el tipo Keras History. **Recomendación INFERIDA:** el loop Torch emitirá epoch/runtime/phase/artifact/selection/predictions/calibration y eventos de cierre equivalentes; una vista `dict[str,list]` de historial puede derivarse de esos registros si un consumidor la necesita. No llenar accuracy/AUC/loss inexistentes ni reconstruir valores artificialmente.

**Alineación multimodal:** congelar texto no garantiza conservar alineación después de ajustar imagen supervisadamente. Medir antes/después en población VAL fijada: cosenos imagen-texto, clasificación por prompts congelados, ranking de conceptos y similitud entre embeddings originales/ajustados. CKA puede complementar comparación geométrica, pero no demuestra alineación con texto ni calidad diagnóstica. Conservar encoder original como baseline. Mantener capacidad original consultable no equivale a que el encoder ajustado conserve su rendimiento; reportar ambos estados. Regularización/distilación multimodal sería otra decisión científica, fuera del mínimo inicial.

## 10. EVALUATE y TEST

**VERIFICADO:** `python -m src.evaluate` y `python -m src.test` delegan en `M/assessment/cli.py:main`. Seleccionan por `--campaign-id`/`--source-training-run-id`, exigen TRAIN completed y `lineage.resolve` revalida sesión/checkpoint/calibración. Split fijo VAL/development o TEST/final. No exigen EVALUATE ni EXPLAIN previos para TEST. Umbral `auto` recupera TRAIN; `clinical` exige calibración VAL; numérico queda protocolizado.

`KerasRuntime.__init__` carga con `tf.keras.models.load_model`; `images` verifica autorización, ruta y SHA de muestra; `predict` devuelve un score por imagen. `service.execute_reserved` escribe por batch; `contracts.prediction`, `verify_rows` reconstruyen predicción y métricas; repository mantiene transacciones y owner. Cada ejecución nueva produce intento/identidad nuevos. C§3.2 y §6 son reutilizables con runtime adaptado.

**Adaptación INFERIDA:** despachar runtime desde identidad persistida, sin seleccionar «latest» por nombre; implementar carga/predicción/transform para Torch e híbrido y ampliar origen para Zero-shot. Conservar mismas muestras, orden verificable, cardinalidad, hashes y decisión. Mantener umbral fijo antes de TEST. Para modelos compuestos, `service.verify` debe verificar todos los componentes, no sólo el archivo de cabeza.

La búsqueda de scripts encontró delegación de compatibilidad en `M/evaluation/evaluator.py` y `M/explainability/pipeline.py` hacia la CLI gobernada; ejecución de campañas por `src.campaign`/`execution.campaign`. Los servicios `B/services/explain_execution.py`, `explain_generation.py` y `representation_generation.py` orquestan operaciones HTTP mediante los mismos prepare/reserve/execute. No se identificó un wrapper shell independiente que habilite PyTorch o quite dependencia de TRAIN; los scripts de pruebas no son rutas productivas alternativas.

### Métricas y comparabilidad

**VERIFICADO, `M/assessment/contracts.py:metrics`, `verify_rows`, `M/evaluation/clinical_metrics.py:_safe_roc_auc`, `_safe_pr_auc`.** Conteos TP/TN/FP/FN, Recall, Specificity, Precision, F2, Accuracy y confusión son comunes. TEST añade F1, balanced accuracy, ROC-AUC y PR-AUC. PR-AUC usa **average precision**, no área trapezoidal: mantener definición al comparar. VAL independiente no añade automáticamente las mismas claves; no inventarlas en UI ni reescribir hashes históricos.

**INFERIDO, criterio científico:** las ocho métricas pedidas son comparables en TEST con los mismos sample_id, labels, dataset_version, pacientes, clase positiva, protocolo y regla de decisión. Umbrales pueden diferir si cada política se fijó en VAL; informarlos. ROC-AUC/AP requieren scores continuos orientados a parasitada, no labels predichos. Softmax Zero-shot permite ordenar casos, sin acreditar calibración. Denominadores vacíos o clase ausente deben generar N/A, no cero fabricado. No comparar fiabilidad/Brier/ECE como si score de similitud fuese probabilidad calibrada.

SQL observado: dataset `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`: TRAIN 22.180/161 pacientes, VAL 2.693/20, TEST 2.685/20. Existe otra versión `f0c1f636-715c-54e2-8e46-ed150f9d8791`: 770/95/100 imágenes. **No mezclar versiones por compartir clases.** La consulta acredita conteos, no una nueva certificación de disjunción; reutilizar gobernanza/validación SAME SPLIT. Comparaciones inferenciales deben agrupar por paciente; bootstrap/IC se declarará derivado con fuentes, no evidencia ya ejecutada.

## 11. EXPLAIN, representaciones y conceptos biomédicos

### 11.1 Matriz XAI

Soporte actual **VERIFICADO** en `M/assessment/runtime.py:explain`, `M/explainability/{gradcam,pipeline,lime_explainer,shap_explainer}.py`, `service.py:explanation_spec`. Factibilidad nueva **INFERIDA**; ejecución BiomedCLIP **PENDIENTE DE PRUEBA** en todas las filas. Contrato C§3.2/§5/§6, con correcciones de §6.2.

| Método | Actual | Zero-shot | Linear híbrido | Fine-tuning | Recomendación/limitación |
|---|---|---|---|---|---|
| Grad-CAM | GradientTape/Keras y selección convolucional | Adaptar a ViT y score objetivo | No hay gradiente a través de NumPy; puente necesario | Adaptar a ViT/Torch | Reemplazar implementación TF para nuevos modelos, mantener método/capa/target explícitos |
| Atribución de tokens/gradientes integrados | Sin método público específico en CLI | Adaptación nueva | Puente differentiable o no disponible sobre imagen | Adaptación nueva | No llamar Grad-CAM a otro método; declarar baseline y reducción espacial |
| Attention rollout | No disponible en ruta inspeccionada | Nuevo método exploratorio | Describe encoder, no necesariamente decisión de cabeza | Nuevo método exploratorio | No equivalente a Grad-CAM/SHAP ni evidencia de causalidad |
| LIME imagen | Wrapper de predicción TF; algoritmo externo | Reutilizar algoritmo con callable Torch | Reutilizar callable compuesto | Reutilizar callable Torch | Perturbar imagen en dominio correcto, reaplicar transform exacto y devolver Nx2 scores |
| SHAP GradientExplainer | Modelo Keras diferenciable y referencias gobernadas | Adaptación módulo Torch | Cabeza: SHAP de embeddings; imagen requiere puente | Adaptación módulo Torch | Identificar expected gradients; validar autograd, shapes, dispositivo y coste |
| Embeddings/PCA/UMAP | GAP Keras; matrices persistidas | Adaptar a vector proyectado | Adaptar a vector congelado | Adaptar a vector ajustado | Reutilizar `save_arrays`, `project`, verificación y rows; actualizar specification |
| CKA | Ya implementada sobre matrices y sample_id comunes | Reutilizar cálculo | Reutilizar cálculo | Reutilizar cálculo | Misma población/orden; no equiparar similitud geométrica con explicación clínica |
| Distribución de scores | Resultados por muestra disponibles | Reutilizar como distribución de scores | Reutilizar | Reutilizar | No etiquetar automáticamente como confianza calibrada |
| Conceptos biomédicos | Sin productor inspeccionado de conceptos textuales | Nuevo consumidor del encoder textual | Original conserva capacidad | Comparar original/ajustado | Similitud descriptiva, no anotación experta ni diagnóstico |

La [guía del autor de pytorch-gradcam para ViT](https://jacobgil.github.io/pytorch-gradcam-book/vision_transformers.html) describe reshape de tokens a malla espacial y elección de capa anterior al bloque final para evitar gradientes nulos en patches. Para ViT-B/16 a 224, la malla propuesta es 14×14; validar estructura real de timm y tokens especiales tras carga. La salida debe mapearse al crop original; un overlay estirado sobre la imagen completa puede localizar erróneamente regiones.

[SHAP GradientExplainer](https://shap.readthedocs.io/en/latest/generated/shap.GradientExplainer.html) admite `torch.nn.Module`, pero esa documentación no certifica el conjunto BiomedCLIP/MPS. Para Linear, una copia algebraicamente equivalente de la cabeza Keras en Torch podría permitir gradientes sobre imagen **sólo tras probar paridad de outputs y pesos**, sin nuevo entrenamiento y con identidad de transformación; mientras tanto declarar gradientes de imagen no disponibles. SHAP sobre 512 embeddings no debe presentarse como mapa de píxeles.

[Attention rollout/flow](https://aclanthology.org/2020.acl-main.385/) aproxima flujo entre tokens; pesos de atención por sí solos no son explicaciones fiables de la decisión. Capturar atención puede requerir desactivar una implementación fusionada y cambiar consumo/rendimiento: medir y registrar. [LIME](https://lime-ml.readthedocs.io/en/latest/lime.html) permite callback de predicción; la segmentación y perturbaciones deben conservarse en protocolo para repetir la explicación.

### 11.2 Selección y recuperación

**VERIFICADO**, `service.select_explanation_samples`, `explanation_spec`, CLI y servicio HTTP: limitar imágenes no equivale al número de perturbaciones (CLI LIME/SHAP 1.000–5.000). Distinguir `sample_id` explicado de `background_sample_id`; background pertenece al split autorizado. Preservar selección determinista, método/clase/capa, intento, checkpoint y hashes. Reutilizar recuperación autenticada de artefactos existente en backend; no exponer rutas arbitrarias ni nuevos accesos directos a archivos.

**VERIFICADO**, `representation_spec` fija GAP y `represent_reserved` lee `runtime.layer.name`; `ScientificRepresentations` y servicio buscan coincidencia de esa especificación exacta. **Recomendación INFERIDA:** descriptor de representación por arquitectura (espacio, capa/proyección, normalización, dimensión, versión), sin fingir una GlobalAveragePooling2D en ViT. Los cuatro roles actuales permiten matrices; nuevos roles de tokens/conceptos requieren extensión explícita de validación, no su inserción como si fueran PCA.

## 12. Reporte A y Comparación Científica

**VERIFICADO:** `B/services/scientific_results.py:ScientificReadService.read` exige TRAIN para trazabilidad SCC; `scientific_report.py:ScientificReportService.read` y schemas/selecciones usan `training_run_id`; `scientific_preflight.py` valida checkpoint y población. `B/repositories/scientific_results.py` ofrece `comparison_catalog`, `comparison_checkpoint`, `comparison_epochs`, `comparison_predictions`, `comparison_representation`. Frontend: `F/pages/CampaignsReport.tsx`, `ModelComparison.tsx`, `F/components/reports/{ScientificReport,ScientificRepresentations,TrainingRunGroupCard,AnalysisWorkspace}.tsx` y tipos asociados. No crear un reporte paralelo BiomedCLIP.

| Dimensión | Evidencia/reutilización | Adaptación recomendada (INFERIDA) |
|---|---|---|
| A: identidad/linaje | Modelos, versiones, hashes, TRAIN y assessments | Presentar origen externo para Zero-shot; eliminar JOIN/DTO obligatorio a TRAIN sólo en esa rama |
| A: aprendizaje | epoch/runtime/phase/selection | Linear muestra aprendizaje de cabeza; Fine-tuning fases reales; Zero-shot N/A, sin curva vacía presentada como fallo |
| A: comportamiento predictivo | assessment_results, verification, confusión | Mismas métricas; diferenciar similitud/score/probabilidad, explicitar umbral/prompts |
| A: evidencia visual | assessment_artifacts y recuperación existente | Método compatible y objetivo; «Sin evidencia» si no generado; no afirmar atención al parásito sin anotación |
| A: representaciones | REPRESENT/PCA/UMAP + CKA de lectura | Adaptar especificación y etiquetas del espacio; misma población |
| A: asociaciones biomédicas | No productor textual constatado | «Sin evidencia» hasta productor con conceptos/prompts/revisión/hash y scores trazables |
| A: preguntas/conclusiones | `scientific_report.py:superiority_answer`, consenso/población | Distinguir preentrenamiento externo, linear probe y fine-tuning; no atribuir aprendizaje local a Zero-shot |
| Comparación: métricas/confusión | Módulos catalog/metrics; TEST tiene métricas ampliadas | Reutilizar conteos y definiciones; exigir población común acreditada |
| Comparación: curvas | Módulo curves | Mostrar sólo entrenables; indicar loss/optimizer distintos aunque claves coincidan |
| Consenso/desacuerdo/errores complementarios | `scientific_report.py:consensus`, resultados por sample_id | Reutilizar categorías TP/TN/FP/FN y desacuerdos; cobertura explícita; nunca juntar por posición de fila |
| Diferencias de arquitectura | run_configurations + identidad | Encoder/revisión/prompts, espacio de features, bloques entrenables, framework y dispositivo |

`ScientificReport.tsx` ya muestra «Sin evidencia» para valores nulos y «No aplica» en algunas dimensiones. **Recomendación INFERIDA:** distinguir N/A (Zero-shot sin entrenamiento) de evidencia faltante y artefacto inválido. `scientific_report.py` ya advierte que score extremo no acredita calibración; extender esa semántica a Zero-shot. No convertir N/A en cero para gráficos/rankings. Los reportes deben revalidar integridad de binarios antes de afirmar disponibilidad (C§5); filas verified no bastan.

## 13. Observación opcional de imágenes durante TRAIN

**VERIFICADO documentalmente**, [PyTorch Dataset/DataLoader](https://docs.pytorch.org/docs/2.14/data.html): el loop recibe los batches producidos por el dataset; puede acceder a sus tensores. **INFERIDO:** Linear permite observar la imagen transformada en el paso de extracción; Fine-tuning permite observar tensores justo antes del forward. Los IDs originales no vienen automáticamente en todo DataLoader: dataset/collate deben retornarlos si se desea vincularlos.

Observar en memoria es sencillo con instrumentación puntual. Prefetch, workers, augmentation y batches descartados impiden equiparar «cargada por Dataset» con «usada por optimizer.step». Demostrar consumo histórico individual exige más instrumentación y persistencia; no surge gratis de PyTorch. El repositorio continúa mostrando consumo individual TRAIN como no demostrado. **Recomendación:** cerrar este punto como oportunidad de depuración, no requisito de integración. No crear tablas, logs ni manifiestos exclusivos; no reabrir la investigación negativa de modelos anteriores. **PENDIENTE DE PRUEBA** sólo la visualización operativa, sin bloquear 01B.

## 14. Brechas y riesgos priorizados

Las evidencias de archivo/función y contrato se encuentran en las secciones referenciadas; la prioridad es recomendación **INFERIDA**.

| ID | Brecha / riesgo | Evidencia y estado | Impacto / acción |
|---|---|---|---|
| B01 | Origen externo inexistente | §3.3/§7; SQL y lineage.resolve, VERIFICADO; C§1/3.2 | Bloquea Zero-shot. Diseñar discriminante y restricciones sin TRAIN ficticio |
| B02 | Dominios SQL cerrados | §3.3; CHECKs architecture/weights/normalization, VERIFICADO | Bloquea entrenables. Ampliación explícita en futura implementación |
| B03 | Catálogo exige entrenable para todas las filas | §3.2; `_registry`, VERIFICADO | Zero-shot puede romper creación de campañas; separar visibilidad/capacidad |
| B04 | Input y serialización Keras | §§3/5/6/10, VERIFICADO; C§3.1/5 | Pesos originales/resize no compatibles; runtime/contrato/loader por formato |
| B05 | Checkpoint parcial de Linear | §8, INFERIDO desde firma y carga actuales | Cabeza sola no basta; manifest/binding compuesto y prueba offline |
| B06 | PyTorch/OpenCLIP no probado | §5, VERIFICADO entorno; PENDIENTE ejecución | Fijar dependencias y medir antes de campañas completas |
| B07 | Fuga TEST / selección de prompts | §§7–10, INFERIDO | Congelar prompts/umbral/checkpoint en TRAIN/VAL; TEST independiente |
| B08 | Score relativo tratado como probabilidad calibrada | §3.3/§7/§10, VERIFICADO contrato e INFERIDO riesgo | Semántica explícita; softmax no equivale a calibración |
| B09 | Gradiente inter-framework roto | §8/§11, INFERIDO | LIME primero; puente validado o N/A para gradientes de imagen |
| B10 | Pérdida de alineación visual-textual | §9, INFERIDO | Preservar original y medir original/ajustado con prompts fijos |
| B11 | Documentación antigua induce duplicación | §6.2, VERIFICADO | Reutilizar REPRESENT/CKA/XAI TEST actuales |
| B12 | Reportes obligan TRAIN/GAP | §11–12, VERIFICADO | Adaptar modelos de lectura y especificaciones antes de anunciar soporte |
| B13 | Confusión de archivo registrado vs disponible | C§5, §6.2, VERIFICADO límite de auditoría | Revalidar componentes físicos en 01B; no sobrescribir históricos |
| B14 | Framework/optimizer iguales nominalmente, distintos numéricamente | §§5/9, INFERIDO | Registrar implementación, versiones y grupos LR; comparar evidencia, no nombres |
| B15 | H-01 por referencia/standalone y proyecciones SCC | §6.2, código VERIFICADO | Probar ambas rutas o delimitar soporte inicial a coordinador; no certificar todas por una sola |
| B16 | Restricción clínica/cambio de dominio | Ficha oficial y §§5/10, VERIFICADO documental; transferencia PENDIENTE | Investigación de células malaria, sin afirmar validación asistencial |

## 15. Propuesta mínima por fases y decisiones pendientes

Propuesta **INFERIDA** basada en la evidencia anterior. Ninguna fase comenzó.

1. **Contratos y diseño de 01B:** aprobar origen externo exclusivo Zero-shot; formato/binding del modelo compuesto; input original y semántica de scores; especificación de representaciones. Revisar CHECKs/triggers identificados, sin compatibilidad histórica de esquemas ni tablas nuevas por defecto. Elegir cómo vincular el baseline Zero-shot con la campaña en contexto de evaluación, excluyéndolo de la matriz TRAIN.
2. **Prueba técnica MPS y dependencias:** entorno reproducible Python 3.12; OpenCLIP/Transformers/timm compatibles; descarga del original sólo cuando 01B esté autorizado. Fijar revisión/hash de todos los insumos. Probar CPU/MPS, recarga y gradientes antes de entrenar campañas completas.
3. **Infraestructura común + Zero-shot:** dispatch por framework/formato, registro de capacidades, origen preentrenado y evaluaciones independientes con umbral fijo. Persistencia y reportes deben aceptar este origen sin ejecutar TRAIN.
4. **Linear:** extracción congelada, cabeza Keras, pipeline reconstruible y eventos de campaña. Evitar caché durable inicial. Validar selección VAL y TEST independiente.
5. **Fine-tuning:** loop Torch, fases/optimizer/parada, artefactos por época y cierre E10 equivalente. Medir alineación y preservar baseline original.
6. **XAI y reportes:** LIME, representaciones/proyecciones/CKA; Grad-CAM/SHAP tras pruebas de objetivos y gradientes. Métodos de tokens/rollout/conceptos pueden quedar declarados sin evidencia hasta un alcance aprobado. Regresión de modelos actuales y rutas CLI/HTTP.

Decisiones pendientes explícitas: (a) diseño exacto de constraints del origen externo; (b) paquete único o binding multicomponente; (c) matriz final de versiones; (d) scope de ajuste de bloques/proyección y política de LR; (e) prompts y política de umbral Zero-shot; (f) puente de gradientes Linear o N/A inicial; (g) requisitos de rendimiento medidos antes de elegir batch; (h) asociación de Zero-shot a una campaña para reportes sin miembro TRAIN. No se requiere decidir una caché durable ni observación individual TRAIN para avanzar.

## 16. Protocolo operativo y criterios de aceptación BIOMEDCLIP-01B

Todo este apartado es **PENDIENTE DE PRUEBA**, requiere autorización posterior. No constituye resultado experimental de 01A.

### 16.1 Medición GPU, memoria, throughput y tiempos

1. Registrar host/OS/RAM, Python y paquetes exactos, build y disponibilidad MPS, device real de parámetros/entradas/salidas, dtype, seeds, threads/workers, transform, revisión/hash de pesos. Verificar modelo original cargable con claves/shapes esperadas y tokenizer correcto.
2. En conjunto gobernado pequeño de TRAIN/VAL, separado por finalidad, comparar CPU y MPS FP32: embeddings, logits/scores y predicción. Tolerancia propuesta inicial `atol=1e-4`, `rtol=1e-3`, a justificar si falla; cualquier discrepancia de clase próxima al umbral se registra, no se oculta. No usar TEST para elegir configuración.
3. Medir por separado decode/transform, transferencia, forward visual, texto, similitud, copia hacia Keras, fit cabeza, forward/backward/step fine-tuning, checkpoint/recarga y XAI. Desglosar arranque frío y régimen estable.
4. Probar batches 1/8/16/32 y aumentar sólo con margen medido. Tras al menos 5 batches de warmup, medir 30 batches o la población disponible, con 3 repeticiones. Sincronizar MPS antes/después de intervalos GPU; usar reloj monotónico. Reportar tamaño efectivo, mediana/p95 de latencia, imágenes/s, duración de época y coste de inicialización. Nunca atribuir decode CPU a aceleración GPU.
5. Muestrear `torch.mps.current_allocated_memory`, `driver_allocated_memory`, `recommended_max_memory`, RSS y presión/swap del host. Informar pico muestreado y frecuencia; no llamarlo pico exacto si el método no lo garantiza. Registrar por separado TensorFlow Metal en Linear. Ver [API MPS](https://docs.pytorch.org/docs/2.14/mps.html).
6. Usar profiler MPS/Metal para demostrar kernels GPU; registrar fallos por operación. Primera prueba sin fallback CPU; si se evalúa fallback, hacerlo como condición separada con coste y operaciones explícitas. `is_available=True` por sí solo no aprueba ejecución GPU.
7. Empezar FP32. Probar AMP sólo después de paridad; repetir semillas y documentar nondeterminismo. Limitar XAI a pocas muestras VAL con identidad fija inicialmente; medir su coste separado. Definir batch operativo a partir de evidencia y margen de memoria, sin prometer throughput previo.

### 16.2 Criterios verificables

| Criterio | Evidencia exigida para aprobar |
|---|---|
| Registro y campañas | Tres UUIDs/nombres distintos; Zero-shot visible deshabilitado con motivo; rechazo backend/CLI de TRAIN Zero-shot; Linear/Fine-tuning generan matriz/miembros correctos |
| Original preservado | Revisión HF inmutable, hashes/bytes de pesos/config/tokenizer; reconstrucción sin depender de `main` o cache mutable |
| MPS | Carga/forward y, para Fine-tuning, backward/step en GPU, profiler, memoria/tiempos y diferencias CPU/MPS documentadas |
| Dataset | Misma versión, pacientes y splits; TRAIN/VAL sin acceso TEST; población TEST exacta por sample_id y hash |
| Linear | Encoder sin cambios de pesos; cabeza aprende sólo TRAIN; checkpoint VAL seleccionado; recarga de pipeline completo reproduce scores |
| Fine-tuning | Parámetros descongelados identificados; congelados invariantes; early stopping/selección reales; estado Torch recuperable y métricas verificables |
| Historial | Una evidencia real por época/fase; LR/optimizer/runtime; sin History artificial; checkpoints por época y selección exacta |
| Persistencia | Owner/transacciones/PK/FK/UNIQUE/CHECK/triggers respetados; inmutabilidad; fallos de integridad detectados; sin sobrescritura de resultados existentes |
| E10/SCC | Campaña cierra con artifacts/evaluations/run_clinical_metrics y completion atribuibles; probar ruta coordinador y delimitar ruta por referencia |
| Zero-shot sin TRAIN | EVALUATE/TEST/EXPLAIN con origen externo válido y cero RUN training artificial; entrenables siguen rechazando TEST sin TRAIN/checkpoint |
| Scores | Prompts/orden/escala/similitudes/regla reproducibles; score [0,1] declarado sin afirmación de calibración; umbral fijado antes de TEST |
| Evaluación | Métricas/confusión reproducibles desde predicciones; F1/F2/Recall/Specificity/Precision/Accuracy/ROC-AUC/AP sobre misma población |
| XAI | Método/capa/objetivo correcto, muestra/background distintos, determinismo razonable, mapa+overlay íntegros; puente Linear con paridad o N/A explícito |
| Representaciones | Especificación verdadera, row→sample_id, dimensión finita, hashes y cuatro roles; PCA/UMAP reutilizados; CKA sólo sobre población común |
| Reportes | Zero-shot con origen y N/A en aprendizaje; ningún JOIN obligatorio oculta resultados; ausencia/invalidación visible; métricas y consenso sin mezcla de versiones |
| Regresión | Custom CNN/VGG16/DenseNet121 conservan contratos; operaciones independientes y rutas de lectura funcionan; ningún histórico reescrito |
| Alcance opcional | Observación de tensores TRAIN no bloquea integración ni crea persistencia exclusiva |

Pruebas de restricciones y fallos de escritura se ejecutarán sólo en entorno de prueba autorizado, nunca mutando históricos científicos. No se exige iniciar campañas completas para validar primero carga, contratos y adaptadores.

## 17. Evidencia reproducible y cierre

### 17.1 Consultas de auditoría

Se ejecutaron consultas de lectura mediante:

```sh
docker exec -i capstone_db sh -c 'PGOPTIONS="-c default_transaction_read_only=on" psql -X -U "$POSTGRES_USER" -d "$POSTGRES_DB" -P pager=off'
```

No se imprimieron contraseñas. Consultas representativas ejecutadas:

```sql
SELECT current_database(), current_setting('transaction_read_only');
SELECT id,name,architecture,model_type,framework FROM models ORDER BY name;
SELECT table_name,column_name,data_type,is_nullable
FROM information_schema.columns
WHERE table_schema='public'
  AND table_name IN ('models','model_versions','artifacts',
                    'assessment_identities','assessment_artifacts','run_configurations')
ORDER BY table_name,ordinal_position;
SELECT conrelid::regclass,conname,pg_get_constraintdef(oid)
FROM pg_constraint WHERE connamespace='public'::regnamespace
  AND conrelid IN ('models'::regclass,'model_versions'::regclass,'artifacts'::regclass,
                  'runs'::regclass,'assessment_identities'::regclass,
                  'assessment_artifacts'::regclass,'train_execution_records'::regclass,
                  'run_configurations'::regclass);
SELECT pg_get_functiondef(oid) FROM pg_proc
WHERE pronamespace='public'::regnamespace
  AND proname IN ('assessment_identity_guard','assessment_attempt_guard',
                  'assessment_result_guard','enforce_model_version_governance',
                  'v2_configuration_guard','train_record_guard');
SELECT i.kind,i.identity->>'split',a.state,count(*)
FROM assessment_identities i JOIN assessment_attempts a ON a.identity_id=i.id
GROUP BY 1,2,3 ORDER BY 1,2,3;
SELECT role,count(*) FROM assessment_artifacts GROUP BY role ORDER BY role;
SELECT count(*) sessions,count(*) FILTER(WHERE state='verified') verified,
 count(*) FILTER(WHERE EXISTS(SELECT 1 FROM artifacts a
   WHERE a.run_id=s.run_id AND a.artifact_type='model_checkpoint')) registered
FROM train_execution_sessions s;
SELECT payload->'runtime_environment' FROM train_execution_records
WHERE kind='runtime' AND payload->'runtime_environment' ? 'accelerator' LIMIT 1;
SELECT dataset_version_id,split_name,count(*),count(DISTINCT clinical_identity_id)
FROM dataset_split_assignments GROUP BY 1,2 ORDER BY 1,2;
```

Resultados agregados observados: EVALUATE verified 9 VAL/5 TEST; EXPLAIN verified 45 VAL/6 TEST y 2 fallidos VAL; REPRESENT verified 3 VAL/2 TEST. TRAIN: 23 sesiones, 22 verified, 22 con artifact model_checkpoint; records: 492 epoch/artifact/artifact_prepared/selection/predictions, 35 runtime/phase, 23 calibration, 2.506 e10_event. Estos conteos no certifican integridad física ni compatibilidad BiomedCLIP.

Entorno inspeccionado con `importlib.metadata` bajo `PYTHONDONTWRITEBYTECODE=1`; consulta MPS:

```sh
PYTHONDONTWRITEBYTECODE=1 malaria_dl_local_project/.venv-metal/bin/python -c 'import torch; print(torch.__version__, torch.backends.mps.is_built(), torch.backends.mps.is_available())'
```

Resultado: `2.14.1 True True`. No se ejecutó entrenamiento ni inferencia. Lecturas de código mediante `cat`, `sed` y `rg`; documentación oficial enlazada en §§5, 11, 13 y 16. No se ejecutaron suites que pudieran crear intentos o alterar la BD; la validación de esta entrega es documental, de referencias y de alcance del diff.

### 17.2 Decisión de cierre 01A

Hay evidencia suficiente para decidir el registro de las tres arquitecturas, el plano de ejecución host MPS, la conservación del original, el ingreso de entrenables a campañas, la ampliación de origen Zero-shot, la reutilización de persistencia y los adaptadores requeridos para evaluación/XAI/reportes. La viabilidad operativa específica de BiomedCLIP, memoria y rendimiento quedan explícitamente pendientes del protocolo 01B.

**01A concluye con este informe. No se inicia 01B.** La recomendación es aprobar el diseño de contratos antes de implementar, mantener las identidades científicas existentes y verificar las tres variantes por separado, con evidencia real y sin entrenamientos ficticios.
