# CAPSTONE-MODEL-CONTRACT-01B

**Estado final: APROBADO.** Verificación del 27 de octubre de 2026. Registro, activación sin EVALUATE e inferencia celular real demostrados en PostgreSQL y en el backend Docker. Esto acredita funcionamiento técnico; no acredita desempeño clínico.

## Identidades persistidas

| Entidad | Identificador |
|---|---|
| Modelo `biomedclip_zero_shot` | `1cf3e462-c0f7-4f72-92fe-306b8aaaa203` |
| TRAIN lógico | `31d27b2d-6e90-4530-a589-ae92c91281df` |
| Checkpoint original | `e5e67ccf-6403-4dfa-b472-31920f4f2346` |
| Model version 1 | `3fd16a84-b5c7-442b-916b-e0438bb0f3e5` |
| Publicación activa | `2ab60a9b-f7a6-45a8-a6cc-45ca44b804a5` |
| Deployment `stage2/default` | `ee60a055-ce19-48af-aa55-609a7f352bb4` |
| Clasificación celular real | `bae280c9-0b10-4cf5-80ff-694a80c947fa` |
| Predicción celular persistida | `62e7764a-92cc-47bf-acd0-b48d15eafcd7` |

El TRAIN tiene `run_type=training`, `status=completed`, `total_epochs=completed_epochs=0`, `training_performed=false` y origen `pretrained_external`. Tiene **cero filas** en `run_configurations`, `training_history` y `run_metrics`. La identificación de TRAIN lógico utiliza exclusivamente `models.metadata.training_mode=logical`. Las versiones observadas del proceso de ingreso están en `runs.execution_parameters.runtime_environment`; no se reintrodujeron columnas TensorFlow/Keras.

La repetición del registro reutiliza modelo, RUN, artefactos y versión. [registration.json](registration.json) documenta la repetición; [sql-evidence.json](sql-evidence.json) muestra las relaciones persistidas.

## Auditoría inicial

HEAD inicial: `b71ed1e0f0b17a88fca4452f591ef2861f0a4467`. La primera consulta `git status --short` estaba vacía. La captura guardada [git-initial.txt](git-initial.txt), tomada inmediatamente después de crear el directorio de evidencia, muestra únicamente ese directorio nuevo sin seguimiento; aún no había cambios de código. No se hicieron commits Git.

Se inspeccionaron las tablas, constraints y triggers reales de PostgreSQL antes de modificar código. El catálogo contenía únicamente `custom_cnn`, `vgg16` y `densenet121`; no había registro parcial BiomedCLIP que reconciliar. `v2_run_configuration_required` estaba ausente y continúa ausente. `run_configurations` sigue disponible. Las columnas retiradas siguen ausentes.

Operaciones y consumidores inspeccionados:

- `persistence/run_repository.py`: `get_or_create_model`, `start_run`, `finish_run`, `log_artifact`; el alta computacional Keras también usa `execution/repository.py`.
- `governance/repository.py`: `create_model_version`, propiedad RUN/artefacto, checksum, tamaño y unicidad.
- `execution/selection.py`, `repositories/stage2_status.py`, `training_summaries.py`: recuperación de TRAIN y linaje. El JOIN de configuraciones en resúmenes ya era LEFT JOIN; no hubo que fabricar configuraciones.
- `cell_activation.py`, `productive_model.py`, publicación, disponibilidad, rutas Stage 2 y paneles del frontend: activación, selección, congelamiento y carga del checkpoint.
- Experimento previo `scripts/experiments/biomedclip_01b/common.py`: prompts, componentes locales, normalización L2 y softmax de similitudes. Se conservaron esos prompts exactamente.

## Cambios por componente

**Persistencia genérica.** `pretrained/registration.py` recibe un manifiesto, verifica físicamente todos sus archivos, serializa el registro y compone los cuatro repositorios existentes en una transacción. `transaction_scope` permite compartir la conexión sin crear SQL de persistencia exclusivo del modelo. Un fallo no deja un TRAIN completado ni una versión parcial. Identidades o metadatos conflictivos se rechazan sin sobrescribir evidencia. El catálogo sigue consultándose desde `public.models`.

**Ejecución.** La omisión de entrenamiento computacional consulta `models.metadata.training_mode`; ya no deduce esa modalidad del descriptor, nombre ni framework. La selección común devuelve ese metadato y conserva el RUN lógico. Las validaciones de parámetros computacionales permanecen en su implementación existente.

**Activación y disponibilidad.** Se separó la existencia de evidencia científica de la activación operativa. La ausencia de EVALUATE no bloquea la selección. Se verifican versión, framework, propiedad, tamaño/SHA, preprocesamiento, mapping y carga/predicción real antes de activar. La selección y su auditoría se confirman en una transacción. La revalidación al crear una clasificación ya no hace INNER JOIN obligatorio con evaluación/calibración. Los endpoints Stage 2 de activación reutilizan el servicio celular; la preparación Keras con selecciones explícitas conserva su flujo. La publicación técnica formal `production/champion` continúa siendo un flujo distinto del slot celular `stage2/default`.

**PostgreSQL.** Se encontraron tres exigencias adicionales de EVALUATE que impedían el flujo real: los CHECK de publicación/evento y la validación del snapshot celular. [cell_activation_optional_evaluation.sql](../../../scripts/sql/cell_activation_optional_evaluation.sql) permite cero o una referencia de evaluación y mantiene la exclusión de referencias simultáneas, las FK, la propiedad de artefactos, la inmutabilidad y la coincidencia del snapshot con la publicación. No se retiraron comprobaciones de identidad. No se utilizó Alembic ni se agregaron revisiones, baselines o guards de compatibilidad.

**Inferencia.** `models/openclip_inference.py` carga los pesos originales y los componentes locales de texto, en modo offline. Conserva el transform de OpenCLIP, L2 de imagen/texto, escala aprendida y softmax. Se integra en el resolver y el preprocesador celular existentes. No se copiaron ni convirtieron los pesos. No se implementó fine-tuning, linear probing ni EXPLAIN PyTorch.

**Interfaz.** La activación no exige TRAIN/EVALUATE completados como regla universal. Se muestra «Sin evidencia de evaluación». Para OpenCLIP se muestran scores relativos, con explicación de que no son probabilidades clínicas calibradas; los modelos Keras conservan sus etiquetas anteriores.

**Entorno.** Se instalaron las dependencias OpenCLIP fijadas en el archivo existente de requirements y se incorporaron a la construcción del backend. `docker-compose.openclip.yml` monta los originales en solo lectura y habilita sus raíces explícitas. La variable local `CAPSTONE_EXTERNAL_MODEL_ROOT` se agregó a `.env` sin exponer credenciales. El backend local admite loopback únicamente con el opt-in `CAPSTONE_LOCAL_TRAIN=1`, igual que el plano de ejecución ML.

## Artefactos y protocolo

Origen: `microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224`, revisión `9f341de24bfb00180f1b847274256e9b65a3a32e`.

Checkpoint físico:

```text
/Users/julio/.cache/capstone-biomedclip-01b/original/biomedclip/9f341de24bfb00180f1b847274256e9b65a3a32e/open_clip_pytorch_model.bin
783705670 bytes
SHA-256 52cc993c5c5ff962bd0c60931874bc001e7e9b41666a385530f4a036294576be
```

También se registraron `open_clip_config.json`, `config.json`, `tokenizer_config.json` y `vocab.txt`, con propietario TRAIN, ruta, tamaño y hash reales. Los componentes de texto corresponden a `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract`, revisión `d673b8835373c6fa116d6d8006b33d48734e305d`. El detalle de archivos está en [registration-manifest.json](registration-manifest.json); no se inventaron fechas de descarga.

Orden y prompts originales:

1. `uninfected`: `a microscopy image of an uninfected red blood cell.`
2. `parasitized`: `a microscopy image of a red blood cell infected with malaria parasites.`

El umbral operativo es 0.5, con fuente `configured_decision`; no hay calibración ni sensibilidad/especificidad atribuidas. PostgreSQL conserva los nombres legados `probability_parasitized`/`probability_uninfected`, exigidos por sus constraints actuales. El contrato congelado identifica explícitamente `score_parasitized` y `relative_similarity_not_clinically_calibrated`; esos nombres legados no cambian el significado científico de los scores.

## Evidencia de inferencia y linaje

- [lineage-queries.sql](lineage-queries.sql): consultas reproducibles de modelo → TRAIN → artefacto → versión, selección y predicción.
- [activation.json](activation.json): activación real sin EVALUATE. [http-availability.json](http-availability.json) y [http-stage2-status.json](http-stage2-status.json) confirman la disponibilidad y el estado servidos por HTTP en el backend activo.
- [inference.json](inference.json): cuatro imágenes celulares reales, con hashes y snapshot del modelo, en Python local.
- [docker-inference.json](docker-inference.json): las mismas cuatro imágenes en el backend Docker. Python `3.12.14`, PyTorch `2.14.1+cpu`, OpenCLIP `3.3.0`, Transformers `4.57.6` observados.
- [inference-parity.json](inference-parity.json): diferencia máxima local/Docker `3.814697265625e-06`; paridad dentro de `atol=1e-4`, `rtol=1e-3`.
- [cell-classification-e2e.json](cell-classification-e2e.json): ejecución real de `CellClassificationService.execute_classification`, lectura y verificación del crop, carga, predicción, resumen y persistencia. Estado `completed`, una célula procesada, cero fallidas. Se reutilizó el RUN de detección `46b4d278-54b6-46e0-8b03-2ce08b2a78d5`; no se modificaron sus imágenes.
- [sql-evidence.json](sql-evidence.json): predicción final `uninfected`, score parasitized `0.4755263484857575`, score uninfected `0.5244736515142425`, threshold 0.5. Son scores relativos, sin interpretación de rendimiento clínico.

## Pruebas y regresiones

| Verificación | Resultado final | Evidencia |
|---|---|---|
| Registro externo, idempotencia, fallo/rollback, modo lógico, activación sin evaluación, framework/artefactos inválidos; más cinco pruebas TRAIN | 14 passed | [postgres-tests-final.txt](postgres-tests-final.txt) |
| Activación heredada: reemplazo atómico, referencias falsas, snapshots, propiedad y permisos runtime | 14 passed | [activation-postgres-tests.txt](activation-postgres-tests.txt) |
| Servicios celulares y consulta de estado Stage 2 | 57 passed | [backend-tests.txt](backend-tests.txt) |
| Tracking, dependencias, modelos, configuraciones, validaciones y adaptadores Keras reales | 52 passed | [keras-regression-tests.txt](keras-regression-tests.txt) |
| Frontend completo | 442 passed | [frontend-all-tests.txt](frontend-all-tests.txt) |
| TypeScript `npx tsc --noEmit` | PASS | [frontend-types.txt](frontend-types.txt) |
| `git diff --check`, `pip check` en backend | PASS | [final-checks.txt](final-checks.txt) |

Comandos principales:

```text
python -m pytest malaria_dl_local_project/tests/test_external_model_registration.py malaria_dl_local_project/tests/test_train_run_persistence.py -q
python -m pytest backend_api/tests/test_cell_activation.py -q
docker exec capstone_backend sh -c 'cd /app && python -m pytest tests/test_cell_classification_services.py tests/test_stage2_status_read_only.py -q'
docker exec capstone_backend sh -c 'cd /app/malaria_dl_local_project && python -m pytest tests/test_artifact_tracking.py tests/test_execution_contract_dependencies.py tests/test_biomedclip_pretrained.py tests/test_model_registry_e2.py tests/test_model_execution_config.py tests/test_max_epochs_config.py -q'
cd frontend && npm test
cd frontend && npx tsc --noEmit
```

Las pruebas PostgreSQL sintéticas usan `CONTRACT_TEST_DATABASE_URL` apuntando a `contract01b_test`, en un contenedor aislado, con copia del esquema actual obtenida por `pg_dump --schema-only`. Los fixtures rechazan otra base. Se copiaron allí los permisos de tablas actuales del runtime; no se ampliaron permisos productivos. Las funciones/constraints vigentes sustituyen las reconstrucciones históricas Alembic.

Incidencias resueltas:

- El test de `README_2.md` apuntaba a un archivo retirado: ahora verifica `README.md` real.
- Los cinco errores de preparación se resolvieron reemplazando el fixture basado en migraciones por uno del esquema actual, con padres sintéticos explícitos, evidencia de dataset coherente y conexión al catálogo aislado. Los cinco casos pasan.
- Las expectativas antiguas de EVALUATE obligatorio se actualizaron para comprobar la independencia de elegibilidad y evidencia.
- Un test read-only asumía que una versión real nunca había sido registrada: ahora verifica el estado observado y ausencia de escrituras, sin ese supuesto temporal.
- La primera corrida amplia del frontend encontró cuatro expectativas de etiquetas Keras. Se conservaron sus etiquetas y se hicieron específicas las etiquetas de scores OpenCLIP; las 442 pasan.
- Una corrida del backend omitió 12 casos por falta de URL aislada ([backend-tests-final.txt](backend-tests-final.txt)). Luego se ejecutó esa suite completa contra la copia vigente: **14 passed**, sin omisiones. No quedan fallos funcionales abiertos en las suites seleccionadas.
- Los mensajes de TensorFlow sobre CUDA/TensorRT y caché Matplotlib son avisos del entorno CPU; la inferencia terminó correctamente. No se cambiaron permisos para ocultarlos.

## Conservación del historial

La comparación por ID y hash de cada fila contra [historical-before.json](historical-before.json) muestra:

- 22 artefactos previos: ninguno modificado ni eliminado; se añadieron cinco.
- Una versión previa: sin cambios; se añadió una.
- 23 RUNs previos: ninguno eliminado; se añadió el TRAIN lógico.
- **Una excepción operativa explícita:** el RUN `bbbd5b60-afaa-4034-a504-a60ed642aafe`, anteriormente seleccionado, cambió sus campos `release_*` mediante `mark_active_training` al activar el nuevo modelo. Por ello su hash de fila completo cambió. No se sobrescribieron sus parámetros, checkpoints, métricas ni estado de ejecución. Las publicaciones/deployments anteriores se conservan inactivos para los snapshots históricos.
- No se fabricaron métricas ni curvas. No se modificaron splits oficiales, imágenes originales, análisis/comparación científica ni implementaciones Grad-CAM/LIME/SHAP.

La búsqueda de referencias ejecutables a los tres archivos retirados no produjo coincidencias. No se restauraron esos archivos.

## Reproducción y estado Git final

Registro genérico, con las variables de conexión del entorno autorizado:

```sh
cd malaria_dl_local_project
python -m src.malaria_dl.pretrained.registration ../docs/audits/CAPSTONE-MODEL-CONTRACT-01B/registration-manifest.json
```

Backend con acceso a los originales:

```sh
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.openclip.yml up -d --build backend
```

`CAPSTONE_EXTERNAL_MODEL_ROOT` debe señalar la raíz física existente indicada por el manifiesto. La instancia verificada ya está ejecutándose con ese montaje. No se solicita descargar ni convertir los pesos.

[git-final.txt](git-final.txt) y [files-changed.txt](files-changed.txt) enumeran el estado y los archivos finales. El HEAD no cambió y no hubo commits Git. La ejecución real acredita registro, activación e inferencia celular; queda pendiente una evaluación científica formal, que no se presenta como realizada.
