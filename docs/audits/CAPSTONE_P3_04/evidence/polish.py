"""Final editorial pass and concise evidence-backed matrices; only audit outputs."""
from pathlib import Path
import json,csv,re
B=Path(__file__).resolve().parents[1]
def read(n):return json.loads((B/'evidence'/f'{n}.json').read_text())
# Fix joined tokens in prose while retaining paths, identifiers, inline code and URLs.
replacements={
'Evidenciaobservada':'Evidencia observada','nuevosestudios':'nuevos estudios','Noimplementado':'No implementado','sin datos para el RUN⁵':'sin datos para el RUN⁵',
'porarchivo':'por archivo','porpaciente':'por paciente','porhash':'por hash','porcélula':'por célula','porfase':'por fase','porcontenido':'por contenido',
'lossVAL':'loss VAL','scoresVAL':'scores VAL','muestrasVAL':'muestras VAL','métricasVAL':'métricas VAL','métricasTEST':'métricas TEST','curvasVAL':'curvas VAL','enTEST':'en TEST','enVAL':'en VAL',
'TRAINprincipal':'TRAIN principal','TESTprincipal':'TEST principal','casoprincipal':'caso principal','checkpointprincipal':'checkpoint principal','poblacióncomún':'población común',
'capacidadde':'capacidad de','modelosTorch':'modelos Torch','datosTorch':'datos Torch','modoTorch':'modo Torch','REPRESENTTorch':'REPRESENT Torch','REPRESENTTEST':'REPRESENT TEST',
'checkpointbaseépoca':'checkpoint base época ','mismohash':'mismo hash','mismohardware':'mismo hardware','mismas muestras':'mismas muestras',
'No mostrarlascomo0':'No mostrarlas como 0','eventosenfiguras':'eventos en figuras','nosobrescribir':'no sobrescribir','noh ay':'no hay',
'porID':'por ID','stateverified':'state verified','kindepoch':'kind epoch','kindselection':'kind selection','roleoverlay':'role overlay','roleembeddings':'role embeddings','rolepca':'role pca','roleumap':'role umap',
'archive_id':'archive_id','fsync yhash':'fsync y hash','trainablecount':'trainable count','float64≤50':'float64 ≤50',
'catalogo03':'catálogo 03','catálogo03':'catálogo 03','documento07':'documento 07','documento06':'documento 06','documento05':'documento 05','las7opciones':'las siete opciones',
'porarchivo':'por archivo','archivosXAI':'archivos XAI','BinariosXAI':'Binarios XAI','OverlayLIME':'Overlay LIME','porcontenido':'por contenido',
'capade':'capa de','cabezacongelada':'cabeza congelada','backbonecongelado':'backbone congelado','ImageNetcongelado':'ImageNet congelado','featuresidénticas':'features idénticas',
'métodosXAI':'métodos XAI','curvasactuales':'curvas actuales','campeónDenseNet':'campeón DenseNet','principalVGG':'principal VGG',
'configruntime':'config runtime','diferenciaspareadas':'diferencias pareadas','variabilidad entresemillas':'variabilidad entre semillas','renderestructural':'render estructural',
'Unmodelo':'Un modelo','unmodelo':'un modelo','delselectorno':'del selector no','enregistros':'en registros','defrotis':'de frotis',
'loss yval_loss':'loss y val_loss','noopera':'no opera','Npositivo':'N positivo','conteosTEST':'conteos TEST','capasViT':'capas ViT',
'datasetversion':'dataset version','mapasfirmados':'mapas firmados','maps/overlay':'maps / overlay','CHECKPOINTSHA':'CHECKPOINT SHA',
'NoGrad-CAM':'No Grad-CAM','GAPantesde':'GAP antes de ','Dense1024':'Dense 1024','encode_image_l2':'encode_image_l2',
'por defectoTEST':'por defecto TEST','kindruntime':'kind runtime','sample_idancla':'sample_id ancla','PCAvarianza':'PCA varianza',
'comparaciónexploratoria':'comparación exploratoria','validaciónexterna':'validación externa','prevalenciareal':'prevalencia real','densidadpor':'densidad por ',
'cadaRUN':'cada RUN','todoslosRUN':'todos los RUN','todosloscheckpoints':'todos los checkpoints','de60RUN':'de 60 RUN','60RUNcampaña':'60 RUN de campaña',
'noimplementado':'no implementado','sin inferencianueva':'sin inferencia nueva','maximodescriptivo':'máximo descriptivo','hipótesisexpertas':'hipótesis expertas',
'loss_definition':'loss_definition','porlayers':'por layers','shape/bytes/hash':'shape / bytes / hash',
'CNNentexto':'CNN en texto','noinferir':'no inferir','Noafirmar':'No afirmar','selectoractual':'selector actual','fuenteactual':'fuente actual',
'Verified':'Verified','metadatacompleta':'metadata completa','sehash':'se hash','checkpointpor':'checkpoint por ',
'layer/framework':'layer / framework','CODEX':'CODEX',
}
for p in B.glob('*.md'):
 s=p.read_text();chunks=re.split(r'(`[^`]*`|\]\([^)]*\))',s)
 for i,chunk in enumerate(chunks):
  if chunk.startswith('`') or chunk.startswith(']('):continue
  for old,new in replacements.items():chunk=chunk.replace(old,new)
  # Separate clear letter/number transitions without damaging scientific labels or filenames:
  chunk=re.sub(r'(?<=\d)(?=(?:células|épocas|pacientes|referencias|archivos|intentos|positivos|réplicas|familias|modos|matrices|componentes|canales|capas|parámetros)\b)',' ',chunk)
  chunk=re.sub(r'\b(\d+)(TRAIN|EVALUATE|EXPLAIN|REPRESENT|JSON|XAI|RUN)\b',r'\1 \2',chunk)
  chunks[i]=chunk
 p.write_text(''.join(chunks))
# Rewrite the recommendation table with complete words and clear sourcing.
head='''# CAPSTONE-P3-04 — Hallazgos y recomendaciones

Fecha: 16 de noviembre de 2026, America/Santiago. Datasource: `malaria`.

El UUID solicitado es un intento EVALUATE TEST, no un TRAIN. Su TRAIN asociado es `87b3eff7-e09a-41c8-945d-bf31b3541adb`. Las recomendaciones siguientes no se implementaron.

## Hallazgos priorizados

| ID | Prioridad | Evidencia y conclusión | Fuente | Recomendación |
|---|---|---|---|---|
'''
items=[
('H01','Alta','HECHO VERIFICADO: el filtro `model_type=classification` excluye del selector los tres modos BiomedCLIP, aunque tengan evaluaciones.','[Catálogo real](evidence/catalog_response.json); CatalogService.models','Revisar el contrato de admisión en una fase de implementación autorizada.'),
('H02','Alta','HECHO VERIFICADO: EXPLAIN `ceaa29af-cb60-4be2-8a67-01b9c9382cda` está verified y sus 5.386 archivos no se encuentran en las rutas comprobadas.','[Inventario físico](csv/artifact_inventory.csv); [intentos](evidence/assessments.json)','Separar disponibilidad actual de verificación histórica; investigar recuperación sin regenerar silenciosamente.'),
('H03','Alta','CÁLCULO REPRODUCIDO: principal TEST tiene sensibilidad 96,4313 %, 47 FN y 223 FP; no alcanza 98 %.','[Métricas](evidence/metric_reproduction.json)','Mostrar split, población, threshold y checkpoint; no trasladar cumplimiento VAL a TEST.'),
('H04','Media','CÁLCULO REPRODUCIDO: dos VGG tienen embeddings GAP idénticos, pero 48/68 errores exclusivos entre ellos.','[Features](evidence/vgg_embedding_identity.json); [errores](evidence/pairwise_errors.json)','Estudiar también representaciones de cabeza/logits; CKA de GAP no captura toda la adaptación.'),
('H05','Media','HECHO VERIFICADO: GET arquitectura ViT puede iniciar un proceso y guardar caché cuando falta estructura.','backend_api/app/services/vit_structure.py:37','Separar consulta y generación en un cambio futuro; la auditoría evitó esta rama.'),
('H06','Media','HECHO VERIFICADO: checkpoint lógico E5 3bbb… y artifact genérico 5406… tienen IDs diferentes y el mismo archivo/hash.','[Sesiones](evidence/training_sessions.json); [checkpoint](evidence/checkpoint_zip_inspection.json)','Conservar namespaces y comprobar identidad por contenido; no forzar una FK inexistente.'),
('H07','Media','HECHO VERIFICADO: verify_rows amplía F1/BA/AUC/AP solo para TEST; los intentos VAL pueden carecer de esos campos.','malaria_dl_local_project/src/malaria_dl/assessment/contracts.py:203','Mostrar ausencia explícita; no completar resultados históricos con otra evaluación.'),
('H08','Media','HECHO VERIFICADO: assessment_metrics proyecta population_hash=None; la lógica de highlights exige un hash no nulo.','[Respuesta clínica](evidence/report_metrics.json); ScientificReportService.read','Explicar por qué hay métricas disponibles sin destacados comparativos; estudiar el contrato en otra fase.'),
('H09','Media','HECHO VERIFICADO: overlay LIME/SHAP usa magnitud absoluta; el mapa NPY conserva signo.','[Estadísticos XAI](csv/principal_xai_maps.csv); attribution_overlay','Distinguir atribución firmada de intensidad visual; no interpretar azul como contribución negativa automáticamente.'),
('H10','Baja','HECHO VERIFICADO: campo fine_tuning_start_epoch=13; primer evento de esa fase es época global 14.','[Épocas](csv/principal_epochs.csv); [RUN](evidence/runs.json)','Documentar la frontera/índice y usar los eventos al graficar.'),
('H11','Media','HECHO VERIFICADO: texto de REPRESENT describe GAP para todos; runtime OpenCLIP extrae encode_image_l2. No hay REPRESENT Torch persistido en esta captura.','scientific_representations.DEFINITIONS; assessment/openclip.py','Adaptar la definición a layer/framework antes de presentar resultados Torch.'),
('H12','Media','INTERPRETACIÓN CIENTÍFICA: los nueve XAI principales cubren tres células y no acreditan conceptos morfológicos ni validación clínica.','[Identidades](evidence/case_identities.json); [resultados](evidence/case_related_scores.json)','Evaluar fidelidad, estabilidad y ROI/conceptos con especialistas en estudios futuros.'),
('H13','Baja','HECHO VERIFICADO: ModelComparison usa los eventos de época correctos; P3-03 describió otra fuente en RunDetail.','[Curvas actuales](evidence/report_curves.json); informe P3-03','Identificar vista y contrato antes de extrapolar el hallazgo histórico.'),
('H14','Media','HECHO VERIFICADO: tres recorridos principales guardados describen VAL, mientras el intento solicitado es TEST.','[Recorridos](evidence/saved_traces_summary.json)','Conservar intento y split al relacionar activaciones con errores.'),
]
text=head+'\n'.join('| '+' | '.join(row)+' |' for row in items)+'''

Las prioridades expresan riesgo de interpretación o reproducibilidad, no una incidencia clínica demostrada. No se infiere causa de desaparición de archivos ni responsabilidad de un actor. Los archivos y líneas exactas de funciones se localizan en el catálogo de fuentes.

## Contraste con P3-03

P3-03 registró 86 TRAIN, 2.425 épocas y 140 EVALUATE. Esta captura tiene los mismos TRAIN/épocas y 141 EVALUATE: un aumento temporal no es una contradicción. Sus cifras del campeón DenseNet no se transfieren al principal VGG16. El problema histórico de `training_history=0` no impide que ModelComparison lea `train_execution_records` correctamente.

## Estudios futuros propuestos

1. Medir fidelidad y estabilidad XAI con perturbaciones controladas y ROI de especialistas; comparar mapas firmados bajo el mismo target/checkpoint.
2. Preparar conceptos expertos para probes o TCAV: anillo, cromatina, tinción, fondo y negativos controlados. Son hipótesis de estudio, no conceptos ya validados.
3. Comparar GAP, cabeza y logits entre checkpoints y relacionarlos con errores y calidad de imagen.
4. Estimar incertidumbre mediante bootstrap por paciente y diferencias pareadas; separar esa variación de la variabilidad entre semillas.
5. Evaluar generalización externa y unidades clínicas de paciente/frotis; medir prevalencia y costos reales de FN/FP y revisión humana.
6. Analizar cohortes alineadas de optimizadores/semillas con los datos existentes antes de proponer nuevas campañas.

## Límites verificados

No se comprobó navegador, bundle servido, autenticación HTTP ni todas las variantes visuales. El replay usa servicios de lectura y fuentes del contenedor cotejadas por hash. No se ejecutó inferencia ni se generaron explicaciones, representaciones o recorridos.

Se comprobó existencia de 35.341 referencias; 43 artefactos relevantes tienen SHA concordante. Se verificaron aparte cuatro originales y se calcularon hashes de cuatro JSON auxiliares existentes. No se verificó SHA de todos los checkpoints globales. El inventario de funciones es estático y amplio: llamadas textuales y pruebas nominales no certifican ejecución de cada función.

No se acreditan validación clínica externa, ROI morfológicas ni sensibilidad por paciente/frotis desde las tasas celulares. Las capacidades del motor BiomedCLIP y su exclusión de la página se documentan por separado.

**No se implementaron modificaciones funcionales, de esquema, registros, umbrales ni modelo activo.**
'''
(B/'CAPSTONE_P3_04_HALLAZGOS.md').write_text(text)
(B/'CAPSTONE_P3_04_EVIDENCIA_PARA_P3.md').write_text('''# CAPSTONE-P3-04 — Evidencia técnica para P3

Fecha: 16 de noviembre de 2026, America/Santiago. Datasource: `malaria`.

El caso principal es el intento TEST `00b8d407-c672-4b68-9814-53c092d034ba`, asociado al TRAIN VGG16-SGD47 `87b3eff7-e09a-41c8-945d-bf31b3541adb`. Esta matriz prepara evidencia para actualizar P3; no constituye una presentación nueva.

| Criterio | Conclusión sustentable | Evidencia concreta | Fuente y visual | Límite obligatorio |
|---|---|---|---|---|
| I. Problema — 5 % | Apoyo a revisión microscópica con errores identificables y linaje. | Imagen original, score, threshold, checkpoint y XAI del caso celular. | Informe 06, principal_sample_lineage.json; diagrama de trazabilidad. | No atribuir diagnóstico autónomo validado. |
| II. Datos — 15 % | Dataset versionado y partición por paciente. | 22.180 TRAIN, 2.693 VAL, 2.685 TEST; 20 identidades de paciente en TEST principal. | dataset_versions.json, dataset_checks.json, principal_full_identity.json; tabla de splits. | Tres células XAI no representan toda la población. |
| III. Soluciones IA — 30 % | Comparación de aprendizaje, arquitectura, clínica, errores, XAI y representaciones con alcance explícito. | 28 épocas principales; métricas reproducidas; errores pareados y CKA. | Informes 05–07; figuras y CSV de comparación. | BiomedCLIP está fuera del selector actual; CKA de GAP no describe toda la cabeza. |
| IV. Sensibilidad y costos — 30 % | Threshold controla el equilibrio FN/FP; las configuraciones y tiempos están registrados. | En VAL, bajar t de 0,5 a 0,25117 reduce FN 63→26 y aumenta FP 96→246. TEST tiene 47 FN; TRAIN dura 2.166,37 s. | threshold_reproduction.json, runs.json; tabla de tradeoff y confusión. | No hay costo monetario/energético ni IC en esta vista; tiempo no equivale a costo clínico. |
| V. Conclusiones y futuros — 20 % | Separar implementado, ejecutado, recuperable y validado. | Nueve XAI de tres células; cuatro matrices principales; ausencias globales identificadas. | Informes 07–08; matriz de cobertura y manifiesto físico. | No afirmar morfología validada ni cumplimiento de 98 % en TEST. |

## Afirmaciones utilizables con procedencia

- **CÁLCULO REPRODUCIDO:** en 2.685 células TEST de 20 identidades de paciente, VGG16-SGD47 alcanza sensibilidad 96,43 % al umbral 0,25117, con 47 FN y 223 FP. Fuente: [métricas reproducidas](evidence/metric_reproduction.json).
- **HECHO VERIFICADO:** la selección conserva época 1 por F2 VAL a threshold 0,5; después se fija el threshold con VAL y se evalúa ese checkpoint en TEST. Fuente: [sesiones](evidence/training_sessions.json), [calibración](evidence/principal_calibration_record.json). F2 no es la pérdida de entrenamiento.
- **CÁLCULO REPRODUCIDO:** dos VGG tienen GAP idéntico y CKA=1, pero decisiones distintas. Fuente: [features](evidence/vgg_embedding_identity.json), [errores](evidence/pairwise_errors.json). No demuestra igualdad de conceptos médicos.
- **HECHO VERIFICADO:** Grad-CAM, LIME y SHAP existen para tres células principales y sus binarios comprobados son íntegros. Fuente: [mapas](csv/principal_xai_maps.csv), [inventario](csv/artifact_inventory.csv). No acredita localización experta de parásitos.
- **HECHO VERIFICADO:** el motor conserva evaluaciones BiomedCLIP, pero el catálogo de la página ofrece tres familias CNN por su filtro model_type. Fuente: [catálogo real](evidence/catalog_response.json) y CatalogService.models.

## Figuras y contexto obligatorio

[Aprendizaje](figures/principal_learning.png), [confusión TEST](figures/principal_confusion.png), [PCA/UMAP persistidos](figures/principal_representations.png). Son derivados de auditoría, no capturas UI.

Cada uso en P3 debe conservar TRAIN, intento, split, dataset version, checkpoint/hash, threshold y N. Las curvas usan TRAIN/VAL; las proyecciones corresponden a REPRESENT TEST `d6f269de-ba63-4a17-9df8-3bd2ce1871b2`. El checkpoint compartido tiene SHA `b26f6e2c66fd5356028ba41eaee603f0c88a2a925b39cb6b21b0fafd79aa24fa`.

TCAV, anotaciones expertas, validación externa y costos son trabajos futuros propuestos; no se presentan como resultados existentes. No se modificaron documentos P3 anteriores.
''')
print('Editorial pass complete')
