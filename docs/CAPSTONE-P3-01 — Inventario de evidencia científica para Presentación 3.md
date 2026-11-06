La evidencia disponible permite comparar las seis modalidades registradas, con diferencias de protocolo que deben quedar explícitas. El resumen del frontend no debe utilizarse para elegir un ganador: combina máximos procedentes de distintas ejecuciones y no refleja todas las evaluaciones independientes.

Auditoría realizada el 6 de noviembre de 2026, mediante consultas PostgreSQL con default_transaction_read_only=on, inspección del código y lectura de artefactos. No modifiqué archivos, datos ni configuraciones; no ejecuté entrenamientos ni pruebas que escribieran datos. Git permanece limpio.

El inventario distingue dos conjuntos experimentales principales.
- PostgreSQL contiene 86 ejecuciones: 83 completadas y 3 fallidas.
- La campaña «all 1», ID eb7ae3da-c954-4f2f-8d19-0398824089c5, contiene 60 entrenamientos completos: cinco modalidades × cuatro optimizadores × tres semillas. Conserva además un intento fallido de Fine-tuning.
- Zero-shot tiene una ejecución lógica independiente, sin entrenamiento.
- Las demás campañas incluyen experimentos anteriores y pruebas operativas; conviene mantenerlas separadas de «all 1».
Modalidad	Completadas / fallidas, todas las campañas	Completadas en «all 1»	Runs con evaluación VAL / TEST verificada
Custom CNN	22 / 1	12	17 / 15
VGG16	18 / 0	12	14 / 13
DenseNet121	18 / 0	12	14 / 13
BiomedCLIP Zero-shot	1 / 0	No aplica	1 / 1
BiomedCLIP Linear	12 / 1	12	12 / 12
BiomedCLIP Fine-tuning	12 / 1	12	12 / 12


VAL y TEST cuentan runs distintos. Zero-shot tiene tres evaluaciones verificadas por split, correspondientes a decisiones o contextos de ejecución diferentes.

Las fuentes actuales están distribuidas entre el registro, el ledger experimental y los assessments.
Evidencia	Tablas o campos efectivos	Observación
Modelos y versiones registrales	models, model_versions	Seis modelos y seis versiones registrales; Linear no tiene versión registral
Ejecuciones y campañas	runs, experimental_campaigns, campaign_members, campaign_configurations	Identidad, estado, fechas, duración y diseño
Configuración utilizada	run_configurations; snapshot en runs.execution_parameters.model_configuration_e2.configuration.resolved	Los JSON actuales son plantillas, no evidencia suficiente de una ejecución histórica
Dataset y partición	dataset_versions, dataset_split_assignments, dataset_split_validation_checks, dataset_materializations	Versión congelada, asignaciones y comprobaciones
Épocas, selección y calibración	train_execution_records, train_execution_sessions	Fuente vigente de las campañas
Evaluaciones producidas durante TRAIN	evaluations, run_clinical_metrics, confusion_matrices, classification_reports	213 evaluaciones, todas de VAL
Evaluaciones independientes	assessment_identities, assessment_attempts, assessment_results	140 intentos EVALUATE verificados: 72 VAL y 68 TEST
Calibración del umbral	run_threshold_calibration y ledger kind='calibration'	Se necesitan ambas representaciones
Checkpoints	artifacts y ledger kind='artifact'	Seleccionados y archivos por época
XAI vigente	assessment_*, especialmente assessment_artifacts	35.254 referencias de artefactos


Hay tablas vacías que no representan ausencia de evidencia: training_history, run_checkpoint_policy, run_image_predictions, explainability_results y las tablas especializadas xai_* tienen cero filas. La historia y XAI actuales están en las fuentes indicadas arriba.

Los identificadores siguientes permiten revisar una ejecución concreta por modalidad.

Para hacer la tabla manejable, uso como referencias los cinco runs Adam, semilla 47, de «all 1», junto con Zero-shot. Es un criterio fijo de inspección; no selecciona los mejores modelos ni sustituye el inventario de las 60 ejecuciones.
Clave	Modalidad y Model ID	Run ID	Model Version ID de la identidad evaluada
C	Custom CNN — 976fef0d-6d98-4ed7-a7c5-5983efee5294	52847955-a181-4eb5-a783-656c94a380cb	5a52670f-055f-4f9f-9a8a-e366c7cf9920
V	VGG16 — 998ae52c-0c6b-4673-9c70-70a44caee16a	9bbd5cb0-dedf-4b89-abb3-c93b3e30e800	f218c975-c5c2-4521-89a7-fa50d8f536ee
D	DenseNet121 — 30354220-10ac-4ac8-a5f5-0d16b13ddbcd	a388cef6-8392-4b93-bb5d-250bcf933984	2ccb2171-2076-4710-8a41-f0390f3537a0
Z	Zero-shot — 1cf3e462-c0f7-4f72-92fe-306b8aaaa203	31d27b2d-6e90-4530-a589-ae92c91281df	3fd16a84-b5c7-442b-916b-e0438bb0f3e5
L	Linear — cb03c92c-18a2-4582-b41f-4547821ce793	6aa9d9c2-9ead-4285-b72c-796c9c73add1	bef24c1e-ac63-4c44-9278-1cd4fc306cae
F	Fine-tuning — 8dbf18c6-89b0-4da3-b9b1-7cd326bfe235	db31b6af-c2a2-44f0-9316-8f8c3492c0f1	a673af1a-d35b-4cec-82ba-227111c99a6a


Las versiones de Z y F tienen fila en model_versions. Las versiones indicadas para C, V, D y L son identidades lógicas del checkpoint, conservadas en la sesión y en el assessment. No deben presentarse como versiones registrales existentes. Esta resolución está implementada en [assessment/lineage.py (line 25)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/src/malaria_dl/assessment/lineage.py:25).

C, V, D, L y F pertenecen a «all 1» y registran el dataset d8c0cab5-09dd-597f-9de7-7ca01aee2ec2. En Z, runs.dataset_version_id y campaign_id son nulos; sus evaluaciones sí acreditan ese dataset.

Para recuperar los identificadores de todas las ejecuciones, sin elegir ninguna:
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;

SELECT
    m.name, m.id AS model_id,
    r.id AS run_id, r.campaign_id, r.dataset_version_id, r.status,
    s.verification #>> '{artifact,version_id}' AS logical_model_version_id,
    mv.id AS registry_model_version_id,
    c.configuration_hash, c.optimizer, c.learning_rate,
    c.fine_tune_learning_rate, c.batch_size, c.random_seed,
    c.dropout, c.l2, c.max_epochs, c.fine_tune_epochs,
    c.fine_tune_layers,
    r.completed_epochs, r.best_epoch, r.duration_seconds
FROM runs r
JOIN models m ON m.id = r.model_id
LEFT JOIN run_configurations c ON c.run_id = r.id
LEFT JOIN train_execution_sessions s ON s.run_id = r.id
LEFT JOIN model_versions mv ON mv.training_run_id = r.id
ORDER BY m.name, r.campaign_id, c.optimizer, c.random_seed, r.started_at;

ROLLBACK;
El diseño de «all 1» está suficientemente registrado para describirlo.
Modalidad	Configuración relevante	Presupuesto / épocas realmente ejecutadas
Custom CNN	Sin preentrenamiento; 200×200; dropout 0,4; L2 0,0001	Máximo 100; ejecutadas 13–36
VGG16	ImageNet; 200×200; dropout 0,5; últimas cuatro capas para fine-tuning	Máximo 100 + 20; ejecutadas 27–38
DenseNet121	ImageNet; 200×200; dropout 0,5; últimas cuatro capas para fine-tuning	Máximo 100 + 20; ejecutadas 29–65
Zero-shot	BiomedCLIP original, dos prompts, transform OpenCLIP 224×224	Sin entrenamiento ni épocas
Linear	Encoder congelado; cabeza lineal 512→1; 224×224	Máximo 100; ejecutadas 14–78
Fine-tuning	Cabeza y últimos cuatro bloques ViT; 224×224	Máximo 10 + 30; ejecutadas 25–40


Las modalidades entrenables comparten batch 32 y semillas 11, 29 y 47. Se probaron Adadelta, Adam, AdamW y SGD:
- CNN: Adam/AdamW 1e-4, SGD 1e-3, Adadelta 1; LR de fine-tuning correspondiente 1e-5, 1e-4 y 1.
- BiomedCLIP: LR de cabeza 1e-3; LR de encoder en Fine-tuning 1e-5.
- AdamW registra weight_decay=0.004.
- El monitor explícito es val_f2_parasitized, modo máximo, con early stopping de paciencia 12.
“B3” no aparece como alias persistido en las fuentes revisadas. La implementación acredita biomedclip_fine_tuning con cuatro bloques finales. Esto no demuestra una inconsistencia: B3 podría ser una denominación académica de la estrategia, cuya equivalencia falta documentar.

En las referencias anteriores se recuperan estos checkpoints y tiempos:
Referencia	Épocas ejecutadas	Checkpoint seleccionado	Duración del run TRAIN	Duración del intento TEST
C	36	Época 24, base	1.643,31 s	15,81 s
V	35	Época 23, fine-tuning	2.820,52 s	26,37 s
D	53	Época 21, base	3.107,86 s	35,63 s
Z	No aplica	Checkpoint original	Registro lógico: 0 s	308,22 s, evaluación clínica
L	15	Época 3, base	139,98 s	32,48 s
F	32	Época 20, fine-tuning	5.315,80 s	32,51 s


El checkpoint seleccionado puede pertenecer a la fase base aunque se haya ejecutado fine-tuning, como ocurre en D. Los tiempos son duraciones observadas de run o intento; no acreditan costo monetario ni tiempo puro de cómputo.

La comparabilidad de población está verificada; los puntos de operación difieren.

El dataset de clasificación es Malaria Patient Split v1, congelado:
Split	Total	Uninfected	Parasitized	Pacientes
TRAIN	22.180	11.043	11.137	161
VAL	2.693	1.368	1.325	20
TEST	2.685	1.368	1.317	20


Las doce comprobaciones registradas están en PASS, incluidos solapamientos de pacientes y duplicados entre splits.

Además del mismo Dataset Version ID, comprobé igualdad del manifiesto de muestras —identidades, etiquetas y hashes— por split entre los 60 runs de «all 1» y Zero-shot. Las evaluaciones independientes comparten protocol.version=exec1 y metrics_definition=binary_counts_rates_v1.

Deben conservarse estas diferencias:
- Umbral, origen del umbral y dominio del score.
- TRAIN·VAL, calibración·VAL, EVALUATE·VAL y EVALUATE·TEST.
- Preprocesamiento y resolución propios de cada arquitectura.
- Semilla, entorno y checkpoint efectivo.
- PR-AUC final calculada como average precision, frente a la aproximación de tf.keras.metrics.AUC(curve="PR") que puede aparecer en curvas Keras.
- Métricas indefinidas: assessments utilizan NULL para denominadores nulos; otras funciones históricas aplican convenciones diferentes.
El ajuste de umbral no acredita calibración probabilística mediante Brier, ECE, Platt o isotonic.

Los resultados siguientes ya existen y pueden exportarse.

Son ejemplos trazables de las referencias C/V/D/L/F y de Zero-shot con umbral clínico. Porcentajes redondeados; todos corresponden a TEST, N=2.685.
Referencia	Recall	Specificity	Precision	Accuracy	F1	F2
C	96,89 %	83,85 %	85,24 %	90,24 %	90,69 %	94,31 %
V	97,42 %	88,89 %	89,41 %	93,07 %	93,24 %	95,70 %
D	96,89 %	65,50 %	73,00 %	80,89 %	83,26 %	90,94 %
Z clínico	96,58 %	68,86 %	74,91 %	82,46 %	84,38 %	91,30 %
L	96,43 %	78,22 %	80,99 %	87,15 %	88,04 %	92,89 %
F	96,96 %	92,25 %	92,34 %	94,56 %	94,59 %	96,00 %


Referencia	Threshold	TP	TN	FP	FN	ROC-AUC	PR-AUC/AP
C	0,053485	1.276	1.147	221	41	0,984206	0,986424
V	0,101739	1.283	1.216	152	34	0,990039	0,991275
D	0,138634	1.276	896	472	41	0,953498	0,956143
Z clínico	0,015105	1.272	942	426	45	0,954955	0,953706
L	0,114451	1.270	1.070	298	47	0,971209	0,973674
F	0,010405	1.277	1.262	106	40	0,990145	0,991490


Los Attempt IDs de estas filas son, respectivamente:
C  59f8385d-2177-4998-a477-ea165fce9497
V  20e518b7-b38d-4579-a763-7208a7f63d38
D  4a2a8fca-f281-469d-83d8-95848bec7bda
Z  b9dcf1fa-2293-47d7-9cd2-13d3775f8410
L  e61a5f30-bcd5-43b7-88ff-4187d497c94c
F  7956a4c2-f65a-4e45-848a-499376b3e61f
La sensibilidad al umbral queda especialmente clara en Zero-shot:
Decisión existente	Threshold	Recall TEST	Specificity TEST	FN / FP
Auto, dos prompts	0,5	11,92 %	99,93 %	1.160 / 1
Clínico, ajustado en VAL	0,015105	96,58 %	68,86 %	45 / 426


La evaluación auto corresponde al intento 9a47c125-7081-4e8a-9bd0-e12718c30708. Ambos resultados deben conservarse.

Las curvas, los artefactos y XAI tienen disponibilidad desigual.

En «all 1» hay 1.933 registros reales de época, distribuidos entre sus 60 entrenamientos. Zero-shot no tiene registros de época.

Para F, el checkpoint de época 20 registra accuracy TRAIN de 99,68 % y VAL de 96,25 %, con loss 0,01039 frente a 0,17043. Es evidencia compatible con sobreajuste, que debe interpretarse junto con la trayectoria. Su recall ajustado en VAL es 98,04 % y en TEST 96,96 %: alcanzar el objetivo en VAL no garantiza alcanzarlo en TEST.
Modalidad	XAI verificado existente
Custom CNN	Grad-CAM, LIME y SHAP
VGG16	Grad-CAM, LIME y SHAP
DenseNet121	Grad-CAM, LIME y SHAP
Zero-shot	LIME y SHAP
Linear	Sin resultados persistidos
Fine-tuning	Sin resultados persistidos


Esta disponibilidad agrupa diferentes runs; no acredita XAI para cualquier checkpoint elegido. Hay evidencia parcial de un intento LIME fallido que debe conservarse como parcial, sin contabilizarlo como completado. Las tablas de evaluación cuantitativa e interpretación especializada XAI están vacías.

Ubicaciones verificadas:
malaria_dl_local_project/outputs/campaign_runs/<run_id>/epoch_<n>.keras
malaria_dl_local_project/outputs/campaign_runs/<run_id>/epoch_<n>.pt
malaria_dl_local_project/artifacts/assessments/<attempt_id>/<artifact_uuid>.npy
malaria_dl_local_project/artifacts/assessments/<attempt_id>/<artifact_uuid>.png
El checkpoint original Zero-shot está en:
/Users/julio/.cache/capstone-biomedclip-01b/original/biomedclip/
9f341de24bfb00180f1b847274256e9b65a3a32e/open_clip_pytorch_model.bin
Se comprobó existencia y tamaño de los 87 artefactos registrados y de 2.425 checkpoints por época. Los hashes coinciden para seis checkpoints registrales, cuatro dependencias BiomedCLIP y 22 archivos XAI de muestra. No se verificó el hash de todos los archivos XAI ni de todos los checkpoints por época.

La trazabilidad del frontend conduce a estos puntos de entrada.
Función	Página	Endpoint y fuente
Resumen	/modelo-ia/resumen	/dashboard/summary, /dashboard/clinical → vistas resumen
Ejecuciones	/modelo-ia/ejecuciones	/runs/training-summaries → runs, configuraciones y resúmenes
Detalle	/modelo-ia/ejecuciones/{run_id}	/runs/{id}, /clinical-summary, /artifacts
Entrenamiento	/modelo-ia/explorador/entrenamiento?run=…	/models/comparison/report, módulo curves; /runs/{id}/training-trajectories
Evaluación independiente	/modelo-ia/evaluaciones/e6/{attempt_id}	/assessments/{attempt_id}, /results, /artifacts
Comparación científica	/modelo-ia/analisis	/models/comparison/preflight, /models/comparison/report
Explicabilidad	/modelo-ia/explicabilidad y comparación	Galería histórica y assessments EXPLAIN
Recuperación de archivos	Visores de artefactos	/artifacts/file, autenticado


La implementación puede seguirse desde [dashboard.py (line 13)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/backend_api/app/routes/dashboard.py:13), [scientific_results.py (line 212)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/backend_api/app/repositories/scientific_results.py:212) y [assessments.py (line 28)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/backend_api/app/routes/assessments.py:28).

Dos límites afectan directamente la presentación:
- El dashboard no consulta las evaluaciones E6 y sus máximos mezclan métricas de diferentes splits.
- El selector científico puede resolver TEST → VAL → TRAIN cuando falta la evaluación solicitada. La exportación debe guardar la evaluación realmente utilizada, sin fallback silencioso.
No invoqué /runs/{id}/architecture: para BiomedCLIP puede generar una caché en disco.

Las ausencias e inconsistencias de representación que deben documentarse son concretas.
1. Versiones lógicas frente a registrales: conservar ambas identidades y su origen.
2. Política nominal frente a selección efectiva: aparece auc_with_min_recall, pero la selección efectiva puede ser máximo F2; el ledger conserva la advertencia.
3. Calibración proyectada parcialmente: target_recall_satisfied es NULL en las 66 filas de la tabla. No significa FALSE: sus evaluaciones seleccionadas alcanzan el objetivo en VAL. El detalle, incluido candidate_count, permanece en payload.result.
4. Sin evidencia persistida de calibración probabilística, picos de memoria, energía o costo monetario.
5. Sin XAI persistido para Linear/Fine-tuning, ni evaluación cuantitativa XAI en las tablas previstas.
6. Alias académico B3 sin equivalencia documentada.
7. TEST disponible para muchas configuraciones: no debe convertirse retrospectivamente en criterio de selección de hiperparámetros.
La exportación propuesta puede reutilizar las lecturas existentes, sin copiar datasets ni checkpoints.

No encontré un exportador que genere los siete archivos solicitados. Propongo una operación de descarga que reutilice [read_only_transaction (line 68)](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/backend_api/app/db.py:68) con repeatable_read=True, selecciones explícitas y salida CSV/JSON en streaming.
Archivo	Contenido y procedencia
model_comparison.csv	Una fila por evaluación seleccionada; métricas, N, split, propósito, umbral, definición, Run y Attempt/Evaluation ID
experiment_configurations.csv	Configuración efectiva por Run, semillas, optimizador, LR, regularización, fases y hash
training_history.csv	Registros kind='epoch', con época global y de fase; ninguna fila ficticia para Zero-shot
confusion_matrices.csv	TP/TN/FP/FN de la misma evaluación; orientación [[TN,FP],[FN,TP]]
threshold_analysis.csv	Umbral default/seleccionado, política, objetivo, métricas VAL, advertencias y número de candidatos
compute_costs.csv	Duración TRAIN y por intento, entorno y hardware; memoria, dinero y energía ausentes como NULL
evidence_manifest.json	Identificadores, fuentes, fechas, protocolo, población, configuración y referencias de artefactos


El manifiesto debe separar:
training_run_id
campaign_id
model_id
logical_model_version_id
registry_model_version_id
assessment_identity_id
attempt_id / evaluation_id
identity_checkpoint_id
registered_checkpoint_artifact_id
dataset_version_id + fingerprints
split + purpose + metric_definition
threshold + threshold_source + score_domain
artifact path/URI + bytes + checksum registrado
estado y fecha de verificación física
fecha del snapshot y procedencia de cada campo
La historia debe evitar duplicar los registros epoch y sus eventos espejo e10_event. Tampoco corresponde fabricar un barrido de thresholds: pueden exportarse los puntos persistidos; cualquier curva derivada posteriormente debe identificarse como cálculo nuevo sobre scores existentes.

Para las diapositivas, recomiendo esta secuencia científica.
1. Hipótesis y diseño: arquitecturas, preentrenamiento, fases, cuatro optimizadores, tres semillas y split por paciente. Identificar estas hipótesis como formulación académica, separada de los resultados observados.
2. Ejecución: matriz de completitud, épocas reales, checkpoint y duración. Mostrar Zero-shot como inferencia sin entrenamiento.
3. Comparación: presentar las 60 ejecuciones agrupadas por optimizador y semilla; acompañar las métricas con FN/FP, umbral y evaluación explícita.
4. Sensibilidad: usar los dos puntos existentes de Zero-shot para explicar el intercambio recall–specificity. Diferenciar el objetivo alcanzado en VAL del desempeño observado en TEST.
5. Interpretación y decisión: curvas y brechas TRAIN/VAL/TEST; XAI sobre las mismas muestras y checkpoints. No declarar superioridad estadística a partir de máximos descriptivos. Para intervalos o análisis pareados posteriores, considerar la agrupación por los 20 pacientes de TEST, no asumir 2.685 observaciones independientes.
La evidencia está lista para una comparación descriptiva trazable y para diseñar la exportación. La elección científica de un modelo requiere un criterio explícito de decisión; esta auditoría no selecciona ninguno.