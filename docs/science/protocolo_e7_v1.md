# Protocolo científico E7

Versión: `capstone_science_e7_v1`.
SHA-256 canónico de la configuración: `7db076d71c2143934f0b3bae47ff253f18d3f65c5c3f8efb2634586acbadbdf2`.

¿Cómo se comparan Custom CNN, VGG16 y DenseNet121 para clasificar células parasitized y uninfected bajo un protocolo común?

## Población, hipótesis y alcance

La unidad de predicción es una imagen de célula; el paciente acreditado es la unidad de remuestreo. La población es exclusivamente la versión explícita FROZEN que pase E1: identidad clínica, pertenencia, READY/PASS, checks, archivos y fingerprints sellados. El alcance demográfico y de adquisición debe extraerse de su documentación, nunca inferirse. La matriz inicial no acredita un dataset accesible. No se presuponen independencia por célula, generalización a otros centros ni validación clínica.
La hipótesis descriptiva es que las arquitecturas pueden diferir en especificidad al orientar el umbral hacia sensibilidad estrictamente > 0,98. Se distinguen objetivo predefinido, estimación puntual e intervalo. Un punto > 0,98 no demuestra que el límite inferior lo supere ni acredita desempeño clínico. No se realizan pruebas de hipótesis ni declaraciones de significancia.
## Particiones

TRAIN ajusta pesos y aumentación. VALIDATION selecciona checkpoint, umbral y configuración. TEST sólo evalúa decisiones previamente congeladas. E1 verifica separación por paciente, muestras y hashes; no se regenera el split. Preprocesamiento de E3 determinista por arquitectura y aumentación sólo TRAIN. No se ajustan normalización, probabilidades, umbral ni exclusiones con TEST. No se eliminan outliers según desempeño.
El uso compartido de VALIDATION introduce optimismo por selección. Toda comparación VAL se rotula exploratoria. Una futura revisión prospectiva deberá acreditar subconjuntos disjuntos por paciente para calibración/comparación o predicciones fuera de pliegue con selección anidada. No se ejecuta esa partición aquí. No hay calibración aprendida de probabilidades: se usan scores raw. Historial TEST desconocido hasta consulta acreditada; ausencia de eventos no prueba que sea intacto.
## Matriz y presupuesto

Tres arquitecturas, cuatro optimizadores implementados (Adam, AdamW, SGD, Adadelta), semillas compartidas 11, 29, 47: 36 miembros originales. Se congelan las configuraciones E2 completas sin semilla en el JSON, incluidas inicialización, learning rates y políticas; los valores no se vuelven a tomar de defaults. El presupuesto iguala número de configuraciones y repeticiones, no FLOPs. Máximo 50 épocas base; hasta 20 de fine-tuning en modelos preentrenados y cero en Custom CNN. Early stopping y checkpoint monitorizan val_f2_parasitized a umbral 0,5. Pesos ImageNet y normalización específica se mantienen según E3.
La ablación originales + sintéticos tiene otros 36 miembros planificados no disponibles. No se encontró un generador conectado. Técnica, proporción y procedencia permanecen ausentes: una nueva versión de protocolo será necesaria antes de ejecutarla. Deberá derivar sólo de TRAIN, sin imágenes sintéticas en VAL/TEST. No se confunde aumentación con generación sintética.
## Tres decisiones separadas

1. Checkpoint: política E2/E5 congelada, basada en VALIDATION. 2. Umbral: entre scores VAL únicos más extremos 0 y 1, predicción positiva score >= umbral; exigir sensibilidad > 0,98, maximizar especificidad, luego F2, luego umbral más alto. Sin ambos soportes no se selecciona. Sin alternativa factible, maximizar sensibilidad y los mismos desempates, rotulando objetivo no alcanzado. No se reescriben predicciones E6; la propuesta es distinta de la decisión realmente evaluada. 3. Candidato: exigir matriz original completa y semillas comunes; priorizar configuraciones que cumplan en todas las semillas, media de especificidad, media F2, hash estable. Si ninguna cumple, máximo mínimo de sensibilidad y mismos desempates, explícitamente exploratorio. El checkpoint representativo usa semilla 11 predefinida, nunca la mejor semilla. Congelar referencia de reporte, checkpoint y decisión antes de TEST; no promover Producción.
Con probabilidades en [0,1] y el extremo 0 incluido, siempre-parasitized alcanza sensibilidad 1 si hay positivos; el objetivo aislado puede cumplirse de forma trivial y no basta para utilidad clínica. Por eso se informa siempre especificidad y baseline, sin inventar un umbral mínimo clínico. El fallback de candidato cubre resultados observados que no cumplen; sin ambas clases el umbral no es estimable.
## Métricas e incertidumbre

Matriz de confusión: filas reales [uninfected=0, parasitized=1], columnas predichas [0,1]: [[TN,FP],[FN,TP]]. Se reportan sensibilidad, especificidad, precisión, F1, F2, balanced accuracy, ROC-AUC y PR-AUC definida como average precision no interpolada, además de soportes y prevalencia. Denominador cero implica null y motivo. Baseline siempre parasitized muestra sensibilidad 1 con especificidad 0 cuando existen ambas clases; no sustituye expertos clínicos.
Por semilla se preservan las predicciones. Media y desviación estándar muestral (ddof=1) entre semillas no son incertidumbre poblacional. IC95% percentiles con 1000 remuestreos de pacientes completos, semilla 7301, mínimo operativo predefinido de 20 pacientes y 95% de réplicas válidas por métrica; el mínimo es una salvaguarda, no garantía asintótica. Se informan réplicas válidas y limitaciones. Sin grupos acreditados no se sustituye por bootstrap de células. No se concatenan semillas como nuevas observaciones.
Contrastes descriptivos pareados entre las tres parejas de arquitecturas con mismo optimizador, condición, semilla y población exacta. Se remuestrean los mismos pacientes para ambos modelos y se informa diferencia izquierda menos derecha e IC95% por semilla. Intervalos puntuales, no simultáneos; no hay inferencia de significancia ni corrección multiplicidad porque no se realizan pruebas. Las curvas ROC y precisión-recall se exportan sólo con ambas clases.
## Linaje, exclusiones y reporte

El comparador recibe IDs explícitos de intentos EVALUATE de E6; no inventa un Run ID de evaluación separado donde E6 usa assessment_attempts. Conserva TRAIN, versión, artefacto/hash exactos, snapshot, configuración, semilla, decisión, identidad y hash de predicciones PostgreSQL. EXPLAIN se referencia explícitamente y se valida contra su evaluación; puede documentar errores mediante orden estable de sample_id, nunca causalidad ni precisión clínica. No se seleccionan versiones por fecha.
Partición, dataset o población incompatibles, integridad rota y resultados incompletos se excluyen con motivo. Metadatos históricos insuficientes no se completan. Fuera de matriz, protocolo o umbral E7 los resultados íntegros sólo son exploratorios, sin candidato. TEST histórico es descriptivo final con exposición registrada, nunca una fuente para ajuste o selección. Reportes y decisiones se persisten append-only en PostgreSQL y se releen antes de exportar JSON/Markdown. El documento de preparación no contiene resultados científicos ni sustituye a PostgreSQL.

## Configuración canónica

Los parámetros completos, configuraciones por arquitectura y semillas se fijan en `malaria_dl_local_project/configs/science/e7_v1.json`.
La serialización de hash usa `campaigns.contracts.canonical` (UTF-8, claves ordenadas, números finitos).

## Referencias metodológicas

- [Average precision, definición no interpolada (scikit-learn)](https://scikit-learn.org/1.5/modules/generated/sklearn.metrics.average_precision_score.html)
- [Bootstrap con datos agrupados por paciente](https://pubmed.ncbi.nlm.nih.gov/10845400/)
- [Obuchowski: análisis ROC con datos agrupados](https://pubmed.ncbi.nlm.nih.gov/9192452/)
