# Matriz de reutilización

|Componente|Rutas|Responsabilidad/contrato actual|Consumidores|Clase|Justificación y modificación permitida|Compatibilidad/transición|Riesgo regresión|
|---|---|---|---|:---:|---|---|---|
|Paquete canónico|`malaria_dl_local_project/src/malaria_dl/**`|ML, tracking y gobierno|CLIs, backend, tests|B|Extender con interfaces Etapa 2 sin cambiar contratos clínicos|Imports públicos estables|Alto|
|Common/config|`malaria_dl/common`, `config`|Paths, settings, labels|Todo ML|D|Unificar settings/perfiles; preservar constantes|Facade temporal|Alto|
|Adaptadores `src.*` simples|`src/{train,evaluate,explain,models,...}.py`|Reexport/import alias|Scripts, tests, posibles externos|G|No agregar lógica; tests de contrato|Deprecar tras migrar imports internos|Alto|
|Legacy con lógica|`src/execution_types.py`, `model_execution_config.py`, `model_metadata.py`|Tipos/config/threshold heredado|TRAIN/EVALUATE/tests|D|Mover lógica canónica después, dejar facade|Release mayor para retiro|Alto|
|`src/model_governance`|`src/model_governance/**`|Facade/repositorio histórico|Servicios canónicos/tests|G|Preservar mientras Canon importe Legacy|Invertir imports gradualmente|Crítico|
|Training|`malaria_dl/training/**`|Entrena clasificador celular|TRAIN scripts|A/B|No alterar; añadir dataset adapter externo|Suites actuales como gate|Crítico|
|Evaluation|`malaria_dl/evaluation/**`|Métricas/calibración|EVALUATE, gobierno|B|Extender a crops y manifests patient-aware|Convención 0/1 inmutable|Crítico|
|Inference predictor|`malaria_dl/inference/predictor.py`|Inferencia celular, batch/TTA|CLI/tests|C|Encapsular como `CellClassifier`|Mantener CLI|Alto|
|Traceable inference|`malaria_dl/inference/traceable.py`|Inferencia gobernada single-image|API/governance smoke|D|Separar command/job execution y reutilizar resolución/cache|Endpoint legacy compatible|Crítico|
|Explainability|`malaria_dl/explainability/**`|Grad-CAM/LIME/SHAP batch|CLI/API lectura/UI|C|Adapter crop + tareas selectivas|Resultados históricos visibles|Alto|
|Cell detection boundary|`malaria_dl/cell_detection/**`|Sólo documentación|Ninguno|F|Crear contrato e implementaciones|Sin contrato previo que romper|Bajo|
|Image quality|`malaria_dl/data/quality_control.py`; `src/image_quality.py`|Chequeos básicos|Tests/uso CLI eventual|B|Conservar métricas como primitives; crear policy/service|Firma legacy intacta|Medio|
|Dataset registry|`malaria_dl/data/registry.py`|Manifest/split físico/checksum opcional|Scripts, browser, tests|B|Agregar fuente NIH y manifest patient-aware; no reutilizar split por imagen|Datasets históricos read-only|Alto|
|Backend API|`backend_api/app/**`|Consulta y gobierno FastAPI|SPA, tests|B/D|Nuevos routers modulares; middleware auth/audit; transacciones commands|Endpoints actuales versionados|Alto|
|DB helper|`backend_api/app/db.py`|Engines y SQL read helpers|Routers|D|Settings compartidos y unit-of-work|Mantener datasource query|Alto|
|Artifact service|`backend_api/app/services/artifacts.py`|Resolución confinada/MIME|Artifact/dataset routes|C|Colocar tras `StorageProvider`|IDs/URLs existentes traducidos|Alto|
|Frontend|`frontend/src/**`|Workbench de experimentos/gobierno|Usuarios web|B|Añadir módulo Frotis y auth; preservar Modelo IA|Rutas actuales intactas|Medio|
|API client/types|`frontend/src/services/api.ts`, `types/api.ts`|Cliente tipado|Todas las páginas|B|Dividir por dominios sin duplicar fetch|Exports actuales|Medio|
|Migraciones|`db/init/001–029`|Schema incremental SQL|init script/tests|G/D|Baseline Alembic en 029; no reescribir historia|Checksums previos preservados|Crítico|
|Runs/lineage|tablas `runs`, `run_lineage`; persistence|Ejecuciones y relaciones|Todo ML/API/UI|B|Reusar como envelope; entidades científicas especializadas|Vistas existentes|Crítico|
|Artifacts|tabla `artifacts` y releases|Metadata/checksum/path|Gobierno/XAI/API|B|Agregar storage URI/immutability scope|Paths históricos resolubles|Crítico|
|Model governance|`governance/**`, `model_versions`|Identidad/contrato/lifecycle|API/UI/inference|A/B|Reusar identidad; extender tipo detector/pipeline|No mutar checkpoint|Crítico|
|Stage2 Availability|`stage2_availability_service.py`; migration 028|Empaqueta, smoke y deployment slot|API/UI tests|D|Conservar mecánica, eliminar rol de fuente paralela|Migración de estados transaccional|Crítico|
|Stage2 Publication|`stage2_publication_service.py`; migration 029|Catálogo reversible multi-modelo|API/Run detail/UI|D|Definir catálogo; enlazar default deployment|Eventos append-only|Crítico|
|Deployments|`deployed_model_versions` / service|Alias activo, smoke, rollback|Inference/API/UI|B|Fuente inferible default; ampliar auditoría|Slots históricos intactos|Alto|
|`image_analysis_jobs`|migration 026/027, repository|Proveniencia/status de inferencia|Traceable/API|D|Evolucionar; attempts/events/priority/lease|Jobs legacy scope `image`|Crítico|
|Predictions|tabla `predictions`, views|Predicción legacy/image y columnas cell|API/XAI/UI|D|No seguir extendiendo; tablas nuevas + vistas compat|Lecturas legacy|Crítico|
|Releases|`releases/production`, `releases/stage2`; `releases.py`|Paquetes inmutables con manifests|Gobierno/inference|B|Reusar mecanismo tras provider|URI y checksums estables|Alto|
|Scripts|raíz `scripts/`, proyecto `scripts/`, run files|Operación/validación/DB/dataset|Desarrolladores|G/B|Mantener; añadir comandos no destructivos y perfiles|Flags actuales|Medio|
|Tests ML|`malaria_dl_local_project/tests`|368 pruebas de clasificación/gobierno|CI futura|A/B|Gate de regresión; sumar detección/pipeline|Python 3.12 ML|Bajo|
|Tests backend|`backend_api/tests`|API unit y E2E opt-in|CI futura|B|Agregar fixtures PostgreSQL efímeras y cobertura de contratos Etapa 2|No apuntar BD usuario|Medio|
|Tests frontend|`frontend/tests`|59 tests estáticos node|CI futura|D|Conservar y sumar DOM/browser E2E|Build como gate|Medio|

## Estrategia de transición

1. Congelar la convención clínica y APIs legacy con tests.
2. Formalizar ADRs de identidad Etapa 2, storage, cola, dominio y seguridad.
3. Introducir interfaces y tablas nuevas sin modificar outputs históricos.
4. Hacer que el pipeline nuevo consuma el mismo `model_version`/checkpoint.
5. Publicar vistas/adaptadores para consumidores antiguos.
6. Migrar imports Canon → Canon; después scripts/tests; por último advertir a externos.
7. Retirar adaptadores sólo con telemetría/evidencia y release mayor.
