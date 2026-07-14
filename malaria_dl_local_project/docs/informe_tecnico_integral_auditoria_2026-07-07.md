# Informe tecnico integral del proyecto de deteccion de malaria

Fecha de auditoria: 2026-07-07  
Alcance: repositorio completo `capstone`, con foco en `malaria_dl_local_project`, `backend_api`, `frontend`, migraciones SQL, scripts de datos, outputs disponibles y pruebas locales.

## 1. Resumen ejecutivo

El proyecto tiene una base tecnica solida para un prototipo academico avanzado: separacion clara entre entrenamiento ML, API de lectura, frontend de monitoreo, tracking en PostgreSQL, metricas clinicas explicitas, convencion de etiquetas documentada y pruebas unitarias extensas en el modulo ML.

La arquitectura actual ya evita varios errores comunes de proyectos de clasificacion medica: invierte correctamente el mapeo legado de TFDS, trata `parasitized` como clase positiva, calcula sensibilidad/especificidad/F2/AUC con semantica clinica, bloquea calibracion de umbral sobre test, detecta colapso de predicciones y registra artefactos, predicciones, politicas de checkpoint y calibraciones.

Sin embargo, el sistema no debe presentarse como listo para uso clinico. Los riesgos principales son:

| Prioridad | Hallazgo | Impacto |
|---|---|---|
| Critica | No hay identificadores de paciente, lamina, muestra o adquisicion en el split fisico. | No se puede demostrar independencia clinica ni descartar fuga por origen comun. |
| Critica | No hay validacion externa ni OOD documentada. | El rendimiento puede no generalizar a otro laboratorio, microscopio, tincion o protocolo. |
| Alta | Ningun checkpoint disponible satisface `min_recall=0.98` a umbral 0.5 en validacion. | La politica clinica configurada no se cumple en los modelos actuales. |
| Alta | El umbral clinico de `custom_cnn` alcanza recall objetivo solo en validacion; no hay metricas de test regeneradas con `--threshold clinical`. | No se puede afirmar rendimiento clinico de test al umbral calibrado. |
| Alta | La UI de explicabilidad no muestra la imagen original lado a lado, aunque el codigo tiene el bloque comentado. | Reduce auditabilidad humana de Grad-CAM/LIME/SHAP. |
| Media-alta | `UploadedPredictions.tsx` oculta valores reales `0.0` porque usa checks truthy. | Puede esconder probabilidades o thresholds validos en reportes clinicos. |
| Media-alta | Backend sin autenticacion/autorizacion. | Aceptable localmente; riesgoso si se expone. |
| Media | Algunas migraciones usan `CREATE OR REPLACE VIEW`. | Puede fallar ante cambios de estructura de vistas. |

Resultado de pruebas durante la auditoria:

| Componente | Resultado |
|---|---|
| ML tests | `143 passed, 15 skipped` con `malaria_dl_local_project/.venv/bin/python -m pytest malaria_dl_local_project/tests -q` |
| Frontend build | `npm run build` exitoso |
| Backend tests | No ejecutables: `pytest` no esta instalado en `backend_api/.venv` ni en Python global |
| Frontend tests | No se encontraron tests ni script de test |

## 2. Estado general del sistema

El sistema esta organizado en cuatro capas principales:

| Capa | Ubicacion | Estado |
|---|---|---|
| ML pipeline | `malaria_dl_local_project/src` | Maduro para prototipo experimental, con buena cobertura de pruebas. |
| Datos | `malaria_dl_local_project/data/malaria_physical_split` | Split fisico reproducible y balanceado, pero sin IDs clinicos. |
| API | `backend_api/app` | API FastAPI de lectura, orientada a dashboard y trazabilidad. |
| Frontend | `frontend/src` | Dashboard React funcional para runs, dataset, explicabilidad y predicciones. |
| Persistencia | `malaria_dl_local_project/db/init` | Esquema amplio para tracking experimental y clinico. |

El flujo principal esperado es:

1. Crear o validar split fisico.
2. Entrenar modelo con `src/train.py`.
3. Seleccionar checkpoint con politica clinica.
4. Calibrar threshold en validacion.
5. Evaluar test con threshold fijo o clinico.
6. Generar explicabilidad.
7. Registrar datos, metricas, predicciones y artefactos en PostgreSQL.
8. Consumir resultados desde API y frontend.

La direccion general es correcta. El principal problema no es de estructura de software, sino de madurez de validacion experimental y clinica.

## 3. Arquitectura tecnica

### Fortalezas

| Area | Evaluacion |
|---|---|
| Separacion de responsabilidades | Buena. Entrenamiento, evaluacion, calibracion, inferencia, explicabilidad, API y UI estan separados. |
| Trazabilidad | Buena. Hay tablas para runs, metricas, confusion matrix, predictions, artifacts, explainability, threshold y checkpoint policy. |
| Reproducibilidad | Parcialmente buena. El split fisico usa seed fijo y manifest. Falta bloqueo completo de version de dependencias y datos externos. |
| Seguridad de artefactos | Razonable para entorno local. `backend_api/app/services/artifacts.py` restringe raices y extensiones, valida magic bytes en imagenes y usa `nosniff`. |
| Auditabilidad | Buena en DB y API; incompleta en frontend por falta de imagen original en explicabilidad. |

### Debilidades

| Debilidad | Archivo o modulo | Recomendacion |
|---|---|---|
| No hay capa de autenticacion | `backend_api/app/main.py` y routers | Agregar auth antes de cualquier despliegue compartido. |
| No hay CI observable en el repo auditado | raiz del proyecto | Agregar pipeline para ML tests, backend tests, frontend build y lint. |
| Backend tests no corren por dependencia faltante | `backend_api/requirements.txt` | Agregar `pytest` o archivo `requirements-dev.txt`. |
| Frontend sin tests | `frontend/package.json`, `frontend/src` | Agregar Vitest/Testing Library y Playwright para flujos criticos. |
| Versionado SQL manual | `malaria_dl_local_project/db/init` | Migrar gradualmente a Alembic o al menos registrar checksums/versiones aplicadas. |

## 4. Pipeline de datos

El proyecto define una convencion oficial clara en `malaria_dl_local_project/src/config.py`:

| Etiqueta | Clase |
|---|---|
| `0` | `uninfected` |
| `1` | `parasitized` |

La fuente TFDS original se reconoce como legado:

| TFDS original | Clase |
|---|---|
| `0` | `parasitized` |
| `1` | `uninfected` |

`src/data.py` remapea explicitamente TFDS con `1 - label`, lo que evita el error critico de invertir positivos y negativos. El dataset por defecto es el split fisico, no TFDS directo, lo que es correcto para reproducibilidad.

### Split fisico auditado

Archivo: `malaria_dl_local_project/data/malaria_physical_split/metadata.json`

| Split | Uninfected | Parasitized | Total |
|---|---:|---:|---:|
| Train | 11023 | 11023 | 22046 |
| Validation | 1378 | 1378 | 2756 |
| Test | 1378 | 1378 | 2756 |
| Total | 13779 | 13779 | 27558 |

El script `scripts/create_physical_dataset_split.py` usa `train_test_split(..., stratify=labels)` con proporcion 80/10/10 y seed 42. Esto es adecuado para un baseline reproducible.

### Riesgo principal del dataset

El manifest contiene indices, labels, paths y dimensiones, pero no contiene identificadores de:

- Paciente.
- Lamina.
- Campo microscopico.
- Lote.
- Microscopio.
- Laboratorio.
- Tecnico.
- Fecha de adquisicion.

Por lo tanto, no se puede probar que train, validation y test sean independientes a nivel clinico. En imagenes de celulas, una separacion aleatoria por imagen puede sobrestimar desempeno si imagenes correlacionadas del mismo origen quedan en splits distintos.

### Recomendaciones de datos

| Prioridad | Accion |
|---|---|
| Critica | Extender manifest con `patient_id`, `slide_id`, `field_id`, `lab_id`, `microscope_id` cuando exista fuente real. |
| Critica | Implementar split agrupado por paciente/lamina con `GroupShuffleSplit` o equivalente. |
| Alta | Crear validacion externa con imagenes de otro laboratorio o fuente. |
| Alta | Registrar estadisticas de color, foco, brillo, contraste y resolucion por split. |
| Media | Agregar normalizacion de tincion/color como transformacion versionada. |

## 5. Preprocesamiento y augmentacion

`src/preprocessing.py` soporta:

- `rescale_0_1`.
- `vgg16_imagenet`.
- Modo `auto`.

La decision conservadora actual de `resolve_preprocessing_mode("auto")` devuelve `rescale_0_1`. Esto evita cambios silenciosos, pero es riesgoso si se entrena VGG16 sin especificar `--preprocessing vgg16_imagenet`. El output `outputs/vgg16_imagenet` si usa la variante correcta, mientras que `outputs/vgg16` parece corresponder a un experimento historico con `rescale_0_1`.

### Evaluacion

| Aspecto | Estado | Riesgo |
|---|---|---|
| Resize | Correcto para CNNs basicas | Puede perder detalles finos si no se valida resolucion optima. |
| Rescale | Correcto para custom CNN | Correcto solo si coincide entrenamiento/inferencia. |
| VGG preprocessing | Disponible | Debe ser obligatorio para VGG preentrenado. |
| Augmentacion | Aplicada solo a train | Correcto. |
| Stain normalization | No observada como etapa central | Alto para generalizacion externa. |

### Recomendaciones

1. Guardar `preprocessing_mode` como metadata obligatoria del checkpoint.
2. Fallar inferencia si el modo solicitado no coincide con metadata del modelo.
3. Para VGG, cambiar recomendacion o validacion CLI para exigir `vgg16_imagenet`.
4. Agregar experimentos con normalizacion de color/tincion.
5. Reportar metricas estratificadas por calidad de imagen.

## 6. Modelos

### Custom CNN

Archivo: `src/models.py`

Arquitectura:

- Bloques Conv2D 32/64/128/256.
- BatchNorm.
- GlobalAveragePooling.
- Dense 128.
- Dropout 0.4.
- Salida sigmoide.

Es una arquitectura razonable para baseline local: menos pesada, mas interpretable y mas controlable que VGG16. Su principal limitacion es capacidad y generalizacion.

Metricas test disponibles a threshold 0.5:

| Metrica | Valor |
|---|---:|
| Accuracy | 0.9521 |
| Precision | 0.9534 |
| Recall/Sensibilidad | 0.9507 |
| Specificity | 0.9536 |
| F2 | 0.9512 |
| ROC AUC | 0.9749 |
| PR AUC | 0.9706 |
| TN/FP/FN/TP | 1314 / 64 / 68 / 1310 |

### VGG16

Archivo: `src/models.py`

La implementacion usa VGG16 ImageNet sin top, GAP, Dense 1024, dropout y salida sigmoide. Es valido como baseline historico, pero VGG16 es pesado, antiguo y no necesariamente optimo para imagenes microscopicas.

Metricas test `outputs/vgg16` a threshold 0.5:

| Metrica | Valor |
|---|---:|
| Accuracy | 0.9554 |
| Recall/Sensibilidad | 0.9485 |
| Specificity | 0.9623 |
| F2 | 0.9511 |
| ROC AUC | 0.9909 |
| PR AUC | 0.9912 |
| TN/FP/FN/TP | 1326 / 52 / 71 / 1307 |

Metricas test `outputs/vgg16_imagenet` a threshold 0.5:

| Metrica | Valor |
|---|---:|
| Accuracy | 0.9550 |
| Recall/Sensibilidad | 0.9702 |
| Specificity | 0.9398 |
| F2 | 0.9644 |
| ROC AUC | 0.9911 |
| PR AUC | 0.9914 |
| TN/FP/FN/TP | 1295 / 83 / 41 / 1337 |

`vgg16_imagenet` es el mejor de los outputs disponibles si la prioridad es reducir falsos negativos a threshold 0.5. Aun asi, su recall test 0.9702 no alcanza el objetivo clinico configurado de 0.98.

### SVM

Archivo: `src/svm_features.py`

El SVM usa features extraidas de una capa del modelo y entrena un `SVC` RBF. Es util como baseline o ablation, pero no deberia ser candidato principal sin:

- Escalado de features.
- Busqueda de hiperparametros en validation.
- Calibracion probabilistica.
- Evaluacion con threshold clinico.
- Registro completo comparable en DB.

### TTA y ensemble

Archivos: `src/tta.py`, `src/ensemble.py`, `src/inference_pipeline.py`

La logica conceptual es correcta: se promedian probabilidades `probability_parasitized` y luego se aplica threshold. El ensemble disponible a threshold 0.5 no supera a `vgg16_imagenet` en recall.

Metricas test ensemble:

| Metrica | Valor |
|---|---:|
| Accuracy | 0.9550 |
| Recall/Sensibilidad | 0.9485 |
| Specificity | 0.9615 |
| F2 | 0.9510 |
| ROC AUC | 0.9907 |
| PR AUC | 0.9903 |
| TN/FP/FN/TP | 1325 / 53 / 71 / 1307 |

### Recomendaciones de modelado

| Horizonte | Accion |
|---|---|
| Corto | Calibrar y evaluar `vgg16_imagenet` con threshold clinico en validation/test. |
| Corto | Mantener `custom_cnn` como baseline explicable. |
| Medio | Entrenar EfficientNetV2, ResNet50, MobileNetV3 y ConvNeXt-Tiny con el mismo split. |
| Medio | Agregar Optuna/Ray Tune para learning rate, dropout, augmentacion, threshold target y min specificity. |
| Medio | Reportar intervalos de confianza via bootstrap. |
| Largo | Evaluar ViT/Swin solo con pretraining fuerte y validacion externa suficiente. |

## 7. Metricas clinicas

Archivo: `src/metrics.py`

La funcion `compute_clinical_metrics` esta bien alineada con la convencion oficial:

- `y_scores` significa `probability_parasitized`.
- Prediccion positiva si `probability_parasitized >= threshold`.
- Matriz de confusion con labels `[negative_idx, positive_idx]`.
- Sensibilidad = `TP / (TP + FN)`.
- Especificidad = `TN / (TN + FP)`.
- F2 prioriza recall de parasitados.
- ROC AUC y PR AUC usan clase positiva `parasitized`.

Esto es una fortaleza importante del proyecto. La semantica de metricas evita ambiguedades comunes.

### Metricas adicionales necesarias

| Metrica | Motivo |
|---|---|
| Brier score | Medir calibracion probabilistica. |
| Expected Calibration Error | Evaluar confiabilidad de probabilidades. |
| Confidence intervals | Evitar reportar valores puntuales como certeza. |
| PPV/NPV por prevalencia | Traducir rendimiento a escenarios clinicos reales. |
| Curvas decision-threshold | Mostrar trade-off FN/FP. |
| Analisis por calidad de imagen | Detectar degradacion por blur, brillo o contraste. |
| Analisis por fuente/laboratorio | Necesario para generalizacion externa. |

## 8. Politica de checkpoint

Archivo: `src/checkpoint_policy.py`

La politica por defecto es `auc_with_min_recall` con `min_recall=0.98` y rechazo de colapso. Esta es una buena orientacion clinica porque evita seleccionar modelos con AUC alto pero sensibilidad insuficiente.

Outputs auditados:

| Modelo | Politica | Min recall | Selected epoch | Val recall seleccionado | Satisface politica |
|---|---|---:|---:|---:|---|
| custom_cnn | `auc_with_min_recall` | 0.98 | 7 | 0.9274 | No |
| vgg16 | `auc_with_min_recall` | 0.98 | 37 | 0.9412 | No |
| vgg16_imagenet | `auc_with_min_recall` | 0.98 | 29 | 0.9594 | No |

Los tres summaries incluyen advertencia equivalente a: no se alcanzo `min_recall`.

### Riesgo

El sistema configura una politica clinica exigente, pero los modelos disponibles no la cumplen a threshold 0.5. Esto debe aparecer como alerta de primer nivel en cualquier reporte, demo o defensa.

### Observacion sobre EarlyStopping

`src/train.py` mantiene `EarlyStopping` monitoreando `val_auc`, mientras la seleccion de checkpoint usa politica clinica. Esto puede detener entrenamiento antes de estabilizar recall/especificidad segun la politica de seleccion.

Recomendacion: alinear EarlyStopping con la misma politica clinica o implementar paciencia multi-metrica.

## 9. Calibracion de threshold

Archivo: `src/threshold_calibration.py`

La calibracion esta bien disenada en un punto critico: bloquea calibracion sobre test. `validate_calibration_split` rechaza explicitamente `test`.

Calibracion disponible para `custom_cnn`:

| Campo | Valor |
|---|---:|
| Threshold seleccionado | 0.1965 |
| Target recall validation | 0.98 |
| Recall validation obtenido | 0.9804 |
| Specificity validation | 0.6698 |
| Precision validation | 0.7481 |
| F2 validation | 0.9231 |
| FP/FN validation | 455 / 27 |

Comparado con threshold 0.5 en validation:

| Threshold | Recall validation | Specificity validation | FP | FN |
|---|---:|---:|---:|---:|
| 0.5 | 0.9274 | 0.9347 | 90 | 100 |
| 0.1965 | 0.9804 | 0.6698 | 455 | 27 |

La calibracion logra reducir falsos negativos en validacion, pero aumenta fuertemente falsos positivos. Esto puede ser aceptable para un sistema de screening si se comunica como apoyo experimental y si existe revision humana posterior.

### Hallazgo critico

`outputs/custom_cnn/model_metadata.json` contiene `clinical_threshold.enabled=true`, pero `outputs/custom_cnn/test_metrics.json` sigue reportando `threshold_source=fixed_cli` y threshold 0.5. No hay evidencia local de test metrics regeneradas con `--threshold clinical`.

Por lo tanto, no se debe afirmar que el threshold clinico alcanza recall objetivo en test hasta ejecutar una evaluacion formal.

Comando recomendado:

```bash
cd malaria_dl_local_project
.venv/bin/python -m src.evaluate \
  --checkpoint outputs/custom_cnn/best_model.keras \
  --threshold clinical \
  --track-db
```

Luego comparar contra threshold 0.5 y registrar el resultado en dashboard.

## 10. Inferencia individual

Archivos:

- `src/predict_image.py`
- `src/inference_pipeline.py`
- `src/decision.py`
- `src/image_quality.py`

La inferencia produce una respuesta estructurada con:

- Probabilidad de parasitada.
- Probabilidad de no parasitada.
- Threshold usado.
- Fuente del threshold.
- Label predicha.
- Decision human-readable.
- Calidad de imagen.
- Explicabilidad opcional.
- Tracking opcional en DB.

### Fortalezas

| Area | Evaluacion |
|---|---|
| Semantica de probabilidad | Clara: `probability_parasitized`. |
| Threshold clinico | Puede resolverse desde metadata. |
| TTA/ensemble | Promedia probabilidades antes de threshold. |
| Imagen invalida | Se trata como error fatal. |
| Disclaimer | Existe y evita diagnostico definitivo. |

### Riesgos

| Riesgo | Archivo | Recomendacion |
|---|---|---|
| Texto habla de "probabilidad estimada de malaria" | `src/decision.py` | Cambiar a "probabilidad estimada de celula parasitada" o "compatible con celula parasitada". |
| Quality checks simples | `src/image_quality.py` | No tratarlos como validacion clinica; calibrarlos con imagenes reales. |
| Warnings de calidad no bloquean inferencia | `src/predict_image.py` | Para modo clinico experimental, permitir politica configurable: advertir, bloquear o requerir revision. |

## 11. Explicabilidad

Archivos:

- `src/explain.py`
- `frontend/src/pages/Explainability.tsx`
- `backend_api/app/routes/explainability.py`

El pipeline genera Grad-CAM, LIME y SHAP. Tambien selecciona casos por:

- True positive.
- True negative.
- False positive.
- False negative.
- Low confidence.

El resumen actual tiene 60 filas: 20 por metodo, 12 por tipo de caso, todas con `success=true`.

### Fortalezas

| Aspecto | Evaluacion |
|---|---|
| Cobertura de metodos | Buena para auditoria exploratoria. |
| Cobertura de errores | Incluye FP/FN, no solo aciertos. |
| Registro | Se integra con DB y artefactos. |
| Threshold metadata | Incluye threshold y fuente en summaries. |

### Limitaciones

| Limitacion | Impacto |
|---|---|
| Explicabilidad no validada por expertos | No prueba causalidad ni razonamiento clinico correcto. |
| SHAP usa background pequeno | Puede ser inestable. |
| Explicaciones sobre test pueden inducir tuning indirecto | Deben usarse solo como auditoria congelada. |
| Frontend no muestra imagen original lado a lado | Dificulta evaluar si el mapa se ubica sobre estructuras relevantes. |

### Recomendacion critica de UI

En `frontend/src/pages/Explainability.tsx`, los bloques de "Imagen real" estan comentados tanto en la tabla como en la galeria. Deben restaurarse para comparar:

- Imagen original.
- Heatmap/explicacion.
- Label real.
- Label predicha.
- Probabilidad.
- Tipo de caso.

### Protocolo recomendado de validacion de explicabilidad

1. Seleccionar muestra estratificada de TP, TN, FP, FN y baja confianza.
2. Revision ciega por al menos dos expertos.
3. Escala de plausibilidad: incorrecta, dudosa, parcialmente plausible, plausible.
4. Registrar si la activacion cae sobre parasitos, borde celular, fondo, artefactos o zonas no informativas.
5. Medir acuerdo interevaluador.
6. Crear taxonomia de fallos.
7. No usar los resultados para ajustar el modelo sin separar un nuevo conjunto de validacion.

## 12. Tracking y PostgreSQL

Archivos principales:

- `db/init/001_schema.sql`
- `db/init/012_dataset_split_image_tracking.sql`
- `db/init/017_clinical_run_tracking.sql`
- `src/db.py`
- `src/db_tracking.py`
- `src/dataset_registry.py`
- `scripts/init_db.py`

El modelo de datos es amplio y bien orientado a trazabilidad:

| Entidad | Estado |
|---|---|
| Experiments/runs/models | Presente. |
| Training history | Presente. |
| Clinical metrics | Presente. |
| Checkpoint policy | Presente. |
| Threshold calibration | Presente. |
| Predictions | Presente. |
| Explainability results | Presente. |
| Artifacts | Presente. |
| Dataset split images | Presente. |
| Run to dataset image usage | Presente. |
| Uploaded predictions | Presente en migraciones posteriores. |

### Fortalezas

| Fortaleza | Evidencia |
|---|---|
| Trazabilidad imagen-run | `dataset_split_images`, `run_dataset_images`. |
| Vistas para dashboard | `vw_clinical_run_summary`, `vw_run_artifacts_summary`, etc. |
| Idempotencia parcial | Uso frecuente de `CREATE TABLE IF NOT EXISTS`, indices `IF NOT EXISTS`. |
| Registro de calibracion | `run_threshold_calibration`. |

### Riesgos

| Riesgo | Archivo | Recomendacion |
|---|---|---|
| `CREATE OR REPLACE VIEW` puede fallar si cambia estructura | `003_views.sql`, `009_uploaded_predictions_views.sql` | Usar `DROP VIEW IF EXISTS ... CASCADE; CREATE VIEW ...`. |
| Split SQL manual por semicolon | `scripts/init_db.py` | Usar migrador formal o parser robusto si aparecen funciones complejas. |
| Sin migraciones reversibles | `db/init` | Migrar a Alembic o similar. |
| Sin checksums de migracion aplicada | `scripts/init_db.py` | Registrar version/checksum. |

## 13. Backend API

Archivos:

- `backend_api/app/main.py`
- `backend_api/app/db.py`
- `backend_api/app/routes/*.py`
- `backend_api/app/services/*.py`

La API es principalmente read-only y expone endpoints para:

- Health.
- Dashboard.
- Runs.
- Catalogo.
- Dataset browser.
- Metricas.
- Explicabilidad.
- Predicciones subidas.
- Observabilidad.
- Artefactos.

### Fortalezas

| Area | Evaluacion |
|---|---|
| Separacion por routers | Clara. |
| Parametros SQL | Uso de `text` con parametros en consultas revisadas. |
| Artifact serving | Raices permitidas, extensiones permitidas, magic bytes, `nosniff`. |
| Dataset browser | Fallback local si DB no esta disponible. |
| CORS local | Limitado a localhost para desarrollo. |

### Debilidades

| Debilidad | Riesgo | Recomendacion |
|---|---|---|
| Sin autenticacion | Alto si se despliega | Agregar auth por token/OIDC/session. |
| Validacion UUID inconsistente | Medio | Responder 400 antes de cast SQL. |
| Tests no ejecutables por dependencia faltante | Medio | Agregar `pytest` a dev requirements. |
| No se observa rate limiting | Medio | Agregar si hay uploads o exposicion externa. |
| No hay contrato OpenAPI versionado | Bajo-medio | Publicar schema y pruebas contractuales. |

## 14. Frontend

Archivos:

- `frontend/src/App.tsx`
- `frontend/src/services/api.ts`
- `frontend/src/pages/DatasetBrowser.tsx`
- `frontend/src/pages/ClinicalEvaluation.tsx`
- `frontend/src/pages/RunDetail.tsx`
- `frontend/src/pages/Explainability.tsx`
- `frontend/src/pages/UploadedPredictions.tsx`
- `frontend/src/components/ConfusionMatrix.tsx`

El frontend esta bien orientado a auditoria de modelos: muestra runs, metricas clinicas, politicas de checkpoint, thresholds, matriz de confusion, predicciones por imagen, dataset browser, artefactos y explicabilidad.

### Fortalezas

| Pantalla | Evaluacion |
|---|---|
| DatasetBrowser | Buena trazabilidad de split, labels, conteos e imagenes. |
| ClinicalEvaluation | Enfatiza recall, specificity, F2, PR-AUC y colapso. |
| RunDetail | Muestra alertas por politica no satisfecha, collapse, threshold y artefactos. |
| ConfusionMatrix | Etiqueta FN como parasitados clasificados no infectados; correcto. |
| Explainability | Galeria y filtros por caso/metodo. |

### Problemas concretos

| Severidad | Archivo | Problema | Correccion |
|---|---|---|---|
| Alta | `Explainability.tsx` | Imagen original comentada en tabla y galeria. | Restaurar side-by-side original vs explicacion. |
| Media-alta | `UploadedPredictions.tsx` | Usa truthy checks para probabilidades y threshold; `0.0` se renderiza como `-`. | Usar `value === null || value === undefined`. |
| Media | `UploadedPredictions.tsx` | Filtro confidence usa `high/medium/low`, pero backend/inferencia puede emitir `alta/media/baja`. | Normalizar valores o mapear ambos idiomas. |
| Media | Frontend completo | No hay tests. | Agregar Vitest y Playwright para flujos clinicos. |

## 15. Seguridad, privacidad y despliegue

No se observo evidencia de datos personales directos en el dataset actual, pero el sistema esta disenado para trabajar con imagenes medicas. Si se incorporan datos reales, hay que tratarlo como informacion sensible.

### Estado actual

| Area | Estado |
|---|---|
| Auth | No implementada. |
| Autorizacion | No implementada. |
| Cifrado en transito | Depende del despliegue; local no aplica. |
| Secret management | `.env` soportado; revisar no commitear credenciales. |
| Artifact serving | Bastante controlado para local. |
| Uploads | Requieren limites, validacion y limpieza si se exponen. |

### Recomendaciones antes de compartir fuera de localhost

1. Agregar autenticacion.
2. Agregar roles: viewer, reviewer, admin.
3. Limitar CORS a origen real.
4. Agregar rate limiting.
5. Agregar tamano maximo de uploads.
6. Sanitizar y expirar archivos temporales.
7. Activar HTTPS.
8. Registrar auditoria de acceso.
9. Definir politica de retencion de imagenes.

## 16. Riesgos clinicos y tecnicos

| Riesgo | Severidad | Probabilidad | Evidencia | Mitigacion |
|---|---|---:|---|---|
| Falsos negativos | Critica | Media | FN test: 41 a 71 segun modelo a threshold 0.5 | Threshold clinico, revision humana, objetivo recall, validacion externa. |
| Falsos positivos excesivos | Alta | Alta con threshold bajo | Custom threshold validation sube FP a 455 | Definir min specificity y flujo de confirmacion. |
| Fuga por paciente/lamina | Critica | Desconocida | No hay IDs de paciente/lamina | Split agrupado y metadata clinica. |
| No generalizacion externa | Critica | Alta | Solo dataset local/TFDS derivado | Validacion multi-fuente/OOD. |
| Etiquetas invertidas | Critica | Baja | Codigo y tests cubren mapping | Mantener metadata y tests de contrato. |
| Colapso de prediccion | Alta | Baja actual | Detector existe y outputs no muestran collapse | Mantener gate de release. |
| Calibracion insuficiente | Alta | Media | Threshold custom solo validado en validation | Evaluar test, Brier, ECE, CI. |
| UI oculta informacion critica | Media-alta | Media | Imagen real comentada, zeros ocultos | Corregir frontend y testear. |
| Migraciones fragiles | Media | Media | `CREATE OR REPLACE VIEW`, splitter manual | Drop/create y migrador formal. |
| Exposicion sin auth | Alta | Media si se despliega | API sin auth | Auth antes de despliegue. |
| Interpretacion clinica exagerada | Alta | Media | Texto "probabilidad estimada de malaria" | Reescribir a nivel celula/imagen. |

## 17. Preparacion para comite, demo o defensa

### Lo que se puede afirmar con respaldo

- El sistema clasifica imagenes individuales de celulas como `parasitized` o `uninfected`.
- La convencion de etiquetas esta documentada y probada.
- El split fisico es balanceado y reproducible por imagen.
- Las metricas clinicas estan calculadas con `parasitized` como clase positiva.
- El pipeline evita calibrar threshold sobre test.
- Hay tracking experimental en PostgreSQL.
- Hay frontend para revisar runs, datos, metricas, predicciones y explicabilidad.
- ML tests pasan localmente.

### Lo que no se debe afirmar

- Que el sistema diagnostica malaria a nivel paciente.
- Que esta validado clinicamente.
- Que alcanza recall clinico objetivo en test con threshold calibrado.
- Que generaliza a otros laboratorios.
- Que Grad-CAM/LIME/SHAP prueban que el modelo mira parasitos reales.
- Que el split garantiza independencia por paciente/lamina.

### Frase recomendada

"El sistema es un prototipo experimental de apoyo para clasificacion de imagenes individuales de celulas en parasitadas/no parasitadas. No constituye diagnostico clinico. Los resultados actuales muestran desempeno prometedor en un split reproducible por imagen, pero requieren validacion externa, control de independencia por paciente/lamina y evaluacion formal del threshold clinico antes de cualquier uso operativo."

## 18. Roadmap priorizado

### 0 a 2 semanas

| Prioridad | Accion | Impacto esperado |
|---|---|---|
| P0 | Regenerar test metrics con `--threshold clinical` para `custom_cnn`. | Saber si el threshold clinico generaliza a test. |
| P0 | Calibrar y evaluar `vgg16_imagenet` con validation/test. | Comparar mejor recall actual contra threshold clinico. |
| P0 | Corregir texto de inferencia de "malaria" a "celula parasitada". | Reducir riesgo de sobreinterpretacion clinica. |
| P0 | Restaurar imagen original en `Explainability.tsx`. | Mejorar auditabilidad humana. |
| P1 | Corregir render de valores `0.0` en `UploadedPredictions.tsx`. | Evitar ocultar probabilidades validas. |
| P1 | Agregar `pytest` a backend dev requirements y ejecutar tests. | Cerrar brecha de verificacion backend. |
| P1 | Cambiar vistas SQL fragiles a `DROP VIEW IF EXISTS ... CASCADE; CREATE VIEW`. | Reducir fallos de migracion. |
| P1 | Agregar alerta de alto nivel cuando `policy_satisfied=false`. | Evitar presentar modelos no conformes. |

### 2 a 6 semanas

| Prioridad | Accion | Impacto esperado |
|---|---|---|
| P1 | Agregar ECE, Brier score y calibration plots. | Mejor evaluacion probabilistica. |
| P1 | Agregar bootstrap CI para metricas principales. | Reportes mas rigurosos. |
| P1 | Agregar min specificity a calibracion clinica. | Controlar explosion de falsos positivos. |
| P1 | Implementar tests frontend con Vitest. | Evitar regresiones en UI clinica. |
| P1 | Implementar Playwright para flujos dataset/run/explainability. | Verificacion end-to-end. |
| P2 | Agregar normalizacion de tincion/color. | Mejor robustez OOD. |
| P2 | Agregar metricas por calidad de imagen. | Detectar fallos por blur/brillo/contraste. |

### 6 a 12 semanas

| Prioridad | Accion | Impacto esperado |
|---|---|---|
| P1 | Conseguir metadata de paciente/lamina o dataset externo con grupos. | Reducir riesgo de leakage. |
| P1 | Implementar split agrupado. | Evaluacion mas clinicamente valida. |
| P1 | Entrenar EfficientNetV2/MobileNetV3/ResNet50/ConvNeXt. | Mejorar trade-off recall/specificity. |
| P2 | Busqueda de hiperparametros reproducible. | Optimizar sin tuning manual. |
| P2 | Validacion de explicabilidad con expertos. | Evidencia cualitativa defendible. |

### 3 a 6 meses

| Prioridad | Accion | Impacto esperado |
|---|---|---|
| P0 | Validacion externa multi-fuente. | Requisito para credibilidad clinica. |
| P1 | Workflow de revision humana en frontend. | Pasar de dashboard a sistema de auditoria. |
| P1 | MLOps formal: model registry, data versioning, CI/CD. | Reproducibilidad operacional. |
| P2 | Docker Compose completo con DB/API/frontend/worker. | Despliegue reproducible. |

### 6 meses o mas

| Prioridad | Accion | Impacto esperado |
|---|---|---|
| P0 | Estudio prospectivo controlado. | Evidencia para uso real. |
| P1 | Segmentacion/deteccion si hay mascaras o bounding boxes. | Mejor interpretabilidad morfologica. |
| P1 | Documentacion regulatoria y gestion de riesgos. | Preparacion para entorno clinico real. |

## 19. Lista de archivos y modulos revisados

### ML, datos y scripts

- `malaria_dl_local_project/src/config.py`
- `malaria_dl_local_project/src/data.py`
- `malaria_dl_local_project/src/models.py`
- `malaria_dl_local_project/src/metrics.py`
- `malaria_dl_local_project/src/train.py`
- `malaria_dl_local_project/src/evaluate.py`
- `malaria_dl_local_project/src/calibrate.py`
- `malaria_dl_local_project/src/threshold_calibration.py`
- `malaria_dl_local_project/src/checkpoint_policy.py`
- `malaria_dl_local_project/src/model_metadata.py`
- `malaria_dl_local_project/src/predict_image.py`
- `malaria_dl_local_project/src/inference_pipeline.py`
- `malaria_dl_local_project/src/decision.py`
- `malaria_dl_local_project/src/image_quality.py`
- `malaria_dl_local_project/src/preprocessing.py`
- `malaria_dl_local_project/src/tta.py`
- `malaria_dl_local_project/src/ensemble.py`
- `malaria_dl_local_project/src/svm_features.py`
- `malaria_dl_local_project/src/explain.py`
- `malaria_dl_local_project/src/dataset_registry.py`
- `malaria_dl_local_project/scripts/create_physical_dataset_split.py`
- `malaria_dl_local_project/scripts/init_db.py`
- `malaria_dl_local_project/scripts/validate.sh`
- `malaria_dl_local_project/data/malaria_physical_split/metadata.json`

### Outputs auditados

- `malaria_dl_local_project/outputs/custom_cnn/test_metrics.json`
- `malaria_dl_local_project/outputs/custom_cnn/threshold_calibration.json`
- `malaria_dl_local_project/outputs/custom_cnn/checkpoint_policy_summary.json`
- `malaria_dl_local_project/outputs/custom_cnn/model_metadata.json`
- `malaria_dl_local_project/outputs/vgg16/test_metrics.json`
- `malaria_dl_local_project/outputs/vgg16/checkpoint_policy_summary.json`
- `malaria_dl_local_project/outputs/vgg16/model_metadata.json`
- `malaria_dl_local_project/outputs/vgg16_imagenet/test_metrics.json`
- `malaria_dl_local_project/outputs/vgg16_imagenet/checkpoint_policy_summary.json`
- `malaria_dl_local_project/outputs/vgg16_imagenet/model_metadata.json`
- `malaria_dl_local_project/outputs/ensemble/ensemble_test_metrics.json`
- `malaria_dl_local_project/outputs/explainability/explanation_summary.csv`

### Base de datos

- `malaria_dl_local_project/db/init/001_schema.sql`
- `malaria_dl_local_project/db/init/003_views.sql`
- `malaria_dl_local_project/db/init/009_uploaded_predictions_views.sql`
- `malaria_dl_local_project/db/init/012_dataset_split_image_tracking.sql`
- `malaria_dl_local_project/db/init/017_clinical_run_tracking.sql`
- migraciones SQL relacionadas en `malaria_dl_local_project/db/init`

### Backend

- `backend_api/app/main.py`
- `backend_api/app/db.py`
- `backend_api/app/routes/dataset.py`
- `backend_api/app/routes/explainability.py`
- `backend_api/app/routes/runs.py`
- `backend_api/app/routes/predictions.py`
- `backend_api/app/services/dataset_browser.py`
- `backend_api/app/services/artifacts.py`
- `backend_api/tests/test_clinical_summary_api.py`
- `backend_api/tests/test_dataset_browser_api.py`
- `backend_api/tests/test_model_comparison_api.py`
- `backend_api/tests/test_run_detail_api.py`

### Frontend

- `frontend/src/App.tsx`
- `frontend/src/services/api.ts`
- `frontend/src/pages/DatasetBrowser.tsx`
- `frontend/src/pages/ClinicalEvaluation.tsx`
- `frontend/src/pages/RunDetail.tsx`
- `frontend/src/pages/Explainability.tsx`
- `frontend/src/pages/UploadedPredictions.tsx`
- `frontend/src/components/ConfusionMatrix.tsx`
- `frontend/package.json`

## 20. Prompts sugeridos para siguientes iteraciones

### Correccion frontend critica

```text
Corrige frontend/src/pages/Explainability.tsx para mostrar la imagen original lado a lado con la explicacion en tabla y galeria. Mantiene filtros actuales, usa artifactUrl/imageUrl existentes y agrega estados de carga/error. Luego ejecuta npm run build.
```

### Correccion de valores cero en predicciones

```text
Revisa frontend/src/pages/UploadedPredictions.tsx y reemplaza checks truthy de probability_parasitized, probability_uninfected y threshold_used por checks null/undefined. Normaliza confidence para aceptar alta/media/baja y high/medium/low. Agrega tests si el proyecto ya tiene framework; si no, deja preparado el cambio y ejecuta npm run build.
```

### Evaluacion clinica real del threshold

```text
Ejecuta o prepara la evaluacion de custom_cnn con --threshold clinical sobre test, registra resultados en PostgreSQL si la DB esta disponible y compara contra threshold 0.5. Reporta FN, FP, recall, specificity, F2, PR-AUC y si el target recall se sostiene en test.
```

### Hardening de migraciones

```text
Audita db/init/003_views.sql y db/init/009_uploaded_predictions_views.sql. Cambia CREATE OR REPLACE VIEW por DROP VIEW IF EXISTS ... CASCADE; CREATE VIEW ... donde corresponda, cuidando dependencias. Ejecuta tests de migracion disponibles.
```

### Backend tests

```text
Agrega dependencias de test al backend, ejecuta backend_api/tests y corrige fallos sin modificar comportamiento de API. Si falta requirements-dev.txt, crealo con pytest y dependencias minimas.
```

### Nuevo baseline de modelo

```text
Implementa un baseline EfficientNetV2 o MobileNetV3 siguiendo los patrones existentes en src/models.py, train.py y metadata. Debe guardar preprocessing_mode correcto, soportar checkpoint policy, threshold calibration, evaluate.py y tracking DB.
```

### Validacion externa y anti-leakage

```text
Disena una extension del manifest del dataset con patient_id, slide_id, lab_id y microscope_id. Implementa split agrupado reproducible y reporta diferencias de metricas contra el split aleatorio actual.
```

## 21. Conclusion

El proyecto esta bien encaminado como plataforma experimental integral: no es solo un notebook de entrenamiento, sino un sistema con datos versionables, metricas clinicas, calibracion, explicabilidad, tracking, API y frontend. Esa es una base fuerte.

La brecha principal para elevarlo a un sistema defendible no esta en agregar mas pantallas, sino en cerrar tres temas: independencia y validacion externa de datos, cumplimiento real del objetivo de sensibilidad con threshold clinico evaluado en test, y auditabilidad visual/operacional sin ambiguedades clinicas.

La recomendacion arquitectonica es mantener la estructura actual, corregir los defectos de alto impacto, agregar gates de calidad y enfocar las siguientes iteraciones en validacion experimental rigurosa antes de ampliar funcionalidad.
