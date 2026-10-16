---
name: dataset-governance-guardian
description: Gobernar datasets versiones y splits de malaria evitando exploración masiva innecesaria.
---

# dataset-governance-guardian

## Reglas
- `malaria_dataset_split_project` administra origen, disponibilidad, particiones y `dataset_version_id`.
- `malaria_dl_local_project` consume versiones de dataset para clasificación; `smear_segmentation_project` las consume para segmentación/detección YOLO y futuros.
- Conservar identidad de versión y SAME SPLIT cuando la comparabilidad lo exija.
- Nunca utilizar TEST para entrenar ni validar; no duplicar descargas ni datasets sin necesidad.
- No ignorar indiscriminadamente el proyecto split: inspeccionar contratos o código cuando la tarea lo requiera; excluir binarios pesados y exploraciones recursivas.

## Referencias
- `references/dataset-contract.md`
- `references/legacy-ignore-policy.md` (histórica).
