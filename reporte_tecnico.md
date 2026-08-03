# Informe Técnico: Sistema de Diagnóstico de Malaria

## 1. Fortalezas del Sistema

El sistema actual demuestra un diseño orientado a la trazabilidad científica rigurosa y a la gestión del ciclo de vida de los modelos. Sus principales aciertos son:

- **Trazabilidad Inmutable y Reproducibilidad:** El sistema cuenta con un registro exhaustivo de ejecuciones (`runs`), checkpoints, métricas, y linaje de los modelos a través de una base de datos PostgreSQL. Esto permite auditar cada paso, desde el entrenamiento hasta la inferencia y las revisiones expertas. Las entradas y salidas del pipeline son congeladas para asegurar la reproducibilidad de los experimentos.
- **Arquitectura Modular Clara en Python:** El monolito está lógicamente separado en un backend API (FastAPI) y un núcleo de modelado (el paquete `malaria_dl` y `malaria_dl_local_project`). Esto facilita el testeo unitario, como se refleja en la alta cobertura de tests de las capas de clasificación clínica, la política de checkpoints, y los contratos de datos (`model_versions`, `runs`).
- **Control de Calidad Técnico Base:** El frontend y backend cuentan con un flujo dedicado para el control de calidad previo a la clasificación (`check_image_quality`), evaluando la resolución, enfoque (varianza laplaciana), contraste (p95-p05), brillo, y exposición. Esto protege al pipeline de falsos negativos causados por imágenes ilegibles o corruptas.
- **Soporte Incorporado para XAI (Explicabilidad):** La implementación robusta de Grad-CAM, LIME y SHAP está integrada directamente en los flujos de inferencia clínica (`run_explain_all_trainings.py` y `pipeline.py`). Es capaz de brindar retroalimentación visual al científico, mostrando claramente las áreas que guiaron la predicción del modelo (zonas de activación).
- **Mecanismo de Gobierno y Calibración:** Los modelos se despliegan utilizando alias, resolviendo `stage2/default` para la inferencia, asegurando un despliegue sin impacto destructivo. Los umbrales de decisión (`threshold`) y la calibración son persistidos inmutablemente en el contrato de metadatos, garantizando que el recall siempre priorice la minimización de falsos negativos acorde a los requisitos experimentales y evitando colapso predictivo.

## 2. Debilidades y Cuellos de Botella

- **Ausencia del Sub-Pipeline de Detección (RBCNet/Crop):** El pipeline está documentado y estructurado para procesar células recortadas (crops), pero el módulo de detección y segmentación celular para frotis de campo completo ("full smear") aún está vacío (`cell_detection/README.md`). Toda la inferencia asume entradas que son ya imágenes de células en vez de extraerlas dinámicamente. Esto representa una limitante funcional severa para llevar el sistema a la producción.
- **Deuda Técnica y Acoplamiento Legacy:** El diseño presenta dependencias invertidas temporales. En lugar de ser puramente consumidores, módulos en el paquete core (`src.malaria_dl`) aún importan y dependen de los adaptadores y servicios legacy (por ejemplo, `traceable.py` depende de `model_governance`, `model_deployment_service`). Esto dificulta refactorizaciones a futuro y mantiene una base de código monolítica donde el modelo ML está acoplado con reglas de negocio del backend.
- **Cuello de Botella en Procesamiento Síncrono:** La inferencia trazable, la evaluación de calidad de imagen y los trabajos (`image_analysis_jobs`) se realizan de forma síncrona dentro del *threadpool* HTTP de FastAPI. Para imágenes de alta resolución, frotis densos (miles de células) y modelos pesados, esto ocasionará timeouts y bloqueará el servidor web si múltiples muestras se analizan al mismo tiempo. No existe un worker o sistema de mensajería asíncrono para gestionar trabajos largos.
- **Falta de Abstracción en Almacenamiento y Archivos:** El sistema maneja blobs (las imágenes en sí) refiriendo rutas absolutas del *filesystem* en múltiples tablas de la BD, sin un `StorageProvider` abstracto u Object Storage unificado (tipo AWS S3 o MinIO). Esto dificulta enormemente la escalabilidad horizontal y las migraciones.
- **Rigidez del Control de Calidad:** Las reglas de validación de las imágenes tienen valores literales codificados fijos ("hardcoded thresholds" para exposición y foco). Una regla fija no adaptable para distintas calidades de muestra puede generar altas tasas de rechazo injustificado en situaciones del mundo real.

## 3. Mejoras de Programación y Buenas Prácticas

### Backend y Modelos
- **Desacoplamiento e Inyección de Dependencias:** Evitar que `malaria_dl` importe librerías de infraestructura como servicios de base de datos o lógica de FastAPI. Utilizar el patrón *Dependency Injection* o arquitecturas limpias, de modo que `malaria_dl` ofrezca interfaces genéricas que FastAPI consuma.
- **Colas y Tareas Asíncronas (Workers):** Sustituir el mecanismo actual basado en bases de datos relacionales por colas formales para las tareas intensivas. Celery (con Redis/RabbitMQ) o simplemente una arquitectura basada en `asyncio` con workers en un contexto distinto para descargar las peticiones HTTP y retornar IDs de Job para que el frontend haga *polling* de estado o se implementen *WebSockets* / *Server-Sent Events* (SSE).
- **Abstracción del Almacenamiento:** Implementar un patrón `StorageProvider` para ocultar la lógica de disco local. Las tablas deben guardar identificadores/URIs universales que el *Provider* resuelva, lo que preparará el sistema para almacenamiento en la nube (MinIO/S3).
- **Validación del Dominio y Seguridad:** Emplear una capa de autorización más fuerte; actualmente, no existe control de roles (RBAC) sólido y hay parámetros (actor, requester) dependientes del cliente. Además, utilizar `Pydantic` estrictamente para validaciones de entrada más complejas (ej. tipos MIME y restricciones de tamaño en los uploaders).

### UI/UX y Frontend Modular en JavaScript/React
- **Gestión del Estado de UI/UX para Imágenes Pesadas:** Actualmente los componentes React manejan la carga, visualización y colas mezclando los responsos lógicos y los efectos visuales. Se debe adoptar una estrategia de carga "perezosa" (Lazy Loading) y compresión de thumbnails al mostrar frotis gigantes o una extensa lista de células. Implementar WebSockets (o Server-Sent Events) para que el frontend no tenga que requerir manualmente (`poll`) la UI de forma constante durante cargas e inferencias pesadas.
- **Modularidad del Frontend:** Fragmentar los gigantescos archivos React (como `SmearWorkflow.tsx` y `SmearUpload.tsx`) que manejan simultáneamente subida de archivos, estados de máquina, vistas condicionales y llamadas de red. Utilizar librerías orientadas a estado del servidor como `React Query` (TanStack Query) o `SWR` para desacoplar el caché de red y refactorizar en componentes más pequeños (ej: `UploadDropzone`, `CaseContext`, `WorkflowProgress`).
- **Validación Robusta de Archivos:** La validación de MIME de imagen y límites de tamaño deben hacerse localmente mediante JavaScript antes del upload de la red, mejorando la UX del operador.

## 4. Evolución Tecnológica y Despliegue

### Trazabilidad y MLOps
- **Registro Externo de Experimentos (MLflow/Weights & Biases):** En lugar de depender exclusivamente de la implementación casera de PostgreSQL para registrar checkpoints y métricas de modelo, integrar el backend ML con plataformas como MLflow. Esto brinda versiones comparativas out-of-the-box, versionado de modelos, tracking automático, visualización rica y alertas.
- **Canalización y Pipeline de Modelos:** Integrar un Data Version Control (DVC) si el conjunto de datos de frotis excede volúmenes tratables. Conectar DVC a las bases PostgreSQL para crear flujos de MLOps automatizados que se reentrenen al introducir nuevos datos de frotis anotados por los científicos.

### Despliegue, Empaquetado y Contenerización
- **Arquitectura en Contenedores (Docker):** El sistema carece de Docker u orquestación como Docker Compose. Para aislar la solución y que la inferencia sea predecible en la clínica, se deben contenerizar:
  1. La Base de Datos PostgreSQL.
  2. La API FastAPI (Servidor Web).
  3. El(Los) Worker(s) de Inferencia y Detección.
  4. El Frontend servido a través de NGINX o similar.
- El uso de Docker garantizará que las dependencias conflictivas (ej: TensorFlow GPU y dependencias C++ como OpenCV/Pillow) se unifiquen, garantizando portabilidad.
- **CI/CD Robusto:** Incorporar flujos automatizados de *GitHub Actions* o *GitLab CI* que corran pre-commits, formaters (`black`, `isort`), type checkers (`mypy`, TypeScript tsc), tests end-to-end, y validen las migraciones (ej: integrar `alembic` propiamente para grafos de base de datos).

### Optimizaciones de Visión Computacional e Inferencia (Entorno Clínico)
- **Aceleración de TensorFlow a TensorRT / ONNX Runtime:** Para inferencia rápida en CPU o GPUs de clínicas periféricas, la conversión del modelo convolucional de TensorFlow Keras a ONNX Runtime u optimización vía TensorRT resulta en descensos drásticos de tiempo de latencia.
- **Optimizaciones del Cálculo Grad-CAM:** Generar un Grad-CAM para cada célula clasificada como parásito en un frotis de miles de cultivos asfixiaría el hardware. Recomendación: calcular Grad-CAM de forma diferencial bajo demanda ("on-demand API"), limitándolo a los crops donde la certeza se posicione entre un umbral medio de revisión o a peticiones puntuales del patólogo.
- **Detección Celular de Campo Amplio Optimizada (Crops):** Para solventar el vacío de la detección, integrar arquitecturas YOLOv8/YOLOv10 o un derivado específico como Mask R-CNN para la segmentación de cajas de delimitación y crops, que son mucho más ágiles sobre imágenes en mosaico ("Tiling") de las microscopías masivas, sin necesidad de calcular la clasificación binaria de cada caja vacía.
