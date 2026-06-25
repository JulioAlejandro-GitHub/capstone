# Reporte técnico del proyecto de capstone: Malaria Parasite Detection

## 1. Resumen ejecutivo

El proyecto presenta un alto grado de madurez como prueba de concepto (PoC) para un flujo de machine learning aplicado a imágenes médicas, pero requiere mejoras arquitectónicas y de pipeline para escalar a un entorno de producción o uso clínico real.

**Principales fortalezas:**
*   **Modularidad y Seguimiento:** Uso destacado de herramientas de tracking de experimentos apoyado en PostgreSQL. La integración del tracking está fuertemente acoplada en scripts principales.
*   **Enfoque en Explicabilidad:** Integración de tres técnicas complementarias (LIME, SHAP, Grad-CAM) para proveer contexto a las predicciones.
*   **Abstracción de Inferencia:** `src/predict_image.py` está encapsulado adecuadamente para su posterior uso como API (`run_clinical_inference`).
*   **Calibración y Ensemble:** Funcionalidades avanzadas de calibración de probabilidad (temperature scaling) y ensamblado de modelos.

**Principales debilidades:**
*   **Riesgo de Data Leakage:** El dataset (`malaria` de TensorFlow Datasets originado de NIH/NLM) agrupa imágenes, y el código realiza un split estratificado al azar a nivel de *imagen*. Si existen múltiples parches del mismo paciente, mezclar pacientes entre *train* y *test* inflará artificialmente las métricas.
*   **Dependencias de entorno y Rutas Hardcodeadas:** Falta contenedorización (Docker). El código asume rutas relativas rígidas (ej. `../data/tensorflow_datasets`).
*   **Métricas de Selección de Checkpoints:** Aunque previene seleccionar por *recall* absoluto (que llevaría al colapso), las alternativas por defecto (como AUC) pueden no ser ideales en contextos clínicos donde minimizar Falsos Negativos (Alta Sensibilidad) a costa de un porcentaje aceptable de Falsos Positivos es preferible.
*   **Pruebas (Testing) Deficientes:** No se evidencia una suite completa de pruebas unitarias o de integración automatizadas para los flujos principales (solo referencias a tests del backend o básicos).

**Riesgos técnicos más importantes:**
*   Uso de modelos con validación sobre un dataset que puede estar sobreajustado a las condiciones únicas de captura del origen (NIH/NLM). La falta de validación externa (cross-cohort) es un riesgo crítico.
*   Deuda técnica en el pipeline CLI, dificultando la integración programática futura del entrenamiento sin usar comandos sub-proceso (subprocess).

**Recomendaciones prioritarias:**
*   Reestructurar el particionamiento de datos (split) para garantizar la separación a nivel de paciente.
*   Implementar Dockerización para Backend, Frontend y el entorno de entrenamiento ML.
*   Establecer una suite de pruebas robusta (`pytest`) abarcando transformaciones de datos, inferencia y métricas.

## 2. Descripción general del proyecto

**Flujo general:**
El sistema toma como **entrada** una imagen microscópica de células sanguíneas (típicamente RGB). Pasa por un control de calidad y preprocesamiento (redimensionamiento a 200x200, normalización o estandarización según el modelo, ej. `vgg16_imagenet` o `rescale_0_1`). Posteriormente, el modelo procesa el tensor y emite una predicción cruda (sigmoid). Se aplica opcionalmente calibración y agregación TTA (Test Time Augmentation). La **salida** es una respuesta estructurada que contiene: la decisión clínica (parasitized o uninfected), la probabilidad calibrada, el nivel de confianza, y si se solicita, las explicaciones visuales.

**Tipo de clasificación:** Clasificación Binaria (`uninfected` vs `parasitized`).

**Probabilidad de sospecha diagnóstica:**
Representa el score (entre 0 y 1) de la neurona de salida sigmoide, típicamente calibrada. Un valor cercano a 1 indica alta sospecha de infección (parasitized), mientras que un valor cercano a 0 indica que la célula está sana.

**Explicaciones visuales:**
El sistema genera mapas térmicos o resaltado de superpíxeles sobre la imagen original para justificar la predicción:
*   **LIME:** Perturba superpíxeles locales para ver su impacto en la predicción.
*   **SHAP:** Estima la contribución (positiva/negativa) de regiones al resultado respecto a un fondo de referencia.
*   **Grad-CAM:** Extrae gradientes de la última capa convolucional para mostrar qué regiones globales activaron la decisión.

## 3. Arquitectura del software

*   **Acoplamientos innecesarios:** Existe un fuerte acoplamiento entre la lógica de ejecución (entrenamiento, evaluación) y el tracking de base de datos dentro de los mismos módulos (ej. importaciones de `src.tracking_integration` inyectadas a mitad de los scripts como `train.py`).
*   **Repetición de código:** Lógica de instanciación de datasets, parsing de argumentos e inicialización de modelos se repite ligeramente entre `train.py`, `evaluate.py`, `explain.py`, y `predict_image.py`.
*   **Manejo de configuración:** Centralizado en `src/config.py`, lo cual es positivo, pero depende excesivamente de variables de entorno implícitas y argumentos CLI, sin un archivo `.yaml` o similar para gestión de experimentos reproducibles (MLOps puro).
*   **Manejo de rutas:** Frágil. Depende de la estructura relativa exacta (`sys.path.insert(0, ...)` y rutas de directorios tipo `../data/tensorflow_datasets`).
*   **Manejo de errores:** Captura básica de excepciones para reportar fallos a la BD de tracking (`fail_tracking_run`), pero podría ser más exhaustiva en la ingesta de datos corruptos.
*   **Escalabilidad del diseño:** El backend de solo lectura con FastAPI está bien aislado y escala. Sin embargo, el pipeline ML no está preparado para escalabilidad horizontal o entrenamiento distribuido, pues asume ejecución local secuencial.

## 4. Pipeline de datos

*   **Carga y organización:** Carga desde `tensorflow_datasets`, remapeado clínico a `0=uninfected`, `1=parasitized` y guardado físico estratificado (`data/malaria_physical_split/`).
*   **Data leakage:** **RIESGO ALTO**. El split estratificado de `sklearn.model_selection` asume que cada imagen es IID (Independiente e Idénticamente Distribuida). Si se capturaron docenas de imágenes por paciente, hay fuga de información entre particiones.
*   **Control de duplicados:** No se observa un proceso explícito de eliminación de duplicados por hash en la generación del split.
*   **Reproducibilidad:** El split es reproducible mediante fijación de semillas (`--seed 42`), lo cual es una buena práctica.
*   **Balanceo de clases:** El dataset de TFDS está inherentemente balanceado (~27,558 imágenes repartidas al 50%), y el split preserva esta proporción (estratificado).
*   **Aumento de datos:** Implementado adecuadamente (volteo, rotación, traslación, zoom, contraste) en `src.data.py` (función `build_augmentation()`).
*   **Preprocesamiento:** Consistente, forzando un mapeo predefinido (`rescale_0_1` o `vgg16_imagenet`) mediante la función `resolve_preprocessing_mode`. Se asegura coherencia entre entrenamiento, inferencia y explicabilidad.
*   **Calidad y Origen:** Existe un módulo `image_quality.py` para alertas de entrada. Se documenta la fuente (NIH/NLM).

**Evaluación de riesgos específicos:**
1.  **Dataset pequeño/poco diverso:** Aunque 27k imágenes no es diminuto para *transfer learning*, la falta de diversidad poblacional y de origen instrumental (todos de un mismo lote de microscopios de NIH/Bangladesh) genera alto riesgo de sesgo.
2.  **Validación Externa:** Completamente ausente. El modelo no se ha probado en datasets independientes (por ejemplo, muestras de hospitales de otras regiones).

## 5. Modelos de inteligencia artificial implementados

1.  **Custom CNN:** Una arquitectura construida desde cero inspirada en literatura previa. Consta de 4 bloques (Conv2D -> BatchNorm -> ReLU -> MaxPool) seguido de GlobalAveragePooling2D, capas densas con Dropout (0.4) y regularización L2.
2.  **VGG16 (Transfer Learning):** Carga pesos preentrenados de ImageNet. Descongela opcionalmente los últimos 4 bloques (`fine-tuning`). Reemplaza la cabeza con GAP2D, Densa(1024), Dropout(0.5) y Densa(1).
3.  **SVM Feature Extractor:** Un pipeline que utiliza la penúltima capa de los modelos CNN (preferiblemente VGG16) como extractor de características para alimentar una Support Vector Machine con kernel RBF.
4.  **Ensemble Simples:** Promedio ponderado de las predicciones probabilísticas de Custom CNN y VGG16.

## 6. Evaluación de modelos

Las métricas monitoreadas son exhaustivas (accuracy, precisión, recall, specificity, AUC, balanced accuracy).
*   **En contexto biomédico:** La métrica más importante cuando un Falso Negativo (enviar a casa a un paciente con malaria) es fatal, es la **Sensibilidad (Recall para la clase positiva)**.
*   Actualmente el checkpoint se elige por defecto mediante `val_auc` (Área bajo la curva ROC).
*   **Crítica:** Si bien optimizar solo por recall puede generar colapso (predecir todo como positivo), se recomienda emplear **F-Beta Score (con Beta > 1, ej. F2-Score)** para penalizar fuertemente los falsos negativos, o seleccionar el modelo con mayor AUC pero que garantice un recall mínimo de (por ejemplo) 98%. Alternativamente, calibrar el umbral clínico operativo en base a la Curva ROC para fijar la sensibilidad deseada.

## 7. Probabilidad de sospecha diagnóstica

Implementada correctamente mediante función de activación sigmoide en la última capa y con la aplicación de Temperature Scaling en `src.calibrate.py`. Esto es esencial porque las redes neuronales profundas (como VGG16) tienden a estar descalibradas (overconfident). La probabilidad reportada es por tanto más representativa de la certeza empírica.

## 8. Explicabilidad e interpretabilidad

El módulo `src.explain.py` es sólido. Implementa LIME, SHAP (GradientExplainer) y Grad-CAM. Genera resúmenes visuales (mapas de calor superpuestos y segmentación de superpíxeles).
*   **Validación clínica faltante:** La explicabilidad *técnica* funciona, pero no hay un proceso en código o documentación que indique cómo un patólogo avala que las características (features) resaltadas por Grad-CAM coinciden con morfología del parásito (ej. anillos de trofozoítos) frente a manchas de colorante (ruido).

## 9. Debilidades técnicas encontradas

**Severidad Crítica**
*   **Data Leakage a nivel de paciente:** Riesgo de sobrestimación severa de las capacidades de generalización.

**Severidad Alta**
*   **Falta de Validación Externa (Out-of-Distribution - OOD):** El sistema podría fracasar ante imágenes de microscopios diferentes (variaciones de iluminación, tinción, resolución).
*   **Dependencia en Rutas y Entorno (Falta de Docker):** Difícil portabilidad y despliegue continuo.

**Severidad Media**
*   **Acoplamiento de Tracking DB en Lógica de Entrenamiento:** Si la BD falla, el entrenamiento falla (aunque parece haber un try/except general, oscurece el flujo).
*   **Suite de Pruebas Unitaria Carente:** Falta cobertura para preprocesamiento y transformaciones de datos.

**Severidad Baja**
*   **Uso de Configuración Vía CLI/Variables Globales:** En lugar de archivos YAML estandarizados tipo Hydra/OmegaConf.
*   **Modelo Base (VGG16) obsoleto:** Aunque clásico, hoy existen arquitecturas más eficientes y precisas.

## 10. Puntos de mejora del software

**Arquitectura:**
1.  **Desacoplar el Tracking:** Utilizar inyección de dependencias o decoradores/callbacks puros (como en Keras) para MLflow/PostgreSQL, de manera que la lógica core del modelo no se entere del tracking.
2.  **Contenedorización:** Proveer `Dockerfile` separados para Backend, Frontend, y un entorno aislado para tareas ML (inferencia/entrenamiento).
3.  **Configuración basada en archivos:** Transicionar de argparse/config.py a YAMLs versionables.

**Modelos de IA:**
1.  **Detección de Objetos (Object Detection):** Mover de clasificación de imagen completa a detección (ej. YOLO, Faster R-CNN). Esto proporciona bounding boxes directos sobre los parásitos, siendo más útil y explicable para un patólogo que la clasificación global + Grad-CAM.
2.  **Detección de Outliers/Anomalías:** Integrar un modelo (ej. Autoencoder) para descartar o marcar imágenes de calidad inaceptable antes de la clasificación binaria.

## 11. Optimización de modelos de IA

1.  **Reemplazo del Backbone:** VGG16 es pesado y computacionalmente ineficiente. Prioridad: Migrar a EfficientNetV2 o MobileNetV3. Reducirá tiempos de inferencia y tamaño del modelo, facilitando el despliegue edge.
2.  **Pre-entrenamiento de Dominio (Domain Adaptation):** En lugar de ImageNet (animales/objetos), usar transfer learning desde modelos preentrenados en dominios biomédicos médicos o histopatológicos.
3.  **Hyperparameter Tuning Automatizado:** Implementar Optuna/Ray Tune para búsqueda de hiperparámetros sistemática en lugar de los actuales valores preestablecidos.

## 12. Modelos alternativos recomendados

| Modelo | Ventajas | Desventajas | Cuándo usar |
| :--- | :--- | :--- | :--- |
| **EfficientNetV2** | Excelente ratio precisión/parámetros. Muy rápido en inferencia. | Más complejo de entender conceptualmente que CNN/VGG16. | Como reemplazo estándar para clasificación en producción. |
| **Vision Transformers (ViT / Swin)** | Capturan relaciones globales en la imagen, menos sesgados por texturas locales que CNNs. | Requieren vastas cantidades de datos o fuerte pre-entrenamiento. | Si se consigue un dataset masivo (>100k imágenes) o pesos pre-entrenados en microscopía. |
| **YOLO (v8/v11) (Detección)** | Localiza *exactamente* dónde está el parásito. Explicabilidad inherente y nativa. | Requiere re-anotar el dataset para crear *bounding boxes* si no existen. | Evolución ideal del proyecto para uso clínico real. |
| **ResNet50 / ResNet18** | Clásico, confiable, buen balance de profundidad, supera ampliamente a VGG16. | Menos eficiente que arquitecturas más recientes (EfficientNet). | Iteración rápida para establecer un baseline robusto post-VGG16. |

## 13. Roadmap de mejora

**Fase 1: Estabilización y Calidad (1-2 meses)**
*   Implementar Dockerización completa.
*   Crear suite de Pruebas Unitarias exhaustivas (pytest).
*   Investigar y resolver el data leakage (agrupar metadata por paciente si existe, de lo contrario, documentar el límite metodológico).
*   Añadir métricas clínicas F-Beta Score y PR-AUC.

**Fase 2: Optimización del Core ML (2-3 meses)**
*   Reemplazar VGG16 por EfficientNetV2.
*   Implementar archivo de configuración YAML (Hydra).
*   Integrar framework para ajuste de hiperparámetros automático.
*   Evaluar robustez contra un dataset externo Out-of-Distribution.

**Fase 3: Evolución Clínica (3-6 meses)**
*   Explorar Detección de Objetos (Bounding boxes) si se consiguen anotaciones.
*   Implementar validación clínica de las salidas Grad-CAM/LIME junto a expertos en dominio.

## 14. Conclusión técnica

El sistema "Malaria Parasite Detection" es una sólida prueba de concepto con una base excelente en ingeniería de Machine Learning local (tracking, ensembling, calibración, explicabilidad post hoc). Sus principales fallas radican en el acoplamiento arquitectónico, ausencia de contenedores, un dataset con riesgo metodológico y una red base (VGG16) algo obsoleta. Solventando estos puntos (principalmente el OOD y el data leakage poblacional), el proyecto tiene un excelente potencial para evolucionar a una herramienta de apoyo al diagnóstico clínico confiable.

## 15. Anexo: checklist técnico

**Principales 5 debilidades:**
1.  Riesgo de fuga de datos (Data Leakage) inter-pacientes en el particionamiento físico.
2.  Falta de pruebas de validación con datasets externos u out-of-distribution.
3.  Acoplamiento directo del código del modelo con la base de datos de tracking de experimentos.
4.  Entorno de ejecución y rutas rígidas; carencia de entornos en contenedor (Docker).
5.  Uso de arquitectura VGG16, que resulta pesada e ineficiente frente a alternativas modernas.

**Principales 5 mejoras recomendadas:**
1.  Adoptar **EfficientNetV2** o **ResNet50** como modelo principal de clasificación.
2.  Containerizar toda la aplicación mediante **Docker** y **Docker Compose**.
3.  Establecer la **F2-Score** (o priorización de Recall) como métrica decisiva para checkpoints, dadas las implicaciones de Falsos Negativos.
4.  Crear **pruebas unitarias** completas para las tuberías (pipelines) de preprocesamiento, inferencia y métricas.
5.  Explorar modelos de **Detección de Objetos** para sustituir/apoyar la clasificación global mediante bounding boxes locales.

**Próximos pasos sugeridos:**
1.  Hacer *refactor* a `train.py` para usar configuración YAML.
2.  Investigar la fuente NIH para agrupar las imágenes por *Patient-ID* antes de la división del dataset.
3.  Escribir el `Dockerfile` para aislar el entorno.
4.  Desarrollar y ejecutar la suite unitaria.
5.  Entrenar el primer modelo `EfficientNetV2` para establecer un nuevo benchmark.