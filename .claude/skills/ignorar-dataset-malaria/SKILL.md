---
name: ignorar-dataset-malaria
display-name: Ignorar Dataset Malaria
description: Ignorar la carpeta malaria_dataset_split_project al explorar el proyecto: es un subsistema cerrado y estable; enfócate en frontend, backend_api y malaria_dl_local_project.
---

# Ignorar Dataset Malaria

## Resumen

El proyecto `malaria_dataset_split_project` contiene demasiados datos y ya es un sistema estable. Para no consumir tokens ni recursos de máquina innecesariamente, este skill instruye al agente a ignorar dicho directorio.

## Cuándo usar

- Siempre que el agente explore la estructura del proyecto o deba hacer análisis del código.
- Cuando haya solicitudes generales de arquitectura.

## Instrucciones

1. **Omitir inspección**: no leas, proceses, listes ni intentes analizar los archivos dentro de `malaria_dataset_split_project`.
2. **Asumir estabilidad**: considera que todo el pipeline de construcción de datasets funciona correctamente y está congelado.
3. **Focalización**: centra toda tu atención y análisis en los módulos en desarrollo activo (frontend, backend_api, malaria_dl_local_project).
