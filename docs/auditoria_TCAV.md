TCAV es parcialmente viable en Capstone. Hay modelos y artefactos suficientes para desarrollar una prueba posterior al entrenamiento, empezando por Custom CNN. Todavía no está acreditada su ejecución efectiva ni su validez científica: faltan el motor TCAV, conjuntos conceptuales validados y controles experimentales.

La principal brecha es la anotación de conceptos microscópicos, más que el entrenamiento de los clasificadores.

Esta evaluación corresponde al 30 de octubre de 2026. Realicé inspección de código, consultas SELECT a PostgreSQL, lectura de anotaciones locales y comprobación de archivos y SHA-256. No modifiqué código, datos, PostgreSQL, checkpoints ni frontend; tampoco ejecuté entrenamientos, assessments o migraciones.

1. Página y módulos solicitados

La URL solicitada devuelve HTTP 200. También responden correctamente los GET de resúmenes de entrenamiento y linaje. Revisé sus componentes frontend y contratos backend; no realicé una comprobación visual interactiva del navegador.

El análisis actual organiza la información en Resumen, Aprendizaje, Desempeño clínico, Errores y consenso, Explicabilidad, Representaciones y Trazabilidad. Está implementado en [AnalysisWorkspace.tsx](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/frontend/src/components/reports/AnalysisWorkspace.tsx) y conectado desde ScientificPreflight.tsx.

Los comandos indicados son entradas públicas con selección explícita:
Entrada	Implementación efectiva	Comportamiento comprobado en código
python -m src.train	execution.operations.main()	Requiere campaña o TRAIN de origen; puede ejecutar campaña o crear un nuevo entrenamiento
python -m src.evaluate	assessment.cli.main("evaluate")	Evaluación de desarrollo sobre VAL
python -m src.explain	assessment.cli.main("explain")	Grad-CAM, LIME o SHAP sobre VAL
python -m src.test	assessment.cli.main("test")	Evaluación final sobre TEST


Los comandos sin argumentos no seleccionan automáticamente un modelo: requieren --campaign-id y/o --source-training-run-id. Deben resolverse desde malaria_dl_local_project, con su entorno Python correspondiente.

src.test evalúa modelos; no es la suite de pruebas de software. Su implementación no exige ejecutar previamente EVALUATE y EXPLAIN.

Evidencia: [operations.py](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/src/malaria_dl/execution/operations.py) y [assessment/cli.py](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/src/malaria_dl/assessment/cli.py).

2. Evidencia ejecutada y persistida

En PostgreSQL comprobé:
Evidencia	Cantidad
TRAIN completados	83
TRAIN fallidos	3
Intentos EVALUATE verificados	140
Identidades EVALUATE sobre VAL	72
Identidades EVALUATE sobre TEST	68
Intentos EXPLAIN verificados	71
Intentos EXPLAIN fallidos	2
Identidades Grad-CAM / LIME / SHAP	20 / 26 / 27
Intentos REPRESENT verificados	6
Artefactos de embeddings	6
Artefactos PCA / varianza PCA / UMAP	6 de cada tipo
Anotaciones de validación científica	0
Revisiones especialistas XAI	0


EVALUATE y TEST comparten kind='evaluate'; se distinguen por split y purpose. Buscar únicamente RUNs con tipo “test” daría una conclusión incorrecta.

Comprobé físicamente los seis checkpoints vinculados desde model_versions: todos existen y coinciden con sus SHA-256 registrados. También coinciden los seis archivos de embeddings y las dependencias registradas de BiomedCLIP.

Existe un checkpoint Linear adicional comprobado en artifacts, aunque el modelo no tiene actualmente una fila correspondiente en model_versions. Esa diferencia afecta su elegibilidad bajo el contrato actual, pero no demuestra que necesite reentrenamiento.

3. Matriz de factibilidad por arquitectura

“VIABLE” indica que la arquitectura ofrece los elementos técnicos necesarios. No significa que TCAV ya esté implementado o probado.
Arquitectura	Estado técnico	Checkpoint comprobado	Activaciones y salida candidata	¿Sin reentrenar?
Custom CNN	VIABLE	.keras, SHA correcto	Bloques convolucionales o GAP de 256 dimensiones; salida sigmoid	Sí, condicionado a verificar carga y gradientes
VGG16	VIABLE	.keras, SHA correcto	Bloques convolucionales o GAP de 512 dimensiones	Sí
DenseNet121	VIABLE	.keras, SHA correcto	Backbone anidado o GAP de 1024 dimensiones	Sí
BiomedCLIP Zero-shot	CONDICIONADO	Base y dependencias verificadas	Bloques ViT o embedding normalizado de 512 dimensiones; puntuación texto-imagen diferenciable	Sí
BiomedCLIP Linear	CONDICIONADO	Checkpoint de cabeza, SHA correcto	Encoder base + cabeza lineal de 512→1	Sí, resolviendo primero su identidad y contrato
BiomedCLIP Fine-tuning	CONDICIONADO	Delta entrenado .pt, SHA correcto	Base + parámetros entrenados; bloques ViT y cabeza	Sí
YOLO26-seg	NO ACREDITADO para TCAV	best.pt local existente	Representaciones internas posibles; falta definir objetivo diferenciable	No puede decidirse todavía


Los checkpoints principales observados incluyen:
- Custom CNN: outputs/campaign_runs/34923815-3637-4008-960b-d311167eabc3/epoch_2.keras.
- VGG16: outputs/campaign_runs/910051e5-a00c-44c4-9d23-77598af470f7/epoch_2.keras.
- DenseNet121: outputs/campaign_runs/b1b39079-658f-4300-b159-52619f981035/epoch_3.keras.
- Fine-tuning: outputs/campaign_runs/db31b6af-c2a2-44f0-9316-8f8c3492c0f1/epoch_20.pt.
- Linear inspeccionado: outputs/campaign_runs/e0484608-3acd-42f6-bfd5-a1e22f04762c/epoch_27.pt.
- YOLO: smear_segmentation_project/runs/yolo26_seg/yolo26n_rbc_1024_v1/weights/best.pt.
Las rutas anteriores son relativas a sus respectivos proyectos.

Las CNN terminan en sigmoid. Recomiendo recuperar el logit previo a sigmoid para reducir problemas de saturación, documentando la clase y orientación del CAV. En DenseNet hay que resolver correctamente el backbone anidado cuando se seleccionen capas interiores.

Evidencia: [architectures.py](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/src/malaria_dl/models/architectures.py) y [runtime.py](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/src/malaria_dl/assessment/runtime.py).

Limitación: no cargué los modelos en TensorFlow/PyTorch ni calculé gradientes nuevos. La recuperación exacta en ejecución queda pendiente de una prueba autorizada.

4. Datos, anotaciones y conceptos

Las versiones solicitadas existen y están FROZEN:
Dataset	TRAIN: imágenes/pacientes	VAL: imágenes/pacientes	TEST: imágenes/pacientes
Celular d8c0…2ec2	22.180 / 161	2.693 / 20	2.685 / 20
Frotis f0c1…8791	770 / 154	95 / 19	100 / 20


La consulta de pacientes asignados a más de un split no devolvió filas dentro de cada versión. Esto no acredita por sí solo independencia entre ambas familias de datasets: antes de formar conceptos con frotis debe cruzarse su identidad de paciente con la población celular.

La fuente local de frotis está en:

malaria_dl_local_project/data/NIH-NLM-ThinBloodSmearsPf

Leí sus 965 archivos GT, sin recorrer masivamente imágenes:
Fuente local	Archivos GT	Pacientes	Parasitized	Uninfected	White_Blood_Cell
Polygon Set	165	33	1.142	33.071	51
Point Set	800	160	6.810	155.640	220


Los comentarios contienen únicamente variantes de No_comment. Los puntos localizan células; no son máscaras ni localizaciones específicas del parásito intracelular.

La ficha general NIH enumera plaquetas, precipitados y otros objetos. Sin embargo, el README de ThinBloodSmearsPf describe anotaciones celulares y los archivos locales inspeccionados solo contienen las tres etiquetas anteriores. No corresponde trasladar el inventario general a este conjunto concreto. Fuentes: ficha NIH/NLM y README ThinBloodSmearsPf.
Concepto solicitado	Evidencia disponible	Derivación posible	Brecha
Estructura anular	Sin etiqueta explícita	Selección de candidatos dentro de células infectadas	Confirmación experta; “infectada” no equivale a “anillo”
Cromatina parasitaria	Sin etiqueta ni región específica	Candidatos visuales	Anotación experta de estructura y localización
Precipitado de tinción	Sin etiqueta en GT local	Búsqueda y selección dirigida	Nuevas anotaciones y controles
Borde del eritrocito	Contornos Polygon disponibles	Banda de borde mediante regla versionada	Validar definición y evitar confusión por fondo o recorte
Variaciones de tinción	Imágenes RGB; sin etiqueta experta	Medidas cromáticas o perturbaciones controladas	Validación de que la medida representa tinción
Artefactos microscópicos	Sin taxonomía local explícita	Candidatos por revisión	Definir categorías y anotarlas
Plaquetas	Sin etiqueta local	Selección en frotis completos	Revisión experta; negativos morfológicamente similares
Eritrocitos superpuestos	Sin etiqueta explícita	Candidatos por relaciones geométricas entre polígonos	Confirmar superposición real y calidad de contornos


No hay cantidades acreditadas de ejemplos positivos para esos ocho conceptos. Las cantidades de células anteriores no deben presentarse como cantidades conceptuales.

Como concepto adicional, White_Blood_Cell sí dispone de etiqueta y localización: 51 polígonos en 23 pacientes y 220 puntos en 109 pacientes. Puede servir para investigar confusores, pero los crops de leucocitos pueden estar fuera de la distribución del clasificador de eritrocitos.

Para plaquetas, superposición y artefactos conviene partir del frotis completo. Para anillos y cromatina puede bastar una célula con resolución adecuada. Los negativos deben corresponder a ausencia confirmada del concepto, no simplemente a la clase uninfected.

Evidencia del parser: [polygon_set.py](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dataset_split_project/src/malaria_split/sources/polygon_set.py).

5. ¿Podemos ejecutar TCAV después del entrenamiento sin modificar TRAIN?

Sí, en principio, para las CNN y las tres modalidades BiomedCLIP, si se recuperan el checkpoint y sus contratos completos. No es necesario guardar todas las activaciones durante TRAIN.

TCAV requiere extraer activaciones de ejemplos conceptuales, ajustar un clasificador lineal y calcular sensibilidad de una puntuación del modelo respecto de la dirección aprendida. Ese trabajo puede realizarse posteriormente. Es la base metodológica de Kim et al., 2018.

Propongo los siguientes tratamientos:
Escenario	Decisión
C1: checkpoint y contratos completos	TCAV posterior, asociado al TRAIN original mediante una identidad nueva
C2: información incompleta pero recuperable	Completar evidencia verificable desde artefactos existentes; no inventar valores históricos
C3: faltan pesos o preprocesamiento irrecuperables	Declarar esa versión no elegible; justificar reentrenamiento solo después de agotar recuperación


Para futuros TRAIN conviene asegurar persistencia de arquitectura, preprocesamiento, checkpoint y hash, versión de framework, clase positiva y dependencias. Capstone ya conserva parte importante de ello.

La selección de capa, configuración del CAV y activaciones conceptuales pertenecen al experimento posterior. No recomiendo cambiar ahora src.train.

Hay una cautela local adicional: execution/accelerator.py contiene una configuración y un canario para divergencias de TensorFlow/Metal. El futuro motor debe reutilizar esa configuración y verificar consistencia de salidas y gradientes.

BiomedCLIP requiere tratamiento separado:
- Zero-shot: conserva encoder visual, encoder textual y prompts. La salida puede ser el logit de clase o un margen entre clases, con definición explícita.
- Linear: usa encoder base y cabeza binaria. Que el encoder esté congelado durante entrenamiento no impide derivar respecto de activaciones.
- Fine-tuning: el .pt guarda parámetros entrenados y referencia a la base; no es un checkpoint autónomo de toda la red.
- Los métodos habituales de predicción usan torch.inference_mode(). El cálculo TCAV necesita una ruta con autograd habilitado.
- Ya existen wrappers diferenciables en assessment/openclip.py, aprovechables como referencia.
- Los bloques visual.trunk.blocks.* son candidatos; deben registrarse bloque, tokens, pooling y normalización exactos.
- Los prompts fijan la función explicada. La similitud texto-imagen no constituye un CAV.
Evidencia: [biomedclip_training.py](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/src/malaria_dl/models/biomedclip_training.py) y [assessment/openclip.py](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/src/malaria_dl/assessment/openclip.py).

6. Reutilización de embeddings, PCA, UMAP y CKA

Los seis embeddings comprobados corresponden a CNN:
Arquitectura	Dimensión	Poblaciones persistidas observadas
Custom CNN	256	VAL, 2.693 células
VGG16	512	VAL y TEST; incluye dos TRAIN distintos en TEST
DenseNet121	1.024	VAL y TEST


El código también implementa extracción de embeddings BiomedCLIP normalizados, pero no encontré artefactos REPRESENT de esa familia en los seis registros actuales.
Componente	Reutilización propuesta	Límite
Embeddings completos	Probing y CAV en esa misma representación	Requieren etiquetas conceptuales alineadas
Identidad de muestras y orden de filas	Alinear modelos, conceptos y evaluaciones	Comprobar población y split
PCA	Exploración descriptiva	Se persisten coordenadas y varianza; eso no garantiza un transformador reutilizable
UMAP	Visualización de vecindarios	Su proyección no sustituye activaciones diferenciables
CKA	Comparar geometrías de representación	No mide sensibilidad conceptual
Checkpoint + grafo	Recuperar gradientes posteriormente	Necesita validación numérica


Probing mide separabilidad; TCAV mide sensibilidad direccional. Un buen probe no demuestra que el modelo use el concepto para decidir.

Además, DenseNet tiene una cabeza lineal inmediatamente después de GAP. Si se explica el logit en ese espacio, su gradiente es constante: el signo de la derivada puede ser igual para todas las células. Conviene evaluar también una capa anterior y declarar esta limitación.

No deben usarse los embeddings TEST existentes para seleccionar conceptos, capas o hiperparámetros.

Evidencia: [representation.py](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/malaria_dl_local_project/src/malaria_dl/assessment/representation.py) y [scientific_representations.py](/Users/julio/Desktop/Archivo/Magister UAI/Capstone MIA 2025 2/Desarrollo/SW/capstone/backend_api/app/services/scientific_representations.py).

7. Protocolo científico propuesto

Este protocolo es una recomendación; no representa resultados obtenidos.
1. Definir conceptos y controles. Crear manual de anotación, ejemplos positivos, negativos difíciles, casos inciertos y revisión experta. Registrar paciente, fuente, tinción y relación con clase.
2. Separar por paciente. Ajustar CAV con pacientes TRAIN; validar separabilidad en pacientes independientes. Reservar TEST para el análisis final previamente fijado.
3. Medir separabilidad. Balanced accuracy, AUROC, sensibilidad, especificidad e intervalos por paciente. Rechazar probes que solo distingan fuente, fondo o clase.
4. Comprobar gradientes. Comparar derivadas de autograd con diferencias finitas en varias escalas y comprobar que la instrumentación conserva predicciones.
5. Evaluar estabilidad. Variar semillas, negativos y capas; informar distribución de resultados, orientación del CAV y pacientes contribuyentes.
6. Aplicar controles estadísticos. Conceptos aleatorios y permutaciones que respeten agrupación; bootstrap por paciente y corrección por comparaciones múltiples.
7. Evaluar fidelidad. Perturbar regiones expertas y regiones control equivalentes. Revisar plausibilidad y cambios fuera de distribución.
8. Relacionar con XAI existente. Contrastar Grad-CAM, LIME y SHAP con regiones expertas; usar CKA/PCA/UMAP como contexto descriptivo.
Como criterios de aceptación propondría: separabilidad superior al control con intervalo agrupado, gradientes numéricamente consistentes, resultados estables y evidencia que sobreviva los controles predefinidos. Los umbrales deben fijarse antes de evaluar TEST.

La coincidencia visual y la significancia estadística, por sí solas, no acreditan causalidad ni utilidad diagnóstica.

Una limitación concreta es que Polygon Set dispone de solo dos pacientes VAL en el split actual. No es una base suficiente para afirmar generalización robusta de conceptos derivados de polígonos. No recomiendo alterar el split: habrá que dimensionar la validación y, si corresponde, obtener nuevos pacientes.

8. Persistencia, Reporte A y Etapa 2

El esquema real ya ofrece runs, model_versions, artifacts, assessment_identities, assessment_attempts, assessment_results, assessment_artifacts y entidades XAI.

Sin embargo, no acepta TCAV directamente: el CHECK de assessment_identities.kind permite únicamente evaluate, explain y represent. No corresponde introducir TCAV cambiando solo un JSON.

Recomiendo estudiar una extensión del sistema actual de assessments, evitando una infraestructura paralela. El contrato mínimo debería incluir:
Grupo	Información
Origen	TRAIN, model version, checkpoint y SHA
Datos	Dataset version, población, pacientes, split y hashes
Concepto	ID, versión, definición, positivos, controles y anotadores
Representación	Capa exacta, forma, pooling, normalización y framework
Experimento	Puntuación explicada, semillas, clasificador CAV e hiperparámetros
Resultados	Separabilidad, TCAV agregado, derivadas individuales, intervalos y controles
Artefactos	CAV, manifiestos y resultados con hash, tamaño y ruta
Ejecución	Intento, entorno, commit, estado y verificaciones


Los binarios seguirían fuera de PostgreSQL. El TRAIN original permanecería inmutable.

También comprobé que assessment_artifacts guarda su evidencia en payload; un JOIN indiscriminado con artifacts no recupera estos archivos. Debe reutilizarse el repositorio efectivo de assessments.

Para frontend propongo:
- Reporte A / Aprendizaje: “Conceptos microscópicos aprendidos”, mostrando ejemplos, controles, capa, separabilidad, TCAV, incertidumbre y limitaciones.
- Comparación Científica: comparar solo el mismo concepto/versionado, población, clase objetivo y protocolo. Mostrar diferencias de arquitectura y capa; no ordenar modelos por “mayor TCAV”.
- Etapa 2: presentar una derivada direccional por célula junto con el TCAV agregado de una población definida.
En Etapa 2 el linaje debe conservar:

frotis → detección → crop y checksum → clasificación/model version → explicación conceptual.

La derivada individual puede asociarse al objeto sobre el frotis. No es un TCAV Score individual ni una máscara espacial. Un mapa local requeriría otra técnica complementaria.

Para contener costo, conviene calcular bajo demanda, procesar por lotes y cachear por checkpoint, crop, concepto, capa y protocolo. No añadiría TCAV como requisito del pipeline productivo.

YOLO queda como investigación aparte: el runtime actual devuelve resultados posprocesados mediante predict, NMS y conversión a CPU. Haría falta definir una puntuación diferenciable previa al posprocesamiento —por ejemplo, clase o máscara de un objeto fijado— y demostrar qué explica. El TCAV del clasificador celular no responde esa pregunta.

9. Plan posterior recomendado
Etapa	Objetivo y componentes	Dependencias y riesgos	Prueba y aceptación
01B	Definir y versionar conceptos con gobierno de datasets y revisión científica	Positivos, negativos y pacientes independientes; confusión concepto/clase	Manifiestos íntegros, acuerdo experto y ausencia de fuga
01C	Motor CNN sobre assessment/runtime.py y contratos existentes; empezar con Custom CNN	Conceptos 01B; capas y logits recuperables	Predicciones preservadas y gradientes consistentes con diferencias finitas
01D	Adaptar assessment/openclip.py y reconstrucción base+delta	Resolver Linear y autograd; normalización/prompts	Carga íntegra, gradientes y reproducibilidad
01E	Validación científica y controles	Conceptos y motores anteriores; dependencia entre células	Estabilidad, controles y análisis por paciente
01F	Persistencia y reportes sobre assessments, servicios científicos y componentes actuales	Contrato validado; restricciones SQL y comparabilidad	Integridad, lectura autorizada e historial inmutable
01G	Explicación conceptual por célula en frotis	Linaje y caché; cambio de dominio	Asociación exacta crop→objeto y distinción individual/agregado


El diseño de persistencia debe acordarse antes del piloto; su integración completa en frontend puede esperar a que el motor produzca evidencia validable.

El experimento mínimo sería Custom CNN, una capa convolucional y GAP, un concepto experto y controles apareados, con pacientes TRAIN para CAV y VAL para desarrollo. Antes del resultado científico debe superar carga, equivalencia de predicción y comprobación numérica del gradiente.

10. Tabla de decisiones
Decisión	Estado	Evidencia	Acción recomendada
TCAV Custom CNN	VIABLE técnicamente	Checkpoint íntegro; arquitectura y GAP accesibles	Primera prueba posterior a TRAIN
TCAV VGG16	VIABLE técnicamente	Checkpoint íntegro; GAP 512 y capas convolucionales	Incorporar tras Custom CNN
TCAV DenseNet121	VIABLE técnicamente	Checkpoint íntegro; GAP 1.024	Resolver backbone anidado y evitar depender solo de cabeza lineal
TCAV BiomedCLIP Zero-shot	CONDICIONADO	Base y dependencias íntegras; wrapper diferenciable	Definir puntuación, capa y protocolo de prompts
TCAV BiomedCLIP Linear	CONDICIONADO	Checkpoint de cabeza íntegro; sin model version actual	Resolver identidad y reconstrucción verificable
TCAV BiomedCLIP Fine-tuning	CONDICIONADO	Delta íntegro y contrato base+parámetros	Verificar carga y gradientes
TCAV YOLO26-seg	NO ACREDITADO	Checkpoint existente; runtime posprocesado	Investigación separada del objetivo diferenciable
Conceptos expertos disponibles	PARCIAL	Clases celulares y contornos; sin etiquetas de los conceptos solicitados	No confundir infección con morfología
Necesidad de nuevas anotaciones	SÍ	GT local sin anillos, cromatina, plaquetas o precipitados	Preparar selección y revisión experta
Necesidad de modificar TRAIN	NO demostrada	Pesos y contratos recuperables	Priorizar TCAV posterior
Integración Reporte A	CONDICIONADA	Componentes científicos existentes	Agregar sección cuando haya evidencia
Integración Comparación Científica	CONDICIONADA	Selección de evaluaciones y representaciones existente	Exigir equivalencia conceptual y experimental
Integración Etapa 2	CONDICIONADA	Detecciones, crops y clasificación trazables	Mostrar derivadas por objeto y agregado separado


Recomendación: conviene avanzar hacia una demostración técnica con Custom CNN, precedida por la preparación de conceptos y controles. Hoy no hay evidencia suficiente para declarar TCAV científicamente validado ni para ofrecer explicaciones de anillos o cromatina. No inicié TCAV-01B ni implementé cambios.