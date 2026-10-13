A. ESTRUCTURA REAL ACTUAL
malaria_dl_local_project/src/malaria_dl/
├── data/
│   ├── governed_dataset.py
│   ├── registry.py
│   ├── loaders.py
│   ├── export.py
│   └── input_contract.py
├── models/                     # plural; no model/
│   ├── adapters.py
│   ├── architectures.py
│   ├── configuration.py
│   └── registry.py
├── training/{cli.py,trainer.py,checkpoint_policy.py}
├── evaluation/{cli.py,evaluator.py,evaluation_training_lineage_service.py}
├── inference/{cli.py,predictor.py,pipeline.py}
├── cell_detection/{__init__.py,README.md}
├── config/{settings.py,execution.py}
├── execution/
│   ├── train.py
│   ├── artifacts.py
│   ├── contracts/{context.py,events.py,reporter.py}
│   └── reporters/
├── persistence/{dataset_evidence.py,lineage.py,tracking.py}
└── common/{paths.py,serialization.py}

backend_api/app/
├── models/cell_detection.py
├── services/
│   ├── cell_analysis.py
│   ├── detectors/{resolver.py,connected_components_v1.py}
│   └── crops/{resolver.py,bbox_crop_v1.py}
└── config.py
cell_detection/ del paquete ML no implementa detección; su README está desactualizado respecto del backend. Prediction reside en inference/. No existe adapter de segmentación en el árbol inspeccionado; models/adapters.py adapta modelos clasificadores.
B. PIEZAS REUTILIZABLES
- data/governed_dataset.py: resolución de Dataset Version congelada, materialización y fingerprints; conservar splits y procedencia.
- execution/contracts/, execution/reporters/: contratos y transporte de eventos; no crear otro sistema de reporting.
- execution/artifacts.py: identidad/verificación física del checkpoint; reutilizar utilidades compatibles, no asumir que verify_session() es genérico.
- Backend: conservar Detector, DetectionResult, resolvers y separación detection/crop.
- No reutilizar directamente los loops Keras, callbacks clínicos, loader .keras, preprocesamiento clasificatorio ni métricas binarias. models/configuration.py y el registro actual también tienen restricciones específicas: YOLO no se habilita únicamente agregando un nombre.
C–D. UBICACIÓN Y RESPONSABILIDADES
Rutas relativas a malaria_dl_local_project/src/malaria_dl/, salvo la última:
Ruta propuesta	Responsabilidad
data/yolo_segmentation_adapter.py	S4: transformar anotaciones y splits existentes en dataset YOLO derivado, conservando identidad y trazabilidad.
models/yolo26_seg/	Código específico del modelo, independiente de clasificación.
models/yolo26_seg/configuration.py	Configuración específica compartida, con parámetros diferenciados por etapa.
models/yolo26_seg/contracts.py	Contratos del modelo, checkpoint y salidas de segmentación.
models/yolo26_seg/loader.py	Carga única del checkpoint YOLO.
models/yolo26_seg/processing.py	Transformaciones y conversión de salidas comunes; aumentación exclusiva de TRAIN.
training/yolo26_seg.py	S5: entrenamiento y selección de checkpoint con train/val.
evaluation/yolo26_seg.py	S6: evaluación de segmentación vinculada al checkpoint y Dataset Version.
cell_detection/yolo26_seg.py	Futuro runtime ML: inferencia usando loader y procesamiento compartidos.
backend_api/app/services/detectors/yolo26_seg.py	Futuro adaptador servido al contrato Detector/DetectionResult existente.


El dataset derivado y los checkpoints son artefactos fuera de src/.
Dataset Version
↓ S4 data/yolo_segmentation_adapter.py
YOLO dataset derivado
↓ S5 training/yolo26_seg.py
checkpoint
↓ S6 evaluation/yolo26_seg.py
detector validado
↓ runtime/serving futuro
CELL DETECTION existente
↓
CELL CROP existente
↓
clasificación intacta
E. DECISIÓN
RECOMMENDED STRUCTURE:
malaria_dl_local_project/src/malaria_dl/
├── data/yolo_segmentation_adapter.py
├── models/yolo26_seg/
│   ├── configuration.py
│   ├── contracts.py
│   ├── loader.py
│   └── processing.py
├── training/yolo26_seg.py
├── evaluation/yolo26_seg.py
└── cell_detection/yolo26_seg.py               # posterior a S6

backend_api/app/services/detectors/
└── yolo26_seg.py                             # posterior a S6
- ¿S4 dentro de yolo26_seg? NO. Adapta datos a un formato; corresponde a data/, sin depender del modelo.
- ¿TRAIN/EVALUATE reutilizan infraestructura? YES. Dataset gobernado, reporting, identidad de artefactos y trazabilidad compatible; requieren lógica científica de segmentación.
- ¿Runtime comparte carga/pre/postprocesamiento? YES. Compartir lo común, manteniendo las transformaciones específicas de entrenamiento separadas.
- ¿La propuesta duplica código existente? NO. Siempre que consuma esas utilidades y contratos, sin copiar clasificadores, resolvers ni reporting.
- ¿Mover connected_components_v1 o bbox_crop_v1? NO.
- ¿Migración BD? NO para esta decisión de estructura. La compatibilidad de persistencia de métricas de segmentación en S5/S6 no queda demostrada por esta auditoría estructural.