# E10.10.4 — Diseño definitivo propuesto de PostgreSQL v2
> Actualización E10.10.5A: A-01 fue aprobada por el usuario. La sección final documenta la enmienda; el cuerpo original conserva su contexto histórico. Implementación y límites actuales: [e10_10_5_implementation.md](e10_10_5_implementation.md).

**Estado: diseño propuesto, pendiente de aprobación. Fecha: 2026-09-29. No inicia E10.10.5.**

Se propone una instancia canónica PostgreSQL 17, un esquema `public`, ownership lógico por dominio y una única línea nueva de Alembic capaz de construir v2 desde cero. La comparación científica usa configuración congelada, identidad de evaluación y mediciones binarias tipadas. Se reutilizan la coordinación E10, el dataset protegido, la inferencia celular y la gobernanza existentes.

## 1. Evidencia, decisiones y límites

| Etiqueta | Significado en este documento |
| --- | --- |
| **EV — evidencia verificada** | Lectura de documentos, catálogos capturados y código; no implica ejecución de servicios. |
| **AP — decisión aprobada previamente** | Restricción del encargo o contrato científico vigente, no aprobación de v2. |
| **DP — diseño propuesto** | Requiere aprobación antes de implementarse. |
| **HP — hipótesis pendiente** | Debe comprobarse en implementación aislada. |
| **RA — riesgo abierto** | Puede impedir adopción aunque la documentación esté completa. |

EV: inventario E10.10.1 de 97 tablas, 27 vistas, 65 funciones propias, 77 triggers de aplicación, 208 FK, 416 CHECK, 389 índices físicos (228 independientes), 130 columnas JSONB en 72 tablas. `runs` tiene **cinco** JSONB, no diez. El UUID oficial es una versión de dataset, no la PK de `datasets`. E10.10.3 complementa esa captura; no se presenta el conteo histórico como medición de hoy.

Se cargaron y recorrieron íntegramente ambos JSON (55.986 y 10.718 valores escalares), los ocho documentos obligatorios y los archivos fuente localizados en backend, proyectos ML/dataset, frontend, Alembic y SQL histórico. El CSV incluye las definiciones actuales completas y localizadores de consumidores por tabla. Las coincidencias textuales son localizadores, no una demostración automática de alcance semántico; los flujos críticos se inspeccionaron por implementación. No se inspeccionaron clientes externos.

Para completar longitudes y precisiones ausentes de `information_schema.columns` en el JSON se extrajeron **sólo declaraciones de esquema** de un respaldo local mediante `pg_restore --schema-only --file=/tmp/...`, sin conexión ni restauración. El respaldo no sustituye al baseline vigente: sólo complementa los tipos de columnas coincidentes; restricciones, funciones, triggers e índices proceden del JSON actual. La aceptación de la futura baseline exige comprobar typmods/colaciones y ACL con el catálogo de una copia; éste es un límite de equivalencia física, no permiso para modificar tipos protegidos.

**No se abrió conexión a PostgreSQL. No se ejecutó SQL, EXPLAIN, migración, stamp, benchmark, entrenamiento, evaluación ni explicación clínica. No se leyeron imágenes ni se recalcularon checksums de imágenes.** Sólo se crearon estos documentos; el SQL es texto conceptual.

## 2. Resumen estructural

| Magnitud | Propuesta |
| --- | ---: |
| Tablas actuales | 97 |
| PROTECTED | 17 |
| KEEP | 67 |
| REFACTOR | 11 |
| MERGE | 2 |
| REPLACE / RETIRE / UNDETERMINED de tablas | 0 / 0 / 0 |
| Tablas nuevas | 8 |
| Tablas físicas objetivo | **103 = 97 − 2 + 8** |

Las 95 tablas actuales que permanecen son 17 protegidas, 67 conservadas y 11 refactorizadas. No se retira funcionalidad por estar vacía una tabla. Las dos consolidaciones son candidatas al retiro **físico** de tablas, reemplazadas por vistas y escritores trasladados, no eliminaciones de evidencia. El CSV contiene las 97 filas actuales; las ocho nuevas se detallan aquí y en el DDL.

| Tabla nueva | Responsabilidad y cardinalidad |
| --- | --- |
| `run_configurations` | 1:1 con TRAIN, configuración resuelta inmutable; FK por run. |
| `evaluations` | Identidad de medición por run, split, población, protocolo y checkpoint; varias por run. |
| `evaluation_ensemble_members` | Miembros ordenados y ponderados de evaluación ensemble; mínimo dos. |
| `xai_evidence` | Extensión reproducible 1:1 de explicación ML, celular o resultado de assessment por muestra, con XOR entre padres. |
| `xai_artifacts` | 1:N archivos numéricos/visuales/manifiestos, sin binarios en PostgreSQL. |
| `xai_quantitative_evaluations` | 1:N pruebas de calidad explicativa con protocolo y referencias; posibilidad nueva, no capacidad ya implementada. |
| `xai_interpretations` | Interpretaciones científicas firmadas por usuario, append-only. |
| `xai_specialist_reviews` | Revisión de una interpretación, identidad/competencia/evidencia; no confirmación diagnóstica automática. |

**AP:** los seis objetos `campaign_controlled_requests`, `campaign_technical_revisions`, `experiment_execution_events`, `experiment_execution_gate`, `local_execution_jobs`, `train_execution_revisions` conservan tablas, claves, guardas y contratos completos. E10.10.2 refutó su supuesto abandono. El ledger `train_execution_records` y los eventos globales tienen identidades distintas.

## 3. Dominios y ownership

| Dominio | Entidades / autoridad de escritura |
| --- | --- |
| Identidad y seguridad | users, roles, user_roles, audit_events; servicios de autenticación. Dataset/credenciales no son fixtures. |
| Dataset científico | dataset_versions, assignments, sources, identities, materializations; gobernanza del split, protegido. |
| Experimentos y ejecución | experiments, campaigns, members, attempts, sessions, gate, jobs, records; coordinador autorizado. |
| Resultados | configurations, evaluations, clinical_metrics, history, calibrations, artifacts; ResultService/repositorios transaccionales. |
| Inferencia clínica | casos, sujetos, muestras, láminas, imágenes, QC, detección, crops, clasificación, predicciones, revisiones; servicios clínicos. |
| Gobernanza/publicación | model_versions, lineage, deployments, stage2 publications; servicios de publicación. |
| XAI científico | padres actuales + evidence/artifacts/quality/interpretations/reviews; generación y revisión separadas. |

DP: mantener `public` reduce cambios en SQL no cualificado, vistas, guards y `search_path`; la separación lógica se expresa mediante contratos y permisos de aplicación, no otro migrador. Una futura separación `clinical`/`ml` permitiría ACL y nombres más claros, pero exige adaptar funciones, FK cruzadas, búsqueda de objetos y pruebas E10. No ofrece beneficio suficiente en esta entrega. No se inventan owners administrativos: el inventario previo no acredita ACL completos. La futura baseline fija rol migrador distinto del rol runtime, sin conceder BYPASSRLS ni DDL al runtime.

La instancia canónica es compartida por FastAPI y Docker. TRAIN local reporta por HTTP; no necesita una segunda PostgreSQL ni replica científica. Los parámetros `datasource` existentes deben resolver a la conexión canónica o rechazarse expresamente; no conservar rutas a bases de archivo como alternativa de escritura.

## 4. Modelo científico y normalización

La secuencia es `campaign → member → attempt → TRAIN run → configuración congelada/checkpoint → evaluación → medición → publicación o comparación`. Un TRAIN standalone tiene sesión y run, sin inventar intento/campaña. La versión de dataset permanece en `runs`; cada evaluación fija además la población y el protocolo efectivamente evaluados.

| Responsabilidad | Destino |
| --- | --- |
| Identidad, estado, tiempos, host, versiones y consumo medido | `runs`, `environment_packages`; memoria máxima NULL si no medida. |
| Configuración estable | `run_configurations`; seed, optimizer, LR y preprocessing se consultan sin JSON. |
| Resultado técnico de TRAIN | `runs` completed_epochs/best_epoch/stopped_epoch y `run_checkpoint_policy`; no una segunda tabla de training_results. |
| VALIDATION final / TRAIN / TEST | `evaluations` con split/role explícitos y `run_clinical_metrics` 1:1. |
| Curvas | `training_history`, UNIQUE(run_id,phase,epoch); train/val explícitos, sin TEST. |
| Matriz binaria | tp/fp/fn/tn de `run_clinical_metrics`; `confusion_matrices` pasa a vista. |
| Reporte por clase | `classification_reports` pasa a vista derivada de los conteos; macro/weighted se calculan en lectura. |
| Métricas no estables | `run_metrics` como extensión, con prohibición de nombres científicos reservados y adaptación de aliases en escritor. |
| Calibración | `run_threshold_calibration`, dos referencias a evaluaciones default/seleccionada; snapshot JSON conserva evidencia del algoritmo. |
| Checkpoints/linaje | `artifacts`, `model_versions`, `run_lineage`, `run_checkpoint_policy`, sin rutas reconstruidas. |
| Evidencia de ejecución | `train_execution_records` y assessments intactos; proyección tipada es estado consolidado. |

La separación de `evaluations` y `run_clinical_metrics` es 1:1 para reutilizar lectores existentes y mantener identidad/protocolo fuera del ancho registro métrico. Una constraint trigger diferida exige medición al commit. No se presenta una evaluación incompleta como resultado disponible.

DP: retirar las dos tablas consolidadas **sólo después** de trasladar `log_confusion_matrix` y `log_classification_report` en `persistence/run_repository.py`, llamadas desde tracking/trainer/evaluation, y adaptar `/runs`/training summaries. E10.10.1 registra cero filas y cero FK entrantes/dependencias de funciones o vistas para ambas; eso facilita la transición, pero los escritores siguen activos. Si la copia futura contiene datos, reconciliar por run/split/checkpoint/protocolo, conservar ID de origen en manifiesto y abortar ante ambigüedad. No escoger arbitrariamente el último registro ni deducir checkpoint del nombre del archivo.

Las columnas históricas de matriz, sensibilidad y reportes en `run_clinical_metrics` son campos de compatibilidad derivados/controlados, nunca fuentes independientes. El trigger deriva matriz y sensibilidad de los conteos y recall; el DTO v2 no expone duplicados. El JSON classification_report no debe seguir siendo escritor de métricas estables; su contenido de evidencia anterior se preserva en Ruta B, y para nuevas evaluaciones se deriva en el servicio de lectura. La reducción principal elimina JSON científico de `runs.parameters`, EAV duplicado y dos tablas redundantes; no promete eliminar todo JSONB ni todos los alias de transición.

### Métricas y nulabilidad

`tn/fp/fn/tp`: bigint no negativo. `sample_count`: suma exacta y positiva; en DDL conceptual numeric para evitar overflow intermedio de bigint. Ratios: numeric sin escala impuesta, dominio [0,1], sin redondeo antes de comparar. LR y datos de TensorFlow: double precision finito; fechas timestamptz. PostgreSQL admite NaN/Infinity: el dominio debe excluirlos, no basta `>=0` para valores sin cota superior.

| Métrica | Definición | NULL |
| --- | --- | --- |
| Recall / sensitivity | TP/(TP+FN), un único valor canónico | Sin positivos verdaderos. |
| Specificity | TN/(TN+FP) | Sin negativos verdaderos. |
| Precision | TP/(TP+FP) | Sin positivos predichos. |
| F1 | 2TP/(2TP+FP+FN) | Denominador cero. |
| F2 | 5TP/(5TP+FP+4FN) | Denominador cero. |
| Balanced accuracy | (recall+specificity)/2 | Cualquiera de las dos indefinida. |
| ROC-AUC / PR-AUC | Resultado del cálculo sobre scores, método versionado | Una clase, no calculada o scores ausentes; razón explícita. |

No recalcular AUC desde la matriz. Una curva PR requiere documentar si el algoritmo usa área trapezoidal o average precision: `protocol_snapshot` y `metric_definition` registran la implementación real; no se intercambian las dos cantidades. El servicio rechaza diferencias entre tasas recibidas y conteos cuando la tasa está definida (tolerancia del contrato actual 1e-12). En casos indefinidos deriva NULL y conserva el cero original solamente en el evento v1.

**RA:** `results/training.py` y `evaluation/binary_counts.py` imponen hoy zero_division=0 y sólo AUC nullable. Cambiar su payload invalidaría hashes/reintentos. V2 propone una **proyección distinta**, `binary_nullable_v2`, sin reescribir `training_results_v1`/`validation_evaluation_v1`, ni modificar los algoritmos en esta etapa. Pydantic/React v2 deberán admitir NULL y mostrar «no definida», sin `?? 0`. Se requiere aprobación de este cambio de representación y pruebas de round-trip legacy.


EV adicional: `assessment/contracts.py:metrics` ya usa NULL para divisiones indefinidas, a diferencia del contrato TRAIN v1. V2 converge en esa semántica sin editar ninguno de los algoritmos actuales. Los perfiles `configs/models/*.json` contienen overrides batch (incluida calibración habilitada en perfiles existentes); no es correcto afirmar que toda configuración efectiva actual tiene calibración OFF. El default de v2 sigue OFF; elegir un perfil que la activa debe quedar explícito en requested/resolved. Esta diferencia se somete a aprobación sin modificar perfiles ni decisiones científicas en E10.10.4.

### Configuración reproducible

EV: `models/configuration.py` resuelve defaults versionados < JSON seleccionado < overrides CLI, fija `requested/provenance/resolved` y hash de `resolved`. Se materializan columnas desde **resolved**, nunca desde el primer alias no vacío que usa hoy training_summaries. Se preservan `canonical_configuration`, hash original y snapshot de procedencia; no se recalcula el hash de un subconjunto tipado. La reserva inserta configuración en la misma transacción del run antes del fit. Guard append-only después del insert; un nuevo entrenamiento requiere otro run.

Custom CNN usa RGB rescale_0_1; VGG16 usa vgg16_imagenet externo; DenseNet121 conserva rescale_0_1 externo y densenet_imagenet_channel_mean_std interno. La identidad incluye dimensión, canales, adapter version, loss y weights. No sustituir VGG16 por `/255`, ni aplicar dos veces normalización DenseNet. Los parámetros específicos del optimizer quedan en `optimizer_extensions`; optimizer y learning_rate son columnas. Fine tuning tiene epochs/LR/layers propios.

AP: calibración OFF por defecto; default 0.5; cuando se habilita, sólo VALIDATION; objetivo recall parasitized ≥0.98. TEST jamás selecciona checkpoints ni calibra umbrales. `protocol_numeric` conserva el mecanismo assessment de umbral explícito autorizado por protocolo: no inventa calibración TEST. La elección/compromiso del protocolo se congela antes de TEST y se prueba en servicio; un CHECK por sí solo no prueba cronología de decisiones humanas.

### Comparación y ensembles

El DTO devuelve `evaluation_id`, TRAIN/run/version/checkpoint, configuración, dataset version, split, population/protocol/input hashes, metric_definition, umbral y todas las métricas. Agrupar sólo dentro de `comparison_contract_hash`: debe fijar versión, asignaciones, protocolo, propósito, métrica/etiquetado y política de umbral; excluye arquitectura/optimizer/seed, que son ejes de comparación. `input_contract_hash` se muestra para documentar preprocessing propio de cada arquitectura; no exige que VGG16 y CNN reciban tensores con igual normalización. Una comparación pareada val/test usa el mismo protocolo experimental y reporta **dos poblaciones**, no las agrega como si fueran la misma muestra.

Por seeds se devuelve n, media, desviación muestral y valores individuales; stddev NULL con n<2. No confundir variación entre seeds con intervalo clínico por paciente. FN/TP absolutos se comparan con denominador y población visibles. Un resultado con recall ≥0.98 marca cumplimiento observado, no elegibilidad adicional de publicación ni confirmación clínica. Selección usa sólo desarrollo/val; TEST se presenta como evaluación final del candidato ya congelado.

Ensemble: miembros FK a versiones/checkpoints, orden y peso positivo con suma 1 y al menos dos miembros al commit. `training_run_id` de evaluación ensemble es el run de referencia de gobernanza, no un supuesto entrenamiento del ensemble. El protocolo fija combinación, salida y umbral; la UI etiqueta explícitamente ensemble y muestra todos los miembros. Protocolo y linaje deben probar que pesos/miembros se fijaron sin TEST. No se implementa algoritmo ensemble. XAI ligado a una evaluación ensemble identifica el miembro exacto explicado; no se etiqueta como explicación de la combinación completa. Una explicación del combinador requeriría un método/protocolo adicional aprobado.

## 5. E10: aceptación, proyección y recuperación

EV: `ResultService.accept_event()` ya hace append y `project_training_result()` dentro de `acceptance_scope`; sólo retorna después del commit raíz. La proyección actual concatena `parameters.training_results`. La implementación v2 cambia esa proyección por insert de identidad y métricas y, para eventos de época, upsert idempotente controlado de `training_history`. No abre otra conexión, no usa `safe_track` que silencie un fallo científico.

Orden: resolver identidad confiable → gate/fencing → locks campaña/miembro/intento/sesión/run en el orden actual, NOWAIT donde corresponda → buscar event_id global → verificar hash canónico y hashes legacy → secuencia por run → validar payload → append evidencia → proyectar → constraints diferidas → commit → ACK. Duplicado idéntico autorizado retorna el ACK previo sin insertar; conflicto de contenido/sequence/gap aborta todo. FK de proyección E10 usa `(run_id,kind,phase,record_key)` de la PK existente: **un índice parcial UNIQUE(event_id) no sirve como objetivo de FK**.

No aceptar un evento en transacción A y materializar en B. Si falla proyección, no queda evento aceptado. Si se pierde ACK, reenvío obtiene duplicado; si una proyección antigua falta, la reparación se hace en una operación versionada auditada sobre copia, no silenciosamente en GET ni mediante volver a aceptar en sesión cerrada. La semántica actual rechaza owner/sesión inválidos incluso ante duplicado.

`ExecutionContext`, `RunEvent`, `RunEventEmitter`, `RunReporter`, `DockerRunReporter`, `HttpRunReporter` conservan su frontera runtime-agnostic. La finalización sigue verificando evidencia completa, checkpoint, selección, snapshot y salida del proceso. Una fila de métricas **no** significa TRAIN completed. `calculation_reported` local no significa released. OOM pausa campaña/gate según contratos actuales, no por un umbral de métricas. Las evidencias globales de coordinación no se fusionan con resultados.

## 6. Frotis: continuidad y separación clínica

Se reutiliza `research_subjects → scientific_cases → blood_samples → smear_slides → microscopy_images`. Ingestión conserva lote/origen; `microscopy_analysis_runs` y su tabla de imágenes fijan ejecución, QC y decisiones de gate. Detección/connected_components/crops llevan a `cell_classification_inputs` congelados, `cell_classification_runs` y `cell_predictions`.

La predicción conserva probabilidad parasitized/uninfected, threshold, política, versión desplegada, preprocessing, duración y estado. `smear_analysis_summaries` es una agregación automática según snapshot de política; `cell_classification_reviews` y validaciones científicas son acciones humanas trazables. `scientific_validation_annotations` y sus eventos mantienen revisión/versionado. No crear una segunda entidad case/patient ni copiar identidades protegidas. El historial React navega la cadena existente y añade evidencia XAI por predicción/imagen; un resultado IA se etiqueta «asistido» hasta la acción humana correspondiente. La revisión XAI no sustituye la revisión de la predicción ni confirma malaria.

## 7. Modelo de datos de explicabilidad científica XAI

### Implementación real y diferencias de rutas

| Ruta / método | Entrada y objetivo | Datos numéricos y visuales actuales | Implicación v2 |
| --- | --- | --- | --- |
| `explainability/pipeline.py` Grad-CAM | Tensor preprocesado; última conv conectada; sigmoid o complemento para clase negativa | Gradientes promediados, ReLU, normalización, resize bilinear; mapa float32 y overlay; wrapper guarda figura PNG | Registrar layer real, invert_scalar_output, salida, resize, cmap y versión; no equiparar figura al mapa raw. |
| pipeline SHAP | GradientExplainer, background recibido; fallback de construcción Keras | Tensor por canal; extracción de última salida; media por canal y normalización max abs para PNG | Guardar tensor raw si disponible, agregación y selección exacta de salida. La clase mostrada no prueba qué salida se explicó. |
| pipeline LIME | RGB display; predict_fn reaplica preprocessing; clase predicha | seed 42, 1000 perturbaciones, SLIC 50/compactness10/sigma1, máscara de 8 regiones positivas y PNG | Guardar segmentos/pesos y surrogate/intercept/score sólo si capturados; no reconstruirlos del PNG. |
| `assessment/runtime.py` los tres | Identidad gobernada; muestras y checkpoint fijados, seed/determinismo | `save_artifacts`: mapa float32 **NPY** y overlay PNG, archivos exclusivos y hash/bytes, assessment_artifacts | **Reutilizar** artefactos y payload, no regenerar mapas ni modificar algoritmos. |
| assessment SHAP | Background de muestras TRAIN acreditadas (`assessment/service.py:104`) | GradientExplainer nsamples/rseed; suma canales y signo por target class | Distinguirlo del promedio normalizado de pipeline; el mapa no conserva tensor por canal completo. |
| assessment LIME | Seed y num_samples de identidad, segmentation defaults de librería | Pesos local_exp sobre segmentos producen mapa; no necesariamente persiste segmentation/objeto surrogate | Registrar versiones de librería y config; ampliación futura de artefactos raw, sin atribuir capacidad actual inexistente. |
| `inference/predictor.py:287` SHAP | Background artificial `[zeros_like(image), image]` | Figura de pipeline | Marcar origen synthetic_zero_plus_input; no compararlo con background TRAIN sin advertencia metodológica. |
| `case_gradcam.py` y `cell_classification.py` | Modelo/version/snapshot y entrada o crop congelado | PNG heatmap/overlay con SHA-256; no NPY raw generalizado | Preservar storage_keys y hashes actuales, ampliar captura numérica futura. |

Los módulos `gradcam.py`, `shap_explainer.py`, `lime_explainer.py` son exports; el algoritmo está en pipeline y assessment runtime. `collect_background_images(max_images=20)` existe en pipeline, pero su existencia no acredita que todas las rutas usen ese background. No afirmar que SHAP/LIME bajo demanda estén disponibles en endpoints celulares: el contrato celular actual es Grad-CAM.

### Relaciones y reproducibilidad

`xai_evidence` referencia exactamente un padre existente: ML `explainability_results`, celular `cell_explanations` o par `assessment_results(attempt_id,sample_id)`. Exige versión y checkpoint, método/versión/implementación, entrada persistente y hash existente, input contract, clase, salida explicada, etapa, seed/configuración, entorno y fecha. Para SHAP exige manifiesto de background con URI/hash. El manifiesto enumera IDs de muestras, orden, split, procedencia, transforms y semilla; no sólo un hash opaco sin recurso recuperable.

Modelo/experimento/campaña se recuperan vía versión→TRAIN→experimento/campaña; no duplicar esos IDs. Caso/muestra/lámina por prediction→classification_input→microscopy_image y análisis. `dataset_source_record_id`, `microscopy_image_id` e `input_artifact_id` son orígenes alternativos explícitos (dataset, clínica o upload acreditado); la ruta de crop conserva además la FK de predicción y crop, y `input_sha256` identifica el crop efectivo. Inputs legacy sin identidad resoluble permanecen en padres originales y se marcan como no incorporados al comparador reproducible; no inventar FKs ni hashes.

`xai_artifacts`: URI persistente, SHA-256, bytes, MIME, rol, ordinal, dtype/shape/axes/coordenadas, fecha y disponibilidad. Puede referenciar el mismo archivo assessment existente sin copiar bytes; este registro es un manifiesto de evidencia, no otra salida científica. Mapa raw, spatial_map, segment_weights y segments se distinguen de render/overlay. Campos numéricos extensos van a NPY/NPZ u otro formato documentado sin pickle; PostgreSQL conserva relaciones/metadatos. Estado missing no elimina historial. Subir/stage/promote y verificar **nuevo artefacto generado** precede al commit; compensación limpia archivos huérfanos sin borrar evidencia ya comprometida. No existe transacción atómica entre filesystem y PostgreSQL: reconciliación de disponibilidad es explícita.

Para comparar una misma imagen: filtrar identidad/`input_sha256`, mostrar checkpoint/input_contract/clase/salida/config/background, y agrupar métodos. Dos heatmaps con distinta clase o distinta región crop no son una comparación controlada. Un PNG de mapa cuantizado no permite recuperar atribuciones originales. La UI diferencia disponible, legacy incompleto y archivo ausente; nunca genera XAI como efecto secundario de GET.

### Evaluación cuantitativa y revisión

`xai_quantitative_evaluations` propone estabilidad (perturbaciones/semillas y registro espacial), faithfulness (p.ej. deletion/insertion con baseline documentado), localización (ROI/segmentación anotada por especialista y versión congelada) y concordancia (par de evidencias compatible; no prueba de corrección clínica). Guarda nombre/versión de métrica, protocolo y hash, seed, n, valor finito o NULL con razón, referencia y detalles persistentes. No imponer [0,1] a toda métrica XAI: algunas son distancias o signed correlations. La referencia de anotación incluye versión y manifiesto congelado para sobrevivir edición posterior.

El servicio deberá exigir misma imagen, clase, salida, coordenadas y protocolo compatible para concordancia; para estabilidad documenta transformación inversa y referencia. Estas validaciones científicas multientidad se prueban con fixtures; el DDL garantiza existencia y dominios, no suficiencia metodológica. No se afirma que dichas métricas estén implementadas hoy.

Cuatro objetos distintos: explicación generada; evaluación cuantitativa; interpretación científica escrita; validación del especialista sobre la interpretación. Roles actuales autorizan acciones, sin crear ni modificar usuarios/roles en esta etapa. Se registra competence_snapshot, razón y autor; nunca inferir autorización por tener una cuenta.

## 8. Dataset físico, modelo y publicación

AP: versión `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`, TRAIN 22.180, val 2.693, TEST 2.685, total 27.558. Identidades y assignments son autoridad. `dataset_split_images` tiene 55.116 filas de **dos raíces**, no el doble de población. La raíz antigua presenta 22.046/2.756/2.756; no debe usarse como sustituto del split oficial.

DP: corregir `dataset_browser.dataset_summary/counts_from_rows`: devolver `scientific_summary` por versión y `physical_roots[]` por dataset_dir, cada una con su metadata/conteos; parámetro root explícito para detalle físico. Agrupar `(dataset_id,dataset_dir,split_name,class_name)` antes de sumar y comprobar suma de clases; nunca sobrescribir clases con `=` mientras se agregan dos raíces. La API de imágenes de inventario sigue mostrando ambas procedencias, sin crear FK científicas para 55.116 filas ni alterar rutas/materializaciones. DatasetBrowser gobernado ya usa versión/estadísticas; UploadedPredictions/Deployments necesitan etiqueta de origen físico.

Publicación incorpora la FK `(model_version_id,training_run_id) → model_versions(id,training_run_id)` reutilizando `uq_model_versions_id_training_run`. Conserva FK versión/artefacto y guards. **AP: TRAIN completed + EVALUATE completed**, sin nuevo gate recall, XAI, calibración o calidad explicativa. Las nuevas restricciones de evaluaciones v2 ordenan linaje de resultados; no deben retroactivamente cambiar `Stage2PublicationService._eligibility`. Si una evaluación legacy no tiene identidad v2 suficiente, su publicación sigue el contrato vigente y no se inventa evidencia.

## 9. Lecturas, índices y experiencia

| Vista funcional | Contrato de lectura |
| --- | --- |
| Resumen experimental | Campaña/miembro/intento/run y estados técnicos; resultados anexos sin inferir completed. |
| Comparador | `vw_v2_model_comparison`, filtros de compatibilidad y keyset por fecha/id; arquitecturas/optimizer/seed explícitos. |
| Entrenamiento | Configuración inmutable + training_history orden phase/epoch + checkpoints/artifacts. |
| Evaluación clínica | Evaluación concreta, tasas nullable, conteos/denominador, threshold/source; split siempre visible. |
| XAI | `vw_v2_xai_comparison`; listado de evidencias primero, artefactos por lote para evitar duplicar paginación por archivo. |
| Frotis/historial | Servicios clínicos actuales, resultado automático separado de review y XAI. |
| Gobernanza | model_versions/lineage/publications; misma elegibilidad funcional. |

No crear materialized views antes de medir. Las tablas consolidadas ya son proyecciones transaccionales. Evitar joins que multipliquen resultados por epoch, artefacto o miembro ensemble; paginar IDs de evaluación antes de agregar. Una consulta de medias por seed debe seleccionar una evaluación por configuración/seed/rol, no promediar todos los reintentos.

EV: cero grupos de índices exactamente duplicados en E10.10.3. Los cuatro pares por prefijo (artifacts/type, predictions/case_type, runs/type, history/run) no autorizan DROP. No indexar automáticamente las 109 FK sin prefijo completo. Mantener índices parciales de exclusión/idempotencia y UNIQUE que respaldan FK compuestas.

DP adicional: sustituir `idx_training_history_run_phase_epoch` no único por el índice de `uq_v2_epoch(run_id,phase,epoch)`. Es la misma cobertura de claves y añade una garantía de identidad; no conservar ambos. Precheck de duplicados en copia y adaptación del writer son obligatorios. El índice estrecho `idx_training_history_run_id` continúa como candidato por prefijo, sin retiro aprobado por falta de uso.

DP: índices nuevos justificables por contrato: `(dataset_version_id,comparison_contract_hash,split,created_at,id)` para cohortes y paginación; `(input_sha256,input_contract_hash,model_version_id,method,generated_at,id)` para comparar XAI de la misma entrada; `(evaluation_id,method)` para detalle. UNIQUE de epochs y padres XAI protegen identidad, no sólo rendimiento. Índices legacy GIN de runs se conservan mientras se leen snapshots; su retiro exige corpus de consultas y medición sintética. Candidatos Top-N TRAIN/publicación de E10.10.3 siguen pendientes, sin promesa de velocidad ni índices automáticos sobre todas las FK.

## 10. Criterios de evaluación de decisiones

C1 comparación; C2 recuperación métrica; C3 reconstrucción experimental; C4 interpretación frotis; C5 XAI; C6 FastAPI–React; C7 experiencia sin pérdida de integridad.

| Decisión | C1 | C2 | C3 | C4 | C5 | C6 | C7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Configuración/evaluación tipadas | Sí | Sí | Sí, identidad congelada | Contexto del modelo | Version/checkpoint | DTO estable | Cohortes explícitas |
| Consolidar matriz/reportes | Sí | Una fuente | Conserva conteos/origen | Métricas interpretables | FN/FP vinculables | Dos lecturas derivadas | Sin sobrescritura |
| Mantener seis tablas técnicas | Reintentos identificados | No mezcla intentos | Fencing/recuperación | Evita ambigüedad de ejecución | Evidencia rastreable | Estados fiables | Fallo visible |
| Reutilizar clínica | No mezcla experimento/inferencia | Probabilidades propias | Linaje modelo | Cadena existente completa | Por predicción/crop | Menos duplicación | IA separada de revisión |
| XAI reproducible | Comparación controlada | Calidad explicativa separada | Seed/entorno/inputs | No valida diagnóstico por sí sola | Núcleo del diseño | Métodos/artefactos tipados | Limitaciones visibles |
| Un schema, nueva baseline | Instalación repetible | Objetos completos | Historia archivada | Guards preservados | Nuevos objetos incluidos | Contrato versionado | Menos canales operativos |

## 11. Riesgos y aprobación

1. Aprobar proyección nullable v2 manteniendo payload/hashes v1 y definir DTO de compatibilidad; es la incompatibilidad científica más concreta.
2. Aprobar consolidación física de confusion_matrices/classification_reports y cambio de identidad del reporte por clase; no cortar escritores antiguos antes de adaptar todas las rutas.
3. Aprobar ocho entidades nuevas, JSON residual de snapshots y conservar un schema. No aprobar generaciones XAI ni algoritmos nuevos por aprobar su modelo de datos.
4. Aprobar estrategia de baseline independiente y adopción sólo sobre copia con equivalencia; un stamp no sustituye validación.
5. RA: equivalencia de typmods/ACL, clientes externos, cobertura de escritores dinámicos y rendimiento no medido se verifican en E10.10.5–9. Datos legacy ambiguos se bloquean, no se completan con supuestos.
6. RA: hashes de configuración conservan representaciones canónicas originales; serializar JSONB de vuelta a texto puede cambiar hashes. No reescribir evidencia v1.
7. RA: eventos aceptados antes de model_version finalizada requieren checkpoint identificado y FK de versión nullable en evaluación, con linaje vía TRAIN; no inventar versión antes de completion. Evidencia XAI reproducible requiere versión real y espera su existencia.
8. RA: aceptación en DB no garantiza archivo disponible. El esquema registra estado y hash; disponibilidad física requiere reconciliación futura sin regenerar entradas protegidas.

Los detalles de DDL y pruebas son verificables estáticamente; no se certifica que la baseline futura ejecute hasta probar Ruta A y B en PostgreSQL aislado. La aprobación de diseño no autoriza cutover ni ejecución sobre la base operativa.

## 12. Referencias técnicas y entregables

El DDL conserva 27 vistas actuales y añade cinco (dos sustituyen tablas MERGE y tres son proyecciones v2), total 32. La revisión final de objeto/semántica se registra en el plan de implementación.

Las FK/UNIQUE respaldan relaciones; los CHECK no sustituyen validaciones entre filas. La documentación PostgreSQL explica también que NULL puede satisfacer un CHECK, por lo que se combina con NOT NULL cuando corresponde. [PostgreSQL 17: constraints](https://www.postgresql.org/docs/17/ddl-constraints.html).

Alembic autogenerate requiere revisión y no cubre todos los objetos de este esquema; funciones, triggers y vistas se incorporan explícitamente. [Alembic: autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html).

- [Inventario y matriz de migración completa](e10_10_4_schema_matrix.csv).
- [Normalización y contratos](e10_10_4_jsonb_normalization.md).
- [DDL conceptual completo — NO EJECUTAR](e10_10_4_target_schema.sql).
- [Modelo ER](e10_10_4_er_diagram.md).
- [Baseline y transición](e10_10_4_alembic_strategy.md).
- [Dependencias y cambios API/React](e10_10_4_dependency_matrix.md).
- [Secuencia E10.10.5–E10.10.9](e10_10_4_implementation_plan.md).

### Manifiesto de documentos obligatorios leídos

| Archivo | Líneas | SHA-256 documental |
| --- | ---: | --- |
| `revision-bd-malaria.md` | 431 | `6a7fadafc6308c6d3bced2df6db14d00dbaec58775c33b7379b409c6add5874f` |
| `e10_10_1_baseline.md` | 1461 | `be6e45d356b5e93e8977a36da8017be9f0a34440f3eb0446f3c8abad637db4d8` |
| `e10_10_1_baseline.json` | 75912 | `ace0f14461eb84ef4d66f438aa571e408403e621e1f8bb5cc4f8fb0014792594` |
| `e10_10_2_schema_ownership.md` | 439 | `f6756de0b4a0542ee088b412e47dac12311922669e06eb47f17524bf738630a5` |
| `e10_10_2_obsolete_candidates.md` | 160 | `4de47ac6c1a036b4d52c0bf3b511dfa69b41403c8e1db93ae054d25af7424b6a` |
| `e10_10_3_integrity_performance.md` | 511 | `b5a6f976778c9c1b9df4dd0d2836e03e914dc2436cbfaa99e023498074fe7012` |
| `e10_10_3_findings.json` | 12475 | `5247653b9e3cce4bad46fd859c9884196245c9eadde04c194743756acc4614c8` |
| `e10_10_3_migration_proposal.md` | 131 | `c889b97b6e880dc47a34ba10584b122b1254436e6bf8171e91e6bc57227183f4` |

**E10.10.4 — DISEÑO POSTGRESQL V2 COMPLETADO, PENDIENTE DE APROBACIÓN.**

## Enmienda A-01 aprobada — 2026-09-29

**A-01 RESUELTA POR DECISIÓN ARQUITECTÓNICA — E10.10.5A PUEDE REANUDARSE.** Autorización explícita del usuario, limitada a diseño, baseline y validación estática; no autoriza B ni cutover. El texto anterior conserva la decisión original. Sus hashes y la definición original de evaluations están en [e10_10_5a_design_before_a01.json](e10_10_5a_design_before_a01.json); el bloqueo original se conserva en [e10_10_5a_initial_block.md](e10_10_5a_initial_block.md).

- `evaluations.split` admite `external` además de los tres splits oficiales. `external_validation` permanece intacto en el dataset protegido; no se crea un alias ni mapping automático.
- Ámbito (`split`), población (`population_hash` y manifiesto), origen (`dataset_origin_id`, `dataset_origin_role` y evidencia de procedencia), protocolo (`protocol_hash/version/snapshot`) y finalidad (`purpose`) son conceptos independientes.
- External exige `purpose=complementary`, `evaluation_role=external_complementary`, manifiestos de población/procedencia recuperables con SHA-256 y FK a la PK existente `(dataset_version_id,dataset_id,role)` del origen registrado en `dataset_version_sources`, sin añadir UNIQUE al dominio protegido. La versión evaluada puede diferir de la versión de entrenamiento; se conserva íntegro el linaje TRAIN/checkpoint/modelo. No se crean versiones ni fuentes ficticias para completar esa FK.
- `source_kind=external_record` identifica nuevas entradas externas; `legacy` permite adopción con evidencia suficiente. No se hace pasar una entrada externa por evento E10 ni por assessment cuyo contrato actual sólo admite splits oficiales.
- Se prohíbe usar external como calibración, selección de checkpoint/modelo, VALIDATION sustitutiva o agregado TEST oficial. Los roles y la finalidad lo impiden en evaluations, el par de calibración exige val, y `vw_v2_model_comparison` sólo contiene train/val/test. `vw_v2_external_evidence` expone evidencia complementaria sin agregación, con población, protocolo y procedencia. El catálogo pasa de 32 a **33 vistas**; mantiene **103 tablas**.
- `run_clinical_metrics.split_name` sigue representando `external`; su trigger lo deriva de la evaluación externa trazada. Se conservan el lector/escritor legacy en la aplicación operativa. Adaptar esos escritores al contrato transaccional v2 corresponde a E10.10.5E: esta enmienda no afirma compatibilidad binaria de INSERT antiguos que carezcan de evaluation_id.
- La existencia de un URI/hash no certifica disponibilidad o validez científica del manifiesto. La adopción abortará sin mapping si falta evidencia; los servicios deben verificar procedencia y políticas de selección. No se modifican imágenes, asignaciones ni hashes históricos.


## Resolución B-01 — roles de instalación v2 (2026-09-29)

Por decisión arquitectónica aprobada, el propietario/migrador se denomina `capstone_v2_migrator` y el runtime independiente `capstone_v2_runtime`. Ambos carecen de SUPERUSER, CREATEDB, CREATEROLE, REPLICATION, BYPASSRLS y memberships. El runtime no dispone de DDL, TEMP, TRUNCATE ni escritura en alembic_version o modificación directa de los ledgers protegidos. Sólo se provisionan en el destino aislado autorizado para B. La evidencia de los nombres reservados anteriores se conserva en el informe B-01.
