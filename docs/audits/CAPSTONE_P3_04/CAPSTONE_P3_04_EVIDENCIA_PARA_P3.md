# CAPSTONE-P3-04 — Evidencia técnica para P3

Fecha: 16 de noviembre de 2026, America/Santiago. Datasource: `malaria`.

El caso principal es el intento TEST `00b8d407-c672-4b68-9814-53c092d034ba`, asociado al TRAIN VGG16-SGD47 `87b3eff7-e09a-41c8-945d-bf31b3541adb`. Esta matriz prepara evidencia para actualizar P3; no constituye una presentación nueva.

| Criterio | Conclusión sustentable | Evidencia concreta | Fuente y visual | Límite obligatorio |
|---|---|---|---|---|
| I. Problema — 5 % | Apoyo a revisión microscópica con errores identificables y linaje. | Imagen original, score, threshold, checkpoint y XAI del caso celular. | Informe 06, principal_sample_lineage.json; diagrama de trazabilidad. | No atribuir diagnóstico autónomo validado. |
| II. Datos — 15 % | Dataset versionado y partición por paciente. | 22.180 TRAIN, 2.693 VAL, 2.685 TEST; 20 identidades de paciente en TEST principal. | dataset_versions.json, dataset_checks.json, principal_full_identity.json; tabla de splits. | Tres células XAI no representan toda la población. |
| III. Soluciones IA — 30 % | Comparación de aprendizaje, arquitectura, clínica, errores, XAI y representaciones con alcance explícito. | 28 épocas principales; métricas reproducidas; errores pareados y CKA. | Informes 05–07; figuras y CSV de comparación. | BiomedCLIP está fuera del selector actual; CKA de GAP no describe toda la cabeza. |
| IV. Sensibilidad y costos — 30 % | Threshold controla el equilibrio FN/FP; las configuraciones y tiempos están registrados. | En VAL, bajar t de 0,5 a 0,25117 reduce FN 63→26 y aumenta FP 96→246. TEST tiene 47 FN; TRAIN dura 2.166,37 s. | threshold_reproduction.json, runs.json; tabla de tradeoff y confusión. | No hay costo monetario/energético ni IC en esta vista; tiempo no equivale a costo clínico. |
| V. Conclusiones y futuros — 20 % | Separar implementado, ejecutado, recuperable y validado. | Nueve XAI de tres células; cuatro matrices principales; ausencias globales identificadas. | Informes 07–08; matriz de cobertura y manifiesto físico. | No afirmar morfología validada ni cumplimiento de 98 % en TEST. |

## Afirmaciones utilizables con procedencia

- **CÁLCULO REPRODUCIDO:** en 2.685 células TEST de 20 identidades de paciente, VGG16-SGD47 alcanza sensibilidad 96,43 % al umbral 0,25117, con 47 FN y 223 FP. Fuente: [métricas reproducidas](evidence/metric_reproduction.json).
- **HECHO VERIFICADO:** la selección conserva época 1 por F2 VAL a threshold 0,5; después se fija el threshold con VAL y se evalúa ese checkpoint en TEST. Fuente: [sesiones](evidence/training_sessions.json), [calibración](evidence/principal_calibration_record.json). F2 no es la pérdida de entrenamiento.
- **CÁLCULO REPRODUCIDO:** dos VGG tienen GAP idéntico y CKA=1, pero decisiones distintas. Fuente: [features](evidence/vgg_embedding_identity.json), [errores](evidence/pairwise_errors.json). No demuestra igualdad de conceptos médicos.
- **HECHO VERIFICADO:** Grad-CAM, LIME y SHAP existen para tres células principales y sus binarios comprobados son íntegros. Fuente: [mapas](csv/principal_xai_maps.csv), [inventario](csv/artifact_inventory.csv). No acredita localización experta de parásitos.
- **HECHO VERIFICADO:** el motor conserva evaluaciones BiomedCLIP, pero el catálogo de la página ofrece tres familias CNN por su filtro model_type. Fuente: [catálogo real](evidence/catalog_response.json) y CatalogService.models.

## Figuras y contexto obligatorio

[Aprendizaje](figures/principal_learning.png), [confusión TEST](figures/principal_confusion.png), [PCA/UMAP persistidos](figures/principal_representations.png). Son derivados de auditoría, no capturas UI.

Cada uso en P3 debe conservar TRAIN, intento, split, dataset version, checkpoint/hash, threshold y N. Las curvas usan TRAIN/VAL; las proyecciones corresponden a REPRESENT TEST `d6f269de-ba63-4a17-9df8-3bd2ce1871b2`. El checkpoint compartido tiene SHA `b26f6e2c66fd5356028ba41eaee603f0c88a2a925b39cb6b21b0fafd79aa24fa`.

TCAV, anotaciones expertas, validación externa y costos son trabajos futuros propuestos; no se presentan como resultados existentes. No se modificaron documentos P3 anteriores.
