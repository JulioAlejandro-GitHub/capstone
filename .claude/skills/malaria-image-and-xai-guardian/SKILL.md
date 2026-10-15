---
name: malaria-image-and-xai-guardian
description: Activa este skill al trabajar con subida de imágenes, frotis, crops celulares, referencias en BD o generación de explicabilidad visual (Grad-CAM, SHAP, LIME).
---

# Malaria Image Storage & XAI Guardian

## Summary
Este skill rige el ciclo de vida de los archivos binarios (imágenes, frotis, recortes y mapas de calor), garantizando su almacenamiento en directorios y su correcta referencia en PostgreSQL, además de regular la salida científica del modelo de ML[cite: 4].

## When to Use
* Al diseñar endpoints de subida de imágenes (ingesta de frotis).
* Al manipular crops celulares para inferencia o entrenamiento.
* Al generar y almacenar explicaciones visuales de ML (`app/services/explainability.py`)[cite: 3].

## Core Rules & Steps
1. **Persistencia Referencial Estricta (Imágenes y Artifacts):**
   * **NUNCA** almacenes arrays de píxeles, imágenes completas, crops celulares o mapas de calor en PostgreSQL en formato binario o base64[cite: 4].
   * Todos los binarios pesados (frotis de entrada, crops de dataset, heatmaps XAI) residen exclusivamente en directorios físicos o `Artifact Storage`[cite: 4].
   * En `PostgreSQL` SOLO se deben registrar los metadatos y las rutas relativas o URIs (ej. `file_path`, `image_url`) que referencian al archivo físico[cite: 4].
2. **Salida Científica de Soporte (No Diagnóstica):**
   * Todo resultado o reporte de inferencia generado debe formularse estrictamente como *análisis parasitario de apoyo a la decisión*, nunca como diagnóstico clínico concluyente[cite: 3].
   * El pipeline exige que la clasificación y la explicabilidad desemboquen siempre en la etapa final de `revisión humana`[cite: 3].
3. **Coherencia Espacial en Explicabilidad:**
   * La explicabilidad (ej. Grad-CAM) se aplica sobre el recorte de la célula detectada (crop), manteniendo la referencia inmutable al ID de la imagen y del frotis original en la base de datos[cite: 3].

### Contrato científico de artefactos y visualización XAI — SCC-ART.1 / SCC-XAI.1

Al recuperar, presentar, comparar o generar evidencia visual de explicabilidad de modelos de IA, aplicar los contratos científicos y de trazabilidad vigentes de Capstone.

**Documentación de referencia:**

- `docs/contracts/scc_art_1.md`: recuperación segura de artefactos científicos.
- `docs/contracts/capstone_ui_css_policy.md`: sistema visual de reportes.
- `docs/contracts/scc_xai_1.md`: contrato del visor XAI compartido, una vez implementado.

**Reglas obligatorias:**

1. **Identidades científicas independientes:** conservar y distinguir `training_run_id`, `assessment_identity_id`, `attempt_id`, `sample_id` y `artifact_id`. No tratarlos como identificadores intercambiables.

2. **Linaje verificable:** toda evidencia XAI debe mantener su relación con el TRAIN de origen, el modelo/checkpoint utilizado, la muestra explicada, el método XAI, el intento de ejecución y el artefacto correspondiente.

3. **Recuperación autenticada:** recuperar los artefactos mediante el mecanismo HTTP autenticado existente, utilizando el `artifact_id` real y el origen correspondiente (`source=assessment` para artefactos EXPLAIN). No exponer rutas físicas del servidor como URLs públicas.

4. **Integridad:** respetar las verificaciones de autorización, pertenencia, confinamiento de rutas y SHA-256 implementadas por el backend. No presentar como evidencia válida un artefacto cuya integridad haya fallado.

5. **Persistencia:** almacenar imágenes, mapas de calor, overlays y otros binarios científicos fuera de PostgreSQL. Registrar en la base de datos sus identificadores, referencias, metadatos y relaciones de trazabilidad según el esquema vigente.

6. **Composición XAI compartida:** presentar la evidencia de cada muestra en cuatro cuadros de posición fija:

   `[Célula original] [Grad-CAM] [LIME] [SHAP]`

   Mantener los cuatro cuadros visibles aunque alguno carezca de evidencia.

7. **Comparabilidad:** agrupar únicamente evidencias compatibles de la misma muestra, TRAIN y checkpoint. Los métodos pueden proceder de distintos intentos EXPLAIN, pero deben conservar sus identidades originales. No mezclar muestras, modelos ni checkpoints incompatibles.

8. **Referencia original:** la célula original debe corresponder a la muestra explicada. No confundir el `background_sample_id` utilizado por SHAP con el `sample_id` de la célula explicada.

9. **Estados de evidencia:** distinguir explícitamente entre disponible, no ejecutado, pendiente, ejecutándose, fallido, artefacto faltante, acceso denegado, integridad fallida y evidencia no comparable. No representar errores técnicos como ausencia de evidencia científica.

10. **Visualización reutilizable:** utilizar un único componente React compartido para las modalidades integrada y modal. Reutilizar el cliente autenticado de artefactos y el sistema visual CAPSTONE-UI-TOKENS.1 mediante `.ds-report`.

11. **Rendimiento:** cargar imágenes bajo demanda o según la página visible, evitar solicitudes duplicadas, liberar recursos temporales y conservar la paginación de reportes extensos. El fallo de un método no debe bloquear los demás.

12. **Generación de métodos faltantes:** la interfaz puede representar la acción «Generar» para Grad-CAM, LIME o SHAP, pero solamente debe habilitarla cuando exista una operación real, autorizada y conectada. No simular ejecuciones ni inventar endpoints.

13. **Separación de fases:** SCC-XAI.1 implementa visualización y recuperación de evidencia existente. SCC-XAI.2 abordará la orquestación para generar los tres métodos y completar únicamente los faltantes. SCC-XAI.3 abordará la integración transversal en los reportes.

14. **Interpretación científica:** no inventar consensos, correlaciones, porcentajes de similitud, conclusiones clínicas ni interpretaciones automáticas a partir de la mera coexistencia de Grad-CAM, LIME y SHAP. Cualquier métrica comparativa requiere un procedimiento científico definido y evidencia verificable.

15. **Revisión humana:** conservar el carácter de apoyo a la decisión del análisis parasitario. La explicabilidad no constituye por sí misma un diagnóstico clínico concluyente.

16. **Protección de resultados históricos:** no sobrescribir artefactos ni resultados de intentos anteriores. Las nuevas ejecuciones deben preservar identidades y trazabilidad independientes.

**Regla de decisión:** ninguna imagen XAI debe presentarse como evidencia científica comparable si no puede acreditarse su identidad, procedencia y correspondencia con la muestra y el modelo analizados.

## Gotchas
* Al devolver imágenes a través de la API de FastAPI, utiliza `FileResponse` o URLs prefirmadas apuntando al directorio/storage, no devuelvas payloads gigantes en JSON con base64.
* Genera los artefactos de explicabilidad de forma asíncrona o bajo demanda para no bloquear el throughput transaccional de la API.