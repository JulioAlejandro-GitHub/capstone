exec((__import__('pathlib').Path(__file__).parent/'write_reports.py').read_text().split("write('CAPSTONE_P3_04_INFORME_GENERAL")[0])
ml='malaria_dl_local_project/src/malaria_dl/'
schema=read('schema');constraints=read('constraints');triggers=read('triggers')
tables=['datasets','clinical_identities','dataset_source_records','dataset_versions','dataset_split_assignments','dataset_materializations','dataset_split_validation_checks','experimental_campaigns','models','runs','run_configurations','train_execution_sessions','train_execution_records','artifacts','model_versions','evaluations','run_clinical_metrics','run_threshold_calibration','run_checkpoint_policy','assessment_identities','assessment_attempts','assessment_results','assessment_artifacts']
rows=[]
for t in tables:
 cs=[c for c in constraints if c['table_name']==t];rows.append((t,', '.join(c['column_name'] for c in schema if c['table_name']==t),'; '.join(c['definition'] for c in cs if 'PRIMARY KEY' in c['definition'] or 'FOREIGN KEY' in c['definition'])))
write('CAPSTONE_P3_04_DATOS_Y_ARTEFACTOS.md','Datos, claves, persistencia y artefactos',intro+'''
## Esquema actual y relaciones verificadas

El esquema procede de information_schema.columns y pg_constraint, no de nombres propuestos en una documentación antigua. Columnas y tipos completos: [schema.json](evidence/schema.json); PK/FK/UNIQUE/CHECK: [constraints.json](evidence/constraints.json); triggers reales: [triggers.json](evidence/triggers.json); vistas: [views.json](evidence/views.json). Su existencia no prueba que todas las reglas se hayan ejercitado en esta auditoría; no se hicieron pruebas de escritura contra la BD científica.

'''+table(['Tabla','Columnas reales','PK y FK declaradas'],rows)+'''

```mermaid
erDiagram
  datasets ||--o{ dataset_source_records : dataset_id
  clinical_identities ||--o{ dataset_source_records : clinical_identity_id
  dataset_versions ||--o{ dataset_split_assignments : dataset_version_id
  dataset_source_records ||--o{ dataset_split_assignments : source_record_id
  dataset_versions ||--o{ dataset_materializations : dataset_version_id
  models ||--o{ runs : model_id
  dataset_versions ||--o{ runs : dataset_version_id
  experimental_campaigns ||--o{ runs : campaign_id
  runs ||--o{ train_execution_records : run_id
  runs ||--o{ train_execution_sessions : run_id
  runs ||--o{ artifacts : run_id
  runs ||--o{ assessment_identities : training_run_id
  assessment_identities ||--o{ assessment_attempts : identity_id
  assessment_attempts ||--o{ assessment_results : attempt_id
  assessment_attempts ||--o{ assessment_artifacts : attempt_id
  evaluations ||--o{ run_clinical_metrics : evaluation_id
```

El diagrama resume claves verificadas; **los IDs dentro de JSON E5/assessment pueden ser identidades lógicas y no FK a artifacts/model_versions**. El linaje por contenido se comprueba en sesión/hash. `dataset_split_images` y `run_dataset_images` pertenecen a contratos adicionales, no sustituyen dataset_source_records para sample_id de assessment. Las tablas `research_subjects`, `scientific_cases`, `blood_samples`, `smear_slides`, `microscopy_images`, `cell_*` representan el flujo de frotis del sistema: no se inventa una unión desde crops experimentales si no existe.

## Catálogo físico completo del registro auditado

[artifact_inventory.csv](csv/artifact_inventory.csv) entrega una fila por referencia: tabla,artifact_id,run_id/attempt_id,sample_id,role,extensión,ruta registrada/ruta resuelta,bytes esperados/observados,SHA esperado/observado,existencia y estado de hash. Son **35.341 referencias**:87 artifacts genéricos y35.254 assessment_artifacts;29.955 archivos existentes en las rutas comprobadas,5.386 ausentes. No se deducen registros a partir de carpetas. SHA comprobado43, coinciden43, otros35.298 quedan not_checked (incluye ausentes y existentes no hasheados). El muestreo de hashing es explícito: checkpoint principal,18 XAI principales y24 matrices de seis REPRESENT. Las cuatro imágenes originales comprobadas están aparte.

`assessment_artifacts`:17.615 mapas.npy,17.615 overlays.png y6×4 matrices. `artifacts`:83 model_checkpoint y4 model_dependency. Las extensiones exactas por fila están en CSV, no se presupone que todos los checkpoints sean .keras. Los paths no se publican por la API de trazabilidad: public_evidence elimina localizadores; este informe local conserva rutas para reproducción.

**Archivos auxiliares locales:** inspección limitada a carpeta TRAIN principal, sus recorridos y caché de estructuras: [local_auxiliary_files.csv](csv/local_auxiliary_files.csv),32 archivos (28 checkpoints.keras,3 recorridos.json,1 estructura.json). Son inventario de carpeta acotada, no todos registrados como artifacts genéricos. Solo el checkpoint seleccionado se hash-comprobó contra registro; no se hashearon1.7GB de checkpoints intermedios ni se copiaron. No se hallaron CSV/logs/historial.json en ese directorio acotado; las épocas y scores están en PostgreSQL. No se afirma ausencia global de esas extensiones en el repositorio.

## Productores, consumidores y función científica

| Tipo | Formato / etapa | Productor | Registro | Recuperación / consumidor | Función / límite |
|---|---|---|---|---|---|
| Checkpoint elegido |.keras o.pt/.bin según modelo; TRAIN/registro |executor TRAIN + finalización E5/e10 |artifacts; train_execution_sessions.verification; contextoruns |lineage.resolve / runtimes; no UI descarga sin contrato |pesos exactos y fase/época; ID lógico≠FK |
| Dependencias base OpenCLIP |JSON/vocab/pesos según rol |registro pretrained |artifacts rolemodel_dependency + version profile |registered_dependencies, runtimeOpenCLIP |transform/tokenización reproducible |
| Historial épocas |JSON payload, no archivo requerido |callbacks/training event recorder |train_execution_records kindepoch |comparison_epochs→TrainingCurves |loss y medidas por época, no TEST |
| Selección/checkpoint |JSON payload |checkpoint_policy / selección |train_execution_records kindselection y sesión |checkpoint_evidence / Curves/Arquitectura |ranking efectivo y warnings |
| Calibración con scoresVAL |JSON payload/result/samples |find_threshold_for_target_recall y TRAIN |event calibration + run_threshold_calibration + evaluations |assessment.threshold auto / reporte |selección de t, no ajuste de probabilidades |
| Scores por célula |JSON fila |prediction / execute_reserved |assessment_results |reportconsensus, tablas, original/XAI |label/score/threshold/predicho con sample/patient |
| Mapa XAI |.npy float32 |runtime.explain→save_artifacts |assessment_artifacts payload |artifacts/file→visorXAI |gradiente/surrogate/expected gradients |
| Overlay XAI |.png uint8 |save_artifacts |assessment_artifacts roleoverlay |ScientificArtifact/GeneratedXAIComparison |representación visual; LIME/SHAP usa abs |
| Embeddings |.npy float32 N×d |runtime.represent→represent_reserved→save_arrays |assessment_artifacts roleembeddings, result.row |representation_evidence→CKA |vector del extractor antes de cabeza |
| PCA coordenadas |.npy float32 N×2 |project(sklearnPCA) |assessment_artifacts rolepca |RepresentationResults |proyección lineal descriptiva |
| PCA varianza |.npy float64≤50 |project |assessment_artifacts rolepca_variance |VarianceChart/KPI |fracción de varianza, no exactitud |
| UMAP |.npy float32 N×2 |project(umapUMAP) |assessment_artifacts roleumap |ProjectionChart |geometría local aproximada |
| CKA |JSON response, sin archivo propio |linear_cka/cka_matrix al leer |no persistencia de par |CkaHeatmap |similitud normalizada sobre intersección |
| EstructuraViT |.json por hash de base |vit_structure_compute |caché filesystemmodel_structure_root |ModelArchitectureService |formas/pesos de estructura, no nuevos pesos |
| Recorrido celular |.json con stats y PNGbase64 |activation_trace_compute/vit_trace_compute, por POST |filesystemactivation_trace_root/TRAIN/sample.json |ActivationTracePanel,TraceCharts |activaciones y score de una célula; no gradiente causal |
| Original celular |.png de materialización |dataset split/materialización |dataset_source_records SHA + assignment |original_sample_image→artifacts/file |crop, paciente fuente, etiqueta y split |
| Figuras de auditoría |.png |evidence/compute.py |solo este directorio |P3/lector informe |derivadas, no capturas UI ni artefactos productivos |

Rutas/productores exactos y líneas en catálogo03. Los CSV conservan identificadores físicos por fila y los JSON originales guardan metadata completa. Extensiones no vistas en el contrato principal (.svg estático, reportesPDF,logs) se distinguen de los SVG calculados en frontend y de evidencia histórica de otros informes.

## Casos de integridad que requieren cuidado

- El EXPLAIN ceaa29af… figura verified pero sus5.386 binarios faltan en ambas resoluciones registradas disponibles; no se regeneran para ocultar la diferencia. Su estado verificaba una ejecución pasada, no presencia continua.
- `file_availability=not_checked` en DTO no significa `available` ni `missing` físico. El inventario comprueba filesystem separadamente.
- Cuatro matrices REPRESENT tienen un sample_id ancla único en artifacts y filas por toda la población en results. No contar cuatro células representadas.
- Version E5e8f94… y checkpoint lógico3bbb… se reconstruyen desde sesión/UUIDv5; artifacts5406… es proyección distinta del mismo archivo b26f….
- Sesiones, identities y resultados pueden conservar distintos git_commit de planificación/ejecución. Para reproducir usar runtime y source_sha más contrato de dependencias; no tomar el README actual como versión histórica.

## Versiones observadas del caso principal

TRAIN y TEST: TF2.17.1,Keras3.15.1,NumPy1.26.4,Python3.12.13. LIME0.2.0.1,scikit-image0.26.0,sklearn1.9.1; SHAP0.49.1; REPRESENT umap-learn0.5.12 ysklearn1.9.1; Pillow12.3.0,matplotlib3.11.2. Fuente: identity.code/inference_packages de cada intento, no versión web actual. El TEST antiguo no guardó sklearn en inference_packages, aunque las ejecuciones XAI/REPRESENT posteriores sí lo hacen; no reescribir retrospectivamente esa ausencia.
''')
# Coverage and explicit comparison answers.
count_table=table(list(coverage[0]),[[row[k] for k in coverage[0]] for row in coverage])
cells=[('Custom CNN','Implementado y verificado','Implementado y verificado','Implementado y verificado','Disponible con limitaciones¹','Implementado y verificado²','Disponible con limitaciones³','Disponible con limitaciones¹'),('VGG16','Implementado y verificado','Implementado y verificado','Implementado y verificado','Implementado y verificado','Implementado y verificado','Implementado y verificado','Disponible con limitaciones⁴'),('DenseNet121','Implementado y verificado','Implementado y verificado','Implementado y verificado','Implementado y verificado','Implementado y verificado²','Implementado y verificado','Disponible con limitaciones⁴'),('BiomedCLIP Zero-shot','Parcial⁵','Parcial⁵','Parcial⁵','Parcial⁵','Parcial⁵','Implementado, sin datos para el RUN⁵','Parcial⁵'),('BiomedCLIP Linear','Parcial⁵','Parcial⁵','Parcial⁵','Implementado, sin datos para el RUN⁵','Parcial⁵','Implementado, sin datos para el RUN⁵','Parcial⁵'),('BiomedCLIP Fine-tuning','Parcial⁵','Parcial⁵','Parcial⁵','Implementado, sin datos para el RUN⁵','Parcial⁵','Implementado, sin datos para el RUN⁵','Parcial⁵')]
questions=[('¿Cuál aprendió mejor?','Respondible parcialmente','Comparar curvas/objetivo/selección de mismas poblaciones; menorloss no equivale a mayor sensibilidad clínica.'),('¿Cuál generaliza mejor?','Respondible parcialmente','TEST disponible, pero necesitaría análisis pareado e incertidumbre; no comparar VAL como TEST.'),('¿Cuál presenta mayor sensibilidad?','Respondible con evidencia actual','Entre intentos ythresholds concretos; sin extrapolación universal ni highlights faltantes.'),('¿Cuál tiene más FN?','Respondible con evidencia actual','Conteos con mismoNpositivo; desigualN impide ranking directo.'),('¿Cuáles cometen mismos errores?','Respondible con evidencia actual','sample_id/label y población reconciliada; tablas pareadas entregadas.'),('¿Cuáles tienen errores complementarios?','Respondible con evidencia actual','Diferencias/intersección yoracle descriptivo; no acredita ensemble útil.'),('¿Qué modelos muestran sobreajuste?','Respondible parcialmente','Curvas temporales ycheckpoint; estadísticas entresemillas necesitan nuevo análisis de evidencia existente.'),('¿Qué regiones usan para justificar decisiones?','Respondible parcialmente','Mapas existentes por target/checkpoint; Requiere nuevas anotaciones de expertos para conceptos morfológicos.'),('¿Qué tan similares son representaciones?','Respondible parcialmente','6REPRESENT, CKA en4TRAIN; faltan restantes; Requiere nuevas evaluaciones REPRESENT para cobertura completa.'),('¿Relación arquitectura,embeddings,errores?','Respondible parcialmente','IDs permiten cruzar; alta CKA con errores distintos demostrado; causalidad requiere experimentos.'),('¿Estabilidad entre semillas/optimizadores?','Requiere nuevos cálculos sobre datos existentes','60RUNcampaña y épocas; separar media/SDentresemillas debootstrap porpaciente. Referencia P3-03,no recertificada aquí.'),('¿Cómo define nuevo experimento?','Respondible parcialmente','Controlar objetivo/población, revisarFN/FP, comparar extractor/cabeza, anotarROI; aprobación posterior antes de nuevas ejecuciones.')]
pairs=read('pairwise_errors');cka=list(csv.DictReader((B/'csv/cka_comparisons.csv').open()))
write('CAPSTONE_P3_04_COMPARACION_Y_COBERTURA.md','Comparación científica y cobertura real',intro+f'''
## Diferencia entre implementación del motor y disponibilidad de la página

**HECHO VERIFICADO:** el catálogo solicitado por la página (`/models?view=traceability&comparison=true`) retorna solo custom_cnn,densenet121,vgg16; capacidad máxima4 y44 TRAIN elegibles (16,14,14 respectivamente). Hay59TRAIN de esas tres familias registrados, pero no todos cumplen admisión. `CatalogService.models(traceability=True)` filtra model_type=classification. PostgreSQL registra BiomedCLIP como zero_shot/linear_probe/fine_tuning, por lo que **sus tres modalidades quedan fuera del selector**, pese a que sus TRAIN/EVALUATE y runtimes existen. [Respuesta real](evidence/catalog_response.json), {ref('backend_api/app/services/catalog.py',"if item['model_type'] == 'classification'")}.

Admisión exige TRAIN completado con checkpoint acreditado y al menos un EVALUATE finalizado verificado con resultados y bindingcoherente. EXPLAIN es opcional. No es prerrequisito de TEST: es la regla específica de admisión al reporte. `eligible` no verifica todos los bytes XAI del host ni establece comparabilidad científica A1–A6. La selección no puede hacer que un modo excluido aparezca por escribir su nombre en el buscador.

## Matriz funcional de siete opciones

'''+table(['Modalidad','Aprendizaje','Clínico','Errores/consenso','XAI','Arquitectura','Representaciones','Trazabilidad'],cells)+'''

1. Custom tiene EXPLAIN verificados y dos fallidos; un intentoverified con5.386 archivos ausentes. No generalizar esa ausencia a todos los RUN.
2. Arquitectura CNN tiene factories,configruntime y renderer; reproducción de servicio completa se ejecutó para VGGprincipal. DenseNet/custom revisados estáticamente y con evidencia, sin render de navegador.
3. Custom solo1REPRESENT; disponibilidad depende del exacto EVALUATE. No toda evaluación tiene PCA/UMAP.
4. Linaje registral presente, pero hashes globales no se comprobaron todos y no hay cadena acreditada a frotis completo.
5. **Parcial por exclusión UI**, no ausencia total de motor. Zero-shot no tiene épocas de entrenamiento por diseño; tiene6EVALUATE y2EXPLAINverificados(LIME/SHAP). Linear/fine-tuning sí tienen curvas y24/25EVALUATE,pero0EXPLAIN y0REPRESENT. Runtimes explain/represent implementados; ausencia de ejecución≠noimplementado. Grad-CAMViT no soportado. ArquitecturaViT tiene derivación/caché potencial y estructura de referencia, no se disparó esa rama.

Clasificación «Implementado y verificado» significa código y evidencia observada para al menos un caso, **no certificación de cadaRUN ni validación clínica**. «No verificable» aplica al render final en navegador y validación experta de todas las modalidades; no se usa para ocultar conteos disponibles. No hay clustering/kernelCKA/TCAV en el contrato REPRESENT de esta pestaña: esos análisis son **No implementado en este módulo**.

## Cobertura registral actual por modalidad

'''+count_table+f'''

Números de épocas son eventos, no muestras. Conteos de intentos no son cantidad de RUNúnicos ni de pacientes. Matrices de6REPRESENT se reparten entre4TRAIN. La disponibilidad física se entrega porarchivo en CSV; no se marca toda una modalidad como completa solo porstateverified.

## RUN principal — resultados propios

VGG16-SGD47 TRAIN `{T}`, TEST `{U}`: N2685,error270,FN47,FP223,recall96.4313 %,specificity83.6988 %,t0.25116682,checkpointbaseépoca1. Sus cifras permanecen separadas de referencias secundarias.

## Referencias secundarias — identidades concretas

- VGG16-Adam47 TRAIN `{V}`, TEST `d1ce1424-c7c3-4ee8-816d-3b91090b42cf`, REPRESENT TEST `2e2c20ac-9014-4e2b-9d6c-7d820bed4f2f`.
- DenseNet121-Adam47 TRAIN `{D}`, TEST `521219d9-7865-428f-9bcf-1491dd754a5e`, REPRESENT TEST `f23e286f-3ce7-473f-8a81-dc2952f0dad0`.

No se eligieron para suplir resultados del principal, que sí dispone de siete familias de evidencia, sino para mostrar comparación pareada/CKA. Cada evaluación usa su propio threshold persistido; no se impone0.5 ni umbral común nuevo.

## Comparación entre RUNs — cálculos nuevos de auditoría

'''+table(['Intentoizq','Intentoder','N','Acuerdos','Erroresizq','Erroresder','Errorescomunes','FNcomunes','FPcomunes','Soloerrorizq','Soloerrorder','Oracle'],[(p['left'],p['right'],p['n'],p['agreement'],p['left_errors'],p['right_errors'],p['shared_errors'],p['shared_fn'],p['shared_fp'],p['left_only_errors'],p['right_only_errors'],p['oracle']) for p in pairs])+'''

**CÁLCULO REPRODUCIDO:** sample_id compartidos2685 y etiquetas coincidentes; sin inferencia nueva. Principal/VGGAdam coinciden2569/2685=95.6797 %, comparten222errores pero48errores son solo del principal y68solo del secundario. Esto demuestra diferencias de decisiones aun con featuresidénticas, no mejora clínica asegurada de combinar modelos. Principal/DenseNet tiene217errorescomunes yoracle91.9181 %, una cota que exige saber qué modelo acierta en cada célula; no es un predictor implementado. [Extracción](sql/comparison_test_scores.sql), [cálculo](evidence/pairwise_errors.json).

'''+table(['TRAINizq','TRAINder','Split','Ncomún','CKAlineal'],[(x['left_train'],x['right_train'],x['split'],x['common'],x['linear_cka']) for x in cka])+f'''

**CÁLCULO REPRODUCIDO:** CKA(TEST,VGGSGD,VGGAdam)=1 y matricesembeddings idénticas con diferencia máxima0. {ref(ml+'assessment/runtime.py','def represent(self, samples)')} extrae GAPantesdeDense1024; ambos modelos pueden aprender cabezas distintas sobre el mismo extractor ImageNetcongelado. El checkpoint de cada uno debe cotejarse para esa interpretación; no concluir que «aprendieron lomismo» globalmente. DenseNet enTEST CKA0.7308257 con ambosVGG; enVAL VGGAdam/DenseNet0.679405. No comparar cifrasVAL/TEST como cambio intrínseco del modelo: cambia población.

## Preguntas del Capstone y estado de respuesta

'''+table(['Pregunta','Clasificación','Evidencia / estudio adicional'],questions)+'''

Ninguna de estas comparaciones demuestra superioridadestadística. Para inferencia clínica pareada se necesita preespecificar hipótesis,población,métricas e incertidumbre porpaciente; comparaciónexploratoria sobreVAL reutilizada para selección no es validaciónexterna. No se propuso cambiar el modeloactivo ni se ejecutó ninguna nueva campaña.
''')
findings=[
('H01','Alta','HECHO VERIFICADO','BiomedCLIP excluido de selector','model_type distinto declassification en los3modos; catálogo real solo3familias','catalog_response.json; CatalogService.models','Revisar contrato de clasificación/presentación en fase autorizada; no reclasificar filas en esta auditoría.'),
('H02','Alta','HECHO VERIFICADO','BinariosXAI ausentes pese averified','EXPLAINceaa29af…,5386referencias no resueltas;TRAINbbbd5…','artifact_inventory.csv; assessments.json','Distinguir disponibilidadactual de verificación histórica; investigar almacenamiento/recuperación, sin regenerar silenciosamente.'),
('H03','Alta','CÁLCULO REPRODUCIDO','Principal no cumple98%TEST','47FN/1317positivos,recall96.4313%;VALsí98.0377%','metric_reproduction.json;threshold_reproduction.json','EnP3 mostrar ambas poblaciones,t ycheckpoint; no afirmar certificación clínica.'),
('H04','Media','CÁLCULO REPRODUCIDO','CKA1no capta diferencia de cabezas','EmbeddingsVGGidénticos,48/68errores exclusivos','vgg_embedding_identity.json;pairwise_errors.json','Comparar también activaciónDense/logits en estudio futuro con capa explícita; no introducir contrato ahora.'),
('H05','Media','HECHO VERIFICADO','GETarquitecturaViT puede escribir','read invoca proceso generador sicachéausente','vit_structure.py;vit_structure_compute.py','Separar generación yconsulta en cambio futuro; enauditoría evitar rama.'),
('H06','Media','HECHO VERIFICADO','IDscheckpointde dos namespaces','3bbb…lógicoE5,5406…artifactgenérico,mismohash','training_sessions.json;artifacts.json;lineage.resolve','Documentar identidadporcontenido yevitar alerta basada soloUUID.'),
('H07','Media','HECHO VERIFICADO','MétricasVALfaltantesporcontrato','verify_rows soloañadeF1/BA/AUC/APenTEST','assessment/contracts.py;reportmetrics','No mostrarlascomo0; cambio futuro exigiría preservar hashes/resultadoshistóricos.'),
('H08','Media','HECHO VERIFICADO','Highlights bloqueados paraassessment','assessment_metrics fija population_hashNone yread exigehashnoNone','scientific_report.py;report_metrics.json','Hacer explícitocomparablefalse; estudiar proyección de evidencia sin fabricarpoblación.'),
('H09','Media','HECHO VERIFICADO','OverlayLIME/SHAPpierdesigno','attribution_overlay usaabs(heat)','runtime.py;principal_xai_maps.csv','EnP3 distinguirmapafirmadodeoverlaymagnitud; noconsiderarazulatribuciónnegativa automáticamente.'),
('H10','Baja','HECHO VERIFICADO','Fronterafine-tuning13/14','runsstart_epoch13; primer eventofine14','runs.json;principal_epochs.csv','Documentaríndices yusar eventosenfiguras; noduplicarépoca13.'),
('H11','Media','HECHO VERIFICADO','DefiniciónREPRESENTsoloCNNentexto','DEFINITIONSafirmaGAP;OpenCLIPruntimeexisteencode_image_l2','scientific_representations.py;openclip.py','Textoporlayer/framework en trabajoautorizado; hoysinREPRESENTTorch persistido.'),
('H12','Media','INTERPRETACIÓN CIENTÍFICA','No hay validaciónmorfológica acreditada','9XAIen3células;sinROI/revisiónespecialista ligada a esosintentos','case_identities.json;case_related_scores.json','AnotarROI/conceptosexpertos;estabilidad/fidelidad;no anunciar diagnósticoporheatmap.'),
('H13','Baja','HECHO VERIFICADO','Curvasactualesusanfuentevigente','ModelComparisonleeepochs;RunDetailhistórico descritoenP3-03leeotratabla','report_curves.json;P3-03','No repetir que todaslascurvasfaltan; identificarvista/contrato.'),
('H14','Media','HECHO VERIFICADO','RecorridosArquitecturausaronVAL','3JSONprincipales refierenattempt811dd…VAL;aná-lisisprincipalTEST','saved_traces_summary.json','Conservar split/intentoalcompararactivaciónyerror;noadscribirrecorridosVALalTEST.')]
write('CAPSTONE_P3_04_HALLAZGOS.md','Hallazgos y recomendaciones sin cambios',intro+'\n## Hallazgos priorizados\n\n'+table(['ID','Prioridad','Tipo','Hallazgo','Evidenciaobservada','Procedencia','Recomendación'],findings)+f'''

Las prioridades describen riesgo de interpretación/reproducción, no una incidencia clínica demostrada. Todos los archivos y líneas se localizan en el catálogo03; números reales provienen de lascapturas enlazadas. No se atribuyen eliminaciones dearchivos a unactor ni se infiere la causa sin historial. Unmodelo fuera delselectorno es unmodelo inexistente.

## Contraste histórico

P3-03:86TRAIN,2425épocas,140EVALUATE ytraining_historyvacía. Capturaactual:86TRAIN,2425épocas,141EVALUATE; no hay contradicción temporal al aumentar intentos. P3-03 revisó un campeónDenseNet diferente y susresultados no se transfieren al principalVGG. La discrepancia de fuentes deépoca deRunDetail permanece como contexto histórico; esta rutaModelComparison recuperaeventoscorrectos. La documentación de política nominalno debe sobreponerse a warningsexplicit_monitor.

## Estudios posteriores propuestos — no ejecutados

1. Fidelidad/estabilidadXAI con ROIexpertas, protocolos de perturbación y comparaciónfirmada entre métodos; no umbralizar colorescomo segmentaciónverdad.
2. Probes o TCAVcon conceptos anillo/cromatina/artefactos/fondo, etiquetas deespecialista y negativoscontrolados; no inferirlosporCKA/UMAP.
3. Representaciones de lacabeza vsGAP, distintas capas y checkpoints en mismas muestras; evaluarrelación de geometría conFN/FP ycalidad.
4. Bootstrap agrupado porpaciente con especificaciónpreelegida y diferenciaspareadas; separarvariabilidad entresemillas devariación demuestras.
5. Generalizaciónexterna, prevalenciareal, sensibilidad porpaciente/frotis, costo operacional deFN/FP yrevisiónhumana; son nuevosestudios, nocálculos inferiblesdeaccuracycelular.
6. Estudiooptimización de60RUN usando cohorts alineadas, configuraciónexacta, misma versión/split y recursos; nocambiarcampeón por máximodescriptivo.

## Límites de la auditoría

No se verificó visualmente el navegador ni la autenticaciónHTTP. El replay directo usa códigodelcontenedor comprobado porhash ylecturasdeBD; no prueba elbundlefrontendservido. Se leyeron archivos existentes sin ejecutarmodelos; loscontroles degeneración/señales animadas no seactivaron. La comprobaciónfísica cubre statde35341referencias yhash43seleccionados más4originales y4JSONauxiliares; noglobalSHA de todosloscheckpoints. Los modelosTorch fueron auditados estáticamente y enregistros, su renderestructural no se invocó por efecto decaché.

No se certifica exactitud de todoh el grafo de funciones por inventarionominal; catálogoautomático y fichashumanas secomplementan, llamadastextuales no son coberturaejecutada. Dependenciasweb oficiales aclaran fórmulas, no certifican versiónejecutada. Estas limitacionesquedan explícitas para evitarcerrar con afirmacionesmayores que la evidencia.

**No se implementó ninguna recomendación ni modificación funcional.**
'''.replace('todoh','todo'))
p3rows=[('I. Problema5%','Apoyo a revisiónmicroscópica conerrores ylinaje, sin diagnósticoautónomovalidado','CasoFNoriginal+score/t+checkpoint+XAI','06;principal_sample_lineage;original_verification','CadenaMermaid ycasocelular','No extrapolar de crop a sensibilidaddiagnóstica porpaciente'),('II. Datos15%','Versiónd8c0…;particiónporpaciente;22180TRAIN/2693VAL/2685TEST','N2685TEST/20pacientes,hashes ychecksreales','dataset_versions,dataset_checks,principal_full_identity','Diagrama version/split ytablaconteos','No presentarselección3XAIcomo muestra representativa'),('III. SolucionesIA30%','Curvas/arquitectura/clínica/errores/XAI/CKA','PrincipalVGGSGD47;comparaciónVGGAdam/DenseNetAdam','05/06/07;CSVpareados;reportservices','learning,confusion,representations','BiomedCLIPexcluidodelselector;CKA1noequivale aaprendizajeidénticoglobal'),('IV. Sensibilidadycostos30%','tVALcalibrado,tradeoffFN/FP;duración yconfiguración','VALFN63→26,FP96→246;TESTFN47;TRAIN2166.37s','threshold_reproduction;run/runtime;metrics','Tablat0.5/vscalibrado ypuntoperativo','Sinmediciónmonetaria/energética niICUI;noasumircostoclínico'),('V. Conclusionesyfuturos20%','Distinguirimplementado/ejecutado/verificado/validado','9XAI/3células,4matrices;ausenciasglobales;hipótesisexpertas','08;inventariofísico;matrizcobertura','Matrizcapacidadyevidencia','No afirmarmorfologíavalidadani98%TEST')]
write('CAPSTONE_P3_04_EVIDENCIA_PARA_P3.md','Evidencia técnica utilizable para P3',intro+'\n## Matriz por criterio de la rúbrica\n\n'+table(['Criterio','Conclusión sustentable','Evidencia concreta','Fuente','Visual apropiada','Límite obligatorio'],p3rows)+'''

## Frases científicas con alcance controlado

- **CÁLCULO REPRODUCIDO:** «En2.685célulasTEST de20identidades depaciente, VGG16-SGD47alcanzó96,43 % desensibilidad al umbral0,25117;hubo47FN y223FP». Fuentes06,CSVprincipal_metrics. No decir que cumple98 % enTEST.
- **HECHO VERIFICADO:** «La selección eligióépoca1 porF2VAL a0,5 ydespués fijóelumbralconVAL;seevaluóesecheckpointenTEST». Fuentestraining_sessions/principal_calibration_record. No llamarF2pérdidadelentrenamiento.
- **CÁLCULO REPRODUCIDO:** «DosVGGtienenGAPidéntico(CKA1) ydecisionesdistintas;laextracciónanterioralacabezanocapturatodalaadaptación». Fuentesvgg_embedding_identity ypairwise_errors. No decir que usan exactamente losmismosconceptosmédicos.
- **HECHO VERIFICADO:** «ExistenGrad-CAM,LIMEySHAPen3célulasdelcasoprincipal;losmapasfueronverificados porhash». Fuentescaseassessments+inventory. No decir que localizanparásitosconvalidaciónexperta.
- **HECHO VERIFICADO:** «LaUIactualofrecetresfamiliasCNN, mientraselmotoralmacenaevaluacionesdetresmodalidadesBiomedCLIPexcluidasporsumodel_type». Fuentescatalog_response,runs,CatalogService.

## Procedencia y preparación de figuras

[Aprendizaje](figures/principal_learning.png), [matrizTEST](figures/principal_confusion.png), [PCA/UMAPpersistidos](figures/principal_representations.png). Son figuras derivadasdeauditoría, no screenshots de laUI. Acompañarlas con TRAIN87b3…,attemptTEST00b8…,datasetversiond8c0…,checkpointSHA b26f…,threshold0.25116682 yN/split. Para curvas, la población esTRAIN/VAL ysemanifiesta aparte;pararepresentaciones,esREPRESENTTESTd6f269….

No se redactó una presentación nueva ni se modificaron documentos P3anteriores. Propuestas de TCAV,validaciónexterna,ROI ycostos se identifican como trabajo futuro y no como resultados existentes.
''')
# Remove cosmetic run-together words in authored compact tables where it improves readability is deferred to final polish.
print('Wrote data, comparison, findings and P3 evidence')
