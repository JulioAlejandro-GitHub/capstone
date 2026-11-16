from pathlib import Path
import json,csv,re,hashlib,subprocess,datetime
B=Path(__file__).resolve().parents[1];R=B.parents[2]
def add(name,text):
 p=B/name;s=p.read_text();p.write_text(s+'\n'+text.strip()+'\n')
def read(n):return json.loads((B/'evidence'/f'{n}.json').read_text())
add('CAPSTONE_P3_04_INFORME_GENERAL.md','''## Hallazgo de acceso funcional confirmado al cierre

**HECHO VERIFICADO:** el catálogo actual de esta página excluye las tres modalidades BiomedCLIP. `CatalogService.models` conserva solo `model_type=classification` en vista traceability; PostgreSQL registra zero_shot, linear_probe y fine_tuning para esas modalidades. La respuesta real ofrece tres familias CNN, 44 TRAIN elegibles y capacidad máxima 4. La disponibilidad de código/evaluaciones BiomedCLIP no significa que puedan seleccionarse en esta UI. Este límite es prioritario para P3. [Respuesta](evidence/catalog_response.json), [matriz y alcance](CAPSTONE_P3_04_COMPARACION_Y_COBERTURA.md).

Hay además tres recorridos celulares existentes para el TRAIN principal, todos sobre EVALUATE VAL `811dd584-bb41-453d-b7e9-26bd61c9990a`. Sus ocho pasos por célula describen activaciones guardadas y no el TEST solicitado. No se recalcularon. [Resumen sin binarios embebidos](evidence/saved_traces_summary.json).
''')
add('CAPSTONE_P3_04_ARQUITECTURA_Y_FLUJOS.md','''## Admisión y catálogo comprobados

La respuesta de `/models?view=traceability&comparison=true` se reprodujo desde CatalogService con transacción de solo lectura. Ofrece custom_cnn (16 elegibles/23 TRAIN), DenseNet121 (14/18) y VGG16 (14/18), máximo cuatro participantes. El filtro classification excluye las tres modalidades BiomedCLIP que usan otros model_type. Esto es una limitación de acceso real de la página; los runtimes Torch y sus registros siguen existiendo. EXPLAIN no bloquea admisión: TRAIN y EVALUATE acreditados sí. [Respuesta](evidence/catalog_response.json).
''')
add('CAPSTONE_P3_04_RUN_00b8d407.md','''## Evidencia complementaria de archivo y recorridos

**HECHO VERIFICADO:** se inspeccionó `config.json` y `metadata.json` del ZIP Keras del checkpoint elegido, sin cargar el modelo ni deserializar pesos. El manifiesto interno y firmas de capas se conservan en [checkpoint_zip_inspection.json](evidence/checkpoint_zip_inspection.json); la comparación por fase distingue los flags trainable del checkpoint y del ajuste fino. Se inventariaron 28 checkpoints de época presentes en la carpeta del TRAIN; solo el elegido se verificó contra hash registral. Las épocas restantes no sustituyen la selección operativa.

Arquitectura dispone de tres recorridos celulares ya guardados: muestras `29e26d17-5e6d-5fb3-b493-bb9bc4a5a07a`, `a39fc40f-7738-5c90-8dc6-c3b31856b360`, `db9fbbd3-e025-524a-ad04-ba5cde0e2f3d`. Todos citan EVALUATE VAL `811dd584-bb41-453d-b7e9-26bd61c9990a`, el mismo SHA de checkpoint y `consistent=true`, con ocho pasos cada uno. Se verificó lectura del JSON y su hash actual; no se repitió el forward para recertificar consistent. No se presentan como activaciones de las células TEST. [Resumen](evidence/saved_traces_summary.json), [inventario](csv/local_auxiliary_files.csv).

**Versiones XAI/REPRESENT observadas:** LIME0.2.0.1, SHAP0.49.1, sklearn1.9.1, scikit-image0.26.0, umap-learn0.5.12, Pillow12.3.0, matplotlib3.11.2 según identity.code.inference_packages de los respectivos intentos; no todas figuran en el TEST anterior. La fuente es cada ejecución, no la versión actual de una página web.
''')
rows=list(csv.DictReader((B/'csv/principal_predictions.csv').open()));fn=next(x for x in rows if x['outcome']=='FN')
add('CAPSTONE_P3_04_RUN_00b8d407.md',f'''### Ejemplo FN explícito reproducible

Muestra `{fn['sample_id']}` → paciente `{fn['patient_id']}` → `{fn['relative_path']}`. Real1, score `{fn['raw_score']}`, t `{fn['threshold']}`, pred0. SHA original `{fn['sha256']}` coincide con el archivo leído en original_verification.json. La misma muestra conserva su fila de REPRESENT si se localiza por sample_id en case_related_scores.json; no se obtiene su fila usando el orden de una página UI.
''')
add('CAPSTONE_P3_04_ANALISIS_POR_OPCION.md','''## Anexo: recorrido de activaciones, gráficos y fórmulas adicionales

La opción Arquitectura incluye medidas que no deben confundirse con XAI de gradientes o con PCA/CKA. `activation_trace_compute.statistics` devuelve mínimo, máximo, media, desviación estándar poblacional (`values.std()`, ddof0) y fracción activa `mean(values>0)` del tensor. Para mapas espaciales selecciona hasta16 canales por mayor media espacial, orden descendente; no muestra todos los canales ni los elige por importancia clínica. Los vectores tienen valores destacados e histograma `numpy.histogram` con bins del módulo. Los PNG de canales se normalizan para visualizar y son resúmenes del tensor, no las matrices originales completas.

`ScoreBar`: pista 0–1, score y marca threshold; usa clamp para dibujo. `StepProfile`: x pasos/capas, y fracción activa 0–100 %, hasta dos células con colores current/compare. Esa fracción depende de activación/normalización y no mide utilidad de una capa ni cantidad de parásito. `VectorHistogram`: bins de valores frente a cantidad de neuronas, altura normalizada al máximo visual; conteos originales en tooltip. `MiniCurves`: loss y val_loss a escala local con checkpoint. El visor permite pasos anterior/siguiente, reproducción animada, click de bloque, escala de mapas, canal y comparación con otra célula guardada; las animaciones navegan datos guardados y no ejecutan el modelo.

Para el principal hay tres recorridos **VAL**, ocho pasos cada uno, consistencia registrada true. Los resúmenes y hashes se leyeron, no se ejecutó forward. El selector de evaluación del repositorio de recorridos es independiente del de Desempeño clínico: hay que conservar attempt/split al interpretar el vínculo. Una barra de score de un recorrido zero-shot representa score relativo de prompts aunque un componente genérico use la palabra «Probabilidad»; no acredita calibración.

Fuentes: [activation_trace_compute.py](../../../backend_api/app/services/activation_trace_compute.py#L153), [TraceCharts.tsx](../../../frontend/src/components/model-architecture/TraceCharts.tsx#L5), [ActivationTracePanel.tsx](../../../frontend/src/components/model-architecture/ActivationTracePanel.tsx#L134), [saved_traces_summary.json](evidence/saved_traces_summary.json).

**Acceso BiomedCLIP:** las fichas de runtime/arquitectura anteriores describen capacidad de código y evidencia registral. La página actual no ofrece esos tres modos porque el catálogo traceability filtra model_type=classification. No se ha verificado una visualización interactiva BiomedCLIP desde este selector; matriz07 conserva esa limitación explícita.
''')
# Add curated function semantics alongside the complete machine-readable index.
curated=[
('compute_clinical_metrics','Calcula','y_true,y_scores,threshold','sklearn y cocientes binarios; score float32','dict clínico; llamador persiste','Callbacks y evaluación; no todas las claves se grafican'),
('compile_binary_model','Configura','Keras model,learning_rate,optimizer_config','BCE y métricas Keras','model compilado','TRAIN; no es cálculo final sklearn'),
('collect_predictions','Calcula / adapta','modelo,dataset,threshold','inferencia de validación en callback; evento de scores','samples y métricas','Selección/calibración y eventos por época'),
('find_threshold_for_target_recall','Calcula','labels,scores,target_recall,min_specificity,beta','grid de scores únicos, filtros y orden lexicográfico','dict threshold y tasas','TRAIN y auto threshold; no escribe solo por llamarlo'),
('verify_rows','Valida / calcula','identity,rows','población exacta, reconstruye decisiones, hash filas','verification con métricas; TEST amplía campos','attempt verification; hashes VAL preservados'),
('metric_dto','Lee / transforma','row run_clinical_metrics','alias a nueve indicadores y undefined_reason','DTO clínico','ScientificReportService→ClinicalMetrics'),
('assessment_metrics','Lee / valida','connection,selection','intento/identity/TRAIN/split/checkpoint/estado','clinical desde verification.metrics','No recalcula métricas faltantes'),
('checkpoint_evidence','Valida / transforma','record,run_id','coherencia metadata epoch/phase/ownership','DTO file_availability not_checked','Curvas/arquitectura; no verifica archivo'),
('validate_samples','Valida / calcula','samples,t,expected','reaplica >=, unicidad, finitud y matriz','indexed,counts,issues','Consenso, rechaza contradicciones'),
('consensus','Calcula','populations,thresholds,filters,pagination','intersección, categorías, acuerdo, overlap,oracle','dict de población+tabla paginada','ConsensusResults; no ensemble'),
('KerasRuntime.represent','Extrae','samples','forward de GAP y salida en el mismo grafo','features float32,scores','represent_reserved; no se ejecutó aquí'),
('project','Calcula','features,spec,seed','PCA full centrado≤50; UMAP2D sobre features','pca,pca_variance,umap','REPRESENT escribe4arrays; no se volvió a ajustar'),
('linear_cka','Calcula','X,Y alineados','centrado y normas Frobenius','float o None','cka_matrix; sin kernelRBF ni archivo'),
('representation_evidence','Lee / valida','repo,connection,selection','coincidencia exacta de intento y SHA/bytes/shape','DTO y embeddings cargados','ScientificRepresentations'),
('compute_gradcam_artifacts','Calcula','model,image,class,layer,invert,preprocess','gradientes→media→suma→ReLU→normalize→resize','heat,overlay,layer','KerasRuntime.explain; no persiste por sí sola'),
('KerasRuntime.explain','Calcula / delega','sample e identity.explanation','GradCAM/LIME/GradientExplainer sobre checkpoint','heat,overlay,result','execute_reserved→save_artifacts'),
('OpenCLIPRuntime.explain','Calcula / delega','sample y spec','LIME o expectedgradients por chunks100','map/overlay/meta','No Grad-CAMViT'),
('attribution_overlay','Visualiza / transforma','rgb,heat','abs y normalize;0.6RGB+0.4color','RGB float','LIME/SHAP overlay; signo perdido'),
('save_artifacts','Persiste archivos','root,target,heat,overlay','creación exclusiva NPY/PNG,fsync,link yhash','payload path/bytes/SHA/IDs','BD registra después; no se ejecutó'),
('normalize_keras','Calcula estructura','runtime records,family','aplano grafo,formas,pesos por reglas','layers,blocks,phases,paramcounts','ArchitectureDetail; sin leer pesos'),
('VitStructureService.read','Lee / genera caché','base,input_size','lectura porSHA o proceso de derivación','estructura JSON','Rama no invocada por efectos'),
('TrainingTrajectoryService.read','Lee / valida / adapta','TRAIN,datasource','scoresVALporépoca; población constante y IDporpathúnico','matriz y samples','Vistascomplementarias; thresholdTRAIN0.5'),
('cluster_interval','Calcula estadística','rows,spec,paired opcional','bootstrap de pacientes completos,percentiles','IC o razones','Subsistema science; no campo delreporte clínico'),
('curveSummary','Calcula resumen','CurveEvidence','conteo fases ygap a checkpoint','KPIs','No clasifica sobreajuste automáticamente'),
('consensusFilterParams','Adapta','MRTcolumnfilters','normaliza label/sample/rangos a request','paramsbackend','No filtra solo página'),
('ProjectionChart','Representa','run,projection,colorBy','agrupa coords persistidas porclase/outcome','scatter ypin','No ajusta PCA/UMAP ni deriva etiqueta descore redondeado')]
add('CAPSTONE_P3_04_CATALOGO_FUNCIONES.md','## Fichas semánticas de funciones centrales\n\n| Función | Tipo de operación | Entradas | Algoritmo / fórmula | Salida / persistencia | Consumidor / límite |\n|---|---|---|---|---|---|\n'+'\n'.join('| '+' | '.join(x)+' |' for x in curated)+'\n\nLos campos completos de archivo/línea, controles, referencias a pruebas y consumidores textuales permanecen en functions.csv. Para las funciones runtime, describir su cálculo no significa que se ejecutaran durante la auditoría. Las fichas05 y06 contienen fórmulas y ejecuciones verificadas.')
# Reproducibility README.
(B/'README.md').write_text('''# CAPSTONE-P3-04 — Índice de reproducibilidad

Auditoría local del 16 de noviembre de 2026 (America/Santiago), datasource `malaria`, ruta `http://localhost/modelo-ia/analisis`. Solo lectura científica y documentación. El UUID solicitado es un **attempt EVALUATE TEST**; su TRAIN es `87b3eff7-e09a-41c8-945d-bf31b3541adb`.

## Documentos

1. [Informe ejecutivo y científico](CAPSTONE_P3_04_INFORME_GENERAL.md).
2. [Arquitectura y flujos](CAPSTONE_P3_04_ARQUITECTURA_Y_FLUJOS.md).
3. [Catálogo de funciones y líneas](CAPSTONE_P3_04_CATALOGO_FUNCIONES.md).
4. [Datos y artefactos](CAPSTONE_P3_04_DATOS_Y_ARTEFACTOS.md).
5. [Análisis de las siete opciones y matemáticas](CAPSTONE_P3_04_ANALISIS_POR_OPCION.md).
6. [Caso principal 00b8d407](CAPSTONE_P3_04_RUN_00b8d407.md).
7. [Comparación y cobertura por modalidad](CAPSTONE_P3_04_COMPARACION_Y_COBERTURA.md).
8. [Hallazgos y recomendaciones](CAPSTONE_P3_04_HALLAZGOS.md).
9. [Evidencia para P3 y rúbrica](CAPSTONE_P3_04_EVIDENCIA_PARA_P3.md).

## Evidencia entregada

- `sql/`: SELECT dentro de transacción READ ONLY REPEATABLE READ; esquema, claves, vistas/triggers, identidades, intentos, épocas, resultados y ejemplos de linaje.
- `csv/`: funciones, fuentes, endpoints, hashes de código local/contenedor, inventario físico completo del registro, archivos auxiliares del caso, métricas/scores/épocas principales, mapas XAI, CKA y cobertura por modalidad.
- `figures/`: curvas, confusión y proyecciones ya persistidas del principal. Son gráficos derivados de auditoría, no capturas UI.
- `evidence/`: respuestas reales de servicios, capturas PostgreSQL, cálculos independientes, resúmenes de archivos y scripts. Se conservan filas/metadata, no pesos de modelos ni grandes artefactos duplicados.
- `evidence/manifest.json`: SHA-256 de documentos/scripts/CSV/SQL/JSON/figuras entregados (excluye a sí mismo). Identifica contenido, no firma clínica.

## Reproducir desde la raíz del repositorio

No iniciar contenedores ni ejecutores nuevos. Requiere los contenedores existentes `capstone_db` y `capstone_backend`. Los extractores pasan `default_transaction_read_only=on`, timeout60s y entregan SQL con BEGIN READ ONLY. Credenciales quedan dentro del contenedor y no se imprimen. Cada consulta tiene snapshot propio; no se afirma consistencia temporal global entre todas las capturas.

```sh
python3 docs/audits/CAPSTONE_P3_04/evidence/extract.py
python3 docs/audits/CAPSTONE_P3_04/evidence/case_extract.py
python3 docs/audits/CAPSTONE_P3_04/evidence/lineage_extract.py
python3 docs/audits/CAPSTONE_P3_04/evidence/session_extract.py
python3 docs/audits/CAPSTONE_P3_04/evidence/comparison_extract.py
python3 docs/audits/CAPSTONE_P3_04/evidence/contracts_extract.py
python3 docs/audits/CAPSTONE_P3_04/evidence/replay_services.py
python3 docs/audits/CAPSTONE_P3_04/evidence/local_inventory.py
python3 docs/audits/CAPSTONE_P3_04/evidence/checkpoint_inspection.py
python3 docs/audits/CAPSTONE_P3_04/evidence/catalog_sources.py
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/capstone_p3_04_mpl malaria_dl_local_project/.venv-metal/bin/python -B docs/audits/CAPSTONE_P3_04/evidence/compute.py
PYTHONDONTWRITEBYTECODE=1 malaria_dl_local_project/.venv-metal/bin/python -B docs/audits/CAPSTONE_P3_04/evidence/contrast.py
```

Estos comandos actualizan **solo evidencia y derivados dentro de la auditoría**; en particular compute/contrast no importan runtimes ni ajustan PCA/UMAP: leen arrays y calculan métricas/CKA/elección de threshold en memoria. Ningún cálculo escribe umbrales productivos. `replay_services.py` invoca directamente módulos de lectura y únicamente arquitectura Keras principal; no llama estructura ViT, generación, activation POST/DELETE, login ni endpoints con auditoría de escritura. Verificar que el código actual siga manteniendo esos contratos antes de repetir después de cambios del sistema.

La generación documental es separada: write_reports.py → write_options.py → write_remaining.py → finish_docs.py. `catalog_sources.py` regenera el índice nominal y finish_docs añade fichas curadas. No ejecutar finish_docs varias veces sin regenerar antes los documentos, pues agrega anexos. La reproducción de datos puede conservar los informes originales y dejar un nuevo snapshot aparte si se necesita comparación temporal. Las capturas contienen paths y pseudónimos de pacientes del dataset: conservar el alcance local previsto para estos documentos.

## Comprobaciones realizadas

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend_api:malaria_dl_local_project malaria_dl_local_project/.venv-metal/bin/python -B -m pytest -p no:cacheprovider malaria_dl_local_project/tests/test_clinical_metrics.py backend_api/tests/test_representation_generation.py -q
node --test frontend/tests/scientific-results-v2.test.mjs frontend/tests/scientific-review-ui.test.mjs frontend/tests/vit-architecture.test.mjs
```

Resultado: 15 pruebas Python y 15 frontend aprobadas; logs en evidence/tests_python.txt y evidence/tests_frontend.txt. No se escribieron pruebas productivas ni se ejecutaron pruebas de persistencia contra la BD científica. Las pruebas de contratos/dobles no validan fidelidad XAI ni diagnóstico.

Reproducción numérica principal: métricas coinciden exactamente, hash de checkpoint y mapas/matrices seleccionados coincide, cuatro originales coinciden. 35.341 referencias inventariadas por stat; 43 artefactos hash comprobados y cuatro originales aparte. 5.386 archivos de un EXPLAIN ajeno al principal ausentes en rutas comprobadas. El resto de hashes globales no se comprobó.

## Límites y cierre

Se documentaron las siete opciones, funciones, contratos reales, tablas/artefactos, fórmulas, figuras y el caso solicitado con sus identidades reales. Las ausencias se distinguen de capacidades no implementadas. Hay matrices por seis modalidades y preguntas científicas, contraste con P3-03 y criterios P3.

No se verificó navegador, bundle servido, transporte HTTP autenticado, todas las variantes de renderer ni la rama ViT con caché generadora. No se acreditan validación clínica externa, conceptos morfológicos expertos ni sensibilidad por frotis/paciente desde estas métricas celulares. BiomedCLIP tiene motor y evaluaciones pero no aparece en selector actual. El catálogo nominal es estático con límites explícitos, complementado por fichas y replay de servicios; no afirma cobertura dinámica de cada callback o función de dependencias.

No se modificaron código productivo, esquema, registros, umbrales, checkpoints ni selección activa. Las modificaciones previas del usuario en frontend se conservaron. No se requiere aprobación para leer esta evidencia; cualquier implementación de recomendaciones pertenece a otra fase autorizada.
''')
print('Final documentation annexes and README written')
