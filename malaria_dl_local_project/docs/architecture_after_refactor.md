# Arquitectura posterior al refactor

`src/malaria_dl` contiene `common`, `config`, `data`, `models`, `training`,
`evaluation`, `explainability`, `inference`, `persistence`, `governance` y la
frontera documental `cell_detection`.

`common.paths` fija la raíz del proyecto sin depender de la profundidad del
módulo. No se cambiaron SQL, endpoints, JSON/CSV, artefactos, thresholds,
lineage ni etiquetas.

Persisten módulos grandes dentro de su límite correcto:
`training/trainer.py`, `explainability/pipeline.py`,
`persistence/run_repository.py`, `persistence/tracking.py` y
`governance/repository.py`. Dividirlos internamente será una siguiente fase de
menor alcance; las pruebas de caracterización y los adaptadores permiten hacerlo
sin romper contratos.

