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

## Gotchas
* Al devolver imágenes a través de la API de FastAPI, utiliza `FileResponse` o URLs prefirmadas apuntando al directorio/storage, no devuelvas payloads gigantes en JSON con base64.
* Genera los artefactos de explicabilidad de forma asíncrona o bajo demanda para no bloquear el throughput transaccional de la API.