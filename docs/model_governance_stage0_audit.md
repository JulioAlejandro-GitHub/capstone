# Auditoría técnica Stage 0: gobierno y linaje de modelos

**Fecha de auditoría:** 2026-07-20<br>
**Repositorio:** rama main, commit bfdf3e8a2a498df73d1a5c588a10c940c52235c8<br>
**Alcance:** repositorio completo, artefactos locales gobernados y estado de PostgreSQL disponible durante la auditoría<br>
**Tipo de intervención:** análisis de solo lectura; este documento es el único cambio

> Regla Stage 0: **outputs/custom_cnn/best_model.keras no es una identidad de modelo**. Es un alias operacional mutable. La identidad oficial debe ser un model_version_id ligado a un artifact_id inmutable y verificable por checksum.

La convención clínica queda fijada y no se propone modificar:

- 0 = uninfected.
- 1 = parasitized.
- positive_label = parasitized.
- El score clínico es probability_parasitized.

## Metodología y alcance de la evidencia

La auditoría combinó:

1. Inventario de los 226 archivos versionados.
2. Lectura profunda de SQL, servicios ML, scripts, backend, frontend, documentación y pruebas.
3. Búsqueda global, sensible y no sensible a mayúsculas según el término, de todas las referencias solicitadas.
4. Inspección de los artefactos locales bajo outputs.
5. Consultas SELECT de solo lectura sobre la base malaria_experiments. No se ejecutaron DDL, DML, scripts de limpieza ni backfills.
6. Contraste entre la definición SQL versionada y las restricciones, filas y vistas existentes en PostgreSQL.

Los conteos de base de datos son una fotografía del 2026-07-20; no deben codificarse como invariantes.

## 1. Resumen ejecutivo

El repositorio ya posee una base útil de gobierno: runs tipados, model_versions, artifacts con SHA-256, run_lineage, calibraciones de threshold, métricas clínicas, snapshots bajo outputs/{model}/runs/{training_run_id} y vistas para el backend. Por ello **no corresponde crear tablas separadas para training runs, evaluation runs, explainability runs ni inference runs**. Todas son especializaciones de runs.

Sin embargo, el sistema todavía opera por rutas en varios puntos críticos:

- best_model.keras se sobrescribe durante el entrenamiento y al publicar un nuevo mejor modelo.
- El snapshot inmutable se crea tarde, después de cargar el alias genérico.
- Evaluación y explicabilidad reciben checkpoint_path; sus relaciones actuales no persisten model_version_id ni checkpoint_artifact_id.
- Explicabilidad comparte outputs/explainability entre ejecuciones. La base demuestra sobrescritura real: 90 rutas compartidas tienen checksums históricos distintos.
- Inferencia recibe archivos físicos, resuelve el threshold desde sidecars y no tiene vínculo con un deployment ni con un model version.
- No existen aún las entidades model_deployments ni image_analysis_jobs.
- El frontend es de observación, no de operación; no envía modelos para inferencia, pero sí conserva fallbacks por path para artefactos.

La situación histórica es recuperable sin borrar datos:

- Hay 12 training runs y 12 model_versions.
- Las 24 relaciones evaluation/explainability pueden vincularse de forma exacta y unívoca con una model_version y un artifact existentes.
- No hay grupos duplicados para las claves candidatas revisadas.
- Los snapshots registrados tienen rutas específicas por UUID y checksum.

La estabilización recomendada es incremental: agregar constraints y entidades mínimas, backfillear por coincidencia exacta, hacer obligatoria la finalización snapshot + artifact + model_version, aislar outputs por run, crear deployments inmutables y hacer que inferencia parta de deployment_id. Las rutas públicas actuales y los campos heredados deben mantenerse durante la transición.

## 2. Arquitectura actual

La solución se divide en cuatro capas:

- **Pipeline ML local:** comandos Python para entrenar, evaluar, explicar, calibrar e inferir.
- **Persistencia:** PostgreSQL mediante SQLAlchemy Core y SQL explícito; no hay modelos ORM declarativos ni Alembic.
- **Backend:** FastAPI de solo lectura, con endpoints GET y consultas SQL/vistas.
- **Frontend:** React 19 + Vite, navegación interna por estado y consumo de los endpoints GET.

### Endpoints actuales

main.py declara explícitamente la API como read-only y CORS solo habilita GET. No hay endpoint de entrenamiento, evaluación, explicabilidad, promoción ni inferencia.

| Área | Endpoints GET existentes |
|---|---|
| Salud/orígenes | /health; /datasources |
| Dashboard | /dashboard/summary; /dashboard/clinical |
| Runs | /runs y /api/runs; /runs/grouped-lineage y alias /api; /runs/clinical/summary y alias /api |
| Detalle de run | /runs/{run_id} y alias /api; /clinical-summary; /clinical-metrics; /checkpoint-policy; /threshold-calibration |
| Evidencia de run | /runs/{run_id}/artifacts y /artifacts-summary con aliases /api; /image-predictions; /io-records; /explainability |
| Catálogo | /models; /models/comparison y /api/models/comparison; /datasets |
| Dataset browser | /api/dataset; /summary; /split; /images; /images/{image_id}; /images/{image_id}/file |
| Métricas | /metrics/{run_id}; /confusion-matrix/{run_id}; /classification-report/{run_id} |
| Explicabilidad | /explainability; /cases; /cases/false-positives; /cases/false-negatives; /cases/low-confidence; /cases/summary; /gallery |
| Predicciones | /predictions/uploads |
| Observabilidad | /errors; /logs |
| Archivos | /artifacts/file por artifact_id y fallback path |

Los sufijos de detalle de run también poseen alias /api donde así están declarados en routes/runs.py. No existe un catálogo HTTP de model_versions aunque la tabla sí existe.

### Linaje actual

~~~mermaid
flowchart TD
    TRAIN["train.py / training run"] --> RUN_T["runs: training"]
    TRAIN --> ALIAS["outputs/model/best_model.keras<br/>alias mutable"]
    ALIAS -->|"se sobrescribe por época o run"| ALIAS
    ALIAS --> FINAL["final_model.keras"]
    ALIAS --> SNAP["outputs/model/runs/training_run_id/<br/>snapshot tardío"]
    SNAP --> ART["artifacts + SHA-256"]
    SNAP --> MV["model_versions<br/>training_run_id + paths"]

    PATH_E["checkpoint_path físico"] --> EVAL["runs: evaluation"]
    PATH_X["checkpoint_path físico"] --> EXPL["runs: explainability"]
    EVAL --> RL_E["run_lineage<br/>parent training; version/artifact NULL"]
    EXPL --> RL_X["run_lineage<br/>parent training; version/artifact NULL"]
    EVAL --> EOUT["checkpoint.parent/evaluation<br/>salida reutilizable"]
    EXPL --> XOUT["outputs/explainability<br/>salida global reutilizable"]

    PATH_I["checkpoint/model_path + sidecar threshold"] --> INF["runs: inference por imagen"]
    INF --> PRED["predictions"]
    INF --> RIP["run_image_predictions<br/>dual-write"]
    INF -. "sin deployment/version" .-> MV
~~~

### Matriz de componentes

| Componente | Estado actual | Problema | Cambio recomendado | Archivos relacionados |
|------------|---------------|----------|--------------------|-----------------------|
| Training runs | Reutiliza runs con run_type = training | La gobernanza final es best-effort y puede completar sin versión oficial | Hacer transaccional y obligatoria la finalización de snapshot, artifact y model_version | malaria_dl_local_project/src/train.py; run_tracker.py; tracking_integration.py |
| Checkpoints | Alias genérico más snapshot posterior por run | El alias se sobrescribe y el snapshot se crea tarde | Guardar primero en ubicación inmutable y actualizar el alias solo como compatibilidad | checkpoint_policy.py; train.py |
| best_model.keras | Alias operativo documentado extensamente | Puede apuntar a bytes distintos a lo largo del tiempo | Prohibirlo como identidad; resolver por model_version_id/artifact_id y checksum | train.py; checkpoint_policy.py; documentación y runners |
| Model versions | 12 filas ligadas a training runs y rutas UUID | La ruta es la identidad práctica; falta FK al artifact y lifecycle | Agregar checkpoint_artifact_id, estado y unicidad gradual | 001_schema.sql; run_tracker.py |
| Evaluation runs | runs + metrics/predictions/artifacts + run_lineage | Entrada por path; salida bajo el directorio del checkpoint; IDs de linaje nulos | Resolver por model_version_id y aislar output por evaluation_run_id | evaluate.py; run_evaluate_all_trainings.py; run_lineage.py |
| Explainability runs | runs + explainability_results + artifacts + run_lineage | Carpeta global y nombres reutilizables; sobrescritura comprobada | Carpeta por explainability_run_id y vínculo obligatorio a versión/artifact | explain.py; run_explain_all_trainings.py |
| Predicciones | predictions y run_image_predictions | Dual-write, semántica mezclada de evaluación e inferencia | Mantener predictions como tabla canónica y enlazar image_analysis_job_id; conservar la tabla heredada temporalmente | run_tracker.py; predict_image.py; 010 y 017 SQL |
| Thresholds clínicos | run_threshold_calibration, run_clinical_metrics y sidecars | El sidecar se puede mutar y el threshold no está ligado a una versión/deployment | Reutilizar run_threshold_calibration, agregar vínculo a versión/artifact y congelar el valor en deployment | calibrate.py; model_metadata.py; threshold_calibration.py; 017 SQL |
| Registro de artefactos | artifacts con path, checksum y run_id | Paths absolutos/no portables; duplicados de ruta; path aún expuesto | Canonizar por artifact_id + checksum; URI/clave relativa; constraint luego de reconciliar | run_tracker.py; artifacts.py; services/artifacts.py |
| PostgreSQL | 25 tablas y 25 vistas, SQL idempotente | Sin ledger de migraciones; FKs de lineage incompletas | Migraciones aditivas, schema_migrations y constraints NOT VALID/VALIDATE | db/init/*.sql; scripts/init_db.py |
| Backend de inferencia | No existe API de escritura/inferencia | Backend declarado read-only; solo consulta predicciones ya cargadas | Agregar API operativa separada y autenticada, basada en deployment_id/job_id | backend_api/app/main.py; routes/predictions.py; rutas nuevas |
| Frontend | Nueve pantallas de observación, navegación por estado | Sin registro de versiones/deployments/jobs ni deep links | Extender en forma aditiva y mantener PageKey/endpoints actuales | frontend/src/App.tsx; Layout.tsx; services/api.ts; types/api.ts |
| Linaje | run_lineage training → evaluation/explainability | Las 24 filas tienen model_version_id y checkpoint_artifact_id nulos | Backfill exacto y validación de pertenencia; conservar parent/child histórico | 022_run_lineage.sql; src/run_lineage.py |
| Tests | 68 archivos Python; buena cobertura unitaria de linaje y convención clínica | Sin tests frontend, E2E ni PostgreSQL real para constraints/concurrencia | Pirámide nueva de migración, contrato, integración y UI | malaria_dl_local_project/tests; backend_api/tests; frontend |
| Limpieza/backfill | Backfill con dry-run; scripts destructivos con confirmación | Limpieza puede romper referencias; backfill solo cubre eval/explain | Inventario, tombstone/retención y backfill por etapas sin borrar historia | scripts/backfill_run_lineage.py; clean_training_outputs.py; purge_db_data.py; reset_experimental_state.py |

## 3. Flujo actual de entrenamiento

### Secuencia observada

1. run_train_all_models.py invoca src.train para cada arquitectura.
2. train.py crea un run UUID y registra el run_type training.
3. La salida predeterminada es outputs/{model_name}.
4. ClinicalCheckpointCallback guarda el mejor checkpoint como best_model.keras con overwrite habilitado.
5. El pipeline guarda final_model.keras y vuelve a cargar best_model.keras para evaluación/selección.
6. Existen un lock por modelo y respaldo/restauración transaccional de archivos de nivel superior, lo que reduce corrupción ante fallos, pero no convierte el alias en inmutable.
7. Al terminar, train.py copia el mejor, el final y sus sidecars a outputs/{model_name}/runs/{training_run_id}.
8. run_tracker registra artifacts con SHA-256 y crea model_versions con training_run_id y las rutas del snapshot.

### Fortalezas reutilizables

- El ID del snapshot coincide con el UUID del training run.
- Los 12 model_versions existentes apuntan a paths UUID, no a aliases genéricos.
- Los 12 checkpoints y los 12 modelos finales registrados tienen checksum.
- El callback clínico, la política de selección y los metadatos de clases están centralizados.
- safe_track permite que el entrenamiento científico continúe si cae el tracking, útil para resiliencia experimental.

### Problemas

- La copia inmutable ocurre después de utilizar el alias mutable; una interrupción entre pasos puede dejar run, artifacts y model_version desalineados.
- safe_track absorbe errores y el retorno de log_model_version no gobierna el estado final. Un run puede quedar completed sin identidad oficial.
- log_model_version hace INSERT sin una clave de idempotencia ni constraint equivalente a training_run_id + version_name/checkpoint_artifact_id.
- El nombre de versión actual, por ejemplo {model}_tracked, no expresa lifecycle ni distingue promociones.
- run_checkpoint_policy conserva la ruta genérica outputs/{model}/best_model.keras. Es evidencia histórica de la política, no una referencia desplegable.
- Las rutas de model_versions son absolutas y dependen del host.

### Decisión Stage 0

El archivo oficial debe escribirse directamente en una ubicación inmutable por run; artifact y model_version deben registrarse en la misma finalización lógica. El alias best_model.keras puede actualizarse después, bajo lock y de forma atómica, solo como compatibilidad para comandos heredados.

## 4. Flujo actual de evaluación

evaluate.py acepta:

- --checkpoint.
- --source-training-run-id opcional.
- --require-lineage.

El orquestador run_evaluate_all_trainings.py consulta la model_version más reciente de cada training run, pero entrega al proceso nuevamente checkpoint_path y source_training_run_id. El pipeline carga Keras directamente desde esa ruta.

Resultados y trazabilidad actuales:

- Crea runs de tipo evaluation.
- Registra métricas, matrices, reportes, artifacts y predicciones.
- Inserta run_lineage con relationship_type = evaluates_checkpoint_from.
- Escribe resultados bajo checkpoint.parent/evaluation, por lo que repetir evaluación puede sobrescribir outputs de otra evaluación del mismo checkpoint.
- En la base viva existen 12 evaluaciones y ninguna está huérfana respecto de un training run.
- Las 12 relaciones tienen model_version_id NULL y checkpoint_artifact_id NULL.

### Brecha de validación

Cuando se entrega source_training_run_id explícito, src/run_lineage.py valida que exista y sea training, pero no demuestra que el checkpoint pertenezca a ese run. Esto permite registrar una relación falsa si se combinan un training_run_id válido y un checkpoint de otro run.

### Cambio incremental

Agregar --model-version-id como entrada preferida. El backend/resolver debe:

1. Resolver model_version.
2. Resolver checkpoint_artifact_id.
3. Verificar run propietario, checksum, tamaño y existencia.
4. Crear evaluation run.
5. Escribir en outputs/evaluation/{evaluation_run_id}.
6. Persistir ambos IDs en run_lineage.

--checkpoint se conserva temporalmente como modo legacy; en modo gobernado debe resolver de forma exacta o fallar sin seleccionar “el último”.

## 5. Flujo actual de explicabilidad

explain.py implementa LIME, SHAP y Grad-CAM. Recibe checkpoint físico y parámetros de casos/métodos, crea un run de explainability, escribe explainability_results y artifacts, y crea lineage hacia un training run.

El orquestador run_explain_all_trainings.py pasa checkpoint y source_training_run_id, pero no un output aislado. El default es outputs/explainability. Los nombres incluyen método, tipo de caso, identificador y probabilidad, pero no model_version_id ni explainability_run_id; explanation_summary.csv también es global.

### Evidencia de sobrescritura

- 1.612 filas de artifacts de explainability representan 1.457 paths distintos.
- Hay 97 paths usados por más de un run.
- En 90 de esos paths la base conserva checksums diferentes.
- outputs/explainability/explanation_summary.csv aparece en 12 runs con 12 checksums.

La base histórica sabe qué bytes existieron, pero una sola ruta local no puede representar simultáneamente todos esos estados. No debe asumirse que el archivo actual reproduce el artifact histórico.

### Cambio incremental

- Entrada primaria model_version_id.
- Output obligatorio outputs/explainability/{explainability_run_id}.
- Nombres o subdirectorios que incluyan el run UUID.
- Registro de source artifact y outputs antes de marcar completed.
- run_lineage con model_version_id y checkpoint_artifact_id obligatorios para escritores nuevos.
- Si el artifact histórico no coincide con el checksum actual, marcarlo missing_or_mutated; no reescribir el checksum histórico.

## 6. Flujo actual de inferencia

predict_image.py acepta --checkpoint, --models, --explain-model y archivos de calibración. Las funciones reutilizables de inferencia también reciben paths. Keras se carga directamente y el threshold clínico se resuelve normalmente desde model_metadata.json junto al checkpoint.

Por cada imagen rastreada:

- Se crea un run de tipo inference.
- Se registran entradas/salidas, artifacts y predicciones.
- Se escribe tanto predictions como run_image_predictions.
- No se registra training_run_id, model_version_id, deployment_id ni run_lineage a la versión usada.
- Los fallos fatales de calidad pueden retornar antes de persistir el evento completo.

No había inference runs en PostgreSQL al momento de la auditoría. La pantalla “Predicciones subidas” consume vw_uploaded_predictions, pero no constituye un backend de ejecución.

También quedan fuera del linaje canónico:

- TTA.
- Ensembles.
- Calibración standalone.
- Extracción/clasificación SVM.
- Explicaciones opcionales de inferencia.

### Consecuencia

Una predicción puede conservar el nombre o path de un modelo en metadatos, pero no puede demostrar de forma referencial qué versión, bytes, threshold y convención estaban desplegados.

## 7. Estructura actual del frontend

### Navegación existente

Layout.tsx define un menú plano de nueve entradas:

1. Dashboard.
2. Ejecuciones.
3. Evaluación clínica.
4. Comparación modelos.
5. Explicabilidad.
6. Predicciones subidas.
7. Dataset.
8. Datasets y modelos.
9. Errores y logs.

App.tsx selecciona páginas mediante estado local PageKey. No se usa un router; por ello no hay URLs profundas, historial atrás/adelante ni enlaces estables a un run. RunDetail es una selección interna.

### Capacidades

- Dashboard y detalle de runs.
- Agrupación training → evaluation/explainability.
- Métricas clínicas, matrices y reportes.
- Comparación de modelos/runs.
- Galería de explicabilidad y casos.
- Consulta de predicciones subidas.
- Navegación de datasets.
- Errores, logs y artifacts.

### Brechas

- “Datasets y modelos” representa modelos lógicos, no un catálogo de model_versions.
- El árbol de linaje no contiene nodo model_version, deployment, inference run ni image analysis job.
- No hay acciones de promoción, rollback o inferencia.
- El frontend no envía model_path/checkpoint_path para inferencia porque esa operación no existe.
- Sí usa path como fallback al solicitar un artifact cuando no dispone de artifact_id, y muestra/copia paths y comandos.
- La comparación advierte que split, preprocessing o threshold podrían diferir, pero no exige comparabilidad por identidad.
- Cambiar datasource no limpia necesariamente la selección de run.
- No hay suite de pruebas frontend, lint configurado ni E2E.

No se debe reemplazar ninguna entrada ni contrato actual en Stage 0. La reorganización debe ser aditiva y conservar PageKey, etiquetas y endpoints públicos.

## 8. Tablas y relaciones existentes

### Acceso a datos

No hay ORM declarativo. src/db.py, src/run_tracker.py y el backend utilizan SQLAlchemy Core/conexiones y SQL textual. Las vistas son parte importante del contrato de lectura.

scripts/init_db.py ordena y ejecuta los SQL de db/init dentro de una transacción, con un separador propio por punto y coma. No mantiene una tabla de versiones/checksums de migración ni implementa downgrade. Los scripts deben ser reejecutables e idempotentes.

### Tablas base encontradas

| Tabla | Papel actual | Decisión |
|---|---|---|
| models | Catálogo lógico de arquitecturas/modelos | Reutilizar |
| runs | Registro polimórfico de training, evaluation, explainability e inference | Reutilizar como única entidad de runs |
| model_versions | Versión producida por training, actualmente centrada en paths | Reutilizar y fortalecer |
| artifacts | Registro de archivos y checksum por run | Reutilizar como identidad de bytes |
| run_lineage | Relación parent/child para evaluación y explicación | Reutilizar y completar FKs |
| experiments | Agrupación experimental | Reutilizar |
| datasets | Registro de datasets | Reutilizar |
| dataset_splits | Splits lógicos/físicos | Reutilizar |
| dataset_split_images | Inventario de imágenes por split | Reutilizar |
| run_dataset_images | Uso de imágenes por run | Reutilizar |
| run_io_records | Entradas y salidas de run | Reutilizar |
| training_history | Historial por época | Reutilizar |
| run_metrics | Métricas generales | Reutilizar |
| run_clinical_metrics | Métricas con convención clínica explícita | Reutilizar |
| run_checkpoint_policy | Decisión/política del checkpoint | Reutilizar como evidencia; agregar versión |
| run_threshold_calibration | Threshold y calibración por run | Reutilizar; agregar versión/artifact |
| confusion_matrices | Matrices de confusión | Reutilizar |
| classification_reports | Reportes por clase | Reutilizar |
| predictions | Predicciones generales y FK usada por explicabilidad | Reutilizar como predicción canónica |
| run_image_predictions | Proyección clínica detallada, hoy dual-write | Mantener por compatibilidad y reconciliar |
| explainability_results | Resultado por método/caso/predicción | Reutilizar |
| environment_packages | Paquetes del entorno | Reutilizar |
| execution_logs | Logs | Reutilizar |
| errors | Errores | Reutilizar |
| synthetic_data_runs | Registro de generación sintética | Reutilizar |

### Relaciones relevantes

- models 1 → N model_versions.
- runs(training) 1 → N model_versions mediante training_run_id.
- runs 1 → N artifacts, metrics, I/O, errores, logs y predicciones.
- run_lineage enlaza parent_run_id con child_run_id y admite model_version_id/checkpoint_artifact_id como columnas, pero esas dos columnas no tienen FKs y están vacías en las filas actuales.
- explainability_results puede enlazarse con predictions.
- datasets/splits/images se enlazan con runs a través de run_dataset_images y registros de I/O.

### Vistas encontradas

PostgreSQL contiene 25 vistas:

- vw_case_level_explainability.
- vw_case_type_summary.
- vw_checkpoint_policy_summary.
- vw_clinical_inference_predictions.
- vw_clinical_run_summary.
- vw_dataset_browser_images.
- vw_dataset_browser_summary.
- vw_dataset_split_images_summary.
- vw_evaluation_lineage.
- vw_explainability_gallery.
- vw_explainability_lineage.
- vw_explainability_summary.
- vw_false_negative_cases.
- vw_false_positive_cases.
- vw_low_confidence_cases.
- vw_model_run_summary.
- vw_run_artifacts_summary.
- vw_run_dashboard.
- vw_run_dataset_usage_summary.
- vw_run_image_predictions_summary.
- vw_run_io_summary.
- vw_run_lineage.
- vw_threshold_calibration_summary.
- vw_uploaded_predictions.
- vw_visual_explainability_audit.

### Fotografía de datos

| Entidad | Conteo observado | Observación |
|---|---:|---|
| runs | 36 | 12 training, 12 evaluation, 12 explainability, 0 inference; todos completed |
| model_versions | 12 | Todos con training_run_id y paths específicos por run |
| artifacts | 1.884 | 12 checkpoints y 12 modelos finales; todos los paths tienen checksum |
| run_lineage | 24 | 12 evaluates_checkpoint_from y 12 explains_checkpoint_from |
| run_lineage con model_version_id | 0 | Brecha recuperable |
| run_lineage con checkpoint_artifact_id | 0 | Brecha recuperable |
| predictions | 33.672 | Incluye evaluación y subconjunto de explicabilidad |
| run_image_predictions | 33.072 | Coincide con las predicciones de evaluación; image_id está nulo |
| explainability_results | 1.800 | 600 predicciones explicadas por tres métodos |
| run_checkpoint_policy | 12 | Conserva rutas best_model.keras genéricas |
| run_clinical_metrics | 24 | Convención clinical_v1_parasitized_positive |
| run_threshold_calibration | 12 | Fuente validation_calibration |
| run_dataset_images | 396.840 | Uso de imágenes por run |
| dataset_split_images | 27.558 | Inventario físico/lógico |
| run_io_records | 36 | Un conjunto por run observado |

### Integridad histórica comprobada

- 12/12 training runs tienen model_version.
- 24/24 lineages pueden asociarse de manera exacta a una sola model_version y a un solo checkpoint artifact.
- No se detectaron duplicados en (training_run_id, version_name).
- No se detectaron duplicados en (run_id, path) para los artifacts usados por el backfill de checkpoints.
- No se detectaron clases, labels, probabilidades o thresholds fuera de la convención clínica en los registros revisados.
- 004_seed.sql conserva un orden de clase legado {parasitized, uninfected}. Debe marcarse como legacy; no se debe reescribir ni borrar la evidencia histórica.

## 9. Riesgos encontrados

| Prioridad | Riesgo | Impacto |
|---|---|---|
| P0 | best_model.keras se sobrescribe | Reproducibilidad y despliegue pueden usar bytes distintos bajo la misma ruta |
| P0 | Outputs de explicabilidad globales y sobrescritos | El archivo local ya no representa el checksum histórico de múltiples runs |
| P0 | No existe deployment → inference run → job | No se puede demostrar qué versión produjo una predicción clínica |
| P0 | source_training_run_id no valida propiedad exacta del checkpoint | Se puede registrar lineage formalmente válido pero materialmente falso |
| P1 | model_version/artifact no están vinculados por FK | La identidad oficial sigue dependiendo de strings de path |
| P1 | Tracking de versión best-effort | Un training completed puede carecer de versión gobernada |
| P1 | Threshold sidecar mutable y no desplegable | La misma versión puede decidir distinto sin evento de gobernanza |
| P1 | Dual-write de predicciones | Divergencia, duplicidad y semántica ambigua |
| P1 | Scripts destructivos pueden borrar archivos referenciados | Ruptura irreversible de reproducibilidad si se ejecutan sin inventario/backup |
| P1 | Rutas absolutas | Baja portabilidad y exposición de estructura del host |
| P2 | Outputs de evaluación reutilizables | Reruns pueden contaminar o sobrescribir resultados |
| P2 | Runners derivados fuera del linaje | TTA, ensemble, SVM y calibración no se atribuyen consistentemente |
| P2 | Sin ledger de migraciones | Difícil comprobar qué DDL exacto fue aplicado |
| P2 | Sin pruebas frontend/E2E/constraints reales | Regresiones de contrato o concurrencia pueden pasar inadvertidas |

## 10. Referencias inseguras a rutas genéricas

### best_model.keras

La búsqueda exacta y sensible a mayúsculas encontró 184 apariciones en 174 líneas de 40 archivos. La búsqueda no sensible a mayúsculas produjo el mismo total de apariciones. La distribución de las 174 líneas coincidentes es:

- 11 en código productivo ML.
- 2 en scripts operacionales.
- 93 en README/documentación.
- 7 en pruebas del backend.
- 61 en pruebas del proyecto ML.
- 0 en frontend.

El literal exacto outputs/custom_cnn/best_model.keras aparece 49 veces en 14 archivos; se concentra en documentación/comandos y fixtures de linaje. No aparece como literal en el frontend.

### Inventario físico actual

Se encontraron 24 archivos best_model.keras bajo malaria_dl_local_project/outputs:

| Clase física | Cantidad | Interpretación |
|---|---:|---|
| Snapshots UUID registrados en model_versions | 12 | Cuatro custom_cnn, cuatro densenet121 y cuatro vgg16; son los candidatos gobernados actuales |
| Snapshots UUID no registrados | 6 | Cinco densenet121 y uno de smoke; requieren atribución manual |
| Aliases o directorios no-run | 6 | Tres aliases principales, vgg16_imagenet y dos outputs de execution_smoke |

Los UUID no registrados son 5e2a1db6-e8f6-4de7-88bd-de643bc7ddfa, 5ec73c64-c4e8-4409-8639-1c342ed256a0, 611c02e0-d6d3-4fe0-8c8d-2b7b80beb4a5, acab1c5e-f89d-4a5f-88a2-cdf2d0b77aa0, d1a2622c-6d91-4801-8dd8-5e9acda38340 y el smoke dd32274c-948d-4ab9-96d9-2389a06cc5ec. Los seis paths no-run son:

- outputs/custom_cnn/best_model.keras.
- outputs/densenet121/best_model.keras.
- outputs/vgg16/best_model.keras.
- outputs/vgg16_imagenet/best_model.keras.
- outputs/execution_smoke_custom_cnn_20260715/best_model.keras.
- outputs/execution_smoke_custom_cnn_snapshot_20260715/best_model.keras.

“No registrado” no equivale a descartable: se debe calcular checksum, buscar logs/manifiestos y clasificar en un inventario de quarantine lógica. Ningún archivo se debe borrar ni asociar automáticamente por el nombre.

Las referencias productivas que requieren migración son:

- malaria_dl_local_project/src/checkpoint_policy.py:608.
- malaria_dl_local_project/src/train.py:127, 136, 818, 977, 978, 1696, 1700, 2100.
- malaria_dl_local_project/src/run_tracker.py:1551.
- malaria_dl_local_project/src/calibrate.py:34.
- malaria_dl_local_project/scripts/backfill_run_lineage.py:176.
- malaria_dl_local_project/scripts/test_db.py:257.

No todas son defectos: algunas pruebas verifican explícitamente comportamiento legado y varias referencias describen snapshots. El riesgo aparece cuando la ruta se usa como identidad, entrada de evaluación/inferencia o instrucción recomendada.

### Otros campos y términos buscados

| Término | Archivos | Apariciones no sensibles a mayúsculas | Lectura |
|---|---:|---:|---|
| best_model.keras | 40 | 184 | Alias genérico, docs y fixtures |
| checkpoint_path | 32 | 228 | Persistencia y transporte principal del checkpoint |
| model_path | 11 | 95 | Inferencia, metadata y pruebas |
| model_file | 0 | 0 | No existe |
| source_training_run_id | 6 | 43 | Linaje de evaluación/explicabilidad |
| training_run_id | 21 | 144 | Bien establecido en versionado y linaje |
| evaluation_run | 3 | 22 | Principalmente UI/servicio de linaje |
| explainability_run | 1 | 1 | Concepto poco explícito |
| model_version | 19 | 76 | Existe, pero no es entrada canónica |
| predict como palabra | 10 | 13 | Además hay derivados como predictions/predict_image |
| inference | 36 | 104 | Flujo local y vistas, sin deployment |
| threshold | 94 | 1.838 | Amplio uso clínico y de tests |
| Grad-CAM / GradCAM / grad_cam | 26 | 112 | Implementación, persistencia, API y UI |
| LIME | 17 | 59 | Implementación, persistencia, API y UI |
| SHAP | 16 | 66 | Implementación, persistencia, API y UI |

Para LIME/SHAP se usaron límites de palabra para evitar falsos positivos como shape. El inventario detallado de best_model.keras está en el Apéndice A.

### Flujos físicos que deben cerrarse

- train.py carga outputs/{model}/best_model.keras.
- evaluate.py recibe --checkpoint y carga esa ruta.
- explain.py recibe --checkpoint y comparte --output-dir.
- calibrate.py recibe checkpoint y puede modificar model_metadata.json junto a él.
- predict_image.py recibe --checkpoint/--models/--explain-model.
- tta.py, ensemble.py y svm_features.py reciben o propagan paths.
- El backend sirve artifacts por artifact_id, pero admite path como fallback.
- El frontend no envía paths de modelos; sí puede enviar path al endpoint GET de artifact cuando falta artifact_id.

## 11. Brechas de trazabilidad

| Enlace objetivo | Estado actual | Brecha |
|---|---|---|
| training run → model version | Existe para 12/12 | Falta transacción, idempotencia y FK al artifact |
| model version → checkpoint artifact | Implícito por path exacto | Falta checkpoint_artifact_id con FK |
| model version → evaluation run | training parent + checkpoint_path | Falta version/artifact persistidos |
| model version → explainability run | training parent + checkpoint_path | Falta version/artifact persistidos y outputs inmutables |
| model version → threshold | Calibration ligada a run/sidecar | Falta vínculo y artifact versionado |
| model version → deployment | Inexistente | No hay entidad ni promoción/rollback |
| deployment → inference run | Inexistente | No hay deployment_id ni snapshot de decisión |
| inference run → image analysis job | Inexistente | Un run por imagen sustituye el concepto de job |
| image analysis job → cell predictions | Parcial en predictions/run_image_predictions | Falta FK al job y granularidad explícita |
| artifact histórico → bytes actuales | Checksum registrado | Paths sobrescritos impiden recuperar algunos bytes |

Además:

- La resolución explícita de source_training_run_id no comprueba ownership.
- La resolución por path evita escoger “el último” si hay ambigüedad, lo cual es correcto, pero su cobertura se limita a evaluación/explicabilidad.
- Los metadatos de evaluation/explainability conservan source_training_run_id y path, útiles para backfill.
- run_threshold_calibration no contiene model_version_id.
- run_checkpoint_policy registra un path genérico; debe considerarse evidencia de política, no source of truth.
- run_image_predictions no enlaza de forma efectiva con run_dataset_images: image_id está nulo en las 33.072 filas observadas.
- La metadata de algunas predicciones indica TFDS mientras el run usa split físico; se requiere reconciliación, no reescritura silenciosa.

## 12. Propuesta de modelo de datos

### Principios

1. Los UUID y FKs son identidad; los paths son atributos legacy/operacionales.
2. artifact_id + checksum identifican bytes.
3. El payload de un deployment es inmutable y cada activación/rollback crea una nueva revisión auditable; nunca es una copia a best_model.keras.
4. El threshold, label mapping y positive_label usados se congelan en el deployment.
5. Los runs continúan en una sola tabla.
6. predictions continúa siendo la tabla canónica; no se duplica cell_predictions.
7. Ningún backfill ambiguo elige “el último”.

### Entidades existentes que se reutilizan

- models.
- runs.
- model_versions.
- artifacts.
- run_lineage.
- run_checkpoint_policy.
- run_threshold_calibration.
- run_clinical_metrics.
- predictions.
- run_image_predictions como compatibilidad/read model temporal.
- explainability_results.
- run_metrics, training_history, confusion_matrices y classification_reports.
- datasets, dataset_splits, dataset_split_images y run_dataset_images.
- run_io_records, execution_logs, errors, experiments y environment_packages.

### Cambios aditivos en tablas existentes

#### model_versions

Agregar:

- checkpoint_artifact_id FK → artifacts.
- lifecycle_status: candidate, validated, deployable, retired o invalid.
- format/serializer version si se necesita distinguir Keras u otros.
- Reutilizar la columna metadata JSONB ya existente para información no normalizada; no crear otra.

Constraints graduales:

- El artifact debe pertenecer al training_run_id de la versión mediante FK compuesta, no solo validación de aplicación.
- Índice único posterior a limpieza sobre training_run_id + version_name.
- Índice único o regla de idempotencia sobre training_run_id + checkpoint_artifact_id.
- Para filas nuevas, checkpoint_artifact_id obligatorio; para legado, nullable hasta completar backfill.

#### run_lineage

Las columnas model_version_id y checkpoint_artifact_id ya existen; no deben duplicarse. Se propone:

- Backfill exacto.
- FKs compuestas a model_versions y artifacts, primero NOT VALID.
- Constraints que demuestren que ambos IDs pertenecen al parent training run y se corresponden entre sí.
- Obligación para nuevos relationships evaluates_checkpoint_from y explains_checkpoint_from.
- Conservación de checkpoint_path y resolution metadata como evidencia legacy.

#### run_checkpoint_policy

Agregar model_version_id y checkpoint_artifact_id. Mantener checkpoint_path histórico. La fila describe por qué se seleccionó un checkpoint; la versión describe qué bytes resultaron.

#### run_threshold_calibration

Agregar:

- model_version_id FK.
- calibration_artifact_id FK opcional al JSON/curva/sidecar registrado.
- score_name, label_mapping_version y positive_label si no están ya disponibles de manera explícita.
- estado o método de calibración si se requiere lifecycle.

No se propone model_version_thresholds en Stage 0: duplicaría la calibración existente. Un deployment puede referenciar directamente la calibración elegida y congelar su snapshot.

#### predictions

Agregar en forma nullable:

- image_analysis_job_id FK.
- prediction_scope, inicialmente legacy_image o cell.
- cell_index.
- source_image_id.
- bbox_xmin, bbox_ymin, bbox_xmax, bbox_ymax.

Los campos que hoy se extraen desde metadata en 018_visual_audit_views pueden poblarse gradualmente. El id existente de predictions funciona como cell_prediction_id para filas nuevas de alcance cell.

#### artifacts

- Favorecer una clave relativa/URI lógica además del path absoluto heredado.
- Agregar estado available, missing, mutated o archived sin cambiar el checksum original.
- Considerar unicidad por run_id + path solo después de auditar duplicados legítimos y tipos.

### Integridad referencial cruzada

Las FKs simples no alcanzan para demostrar ownership. Después del backfill y de revisar duplicados se propone:

- UNIQUE (id, run_id) en artifacts.
- UNIQUE (id, training_run_id) y UNIQUE (id, checkpoint_artifact_id) en model_versions.
- FK model_versions(checkpoint_artifact_id, training_run_id) → artifacts(id, run_id).
- FK run_lineage(model_version_id, parent_run_id) → model_versions(id, training_run_id).
- FK run_lineage(checkpoint_artifact_id, parent_run_id) → artifacts(id, run_id).
- FK run_lineage(model_version_id, checkpoint_artifact_id) → model_versions(id, checkpoint_artifact_id).
- FK run_checkpoint_policy(model_version_id, run_id) → model_versions(id, training_run_id).
- FK run_checkpoint_policy(checkpoint_artifact_id, run_id) → artifacts(id, run_id), más FK compuesta version/artifact como en run_lineage.
- UNIQUE (run_threshold_calibration_id, model_version_id) en run_threshold_calibration.
- FK run_threshold_calibration(calibration_artifact_id, run_id) → artifacts(id, run_id).
- FK model_deployments(threshold_calibration_id, model_version_id) → run_threshold_calibration(run_threshold_calibration_id, model_version_id).

Estas constraints permanecen compatibles con NULL para filas legacy durante la transición. Para escritores nuevos, un constraint trigger transaccional debe exigir ambos IDs y validar los tipos:

- El propietario de model_versions es un run_type = training.
- evaluates_checkpoint_from tiene parent training y child evaluation.
- explains_checkpoint_from tiene parent training y child explainability.
- run_model_deployments solo se liga a un run inference.
- image_analysis_jobs solo se liga a un run inference.

Un CHECK normal no puede consultar otra tabla en PostgreSQL; por ello esta regla requiere constraint trigger/procedimiento de escritura además de defensa en el servicio. No se recomienda cerrar globalmente runs.run_type con una lista incompleta antes de inventariar TTA, ensemble, calibración, SVM y generación sintética.

### Tablas nuevas propuestas

#### model_deployments

Cada fila representa una revisión de activación auditable:

- id.
- model_version_id FK.
- threshold_calibration_id FK → run_threshold_calibration.
- environment y slot.
- status.
- supersedes_deployment_id FK nullable.
- rollback_of_deployment_id FK nullable.
- artifact checksum snapshot.
- decision_threshold snapshot.
- label_mapping snapshot.
- positive_label snapshot, siempre parasitized para clinical_v1.
- score_name snapshot.
- activated_at, retired_at, created_at.
- activated_by, activation_reason, retired_by, retire_reason y metadata.

Debe existir como máximo una revisión active por environment + slot mediante índice parcial. Model version, artifact, threshold y mapping quedan inmutables después del INSERT; un trigger puede impedir su UPDATE. Una promoción o rollback crea una fila nueva, cierra el intervalo de la revisión activa dentro de la misma transacción y conserva supersedes/rollback_of. Nunca se reactiva ni se sobrescribe una fila histórica y nunca se copia un archivo sobre un alias.

#### run_model_deployments

Tabla puente para demostrar qué deployment usó un inference run:

- run_id FK → runs.
- deployment_id FK → model_deployments.
- role, por ejemplo primary, ensemble_member o explainer.
- ordinal y weight.
- snapshot metadata.

Una tabla puente, en vez de runs.deployment_id, soporta ensembles sin introducir columnas repetidas.

#### image_analysis_jobs

Representa la solicitud/caso procesado:

- id.
- inference_run_id FK → runs.
- input_artifact_id FK → artifacts.
- idempotency_key.
- status y timestamps.
- error_id opcional.
- patient/slide/source references compatibles con privacidad.
- total_cells, positive_cells y summary metadata.

La capa de servicio debe validar que inference_run_id corresponda a run_type = inference.

#### schema_migrations

Tabla administrativa propuesta:

- migration_id.
- checksum.
- applied_at.
- execution metadata.

Su adopción debe comenzar con un baseline explícito de los 16 SQL ya aplicados; no se deben “reaplicar” como si fueran nuevos.

#### model_governance_backfill_audit

Tabla administrativa append-only para hacer el backfill reversible:

- id y batch_id.
- event_type: apply o revert, y reversal_of_audit_id para una reversión.
- table_name y record_id.
- before_values y after_values JSONB.
- resolution_rule y candidate_ids.
- result/status.
- event_at y actor.

El manifiesto completo del batch también debe registrarse como artifact con checksum. La tabla no se actualiza: una reversión inserta un evento nuevo que referencia el evento aplicado. Así se evita depender de logs efímeros o de agregar batch_id a cada tabla de dominio.

### Linaje objetivo

~~~mermaid
flowchart TD
    TR["training run<br/>runs"] --> MV["model version<br/>model_versions"]
    MV --> CA["checkpoint artifact<br/>artifacts + SHA-256"]
    MV --> ER["evaluation run<br/>runs"]
    MV --> XR["explainability run<br/>runs"]
    MV --> TC["threshold calibration<br/>run_threshold_calibration"]
    MV --> DEP["deployed model version<br/>model_deployments"]
    TC --> DEP
    CA --> DEP
    DEP --> RMD["run_model_deployments"]
    RMD --> IR["inference run<br/>runs"]
    IR --> JOB["image analysis job<br/>image_analysis_jobs"]
    JOB --> CP["cell predictions<br/>predictions"]
    CP --> IX["explainability result opcional"]
    ER --> EA["evaluation artifacts/metrics"]
    XR --> XA["explainability artifacts/results"]
~~~

La relación visual model version → evaluation/explainability se implementa reutilizando run_lineage; no exige tablas específicas por tipo de run.

## 13. Propuesta de APIs

El backend actual debe conservar todos sus endpoints GET y sus campos. Las APIs siguientes son aditivas.

### Catálogo de versiones

| Método | Endpoint propuesto | Uso |
|---|---|---|
| GET | /api/model-versions | Listar versiones con modelo, training run, artifact, checksum y lifecycle |
| GET | /api/model-versions/{model_version_id} | Detalle reproducible |
| GET | /api/model-versions/{model_version_id}/lineage | Training, evaluaciones, explicaciones, calibraciones y deployments |
| GET | /api/model-versions/{model_version_id}/artifacts | Artifacts por ID; sin depender del path |

Filtros recomendados: model_id/model_name, training_run_id, lifecycle_status, created_from/to y checksum. La respuesta debe marcar explícitamente legacy_unresolved cuando falte artifact.

### Deployments

| Método | Endpoint propuesto | Uso |
|---|---|---|
| GET | /api/model-deployments | Historial por environment/slot/estado |
| GET | /api/model-deployments/{deployment_id} | Snapshot completo de versión y decisión clínica |
| POST | /api/model-deployments/activations | Crear y activar una nueva revisión inmutable desde model_version_id y calibración |
| POST | /api/model-deployments/{deployment_id}/retire | Retirar sin borrar |
| POST | /api/model-deployments/{deployment_id}/rollback | Crear una revisión nueva basada en un deployment histórico compatible |

Las acciones de escritura requieren autenticación, autorización, actor, reason, idempotency key y audit log. Activar o hacer rollback debe ser transaccional, serializar el slot para impedir dos activos, cerrar el intervalo anterior y devolver un deployment_id nuevo. Retire solo cierra la revisión activa; nunca cambia su payload clínico.

### Inferencia y jobs

| Método | Endpoint propuesto | Uso |
|---|---|---|
| POST | /api/image-analysis-jobs | Subir/referenciar imagen y elegir deployment_id o slot |
| GET | /api/image-analysis-jobs/{job_id} | Estado, run, deployment y resumen |
| GET | /api/image-analysis-jobs/{job_id}/predictions | Predicciones celulares paginadas |
| GET | /api/inference-runs/{run_id} | Detalle del run y deployments usados |
| POST | /api/image-analysis-jobs/{job_id}/cancel | Cancelación si el estado lo permite |

El servidor resuelve el artifact desde deployment_id. No acepta model_path, checkpoint_path ni model_file en el contrato gobernado. El upload debe tener límites, validación MIME/contenido, antivirus según entorno, control de privacidad y almacenamiento fuera de rutas servibles directamente.

### Compatibilidad

- /api/runs y su grouped-lineage mantienen la forma actual y agregan nodos/campos opcionales.
- /api/predictions/uploads permanece disponible y se enriquece con model_version_id, deployment_id, inference_run_id y image_analysis_job_id cuando existan.
- /api/artifacts/file conserva temporalmente path como fallback de solo lectura; los clientes nuevos usan artifact_id.
- Los CLI conservan --checkpoint en modo legacy. Se agregan --model-version-id y --deployment-id.
- Los errores nuevos deben distinguir unresolved, ambiguous, checksum_mismatch, artifact_missing y ownership_mismatch.

### Contratos de seguridad e integridad

- Nunca aceptar source_training_run_id como prueba suficiente.
- Resolver IDs dentro de una transacción consistente.
- Volver a calcular/verificar checksum antes de cargar cuando el storage pueda mutar.
- Comparar label_mapping, positive_label y score_name con clinical_v1.
- Rechazar una versión no deployable o un deployment no active.
- Propagar correlation_id/idempotency_key a run, job, logs y errors.

## 14. Propuesta de migración

La migración es forward-compatible y no elimina datos.

### Fase 0: baseline y congelamiento operacional

1. Pausar temporalmente nuevos entrenamientos, evaluaciones, explicaciones y promociones durante el inventario.
2. Crear pg_dump verificado y un manifiesto de artifacts con path, tamaño, mtime y SHA-256.
3. Registrar commit, versión Python/TensorFlow/PostgreSQL y conteos de las 25 tablas.
4. Marcar best_model.keras como alias legacy en documentación y operación; no borrarlo.
5. Inventariar snapshots locales no registrados.

Se observaron 24 archivos best_model.keras: 12 snapshots UUID registrados, seis UUID no registrados y seis aliases/paths no-run, detallados en la sección 10. Los no registrados y las carpetas generadas por pruebas deben ponerse en inventario/quarantine lógica para atribución manual; no deben enlazarse por basename ni eliminarse automáticamente.

### Fase 1: DDL aditivo

1. Crear schema_migrations y registrar el baseline con checksum de los 16 SQL existentes.
2. Crear model_governance_backfill_audit.
3. Agregar columnas nullable a model_versions, run_checkpoint_policy, run_threshold_calibration, predictions y artifacts.
4. Crear model_deployments, run_model_deployments e image_analysis_jobs.
5. Crear índices/UNIQUE compuestos no bloqueantes cuando el entorno lo permita.
6. Agregar FKs compuestas nuevas como NOT VALID para separar despliegue de validación.
7. Agregar constraint triggers de ownership/tipo inicialmente compatibles con legado.
8. No agregar aún NOT NULL a datos históricos.

Nombres sugeridos, respetando la numeración existente:

- 023_schema_migrations_baseline.sql.
- 024_model_version_artifact_governance.sql.
- 025_model_deployments.sql.
- 026_inference_jobs.sql.
- 027_model_governance_backfill_constraints.sql.

Los nombres son propuesta; el equipo debe reservarlos antes de escribir para evitar colisiones.

### Fase 2: backfill exacto y auditable

Ejecutar primero en dry-run y exportar:

- fila objetivo.
- regla usada.
- candidatos.
- checksum esperado/actual.
- resultado exact, ambiguous, missing o mismatch.
- batch_id y timestamp.
- before_values y after_values por fila.

Orden:

1. Abrir batch en model_governance_backfill_audit y registrar el manifiesto como artifact.
2. Vincular model_versions.checkpoint_artifact_id por mismo training_run_id + path exacto + checksum.
3. Vincular run_lineage.model_version_id por parent training run + checkpoint_path exacto.
4. Vincular run_lineage.checkpoint_artifact_id por model version + artifact exacto.
5. Vincular run_checkpoint_policy con la versión del mismo training run, sin interpretar el alias como bytes.
6. Vincular run_threshold_calibration por run/model/version y evidencia del sidecar/artifact.
7. Incorporar calibración, TTA, ensemble, SVM e inferencia histórica solo cuando haya evidencia unívoca.
8. Cerrar el batch con conteos y checksum del manifiesto before/after.

Con la fotografía actual, las 24 filas de run_lineage de evaluación/explicabilidad tienen una coincidencia exacta y única. Aun así, el script debe volver a comprobar antes de aplicar.

Reglas prohibidas:

- Elegir la model_version “más reciente”.
- Asociar solo por nombre best_model.keras.
- Recalcular y reemplazar un checksum histórico para que coincida con el archivo actual.
- Inferir lineage ambiguo sin revisión.

### Fase 3: escritores consistentes

1. Corregir la validación de ownership en src/run_lineage.py.
2. Hacer idempotente la finalización del training.
3. Guardar directo al snapshot y registrar artifact/version antes de completed.
4. Aislar evaluación y explicabilidad por child run ID.
5. Escribir version/artifact IDs en todo lineage nuevo.
6. Registrar artifact status si el archivo desaparece o muta.

### Fase 4: dual-read, luego ID-first

- Backend y CLI resuelven primero IDs.
- Si una fila legacy solo tiene path, usan el resolver exacto y exponen una advertencia.
- Se conservan respuestas/endpoints actuales.
- Se mide el uso de fallback por path.
- Solo después de llegar a cero uso gobernado se deprecia, sin borrar columnas históricas.

### Fase 5: deployments e inferencia

1. Habilitar lifecycle de versiones.
2. Registrar calibración versionada.
3. Crear revisiones de activación de deployments con snapshot clínico.
4. Resolver inferencia por deployment.
5. Crear un inference run por solicitud/lote y uno o más image_analysis_jobs.
6. Insertar predictions con job_id.
7. Mantener run_image_predictions como compatibilidad hasta reconciliar consumidores.

### Fase 6: constraints finales

Después de reportar cero anomalías para escritores nuevos:

- VALIDATE CONSTRAINT.
- Agregar NOT NULL con estrategia para filas post-cutover, o constraint condicional por schema/version.
- Activar unicidad parcial.
- Impedir deployments con convención clínica incompatible.
- Impedir lineage nuevo sin versión/artifact.

Las filas legacy no resueltas deben permanecer identificables; nunca se inventan datos para satisfacer un NOT NULL.

## 15. Propuesta de reorganización del frontend

### Objetivo

Hacer visible el linaje completo sin retirar las nueve entradas ni cambiar sus contratos.

### Organización sugerida

| Grupo visual | Entradas existentes preservadas | Entradas aditivas futuras |
|---|---|---|
| Operación | Dashboard; Ejecuciones | Jobs de análisis |
| Validación | Evaluación clínica; Comparación modelos; Explicabilidad | Registro de versiones |
| Inferencia | Predicciones subidas | Deployments |
| Datos | Dataset; Datasets y modelos | Sin cambio inicial |
| Observabilidad | Errores y logs | Sin cambio inicial |

Los grupos pueden implementarse solo como encabezados visuales. PageKey y cualquier ruta pública futura deben mantenerse estables.

### Cambios de pantallas

- **Ejecuciones:** expandir el grupo a training → model version → evaluation/explainability; mostrar unresolved/conflict como hoy.
- **Datasets y modelos:** mantener catálogo lógico y agregar acceso a versiones.
- **Registro de versiones:** checksum, training run, artifact, threshold, evaluaciones, explicaciones y lifecycle.
- **Deployments:** environment/slot, versión activa, threshold congelado, historial y rollback.
- **Predicciones subidas:** conservar vista; agregar version/deployment/run/job y enlace navegable.
- **Jobs de análisis:** estado, imagen de entrada, conteos y predicciones celulares.
- **Comparación:** bloquear o advertir comparaciones no equivalentes usando dataset split, preprocessing, score y threshold normalizados.
- **RunDetail:** priorizar IDs; path queda en sección legacy/diagnóstico.

### Navegación

Introducir un router en una fase posterior mediante URLs aditivas y redirects/compatibilidad desde el estado actual. Antes de hacerlo, crear pruebas que capturen navegación, datasource y selección. Al cambiar datasource se debe limpiar cualquier run/version/job seleccionado que pertenezca al origen anterior.

### Contratos frontend

- Tipos separados para ModelVersion, ModelDeployment, InferenceRun e ImageAnalysisJob.
- Nunca construir una solicitud de inferencia con path.
- ArtifactLink usa artifact_id; path fallback muestra badge legacy.
- Los labels clínicos se muestran desde el contrato y se validan contra clinical_v1; no se invierte la clase para presentación.

## 16. Archivos que deberán modificarse

Esta lista es una hoja de ruta, no cambios realizados por esta auditoría.

| Fase | Archivos existentes | Archivos nuevos probables |
|---|---|---|
| Migración de esquema | malaria_dl_local_project/db/init/001_schema.sql como referencia; 002_indexes.sql; 003_views.sql; 017_clinical_run_tracking.sql; 022_run_lineage.sql; scripts/init_db.py | db/init/023_schema_migrations_baseline.sql; 024_model_version_artifact_governance.sql; 025_model_deployments.sql; 026_inference_jobs.sql; 027_model_governance_backfill_constraints.sql |
| Training inmutable | src/train.py; checkpoint_policy.py; run_tracker.py; tracking_integration.py; model_metadata.py | Servicio/resolver de model registry si se separa |
| Lineage y backfill | src/run_lineage.py; scripts/backfill_run_lineage.py; scripts/diagnose_run_lineage.py | Script de inventario/checksum y backfill de gobernanza |
| Evaluación | src/evaluate.py; run_evaluate_all_trainings.py | Ninguno obligatorio |
| Explicabilidad | src/explain.py; run_explain_all_trainings.py | Ninguno obligatorio |
| Thresholds | src/calibrate.py; calibration.py; threshold_calibration.py; model_metadata.py; decision.py | Ninguno obligatorio |
| Inferencia | src/predict_image.py; inference_pipeline.py; prediction_uploads.py; tta.py; ensemble.py; svm_features.py | Servicio de deployment/job |
| Backend | app/main.py; db.py; routes/runs.py; predictions.py; catalog.py; artifacts.py; services/run_lineage.py; artifacts.py; schemas/common.py | routes/model_versions.py; deployments.py; inference_jobs.py; servicios y schemas correspondientes |
| Frontend | src/App.tsx; components/Layout.tsx; services/api.ts; types/api.ts; páginas Runs, RunDetail, DatasetsModels, UploadedPredictions, ModelComparison y Explainability; componentes reports | pages/ModelVersions.tsx; ModelDeployment(s).tsx; ImageAnalysisJobs.tsx; componentes de linaje |
| Tests | Tests ML de artifact, checkpoint, lineage, evaluation, explainability, inference, threshold y migrations; backend tests de lineage/artifacts/predictions | Tests frontend, integración PostgreSQL, contratos deployment/job y E2E |
| Documentación | README.md; README_2.md; db/README_DB.md; docs/checkpoint_policy.md; threshold_calibration.md; training_evaluation_inference_workflow.md; workflows.md y documentos con best_model.keras | ADR de identidad de modelo y runbook de promoción/rollback |
| Operación | scripts/clean_training_outputs.py; purge_db_data.py; reset_experimental_state.py; test_db.py; scripts/validate.sh | Comando seguro de auditoría/retención |

No se recomienda editar retrospectivamente 001_schema.sql para simular que las columnas siempre existieron. Debe conservarse como baseline histórico y aplicar DDL en nuevas migraciones.

## 17. Orden recomendado de implementación

Este es el orden exacto recomendado para los siguientes cambios:

1. **Congelar e inventariar:** backup PostgreSQL, manifiesto SHA-256, snapshot registrado/no registrado y métricas baseline.
2. **Agregar migraciones aditivas:** schema ledger, auditoría de backfill, columnas de artifact/version, tablas deployment/job, FKs compuestas NOT VALID y triggers de ownership.
3. **Ejecutar dry-run de backfill exacto:** producir reporte de coincidencias, ambigüedades, missing y checksum mismatch.
4. **Aplicar backfill exacto:** primero model_versions → artifacts; luego run_lineage → model_version/artifact; validar conteos.
5. **Corregir ownership:** source_training_run_id debe coincidir con la versión, artifact, path y checksum.
6. **Estabilizar finalización de training:** snapshot primero; artifact + model_version idempotentes y obligatorios; alias después.
7. **Aislar outputs derivados:** evaluation/{run_id} y explainability/{run_id}; registrar artifact antes de completed.
8. **Adoptar model_version_id:** CLI/backend ID-first, path fallback exacto y observable.
9. **Versionar decisiones clínicas:** ligar run_threshold_calibration a versión/artifact y bloquear incompatibilidad de labels.
10. **Implementar deployments:** cada promoción/rollback crea una revisión nueva, cierra la activa atómicamente y no copia archivos.
11. **Implementar inferencia gobernada:** deployment → inference run → image_analysis_job → predictions.
12. **Extender backend de forma aditiva:** catálogo, deployments, jobs y lineage enriquecido; mantener GET actuales.
13. **Extender frontend:** versiones, deployments y jobs; nunca enviar rutas de modelos.
14. **Incorporar runners secundarios:** TTA, ensemble, calibración, SVM y explain-inference al mismo contrato.
15. **Reconciliar dual-write:** elegir predictions como fuente canónica, validar paridad y mantener una vista/adapter legacy.
16. **Fortalecer limpieza/retención:** preflight referencial, tombstone, backup y bloqueo de borrado de artifacts desplegados.
17. **Completar tests:** PostgreSQL real, concurrencia, contratos, frontend y E2E.
18. **Validar constraints finales:** FKs, unicidad y requisitos para filas post-cutover.
19. **Actualizar documentación y deprecar aliases:** medir uso; no borrar historia ni romper comandos públicos sin ventana de transición.

No se debe iniciar por la UI ni por copiar best_model.keras a otra carpeta: primero se estabiliza la identidad y la integridad transaccional.

## 18. Riesgos de compatibilidad

| Riesgo | Mitigación |
|---|---|
| Scripts externos dependen de --checkpoint | Mantener flag legacy, agregar --model-version-id y emitir warning medible |
| README y operadores usan best_model.keras | Alias se mantiene; documentación cambia su semántica a “último local”, nunca “oficial” |
| Filas históricas sin IDs | Columnas nullable, estado legacy_unresolved y backfill exacto |
| Artifact local perdido/sobrescrito | Conservar checksum/metadata y marcar estado; restaurar solo desde backup comprobado |
| Rutas absolutas en DB | Añadir storage key relativa; no reescribir paths históricos |
| Backend/Frontend esperan campos actuales | Respuestas aditivas; no renombrar ni eliminar campos/endpoints |
| Vistas dependen de tablas actuales | Actualizar con CREATE OR REPLACE y tests de contrato antes del cutover |
| Dual-write consumido por vistas | Reconciliar, mantener vista/adaptador y apagar escritor secundario solo tras paridad |
| init_db reejecuta SQL | Baseline/ledger y scripts idempotentes; no marcar aplicado sin checksum |
| Constraints bloquean legado | NOT VALID, validación separada y reglas condicionales post-cutover |
| Ensemble usa varias versiones | run_model_deployments con role/ordinal/weight |
| Convención seed histórica invertida | Etiquetar legacy; no borrar/reordenar; normalizar solo en el borde con metadata explícita |
| Nuevo backend de escritura amplía superficie | Separar autorización, límites, idempotencia y audit log del backend GET |

## 19. Estrategia de rollback

### Antes de migrar

- pg_dump con prueba de restauración.
- Copia/manifiesto de artifacts y checksums.
- Conteos por tabla, constraints, índices y vistas.
- Registro del commit y migration batch.

### Rollback de aplicación

1. Desactivar feature flags de IDs/deployments/jobs.
2. Volver a la versión previa de backend/frontend.
3. Mantener columnas/tablas nuevas; el código anterior las ignora.
4. Mantener aliases y contratos GET actuales durante toda la ventana.

### Rollback de deployment clínico

- Crear transaccionalmente una nueva revisión con el payload clínico del deployment histórico compatible.
- Establecer rollback_of_deployment_id y supersedes_deployment_id, cerrar la revisión activa y registrar actor, reason y timestamp.
- No reactivar ni modificar el payload de la fila histórica.
- No copiar ni renombrar model files.
- No editar la model_version ni el threshold históricos.

### Rollback de backfill

- Cada UPDATE debe tener su before/after en model_governance_backfill_audit y un manifiesto artifact con batch_id.
- Si se descubre una regla defectuosa, limpiar solo los nuevos IDs de las filas atribuidas a ese batch, después de verificar/exportar esa evidencia durable.
- Registrar cada limpieza como un evento revert nuevo con reversal_of_audit_id; no modificar la fila de auditoría original.
- No borrar runs, artifacts, predicciones, métricas ni lineage histórico.
- Constraints NOT VALID pueden retirarse independientemente si bloquean, sin revertir datos válidos.

### Artifacts

- Nunca recuperar sobrescribiendo el path histórico sin comparar checksum.
- Restaurar a una clave inmutable nueva y actualizar el estado/referencia mediante un evento auditable.
- Los scripts clean/purge/reset deben bloquear artifacts ligados a un deployment activo y requerir manifiesto/backup.

## 20. Criterios de aceptación

### Identidad y entrenamiento

- [ ] Ningún flujo gobernado identifica un modelo solo por best_model.keras, checkpoint_path o model_path.
- [ ] Todo training completed posterior al cutover tiene model_version_id y checkpoint_artifact_id válidos.
- [ ] El artifact oficial existe, coincide en tamaño/SHA-256 y está bajo una clave inmutable.
- [ ] Reintentar la finalización no crea versiones/artifacts duplicados.
- [ ] El alias best_model.keras se actualiza únicamente después de confirmar la versión y puede fallar sin invalidarla.

### Linaje histórico y nuevo

- [ ] Las 24 filas históricas revisadas quedan vinculadas por backfill exacto, o cualquier excepción queda explícitamente unresolved.
- [ ] Ningún caso ambiguo se resuelve seleccionando “el último”.
- [ ] Un checkpoint de otro training run produce ownership_mismatch.
- [ ] Evaluación y explicabilidad nuevas persisten model_version_id y checkpoint_artifact_id.
- [ ] Los outputs de cada child run se guardan en un directorio inmutable propio.

### Convención clínica y thresholds

- [ ] 0 = uninfected y 1 = parasitized en training, evaluación, explicabilidad, deployment e inferencia.
- [ ] positive_label = parasitized y score_name = probability_parasitized.
- [ ] Todo deployment referencia una calibración/version y congela threshold + mapping.
- [ ] Una FK compuesta impide combinar una model_version con la calibración de otra versión.
- [ ] Cambiar threshold crea una nueva decisión/deployment; no muta el histórico.
- [ ] Metadata incompatible bloquea promoción/inferencia y no queda solo como warning.

### Deployment e inferencia

- [ ] Existe como máximo un deployment active por environment + slot.
- [ ] Rollback crea una revisión nueva con rollback_of/supersedes; no reactiva la fila histórica ni sobrescribe archivos.
- [ ] Todo inference run está ligado al deployment o deployments exactos.
- [ ] Todo image_analysis_job está ligado a un inference run y artifact de entrada.
- [ ] Toda predicción celular nueva está ligada a un job.
- [ ] La API gobernada no acepta rutas físicas de modelos desde el cliente.

### Datos y compatibilidad

- [ ] No se eliminan ni reescriben datos históricos.
- [ ] Las rutas/endpoints públicos actuales siguen respondiendo.
- [ ] La lectura legacy por path está instrumentada y solo resuelve coincidencias exactas.
- [ ] predictions y la proyección legacy tienen reconciliación automática sin divergencia silenciosa.
- [ ] Rutas absolutas no aparecen en contratos nuevos salvo vista administrativa autorizada.

### Calidad

- [ ] Pruebas unitarias de ownership, checksum, idempotencia y ambigüedad.
- [ ] Pruebas de migración forward/rollback sobre una copia real de PostgreSQL.
- [ ] Pruebas de constraints y promoción concurrente.
- [ ] Pruebas de contrato de endpoints viejos y nuevos.
- [ ] Pruebas frontend para navegación, datasource, linaje y no envío de paths.
- [ ] E2E training → version → evaluation/explainability → deployment → inference → job → prediction.
- [ ] scripts/validate.sh ejecuta también backend_api/tests y la suite frontend.

## Apéndice A. Inventario exhaustivo de best_model.keras

La lista siguiente corresponde a las 174 líneas coincidentes (184 apariciones literales), agrupadas por archivo:

### Backend tests

- backend_api/tests/test_grouped_run_lineage_api.py:92, 139, 155, 294, 302, 316, 328.

### Documentación y README

- malaria_dl_local_project/README.md:181, 237, 296, 303, 313, 319, 400, 413, 425, 438, 453, 465, 495, 501, 511, 551, 569, 570, 571, 572, 579, 629, 631, 633.
- malaria_dl_local_project/README_2.md:83, 99, 107, 138, 149, 162, 185, 196, 209, 219, 229.
- malaria_dl_local_project/db/README_DB.md:83, 89, 95, 96, 97.
- malaria_dl_local_project/docs/checkpoint_policy.md:134, 145.
- malaria_dl_local_project/docs/database_dataset_tracking.md:77, 78, 79, 80, 81.
- malaria_dl_local_project/docs/frontend_clinical_dashboard.md:136, 147.
- malaria_dl_local_project/docs/informe_tecnico_integral_auditoria_2026-07-07.md:360.
- malaria_dl_local_project/docs/physical_dataset_split.md:115, 125.
- malaria_dl_local_project/docs/postgresql_tracking.md:127.
- malaria_dl_local_project/docs/threshold_calibration.md:71, 87, 139, 152, 162, 171, 175.
- malaria_dl_local_project/docs/training_evaluation_inference_workflow.md:54, 71, 88, 98, 113, 121, 131.
- malaria_dl_local_project/docs/workflows.md:158, 177, 204, 221, 231, 298, 312, 379, 381, 383, 386, 439, 468, 492, 499, 507, 529, 599, 610, 622, 636, 649, 651, 663, 676, 690.

### Código y scripts ML

- malaria_dl_local_project/scripts/backfill_run_lineage.py:176.
- malaria_dl_local_project/scripts/test_db.py:257.
- malaria_dl_local_project/src/calibrate.py:34.
- malaria_dl_local_project/src/checkpoint_policy.py:608.
- malaria_dl_local_project/src/run_tracker.py:1551.
- malaria_dl_local_project/src/train.py:127, 136, 818, 977, 978, 1696, 1700, 2100.

### Tests ML

- malaria_dl_local_project/tests/test_artifact_tracking.py:76, 77, 113.
- malaria_dl_local_project/tests/test_backfill_run_lineage.py:17, 22, 173, 200, 223.
- malaria_dl_local_project/tests/test_checkpoint_lineage_resolution.py:36, 40, 53, 74, 100, 127, 144, 156, 172, 211.
- malaria_dl_local_project/tests/test_checkpoint_policy_tracking.py:59.
- malaria_dl_local_project/tests/test_checkpoint_selection_metadata.py:166.
- malaria_dl_local_project/tests/test_clean_training_outputs.py:26, 84.
- malaria_dl_local_project/tests/test_decision.py:39, 93.
- malaria_dl_local_project/tests/test_diagnose_run_lineage.py:95, 101, 122.
- malaria_dl_local_project/tests/test_evaluate_lineage_tracking.py:67, 75, 83, 113, 145, 153.
- malaria_dl_local_project/tests/test_evaluate_threshold_modes.py:50, 67.
- malaria_dl_local_project/tests/test_explain_lineage_tracking.py:71, 79, 87, 117, 149, 157.
- malaria_dl_local_project/tests/test_inference_pipeline.py:68.
- malaria_dl_local_project/tests/test_inference_pipeline_threshold.py:41.
- malaria_dl_local_project/tests/test_max_epochs_main_smoke.py:164, 203.
- malaria_dl_local_project/tests/test_model_execution_outputs.py:79, 97, 132.
- malaria_dl_local_project/tests/test_model_metadata_integration.py:47.
- malaria_dl_local_project/tests/test_model_metadata_threshold.py:53, 73, 91.
- malaria_dl_local_project/tests/test_predict_image_outputs.py:29, 62.
- malaria_dl_local_project/tests/test_predict_image_threshold_modes.py:36.
- malaria_dl_local_project/tests/test_run_lineage.py:39, 104, 128, 163.
- malaria_dl_local_project/tests/test_threshold_clinical_mode.py:51, 82.

## Apéndice B. Archivos inspeccionados

Se ejecutó inventario y búsqueda sobre los 226 archivos versionados. Se excluyeron como código fuente node_modules, .venv, caches, dist generado, datos de imágenes y binarios de outputs. Esos árboles solo se inventariaron cuando eran relevantes para artifacts.

### PostgreSQL, scripts y orquestadores

- malaria_dl_local_project/db/init/001_schema.sql, 002_indexes.sql, 003_views.sql, 004_seed.sql, 007_case_level_explainability_views.sql, 008_case_level_explainability_indexes.sql, 009_uploaded_predictions_views.sql, 010_clinical_inference_tracking.sql, 011_label_mapping_clinical_v1.sql, 012_dataset_split_image_tracking.sql, 013_dataset_browser_views.sql, 017_clinical_run_tracking.sql, 018_visual_audit_views.sql, 019_model_execution_parameters.sql, 020_max_epochs_release.sql y 022_run_lineage.sql.
- malaria_dl_local_project/scripts/backfill_run_lineage.py, clean_training_outputs.py, create_physical_dataset_split.py, diagnose_run_lineage.py, download_malaria_dataset.py, init_db.py, purge_db_data.py, register_physical_split_in_db.py, reset_experimental_state.py y test_db.py.
- malaria_dl_local_project/run_train_all_models.py, run_evaluate_all_trainings.py y run_explain_all_trainings.py.
- scripts/validate.sh.

### Servicios ML

- malaria_dl_local_project/src/__init__.py, calibrate.py, calibration.py, checkpoint_policy.py, config.py, data.py, dataset_registry.py, db.py, decision.py, ensemble.py, evaluate.py, execution_types.py, explain.py, export_dataset.py, image_quality.py, inference_pipeline.py, metrics.py, model_execution_config.py, model_metadata.py, models.py, predict_image.py, prediction_uploads.py, preprocessing.py, run_lineage.py, run_tracker.py, svm_features.py, threshold_calibration.py, tracking_integration.py, train.py, training_plots.py y tta.py.

### Backend

- backend_api/app/__init__.py, db.py y main.py.
- backend_api/app/routes/__init__.py, artifacts.py, catalog.py, dashboard.py, dataset.py, explainability.py, health.py, metrics.py, observability.py, predictions.py y runs.py.
- backend_api/app/schemas/__init__.py y common.py.
- backend_api/app/services/artifacts.py, dataset_browser.py, explainability.py, run_lineage.py y serialization.py.
- backend_api/tests/test_artifacts_api.py, test_clinical_summary_api.py, test_dataset_browser_api.py, test_explainability_api.py, test_grouped_run_lineage_api.py, test_model_comparison_api.py y test_run_detail_api.py.
- backend_api/README_API.md, .env.example y requirements.txt.

### Frontend

- frontend/src/App.tsx, main.tsx, services/api.ts, types/api.ts, styles.css y vite-env.d.ts.
- frontend/src/components/ClinicalMetricsCards.tsx, ConfusionMatrix.css, ConfusionMatrix.tsx, DataTable.tsx, DomainBadge.tsx, Layout.tsx, Loading.tsx, MetricCard.tsx y StatusBadge.tsx.
- frontend/src/components/reports/AutoAnalysisBadge.tsx, CommandChips.tsx, LineageBadge.tsx, MetricChip.tsx, MiniConfusionMatrix.tsx, ReportBadge.tsx, ReportFilters.tsx, ReportSelectFilter.tsx, RunLineageChildCard.tsx, RunProcessBadge.tsx, RunSummaryRow.tsx, TrainingRunGroupCard.tsx y UnlinkedRunsSection.tsx.
- frontend/src/pages/ClinicalEvaluation.tsx, Dashboard.tsx, DatasetBrowser.tsx, DatasetsModels.tsx, ErrorsLogs.tsx, Explainability.tsx, ModelComparison.tsx, RunDetail.tsx, Runs.tsx y UploadedPredictions.tsx.
- frontend/src/utils/explainability.ts, format.ts, runDetail.ts y runReport.ts.
- frontend/package.json, package-lock.json, index.html, tsconfig.json, tsconfig.node.json, vite.config.ts, README_FRONTEND.md y .env.example.

### Tests ML

Se inspeccionaron los 61 archivos:

- test_artifact_tracking.py, test_backend_endpoints.py, test_backfill_run_lineage.py, test_calibration.py, test_checkpoint_lineage_resolution.py, test_checkpoint_policy.py, test_checkpoint_policy_tracking.py y test_checkpoint_selection_metadata.py.
- test_clean_training_outputs.py, test_clinical_metrics.py, test_clinical_metrics_tracking.py, test_clinical_validation_callback.py, test_data_loading.py, test_dataset_browser_api.py, test_dataset_browser_queries.py y test_dataset_image_pagination.py.
- test_dataset_registry.py, test_db_migrations.py, test_decision.py, test_densenet_model.py, test_diagnose_run_lineage.py, test_early_stopping_policy.py, test_ensemble_threshold_integration.py y test_evaluate_lineage_tracking.py.
- test_evaluate_threshold_modes.py, test_execution_types.py, test_explain_lineage_tracking.py, test_explain_threshold_integration.py, test_image_quality.py, test_inference_pipeline.py, test_inference_pipeline_threshold.py y test_label_mapping.py.
- test_max_epochs_config.py, test_max_epochs_main_smoke.py, test_max_epochs_tracking.py, test_metrics.py, test_minimal_keras_inference.py, test_model_execution_config.py, test_model_execution_outputs.py y test_model_execution_tracking.py.
- test_model_metadata_integration.py, test_model_metadata_threshold.py, test_physical_dataset_split.py, test_predict_image_outputs.py, test_predict_image_threshold_modes.py, test_prediction_collapse.py, test_preprocessing.py y test_purge_db_data.py.
- test_run_io_tracking.py, test_run_lineage.py, test_run_lineage_migration.py, test_threshold_calibration.py, test_threshold_calibration_tracking.py, test_threshold_clinical_mode.py, test_tracking_integration.py y test_train_checkpoint_policy_args.py.
- test_train_integration.py, test_training_history_outputs.py, test_training_plots.py, test_training_selection.py y test_tta_threshold_integration.py.

### Documentación y configuración

- .gitignore.
- data/prediction_uploads/.gitkeep y malaria_dl_local_project/data/.gitkeep.
- malaria_dl_local_project/.gitignore, .env.example, requirements.txt, README.md y README_2.md.
- malaria_dl_local_project/db/README_DB.md.
- Los 13 documentos de malaria_dl_local_project/docs: checkpoint_policy.md, clinical_metrics.md, database_dataset_tracking.md, dataset_browser.md, frontend_clinical_dashboard.md, informe_tecnico_integral_auditoria_2026-07-07.md, physical_dataset_split.md, postgresql_tracking.md, reporte_tecnico_capstone.md, reset_experimental_state.md, threshold_calibration.md, training_evaluation_inference_workflow.md y workflows.md.

## Apéndice C. Cobertura y brechas de pruebas

### Inventario

- 68 archivos Python de pruebas.
- 313 métodos test detectados.
- malaria_dl_local_project/tests: 61 archivos y 282 métodos.
- backend_api/tests: 7 archivos y 31 métodos.
- Frontend: 0 archivos de pruebas.

### Cobertura existente valiosa

- Ambigüedad de resolución por checkpoint, UUID y artifacts.
- Tracking y backfill de run_lineage.
- Selección clínica y early stopping.
- Convención de labels y probability_parasitized.
- Thresholds en evaluación, explicación, inferencia, TTA y ensemble.
- Seguridad de path traversal en artifacts.
- Respuestas del grouped lineage y secciones unresolved/conflict.
- Migraciones verificadas principalmente por estructura/texto.

### Brechas

- Lifecycle de model_versions.
- Inmutabilidad y checksum extremo a extremo.
- Finalización transaccional/concurrente.
- FK y constraints contra PostgreSQL real.
- Promoción/rollback de deployments.
- Snapshot de threshold y label convention en deployment.
- Cadena completa deployment → inference → job → prediction.
- Reconciliación de dual-write.
- Contratos de API por IDs.
- Tests frontend y E2E.

scripts/validate.sh no ejecuta actualmente los 31 tests de backend_api/tests; solo incluye la suite del proyecto ML y un test de endpoints ubicado dentro de ella. Tampoco hay comando de test/lint en frontend/package.json.

### Baseline ejecutado durante la auditoría

- scripts/validate.sh: 276 pruebas ML aprobadas, 15 omitidas; 7 pruebas de malaria_dl_local_project.tests.test_backend_endpoints aprobadas; build Vite/TypeScript aprobado.
- backend_api/.venv/bin/python -m unittest discover -s backend_api/tests: 31 pruebas aprobadas.
- No se ejecutaron scripts de escritura en PostgreSQL, backfill, purge, reset ni limpieza.

## Apéndice D. Scripts de migración, backfill y limpieza

### Migración

- scripts/init_db.py aplica por nombre los 16 SQL de db/init en una transacción.
- No hay Alembic, tabla de ledger, checksum de migración ni downgrade.
- El parser manual por punto y coma incrementa el riesgo si un DDL futuro contiene bloques complejos.

### Linaje

- scripts/backfill_run_lineage.py es dry-run por defecto y evita resolver ambigüedades; es una buena base.
- scripts/diagnose_run_lineage.py es de solo lectura.
- Ambos cubren principalmente evaluation/explainability, no todo el universo de inferencia/derivados.

### Datos y artifacts

- clean_training_outputs.py, purge_db_data.py y reset_experimental_state.py tienen salvaguardas/dry-run o confirmación, pero pueden borrar archivos o truncar datos si se autorizan.
- clean_training_outputs.py no cubre consistentemente todas las carpetas de arquitectura observadas y puede dejar paths en DB sin bytes.
- test_db.py escribe en la base configurada y no limpia todas sus filas; debe apuntar a una base aislada.

Ninguno de estos scripts debe ejecutarse como parte de Stage 0 hasta contar con backup, inventario referencial, política de retención y protección de deployments.

## Apéndice E. Hotspots de implementación

Las líneas corresponden al commit auditado:

| Tema | Ubicaciones principales |
|---|---|
| Convención clínica | malaria_dl_local_project/src/config.py:11-40 |
| Escritura mutable del mejor checkpoint | src/checkpoint_policy.py:603-672 |
| Directorio/alias y carga del mejor modelo | src/train.py:1189-1200 y 1695-1704 |
| Backup/lock del alias | src/train.py:1033-1134 |
| UUID y snapshot de training | src/train.py:1382-1387 y 2025-2071 |
| Registro de artifacts/version | src/train.py:2112-2181; src/run_tracker.py:921-1027 y 1585-1619 |
| Tracking best-effort | src/run_tracker.py:154-204 |
| Entrada/salida de evaluación | src/evaluate.py:21-68 y 254-255; run_evaluate_all_trainings.py |
| Entrada/output global de explicación | src/explain.py:81-149 y 676-686; run_explain_all_trainings.py |
| Ownership incompleto del checkpoint | src/run_lineage.py:418-441 |
| Threshold desde sidecar | src/model_metadata.py:66-97 y 169-292 |
| Mutación opcional del sidecar | src/calibrate.py:405-491 |
| Paths en inferencia | src/predict_image.py:46-128, 1019-1064 y 1228-1303 |
| Tablas base/model_versions | db/init/001_schema.sql:43-103 |
| Métricas, política y threshold clínicos | db/init/017_clinical_run_tracking.sql |
| Lineage | db/init/022_run_lineage.sql:1-65 |
| API read-only | backend_api/app/main.py:18-33 |
| Path fallback de artifacts | backend_api/app/services/artifacts.py:34-123 |
| Menú/PageKey | frontend/src/components/Layout.tsx:5-36 |
| Navegación por estado | frontend/src/App.tsx:17-109 |
| artifact_id/path fallback del cliente | frontend/src/services/api.ts:29-89 |
| Migración/backfill | scripts/init_db.py; scripts/backfill_run_lineage.py; scripts/diagnose_run_lineage.py |

## Conclusión

La base técnica permite una estabilización incremental. El repositorio no necesita rehacer su tracking: necesita convertir model_versions y artifacts en la identidad obligatoria, cerrar las FKs ya previstas en run_lineage, congelar la decisión clínica en deployments y formalizar los jobs de inferencia. El alias best_model.keras puede sobrevivir como compatibilidad local, pero nunca volver a ser la referencia oficial.
