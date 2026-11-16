from pathlib import Path
import json,csv,re,collections,subprocess,datetime
B=Path(__file__).resolve().parents[1];R=B.parents[2]
def read(n):return json.loads((B/'evidence'/f'{n}.json').read_text())
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(str(x).replace('|','/').replace('\n',' ') for x in row)+' |' for row in rows])
def ref(file,token=None):
 p=R/file;lines=p.read_text().splitlines();line=next((i+1 for i,s in enumerate(lines) if token and token in s),1);return f'[{file}:{line}](../../../{file}#L{line})'
def write(name,title,s):
 (B/name).write_text('# CAPSTONE-P3-04 — '+title+'\n\nFecha: 16 de noviembre de 2026, America/Santiago. Datasource: `malaria`.\n\n'+s.strip()+'\n')
T='87b3eff7-e09a-41c8-945d-bf31b3541adb';U='00b8d407-c672-4b68-9814-53c092d034ba';V='910051e5-a00c-44c4-9d23-77598af470f7';D='b1b39079-658f-4300-b159-52619f981035'
runs=read('runs');a=read('assessments');run=next(r for r in runs if r['id']==T);main=next(r for r in a if r['id']==U);m=read('metric_reproduction');reps=read('representation_reproduction');learning=read('learning_reproduction');inventory=list(csv.DictReader((B/'csv/artifact_inventory.csv').open()));coverage=list(csv.DictReader((B/'csv/modality_counts.csv').open()))
intro=f'''**HECHO VERIFICADO.** El identificador solicitado `{U}` no es una fila de `runs`: es `assessment_attempts.id`, tipo `evaluate`, split **TEST**, estado `verified`. Su identidad es `a981125c-a9b6-4bec-9fb7-2fa52b907147` y su TRAIN es `{T}`. La auditoría conserva el UUID pedido como caso principal y utiliza su TRAIN únicamente para reconstruir el entrenamiento y sus descendientes. Evidencia: [consulta de identidad](sql/principal_identity.sql), [captura](evidence/principal_identity.json), [identidad completa](evidence/principal_full_identity.json).

Convenciones: **HECHO VERIFICADO** = código/registro/archivo observado; **CÁLCULO REPRODUCIDO** = cálculo independiente sobre evidencia existente; **INTERPRETACIÓN CIENTÍFICA** = lectura con límites; **HIPÓTESIS** = explicación no demostrada; **PENDIENTE** = no comprobado. La existencia de código, de un registro `verified` y de un archivo con checksum coincidente son tres evidencias diferentes.
'''
write('CAPSTONE_P3_04_INFORME_GENERAL.md','Informe ejecutivo y científico',intro+f'''
## Resultado científico principal

**CÁLCULO REPRODUCIDO.** VGG16, SGD, semilla 47, checkpoint época 1, threshold `{m['threshold']}`: N=2.685 células de **20 identidades de paciente**. Matriz TEST `[[1145,223],[47,1270]]`. Sensibilidad **96,4313 %**, especificidad **83,6988 %**, precision **85,0636 %**, accuracy **89,9441 %**, F1 **0,90391459**, F2 **0,93921018**, ROC-AUC **0,97887832**, Average Precision (campo PR-AUC) **0,98082304**. La reproducción independiente de todos los conteos y tasas tiene diferencia máxima **0** frente a lo persistido. [Resultados](evidence/metric_reproduction.json), [scores](csv/principal_predictions.csv).

**INTERPRETACIÓN CIENTÍFICA.** Este TEST no alcanza la sensibilidad objetivo del 98 %. El umbral calibrado en VALIDATION sí alcanzó allí 98,0377 %, con especificidad 82,0175 %. No se debe transferir ese cumplimiento a TEST ni presentar una estimación por célula como sensibilidad de diagnóstico por paciente/frotis. No hay validación clínica externa acreditada por estas capturas.

## Capacidades realmente observadas

- Aprendizaje: 28 épocas registradas; 13 base y 15 fine-tuning. El checkpoint conservado pertenece a la fase base. El monitor explícito `val_f2_parasitized` tiene prioridad sobre el nombre de política `auc_with_min_recall`. Loss BCE y F2 cumplen funciones distintas.
- Clínico: el servicio atribuye métricas al intento seleccionado, con split, threshold y checkpoint. El frontend no vuelve a calcular sus tasas. En intentos VAL antiguos pueden faltar F1/AUC/BA por contrato, aun existiendo scores para calcularlas.
- Errores: matriz y scores reconciliados, filtros globales antes de paginar, acuerdo y errores compartidos sobre intersección de muestras. El oracle es una cota descriptiva, no un ensemble.
- XAI principal: nueve EXPLAIN verificados —tres métodos en tres células TEST—, 18 archivos mapa/overlay. Las magnitudes resaltadas no validan conceptos morfológicos ni diagnóstico.
- Arquitectura: VGG16 registrada por TRAIN, 15.241.025 parámetros; 526.337 entrenables en base y 7.605.761 en fine-tuning. No se cargó el checkpoint para contar parámetros: se reconstruyeron desde registros de configuración.
- Representaciones: matriz principal `(2685,512)` con PCA, varianza y UMAP persistidos e íntegros. Dos componentes explican 39,7531 %; 50 explican 87,9255 %. CKA se calcula al consultar, alineando sample_id.
- Trazabilidad: se reconstruyeron imagen, paciente, split, checkpoint y resultado para FN y células XAI. Los identificadores de checkpoint de TRAIN y assessment se derivan por mecanismos distintos y apuntan al mismo hash físico; no son una FK intercambiable.

## Hallazgos prioritarios

1. **HECHO VERIFICADO:** hay 5.386 referencias de archivos XAI que no se resuelven físicamente en las rutas comprobadas, todas de EXPLAIN `ceaa29af-cb60-4be2-8a67-01b9c9382cda`, TRAIN `bbbd5b60-afaa-4034-a504-a60ed642aafe`, marcado `verified`. Esto no afecta a los archivos comprobados del caso principal. No se infiere cuándo o por qué dejaron de estar disponibles.
2. **CÁLCULO REPRODUCIDO:** embeddings TEST de VGG16-SGD y VGG16-Adam semilla 47 son idénticos elemento a elemento y tienen CKA=1; sus errores difieren. **INTERPRETACIÓN:** la extracción es anterior a la cabeza y ambos checkpoints conservan el backbone base congelado. CKA no puede detectar diferencias aprendidas solo por la cabeza.
3. **HECHO VERIFICADO:** GET arquitectura ViT puede cargar una base y persistir una caché estructural. Se inspeccionó, pero no se ejecutó esa rama. Los botones generar XAI/REPRESENT/recorrido tienen efectos y no se usaron.
4. **HECHO VERIFICADO:** `runs.fine_tuning_start_epoch=13` en el principal; el primer evento `phase=fine_tuning` tiene época global 14. La gráfica usa los eventos. Documentar diferencia de índice/frontera, sin asignarle una época inexistente.
5. **HECHO VERIFICADO:** el servicio de métricas exige `population_hash` no nulo para destacar máximos conjuntos, pero la proyección de EVALUATE independiente devuelve `population_hash=None`. Sus métricas pueden estar disponibles sin highlights comparativos.

## Alcance y evidencia de verificación

Capturas PostgreSQL nuevas de esta fecha; no se reutilizan resultados históricos como si fueran actuales. El snapshot de cada consulta es REPEATABLE READ READ ONLY; no se afirma una única transacción global para todos los archivos. Inventario: 86 TRAIN, 2.425 épocas; 141 EVALUATE verificados, 77 EXPLAIN verificados y 2 fallidos, 6 REPRESENT verificados; `training_history=0`, `predictions=0`, `xai_evidence=0`. Las tablas vacías no significan ausencia de resultados: assessments y eventos contienen evidencia. [Conteos](evidence/table_counts.json), [matriz](csv/modality_counts.csv).

Se reprodujeron directamente los seis módulos del servicio de reporte, preflight y arquitectura Keras en el backend Docker, con transacción de solo lectura, sin el transporte HTTP. Los 59 archivos cotejados inicialmente entre workspace y backend coinciden; el inventario final amplía esa comprobación en [runtime_source_identity.csv](csv/runtime_source_identity.csv). No se afirma prueba de navegador ni render de la aplicación desplegada. Las figuras son derivadas de auditoría, no capturas UI.

15 pruebas Python de métricas/contratos REPRESENT y 15 pruebas frontend existentes pasaron. Las pruebas usan contratos/dobles y no certifican inferencia real, fidelidad XAI o validación clínica. [Logs](evidence/tests_python.txt), [frontend](evidence/tests_frontend.txt). No se modificó código productivo ni registros científicos; las modificaciones previas del usuario se conservaron.

## Lectura recomendada

El documento 05 explica matemáticas y siete opciones; el 06 reconstruye el caso principal; el 07 separa comparaciones y cobertura; el 08 detalla riesgos y recomendaciones. El catálogo 03 y sus CSV permiten navegar por funciones y líneas. El README contiene reproducción y límites del cierre.
''')
endpoints=[
('GET','/models?view=traceability&comparison=true','CatalogService.models','catálogo, elegibilidad, capacidad'),
('GET','/runs/training-summaries','list_training_summaries','selector TRAIN, limit100'),
('GET','/runs/{id}/lineage-children','get_lineage_children','slots y EXPLAIN, paginación'),
('POST','/models/comparison/preflight','ScientificPreflightService.read','identidades explícitas, dictámenes y procedencia'),
('POST','/models/comparison/report','ScientificReportService.read','module catalog/curves/metrics/consensus/questions/representations'),
('GET','/assessments','AssessmentReadService.list','TRAIN, campaña, offset, limit, view'),
('GET','/assessments/{attempt_id}','AssessmentReadService.detail','identidad congelada, estado y verificación'),
('GET','/assessments/{attempt_id}/results','AssessmentReadService.payloads','scores/resultados; sample_id[]'),
('GET','/assessments/{attempt_id}/artifacts','AssessmentReadService.payloads','metadatos paginados; no certifica existencia'),
('GET','/artifacts/file','artifact_file','original, training o assessment; valida pertenencia/integridad'),
('GET','/runs/{run_id}/architecture','ModelArchitectureService.read','Keras registros; ViT caché derivable, efecto potencial'),
('GET','/runs/{run_id}/activation-traces','ActivationTraceService.catalog','catálogo de recorridos guardados'),
('GET','/runs/{run_id}/activation-traces/candidates','ActivationTraceService.candidates','FN/FP/etc según evaluación elegida por repo'),
('GET','/runs/{run_id}/activation-traces/{sample_id}','ActivationTraceService.read','lee recorrido JSON; 404 ausente'),
('POST / DELETE','/runs/{run_id}/activation-traces[/{sample_id}]','ActivationTraceService.create/delete','genera o elimina; NO ejecutado'),
('GET','/runs/{run_id}/training-trajectories','TrainingTrajectoryService.read','trayectorias de scores VAL; utilizado por vistas complementarias'),
('GET','/explain-generations[ /executor]','ExplainService.state / executor','estado y disponibilidad ejecutor'),
('POST','/explain-generations/prepare ; /explain-generations','prepare / generate','preparación y ejecución; NO ejecutados'),
('GET / POST','/representation-generations','RepresentService.state / generate','consulta / reserva ejecución; POST NO ejecutado'),
('GET','/runs/{run_id}/scientific-results?view=traceability','ScientificReadService.read','contrato general; no sustituye report modules')]
mat=[('Aprendizaje','TrainingCurves','report module=curves','comparison_epochs / checkpoint_evidence','train_execution_records, run_configurations, artifacts, runs','checkpoint referenciado','lectura épocas, gap','líneas TRAIN/VAL'),('Clínico','ClinicalMetrics','report module=metrics','metrics / assessment_metrics / metric_dto','evaluations, run_clinical_metrics, assessment_identities/attempts','ninguno para tasas ya calculadas','tasas persistidas','barras, matrices, sensibilidad/especificidad'),('Errores','ConsensusResults / ConsensusSamplesTable','report module=consensus','prediction_population / validate_samples / consensus','assessment_results, dataset_split_assignments; eventos VAL','original celular','intersección, decisiones y conteos','distribución, heatmaps, tabla'),('XAI','PersistedXAI / GeneratedXAIComparison','assessments; artifacts/file','AssessmentReadService; scientific_artifact','assessment_identities/attempts/results/artifacts','map.npy, overlay.png','atribuciones generadas antes; UI compone','original, mapas y superposición'),('Arquitectura','ArchitecturePanel / ArchitectureDetail','runs/{id}/architecture; activation-traces','normalize_keras / normalize_biomedclip','train_execution_records runtime, run_configurations, model_versions, artifacts','caché estructura/recorridos cuando existen','formas y conteo de pesos','SVG, tablas, fórmulas'),('Representaciones','ScientificRepresentations','report module=representations','representation_evidence / cka_matrix','assessment_*','embeddings.npy,pca.npy,pca_variance.npy,umap.npy','lectura PCA/UMAP; CKA al consultar','scatter, varianza, matriz CKA'),('Trazabilidad','PreflightEvidence','comparison/preflight','ScientificPreflightService.read','dataset_*, runs, artifacts, assessments, evaluaciones','referencias; no todos se abren','validaciones de comparabilidad','dimensiones, dictámenes, referencias')]
write('CAPSTONE_P3_04_ARQUITECTURA_Y_FLUJOS.md','Arquitectura y flujos',intro+'''
## Flujo completo

```mermaid
flowchart TD
  UI[React ModelComparison datasource malaria] --> CAT[Catálogo TRAIN y selección en contexto React]
  CAT --> SLOT[TRAIN VAL / EVALUATE VAL / EVALUATE TEST]
  SLOT --> PREF[POST preflight: procedencia y comparabilidad]
  SLOT --> REPORT[POST report: lectura por módulo]
  REPORT --> RO[Transacción PostgreSQL READ ONLY]
  RO --> EVENTS[train_execution_records: épocas y selección]
  RO --> HIST[evaluations y run_clinical_metrics]
  RO --> AS[assessment_identities y assessment_attempts]
  AS --> RESULTS[assessment_results: scores y sample_id]
  AS --> AR[assessment_artifacts: mapas y matrices]
  AR --> FS[Archivos host; resolución Mac/Docker; SHA-256]
  FS --> REP[PCA/UMAP persistidos; CKA calculado al leer]
  RESULTS --> ERR[Decisión score >= threshold; consenso e intersección]
  EVENTS --> CURVES[Curvas TRAIN/VAL]
  REPORT --> VIEW[Recharts / Material React Table / SVG / imágenes]
  ERR --> VIEW
  CURVES --> VIEW
  REP --> VIEW
  PREF --> TRACE[Trazabilidad UI]
  GEN[Acciones generar XAI / REPRESENT / recorrido] -. fuera de la auditoría .-> EXEC[Ejecutor host o Docker]
  EXEC -. resultados futuros .-> AS
```

Los arcos punteados describen capacidades de ejecución; no se activaron. Docker mantiene frontend/API/BD; los TRAIN/assessments auditados registran ejecución local Python en Mac. PostgreSQL es fuente registral y los binarios viven en el host. El mapeo de rutas no convierte un archivo registrado en archivo existente.

## Matriz de las siete opciones

'''+table(['Opción','Frontend','Endpoint','Función backend','Tablas','Artefactos','Cálculos','Gráficos'],mat)+'''

## Endpoints efectivos y efectos

'''+table(['Método','Ruta relativa al backend','Función','Contrato / efecto'],endpoints)+f'''

Referencias de ruta: {ref('backend_api/app/routes/scientific_preflight.py','def scientific_report')}; {ref('backend_api/app/routes/assessments.py','def results')}; {ref('backend_api/app/routes/artifacts.py','def artifact_file')}; {ref('backend_api/app/routes/model_architecture.py','def model_architecture')}; {ref('backend_api/app/routes/explain_generation.py','def generate')}; {ref('backend_api/app/routes/representation_generation.py','def generate')}. Inventario adicional de declaraciones exactas, parámetros y decoradores en [endpoints_static.csv](csv/endpoints_static.csv); los prefijos del router deben anteponerse a declaraciones locales.

## Contratos, permisos y errores

`ScientificReportRequest` extiende PreflightRequest: selección explícita training_run_id, evaluación histórica o assessment identity_id+attempt_id, split/checkpoint opcionales; module obligatorio. offset≥0, limit1–100; categorías cerradas, label0/1, rangos de score por índice0–9, búsqueda≤200 caracteres y orden validado. No se elige una evaluación porque su UUID se parezca al TRAIN.

Preflight/report requieren RUNS_READ y permisos MODELS_READ, DATASETS_READ, PREDICTIONS_READ, ARTIFACTS_READ; principal local inseguro rechazado 401, insuficiencia403. UUID no encontrado404, identidad/split/checkpoint contradictorios422, SQL fallido503. Header `Cache-Control: private, no-store`. El permiso de generar explicaciones es separado del de leer. El replay directo verifica servicio/datos, no RBAC ni proxy HTTP.

`read_only_transaction` configura READ ONLY, statement timeout10s, lock timeout2s y rollback al terminar; módulos complejos usan REPEATABLE READ. La extracción SQL de auditoría tiene 60s por sentencia. Referencia {ref('backend_api/app/db.py','def read_only_transaction')}.

## React, estado y procedencia

Ruta {ref('frontend/src/router.ts',"comparison:")}; entrada {ref('frontend/src/pages/ModelComparison.tsx','function ComparisonPage')}. Datasource se pasa desde App y se propaga al cliente API; solo `malaria` está habilitado en backend. TRAIN seleccionados se conservan en ComparisonSelectionProvider (memoria, no se inventa persistencia URL/localStorage). `seccion`, `muestra`, `modelo`, `evaluacion` son parámetros de navegación; evaluación global por defecto TEST, con fallback TEST→VAL→TRAIN y override por tarjeta. Los IDs seleccionados no se derivan del parámetro `modelo`, que controla la arquitectura visible.

Hay una pestaña adicional **Resumen**, además de las siete solicitadas. Los paneles se montan al primer acceso y se mantienen ocultos después; filtros y caché en memoria sobreviven al cambio de pestaña. useComparisonEvidence controla consulta, estado de carga, error/reintento y cache key (datasource, identidades, revisión). Cambiar usuario/permisos/datasource/conjunto TRAIN remonta la sesión. No hay sustitución de resultados científicos por mocks en este flujo identificado. Valores ausentes se muestran como «Sin evidencia», «—», missing/incompatible; no se rellenan curvas faltantes.

Tipos: `types/scientificReport.ts`, `scientificPreflight.ts`, `scientificRead.ts`, `modelArchitecture.ts`, `api.ts`; clientes en {ref('frontend/src/services/api.ts','getComparisonReport')}. Hooks `useComparisonCatalog`, `useComparisonSelection`, `useComparisonTrainingSummaries`, `useComparisonEvidence`, `useExplainExecutor`. La galería XAI agrega métodos/célula mediante `xai/comparison.ts`; no recalcula atribuciones.

Visualización: Recharts (líneas, barras, scatter), Material React Table (filtros/orden/paginación), SVG y JSX propios para arquitectura y fórmulas. Los gráficos de arquitectura incluyen dibujos pedagógicos y bloques de referencia ViT identificados, no mediciones de activación salvo recorrido persistido. Exportación: copiar ID/enlace/comandos y descargar binarios mediante artefactos; no se encontró un exportador integral de las siete opciones. Los CSV de esta auditoría son productos nuevos de documentación.

## Precedencia y cachés

Curvas: eventos `kind=epoch` → normalización numérica/validación de eje → UI; no fallback a training_history. Configuración: run_configurations primero, si no existe configuración resolved de runs.execution_parameters. Checkpoint: contexto e10 en runs referencia artifacts, último evento selection define época/fase. Histórico clínico: evaluations+run_clinical_metrics; independiente: assessment verification.metrics, sin completar medidas ausentes silenciosamente. REPRESENT: último intento verified que coincide exactamente en población ordenada, decisión, split, purpose, checkpoint, hash, dataset y especificación; luego SHA y shape físicos. XAI: métodos elegidos explícitamente por tarjeta; puede admitir distinto split/checkpoint y advertirlo. CKA no se guarda: depende de la comparación solicitada.

La arquitectura ViT es la excepción a una lectura sin escritura de archivos: {ref('backend_api/app/services/vit_structure.py','def read')} deriva caché por hash cuando falta. Se evitó ejecutar esa rama. Recorridos se generan mediante POST y se consultan mediante GET; no se generaron durante esta auditoría.
''')
# Case technical dossier
principal_ass=[x for x in a if x['training_run_id']==T]
case_rows=[(x['kind'],x['id'],x['identity']['split'],x['state'],x['sample_count'],(x['identity'].get('explanation') or {}).get('method','—')) for x in principal_ass]
write('CAPSTONE_P3_04_RUN_00b8d407.md','Caso principal 00b8d407',intro+f'''
## Identidad experimental reconstruida

'''+table(['Campo','Valor'],[
('UUID solicitado / naturaleza',U+' / assessment_attempts, EVALUATE TEST'),('TRAIN asociado',T),('Modelo',run['model_id']+' / VGG16 / tensorflow-keras / transfer learning'),('Versión lógica E5','e8f94b69-1e92-4092-994b-898d6c66dd31, en train_execution_sessions.verification.artifact; no fila model_versions de este TRAIN'),('Campaña','eb7ae3da-c954-4f2f-8d19-0398824089c5 / all 1'),('Dataset','3f4058c7-5671-4c2f-a089-d1482d5661f4'),('Versión dataset','d8c0cab5-09dd-597f-9de7-7ca01aee2ec2'),('Materialización','e15dc166-1c4b-558e-b77b-727b1783430c'),('Semilla / batch','47 / 32'),('Optimizador','SGD LR0.001, momentum0.9, nesterov false, weight_decay null; fine-tuning LR0.0001'),('Regularización','Dropout0.5 en cabeza; L2=0; VGG16 sin BatchNorm'),('TRAIN estado y duración','completed; 2166.370553 segundos'),('TRAIN fechas UTC',run['started_at']+' → '+run['finished_at']),('TEST fechas UTC',main['started_at']+' → '+main['finished_at']+'; 26.095353 segundos'),('Épocas','máximo100+20; ejecutadas28; mejor1; 13 base +15 fine_tuning'),('Monitor efectivo','val_f2_parasitized max; early stopping paciencia12, min_delta0.0001, restore_best_weights true'),('Política nominal','auc_with_min_recall; sobreescrita para ranking por explicit_monitor; policy_satisfied=false en selección'),('Checkpoint físico','epoch_1.keras; 63.161.620 bytes'),('SHA-256','b26f6e2c66fd5356028ba41eaee603f0c88a2a925b39cb6b21b0fafd79aa24fa'),('artifact_id en artifacts','5406dae8-6a82-568c-a0e9-9ecff89d5f4e'),('checkpoint_artifact_id assessment','3bbb3405-1db1-5811-b4b5-f208f9e64503 = UUIDv5(version_id, e5-selected-checkpoint)'),('Threshold selección / operativo','0.5 / 0.25116682052612305 calibrado en VAL'),('Dominio score','probability_parasitized, sigmoid; calibrated_score=None; comparación >='),('Framework observado','Python3.12.13, TF2.17.1, Keras3.15.1, NumPy1.26.4; Apple GPU/Metal1.2.0, Darwin arm64')])+f'''

Fuentes: [runs.json](evidence/runs.json), [sesiones](evidence/training_sessions.json), [calibración estructurada](evidence/principal_calibration_record.json), [inventario físico](csv/artifact_inventory.csv). Los timestamps se conservan en UTC para reproducción; en Chile eran 10:55–11:31 para TRAIN y 19:37–19:38 para TEST el 29 de octubre de 2026. La configuración de planificación registra Python3.12.14/SQLAlchemy2.0.52; runtime registra Python3.12.13/SQLAlchemy2.0.53. No mezclar entorno planeado y ejecutado. PYTHONHASHSEED registrado42 y seed de modelo47 son mecanismos distintos; no demuestran por sí solos igualdad bit a bit entre hardware.

## Aprendizaje

**HECHO VERIFICADO:** 28 eventos válidos, sin duplicación del eje en el servicio. Época1 seleccionada por F2 VAL0.9477320516671673 a threshold0.5; no por mínimo loss. TRAIN loss0.3414160 y VAL loss0.1831485 en esa época. Mínimo VAL loss0.138228 en época16; última época28: TRAIN loss0.1397561, VAL loss0.1515374. Configuración pedía100+20, no significa que se ejecutaran120.

**INTERPRETACIÓN CIENTÍFICA:** el ascenso de val_loss desde época16 a28 mientras disminuye TRAIN loss es compatible con deterioro de generalización de pérdida/confianza en ese tramo; no prueba causalidad ni diagnóstico global de sobreajuste. El checkpoint que realmente se evaluó es anterior. La brecha VAL–TRAIN en época1 es negativa y no prueba ausencia de sobreajuste (augmentación/dropout y modos de evaluación difieren). No inferir sobreajuste únicamente de VAL–TEST.

Reproducir: SQL epochs → eventos del TRAIN → módulo curves → CSV [principal_epochs](csv/principal_epochs.csv); cálculos [learning_reproduction](evidence/learning_reproduction.json), figura [aprendizaje](figures/principal_learning.png). `run_checkpoint_policy` está vacío para este TRAIN; la selección sí existe en eventos y sesión. Primera fase fine_tuning en eventos=14; campo `fine_tuning_start_epoch`=13 conserva una frontera/índice distinto.

## Desempeño clínico y umbral

'''+table(['Métrica TEST','Cálculo independiente'],[(k,v) for k,v in m['computed'].items()])+f'''

**CÁLCULO REPRODUCIDO:** diferencia máxima0 respecto a verification.metrics. [Reproducción](evidence/metric_reproduction.json). NPV calculado en auditoría={m['npv_derived']:.10f}; no es indicador expuesto por esta vista. Matriz [figura](figures/principal_confusion.png). Las métricas son celulares y no tienen IC en el reporte principal.

Calibración independiente en memoria sobre los scores VAL del checkpoint seleccionado: 2.683 candidatos únicos incluyendo0/0.5/1; maximización lexicográfica de especificidad, precision, F2, BA y threshold entre los que satisfacen recall≥0.98. Resultado reproduce t=0.25116682052612305, TN1122, FP246, FN26, TP1299, N2693. A t0.5 VAL tenía TN1272, FP96, FN63, TP1262. Se reducen37 FN a costo de150 FP adicionales en VAL. Este contraste no recalibra ni modifica el umbral operativo. [Reproducción](evidence/threshold_reproduction.json).

## Errores y consenso

47 FN y223 FP, 270 errores. 31 errores con score extremo según definición ≥0.9 al predecir1 o ≤0.1 al predecir0; 118 células a distancia≤0.05 del umbral. No son medidas de incertidumbre calibrada. La galería puede recuperar original y abrir Explicabilidad mediante sample_id. La tabla filtra y ordena globalmente antes de paginar.

Con un único TRAIN no hay consenso entre modelos. Referencias secundarias VGG16-Adam47 y DenseNet121-Adam47 se comparan en documento07, nunca se agregan al resultado principal. Los scores originales quedan en [CSV](csv/principal_predictions.csv), incluidos los47 FN.

## Explicabilidad

Nueve intentos verificados, sobre **tres células únicas** TEST; no equivale a explicar2.685. Grad-CAM, LIME1000 y SHAP1000/clase1 para cada una. SHAP utiliza una célula uninfected TEST distinta como background; su sample_id no sustituye al target. Los18 mapas/overlays existen, se hash-verificaron y sus9 mapas numéricos son finitos. [Estadísticos de mapas](csv/principal_xai_maps.csv). Cobertura3/2685=0.1117318 %. No hay validación morfológica experta acreditada por estas ejecuciones.

'''+table(['Tipo','Attempt','Split','Estado','N','Método'],case_rows)+f'''

## Arquitectura

Entrada RGB200×200×3; VGG16 preprocess ImageNet BGR en loader, no aplicar además rescale por intuición. Backbone ImageNet, cinco bloques convolucionales/pooling → GAP512 → Dense1024 ReLU → Dropout0.5 → Dense1 sigmoid. 15.241.025 parámetros: base526.337 entrenables y14.714.688 congelados; fine-tuning7.605.761 entrenables y7.635.264 congelados. El checkpoint seleccionado es **fase base**, aunque se consulten estados entrenables de fine-tuning en Arquitectura.

Reproducción desde `train_execution_records kind=runtime record_key=configuration` y `normalize_keras`; resultado [architecture.json](evidence/architecture.json), fuentes [runtime_records](evidence/runtime_records.json). Sin inferencia ni deserialización del modelo.

## Representaciones

REPRESENT `d6f269de-ba63-4a17-9df8-3bd2ce1871b2`, misma población/decisión/modelo TEST que el intento solicitado. Embeddings2685×512 float32; PCA2685×2; varianza50; UMAP2685×2. Las cuatro matrices tienen SHA/bytes concordantes y son finitas. Sin normalización L2 en Keras; media de norma91.94138, no equiparar directamente con encode_image_l2 de OpenCLIP.

PCA2 explica39.753147 %, PCA50 explica87.925476 %, 25 componentes alcanzan80 %. PCA se ajustó una sola vez al generar REPRESENT; la auditoría lee sus matrices, no las vuelve a ajustar. [Reproducción numérica](evidence/representation_reproduction.json), [figuras](figures/principal_representations.png). CKA con otro RUN solo aparece como comparación separada en documento07. No hay clustering aprendido, TCAV ni comparación de todas las capas implementados en este contrato REPRESENT.

## Trazabilidad: cinco pruebas concretas

1. Métrica: intento `{U}` → identidad `a981125c-a9b6-4bec-9fb7-2fa52b907147` → verification.metrics.recall y 2.685 assessment_results → 1270/(1270+47). El objeto `evaluations` histórico de TRAIN no es la fuente de ese TEST.
2. Predicción celular: sample `014d8b8e-3397-5ae8-88fd-8cef2a2d6c64`, real0, score0.6909072995185852, pred1 a t0.25116682. `dataset_source_records.id` → clinical_identity `d4b8e72c-782e-570d-a4df-5e6c618b9a35` (`C139P100ThinF`) → assignment TEST de versión d8c0… → imagen `test/uninfected/C139P100ThinF_IMG_20151005_182822_cell_142.png`, SHA `9155ff4224d8b5e413cfaff4e9a70785fd78a2156b9d440c0773e8ca130d3301`.
3. FN: los47 joins reales con fuente/paciente/split están en [principal_sample_lineage.json](evidence/principal_sample_lineage.json). Un FN se selecciona determinísticamente como primera fila label1/pred0 de principal_predictions; su imagen y SHA se verifican en [original_verification](evidence/original_verification.json). No se inventa un frotis físico completo a partir del nombre del crop.
4. Archivo XAI: intento Grad-CAM `4b5fe111-681f-4d68-a36f-4a96c949abd2` → sample014d8… → dos assessment_artifacts map/overlay → paths/hash en inventario → mismo checkpoint y target clase1 de su identidad. sample SHAP background0005c2… es referencia distinta.
5. Representación: mismo sample_id → assessment_results del REPRESENT d6f269… → result.row → fila de embeddings/pca/umap; artefactos poblacionales se registran con sample_id de la primera muestra por contrato, **no significan que solo esa muestra tenga representación**.

Cadena de checkpoint común: sesión TRAIN.verification.artifact.version_id e8f94… → UUIDv5 lógico3bbb… en assessment → path y SHA b26f…; proyección registral artifacts5406… → misma ruta,63.161.620 bytes y hash comprobados. La versión E5 no requiere una fila model_versions nueva en este flujo; tabla vacía para el TRAIN no es pérdida automática de linaje. {ref('malaria_dl_local_project/src/malaria_dl/assessment/lineage.py','def resolve')}.

## Límites específicos

No se ejecutaron modelos, nuevas explicaciones, representaciones ni calibraciones productivas. No se comprobó una cadena hasta imagen de frotis completo ni registro de paciente clínico asistencial; existe identidad PATIENT de origen del dataset. No se acreditan ROI, conceptos expertos, evaluación clínica externa, presupuesto monetario, consumo eléctrico o IC del principal desde esta UI. No hay que escribir «No implementado» para XAI/REPRESENT: ambos tienen evidencia de ejecución para este caso.
''')
