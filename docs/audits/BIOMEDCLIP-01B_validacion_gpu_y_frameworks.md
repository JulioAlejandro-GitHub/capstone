# BIOMEDCLIP-01B — Validación técnica de BiomedCLIP en GPU local

Fecha de ejecución: 2026-10-26, America/Santiago. Código de referencia: `41b6f572a132b0499c6883298f8f5a2483cb2232`.
Estado: **validación técnica mínima completada; integración productiva no realizada**.

## 1. Resumen ejecutivo

Se ejecutaron satisfactoriamente las tres variantes experimentales sobre el host Apple M4 Max:

| Variante / criterio | Resultado observado | Estado |
|---|---|---|
| Original oficial | Checkpoint cargado offline, revisión fijada y SHA-256 coincidente con LFS de origen | VERIFICADO |
| Zero-shot CPU/MPS | Embeddings, cosenos, logits y scores dentro de tolerancia; sin cambios de clase en las entradas comparadas | VERIFICADO |
| Ejecución GPU | Tensores y resultados `mps:0`, FP32, forward/backward y actualizaciones reales, fallback CPU deshabilitado | VERIFICADO |
| Linear | Encoder congelado + Dense Keras de una salida; 3 épocas; recarga del pipeline con diferencia máxima de score 0 | VERIFICADO |
| Fine-tuning | Actualización de cabeza y después del bloque visual 11; 12 tensores del bloque cambiaron, congelados invariantes; recarga con diferencia 0 | VERIFICADO |
| XAI preliminar | Gradientes sobre imagen, embedding y tokens visuales; LIME con pipeline híbrido completo | VERIFICADO |
| REPRESENT preliminar | Embeddings finitos de 512 dimensiones; reutilización efectiva de CKA existente | VERIFICADO |
| Registro Zero-shot en PostgreSQL | Diseño de Opción B contrastado con constraints/triggers; no ejecutado | VERIFICADO como diseño; PENDIENTE DE PRUEBA de implementación |
| Ausencia de modificaciones productivas | Sin cambios propios en código/paquetes productivos; SQL sólo lectura. Hubo actividad concurrente de EXPLAIN, detallada en §14 | VERIFICADO dentro de los controles descritos |

**Recomendación:** avanzar a una fase 01C explícitamente autorizada para implementar contratos y adaptadores. La evidencia permite elegir PyTorch/OpenCLIP para Zero-shot y Fine-tuning, y PyTorch + cabeza Keras para Linear. No demuestra rendimiento clínico, estabilidad de campañas largas, calibración ni soporte EXPLAIN completo.

La Opción B aprobada por el usuario reemplaza el diseño alternativo de 01A: el origen Zero-shot tendrá posteriormente `runs.run_type='training'`, pero significará **registro verificable de un modelo preentrenado, sin optimización local**. Se conservará `source_training_run_id`, diferenciando el origen mediante un discriminante obligatorio y verificadores específicos. No se creó ese RUN en 01B.

## 2. Documentos leídos, contratos y alcance

Se leyeron íntegramente antes de las pruebas:

1. [Contrato de artefactos científicos y persistencia](../architecture/capstone_scientific_artifacts_and_persistence.md), encabezado, §§1–8 y nota final.
2. [Auditoría BIOMEDCLIP-01A](BIOMEDCLIP-01A_auditoria_integracion.md), §§1–17 completos.

Se retomaron los hallazgos sin repetir la auditoría. Permanecen vigentes PostgreSQL como fuente productiva de verdad, identidad de muestras/pacientes, separación de splits, hashes, inmutabilidad de históricos y reconstrucción del modelo completo. Los binarios experimentales y sus manifiestos se mantienen **fuera de la persistencia científica productiva**, conforme a la autorización específica de 01B.

Las discrepancias documentales identificadas en 01A siguen siendo relevantes: REPRESENT/PCA/UMAP/CKA y EXPLAIN TEST ya existen en código. No se construyó una alternativa. Se utilizó la función pura `linear_cka` existente para una comparación descriptiva.

La instrucción actual prevalece sobre dos recomendaciones anteriores: TRAIN debe **omitir** Zero-shot y continuar, no abortar toda la selección; el origen usará un RUN `training` explícito, no una FK nullable a un origen sin RUN. Ambos cambios se documentan en §12 y permanecen sin implementar.

Estados utilizados: **VERIFICADO** = ejecución o evidencia estática identificada; **FALLIDO** = prueba intentada sin satisfacer el objetivo; **PENDIENTE DE PRUEBA** = no ejecutado; **NO APLICA** = no corresponde al alcance o modalidad. Un diseño verificado contra código no significa que su implementación haya pasado pruebas.

## 3. Entorno experimental efectivo y aislamiento

| Elemento | Observado |
|---|---|
| Host | Apple M4 Max, arm64 |
| Memoria unificada | 51.539.607.552 bytes, 48 GiB |
| Sistema | macOS 26.7.1, build 25G241 |
| Python | 3.12.13 |
| Entorno productivo inspeccionado | `malaria_dl_local_project/.venv-metal` |
| Entorno experimental | `/Users/julio/.cache/capstone-biomedclip-01b/venv` |
| Binarios experimentales | `/Users/julio/.cache/capstone-biomedclip-01b/` |
| Evidencia pequeña versionable | [`evidence/biomedclip_01b/`](evidence/biomedclip_01b/) |
| Scripts | [`scripts/experiments/biomedclip_01b/`](../../scripts/experiments/biomedclip_01b/) |
| Device / precisión | PyTorch MPS FP32; cabeza Keras TensorFlow Metal |
| Semilla | `20261026` para Python, NumPy, Torch y Keras según proceso |
| CPU de benchmark | Torch con 4 threads |
| Fallback | `PYTORCH_ENABLE_MPS_FALLBACK=0`, antes de importar Torch |
| Red en ejecución del modelo | `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` |

Se creó una copia independiente APFS mediante `cp -cR` del venv existente y se invocó siempre su **Python explícito con `-m pip`**; no se usaron los shebangs copiados de ejecutables pip. `sys.prefix` resolvió al entorno experimental. Se instalaron dependencias únicamente en esa copia. Una reproducción portable debe crear un venv nuevo y usar el lock, no depender de copiar un venv de otra máquina.

[Paquetes productivos antes](evidence/biomedclip_01b/production_environment_before.txt) y [después](evidence/biomedclip_01b/production_environment_after.txt) son idénticos. No se modificaron `.env`, launchers productivos, backend, frontend, esquema o registros de experimentos. No se creó campaña ni se ejecutó `src.train`, `src.evaluate`, `src.test` o `src.explain` productivo.

### Muestras gobernadas

Dataset `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`, estado SQL `FROZEN`, materialización `READY/PASS`.

- TRAIN: 16 imágenes, 8 por clase.
- VALIDATION: 8 imágenes, 4 por clase.
- Selección determinista: primeros UUID por split/clase, sin optimizar selección por resultado.
- Se comprobó SHA-256 de cada archivo frente a `dataset_source_records` antes de uso.
- Consulta de asignaciones: cero pacientes con más de un split en esa versión; además se verificó intersección vacía de pacientes TRAIN/VAL seleccionados.
- Se preservan `dataset_version_id`, `sample_id`, `patient_id`, label, split, ruta y hash en [samples.json](evidence/biomedclip_01b/samples.json).
- **No se abrió ninguna imagen TEST.** Sólo se consultaron asignaciones para validar disjunción por paciente.

`prepare.py` limita la selección SQL a TRAIN/VAL y reproduce la regla de filename con prefijo UUID si hay colisiones. Los procesos de cálculo no abren conexiones PostgreSQL. Las consultas de preparación y control se ejecutaron con `default_transaction_read_only=on`.

## 4. Dependencias resueltas y reproducibilidad

| Paquete | Versión efectiva |
|---|---|
| torch | 2.14.1 |
| torchvision | 0.29.1 |
| open_clip_torch | 3.3.0 |
| transformers | 4.57.6 |
| timm | 1.0.30 |
| huggingface-hub | 0.36.2 |
| tokenizers | 0.22.2 |
| safetensors | 0.8.0 |
| hf-xet | 1.7.0 |
| regex | 2026.9.29 |
| ftfy / wcwidth | 6.3.1 / 0.9.4 |
| tensorflow / tensorflow-metal | 2.17.1 / 1.2.0 |
| keras | 3.15.1 |
| numpy | 1.26.4 |

Se consultaron la [ficha oficial](https://huggingface.co/microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224) y las [dependencias de OpenCLIP](https://github.com/mlfoundations/open_clip/blob/main/pyproject.toml). No se copiaron automáticamente los pins antiguos para Python 3.10. Se resolvió primero con `pip --dry-run`, después se instaló la combinación indicada en el venv aislado. **`pip check`: `No broken requirements found.`** La compatibilidad declarada fue seguida por carga y ejecución reales.

Evidencia: [plan](evidence/biomedclip_01b/dependency_plan.json), [instalación](evidence/biomedclip_01b/dependency_install.json), [log](evidence/biomedclip_01b/dependency_install.log), [pip check](evidence/biomedclip_01b/pip_check.txt) y [lock completo](evidence/biomedclip_01b/requirements.lock.txt). Los JSON de pip incluyen procedencia y hashes de distribuciones nuevas. El lock congela versiones de todo el entorno, incluidas dependencias heredadas; no es un wheelhouse completo ni un lock con hashes de todas ellas.

**VERIFICADO:** esta combinación funciona en las pruebas realizadas. **PENDIENTE DE PRUEBA:** instalación limpia del lock en otra máquina, actualizaciones de versiones, AMP y otros sistemas operativos. Integrarla en el entorno productivo deberá ser una decisión de 01C con regresión, no copiar paquetes sin validar.

## 5. Identidad y conservación del modelo original

Repositorios y revisiones exactas:

- BiomedCLIP: `microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224`, revisión **`9f341de24bfb00180f1b847274256e9b65a3a32e`**.
- Configuración/tokenizer de texto: `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract`, revisión **`d673b8835373c6fa116d6d8006b33d48734e305d`**.

| Componente | Bytes | SHA-256 |
|---|---:|---|
| `open_clip_pytorch_model.bin` | 783705670 | `52cc993c5c5ff962bd0c60931874bc001e7e9b41666a385530f4a036294576be` |
| `open_clip_config.json` | 707 | `9a41f334a8c444678772c0ebb9ab854c97ab350bced3a17b803e258d39c23dc0` |
| Texto `config.json` | 385 | `56bab767c02bc792897638feb8addc06d483d9c73769a5f554bbabea1f5507a1` |
| `tokenizer_config.json` | 28 | `53b6f42b8b8daddbdc6d3532c324187a92b46c1602bd6e8d4ad5a413b4fc90e1` |
| `vocab.txt` | 225062 | `7b36651908a88bc38bda41b728b2a598191e0d3b553cbacf7b1e5f026d5b5b9f` |

[original_assets.json](evidence/biomedclip_01b/original_assets.json) contiene rutas y hashes. El hash del checkpoint se comparó también con el SHA-256 LFS publicado; los archivos pequeños se fijan por revisión y hash local. `prepare.py` quedó con revisiones explícitas para reproducciones, sin resolver nuevamente `main`.

`common.load()` conserva la configuración original en disco y adapta únicamente en memoria las rutas HF de texto a los archivos locales fijados. Desactiva carga de pesos independientes de PubMedBERT: **los pesos de ambos encoders provienen del checkpoint BiomedCLIP completo**, no de una segunda descarga de BERT. Usa el constructor OpenCLIP y su carga del checkpoint; la reconstrucción funcionó offline. No se convirtió BiomedCLIP a Keras.

Se observaron **195.902.721 parámetros**, encoder visual ViT-B/16, bloques visuales `visual.trunk.blocks`, encoder textual BERT biomédico, embeddings proyectados de 512 dimensiones y contexto de tokenización 256. Tensores visuales `[N,3,224,224]`, tokens visuales de la capa inspeccionada `[N,197,768]`.

Transformación efectiva registrada:

```text
RGB → Resize(224, bicubic, antialias=True) → CenterCrop(224,224)
→ tensor CHW float32 → Normalize
mean = [0.48145466, 0.4578275, 0.40821073]
std  = [0.26862954, 0.26130258, 0.27577711]
```

Embeddings normalizados L2 mediante `encode_image(..., normalize=True)`; norma observada 0,99999994–1,0. Configuración, pesos, vocabulario y hashes se revalidan al cargar y al cierre. **VERIFICADO:** los archivos originales conservaron sus hashes tras fine-tuning. Los pesos ajustados se guardaron en otro archivo.

## 6. Zero-shot: ejecución y semántica

Evidencias: [zero_shot.json](evidence/biomedclip_01b/zero_shot.json), [suplemento balanceado](evidence/biomedclip_01b/supplement.json), scripts `zero_shot.py` y `supplement.py`.

Prompts exactos, fijados antes de ejecutar y sin búsqueda posterior:

```text
0: a microscopy image of an uninfected red blood cell.
1: a microscopy image of a red blood cell infected with malaria parasites.
```

Clase positiva = 1, parasitada. Idioma inglés, contexto 256, padding/truncación por el tokenizer fijado. Se conservaron IDs de tokens. No se empleó ensemble de prompts ni calibración de probabilidad.

Regla ejecutada: `v` y `t` normalizados → `cosine = v @ t.T` → `logits = exp(logit_scale) * cosine` → `softmax(logits, dim=-1)` → score de columna 1 → predicción positiva si `score >= 0.5`. Escala observada **85,2322769165**. Softmax se informa como **score relativo a estos dos prompts**, no probabilidad clínicamente calibrada.

La comparación inicial utilizó 8 muestras TRAIN; por el orden determinista eran las 8 de la clase parasitada. Se agregó una comparación separada sobre las **8 VALIDATION balanceadas**. Ambos conjuntos usaron exactamente los mismos tensores preprocesados en CPU y MPS, sin cambio de prompts o umbral.

**VERIFICADO:** carga visual/textual, tokenización, coseno, logits/escala, softmax, orientación positiva y predicción; resultados finitos. Los arrays CPU/MPS y embeddings ajustados se guardaron en `parity_and_representations.npz`, con hash/ruta en el suplemento. Las sucesivas reconstrucciones del encoder produjeron embeddings idénticos en MPS en la prueba Linear. No se exige ni se concluye precisión clínica mínima.

## 7. Linear: encoder congelado y cabeza Keras

[linear.json](evidence/biomedclip_01b/linear.json) y [linear.log](evidence/biomedclip_01b/linear.log) contienen resultados efectivos.

- Entrada a la cabeza: **`[None,512]`**, no imágenes NHWC.
- Cabeza: una única `Dense(1, activation='sigmoid')`, sin capas ocultas: regresión logística sobre embeddings, con logit afín lineal.
- Optimizador SGD Keras, learning rate 0,1, BCE; semilla 20261026.
- Tres épocas, un batch completo de las 16 muestras TRAIN por época. VALIDATION separada de 8 muestras; sin augmentation ni TEST.
- Encoder en `eval()`, `requires_grad_(False)`. Se compararon hashes de todo su state_dict antes y después: **sin cambios**.
- Variables de la cabeza en `/job:localhost/replica:0/task:0/device:GPU:0`; TensorFlow identificó Apple M4 Max/Metal en el log.

| Época | Loss TRAIN real | Loss VAL real | Accuracy VAL descriptiva |
|---:|---:|---:|---:|
| 1 | 0,68988061 | 0,68606949 | 0,750 |
| 2 | 0,68856215 | 0,68514407 | 0,750 |
| 3 | 0,68724835 | 0,68422198 | 0,875 |

Se guardaron tres checkpoints de cabeza separados, sin sobrescritura. Se seleccionó época 3 por menor loss VAL. Estas métricas son de un ensayo técnico diminuto; no son una estimación de generalización. No se aplicó early stopping.

Checkpoint seleccionado: `linear_epoch_3.keras`, 16.872 bytes, SHA-256 `3168f4b07220711fd56396291f12bb879ec9058be705bc897adcec0167891633`.

Se reconstruyeron **encoder y cabeza** a partir de archivos, se volvieron a procesar las imágenes y se compararon los scores VAL. Diferencia máxima = **0**; embeddings recargados también diferencia **0**. No se evaluó sólo una cabeza con un embedding supuesto.

[Manifiesto compuesto experimental](evidence/biomedclip_01b/linear_composite_manifest.json): referencia al manifiesto original con hash, cabeza/hash/bytes, dimensión 512, normalización L2, transformación, clase positiva, mapping y umbral. Es evidencia de reconstrucción de 01B, **no un nuevo contrato productivo**. Demuestra por qué una cabeza `.keras` aislada no representa el clasificador completo.

## 8. Fine-tuning: actualizaciones reales y recuperación

[fine_tuning.json](evidence/biomedclip_01b/fine_tuning.json), script `fine_tuning.py`. Se usaron dos imágenes TRAIN, una por clase, para cada paso. Encoder inicial original, cabeza Torch `Linear(512,1)`, BCE con logits, FP32, AdamW con weight decay 0.

1. Encoder completo congelado, LR cabeza `1e-3`: un forward/backward/step. Cambiaron los pesos de la cabeza; **ningún tensor del encoder cambió**.
2. Se descongeló exclusivamente **`visual.trunk.blocks.11`**, LR visual `1e-5`, manteniendo LR cabeza `1e-3`: un segundo forward/backward/step.
3. Los **12 tensores entrenables del bloque** cambiaron; los demás parámetros/buffers del modelo permanecieron idénticos por hashes. Nombres completos en el JSON. El encoder textual y la proyección fuera del bloque permanecieron congelados.

| Paso | Loss real | Forward | Backward | Optimizer step |
|---|---:|---:|---:|---:|
| Sólo cabeza | 0,68542385 | 0,35635 s | 0,00358 s | 0,12865 s |
| Cabeza + bloque 11 | 0,68222141 | 0,25428 s | 0,98855 s | 0,09629 s |

Son pasos iniciales pequeños e incluyen costes de preparación/compilación; no describen una época estable. La torre permaneció en `eval()` para desactivar dropout mientras se habilitaron gradientes del bloque. Esto es válido para la prueba controlada de actualización, pero **no certifica la futura receta completa en modo `train()`**.

Checkpoint experimental `fine_tuning.pt`: estado visual ajustado + cabeza + seed/nombres, **344.817.737 bytes**, SHA-256 `7c137f3b23f378e2a811e648182f6cef6736bdaecf74cb110e90690201e4c954`. Recarga en encoder reconstruido desde el original, `load_state_dict(..., strict=True)` para visual y cabeza. Scores antes/después: diferencia máxima **0**. Guardado 0,36064 s; carga del archivo 0,03317 s; reconstrucción original adicional 1,94832 s.

No se guardó el estado del optimizador para continuar entrenamiento: **VERIFICADO para reconstrucción de inferencia; PENDIENTE DE PRUEBA para reanudación exacta de entrenamiento**. El manifiesto general vincula checkpoint, script, configuración y original. No se generaron métricas o épocas ficticias.

El original siguió disponible e íntegro. El cambio de visual altera potencialmente la alineación con texto aunque el texto no cambie. Como observación preliminar, CKA original/ajustado sobre las 8 VAL = **0,9999981017**, tras sólo una actualización visual. No acredita conservación multimodal ni desempeño. Un protocolo posterior debe fijar población VAL, prompts/conceptos, transformaciones y comparar cosenos/rankings/zero-shot antes y después, además de geometría y rendimiento supervisado. TEST no debe orientar esos ajustes.

## 9. GPU, memoria, throughput y tiempos

### 9.1 Evidencia de ejecución efectiva

No se utilizó `mps.is_available()` como prueba suficiente. Se ejecutaron encoders visual y textual con parámetros/inputs/salidas en MPS, softmax, gradientes y optimizer steps; los resultados se sincronizaron con `torch.mps.synchronize()` antes/después de los intervalos medidos. No aparecieron errores de operación MPS no soportada; fallback CPU estuvo deshabilitado. Preprocesamiento y acceso a disco sí corresponden a CPU por diseño.

No se capturó una traza Instruments/Metal persistida. La evidencia aquí es ejecución de tensores/resultados/gradientes en MPS y actualizaciones reales sin fallback. Perfilado de kernels detallado queda **PENDIENTE DE PRUEBA** y no bloquea esta validación funcional.

### 9.2 Visual encoder, régimen caliente

Dos batches de warmup por tamaño/dispositivo, cinco mediciones sincronizadas; mediana. Entradas preprocesadas y transferidas antes del intervalo; no incluye texto, disco ni transferencia. Batches pequeños 1→4→8, sin presión observada de memoria. Es un microbenchmark, no un throughput de producción.

| Batch | CPU mediana | CPU imágenes/s | MPS mediana | MPS imágenes/s |
|---:|---:|---:|---:|---:|
| 1 | 25,444 ms | 39,30 | 7,430 ms | 134,59 |
| 4 | 75,506 ms | 52,98 | 17,694 ms | 226,07 |
| 8 | 135,919 ms | 58,86 | 30,289 ms | 264,12 |

Todos los tiempos individuales/p95 están en `zero_shot.json`. CPU usa cuatro threads: estos resultados no equivalen a comparar contra la máxima optimización CPU posible. No se probaron batches 16/32, entrenamiento largo ni repetición entre días; el protocolo propuesto en 01A era más amplio y se acotó aquí a la prueba mínima solicitada.

### 9.3 Costes de carga, arranque y etapas

| Operación | Medición |
|---|---:|
| Primera carga, incluyendo imports/inicialización y hashes | 95,80645 s |
| Cargas posteriores en otros procesos | 3,38052 s / 5,92194 s |
| Reconstrucción adicional en proceso caliente | ≈1,95 s |
| Preprocesamiento de 24 imágenes | 0,02204 s |
| Transferencia inicial del modelo CPU→MPS | 0,10990 s |
| Primer forward multimodal, 8 TRAIN, CPU | 0,20715 s |
| Primer forward multimodal, 8 TRAIN, MPS | 1,33417 s |
| Extracción MPS de 24 embeddings en batches de 4, incluyendo copia a CPU | 0,10763 s |
| Linear: tres épocas + validación + guardados | 0,94678 s |
| Sonda separada: primer train_on_batch Keras | 0,18666 s |
| Sonda separada: guardar/recargar cabeza | 0,00924 / 0,00882 s |
| LIME, 32 perturbaciones | 0,28831 s |

El primer forward MPS fue más lento que CPU por arranque; no confundirlo con régimen caliente. La primera carga incluye importaciones diferidas de bibliotecas y verificación de hashes, no sólo lectura de pesos. No se atribuye su duración a una única causa sin evidencia.

El suplemento desglosó visual/texto/similitud sobre 8 VAL: CPU 0,14330/0,05655/0,000058 s; MPS 0,12696/0,02152/0,00889 s. Son primeras ejecuciones de esas formas en otro proceso; no sustituyen el microbenchmark caliente.

### 9.4 Memoria observada

| Punto | MPS asignada | Driver MPS | RSS del proceso |
|---|---:|---:|---:|
| Inferencia visual batch 8 | 799326464 B | 1456160768 B | 1385742336 B |
| Después de actualizar bloque visual | 875321344 B | 1464713216 B | 1577025536 B |
| Linear con dos encoders cargados para recarga/LIME | 1575928320 B | 1659650048 B | 1647869952 B |

Memoria recomendada por API MPS: 40.200.896.512 bytes. Son **snapshots**, no picos continuos ni suma de memoria unificada independiente: RSS/driver/asignaciones pueden solaparse. No extrapolar a entrenamiento completo.

La consulta TensorFlow `get_memory_info('GPU:0')` devolvió `current=0, peak=0` pese a variables y entrenamiento en Metal. **FALLIDO para estimar memoria real TensorFlow**; no se interpreta como consumo nulo. Medición fiable de memoria Metal de la cabeza y perfilado de presión/swap quedan pendientes.

## 10. Paridad numérica y reproducibilidad

Tolerancias fijadas: **`atol=1e-4`, `rtol=1e-3`**, FP32. Se comparó `np.allclose` y diferencias absolutas, sin ajustar tolerancias después de observar resultados.

| Magnitud | Máx. abs. CPU/MPS, 8 TRAIN | Máx. abs. CPU/MPS, 8 VAL balanceadas | Estado |
|---|---:|---:|---|
| Embedding visual | 5,51343e-7 | 6,57514e-7 | VERIFICADO |
| Embedding textual | 2,38419e-7 | 2,38419e-7 | VERIFICADO |
| Coseno | 6,25849e-7 | 4,17233e-7 | VERIFICADO |
| Logits | 5,34058e-5 | 3,43323e-5 | VERIFICADO |
| Scores softmax | 1,13547e-5 | 4,94719e-6 | VERIFICADO |
| Cambios de clase | 0 | 0 | VERIFICADO |

La escala fue idéntica. Los márgenes respecto de 0,5 se conservan para TRAIN, y los scores completos para VAL permiten reconstruirlos. No hubo flips cercanos al umbral en estos casos; no se generaliza a toda la población.

Recarga Linear: diferencia de embeddings = 0, diferencia de scores = 0. Recarga Fine-tuning: diferencia de scores = 0. Semillas, dtype, dispositivos, preprocesamiento y versiones quedan registrados. No se ejecutó un estudio de determinismo entre múltiples reinicios/semillas ni tolerancias de gradiente CPU/MPS: **PENDIENTE DE PRUEBA**.

## 11. XAI y REPRESENT: alcance comprobado

| Caso | Ejecución mínima | Resultado / límite |
|---|---|---|
| Zero-shot: gradiente imagen | Derivar coseno del prompt positivo respecto de input | Gradiente finito `mps:0`, suma absoluta ≈14,472; VERIFICADO |
| Zero-shot: embedding | `retain_grad` en vector visual normalizado | Gradiente no nulo, suma absoluta ≈13,582; VERIFICADO |
| Zero-shot: tokens visuales | Hook en `visual.trunk.blocks.11.norm1` | `[1,197,768]`, gradiente no nulo ≈0,98437; VERIFICADO |
| Linear: LIME | 32 perturbaciones, 8 llamadas batch 4 a imagen→Torch→NumPy→Keras | Scores finitos y pesos de explicación; VERIFICADO funcionalmente |
| Linear: autograd | Frontera `detach().cpu().numpy()` y consumo Keras | Grafo Torch no atraviesa NumPy; no hay gradiente hacia imagen por esa cadena |
| Fine-tuning: activaciones/gradientes | Hook en mismo norm1, logit binario como objetivo | Activaciones finitas; gradiente token ≈0,55322, imagen ≈7,19785 en MPS; VERIFICADO |
| REPRESENT original/Linear | Extracción normalizada de las 24 muestras | `[24,512]`, finita, encoder congelado idéntico |
| REPRESENT ajustado | Dos muestras TRAIN y suplemento de 8 VAL | `[2,512]` / `[8,512]`, finitas |
| CKA | Función existente `assessment.representation.linear_cka` | Original/ajustado sobre mismos sample_id VAL: 0,9999981017 |

LIME operó sobre una imagen VAL identificada, con resize de presentación a 224 y segmentación SLIC (`n_segments=16`, `compactness=10`); cada perturbación se vuelve a pasar por la transformación OpenCLIP. Es una prueba funcional de callback, **no certificación de fidelidad de mapa ni del protocolo EXPLAIN productivo**. Las 32 perturbaciones son deliberadamente menores que el presupuesto CLI productivo: no confundirlos.

Los IDs de tokens textuales son enteros, no variables diferenciables. No se probaron atribuciones a embeddings de entrada textual, SHAP, attention rollout ni construcción final de Grad-CAM. Se identificó una capa candidata ViT y se verificó que permite gradientes; no se presentó un heatmap como resultado científico validado. Atribuciones de embeddings no se presentaron como mapas de píxeles.

Para alimentar REPRESENT existente: conservar orden `sample_id→row`, SHA del encoder, espacio **proyección visual 512 normalizada L2**, shape/dtype y población; sustituir la especificación fija `GlobalAveragePooling2D` y `runtime.layer.name` por metadatos reales del adaptador. Reutilizar `M/assessment/representation.py:project`, `runtime.py:save_arrays`, roles y verificadores de `service.py`; reutilizar lectura en `B/services/scientific_representations.py`. No se generaron nuevos artefactos productivos ni se implementó una caché paralela. PCA/UMAP no se volvieron a probar con esta población en 01B.

## 12. Diseño del RUN Zero-shot — Opción B aprobada

**Diseño exclusivamente; no se insertó RUN, model_version, artifact ni sesión en PostgreSQL.** Evidencia estática actual: [schema_evidence.txt](evidence/biomedclip_01b/schema_evidence.txt), `M/execution/{selection,operations,artifacts,completion,repository}.py`, `M/assessment/{lineage,service,contracts}.py`, `M/data/governed_dataset.py:training_dataset_metadata`. `M/` significa `malaria_dl_local_project/src/malaria_dl/`.

### 12.1 Identidad y semántica

Mantener `runs.run_type='training'` como categoría operativa compatible con FK y consumidores, agregando un **discriminante científico obligatorio e inmutable**. Propuesta de contenido, no nombre de columna nuevo:

```json
{
  "scientific_origin": {
    "schema": "pretrained_origin_v1",
    "kind": "pretrained_external",
    "mode": "zero_shot",
    "training_performed": false,
    "architecture": "biomedclip_zero_shot",
    "model_repository": "microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224",
    "revision": "9f341de24bfb00180f1b847274256e9b65a3a32e"
  }
}
```

Ubicarlo en JSON de configuración/`execution_parameters`, con validación SQL y Python coherente, no como etiqueta libre que permita saltar verificaciones. El registro debe tener `run_id` propio, FK `model_id` de Zero-shot, `dataset_version_id` y snapshot gobernado completo, seed, perfil de inferencia, prompts/tokenizer/transform/mapping/umbral y hashes de la configuración y componentes. Las fechas y duración corresponderán a **registro/verificación**, no a tiempo de optimización. Sin loss, métricas TRAIN, optimizer o epochs.

El modelo original podrá compartirse físicamente por hash, pero cada artifact/version debe tener ownership y procedencia verificables; reutilización de hash documentada donde lo exija la gobernanza. Conservar los originales fuera del cache mutable como activos gobernados cuando llegue la implementación productiva.

### 12.2 Relaciones y estado

- `models`: fila independiente `biomedclip_zero_shot`, familia BiomedCLIP y capacidad `trainable=false`.
- `runs`: `run_type='training'`, discriminante validado, estado completed **sólo después de verificar origen**; `release_status` no debe publicar el modelo automáticamente.
- `artifacts`: `artifact_type='model_checkpoint'`, `run_id` del registro, path/bytes/checksum, formato OpenCLIP y referencias de componentes verificables.
- `model_versions`: `model_id`, `training_run_id` del registro, `checkpoint_artifact_id`, hash/tamaño, firmas/mapping/preprocesamiento/framework; status de investigación/candidate según política existente, no approved/deployed automáticamente.
- FK compuesta `(checkpoint_artifact_id, training_run_id)` conserva ownership. Las restricciones que exigen un RUN training pueden conservarse con esta opción.
- Sesión: se recomienda reutilizar `train_execution_sessions` para owner, raíz, active→completed→verified, con **contrato de completion/verificación específico de origen**, distinto de `TrainingCompletionContractV1`.
- Records: se pueden conservar registros reales de runtime/origen/artifact; `train_execution_records` permite kind/phase textuales y payload objeto, pero debe agregarse validación estricta de los kinds autorizados para esta rama. Sin artefacto atribuido a época 0 ni selection/early stopping ficticios.

### 12.3 Adaptaciones mínimas identificadas

| Restricción/consumidor vigente | Evidencia observada | Adaptación futura necesaria |
|---|---|---|
| `v2_run_configuration_required()` | Constraint trigger diferido exige `run_configurations` para cualquier RUN training | Rama Zero-shot validada por arquitectura+origen+configuración completa; permitir configuración de origen sin fila de hiperparámetros de optimización. Mantener exigencia actual para entrenables |
| `run_configurations` | Optimizer/LR/épocas NOT NULL; max_epochs>0; CHECKs sólo modelos actuales/pesos none/imagenet | No llenar con valores ficticios Zero-shot. Linear/Fine-tuning sí necesitan extensión explícita del dominio y configuración entrenable |
| `train_session_guard()` | Para verified exige al menos epoch y artifact, count de épocas y records_hash | Bifurcar por origen previamente validado: verificar checkpoint/manifiesto/registro sin epochs; preservar rama conventional íntegra, owner e inmutabilidad |
| `artifacts.verify_session()` | Exige epochs, fases, predicciones VAL, calibration y selección de época | Verificador dedicado de origen; no retornar éxito temprano sin verificar binarios y configuración |
| `TrainingCompletionContractV1` | Exige checkpoint_epoch>0, evaluación VAL, eventos y hashes de training results | Nuevo contrato de completion de registro, sin campos inventados; no simular eventos de aprendizaje/E10 TRAIN |
| `train_event_guard`, `train_record_guard` | Secuencia/owner; records inmutables | Reutilizar fencing; si se agregan eventos de registro, definir su semántica, no usar PHASE/EPOCH falsos |
| `enforce_model_version_governance`, CHECKs/FK de model_versions | Origen debe referenciar RUN training; payload gobernado protegido | Mantener FK y protección; incorporar discriminante y binding compuesto a validación/identidad inmutable |
| `assessment_identity_guard()` | Exige RUN training | Esta condición sigue satisfaciéndose; agregar/garantizar origen verified y arquitectura coherente al resolver |
| `assessment.lineage.resolve()` | Busca sesión TRAIN y llama verify_session; exige calibration del checkpoint seleccionado | Detectar rama de origen, verificar manifest/model_version/artifact y devolver binding sin época/selección ficticia |
| `assessment.service.inference_options()` | Lee `model_configuration_e2.configuration.resolved.execution` para defaults | Leer perfil explícito de inferencia/seed del registro Zero-shot; no inventar optimizer/epochs para cumplir esa forma |
| `training_dataset_metadata()` | Snapshot completo de dataset/materialización/fingerprints/counts | Guardar snapshot real para la población de evaluación; no presentarlo como dataset usado al preentrenar |
| `contracts.threshold('auto')` | Exige evidencia de umbral TRAIN/calibration | Rama `pretrained_fixed_threshold_v1` con valor y hash fijados antes de TEST. `clinical` debe fallar si no existe calibración VAL explícita |
| `select_trainings()` / CLI EVALUATE/TEST | Selección por RUN training, completed | Conservar `source_training_run_id`; resolver como origen Zero-shot y usar runtime Torch. TEST no necesita una EVALUATE previa con umbral fijo |
| `operations.training_plan`, coordinador/worker | Clonan configuración/entrenan selección | Filtrar capacidad antes de generar plan/claim: omitir Zero-shot, continuar los entrenables; todos omitidos → terminar sin nuevos RUN |
| Catálogo de campañas | `_registry` resuelve todos como entrenables | Publicar fila visible deshabilitada con motivo; backend no debe crear miembro TRAIN para Zero-shot |
| Reportes SCC / comparación | training_run_id, curvas, checkpoint elegido por época, configuración optimización | Mantener enlace RUN; mostrar «Origen preentrenado Zero-shot», epochs/curvas/optimizer N/A; checkpoint por procedencia verificada, no selección por época |
| REPRESENT/EXPLAIN | Runtime Keras y representación GAP | Runtime por framework/origen; identidad correcta, mismos mecanismos científicos existentes |

La alternativa recomendada para `run_configurations` es una excepción estrecha del trigger que exija **otra configuración real y validada en el RUN**, no hacer nullable globalmente sus columnas ni poner Adam/1 época ficticios. En 01C debe probarse que un RUN entrenable no pueda disfrazarse con el discriminante Zero-shot: modelo SQL, capacidad, architecture, `training_performed=false`, formato y procedencia deben concordar; bloquear ambos contratos presentes o ninguno.

El registro será una operación explícita separada de ejecutar TRAIN. **Omitir Zero-shot en `src.train` no creará silenciosamente ese registro.** Si sólo hay Zero-shot, la salida debe indicar omisión por no requerir entrenamiento, sin nuevos RUN, sesiones o miembros. EVALUATE/TEST/EXPLAIN/REPRESENT usarán posteriormente el `run_id` de un registro ya verificado. Esto evita confundir omisión con creación implícita de evidencia.

### 12.4 Calibración, reportes e integridad

Baseline mínimo: umbral fijo 0,5 protocolizado; no crear `calibration/val/selected` con predicciones inventadas. Si una fase futura selecciona umbral en VAL, vincular evidencia real de ese intento, prompts y checkpoint; nunca TEST. No hay calibración de probabilidades en 01B.

Consultas/reportes deben separar `run_type` operativo de `training_performed` científico. Curvas y épocas N/A, no «entrenamiento fallido» ni cero loss. Mostrar hash/revisión/prompts, dataset objetivo, scores relativos y estado de integridad. Una comparación de tiempos debe separar registro/carga de entrenamiento. La detección inequívoca del origen debe usarse también en filtros, reentrenamiento por referencia, métricas de campañas y publicación Stage 2.

Este diseño mantiene PK/FK/ownership y las políticas de TEST de modelos entrenables; cambia sólo las ramas que hoy presuponen optimización en todo RUN training. **PENDIENTE DE PRUEBA:** SQL de implementación, pruebas negativas de constraints/triggers, transacciones/rollback y regresión de consumidores. Ninguna restricción fue modificada aquí.

## 13. Riesgos y limitaciones

- Población pequeña seleccionada por UUID, dos pasos Fine-tuning y tres épocas de cabeza: no acredita convergencia, desempeño clínico ni generalización.
- Microbenchmark de 5 repeticiones y batches hasta 8; no certifica throughput sostenido, uso concurrente, memoria máxima o estabilidad térmica.
- Memoria TensorFlow Metal no medible con los contadores usados; snapshots MPS no son picos globales.
- El checkpoint fine-tuning reconstruye inferencia, no reanuda optimizer/RNG/scheduler.
- Gradientes disponibles no validan causalidad/localización clínica. SHAP, rollout, mapas Grad-CAM completos, atribución textual y puente diferenciable Keras/Torch no se implementaron.
- El corte NumPy es apropiado para Linear congelado pero impide autograd continuo. No se debe mostrar SHAP de embeddings como atribución de píxeles.
- Se ajustó un bloque en modo eval con gradientes; futura receta de train/dropout, early stopping, fases y selección requiere validación.
- CKA casi uno después de un paso no acredita alineación multimodal conservada ni equivalencia científica.
- No se ejecutaron campañas, contratos productivos ni pruebas SQL de escritura. Las excepciones Zero-shot siguen siendo diseño.
- El lock completo no se reinstaló de cero en otra máquina; no se certifican futuras versiones ni diferencias entre sistemas.
- Checkpoints originales y experimentales están en cache local separada y sus rutas constan en manifiestos. Conservarlos/respaldarlos junto con evidencia si se necesita repetir la recuperación exacta; los hashes sin binarios no bastan.

## 14. Incidencias y controles finales

| Incidencia/control | Resultado |
|---|---|
| Dependencias originales faltantes | Resuelto en entorno aislado, sin degradar paquetes productivos |
| Primera carga lenta | 95,8 s, incluyendo imports y hashes; cargas posteriores menores. No error funcional |
| Mensaje TensorFlow NUMA/default y device con «0 MB» | Log de inicialización; entrenamiento/variables GPU verificados. No interpretarlo como CPU |
| Memoria TensorFlow current/peak=0 | FALLIDO como medición de consumo; pendiente profiler alternativo |
| Operación MPS no soportada | Ninguna encontrada en las rutas ejecutadas |
| Paridad fuera de tolerancia / cambio de clase | Ninguno en los casos comparados |
| Restricciones SQL del registro Zero-shot | Bloqueos vigentes confirmados; no se intentó eludirlos ni insertar registros |
| Integridad del original | Hashes iguales al cierre |
| Paquetes `.venv-metal` | Freeze antes/después idéntico |
| Tablas productivas | [before](evidence/biomedclip_01b/database_before.json) / [after](evidence/biomedclip_01b/database_after.json): 8 tablas iguales; 4 tablas assessment cambiaron por actividad concurrente observada |
| Código productivo | Estado Git muestra únicamente informe, evidencia y scripts experimentales nuevos |

El primer control intermedio dio igualdad; al cierre aparecieron tres EXPLAIN HTTP sobre el TRAIN existente `b1b39079-658f-4300-b159-52619f981035`: Grad-CAM, LIME y SHAP, una muestra cada uno, entre 23:13:12 y 23:13:47 UTC. Evidencia: [concurrent_assessments.txt](evidence/biomedclip_01b/concurrent_assessments.txt) y [database_changes.json](evidence/biomedclip_01b/database_changes.json). Se observaron +3 identities, +3 attempts, +3 results y +6 artifacts; no se intentó revertirlos. Las identidades contienen `http_request`; no son salidas de estos scripts aislados. No se identifica aquí quién los inició. **FALLIDO el control de igualdad global final por actividad concurrente; no equivale a una escritura de 01B.** Todas las sesiones SQL de esta tarea estuvieron en read-only; no se ejecutó DML/DDL. Los controles count/xmin no son un backup/hash exhaustivo de toda la BD. Se verificaron muestras sólo por sus referencias explícitas, sin exploración masiva del dataset. No se hicieron commits ni merges.

## 15. Scripts, resultados y recomendación final de arquitectura

Scripts reproducibles:

- [`prepare.py`](../../scripts/experiments/biomedclip_01b/prepare.py): snapshot SQL sólo lectura, muestras gobernadas/hashes, descarga por revisión y manifiesto original.
- [`common.py`](../../scripts/experiments/biomedclip_01b/common.py): carga offline, transformaciones, timers sincronizados, hashing, semillas y paridad.
- [`zero_shot.py`](../../scripts/experiments/biomedclip_01b/zero_shot.py): CPU/MPS, microbenchmark, gradientes y embeddings.
- [`linear.py`](../../scripts/experiments/biomedclip_01b/linear.py): cabeza Keras, congelamiento, selección VAL, recarga y LIME.
- [`fine_tuning.py`](../../scripts/experiments/biomedclip_01b/fine_tuning.py): dos actualizaciones, invariantes y checkpoint.
- [`supplement.py`](../../scripts/experiments/biomedclip_01b/supplement.py): paridad balanceada, arrays, CKA existente y timings separados de cabeza.
- [`README.md`](../../scripts/experiments/biomedclip_01b/README.md): reproducción en directorios nuevos y límites.

El [manifiesto experimental](evidence/biomedclip_01b/manifest.json) lista hashes/tamaños de scripts, resultados, lock y binarios. La configuración efectiva de AdamW (betas, eps y opciones por defecto de esta versión) está en [optimizer_effective_defaults.json](evidence/biomedclip_01b/optimizer_effective_defaults.json). Los JSON/tablas/logs son evidencia de 01B, no fuentes productivas paralelas. Los arrays grandes y checkpoints no se incorporaron al árbol científico de TRAIN/assessments.

Recomendación fundamentada:

1. Conservar PyTorch/OpenCLIP y sus pesos originales, con adaptador de entrada NCHW/transform original y salida binaria de semántica explícita.
2. Linear: encoder congelado y cabeza Keras funciona; reconstrucción debe vincular original+transform+embedding+cabeza. No se necesita caché durable para el primer alcance.
3. Fine-tuning: ejecutor Torch separado que emita evidencia científica común. El bloque autorizado se actualiza en MPS; definir receta y checkpoint completo para reanudación en integración posterior.
4. Implementar el registro Zero-shot de Opción B con discriminante validado y verificación específica; mantener intactas las exigencias de entrenamiento real para entrenables.
5. Reutilizar resultados, artefactos, muestras, REPRESENT/CKA y reportes existentes; adaptar capacidades y formatos, sin convertir todo el modelo a Keras ni crear nuevas tablas por framework.

## 16. Cierre y criterios de entrada a BIOMEDCLIP-01C

Los criterios técnicos mínimos de carga, inferencia MPS, paridad, embeddings, Zero-shot, Linear, actualización Fine-tuning, recarga, XAI preliminar y diseño de origen tienen evidencia efectiva. El entorno está fijado y la separación de las operaciones de esta tarea respecto de producción fue preservada; se documenta actividad productiva concurrente externa a estos scripts. **01B puede aprobarse como validación técnica mínima**, con las limitaciones expresas de memoria Metal y alcance de pruebas; no como integración científica completa.

Antes de implementar 01C, se requiere autorización explícita y acordar:

- Contrato exacto de origen/configuración/completion Zero-shot y branches de triggers/consumidores; pruebas negativas contra disfraz de modelos entrenables.
- Semántica de `src.train`: omitir no entrenables, continuar demás, no crear RUN si ninguno aplica, registro Zero-shot separado.
- Formato productivo de checkpoint compuesto y verificación de todos los componentes; rutas gobernadas recuperables Mac/Docker.
- Adaptadores de entrenamiento/inferencia por framework y perfil local de dependencias con regresión de modelos actuales.
- Receta Fine-tuning, historial real, optimizer/RNG para reanudación, selección/umbral sólo VAL y TEST independiente.
- XAI soportado inicialmente, especificación de representación, estados N/A/Sin evidencia y semántica del score Zero-shot.
- Pruebas pequeñas de contratos/persistencia en entorno de pruebas, antes de campañas productivas, y medición de memoria/estabilidad ampliada.

**No se inicia 01C automáticamente.**
