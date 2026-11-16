# CAPSTONE-P3-04 — Análisis funcional, matemático y científico por opción

Fecha: 16 de noviembre de 2026, America/Santiago. Datasource: `malaria`.

**HECHO VERIFICADO.** El identificador solicitado `00b8d407-c672-4b68-9814-53c092d034ba` no es una fila de `runs`: es `assessment_attempts.id`, tipo `evaluate`, split **TEST**, estado `verified`. Su identidad es `a981125c-a9b6-4bec-9fb7-2fa52b907147` y su TRAIN es `87b3eff7-e09a-41c8-945d-bf31b3541adb`. La auditoría conserva el UUID pedido como caso principal y utiliza su TRAIN únicamente para reconstruir el entrenamiento y sus descendientes. Evidencia: [consulta de identidad](sql/principal_identity.sql), [captura](evidence/principal_identity.json), [identidad completa](evidence/principal_full_identity.json).

Convenciones: **HECHO VERIFICADO** = código/registro/archivo observado; **CÁLCULO REPRODUCIDO** = cálculo independiente sobre evidencia existente; **INTERPRETACIÓN CIENTÍFICA** = lectura con límites; **HIPÓTESIS** = explicación no demostrada; **PENDIENTE** = no comprobado. La existencia de código, de un registro `verified` y de un archivo con checksum coincidente son tres evidencias diferentes.

## A. Aprendizaje — cómo evolucionó el entrenamiento

### Pregunta, procedencia y contrato

La unidad de selección es TRAIN; las curvas no cambian al elegir EVALUATE TEST, porque describen la optimización sobre TRAIN y VALIDATION. `CurvesModule` envía solo training_run_id al módulo curves. `comparison_epochs` consulta `train_execution_records` con kind=epoch, orden de evento y record_key; no `training_history`. El servicio convierte solo números finitos mediante `number` (rechaza bool), valida época entera positiva y única globalmente. Si hay eje duplicado/ambiguo devuelve epochs=[] e issues; no une fases con el mismo número silenciosamente. Conserva phase y count ejecutado.

Configuración: `run_configurations` si existe; alternativa explícita a runs.execution_parameters.model_configuration_e2.configuration.resolved. Monitor/checkpoint provienen del último evento selection y de artifacts referenciado en contexto e10. `checkpoint_evidence` comprueba propiedad TRAIN, época entera, metadata epoch/fase coherentes; **file_availability=not_checked**. La figura no verifica físicamente el binario; esa comprobación se hizo por separado en auditoría.

Código: [backend_api/app/repositories/scientific_results.py:188](../../../backend_api/app/repositories/scientific_results.py#L188); [backend_api/app/services/scientific_report.py:273](../../../backend_api/app/services/scientific_report.py#L273); [frontend/src/components/reports/ScientificReport.tsx:126](../../../frontend/src/components/reports/ScientificReport.tsx#L126); [frontend/src/utils/analysisSummaries.ts:6](../../../frontend/src/utils/analysisSummaries.ts#L6).

### Función de pérdida, indicadores y selección

Para una célula con etiqueta y∈{0,1}, probabilidad p=σ(z):

`BCE(y,p) = −[y log(p)+(1−y)log(1−p)]`; pérdida del batch = promedio, más regularización cuando el grafo la añade. `compile_binary_model` invoca Keras BinaryCrossentropy(from_logits=False,label_smoothing=0,axis=-1,reduction=sum_over_batch_size). Modelos Torch supervisados utilizan BCE con logits en entrenamiento y sigmoid al predecir. BCE penaliza la confianza de errores y es diferenciable; F2 es métrica sobre decisiones a un umbral. F2 no sustituye a la pérdida ni se optimiza directamente por backpropagation en este flujo.

`compile_binary_model` registra accuracy, Precision, Recall, ParasitizedRecall, Specificity, BalancedAccuracy, AUC ROC y PR de Keras. Las clases propias acumulan TP/FN o TN/FP y usan divide_no_nan; threshold0.5, comparación≥. Las métricas genéricas de Keras se delegan a la biblioteca; no atribuir su discretización AUC al código de sklearn. Keras AUC es aproximación a partir de umbrales; `val_roc_auc_parasitized` de la pasada clínica usa sklearn y puede diferir legítimamente de `val_auc`. Keras PR-AUC tampoco equivale automáticamente a Average Precision. Ejemplo principal época1: val_auc0.9812548161 frente a val_roc_auc_parasitized0.9816087388; val_pr_auc0.979665339 frente a AP0.981555775. Son definiciones distintas, no evidencia suficiente de error de cálculo.

`compute_clinical_metrics` es una pasada de scores clínicos posterior/por callback: convierte score a float32 y calcula la familia clínica con sklearn; `collect_predictions`/checkpoint callbacks incorporan valores val_* y selección. No todas las métricas finales se calculan como promedio de métricas de minibatches. En Torch hay TRAIN loss/accuracy y clínica VAL; no se deben inventar TRAIN F2/recall de un historial que no los guardó. La UI ofrece loss/accuracy y opciones AUC, PR-AUC, recall, specificity, F2 solo si hay evidencia y definición de métricas. No expone necesariamente todas las claves presentes: precision, balanced_accuracy o recall_parasitized pueden existir en payload sin selector dedicado.

Código: [malaria_dl_local_project/src/malaria_dl/models/architectures.py:153](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L153); [malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py:234](../../../malaria_dl_local_project/src/malaria_dl/evaluation/clinical_metrics.py#L234); [malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py:542](../../../malaria_dl_local_project/src/malaria_dl/training/checkpoint_policy.py#L542). Funciones exactas/consumidores/tests en catálogo 03.

La política se debe leer con `selection_method`, `selected_metric`, `selected_metric_mode`, warnings y policy_satisfied. En principal, nombre auc_with_min_recall y monitor explícito val_f2_parasitized coexisten: el warning documenta que ganó el monitor explícito. No afirmar selección por ROC-AUC por el nombre de la política. EarlyStopping monitor F2/max, patience12,min_delta0.0001,restore_best_weights; ReduceLROnPlateau monitor val_loss factor0.5 patience4 min_lr1e-6; cada fase puede tener LR propio y restauración de checkpoint. El archivo evaluado se fija por sesión, no última época.

### Regularización y fases

Custom CNN añade L2 en kernels de convolución/cabeza, BatchNorm, dropout; transfer VGG16 congela backbone y ajusta cabeza antes de descongelar las últimas capas; DenseNet incorpora normalización ImageNet y backbone llamado training=False para el estado BN conforme a la implementación. BiomedCLIP linear congela encoder; fine-tuning usa los bloques configurados y grupos LR diferenciados. La configuración efectiva de cada RUN prevalece sobre defaults de factories.

LR, batch, dropout, L2, optimizador, weight_decay, augmentación y seed son causas potenciales que deben controlarse al comparar; no se infieren de la forma de la curva. El tiempo/recursos depende también del hardware, batch y número de épocas. No hay justificación para atribuir causalmente un cambio a SGD frente a Adam sin cohortes alineadas.

### Visualizaciones y lectura válida

Curva: x=época global, y=valor original, TRAIN continua y VAL discontinua, color por índice RUN; huecos explícitos, connectNulls=false; toggles por métrica/serie y referencia vertical del checkpoint válido. Primera transición fine_tuning encontrada entre RUN se marca como referencia común: si las fronteras difieren, no asumir que todas las arquitecturas cambian en la misma época. Tabla muestra base/ajuste/total ejecutado frente a configurado y checkpoint/política. KPI loss y gap corresponden a la época seleccionada, **gap=val_loss−loss**, no a última época ni a TEST.

**INTERPRETACIÓN CIENTÍFICA:** caída TRAIN con ascenso sostenido VAL tras un mínimo es señal compatible con sobreajuste; comparar ventanas temporales y score/loss, no solo dos valores. Una brecha negativa puede deberse a augmentación/dropout/regularizadores activos en entrenamiento. Plateau y early stopping no prueban ausencia de sobreajuste. Curvas no prueban estabilidad entre semillas; se necesitan distribuciones de varias ejecuciones. Colapso de decisiones≥95 % a una clase es distinto de convergencia de pérdida. Balance real de población afecta esa heurística.

**Contraste P3-03:** permanecen 2.425 eventos epoch y training_history=0. El informe histórico localiza un problema en RunDetail; el reporte actual ModelComparison sí lee eventos por el contrato específico y muestra28 épocas principales. No trasladar una ausencia de detalle a todas las vistas. [Auditoría anterior](../../../CAPSTONE_P3_03_AUDITORIA_ANALISIS_AUTOMATICO_Y_SOBREAJUSTE.md), [captura actual](evidence/report_curves.json).

Reproducir: SQL epochs → filtrar TRAIN → ordenar → comparar report_curves JSON → CSV principal_epochs y figura. No ejecutar TRAIN.

## B. Desempeño clínico — equilibrio de errores

### Catálogo matemático exacto

Clase positiva1=parasitized; negativa0=uninfected. Para score continuo s, `ŷ=1[s≥t]`. Matriz filas clase real, columnas predicha: `[[TN,FP],[FN,TP]]`. N=TN+FP+FN+TP. Un score es entrada continua; predicción es resultado del threshold. El threshold no altera ranking/AUC si no modifica scores.

| Indicador | Fórmula | Fuente efectiva / límite |
|---|---|---|
| Sensibilidad/recall | TP/(TP+FN) | Positiva parasitized; no sensibilidad por paciente |
| Especificidad | TN/(TN+FP) | Negativa uninfected |
| Precision/PPV | TP/(TP+FP) | La UI expone precision; PPV es el mismo cociente |
| Accuracy | (TP+TN)/N | Depende del balance de clases |
| F1 | 2TP/(2TP+FP+FN) | No guardado en todas las verificaciones VAL históricas |
| F2 | 5TP/(5TP+4FN+FP) | β=2; FN pesa4 veces respecto a FP en denominador |
| Balanced Accuracy | (recall+specificity)/2 | Igual peso a cada clase, no a cada célula |
| FNR | FN/(TP+FN) | Disponible en cálculo clínico; no fila dedicada en tabla principal |
| FPR | FP/(TN+FP)=1−specificity | Eje x del punto operativo |
| NPV | TN/(TN+FN) | Derivado de auditoría; no indicador dedicado de esta vista |
| ROC-AUC | P(s+>s−)+0.5P(empate) | sklearn roc_auc_score, requiere dos clases |
| PR-AUC/AP | Σ(Rₖ−Rₖ₋₁)Pₖ | sklearn average_precision_score; no integral trapezoidal |

`compute_clinical_metrics`: _safe_divide retorna0 para denominador cero; sklearn precision/f1/fbeta zero_division=0; AUC/AP None con una sola clase o ValueError. `assessment.contracts.metrics` usa None para denominador cero. `verify_rows` conserva hashes VAL históricos y añade F1/BA/AUC/AP **solo en TEST**; un VAL independent puede mostrar medidas ausentes aunque compute_clinical_metrics sí las soporte. `metric_dto` para tabla histórica expone undefined_reason=zero_denominator o razón AUC. `assessment_metrics` usa not_persisted si falta una clave; la UI no debe convertir ausencias a ceros.

Código: [malaria_dl_local_project/src/malaria_dl/assessment/contracts.py:188](../../../malaria_dl_local_project/src/malaria_dl/assessment/contracts.py#L188); [malaria_dl_local_project/src/malaria_dl/assessment/contracts.py:210](../../../malaria_dl_local_project/src/malaria_dl/assessment/contracts.py#L210); [backend_api/app/repositories/scientific_results.py:10](../../../backend_api/app/repositories/scientific_results.py#L10); [backend_api/app/services/scientific_report.py:201](../../../backend_api/app/services/scientific_report.py#L201). AP no interpolada: [documentación primaria sklearn](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html). La versión usada para cálculo independiente queda en computation_environment.json; el metadato de ejecución original no registra todas las versiones sklearn, por lo que no se infiere su versión histórica a partir de la actual.

### Recuperación, no recálculo frontend

Evaluación histórica: evaluation_id debe pertenecer al TRAIN; split y checkpoint opcionales deben concordar. Se exige una sola fila clínica y threshold/run coherentes. Para training_validation_final se comprueba selección de checkpoint. Assessment: attempt+identity deben pertenecer al TRAIN, tipo evaluate,state=verified, metrics presentes; devuelve clinical del objeto verificado y threshold de la identidad. Campos ausentes no se rellenan desde otra evaluación. Un módulo disponible no implica comparable entre modelos.

Máximos conjuntos solo si todos available, un único split e igualdad no nula de dataset_version_id,population_hash,metric_definition,protocol_hash,threshold_used. En independent assessment `population_hash=None`, por lo que no hay highlights aun con scores perfectamente alineados en consenso. Se comprobó principal comparable=false sin errores en metrics. Es un límite conservador del contrato, no ausencia de métricas.

### Threshold y calibración

Default0.5. `find_threshold_for_target_recall` construye candidatos0/1/0.5 y valores únicos finitos recortados[0,1]. Evalúa con compute_clinical_metrics. Filtra recall≥target; opcionalmente specificity≥mínimo. Si el mínimo de specificity no se satisface pero sí recall, conserva candidatos recall con warning; si no hay recall objetivo, fallback por máximo recall, specificity, precision,F2,BA,t. Entre admisibles maximiza specificity,precision,F2,BA,t en ese orden. β se registra pero evaluate_threshold calcula F2 fijo. `validate_calibration_split` rechaza TEST; función pura recibe arrays y no conoce su split, así que el guard corresponde al llamador/identidad.

Persistencia: evento calibration con checkpoint_epoch,samples,result; run_threshold_calibration y evaluaciones calibration_default/calibration_selected/training_validation_final. EVALUATE auto recupera threshold asociado a checkpoint seleccionado, no vuelve a ajustar scores; `calibrator=None`, score_domain=raw. Zero-shot usa0.5 para comparar dos prompts, o modo clinical con evidencia VAL según política específica; sus scores son similitudes relativas, no probabilidades clínicas calibradas.

Código [malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py:154](../../../malaria_dl_local_project/src/malaria_dl/evaluation/threshold_calibration.py#L154); [malaria_dl_local_project/src/malaria_dl/assessment/contracts.py:28](../../../malaria_dl_local_project/src/malaria_dl/assessment/contracts.py#L28); [malaria_dl_local_project/src/malaria_dl/assessment/openclip.py:121](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L121). Auditoría reproduce elección principal en memoria, no escribe run_threshold_calibration.

### Visualizaciones, contexto e incertidumbre

Punto operativo scatter x=1−specificity,y=recall; un punto por RUN/umbral, **no curva ROC ni barrido interactivo**. Y puede comenzar en auto y terminar1; comprobar escala antes de comparar distancias. Barras recall/specificity/F2 en[0,1], coloreadas por métrica; no confundir color con modelo. Matriz con conteos y N, tabla completa con tasas, N y threshold; split visible en encabezados y protocolo dentro de Evidencia. La vista no presenta curva ROC/PR, reliability diagram ni IC del principal.

98 % es objetivo del proyecto; no certificación clínica. PPV/NPV dependen de prevalencia; dataset de crops casi balanceado no representa necesariamente un laboratorio real. La partición por paciente evita mezcla de células de un mismo paciente entre splits si checks lo acreditan; no transforma automáticamente medidas celulares en medidas por paciente. No se acredita desempeño por frotis completo en este módulo.

**Bootstrap implementado en otro subsistema:** `science.statistics.cluster_interval` agrupa filas por patient_id, remuestrea pacientes completos con reemplazo, conserva multiplicidad, calcula métricas o diferencias pareadas y usa cuantiles percentiles. Falta patient_id o clusters mínimos → razón explícita; replicas válidas insuficientes → intervalo None. La campaña declara1000 réplicas/95 %, pero esa declaración no demuestra ejecución ni que los IC aparezcan en ModelComparison. No se encontró campo IC en el DTO clínico de la vista auditada. [malaria_dl_local_project/src/malaria_dl/science/statistics.py:188](../../../malaria_dl_local_project/src/malaria_dl/science/statistics.py#L188).

Reproducir: principal_scores → aplicar threshold congelado → conteos/fórmulas → sklearn AUC/AP → cotejar verification y report_metrics; [CSV](csv/principal_metrics.csv).

## C. Errores y consenso — comparación por la misma célula

### Contrato por muestra

Assessment EVALUATE conserva sample_id,patient_id,label,raw_score,calibrated_score(None),threshold,predicted. Antes de comparar, `prediction_population` exige decisión raw, clase positiva1, comparación>= y calibratorNone; comprueba expected/retrieved unique, faltantes/inesperadas/no gobernadas, etiquetas y duplicados. Verifica sample_id/threshold en payload. Luego `validate_samples` vuelve a aplicar decisión y reconcilia TN/FP/FN/TP y N con evaluación. Scores fuera[0,1], no finitos, bool, label inválida o duplicados no se reparan silenciosamente.

Histórico TRAIN VAL: solo training_validation_final, input_contract de probabilidad parasitized y un único evento predictions de época/fase seleccionadas, role val. Identidad sample es ruta relativa; no se mezcla con sample_id gobernado sin correspondencia acreditada. Mixed namespaces → incompatible. Nombres de fichero similares no acreditan misma célula.

### Fórmulas

Para poblaciones Pᵢ, S=∩Pᵢ, U=∪Pᵢ. Comparación en S, con labels coherentes. Cobertura_i=|S|/|Pᵢ|; missing_i=|U\Pᵢ|; exclusive del DTO=|Pᵢ\S|, que con más de dos RUN **no implica exclusiva de un solo RUN**.

`agreement_ij = Σₛ∈S 1[ŷᵢ(s)=ŷⱼ(s)]`, la API devuelve conteo y N; UI expresa conteo/N. `error_overlap_ij=Σ1[ŷᵢ≠y ∧ ŷⱼ≠y]`. Error exclusivo_i = modelo i falla y todos los demás aciertan; acierto exclusivo_i = solo i acierta. `oracle=Σ1[existe i correcto]/|S|`; all_wrong=ninguno acierta.

Consenso: todas las decisiones binarias iguales; categoría CONSENSUS_TP/TN/FP/FN usando etiqueta real. Desacuerdo=al menos una decisión distinta. No hay voto mayoritario, promediado ponderado de scores ni ensemble entrenado en esta función. Para dos modelos los errores comunes son los casos donde ambos fallan, no una verdad clínica alternativa. Todos pueden coincidir y equivocarse.

Alta confianza errónea: existe error con score≥0.9 si pred1 o ≤0.1 si pred0. Cerca de threshold: existe |score−tᵢ|≤0.05. Son reglas de priorización, no entropía ni calibración estadística. `confidence` no se estima a partir de IC.

Código [backend_api/app/services/scientific_report.py:44](../../../backend_api/app/services/scientific_report.py#L44); [backend_api/app/services/scientific_report.py:82](../../../backend_api/app/services/scientific_report.py#L82). Complejidad de conteos pareados O(Ncomún·R²), indexación/población en memoria; paginar25/100 limita respuesta, no el trabajo científico previo.

### Visualización y controles

KPI FN/FP/error/high confidence/cerca umbral en caso individual; comparativo incluye oracle, all_wrong y N común/unión. Barras distribución por categoría, aciertos/errores exclusivos; heatmaps acuerdo y solapamiento con N visible e intensidad normalizada; tabla MRT de células con filtros sample contiene, label, categoría y score min/max por RUN. Orden y filtros se aplican en backend a toda población antes de offset/limit; cambian página a0. La matriz/indicadores globales no se recalculan sobre solo las filas visibles filtradas: no interpretar un filtro como una nueva cohorte clínica.

El resumen frontend llama «par más complementario» al de menor número absoluto de errores compartidos. Ese indicador es descriptivo y depende de tasa marginal de error/N, no una demostración de mejora de un ensemble ni independencia estadística. La galería original se sirve con source=dataset_sample,TRAIN,attempt,sample,dataset_version y validación de pertenencia/hash. Abrir Explicabilidad conserva muestra seleccionada en parámetro `muestra`.

### Respuestas científicas permitidas

Sí puede medirse si se equivocan en las mismas células y separar errores complementarios cuando sample_id/labels/población concuerdan. Células de all_wrong, scores extremos incorrectos y cercanas al umbral son candidatas de revisión. Para atribuir desacuerdo a calidad de imagen hacen falta medidas/anotaciones de calidad alineadas; este consenso no calcula esa relación. Un especialista recibe imagen original, identidad, score, umbral, decisiones y XAI existente. Puede orientar nuevas anotaciones/augmentación/controles de tinción; no modifica automáticamente etiquetas.

Reproducción y ejemplos de tres RUN estrictamente separados en [pairwise_errors.json](evidence/pairwise_errors.json) y documento 07. No se ejecutó ensemble.

## D. Explicabilidad — tres fichas independientes

### Contrato compartido y cobertura

`explanation_spec` valida método gradcam/lime/shap, class0/1; LIME/SHAP num_samples1000–5000(default1000), gradcam sin num_samples; layer solo para gradcam; SHAP exige background y los otros lo prohíben. Selección de muestra se hace por dataset_split_assignments ordenados por source_record_id con límite determinista; max_images y sample_id son mutuamente compatibles según contrato. No se selecciona por posición de una lista de imágenes arbitraria.

`KerasRuntime.images`: bytes de muestra autorizada, SHA, ruta dentro de dataset/split, RGB resize bilineal antialiasFalse y preprocessing del input_contract. Model load compile=False, semilla de identidad, inference training=False. SHAP background viene de otra muestra autorizada y conserva patient_id/sample_id propios. `runtime_for` discrimina por contrato de entrada, no nombre visual del modelo; TF/Torch deben estar en su entorno respectivo.

`save_artifacts` genera map.npy float32 y overlay.png uint8 con IDs nuevos, creación exclusiva, fsync y enlace atómico sin overwrite. BD: assessment_identities (checkpoint/dataset/samples/spec/code), attempts (estado/timestamps/root/verificación), results (target/result/artifacts), artifacts (artifact_id,sample_id,role,payload con path/bytes/SHA). Runtime produce atribuciones; backend las lee y React compone vistas. Tablas xai_evidence/xai_artifacts del contrato histórico no son la fuente de estos EXPLAIN actuales.

Código [malaria_dl_local_project/src/malaria_dl/assessment/service.py:27](../../../malaria_dl_local_project/src/malaria_dl/assessment/service.py#L27); [malaria_dl_local_project/src/malaria_dl/assessment/runtime.py:14](../../../malaria_dl_local_project/src/malaria_dl/assessment/runtime.py#L14); [malaria_dl_local_project/src/malaria_dl/assessment/runtime.py:215](../../../malaria_dl_local_project/src/malaria_dl/assessment/runtime.py#L215); [frontend/src/components/reports/ScientificReport.tsx:328](../../../frontend/src/components/reports/ScientificReport.tsx#L328).

### D1. Grad-CAM

**Fundamento:** activación de capa convolucional Aᵏ, score objetivo f_c. `αᶜₖ=(1/HW)Σᵢⱼ ∂f_c/∂Aᵏᵢⱼ`; `Lᶜ=ReLU(Σₖ αᶜₖ Aᵏ)`. Implementación `compute_gradcam_artifacts`: obtiene capa explícita o última convolucional conectada; modelo auxiliar devuelve features+salida; GradientTape sobre **sigmoid p** para clase1 o **1−p** para clase0 (no afirmar que usa logit). Promedia gradientes ejes batch/H/W, suma canales, ReLU, divide por máximo si positivo o mapa cero, resize bilineal al tamaño de entrada. Overlay JET=0.6imagen+0.4mapa coloreado.

Compatibilidad: CNN Keras custom/VGG16/DenseNet con salida rank4 conectada; casos de grafo no conectado/gradiente None generan GradCAMUnsupportedError. BiomedCLIP/ViT en runtime auditado admite solo LIME/SHAP; no hay Grad-CAM ViT ni attention rollout por analogía. Capa efectiva queda en result de EXPLAIN, no se infiere del último bloque dibujado.

Salida: mapa no negativo[0,1], overlayPNG; no conserva evidencia inhibitoria eliminada por ReLU. Mapa cero no prueba que no exista rasgo útil; saturación, capa/objetivo y gradientes afectan interpretación. El resize no agrega resolución causal. No mide localización anatómica real ni segmentación de parásito.

Código [malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py:963](../../../malaria_dl_local_project/src/malaria_dl/explainability/pipeline.py#L963); pruebas nominales en catálogo (Grad-CAM/graph/input contracts). Caso principal tres targets con artefactos íntegros; no se generó ninguno nuevo.

### D2. LIME

**Fundamento:** segmentación en superpíxeles z∈{0,1}ᵐ, perturbaciones, consulta f(z), ajuste de surrogate local `g* = argmin_g Σ_z πₓ(z)(f(z)−g(z))² + Ω(g)`. Se delega segmentación, ponderación y regresión a `lime.lime_image.LimeImageExplainer`, con semilla de identidad, labels=(class,),top_labels=None,num_samples1000–5000,batch_size y random_seed. Los defaults no pasados explícitamente dependen de la versión instalada y no deben presentarse como hiperparámetros propios persistidos.

Keras callback transforma displayRGB al input real y devuelve[1−p,p]. Torch utiliza transform OpenCLIP invertida/replicada sobre display y su score de dos clases. Heat por píxel = coeficiente firmado del superpíxel, no intensidad de infección. `local_exp[class]` se proyecta con explanation.segments. La salida map.npy preserva signo; overlay PNG guardado usa abs(heat)/max y mezcla 0.6RGB+0.4colormap rojo/azul, por lo que **ese PNG pierde distinción positiva/negativa**. La superposición canvas de la UI se reconstruye desde NPY y sí conserva el signo, como se detalla más abajo. Es diferente del JET de Grad-CAM.

Compatible con todas las seis modalidades por runtime/callback; que haya implementación no prueba ejecución en linear/fine-tuning, cuyos EXPLAIN registrados son cero en captura. Perturbar superpíxeles puede producir imágenes fuera de distribución; tamaño/regiones/seed afectan resultado; no es segmentación experta ni prueba global de fidelidad. No se encontró persistencia de score local de surrogate o estudio de estabilidad por semilla en el reporte principal.

Código [malaria_dl_local_project/src/malaria_dl/assessment/runtime.py:70](../../../malaria_dl_local_project/src/malaria_dl/assessment/runtime.py#L70); [malaria_dl_local_project/src/malaria_dl/assessment/openclip.py:290](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L290); [malaria_dl_local_project/src/malaria_dl/assessment/runtime.py:168](../../../malaria_dl_local_project/src/malaria_dl/assessment/runtime.py#L168).

### D3. SHAP (Expected Gradients)

**Fundamento:** no se implementa enumeración exacta de coaliciones Shapley; se llama `shap.GradientExplainer`, que aproxima expected gradients: `φᵢ(x) ≈ E_(b,α)[(xᵢ−bᵢ) ∂f(b+α(x−b))/∂xᵢ]`, con backgrounds b y α en[0,1]. `nsamples=num_samples`,rseed=seed. El resultado depende del background; no describirlo como DeepExplainer o KernelSHAP porque el repositorio también tenga otros pipelines.

Keras expone un wrapper de las mismas entradas/salida y pesos, no recarga/clona el checkpoint; obtiene atribución de canal, exige shape de imagen, suma canales y cambia signo para explicar clase0 de salida binaria. Torch usa módulo de score positivo diferenciable; ejecuta chunks de100 perturbaciones, seeds seed+índice y promedio ponderado por tamaño. La versión usada queda en identity.code.inference_packages cuando se guardó; cada intento es su fuente, no requirements actual.

Map conserva atribuciones positivas y negativas tras suma de canales; canales pueden cancelarse. El overlay PNG guardado de magnitud absoluta no comunica signo; la vista canvas alternativa sí utiliza el NPY firmado. Un único background no estima representatividad de población; en principal el background uninfected está en TEST por el contrato EXPLAIN, no se usa para calibrar ni entrenar. Aunque se explica TEST, no implica nueva evaluación externa.

Compatible CNN y OpenCLIP diferenciable por runtime; limita memoria y batch. La suma de atribuciones no se presenta como chequeo de additivity certificado; no hay comparación contra ROI experta o estabilidad/fidelidad cuantitativa acreditada en estos nueve intentos.

### Lectura de la UI y límites de validación

`PersistedXAI` consulta intentos paginados, combina métodos por célula; selecciona población por tarjeta y agrega explicaciones de una sola célula; pagina muestras de5 y artefactos de100. Puede mostrar EXPLAIN de distinto split/checkpoint ID con avisos; el resultado clínico adjunto procede del EVALUATE del split seleccionado o más reciente de ese split. Es necesario conservar attemptId del outcome: no atribuir score de otra evaluación a la ejecución que generó el mapa sin verificar contexto.

La UI lee blobs autenticados mediante ScientificArtifact, muestra original/mapa/overlay y opciones de inspección; su tabla de artefactos no prueba presencia física, y errors al cargar son distintos de falta de registros. La función attribution_overlay elimina signo de LIME/SHAP en el PNG persistido. La vista Superposición usa otro camino: vuelve a pintar el mapa.npy firmado. No se debe atribuir al canvas la limitación del PNG.

No hay evidencia aquí de evaluación experta sobre anillo, cromatina, membrana, tinción, texturas o fondo. Una región resaltada es **atribución local al score**, no demostración de concepto aprendido. Para conceptos: anotaciones expertas/ROI y estudios como TCAV son trabajo futuro; para fidelidad: deletion/insertion o contrafactuales controlados; para estabilidad: repeticiones/perturbaciones y métricas; para concordancia: comparar métodos con igual target/checkpoint y definición de signo. No se ejecutan esas propuestas como parte de la auditoría.

## E. Arquitectura — estructura y efecto científico

### Recuperación fiel y límites

`ModelArchitectureRepository.read` obtiene run/configuración, runtime records kind=runtime,record_key=configuration por fase y checkpoint. `normalize_keras` aplana configs Functional/Sequential, conserva conexiones, infiere formas donde no hay tensor consumidor y calcula parámetros por reglas; no inspecciona pesos entrenados. Un grafo dibujado usa esa respuesta. `_weights` conoce Conv2D,Dense,BatchNorm; capas no reconocidas reciben0, por lo que no extender exactitud a arquitecturas arbitrarias. Familias actuales se auditan contra sus factories.

Parámetros Conv2D=k_h k_w c_in c_out + bias(c_out si existe); Dense=d_in d_out + bias; BN total canales*(gamma?+beta?+2 estadísticas), entrenables gamma/beta. ReLU=max(0,z); sigmoid=1/(1+exp(−z)); GAP_k=(1/HW)ΣA_ijk. Dropout durante entrenamiento conserva valor esperado mediante máscara/escalado, en inference es identidad. BN depende de medias/varianzas y estado training, no de sample_id.

Código [backend_api/app/services/model_architecture.py:163](../../../backend_api/app/services/model_architecture.py#L163); [backend_api/app/services/model_architecture.py:57](../../../backend_api/app/services/model_architecture.py#L57); [frontend/src/components/model-architecture/ArchitectureDetail.tsx:14](../../../frontend/src/components/model-architecture/ArchitectureDetail.tsx#L14).

### Fichas por modalidad

| Arquitectura | Entrada / estructura / salida | Preentrenamiento y entrenamiento | Representación |
|---|---|---|---|
| Custom CNN | Factory default200×200×3; Conv3×3 same sin bias32→64→128→256, BN+ReLU, MaxPool2 tras primeros3; GAP→Dense128ReLU→Dropout→Dense1sigmoid | Inicialización Keras de capas; L2/dropout configurables; todas entrenables según fase | GAP256, previo a Dense128 |
| VGG16 | VGG16 include_top=False; 5 bloques, conv3×3ReLU y pooling; GAP512→Dense 1024ReLU→Dropout→Dense1sigmoid | ImageNet; cabeza base, últimas n capas en ajuste; input BGR ImageNet según contrato | GAP512, **no Dense 1024 ni salida** |
| DenseNet121 | Bloques densos, concatenación de features previas y transiciones; Normalization ImageNet→backbone→GAP1024→Dropout→Dense1sigmoid | ImageNet, congelación/descongelación; base training=False en factory; parámetros de fase en registros | GAP1024 |
| BiomedCLIP Zero-shot |224×224RGB transform original; ViT imagen + encoder de prompts, embeddings L2; softmax(similitudes con escala)2 clases | Base registrada congelada; TRAIN lógico, sin época de optimización propia | encode_image_l2, no GAP CNN |
| BiomedCLIP Linear |Base ViT→embeddingL2→cabeza lineal1logit→sigmoid en predicción |Encoder congelado; BCEWithLogits en cabeza |embedding de encoder, anterior a cabeza |
| BiomedCLIP Fine-tuning |Misma ruta con bloques ViT entrenables según configuración |Full o last_n_blocks según receta; gruposLR; no atribuir cambio a todos los bloques |embedding del encoder ajustado |

Factories y contratos: [malaria_dl_local_project/src/malaria_dl/models/architectures.py:193](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L193); [malaria_dl_local_project/src/malaria_dl/models/architectures.py:240](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L240); [malaria_dl_local_project/src/malaria_dl/models/architectures.py:286](../../../malaria_dl_local_project/src/malaria_dl/models/architectures.py#L286); [malaria_dl_local_project/src/malaria_dl/models/biomedclip_training.py:16](../../../malaria_dl_local_project/src/malaria_dl/models/biomedclip_training.py#L16); [malaria_dl_local_project/src/malaria_dl/assessment/openclip.py:39](../../../malaria_dl_local_project/src/malaria_dl/assessment/openclip.py#L39).

ViT: tokens de patches más CLS, atención `softmax(QKᵀ/√d)V`, residuales y MLP por bloque, normalización y proyección de imagen. Zero-shot p_c=exp(τ⟨v,t_c⟩)/Σ exp(τ⟨v,t_k⟩). Las dimensiones/head/patch/width verificables deben leerse de la base registrada o caché estructural, no de una imagen genérica. `normalize_biomedclip` distingue bloques origin=reference cuando no hay estructura derivada. `VitStructureService` indexa caché por SHA del checkpoint base y puede generarla en un proceso; no se invocó en auditoría.

### Visualizaciones y controles

Custom: mapas apilados/bloques/tabla; VGG16: bloques3D/mapas/tabla; DenseNet: grafo/conexiones/tabla; BiomedCLIP: flujo/bloquesViT/tabla; genérico solo tabla. Los tamaños espaciales/canales se dibujan con escalas logarítmicas propias, no dimensiones físicas a escala; etiquetas contienen formas reales. Selector fase cambia resaltado de entrenables, no cambia automáticamente el checkpoint evaluado. Click bloque abre fórmulas/detalles; MathFunctionPanel contiene explicaciones matemáticas de operaciones, no nueva medición del caso.

Recorrido de una célula: catálogo/read consulta JSON guardados; POST ejecuta forward y guarda activaciones/summaries, DELETE elimina. Se inspeccionó sin ejecutar mutaciones. El repositorio selecciona un EVALUATE para el recorrido; no asumir equivalencia con el intento de la pestaña clínica si no se cotejan IDs. No llamar «activación observada» a una textura/dibujo estructural ni «attention causal» a peso de atención.

**Comparabilidad:** comparar estructura/entrada/parámetros es descriptivo, no prueba mejor generalización. Representaciones tienen dimensiones distintas y se comparan en mismas muestras; XAI depende de capa/framework. Para el principal, configuración reconstruye15.241.025 parámetros y fases, pero checkpoint es base; mayor trainable count de ajuste no implica que ese ajuste esté en el archivo elegido.

## F. Representaciones — qué información codifica el extractor

### Identidad, extracción y persistencia

`KerasRuntime.represent` encuentra exactamente una capa top-level GlobalAveragePooling2D; si no hay una o hay varias rechaza ambigüedad. Modelo multi-output devuelve pooled features y score en un mismo forward training=False por batch; float32 y finitud. `represent_reserved` concatena batches de toda la población, ajusta PCA/UMAP una vez, escribe cuatro matrices y una fila por muestra con row,raw_score,predicted,layer,patient_id,label y IDs de artefactos. Cada artefacto poblacional usa sample_id de primera muestra como ancla de contrato; el mapeo real es result.row para cada sample.

OpenCLIP implementa encode_image(normalize=True); linear/fine-tuning usan encoder correspondiente y scores de cabeza. **Limitación de descripción:** DEFINITIONS del reporte afirma siempre GlobalAveragePooling2D, pero runtime OpenCLIP produce encode_image_l2. Actualmente no hay REPRESENT Torch persistidos, por lo que el texto no contradice una proyección Torch mostrada en esta captura; es una limitación funcional a resolver si se generan. No afirmar que extracción Torch no está implementada.

Identidad frozen: modelo/checkpoint SHA, dataset version y muestras ordenadas (ID,label,paciente,path,hash), split/purpose, seed,batch,code,decisión,representation_spec. `comparison_representation` requiere misma población ordenada y contexto de EVALUATE independiente (histórico TRAIN VAL no sirve como source), última verified compatible. `representation_evidence` exige roles exactos, filas0..N−1, SHA/bytes/shape; carga allow_pickle=False. Error/missing produce estado explícito, no recalcula embeddings ni proyecciones.

Código [malaria_dl_local_project/src/malaria_dl/assessment/representation.py:14](../../../malaria_dl_local_project/src/malaria_dl/assessment/representation.py#L14); [malaria_dl_local_project/src/malaria_dl/assessment/runtime.py:53](../../../malaria_dl_local_project/src/malaria_dl/assessment/runtime.py#L53); [malaria_dl_local_project/src/malaria_dl/assessment/service.py:331](../../../malaria_dl_local_project/src/malaria_dl/assessment/service.py#L331); [backend_api/app/repositories/scientific_results.py:220](../../../backend_api/app/repositories/scientific_results.py#L220); [backend_api/app/services/scientific_representations.py:34](../../../backend_api/app/services/scientific_representations.py#L34).

### PCA

Matriz X∈ℝⁿˣᵈ float64 al proyectar. Sin StandardScaler, whitening ni L2 extra. Centrado de columnas `Xc=X−1μᵀ`; SVD full `Xc=UΣVᵀ`; coordenadas Z=XcV_r; varianza λ_j=σ_j²/(n−1), ratio λ_j/Σλ. sklearn PCA(n_components=min(50,n,d),svd_solver=full,random_state=seed), salida primeras2 float32, ratio float64 hasta50. La curva acumulada muestra fracción de varianza, no accuracy ni información clínica validada. Los componentes maximizan varianza lineal de features, no separación supervisada de clases.

[Definición primaria PCA](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA). Este PCA es de **embeddings aprendidos/preentrenados**, no PCA de atributos técnicos del EDA (color, tamaño, textura). Cada RUN se proyecta por separado: no comparar directamente CP1 del modeloA con CP1 del B como coordenadas comunes sin alineación.

### UMAP

Spec: n_components2,n_neighbors15,min_dist0.1,metric euclidean,random_state=seedTRAIN. Se ajusta sobre features completas, **no sobre PCA50**. Sin escalado añadido en project; Keras sin L2, OpenCLIP ya L2. UMAP construye vecindarios y una representación de conectividades difusas, optimiza aproximación en2D; el proyecto delega a umap-learn y no implementa otra fórmula propia. n_neighbors controla vecindad y min_dist compactación de puntos. Defaults no congelados explícitamente y versión de dependencia afectan reproducción; guardar spec no basta para independencia de versión/hardware. [Parámetros primarios UMAP](https://umap-learn.readthedocs.io/en/latest/parameters.html?highlight=metric).

Separación en2D es descriptiva. Distancias/tamaños globales, orientación y huecos no son medidas de diferencia semántica ni probabilidad. Seed fija reduce variación pero no acredita estabilidad ante otras seeds/hiperparámetros; no se ejecutó estudio de estabilidad. Grupos visuales no implican clustering implementado ni etiología de una clase.

### CKA lineal

`linear_cka` convierte X,Y a float64, mismo N>1, centra columnas. Calcula

`CKA(X,Y)=||YcᵀXc||²_F / (||XcᵀXc||_F · ||YcᵀYc||_F)`.

Equivale a alineación de Gram lineales centradas Kc=HXXᵀH,Lc=HYYᵀH con H=I−11ᵀ/n, por producto de Frobenius normalizado, pero el código **no materializa matrices n×n ni implementa kernel RBF**. Denominador cero→None. CKA es invariante a rotación ortogonal y escala isotrópica (y tras centrado a traslación), no a cualquier transformación invertible ni escalado anisotrópico. Un valor1 no prueba igualdad absoluta de embeddings; en los dos VGG auditados la igualdad se verificó además elemento a elemento.

`cka_matrix` alinea IDs por intersección y orden lexicográfico antes de indexar cada matriz, calcula simétricamente, redondea6 decimales y devuelve N común. No exige misma dimensionalidad de features. Complejidad aproximada por par O(n·dₓdᵧ+n·dₓ²+n·dᵧ²), memoria O(n(dₓ+dᵧ)+dₓdᵧ+dₓ²+dᵧ²); R modelos requiere R(R+1)/2 pares; no confundir con O(n²) obligatorio de una formulación Gram. CKA se calcula en lectura sobre archivos hasheados y no se persiste como resultado inmutable del par. El frontend solo presenta la matriz recibida.

Fuente matemática primaria: [Kornblith et al., 2019](https://arxiv.org/abs/1905.00414). Código [malaria_dl_local_project/src/malaria_dl/assessment/representation.py:56](../../../malaria_dl_local_project/src/malaria_dl/assessment/representation.py#L56); [backend_api/app/services/scientific_representations.py:71](../../../backend_api/app/services/scientific_representations.py#L71); prueba existente de rotación/escala y alineación nominal en test_representation_generation.py (ejecutada).

### Visualización e interpretación experimental

Selector UMAP/PCA, color por real0/1 o TN/TP/FP/FN; número por grupo en leyenda, correctos atenuados en modo outcome. Scatter ejes automáticos sin ticks numéricos en UI, dot size fijo; un punto por célula, tooltip score redondeado4 decimales, sample/label/predicted, click fija panel y abre la misma vista XAI de Errores. La decisión de error usa predicted persistida, no score redondeado. La figura puede esconder densidad por superposición; no inferir proporciones por área coloreada.

Curva varianza: componente1..min(50,n,d), y[0,1], acumulación en backend. KPI informa componentes para80/90 % solo si se alcanza dentro de las componentes persistidas; «>50» significa no alcanzado allí, no número total exacto. Heatmap CKA muestra valores y N por par; par más similar es máximo entre pares disponibles, sin IC ni test de diferencias.

Preguntas: PCA muestra ejes de máxima varianza lineal; UMAP vecindarios aproximados; CKA geometría de dos representaciones sobre mismas muestras. Alta CKA no prueba que ambos identifiquen cromatina/anillo ni mismo razonamiento; baja CKA no prueba complementariedad predictiva. Los FN/FP pueden localizarse por row/sample y colorearse; para saber si diferencias codifican rasgos expertos se necesitan anotaciones/probes/TCAV. No se encontró comparación exhaustiva de capas, kernel CKA, k-means/silhouette o clustering aprendido en el contrato de esta pestaña. Los recorridos de Arquitectura son capacidad distinta de un estudio de similitud entre todas las capas.

Resultado principal y comparación concreta: PCA2=39.7531 %, PCA50=87.9255 %, CKA VGG-SGD/VGG-Adam=1 sobre2.685TEST (embeddings idénticos); CKA con DenseNet-Adam=0.7308256995. Son resultados de casos seleccionados, no ranking universal de arquitecturas ni representación de todas las semillas.

## G. Trazabilidad — reconstruir cada conclusión

### Linajes que no deben mezclarse

Dataset experimental: datasets → dataset_source_records.id (=sample_id assessment) → clinical_identities.id (PATIENT) y dataset_split_assignments(source_record_id,clinical_identity_id,dataset_version_id,split_name) → materialización/versión. El crop fuente ya es la unidad celular. El nombre de fichero conserva origen, pero no se crea una relación ficticia con microscopy_images o cell_detections.

Flujo de frotis del sistema: research_subjects → scientific_cases/blood_samples → smear_slides → microscopy_images → análisis/detección → cell_crops/cell_predictions; sus FK existen en esquema pero no se acredita un join desde cada crop del dataset experimental a un frotis completo en este caso. [Constraints reales](evidence/constraints.json). No duplicar patient_id del assessment como una nueva identidad asistencial.

Experimental: campaña/versiondataset → runsTRAIN/configuración → train_execution_sessions.verification → checkpoint físico y selección → assessment_identity congelada → attempt ejecución → resultados y artefactos → DTO reporte → React. Historial v2 de evaluations/clinical coexiste con attempts independientes; no son filas equivalentes que puedan sumarse sin rol.

### Reproducibilidad e integridad

Semilla, configuración resolved, adapter version, git_commit/source_sha, entorno runtime, dataset fingerprints, umbral, política seleccionada, epoch/fase, SHA/bytes y tiempos se conservan en registros. `verify_rows` hashea filas ordenadas; `verify_representation` verifica orden/shape / bytes / hash y resultado; checkpoints se revalidan por sesión. Un checksum en PostgreSQL no demuestra que los bytes sigan disponibles; `not_checked` en DTO es deliberado. La auditoría verificó43 archivos relevantes por SHA y stat de35.341 referencias; no hasheó todos los archivos globales.

Preflight organiza dimensiones y análisis, con razones de ausencia/incompatibilidad/error; no es una verdad clínica ni se debe convertir consulta fallida en cero resultados. Un solo TRAIN da EVIDENCIA_INSUFICIENTE para comparación aunque sus datos estén disponibles; la UI evita mostrar esos dictámenes como veredicto comparativo individual. La trazabilidad puede mostrar references sin cargar binarios; consultar original está autenticado y valida pertenencia.

### Cinco reconstrucciones verificables

Se entregan en documento 06: métrica recall TEST desde conteos/filas; predicción celular y FP concreto;47FN con joins source/patient/assignment; XAI Grad-CAM de sample014d…; fila de REPRESENT de ese sample. Consultas SQL en sql/principal_scores.sql, principal_sample_lineage.sql, case_related_scores.sql, principal_full_identity.sql. Los archivos se localizan en csv/artifact_inventory.csv y se verifican contra SHA; no se copian checkpoints.

### Rupturas y límites

EXPLAIN externo al caso principal tiene estadoverified y5.386 archivos no disponibles. Identificadores lógicos3bbb…/versione8f94… de E5 no son filas artifacts/model_versions: reconstruir por sesión/UUIDv5 y hash, no forzar una FK inexistente. El frontend advierte checkpoint IDs distintos, pero el usuario necesita cotejar bytes/hash para distinguir namespace de diferencia real. Dependencias históricas incompletas, cachés de arquitectura y recorridos de archivos sin registro por artifact genérico pueden limitar reproducibilidad. IDs de paciente de dataset no contienen validación diagnóstica externa. No se ejecutaron backups, reparaciones ni regeneraciones.

## Inventario transversal de visualizaciones

La siguiente matriz complementa las fichas anteriores. En todos los casos N/RUN/split/checkpoint/threshold se toman del contexto descrito; cuando no figuran sobre el gráfico, están en Evidencia/tabla y deben acompañar cualquier exportación a P3. No se certificó el render en navegador.

| Vista | Fuente / transformación | Ejes / color / control | Faltantes / límite científico |
|---|---|---|---|
| Resumen metodológico y dictámenes |preflight; dedup reason_id |tarjetas y razones, refrescar |individual no acredita comparación; técnico≠científico |
| Épocas/configurado/checkpoint |events epoch/selection+config |tabla por RUN; fase |planificado≠ejecutado |
| Curva loss/accuracy/AUC/etc |valores epoch finitos |xépoca,yoriginal; colorRUN; VALdiscontinua; toggle/ref |sin interpolar; no TEST |
| KPI gap |loss de época seleccionada |val_loss−loss |no diagnóstico automático de sobreajuste |
| Punto operativo |recall y1−specificity persistidos |xFPR,yrecall; colorRUN |no curva ROC ni IC |
| Barras clínicas |recall/specificity/F2 |[0,1], colormétrica |tasas a cada threshold; no ganador universal |
| Confusión |TN/FP/FN/TP |filareal/columnapredicha; intensidad por conteo |N visible; no cálculo por paciente |
| Tabla clínica |DTO9tasas+N+t |split por columna |None=sin evidencia; no cero |
| Categorías errores/consenso |población común y decisiones |barras categorías / filtros |consenso≠verdad ni ensemble |
| Heatmaps acuerdo/errores |conteos pares |N común / intensidad |sin prueba pareada estadística |
| Exclusivos |solo uno acierta/falla |barras por RUN |depende de R y tasas marginales |
| Tabla células |scores por sample |MRTfiltros/orden/páginas y abrirXAI |N global no equivale a página |
| Galería XAI |npy/png e identidad |original/map/overlay, método/target |magnitud overlay pierde signo; no ROIvalidada |
| Diagramas arquitectura |configs/estructura base |SVGescalaslog, selector fase/bloque/vista |reference≠medición; parámetros≠desempeño |
| Tabla capas/fórmulas |settings y conexiones |shapes,kernel,stride,pesos |sin inspección de pesos reales por este GETKeras |
| Recorrido celular |JSONactivaciones ya guardadas |bloques/canales/célula |generación explícita no ejecutada; contexto puede diferir |
| PCA/UMAPscatter |matrices persistidas, redondeo4 |ejesauto, colorclase/outcome, pin |no semántica clínica ni estabilidad |
| VarianzaPCA |ratios y cumsum |componentes,y[0,1],80/90% |máximo50 no total de representación |
| HeatmapCKA |embeddings hash→intersección→CKA |similitud yN; colorintensidad |sin IC ni equivalencia de conceptos |
| Trazabilidad |preflight evidence/refs |dimensiones, IDs, fuentes |registrado≠disponible físicamente |

**Exportación:** copiar ID/enlace/comando y recuperar archivos existentes; no se identificó exportador nativo integral de gráficos/tablas de esta ruta. Las figuras de auditoría tienen N/split/fuente propios y no deben presentarse como capturas de la aplicación.

## Anexo: recorrido de activaciones, gráficos y fórmulas adicionales

La opción Arquitectura incluye medidas que no deben confundirse con XAI de gradientes o con PCA/CKA. `activation_trace_compute.statistics` devuelve mínimo, máximo, media, desviación estándar poblacional (`values.std()`, ddof0) y fracción activa `mean(values>0)` del tensor. Para mapas espaciales selecciona hasta16 canales por mayor media espacial, orden descendente; no muestra todos los canales ni los elige por importancia clínica. Los vectores tienen valores destacados e histograma `numpy.histogram` con bins del módulo. Los PNG de canales se normalizan para visualizar y son resúmenes del tensor, no las matrices originales completas.

`ScoreBar`: pista 0–1, score y marca threshold; usa clamp para dibujo. `StepProfile`: x pasos/capas, y fracción activa 0–100 %, hasta dos células con colores current/compare. Esa fracción depende de activación/normalización y no mide utilidad de una capa ni cantidad de parásito. `VectorHistogram`: bins de valores frente a cantidad de neuronas, altura normalizada al máximo visual; conteos originales en tooltip. `MiniCurves`: loss y val_loss a escala local con checkpoint. El visor permite pasos anterior/siguiente, reproducción animada, click de bloque, escala de mapas, canal y comparación con otra célula guardada; las animaciones navegan datos guardados y no ejecutan el modelo.

Para el principal hay tres recorridos **VAL**, ocho pasos cada uno, consistencia registrada true. Los resúmenes y hashes se leyeron, no se ejecutó forward. El selector de evaluación del repositorio de recorridos es independiente del de Desempeño clínico: hay que conservar attempt/split al interpretar el vínculo. Una barra de score de un recorrido zero-shot representa score relativo de prompts aunque un componente genérico use la palabra «Probabilidad»; no acredita calibración.

Fuentes: [activation_trace_compute.py](../../../backend_api/app/services/activation_trace_compute.py#L153), [TraceCharts.tsx](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L5), [ActivationTracePanel.tsx](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L134), [saved_traces_summary.json](evidence/saved_traces_summary.json).

**Acceso BiomedCLIP:** las fichas de runtime/arquitectura anteriores describen capacidad de código y evidencia registral. La página actual no ofrece esos tres modos porque el catálogo traceability filtra model_type=classification. No se ha verificado una visualización interactiva BiomedCLIP desde este selector; matriz07 conserva esa limitación explícita.

## Verificación específica del visor XAI: PNG frente a mapa firmado

**HECHO VERIFICADO EN CÓDIGO:** hay dos caminos de visualización diferentes, no un único overlay:

1. **Comparación de cuatro cuadros:** original y PNG de cada método recuperados como blob autenticado. Para LIME/SHAP, el PNG creado en runtime resume magnitud absoluta. Grad-CAM usa su JET no negativo.
2. **Vista ampliada → Superposición:** `XAIOverlayView` recupera los mapas NPY, los interpreta con `parseNpy` y crea un canvas por método. LIME/SHAP se pintan con signo: rojo `(214,39,40)` a favor, azul `(31,119,180)` en contra de la **clase explicada**; Grad-CAM usa rampa de activación no negativa. No se está volviendo a explicar el modelo: se transforman números persistidos en píxeles.

`parseNpy` valida magic NUMPY, shape de dos dimensiones, orden C (`fortran_order=False`), dtype little-endian f4 o f8 y longitud; f8 se convierte a float32. Para mapa firmado, escala=max|atribución|; para Grad-CAM, escala=max(activación). Cada valor se divide por su propia escala, alpha=round(255×magnitud_normalizada); regiones neutras transparentes. En Grad-CAM se usa activationColor interpolando seis nodos de color; no el JET del PNG guardado. Las intensidades no se comparan entre métodos porque las escalas son independientes.

La composición canvas dibuja el original redimensionado a resolución del input y luego capas Grad-CAM→LIME→SHAP con `globalAlpha=opacidad/100`. Defaults: Grad-CAM50 %, LIME0 %, SHAP0 %; cada capa tiene checkbox y slider0–100 %. Por eso un método existente puede ser invisible inicialmente sin estar ausente. El orden, escala y alpha son transformaciones visuales; no son suma científica de atribuciones ni consenso entre métodos.

Exportación adicional real: `CellTrace` ofrece **Descargar JSON completo por método**, con referencia de artefacto e identidad/metadata completa. La UI compacta listas de samples al mostrar metadata, pero el JSON descargado conserva esa información. No se encontró exportador integral de las siete opciones.

La agrupación `groupXAIComparisons` usa clase objetivo, contexto canónico (modelo/dataset/decisión/protocolo, sin localizadores físicos), TRAIN, versión, checkpoint, sample_id, dataset version, split y purpose. Excluye método/background/semilla/batch/code como claves de equivalencia entre métodos. Repetir un método produce otra fila; no sobrescribe evidencia. SHAP background se conserva como referencia, no como célula target. La equivalencia de contexto no significa identidad de parámetros de perturbación ni comparación cuantitativa de fidelidad.

Recuperación de originales: UUIDs válidos, pertenencia a TRAIN/attempt/sample y dataset/split, snapshot concordante, ruta confinada y SHA del source record. Error de relación404, ID400, archivo faltante410, integridad409, almacenamiento503; cliente los traduce a missing/denied/integrity_failed/not_comparable/error. No son valores cero ni una nueva inferencia.

Fuentes: [XAIOverlayView.tsx](../../../frontend/src/components/reports/XAIOverlayView.tsx#L8), [attributionMaps.ts](../../../frontend/src/utils/attributionMaps.ts#L6), [XAIComparisonViewer.tsx](../../../frontend/src/components/reports/XAIComparisonViewer.tsx#L24), [comparison.ts](../../../frontend/src/components/reports/xai/comparison.ts#L74), [dataset_samples.py](../../../backend_api/app/services/dataset_samples.py#L14).
