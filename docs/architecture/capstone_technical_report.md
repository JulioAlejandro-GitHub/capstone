# Reporte Técnico de Arquitectura: Capstone MIA

**Autor:** Arquitecto de Software Principal / Líder Científico IA
**Fecha:** Octubre 2026 (Actualizado)

---

## 1. Resumen Ejecutivo

**Capstone MIA** es una plataforma científica experimental, diseñada como un monolito modular y contenedorizado, orientada a garantizar la trazabilidad extrema, reproducibilidad y validación humana inmersiva (Human-in-the-Loop) de pipelines de Deep Learning aplicados a la detección microscópica y clasificación celular de malaria, no con fines de diagnóstico clínico final, sino como entorno riguroso de orquestación y gobierno de modelos IA.

---

## 2. Flujo de Datos Extremo a Extremo (E2E)

El ciclo de vida de un dato científico atraviesa desde su ingesta hasta su validación humana en la interfaz inmersiva, garantizando la inmutabilidad de resultados en cada fase:

1.  **Ingesta y Partición Gobernada (malaria_dataset_split_project):**
    *   Descarga automatizada del dataset (NIH/NLM).
    *   Generación de versiones de dataset inmutables, con partición estratificada por paciente (Patient-disjoint split) para evitar *data leakage*.
    *   Generación de *fingerprints* (SHA-256) de los datos materializados en PostgreSQL para auditoría permanente.
2.  **Entrenamiento y Experimentación (malaria_dl_local_project):**
    *   Validación obligatoria de los *fingerprints* de la versión del dataset antes de ejecutar operaciones.
    *   Ejecución de experimentos locales (TRAIN, EVALUATE). Los modelos (Custom CNN, VGG16, DenseNet121 o ensambles E8) se entrenan con un estricto preprocesamiento y optimización de hiperparámetros.
    *   Generación de artefactos, métricas y metadatos clínicos (evaluaciones umbralizadas, ROC-AUC, F2, reportes de explicabilidad LIME/SHAP/Grad-CAM).
3.  **Trazabilidad y Orquestación (backend_api):**
    *   Recepción estructurada de predicciones del modelo.
    *   Persistencia relacional pseudonimizada garantizada: `Sujeto -> Caso -> Muestra (Sangre) -> Frotis -> Imagen (Microscopía)`.
    *   Aplicación de Quality Gates: Validación criptográfica e integridad antes de aceptar la inferencia o manifestación para inferencia de lotes (Runs productivos/experimentales).
4.  **Revisión y Validación Humana (frontend):**
    *   **Vista Científicos de Datos:** Visualizan métricas de campañas, reportes técnicos (matriz de confusión, PR-AUC, *prediction collapse*) y explicabilidad visual (Grad-CAM) para gobernar las versiones de los modelos.
    *   **Vista Expertos en Frotis:** Interfaz de validación de imágenes microscópicas, visualización inmersiva de detecciones YOLO y clasificaciones de la CNN, junto con mapas Grad-CAM para asegurar que la IA presta atención clínica razonable.

---

## 3. Matriz de Componentes

La interacción sistémica de los 7 subsistemas configura el monolito operado por Docker Compose.

| Subsistema | Naturaleza / Tecnologías | Responsabilidad y Flujo |
| :--- | :--- | :--- |
| **`backend_api`** | Python, FastAPI, SQLAlchemy | Centro neurálgico de operaciones. Orquesta APIs para frontend, y actúa de guardián de persistencia en PostgreSQL de experimentos, *quality gates*, predicciones clínicas y configuraciones E2E. |
| **`frontend`** | React, TypeScript, Vite, NGINX | Provee UI inmersiva SPA. Interactúa exclusivamente con `backend_api` a través de REST. Gestiona las vistas especializadas de Científicos y Hematólogos. |
| **`malaria_dl_local_project`** | Python, TensorFlow, Keras | Núcleo de IA. Realiza detección de celdas (YOLO) y clasificación (CNN/DenseneNet121). Emite métricas de *explainability* (LIME/Grad-CAM) y requiere PostgreSQL validado (`dataset_version_id`) para actuar. |
| **`malaria_dataset_split_project`**| Python (Scripts automatizados) | Fuente externa gobernada. Descarga TFDS, hace la partición *patient-level* E1, materializa los manifiestos, valida fugas de datos y sella la base fundacional de experimentación en BD. |
| **`smear_segmentation_project`** | Pipeline Experimental | Ecosistema de entrenamiento experimental acoplado para YOLO. Su objetivo es iterar la detección antes de insertarla al pipeline de clasificación `malaria_dl`. |
| **`docs`** | Markdown, Mermaid | Repositorio de verdad. Contiene el contrato, ADRs, registros de riesgos (Stage0 a Stage2) y guías de infraestructura, gobernando el estado del arte y deuda técnica del proyecto. |
| **`graphify-analysis`** | Módulo de análisis (Experimental) | Módulo adyacente para validación analítica avanzada y representación gráfica experimental, acoplado al análisis post-entrenamiento. |
| **`db` (Docker Compose)** | PostgreSQL 17.9 | Almacenamiento central del entorno. Administra identidades estables, configuraciones, *snapshots* y resultados inmutables (append-only) de ML mediante SQLAlchemy/Alembic. |

---

## 4. Conclusión Tecnológica

La arquitectura evaluada presenta un **nivel excepcional de robustez** para su fin declarado: una plataforma de experimentación científica.

- **Fortalezas del Diseño:** La separación tajante entre los datos físicos del modelo y la identidad inmutable relacional en PostgreSQL es un acierto rotundo, evitando la corrupción del dataset. La estrategia de encapsulamiento mediante Docker Compose garantiza reproducibilidad, al unificar dependencias de bases de datos, APIs y servidores web estáticos. El diseño *offline-first* para los modelos (previa carga desde BD) demuestra una madurez alta al no congestionar el sistema con entrenamiento síncrono. La adopción de validación *Human-in-the-loop* apoyada con métricas clínicas (sensibilidad/F2 por sobre *accuracy* global) y explicabilidad (Grad-CAM) refleja una comprensión profunda del dominio médico, donde entender *por qué* el modelo se equivoca es más valioso que una precisión opaca.
- **Limitaciones Contextuales:** Operar como monolito modular en Compose asume un despliegue "Vertical" o de *Single Instance* (como certifica su arquitectura), lo cual es ideal para experimentación y validación local o en laboratorios aislados, pero no escala elásticamente en nube de forma automática (K8s no provisto). Esto no es un defecto, sino una decisión arquitectónica informada para simplificar la orquestación en la presente fase del proyecto (Stage 2).
- **Veredicto:** El estado técnico actual supera los estándares de una prueba de concepto (PoC), consolidando un entorno de orquestación MLOps de clase médica altamente disciplinado y documentado.