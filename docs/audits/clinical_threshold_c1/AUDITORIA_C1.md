# C1 — Auditoría de calibración clínica existente

Estado documental: `HISTORICAL_AUDIT`. Fecha: 2026-10-04. C2 no implementado ni autorizado por esta entrega.

**Metodología: auditoría estática, sin ejecución de código, pruebas ni consultas PostgreSQL.**

## 1. Resumen ejecutivo

Sí existe un mecanismo reutilizable: `find_threshold_for_target_recall`, en `malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py:154–272`. Está **IMPLEMENTADO y CONECTADO** al ejecutor de campañas después de cargar el checkpoint seleccionado. No usa Youden ni calibra durante cada época. No puede calificarse sin reservas como una calibración clínicamente adecuada: admite degradación de restricciones, entradas insuficientemente validadas y hay discrepancias entre políticas y proyecciones.

B1 acredita 12 RUNS, 396 épocas y evaluaciones finales VAL a 0.5, sin calibración habilitada. Los 12 incumplen tanto `>=0.98` como `>0.98` (máximo histórico 0.948679). Esto no demuestra que un umbral alternativo útil sea imposible. No se calculó ninguno en C1.

La entrega completa está en [DOCUMENTO_C1_THRESHOLDING_CLINICO.md](DOCUMENTO_C1_THRESHOLDING_CLINICO.md), con 15 capítulos y cinco anexos. [FUNCIONES_C1.md](FUNCIONES_C1.md) contiene inventario y pruebas; [SQL_C1.md](SQL_C1.md), esquema y consultas no ejecutadas; [PLAN_C2.md](PLAN_C2.md), intervención mínima.

## 2. Estado real de la calibración

| Evidencia | Conclusión |
| --- | --- |
| **IMPLEMENTADO** | Búsqueda exhaustiva de candidatos finitos en [0,1], filtro recall y especificidad, desempate determinista. |
| **CONECTADO** | `execution/train.py:273–308` llama al calibrador si `resolved.execution.calibrate_threshold`. |
| **CONFIGURADO** | `campaigns/contracts.py:318–343` traduce `threshold_grid` a `true`; `science/protocol.py:213–216` fija `none` en el plan E7. |
| **PERSISTIDO** | Significa operación de escritura identificada en código, no consulta nueva: registros, eventos y proyección v2. |
| **EJECUCIÓN HISTÓRICA ACREDITADA** | Los documentos B1 y sus CSV acreditan evaluación fija y calibración desactivada; se hereda su evidencia, no se revalida la BD. |
| **NO VERIFICADO** | Funcionamiento actual de la rama habilitada contra PostgreSQL; disponibilidad actual de scores y archivos. |
| **NO IMPLEMENTADO** | En el calibrador TRAIN no hay rechazo obligatorio por ausencia de ambas clases ni factibilidad clínica conjunta como condición para aplicar el resultado. |

`calibrate_clinical_threshold()` no fue localizado en el código fuente inspeccionado. Los adaptadores `src/threshold_calibration.py`, `src/metrics.py` y `src/checkpoint_policy.py` reexportan módulos canónicos; no son otros algoritmos.

## 3. Flujo TRAIN → VALIDATION → checkpoint → calibración

`run_train_all_models.main` → `execution.campaign.main` → worker → `execution.train.train`. El RUN recibe un snapshot persistido; carga únicamente TRAIN/VAL. Por época, `model.fit` calcula métricas Keras y `ClinicalValidationMetricsCallback` recoge scores VAL a 0.5, añade F2/recall/especificidad y el score normalizado de EarlyStopping. `PersistEpoch` selecciona sobre la historia acumulada, guarda cada checkpoint y sus predicciones.

EarlyStopping mira `val_early_stopping_score`, derivado del monitor lógico; en B1 éste es F2. Paciencia histórica 12, min_delta 1e-5 y restauración de pesos activada. ReduceLROnPlateau sigue `val_loss`. El checkpoint final puede proceder de base o fine-tuning: el historial es global; se carga explícitamente su archivo después de ambas fases. La restauración local de pesos de EarlyStopping no sustituye esa selección.

**Diferencia decisiva:** el monitor explícito `val_f2_parasitized` activa `select_best_epoch_by_monitor`, aunque la configuración conserve el nombre `auc_with_min_recall`. En ese camino no se exige recall mínimo para elegir. `policy_satisfied=true` no significa objetivo clínico satisfecho (`checkpoint_policy.py:422–454`).

La calibración ocurre una vez sobre VAL del checkpoint recargado. Desactivada, genera `{"enabled":false,"threshold":0.5}`; ese registro `kind=calibration` no acredita calibración ejecutada. El evento canónico de calibración se omite, y la evaluación final usa fuente `default` (`execution/train.py:124–125,276–311`).

TEST pertenece a la evaluación separada E6: `assessment.service.prepare:53–79` resuelve una decisión explícita antes de evaluar. `assessment.contracts.threshold:28–64` admite número autorizado por protocolo o `clinical` con evidencia VAL del checkpoint exacto (`assessment/lineage.py:55–64`). No busca umbrales sobre TEST. La identidad exige TEST sólo con purpose final (`contracts.py:81–96`); la regla predicha sigue >= (`:140–154`). Ese resolver comprueba procedencia, pero tampoco exige flags de factibilidad conjunta del resultado clinical. Su ejecución histórica en TEST es NO VERIFICADO y no se realizó en C1.

## 4. Algoritmo matemático implementado

Clase positiva `parasitized=1`, regla `score >= threshold`. Sensibilidad `TP/(TP+FN)`; especificidad `TN/(TN+FP)`; F2 `5TP/(5TP+4FN+FP)`.

Los candidatos son scores únicos finitos recortados a [0,1], más 0, 0.5 y 1. Se exige **recall >= target_recall**, luego especificidad >= mínimo si se proporcionó. Entre factibles se maximiza lexicográficamente `(specificity, precision, F2, balanced_accuracy, threshold)`. No es maximización de Youden J, ni F2 como primer criterio, ni simplemente mayor umbral factible.

Si sólo falla especificidad, se relaja ese filtro y devuelve advertencia con `min_specificity_satisfied=false`. Si falla recall, maximiza `(recall, specificity, precision, F2, balanced_accuracy, threshold)` y marca incumplimiento. **Ningún fallback se considera cumplimiento clínico conjunto en esta auditoría.** El colapso se informa pero no excluye candidatos de calibración. `beta` se registra, pero el cálculo siempre es F2.

## 5. Parámetros y valores efectivos

| Parámetro | B1 / procedencia | Efecto real |
| --- | --- | --- |
| threshold | 0.5; evaluaciones B1 y selección | Fijo en selección; final sólo cambia si se calibra. |
| calibrate_threshold | false; snapshot RUN | No se invocó calibración TRAIN. |
| target_recall / min_recall | 0.98 / 0.98; snapshot | Calibrador / política y objetivo de cierre; no intercambiables. |
| min_specificity | 0; protocolo/snapshot B1 | Restricción trivial; modelos JSON individuales tienen null. |
| beta | 2; snapshot | F2; resolución rechaza otro beta. |
| min_class_fraction | 0.05; snapshot | Colapso por época; calibrador no recibe este parámetro. |
| reject_prediction_collapse | true; snapshot | Filtro checkpoint, no filtro de umbral. |
| checkpoint_monitor | val_f2_parasitized; snapshot y B1 | Prevalece monitor explícito sobre selección AUC condicionada. |

Precedencia individual: JSON versionado → perfil batch si aplica → JSON seleccionado → CLI explícita. En campaña congelada prevalece protocolo persistido: se rechazan conflictos de variante; el hijo recibe snapshot con semilla. El CLI público de campaña no admite overrides científicos. No se encontró conexión de variables `.env` a estos parámetros; se buscaron sólo nombres pertinentes, sin exponer credenciales. No existe parámetro arbitrario de threshold de selección: contrato y ejecución exigen 0.5.

## 6. Integración con campañas

El contrato interno admite `calibration.algorithm=threshold_grid` y lo conecta al ejecutor. La configuración pública permite editar un subconjunto y muestra la calibración como fija (`campaigns/configuration.py:204–224,433–451`), derivada del plan E7 con algoritmo `none`. Los JSON de modelos tienen `execution.calibrate_threshold=false`, pero `batch.calibrate_threshold=true`; no debe atribuirse ese default batch a B1, pues su protocolo lo sobreescribe.

El selector científico E7 `science/statistics.py:125–170` ya propone umbrales desde scores guardados con sensibilidad estricta `>0.98`, especificidad, F2 y umbral. Lo consumen `science/comparison.py:173` y `science/ensemble.py:250`; no es el calibrador TRAIN. C2 debe aclarar compatibilidad y versiones sin crear un tercer sistema.

## 7. Persistencia PostgreSQL

`ExecutionRepository._create_run` guarda `runs.execution_parameters.model_configuration_e2.configuration`; `project_configuration` crea `run_configurations`, cuyo JSON efectivo se llama **extension_configuration**, no `configuration`. `campaign_configurations.configuration` sí existe. La consulta inicial del encargo necesita esa corrección.

Los registros legacy viven en `train_execution_records`; el worker también emite eventos aceptados por `ResultService`. La proyección v2 crea `calibration_default`, `calibration_selected`, su pareja `run_threshold_calibration` y la evaluación `training_validation_final`. `v2_binary_metric_guard` deriva métricas desde conteos y copia threshold/fuente desde `evaluations`.

**Brecha confirmada por código:** `project_calibration` inserta umbral y target, pero omite `min_specificity`, flags de cumplimiento, warning, candidate_count y métricas resumen en la fila de calibración. El resultado completo permanece en el evento/registro; la vista `vw_threshold_calibration_summary` lee columnas omitidas y puede exponer null. Tampoco la proyección final llena `prediction_collapse` (queda `{}`); no equivale a false.

## 8. Riesgos y diferencias detectadas

| ID | Severidad | Evidencia y alcance |
| --- | --- | --- |
| H01 | Alta | **IMPLEMENTADO:** relajación de especificidad y aplicación de fallback sin gate conjunto; no se demuestra un daño ni ocurrencia B1. |
| H02 | Alta | **IMPLEMENTADO/CONFIGURADO:** TRAIN `>=` frente a E7 `>` y desempates diferentes. |
| H03 | Alta | **IMPLEMENTADO:** cierre `clinical_objective_met` usa métricas de selección a 0.5 y `min_recall`, no evaluación recalibrada/`target_recall`. |
| H04 | Alta | **PERSISTIDO:** proyección de calibración incompleta para vista/API; evento preserva detalle. |
| H05 | Alta | **IMPLEMENTADO:** calibrador no exige ambas clases, scores finitos y rango válido; sanitizar sólo candidatos no valida datos evaluados. |
| H06 | Media | **IMPLEMENTADO:** monitor explícito F2 evita filtro min_recall; nombre de política puede inducir error de interpretación. |
| H07 | Media | **IMPLEMENTADO:** float64 candidatos frente a float32 métricas; riesgo potencial de empates/redondeo, sin caso B1 demostrado. |
| H08 | Media | **IMPLEMENTADO:** evaluación Python usa cero ante denominador cero; SQL v2 usa null. B1 tiene ambas clases. |
| H09 | Media | **CONFIGURADO:** calibración no editable en flujo público, aunque ejecutor conectado. |
| H10 | Media | **NO VERIFICADO:** generalización clínica; VAL reutilizada, una semilla y ninguna evaluación externa nueva. |

## 9. Evidencia verificable

Código principal: `evaluation/threshold_calibration.py:63–272`, `evaluation/clinical_metrics.py:234–362,430–464`, `training/checkpoint_policy.py:319–454,498–592`, `execution/train.py:36–328`, `models/configuration.py:37–59,197–234` bajo `malaria_dl_local_project/src/malaria_dl/`.

Persistencia: `persistence/v2_projection.py:29–54,116–198`, `execution/repository.py:179–258,355–395`; `alembic_v2/baseline/03_tables.sql:84,134–150,180–184`; `04_functions.sql:1129–1165`. API: `backend_api/app/routes/runs.py:539–613,703–757`.

B1: `results/benchmarks/cpu_historical/HALLAZGOS_B1.md:9–11,25–35,39–52,109`; `SQL_B1.md:332–350,367–390`; `report.md`; `runs.csv` y `epochs.csv` leídos como archivos, sin recalcularlos. Snapshot histórico 2026-10-04T12:56:54.183938+00:00. Commit runtime B1 consignado allí: `8411be7e71944370d017c96cc277e2b844c3de6e`. HEAD observado durante C1: `abd9aae0378c0aca0e178b5e2d3d2138411d1dcb`; no se equipara con runtime histórico.

## 10. Conclusión técnica

Capstone dispone de un calibrador reutilizable y conectado, pero su activación clínica exige resolver factibilidad, semántica del objetivo, validación de entradas y trazabilidad de resultados. La habilitación pública debe realizarse en una nueva configuración/protocolo, conservando B1. La calibración retrospectiva es viable con los scores históricos acreditados y su linaje, sin TRAIN, modelos, inferencia ni TEST; su disponibilidad actual queda pendiente de C2. No se escribió fuera de los cinco documentos permitidos, incluido el índice global que el skill documental normalmente solicita actualizar.
