# Auditoría de observaciones expertas sobre los modelos de malaria

> **Estado documental: HISTORICAL_AUDIT.** Snapshot del ZIP identificado abajo;
> preservado como evidencia de la revisión realizada. Sus afirmaciones sobre el split
> anterior no describen `Malaria Patient Split v1` (`FROZEN`, patient-disjoint) y no
> deben usarse como estado actual del repositorio.

**Proyecto revisado:** `capstone-main(3).zip`  
**Área:** Deep Learning aplicado a imágenes microscópicas de frotis sanguíneo  
**Tipo de revisión:** análisis estático de código, configuración, pruebas y artefactos de liberación incluidos en el ZIP.

## 1. Conclusión ejecutiva

Las seis observaciones son técnicamente razonables como lista general de riesgos, pero no todas describen correctamente la versión actual del sistema.

1. **Fuga de datos por paciente:** confirmada como brecha crítica. El split actual se realiza por imagen/célula y no conserva `patient_id` ni `smear_id`.
2. **Umbral clínico:** la necesidad es real, pero el sistema ya implementa calibración orientada a recall sobre validación. Reemplazarla por J de Youden no sería una mejora automática; para este caso clínico la política de recall objetivo está mejor alineada con la reducción de falsos negativos.
3. **Flatten + Dense(4096):** no existe en la versión revisada. Los tres modelos usan Global Average Pooling y Dropout; `custom_cnn` además usa L2.
4. **Ensemble sin calibración individual:** la brecha existe, aunque la afirmación de que un modelo “dominará completamente” es exagerada para un promedio ponderado. El sistema puede calibrar el resultado final del ensemble, pero no cada modelo antes de combinarlo.
5. **TTA para todas las imágenes:** confirmado. Cuando se activa, se aplica siempre; no existe TTA condicional. Con `n_aug=8`, cada imagen usa nueve vistas incluyendo la original.
6. **Color augmentation:** parcialmente confirmada. Hay contraste, pero no hay jitter explícito de hue, saturation, brightness, balance de blancos o normalización de tinción.

## 2. Tabla resumen

| Programa / componente | Observación evaluada | Evidencia encontrada | Veredicto | Necesidad | Recomendación |
|---|---|---|---|---|---|
| `scripts/create_physical_dataset_split.py` | Fuga de datos por paciente | `collect_tfds_records()` conserva solo índice y etiqueta (`115-137`). `stratified_split_records()` usa `train_test_split` sobre índices de imágenes (`140-169`). El manifest no contiene paciente, lámina o muestra (`297-309`, `333-345`). | **Confirmada** | **Crítica / P0** | Obtener el CSV oficial de mapeo célula-paciente, extender el manifest con `patient_id`/`smear_id` y dividir grupos completos con `StratifiedGroupKFold`, `GroupShuffleSplit` o una asignación determinista estratificada por paciente. |
| `src/malaria_dl/data/loaders.py` y BD | Control de integridad del split | `validate_physical_split()` verifica clases, carpetas y cantidades, pero no disyunción de pacientes (`103-175`). `dataset_split_images` tampoco tiene columnas de paciente/lámina (`db/init/012...:1-30`). | **Confirmada** | **Crítica / P0** | Añadir guardas que fallen si un `patient_id`, `slide_id` o `smear_id` aparece en más de un split. Registrar grupos en PostgreSQL y crear una vista de auditoría de leakage. |
| `src/malaria_dl/evaluation/threshold_calibration.py` | Umbral 0.5 inseguro | Existe `DEFAULT_THRESHOLD=0.5` (`21-27`), pero `find_threshold_for_target_recall()` busca un threshold que alcance recall objetivo y usa especificidad/F2 como desempate (`154-272`). Rechaza calibrar con test (`54-60`). | **Parcial / observación desactualizada** | **Alta**, pero ya implementada | Mantener la política `target_recall`; hacerla obligatoria para modelos productivos. No sustituirla sin validación por J de Youden, porque Youden pondera sensibilidad y especificidad de forma simétrica. |
| `src/malaria_dl/training/trainer.py`, `run_train_all_models.py` | Integración real del threshold | La calibración es opcional en CLI (`trainer.py:169-184`) y sin ella test usa 0.5 (`1706-1720`). El orquestador oficial sí activa `--calibrate-threshold --target-recall 0.98` (`run_train_all_models.py:99-116`). | **Implementada con riesgo de bypass** | **Alta / P1** | Exigir threshold clínico calibrado como precondición de liberación, salvo modo explícitamente experimental. Cambiar inferencia productiva para resolver `clinical` por defecto. |
| Releases Stage 2 | Uso de thresholds clínicos | Los artefactos incluidos declaran thresholds 0.126208 para `custom_cnn` y 0.275814 para `densenet121`, ambos con calibración clínica. | **Confirmación de implementación** | — | Validar que cada threshold tenga métricas independientes de test y que pertenezca exactamente al mismo checkpoint y calibrador de probabilidad liberado. |
| `src/malaria_dl/models/architectures.py` | Flatten + Dense(4096) provoca sobreajuste | No aparece `Flatten`. `custom_cnn`: GAP + Dense(128) + L2 + Dropout 0.4 (`203-235`). VGG16: GAP + Dense(1024) + Dropout 0.5 (`246-285`). DenseNet121: GAP + Dropout 0.5 + salida (`288-336`). | **No verdadera para este ZIP** | **Baja como corrección inmediata** | No implementar el cambio propuesto porque ya existe. Mantener vigilancia de sobreajuste mediante curvas, gap train/val, regularización y validación agrupada. Evaluar reducir Dense(1024) de VGG solo si ablations muestran beneficio. |
| `src/malaria_dl/evaluation/probability_calibration.py` | CNN sobreconfiadas | Implementa Temperature Scaling, NLL, Brier y ECE (`31-144`). Solo acepta `temperature_scaling` (`147-226`). | **Mitigación existente** | **Alta / P1** | Conservar Temperature Scaling. Añadir reliability diagrams, bootstrap de ECE/Brier y control de drift de calibración. Isotonic/Platt pueden incorporarse como alternativas, no como reemplazo obligatorio. |
| `src/malaria_dl/inference/ensemble.py` | Promedio de probabilidades sin calibrar | Modelos predicen directamente y sus probabilidades se promedian (`143-180`). No se carga un calibrador por modelo. Los pesos son iguales por defecto o manuales (`145-151`). | **Confirmada** | **Alta / P1** | Permitir un perfil de calibración por miembro y luego recalibrar el ensemble completo sobre validación. Aprender pesos con validación agrupada, no definirlos manualmente sin evidencia. |
| `src/malaria_dl/inference/pipeline.py` | Orden de calibración del ensemble | `predict_ensemble_probability()` promedia resultados crudos (`176-235`) y `apply_probability_calibration()` calibra una sola probabilidad final (`238-251`). | **Brecha parcial** | **Alta / P1** | Comparar experimentalmente: ensemble crudo + calibración final, miembros calibrados + promedio, y miembros calibrados + recalibración final. Elegir por NLL/Brier/ECE y métricas clínicas, no por supuesto teórico. |
| `src/malaria_dl/inference/ensemble.py` | Preprocesamiento heterogéneo | Un único `--preprocessing` se aplica a todos los modelos (`57-62`, `153-160`). | **Hallazgo adicional** | **Alta / P1** | Cada miembro debe cargar su propio contrato de preprocesamiento desde metadata. Rechazar ensembles incompatibles si no existe un adaptador por modelo. |
| `src/malaria_dl/inference/tta.py` | TTA costoso para todas las células | `n_aug=8` por defecto (`39-47`). Se genera la original más ocho aumentos (`80-114`) para cada imagen del test (`181-195`). No hay condición por incertidumbre. | **Confirmada** | **Media-Alta / P1** | Implementar TTA selectivo alrededor del threshold clínico: por ejemplo `abs(p - threshold) <= delta`, entropía alta o desacuerdo del ensemble. No usar una zona fija 0.3–0.7 cuando el threshold liberado puede ser 0.126 o 0.276. |
| `src/malaria_dl/inference/tta.py` | Eficiencia de implementación | Para preprocesamiento no VGG realiza una llamada `predict()` por vista (`96-114`), aumentando también overhead de ejecución. | **Confirmada** | **Media / P2** | Construir un batch con todas las vistas y ejecutar una sola inferencia, como ya hace parcialmente `inference/pipeline.py`. Medir latencia p50/p95 y throughput. |
| `src/malaria_dl/data/loaders.py` | Aumentación desalineada con tinción | Contiene flip, rotation, translation, zoom y contrast (`481-495`), pero no hue/saturation/brightness ni normalización de tinción. | **Parcialmente confirmada** | **Alta / P1** | Añadir augmentations cromáticas suaves y configurables antes del preprocesamiento específico del modelo. Validar que preserven morfología y etiqueta. Considerar normalización de color y pruebas externas por laboratorio/microscopio. |
| Pruebas | Cobertura de riesgos clínicos | `test_physical_dataset_split.py` valida reproducibilidad y balance por clase, no grupos de pacientes (`30-61`). Las pruebas de ensemble/TTA verifican promedio y threshold, no calibración por miembro ni TTA condicional. | **Confirmada** | **Alta / P1** | Incorporar tests de disyunción de grupos, lineage del calibrador, compatibilidad de preprocesamiento, calibración del ensemble y activación condicional de TTA. |

## 3. Análisis detallado

### 3.1 Fuga de datos por paciente

Esta es la observación más importante y la única que puede invalidar transversalmente las métricas actuales. El código crea una lista de células individualizadas y las divide aleatoriamente de forma estratificada por clase. No existe una clave de agrupación clínica. Por tanto, el sistema no puede asegurar que células del mismo paciente o frotis no queden distribuidas entre entrenamiento, validación y test.

La solución mínima no es necesariamente implementar validación cruzada completa. Lo indispensable es:

1. Conservar la identidad de paciente/muestra desde la fuente.
2. Crear un holdout de test por paciente que permanezca congelado.
3. Realizar selección de arquitectura, checkpoint, threshold y calibración solo con train/validation agrupados.
4. Usar validación cruzada agrupada como complemento cuando el número de pacientes sea pequeño o se necesiten intervalos más robustos.
5. Reportar métricas por célula y por paciente/frotis.

El dataset oficial dispone de archivos CSV de correspondencia entre Patient-ID y células, pero la ruta TFDS usada en el proyecto carga únicamente `(image, label)` mediante `as_supervised=True`; esa simplificación elimina la información requerida para el split clínicamente correcto.

### 3.2 Calibración del threshold clínico

La observación original asume que el sistema decide siempre con 0.5. Esto no describe el flujo completo actual. El proyecto implementa:

- calibración exclusivamente sobre validation;
- recall objetivo configurable, por defecto 0.98;
- especificidad mínima opcional;
- desempate por especificidad, precisión, F2 y balanced accuracy;
- artefacto `threshold_calibration.json` y metadata asociada;
- evaluación posterior sobre test con el threshold seleccionado cuando `--calibrate-threshold` está activo.

Para una tarea donde los falsos negativos son prioritarios, esta política es más coherente que maximizar J de Youden como objetivo principal. Youden puede incluirse como análisis secundario o baseline, pero no garantiza el recall clínico mínimo.

La brecha real es operacional: `--calibrate-threshold` no es obligatorio en el CLI general y la inferencia conserva `0.5` como default. El orquestador de entrenamientos sí activa la calibración, y los releases Stage 2 incluidos ya contienen thresholds clínicos diferentes de 0.5.

### 3.3 Arquitecturas y sobreajuste

La descripción `Flatten() -> Dense(4096)` no corresponde al código actual. Las tres arquitecturas ya aplican Global Average Pooling. Esto elimina la corrección propuesta como tarea inmediata.

Persisten riesgos normales de sobreajuste, especialmente:

- VGG16 mantiene una capa Dense de 1024 unidades después del GAP;
- el dataset efectivo por paciente puede ser mucho menor que el conteo de células;
- el fine-tuning y la selección de hiperparámetros pueden explotar correlaciones de paciente si no se corrige el split;
- la regularización arquitectónica no compensa una validación con leakage.

Antes de modificar las cabezas, debe corregirse el split agrupado y luego ejecutar ablations controladas: Dense(1024) versus Dense(256) versus cabeza lineal, manteniendo pacientes y semillas constantes.

### 3.4 Ensemble y calibración

El ensemble standalone y el pipeline clínico promedian probabilidades no calibradas de los miembros. Después, el pipeline puede aplicar un único Temperature Scaling al resultado agregado.

La observación es válida como brecha funcional, pero su solución debe ser experimental. Calibrar cada miembro no garantiza por sí solo que el promedio quede calibrado. La estrategia recomendada es implementar y comparar tres variantes sobre una validación agrupada:

1. Promedio crudo y calibración del ensemble final.
2. Calibración individual y promedio.
3. Calibración individual, promedio y recalibración final.

La selección debe considerar NLL, Brier, ECE, recall, specificity, F2 y estabilidad por paciente. También debe validarse la diversidad entre modelos; combinar modelos altamente correlacionados puede aportar poco aunque estén calibrados.

Existe además una brecha no mencionada: todos los miembros reciben el mismo modo de preprocesamiento. Un ensemble robusto debe resolver el preprocesamiento por checkpoint desde su metadata.

### 3.5 TTA condicional

La observación es correcta respecto de la implementación: activar TTA implica aplicarlo a todas las imágenes. Con `n_aug=8` se procesan nueve vistas por célula. En el evaluador TTA, la rama no VGG realiza predicciones separadas por vista, por lo que el costo incluye tanto cómputo como overhead de llamadas.

La zona fija `0.3–0.7` no es apropiada para este proyecto porque los thresholds clínicos liberados son muy inferiores a 0.5. La incertidumbre debe definirse en torno al threshold efectivo o mediante entropía/desacuerdo. Ejemplo conceptual:

```python
needs_tta = abs(probability_parasitized - clinical_threshold) <= margin
```

El margen debe calibrarse con validación. Además, TTA no debe asumirse beneficioso: debe demostrarse que mejora sensibilidad, calibración o estabilidad sin deteriorar especificidad ni alterar la distribución de entrada.

### 3.6 Aumentación cromática y tinción

El pipeline actual sí tiene una forma de variación cromática mediante `RandomContrast(0.3)`, por lo que no está completamente desprovisto de robustez de color. Sin embargo, no modela explícitamente cambios de:

- saturación;
- hue;
- brillo/exposición;
- temperatura o balance de blancos;
- intensidad y protocolo de Giemsa;
- laboratorio, cámara o microscopio.

La recomendación de HSV es razonable, pero no debe limitarse únicamente al canal de saturación. Debe construirse una política físicamente plausible, con rangos moderados, inspección visual y pruebas de no alteración de etiqueta. También conviene separar:

- augmentation para entrenamiento;
- normalización de color determinista;
- pruebas de robustez y domain shift externas.

## 4. Prioridad recomendada

### P0 — Antes de aceptar nuevas métricas como clínicas

1. Incorporar `patient_id`/`smear_id` al dataset y manifest.
2. Regenerar train/validation/test mediante grupos disjuntos.
3. Congelar un test por paciente.
4. Reentrenar y recalibrar todos los modelos desde cero.
5. Invalidar comparaciones clínicas directas con métricas obtenidas mediante el split por imagen, o etiquetarlas explícitamente como exploratorias.

### P1 — Robustez de probabilidad e inferencia

1. Hacer obligatoria la calibración de threshold para liberación Stage 2.
2. Implementar perfiles de calibración y preprocesamiento por miembro del ensemble.
3. Calibrar también el ensemble final y aprender pesos en validation agrupada.
4. Implementar TTA condicional y medir beneficio/latencia.
5. Añadir color augmentation plausible y pruebas por dominio.
6. Ampliar tests y guardas de leakage.

### P2 — Optimización posterior

1. Ablations de la cabeza VGG16.
2. Batch único para vistas TTA.
3. Intervalos de confianza por bootstrap de pacientes.
4. Métricas y decisión agregadas a nivel de frotis/paciente.

## 5. Veredicto final por observación

| Observación | Veracidad en el código actual | Acción |
|---|---|---|
| Data leakage por paciente | **Verdadera y crítica** | Implementar inmediatamente. |
| Threshold clínico | **Necesidad verdadera, diagnóstico del estado parcialmente falso** | Mantener `target_recall`, endurecer su obligatoriedad; no reemplazar automáticamente por Youden. |
| Flatten + Dense(4096) | **Falsa para esta versión** | No aplicar; ya se usa GAP/Dropout. |
| Ensemble sin calibración previa | **Verdadera como brecha parcial** | Implementar calibradores por miembro y comparar contra calibración final del ensemble. |
| TTA para todas las células | **Verdadera** | Implementar TTA condicional basado en threshold/incertidumbre y validarlo. |
| Falta de adaptación cromática | **Parcialmente verdadera** | Añadir hue/saturation/brightness y/o normalización de tinción con validación de dominio. |

## 6. Limitaciones de esta auditoría

- El ZIP no incluye el dataset físico generado ni su `files_manifest.csv`, por lo que no fue posible contar pacientes repetidos entre splits; la brecha se confirma por la lógica del generador y la ausencia de identificadores de grupo.
- Los releases incluyen metadata, thresholds y checksums, pero no los binarios `.keras` completos ni datos de evaluación suficientes para reproducir métricas.
- El entorno de revisión no tenía TensorFlow instalado, por lo que no se ejecutaron los modelos ni la suite que depende de TensorFlow. La evidencia presentada es estática y trazable al código.
