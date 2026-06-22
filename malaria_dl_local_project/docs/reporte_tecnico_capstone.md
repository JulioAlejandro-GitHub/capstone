# Reporte técnico del proyecto de capstone

## 1. Resumen ejecutivo

El proyecto de capstone aborda la clasificación microscópica de imágenes de sangre para la detección de la malaria, usando el dataset NIH / NLM Malaria Cell Images. El objetivo es construir un sistema automatizado de apoyo diagnóstico que clasifique las imágenes en "parasitized" (parasitado) y "uninfected" (no infectado), y que provea explicaciones visuales para que los clínicos comprendan el motivo detrás de la predicción.

El sistema se encuentra en un estado de madurez de **prueba de concepto funcional o prototipo avanzado**. Integra exitosamente flujos de carga de datos, entrenamiento de modelos, evaluación exhaustiva y metodologías post-hoc de interpretabilidad.

**Principales fortalezas:**
- Organización modular y limpia del código (`src/`), con clara separación entre carga de datos, modelos, entrenamiento, evaluación e inferencia.
- Soporte para múltiples arquitecturas: Custom CNN y Transfer Learning con VGG16, incluyendo soporte para métodos híbridos como extracción de features con SVM y ensambles.
- Incorporación nativa de explicabilidad post-hoc (LIME, SHAP, Grad-CAM).
- Calibración de probabilidad, lo que lo acerca a un sistema útil de sospecha clínica.
- Módulos para registro y trazabilidad a base de datos (`track-db`), preparando el proyecto para la integración con sistemas frontend.

**Principales debilidades:**
- Dependencia del split único del dataset público (80/10/10 a partir de "train"), con un alto riesgo de *data leakage* si múltiples imágenes del mismo paciente (o gota de sangre) caen en distintos splits, debido a la falta de metadatos de paciente.
- A nivel arquitectónico, el acoplamiento implícito original al ordenamiento TFDS (`0=parasitized`, `1=uninfected`) fue reemplazado por una convención clínica explícita del proyecto: `0=uninfected`, `1=parasitized`, `raw_model_score=probability_parasitized`.

**Riesgos técnicos más importantes:**
- *Data Leakage:* Que las métricas de test estén sobreestimadas debido a la contaminación de casos similares de la misma muestra sanguínea.
- *Falta de Validación Externa:* El rendimiento del modelo no está comprobado frente a bases de datos provenientes de otros laboratorios, un paso crítico en aplicaciones de salud.

**Recomendaciones prioritarias:**
- Auditar y reestructurar el dataset para asegurar un split a nivel paciente/caso (Patient-ID), si los metadatos existen o pueden aproximarse.
- Evaluar los modelos en un dataset independiente o externo para comprobar la capacidad real de generalización.

## 2. Descripción general del proyecto

**Objetivo del sistema:**
Clasificar imágenes microscópicas de frotis de sangre para identificar si están parasitadas por el patógeno causante de la malaria o si están sanas (no infectadas). Sirve como un sistema de apoyo o alerta clínica, no como un diagnosticador definitivo.

**Entradas esperadas:**
Imágenes digitales de microscopía en formato PNG, RGB.

**Salidas esperadas:**
- La clase predicha (`parasitized` o `uninfected`).
- Probabilidad y nivel de confianza.
- Una imagen generada que explica las zonas clave usadas por el modelo para tomar la decisión.

**Flujo general desde una imagen microscópica hasta una predicción:**
1. Carga de la imagen y preprocesamiento (redimensionamiento a 200x200, escalado o normalización dependiente del modelo).
2. Inferir mediante uno de los modelos entrenados (.keras).
3. Obtener el puntaje crudo del clasificador binario (sigmoide).
4. Interpretar el puntaje bajo el orden predefinido (clase 0 parasitada, clase 1 no infectada).
5. Calcular la probabilidad y calibrarla (si se aplica un mapeo extra de calibración).
6. Aplicar un umbral de decisión (típicamente 0.5) para obtener la clasificación final.
7. Generar métricas de reporte.
8. (Opcional) Pasar la misma imagen por el módulo de explicabilidad (Grad-CAM, LIME, SHAP) para crear un mapa de calor/superpíxeles y retornarlo al clínico.

**Tipo de clasificación implementada:**
Clasificación binaria ("parasitized" vs "uninfected").

**Qué significa la probabilidad de sospecha diagnóstica:**
Representa el grado de certeza o "confianza" que el modelo tiene en que la imagen estudiada pertenezca a la clase de interés (típicamente `parasitized` desde el punto de vista clínico, donde interesa una alta sensibilidad).

**Qué explicaciones visuales genera o debería generar:**
Genera imágenes overlay que fusionan la imagen microscópica original con:
- Mapa de calor que resalta activaciones de capas convolucionales (Grad-CAM).
- Polígonos de superpíxeles que más contribuyeron a la predicción (LIME).
- Mapas que estiman contribución positiva o negativa por pixel (SHAP).
La idea es que el clínico vea si el modelo presta atención al parásito dentro de la célula y no a un artefacto del fondo o borde del cristal.

## 3. Arquitectura del software

**Estructura del repositorio:**
El backend está separado adecuadamente:
- `data/`: Gestión de datos con descargas y artefactos TFDS.
- `malaria_dl_local_project/src/`: Código fuente de machine learning, dividido funcionalmente en `data.py`, `models.py`, `train.py`, `evaluate.py`, `metrics.py`, `explain.py`, `inference_pipeline.py`.
- `backend_api/` y `frontend/`: Capas para construir y servir una API REST (FastAPI) y un dashboard.

**Separación entre entrenamiento, evaluación e inferencia:**
La separación es robusta. Existen scripts específicos con puntos de entrada (`train.py`, `evaluate.py`, `predict_image.py`), los cuales comparten librerías pero mantienen responsabilidades segregadas.

**Separación entre lógica de datos, modelos, métricas, explicabilidad y visualización:**
Muy bien conseguida. `data.py` se encarga de todo el split; `metrics.py` abstrae los cálculos; y `explain.py` encapsula la lógica post-hoc sin ensuciar la inferencia normal.

**Modularización, claridad y repetibilidad:**
- **Calidad de modularización y Claridad de nombres:** Alta. Los módulos describen bien su rol, y las funciones (como `build_custom_cnn`, `run_clinical_inference`) son auto-explicativas.
- **Acoplamientos innecesarios:** Existe un ligero acoplamiento en cómo los módulos necesitan rastrear manualmente el índice (0 o 1) y manejar el mapeo estático ("parasitized", "uninfected").
- **Manejo de rutas y configuración:** Se utilizan constantes en `config.py` o variables de entorno (como `TFDS_DATA_DIR`), lo que favorece la reusabilidad.
- **Manejo de errores:** Capturas genéricas y reporte a la base de datos de tracking (en bloques `try-except` con `fail_tracking_run`).
- **Escalabilidad:** Muy alta. Añadir un nuevo modelo (ej. EfficientNet) implicaría agregar una función en `models.py` y actualizar un `choices` en `train.py`.

**Diagrama de Flujo Actual:**

```text
Imagen microscópica (o dataset TFDS)
  ↓
Carga de datos (src.data)
  ↓
Preprocesamiento (resize 200x200, rescale_0_1 o vgg16_imagenet) (src.preprocessing)
  ↓
Modelo (Custom CNN / VGG16) (src.models)
  ↓
Predicción (score sigmoide)
  ↓
Calibración opcional (src.calibration) -> Probabilidad de sospecha
  ↓
Decisión (por umbral configurable)
  ↓
Evaluación/Métricas (Recall_Parasitized, F1, etc) (src.metrics)
  ↓
Explicación visual (Grad-CAM, LIME, SHAP) (src.explain)
  ↓
Registro estructurado (DB Tracking) (src.tracking_integration)
  ↓
Visualización o reporte (Backend API/Frontend)
```

## 4. Pipeline de datos

**Carga de imágenes y organización de clases:**
El sistema depende completamente del paquete público de TensorFlow Datasets (TFDS) para "malaria", el cual provee las clases 0: `parasitized` y 1: `uninfected`.

**División train/validation/test:**
Se realiza tomando fracciones del único dataset original: `train[:80%]`, `train[80%:90%]`, `train[90%:]`.

**Riesgo de Data Leakage y duplicados:**
**Alto**. El dataset de origen contiene células individuales recortadas. Es probable que haya múltiples recortes provenientes del mismo paciente o la misma frotis. Al dividir las imágenes aleatoriamente o secuencialmente (80/10/10) sin un `Patient-ID`, hay un gran riesgo de mezclar células idénticas entre entrenamiento y evaluación.

**Reproducibilidad y Aumentos:**
- **Reproducibilidad:** El pipeline fuerza una `seed` (ej. 42), por lo que las particiones son consistentes en la misma máquina.
- **Aumentos (Data Augmentation):** Sí aplica. `build_augmentation()` emplea rotación (0.07), translación (0.2), zoom (0.2) y flip horizontal/vertical, lo cual es muy adecuado para la microscopía porque las células no tienen una orientación fija.
- **Consistencia en preprocesamiento:** Está altamente regulado por el módulo `src.preprocessing` usando `PREPROCESSING_RESCALE_0_1` o `vgg16_imagenet`, asegurando que train e inferencia coincidan.

## 5. Modelos de inteligencia artificial implementados

**Modelo 1: Custom CNN**
- **Arquitectura:** Red Secuencial con 4 bloques convolucionales (cada uno de dos `Conv2D` y un `MaxPooling2D`) seguidos por una serie de Dense, Dropout y salida sigmoide.
- **Entrada:** Imágenes RGB 200x200.
- **Salida:** Escalar sigmoide.
- **Función de pérdida:** Binary Crossentropy.
- **Optimizador:** Adadelta (con soporte para Adam).
- **Métricas:** Accuracy, Precision, Recall, ParasitizedRecall, AUC.
- **Hiperparámetros:** Típicamente entrena 30 épocas, batch size 64.
- **Ventajas:** Liviana, permite construir representaciones de características (features) centradas específicamente en parásitos desde cero.
- **Riesgo:** Alto overfitting por no tener pesos previos, compensado con los Dropouts 0.5 implementados.

**Modelo 2: VGG16 (Transfer Learning)**
- **Arquitectura:** VGG16 base (ImageNet, sin top) seguido por `GlobalAveragePooling2D`, un `Dense` de 1024, Dropout(0.5) y salida sigmoide.
- **Entrada y Salida:** Igual a la CNN.
- **Optimizador, Loss, Métricas:** Igual a la CNN.
- **Hiperparámetros:** Usa Fine-Tuning progresivo (descongelando las últimas 4 capas convolucionales después del entrenamiento base).
- **Ventajas:** Aprovecha patrones visuales de nivel inferior preentrenados, mejorando drásticamente el desempeño en datasets pequeños.
- **Nivel de adecuación:** Bueno. Es un estándar sólido en imágenes biomédicas.

**Modelo 3: SVM sobre Features CNN**
- Usa una red (como VGG16) para crear embeddings que luego se clasifican usando una Support Vector Machine con kernel RBF. Una técnica de ensamblado/extracción útil pero que limita la explicabilidad Grad-CAM a nivel SVM (pues la SVM no es diferenciable respecto a los gradientes visuales).

**Modelo 4: Ensemble Simple**
- Promedio ponderado de probabilidades de los modelos Keras, lo que incrementa la robustez diagnóstica.

## 6. Evaluación de modelos

El proyecto realiza una muy buena evaluación calculando un set extenso y apropiado de métricas (vía `src.metrics.evaluate_binary_predictions`):
- Accuracy, Precision, Recall (macro).
- **Sensibilidad (ParasitizedRecall)**: Esta métrica es estelar, es usada como monitor para los Checkpoints. Al ser una herramienta de apoyo clínico, fallar en detectar la enfermedad (Falsos Negativos) es mucho peor que Falsos Positivos.
- Especificidad.
- F1-score, ROC-AUC.
- Matriz de confusión.
- Reporte por clase.

**Evaluación de las métricas:**
Son completamente suficientes y aptas para un sistema de sospecha diagnóstica. Al enfocarse en `recall_parasitized`, el modelo prioriza de forma experta la reducción de Falsos Negativos, algo vital biomédicamente. Faltan, no obstante, métricas de Intervalos de Confianza (p. ej. usando Bootstrapping) y curvas PR-AUC, importantes cuando la prevalencia difiere de 50/50.

## 7. Probabilidad de sospecha diagnóstica

**Análisis de la probabilidad:**
El modelo calcula el `raw_model_score` mediante la activación Sigmoide (salida 1 neurona). Bajo la convención clínica vigente, un puntaje alto representa mayor probabilidad de la clase "parasitized"; por tanto `raw_model_score` equivale a `probability_parasitized`. Los checkpoints legacy entrenados con la convención TFDS previa deben declararse explícitamente.
- **Calibración:** Existe una función `src.calibration.calibrate_probability` aplicada (con temperatura, Isotonic Regression o Platt Scaling) si se pasa un `calibration.json`. Esto soluciona un problema común en las CNNs donde la "probabilidad" de salida suele estar sobreconfiada.
- **Salida comprensible:** El pipeline (p. ej., `build_structured_clinical_response`) estructura esto elegantemente, retornando: clase predicha, probabilidades específicas, nivel de confianza, y si el resultado requiere atención.

**Propuestas de Mejora:**
Agregar categorías cualitativas fijas e inyectar validaciones que detecten "imágenes borrosas o sin iluminación" antes de enviar un resultado. También un campo `recommendation` tipo "Revisión humana requerida" (p. ej., para casos cerca del umbral 0.5 o de baja confianza).

## 8. Explicabilidad e interpretabilidad

El proyecto incluye de forma notable las tres técnicas estelares del campo: Grad-CAM, LIME y SHAP (en `src.explain.py`).

**Evaluación de la implementación:**
- Selecciona casos inteligente y balanceadamente: Verdaderos Positivos, Falsos Negativos, Falsos Positivos, Verdaderos Negativos, y los de "baja confianza" en torno al umbral.
- Se guardan los "overlays" con nombres enriquecidos y todo condensado en un CSV (`explanation_summary.csv`).
- **Grad-CAM** detecta automáticamente la última capa convolucional útil y genera el mapa de calor correctamente interpolado y fusionado (el `overlay`) con la imagen real.
- Diferencia las métricas, permite entender cómo se engaña el modelo en Falsos Positivos.

**Riesgo y Mejoras propuestas:**
- **Riesgo:** SHAP es muy ineficiente y LIME a menudo resalta superpíxeles arbitrarios que el clínico no sabrá interpretar si el sistema confía al 100%. Las explicaciones pueden usarse como sesgo de confirmación por el clínico.
- **Mejoras:**
  - Guardar lado a lado: Una grilla final de (Original | GradCAM | Original con cuadro de bounding box).
  - Usar Grad-CAM guiado y combinar LIME con bordes celulares definidos médicamente en lugar de superpíxeles matemáticos genéricos.
  - Generar un texto automático (NLG - Natural Language Generation) que acompañe el diagnóstico para no depender sólo de interpretar colores cálidos.

## 9. Debilidades técnicas encontradas

### Críticas
- **Data Leakage no controlado:**
  - *Módulo:* `src.data.load_malaria_splits`
  - *Impacto:* Las métricas reportadas pueden ser demasiado optimistas. Las células provenientes del mismo frotis están correlacionadas, un modelo que "aprende el fondo del microscopio de ese paciente" memorizará la muestra, invalidando las pruebas cruzadas.
  - *Recomendación:* Se requiere agrupar el dataset por `Patient-ID` antes del split, o al menos validar el modelo contra un conjunto de datos externo completamente independiente.

### Altas
- **Dependencia de la codificación interna estática (0/1):**
  - *Módulo:* `src.data`, `src.config`, métricas, inferencia y tracking.
  - *Estado:* Mitigado mediante conversión explícita temprana en `Dataset.map()`.
  - *Convención:* `0 = uninfected`, `1 = parasitized`, `raw_model_score = probability_parasitized`.
  - *Riesgo residual:* Checkpoints entrenados antes de esta convención deben ejecutarse como legacy para evitar reportes invertidos.
  - *Recomendación:* Mantener pruebas unitarias de mapeo y registrar `label_mapping_version` en todo artefacto o predicción.

### Medias
- **Desempeño y peso de SHAP:**
  - *Módulo:* `src.explain.explain_with_shap`
  - *Impacto:* SHAP sobre imágenes toma muchísimo tiempo computacional, lo cual degrada la eficiencia del análisis.
  - *Recomendación:* Mantener a Grad-CAM por defecto en producción; mover SHAP a reportes asíncronos profundos (solo a pedido).

### Bajas
- Falta de pruebas unitarias (`pytest`) que comprueben la equivalencia exacta de pipeline de entrenamiento y pipeline de inferencia.

## 10. Puntos de mejora del software

- **Validación Externa e Intervalos de Confianza:** Integrar funciones para Bootstrapping sobre la métrica `ParasitizedRecall` para arrojar resultados estadísticos rigurosos en contextos biomédicos.
- **Calidad de Imagen:** Crear un modelo previo ligero u heurístico de Laplacian variance (detección de bordes) para filtrar imágenes desenfocadas o sin células antes del modelo.
- **Testing (`tests/`):** Crear suites de validación (`test_decision.py`, `test_metrics.py`) para evitar regresiones lógicas matemáticas.
- **Experiment Tracking:** Aunque se implementó integración a base de datos (`track-db`), el uso de herramientas como MLflow, Weights&Biases ayudaría a visualizar curvas de aprendizaje sin esfuerzo.

## 11. Optimización de modelos de IA

Para el tipo de imagen celular microscópica, las mejoras más relevantes serían:
1. **Focal Loss o Weighted Loss:** Ayuda enormemente con falsos positivos difíciles, aunque las clases estén balanceadas, hay ciertos artefactos raros que penalizar mediante Focal Loss forzará al modelo a estudiarlos mejor.
2. **Data Augmentation Específica:** Incorporar desenfoque gaussiano, manchas morfológicas o ruido sal y pimienta. Los microscopios suelen estar sucios o desenfocados.
3. **Calibración de Probabilidades (Platt Scaling continuo):** La calibración actual debe validarse usando Curvas de Confiabilidad empíricas para asegurar su exactitud clínica.

## 12. Modelos alternativos recomendados

Dado el contexto (resolución pequeña, features celulares finas):
- **EfficientNetV2-B0 / B1:**
  - *Cuándo usar:* Remplazo directo para VGG16.
  - *Ventaja:* Muchísimo más eficiente computacionalmente, menos riesgo de overfitting, gran capacidad de extracción.
  - *Desventaja:* El feature map convolucional final es pequeño; el Grad-CAM puede ser menos interpretable o verse "pixelado".
- **ConvNeXt (Tiny/Micro):**
  - *Ventaja:* Moderniza la familia CNN con técnicas de Transformers, pero manteniendo una excelente interpretabilidad espacial natural que es clave para apoyar explicaciones visuales a patólogos.
- **Vision Transformers (ViT o Swin Transformer):**
  - *Recomendación:* No usar si hay pocos datos. Son data-hungry (difícilmente convergentes sin millones de imágenes). Swin Transformer genera una buena atención local, pero en un Capstone VGG o EfficientNet son más adecuados.

## 13. Recomendación de arquitectura objetivo

Se sugiere la siguiente evolución de los flujos:

```text
Imagen nueva
  → [Control de Calidad] (Blur? Tinte muy raro?)
  → [Preprocesamiento Estándar]
  → Modelo Base (ej. EfficientNet)
  → TTA (activado para reducir varianza en inferencia)
  → Calibración de probabilidad (Temperature Scaling)
  → Decisión (Umbral orientado a Recall>98%)
  → [Explicabilidad] Grad-CAM rápido
  → Respuesta estructurada JSON (Score, Confidence, BoundingBox_from_GradCAM)
  → Base de Datos e Histórico
  → Interfaz del Dashboard Clínico
```

**Módulos objetivo del repositorio:**
- `data/`
- `src/preprocessing/`
- `src/training/`
- `src/evaluation/`
- `src/inference/`
- `src/explainability/`
- `src/database/` (Conectores CRUD)
- `src/api/` (Rutas FastAPI)
- `configs/`
- `tests/`
- `docs/`

## 14. Roadmap de mejora

### Etapa 1: Orden y reproducibilidad
- **Objetivo:** Garantizar que no hayan fallas por semillas, y empaquetar en contenedores.
- **Tareas:** Dockerización (crear `Dockerfile`), refactorización del pre-commit.
- **Prioridad/Impacto:** Alta / Medio.

### Etapa 2: Evaluación robusta
- **Objetivo:** Cuantificar la validez estadística y clínica real.
- **Tareas:** Corregir posible fuga de datos de paciente si existe metadatos. Adquirir dataset cruzado (una muestra pequeña desde Internet o kaggle no NIH). Agregar `Bootstrapping` para Intervalos de Confianza (95%).
- **Prioridad/Impacto:** Crítica / Alto.

### Etapa 3: Mejora de modelos
- **Objetivo:** Optimizar métricas de FN.
- **Tareas:** Migrar de Custom CNN y VGG16 hacia un EfficientNetB0 con Focal Loss.
- **Prioridad/Impacto:** Media / Medio.

### Etapa 4: Explicabilidad profesional
- **Objetivo:** Hacer los mapas de GradCAM realmente útiles al humano.
- **Tareas:** Umbralización de los Grad-CAM para pintar cajas delimitadoras (Bounding Boxes) sobre el presunto parásito en vez de un mapa térmico difuso.
- **Prioridad/Impacto:** Media / Alto.

### Etapa 5: Sistema de apoyo diagnóstico
- **Objetivo:** Convertirse en una alerta inteligente.
- **Tareas:** Filtro de calidad de imagen. Integración total en tiempo real y UI para "Accept/Reject" el veredicto por parte del médico, retroalimentando a un módulo de aprendizaje activo.
- **Prioridad/Impacto:** Baja (futura) / Muy Alto.

## 15. Conclusión técnica

El estado actual del proyecto `malaria_dl_local_project` representa una sólida prueba de concepto con madurez técnica destacable para un proyecto de Capstone. Los autores han incorporado exitosamente las mejores prácticas de la industria en la orquestación (monitoreo de callback, early stopping), un criterio clínico (ParasitizedRecall), preprocesamientos homogéneos y una fantástica arquitectura de explicabilidad y registro (track-db y su API respectiva).

El sistema está muy preparado para presentarse. Para considerarlo un **sistema robusto y de nivel productivo biomédico real**, falta fundamentalmente resolver la independencia del dataset para evitar fuga de información por paciente y agregar controles de validación de calidad de imagen entrante. Se debe enfatizar fuertemente que **este es un sistema de apoyo a la sospecha diagnóstica** y no una máquina automática, y los módulos de explicabilidad actuales brindan precisamente el puente transparente necesario hacia el usuario clínico.

## 16. Anexo: checklist técnico

| Ítem | Estado | Comentario |
|---|---|---|
| Dataset documentado | **Implementado** | Bien documentado el origen (NIH) y uso TFDS. |
| Split reproducible | **Implementado** | Configuración de seed. |
| Preprocesamiento consistente | **Implementado** | El módulo de rescale y VGG16_imagenet es robusto. |
| Modelo entrenable | **Implementado** | Custom CNN y VGG16 entrenan bien, con callbacks de ES y Checkpoints. |
| Evaluación completa | **Implementado** | Sensibilidad, Accuracy, Specificity, F1, AUC. |
| Matriz de confusión | **Implementado** | Módulo métrico guarda y loguea la CM. |
| Métricas clínicas | **Parcialmente** | Muy buen `recall_parasitized`, falta IC (Intervalo Confianza) y validación externa. |
| Calibración | **Implementado** | Soporta Calibration JSONs. |
| Umbral configurable | **Implementado** | Vía cli parameter `--threshold`. |
| Inferencia separada | **Implementado** | Pipeline maduro en `predict_image.py`. |
| Explicabilidad | **Implementado** | Sobresaliente integración de LIME, SHAP y Grad-CAM. |
| Registro de predicciones | **Implementado** | Integración PG-DB (track-db). |
| Registro de artefactos | **Implementado** | Logueo automático. |
| Tests | **No encontrado** | Carece de suite de tests automatizados unitarios tipo `pytest`. |
| Documentación | **Implementado** | Bien organizado en `docs/` y `README`. |
| Instalación reproducible | **Implementado** | Requirements.txt disponible. |
| Dashboard o visualización | **Implementado** | Separado en `/frontend` (React) y `/backend_api`. |
| Preparación para despliegue | **Parcialmente** | Carece de contenedores Docker y configuraciones robustas de despliegue cloud. |
