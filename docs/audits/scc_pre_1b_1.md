# SCC-PRE.1B.1 — Auditoría HTTP/SQL y propuesta de respuesta

Fecha: 2026-10-16. Estado: preparado para revisión técnica; **no implementa ni certifica operativamente el Preflight**.

Fuente normativa: [SCC-PRE.1A](../contracts/scc_pre_1a.md), leído antes del código. Se consultó también `/Users/julio/Desktop/Capstone - Inventario de datos existentes y su origen.md` como inventario descriptivo. Ninguno fue modificado.

La base reutilizable existe: lectura científica TRAIN, assessments por intento y registros gobernados. Faltan una lectura consistente entre dominios, selección tipada sin equivalencias implícitas, cobertura poblacional y dictámenes por análisis. No se justifican tablas nuevas ni un catálogo físico centralizado.

## 1. Alcance y grado de verificación

**Verificado estáticamente:** rutas, servicios, SQL, modelos públicos, proyecciones, productores E6, esquema versionado y consumidores de Comparación Científica citados aquí. Los DDL acreditan el esquema esperado, no su instalación efectiva ni la presencia de registros.

**Verificado operativamente: ninguno.** No se ejecutaron HTTP, SQL, pruebas, procesos científicos ni comprobaciones de archivos. La disponibilidad del entorno operativo no fue comprobada; no se afirma que esté caído. Quedan pendientes autorización real, esquema desplegado, cobertura por TRAIN, consistencia bajo concurrencia e integridad física. La auditoría no necesita extraer resultados científicos para establecer estas brechas.

Método ejecutado: `git status --short`, búsquedas acotadas `rg -n` / `rg --files` y lectura `cat` / `sed` de las fuentes citadas. Estado inicial de Git limpio. Las suites mencionadas en §7 se localizaron/inspeccionaron, no se ejecutaron. Único entregable nuevo: este informe; sin cambios de código, contratos aprobados, inventario, skills, PostgreSQL, commit o push.

## 2. Mapa HTTP/SQL reutilizable

Referencias abreviadas:

- **R:** [routes/runs.py](../../backend_api/app/routes/runs.py).
- **S:** [ScientificReadService](../../backend_api/app/services/scientific_results.py), [ScientificReadRepository / read_scientific_results / metric_dto](../../backend_api/app/repositories/scientific_results.py).
- **A:** [routes/assessments.py](../../backend_api/app/routes/assessments.py), [AssessmentReadService](../../backend_api/app/services/assessments.py), [AssessmentReadRepository](../../backend_api/app/repositories/assessments.py).
- **D:** [routes/dataset_versions.py](../../backend_api/app/routes/dataset_versions.py), [governed_datasets.py](../../backend_api/app/services/governed_datasets.py).
- **DB:** [db.py](../../backend_api/app/db.py); **DDL:** [tablas](../../alembic_v2/baseline/03_tables.sql), [vistas](../../alembic_v2/baseline/08_views.sql), [funciones](../../alembic_v2/baseline/04_functions.sql).

Todas las operaciones de esta tabla son GET. `datasource` resuelve únicamente `malaria`; otro valor produce 404. Las rutas R de detalle, política, calibración, artefactos y predicciones tienen alias `/api/runs/...`.

| Ruta | Implementación canónica actual y SQL | Identificadores y campos realmente devueltos | Paginación, ausencia y reutilización |
|---|---|---|---|
| `/runs/{run_id}/scientific-results?view=traceability` | R.scientific_results → S.read → `read_scientific_results`; después `AssessmentReadRepository.list` | UUID TRAIN; `contract_version=scc_core_1`, `training_run_id`, `model`, `training`, `evidence`, `assessments`, `evidence_status`, `references`. Evidence: configuraciones, evaluations, miembros de ensemble, métricas clínicas con razones de indefinición, historia, XAI, dataset_version, model_versions, checkpoint_policy, run_metrics, artifacts, io_records y predictions | Predicciones: 100 por defecto, máximo 1000, offset, total; orden `created_at,id`. Otros conjuntos sin paginar; assessments internos usan `LIMIT NULL`. 404 TRAIN ausente; 422 no TRAIN o modelo conocido no clasificación. A1–A6 como evidencia, sin dictamen. `evaluations` filtra `run_id`, no `training_run_id`: no descubre automáticamente evaluaciones de runs hijos |
| `/runs/{run_id}` | R.get_run; SQL directamente en ruta mediante DB.fetch_one/fetch_all, sin servicio/repositorio de dominio | run_id string; `run=r.*` más experiment_name/model_name/model_type/dataset_name; `metrics`, `artifacts`, `training_history`, `errors` | Sin paginación. 404 run ausente. Consultas/conexiones separadas. A4 e historia; preferir S para el nuevo orquestador, evitando copiar SQL |
| `/api/datasets/{dataset_version_id}` | D.governed_dataset_version_detail; `_summary`, `_statistics`, `_latest_checks`; `resolve_trainable_materialization`, `get_dataset_version_trainability` | UUID versión; `dataset`, `distribution`, `integrity`, `validation`, `materialization`, `lineage`, `lifecycle`, `runs`. Dataset: semver, estado, seed, class_mapping, algoritmo/grouping; lineage: cuatro fingerprints del freeze_contract; materialización: id, estado, reconciliación, conteos, intento | Sin paginación; 404 versión ausente. Estadísticas/checks seleccionan registros más recientes. No lista las muestras. A1/A2; ceros y booleanos derivados con defaults no acreditan ausencia de conflictos ni población vacía |
| `/runs/{run_id}/checkpoint-policy` | R.get_run_checkpoint_policy → DB.fetch_all → `vw_checkpoint_policy_summary` | string convertido a UUID SQL; run_id, model_name, checkpoint_policy, min_recall_required, selected_epoch, policy_satisfied, selected_metric/value, métricas VAL, flags de colapso, warning, checkpoint_path, created_at | Sin paginación, fecha descendente. `items=[]` tanto sin registros como run inexistente. A5/A4. La vista omite `checkpoint_artifact_id`, `model_version_id` y policy_config; S lee la tabla completa |
| `/runs/{run_id}/threshold-calibration` | R.get_run_threshold_calibration → DB.fetch_all → `vw_threshold_calibration_summary` | run_id, model_name, threshold_policy/source/selected, default_threshold, target_recall/satisfied, recall/specificity/F2/PR-AUC/ROC-AUC VAL, warning, calibration_split, created_at | Sin paginación, fecha descendente, vacío ambiguo. A6 contextual; la vista omite id de calibración, evaluaciones default/selected, score_name, label_mapping y model_version_id presentes en tabla; no identifica el umbral del intento seleccionado |
| `/runs/{run_id}/image-predictions` | R.get_run_image_predictions → COUNT y SELECT de `run_image_predictions` mediante DB.fetch_one/fetch_all | run_id; filtros split/case_type/class_name/is_correct; `items,total,limit,offset`. Filas: run_image_prediction_id, image_id, split_name, usage_context, etiquetas, probabilidades, raw_model_score/meaning, threshold_used/source, is_correct, case_type, metadata, created_at | 100/1000; offset; **solo `ORDER BY created_at DESC`**, sin desempate; count y página en conexiones separadas. Vacío ambiguo. Sin evaluación/intento ni filtro por ellos. A3/A6 históricos, no reemplaza resultados E6. traceability sanitiza localizadores |
| `/runs/{run_id}/artifacts-summary` (también `/artifacts`) | R.get_run_artifacts_summary → DB.fetch_all → `vw_run_artifacts_summary` | run_id, artifact_type, artifact_path, exists, created_at, name, mime_type, file_size_bytes, metadata | Sin paginación, fecha descendente, vacío ambiguo. **Omite id/checksum**, y `exists` proviene de metadata con default TRUE. A5 solo inventario; usar S o ArtifactReadRepository para identidad/hash |
| `/assessments?training_run_id=…&view=traceability` | A.list → repository.list; JOIN identities/attempts/runs y consumers de campaña | UUID training_run_id/campaign_id opcionales; items + contract=assessment_identity_v1. identity_id/hash, attempt_id, ordinal/state, TRAIN/model, kind/split/purpose, timestamps, verification, dataset_version_id, checkpoint_artifact_id, threshold; proyección agrega assessment_type y estados de evidencia | 50 por defecto, máximo 500; offset; orden started_at DESC,id. Sin total. Sin coincidencias devuelve vacío, no certifica existencia del TRAIN. Lista múltiples identidades/intentos, no selecciona uno |
| `/assessments/{attempt_id}?view=traceability` | A.detail → repository.detail; JOIN attempt→identity→TRAIN | UUID **del intento**, no identity_id ni evaluations.id. Campos del intento, verification, identity completa, identity_hash, training_run_id, kind, model_id; sin owner/host/pid y con sanitización pública | Sin paginación; 404 intento ausente. Identity incluye samples completos: respuesta potencialmente grande. A1–A6 y XAI según kind |
| `/assessments/{attempt_id}/results?view=traceability` | A.payloads → detail + repository.payloads; SELECT payload de assessment_results | UUID intento; items payload + attempt_id, identity_id, training_run_id, model_id, split. EVALUATE: sample_id, patient_id, label, raw_score, calibrated_score, threshold, predicted. EXPLAIN: sample_id, patient_id, specification, result, artifacts | 100/1000, offset, orden sample_id. Sin total ni indicador complete. Traceability: 404 si no existe intento; existing: vacío incluso si no existe. A3/A6; detalle y página se leen en transacciones distintas |
| `/assessments/{attempt_id}/artifacts?view=traceability` | A.payloads → SELECT payload de assessment_artifacts | UUID intento; artifact_id/sample_id/role/hash/tamaño según payload, procedencia añadida, file_availability=not_checked; localizadores ocultos | 100/1000, offset, orden sample_id,role; sin total. Misma semántica de ausencia. XAI/A5; no verifica bytes |

**Autorización y errores comunes.** R y A no declaran `require_permission`; [main.py](../../backend_api/app/main.py) tampoco instala autenticación global al incluirlos. Es una brecha estática, no una afirmación sobre un proxy externo. D exige `DATASETS_READ`. [security.py](../../backend_api/app/security.py) valida Bearer JWT y roles actuales de PostgreSQL: 401 autenticación, 403 permiso; con `auth_mode=disabled` concede principal local administrador. No se inspeccionó la configuración activa. UUID tipados producen 422 ante formato inválido; los run_id string casteados solo en SQL pueden terminar en 500. Excepciones SQL no capturadas llegan al handler genérico 500 `INTERNAL_ERROR`; el envelope actual es `error{code,message,details,correlation_id,retryable}`. No convertir estos errores en colecciones vacías.

**Contratos existentes.** [ScientificRead](../../backend_api/app/schemas/scientific_read.py) usa Pydantic pero `evidence` es diccionario abierto; A usa `list[dict[str,Any]]`. [scientific_public.py](../../backend_api/app/services/scientific_public.py) elimina localizadores y canonical_configuration, incluso anidados; `available` indica registro, no integridad/completitud. Frontend: [scientificRead.ts](../../frontend/src/types/scientificRead.ts), [useComparisonRun](../../frontend/src/hooks/useComparisonRun.ts) y [AssessmentComparison](../../frontend/src/components/reports/AssessmentComparison.tsx). Este último conserva selección explícita de intentos con checkboxes, sin default «último».

## 3. Resolución de V1–V6

### V1 — Identidades y agregados

Cadena E6: `runs.id TRAIN ← assessment_identities.training_run_id ← assessment_attempts.identity_id ← assessment_results.attempt_id`. La identidad JSON fija `model{training_run_id,model_version_id,checkpoint_artifact_id,sha256,bytes,input_contract,source}`, dataset, samples, split, purpose, protocol, decision, seed, batch_size y metrics_definition. El intento conserva ordinal, estado y `verification{count,sha256,metrics}`; métricas y filas deben proceder del mismo intento. TEST es kind=evaluate/split=test; no existe una identidad universal «evaluation_id» que pueda sustituir al intento.

Otra cadena: `evaluations.id → predictions.evaluation_id`, con `evaluations.training_run_id`, `run_id`, checkpoint/model_version/dataset, hashes de protocolo/población/input/comparison, protocol_snapshot, threshold y metric_definition. `evaluations.source_assessment_attempt_id` permite un vínculo **explícito** con E6; su ausencia no permite inventarlo. `run_image_predictions` no dispone de este vínculo en sus columnas. Consultar una evaluación histórica exacta exige extender la lectura del repositorio por evaluations.id, conservando su run de ejecución y TRAIN padre.

La estructura permite varias identidades por TRAIN y varios intentos por identidad; no se certificó cardinalidad real. A.detail ya resuelve el intento exacto. Las listas de A/S no eligen último. [assessment_lineage.py](../../backend_api/app/repositories/assessment_lineage.py) calcula attempt_rank pero `visible_assessments` conserva todas las filas: no confundir ranking con filtrado. En cambio R.get_run_clinical_summary usa `latest_item` para métricas/política/calibración: es un resumen de UI, **no seleccionador científico**. Cambio mínimo: requerir selección explícita en el nuevo contrato y consultar por esa clave; no modificar globalmente los resúmenes.

### V2 — Checkpoint

S devuelve artifacts con id/run_id/checksum/tamaño y model_versions, además de policy completa. La identidad E6 permite contrastar esos registros contra el checkpoint utilizado; epoch aparece en `model.source.epoch` para E5 y en selected_epoch de policy. Una política sin vínculo inequívoco al artifact seleccionado no prueba su época.

[ArtifactReadRepository.get](../../backend_api/app/repositories/artifacts.py) recupera por artifact_id y fuente, con TRAIN e intento cuando corresponde. [scientific_artifact](../../backend_api/app/services/artifacts.py) valida pertenencia solicitada, localizador, tamaño/hash cuando registrado y formato. `/artifacts/file` exige ARTIFACTS_READ; admite imágenes, npy/json/csv, **no .keras**. Distingue ARTIFACT_NOT_REGISTERED (404), RELATION_MISMATCH (404), CONTENT_MISSING (410), INTEGRITY_FAILED (409), STORAGE_UNAVAILABLE (503), MEDIA_INVALID (415). No usar esta descarga como verificador público de checkpoints.

Existe [execution.artifacts.file_identity](../../malaria_dl_local_project/src/malaria_dl/execution/artifacts.py): resuelve localizador científico, rechaza archivo no final/symlink y calcula SHA-256/tamaño sin cargar Keras. [assessment.lineage.resolve](../../malaria_dl_local_project/src/malaria_dl/assessment/lineage.py) contrasta TRAIN, versión, artifact y bytes, pero pertenece al flujo de ejecución y exige evidencia completa. No invocar el resolver completo desde Preflight ni convertir un archivo ausente en rechazo de métricas trazables. Si B.2 necesita comprobar bytes, un adaptador de lectura acotado debe reutilizar los verificadores y distinguir archivo ausente, localización inválida y acceso fallido; `file_identity` por sí solo agrupa varias causas en CHECKPOINT_NOT_FINALIZED.

Métricas persistidas son comparables sin cargar `.keras` si evaluación/intento, población, protocolo y checkpoint registrado tienen linaje acreditado. Disponibilidad física e integridad actual permanecen `not_checked` hasta una comprobación específica; un hash persistido no acredita bytes actuales.

### V3 — Muestras y cobertura

[assessment.lineage.dataset_samples](../../malaria_dl_local_project/src/malaria_dl/assessment/lineage.py) asigna sample_id desde source_record_id. [data/sample_repository.py](../../malaria_dl_local_project/src/malaria_dl/data/sample_repository.py) centraliza `select_dataset_sample_ids` y `select_dataset_sample_records`: assignments por dataset/split JOIN dataset_source_records; orden source_record_id. E6 acredita así el namespace `dataset_source_records`, **no el de muestras clínicas ni cualquier image_id**. `predictions.dataset_source_record_id` es otra referencia explícita posible; no alinear históricos por nombre de archivo o formato UUID.

DDL: PK de assessment_results=(attempt_id,sample_id), payload.sample_id consistente, pertenencia a identity.samples, etiqueta/umbral/predicción coherentes por trigger; finalización verified exige count completo y hash. Filas y terminales son inmutables según guards. Esto permite una lectura estable de intentos terminales, condicionado a verificar esas garantías desplegadas. Intentos activos pueden recibir inserciones entre páginas. El detalle conserva población esperada; verification.count describe filas verificadas, no necesariamente todas las muestras del split si hubo una selección.

Datos suficientes para diseñar intersección, exclusivos, faltantes y conflictos de etiquetas entre intentos E6: sí. Operación que entregue cobertura completa y diagnósticos P4: no. Debe contrastar población declarada, filas recuperadas, claves únicas, assignments y completitud; nunca confundir `len(items)` con población total. La PK impide duplicados exactos dentro de un intento E6 bajo el esquema esperado, pero no demuestra ausencia de duplicados de contenido ni etiquetas contradictorias entre fuentes/versiones.

Las páginas E6 de resultados tienen orden único por PK; las de artefactos necesitan desempate artifact_id si no se acredita unicidad sample_id/role. `predictions` usa created_at,id (orden total); `run_image_predictions` no, y su count es otra lectura. Offset con datos mutables puede omitir/repetir filas aun con desempate. Extensión mínima: consultas con conexión compartida, conteo de filas/únicos, cursor estable por clave y contrato de completitud. Para un intento terminal realmente inmutable, agotamiento de páginas y contraste con población/count permiten acreditar totalidad sin snapshot entre peticiones; no aplicar esto a intentos activos.

No se calcularon intersecciones, métricas ni comparaciones. El futuro informe debe separar población original e intersección, mostrar numerador/denominador por TRAIN y ratio null con razón si denominador desconocido o cero; preservar duplicados/conflictos y referencias recuperables a las claves afectadas.

### V4 — Configuración

`run_configurations` contiene architecture, random_seed, optimizer, learning_rate/fine_tune_learning_rate, batch_size, epochs, early stopping, checkpoint monitor/mode, dropout, L2, dimensiones, weights, fine_tune_layers, normalization/internal_preprocessing, loss_function, clinical_target_recall, configuration_hash, optimizer_extensions, extension_configuration y provenance_snapshot. S lo recupera; no se acredita que todo TRAIN tenga fila.

`runs.parameters` y `execution_parameters` complementan la evidencia. [persistence/v2_projection.py](../../malaria_dl_local_project/src/malaria_dl/persistence/v2_projection.py) persiste extension_configuration y provenance_snapshot; [execution/train.py](../../malaria_dl_local_project/src/malaria_dl/execution/train.py) consume `resolved.execution.no_augment`. Augmentación requiere extracción explícita desde el snapshot/configuración correspondiente, no una columna universal ni defaults actuales. `train_execution_sessions.configuration` y `train_execution_records` son fuentes adicionales; S no los lee hoy. Reutilizar sus lectores de ejecución solo en modo consulta o añadir proyección acotada en S si la evidencia pública resulta insuficiente. Registrar ruta JSON y fuente de cada valor normalizado; conservar contradicciones, no decidir prioridad silenciosa. Diferencias experimentales son advertencias salvo condición controlada explícitamente incumplida.

### V5 — EXPLAIN y representaciones

[assessment.service](../../malaria_dl_local_project/src/malaria_dl/assessment/service.py), contracts y runtime persisten `identity.explanation` (method gradcam/lime/shap, class, layer, num_samples, background y selección), seed/batch_size/code; payload.specification/result (capa resuelta para Grad-CAM) y referencias de artifacts. SHAP normaliza background a registros con sample_id, etiqueta y hash. `background_sample_id` de la petición HTTP no es una columna universal: extraerlo de explanation.background; el request puede además aparecer en identity.http_request. EXPLAIN conserva su propio intento, model/checkpoint y `identity.evaluation={attempt_id,identity_hash}` cuando tiene padre. Null es EXPLAIN independiente, no ausencia de ejecución.

S también recupera xai_evidence/xai_artifacts y evaluaciones/interpretaciones XAI. xai_evidence contiene target_layer/class, input/checkpoint hash, background_manifest hash, method_configuration_id, environment_snapshot y enlaces de evaluación/muestra/intento. **S no recupera xai_method_configurations**, cuya tabla contiene method/implementation/version/parameters/configuration_hash: falta ese JOIN/lector por ids para comparar metodología de esta fuente. Dos artefactos del mismo método no prueban equivalencia metodológica.

En las lecturas científicas y módulo science inspeccionados no se identificó contrato de recuperación de embeddings/PCA/UMAP/CKA con orden de muestras, capa, dimensión y transformaciones. Descarga genérica de .npy no lo acredita. Cobertura de recuperación metodológica: ausente en ese alcance; existencia real de archivos/registros: no verificada. Informar evidencia insuficiente según análisis, sin extraer ni calcular.

### V6 — Consistencia y reutilización

DB.read_only_transaction ejecuta SET TRANSACTION READ ONLY, statement_timeout=10s, lock_timeout=2s y rollback. No fija REPEATABLE READ: una transacción no implica snapshot estable entre SELECT bajo READ COMMITTED. S lee su repositorio y assessments en transacciones distintas; A.detail y payloads también. fetch_one/fetch_all abren conexiones separadas; D comparte conexión pero no establece snapshot/restricción READ ONLY explícitos.

Para B.2: usar una conexión de lectura con aislamiento explícito y reutilizar funciones de repositorios que acepten esa conexión. Aislar consultas de dominio mediante savepoints para que un fallo SQL no deje abortada la transacción de todo el reporte; un fallo de conexión afecta todas las dependencias aún no consultadas y debe declararse. No realizar HTTP interno en cadena. El snapshot SQL no acredita bytes del filesystem: conservar checked_at y resultado independiente por artefacto.

El [comparador E7](../../malaria_dl_local_project/src/malaria_dl/science/comparison.py) es otro consumidor: `read_evaluation` usa un parámetro llamado evaluation_id que representa un attempt E6, verifica bytes/población y `compare` calcula estadísticas/selección. No reutilizarlo como orquestador PRE: impone dependencias físicas y cálculos fuera del alcance. [GET /models/comparison](../../backend_api/app/routes/catalog.py) solo lee vw_clinical_run_summary, máximo 500/default 100; tampoco implementa A1–A6.

## 4. Matriz A1–A6

Cobertura de la capacidad técnica existente; **todas las filas son verificadas estáticamente y no verificadas operativamente**, no dictámenes sobre TRAIN concretos.

| Dimensión | Evidencia necesaria | Operación reutilizable | Cobertura | Brecha |
|---|---|---|---|---|
| A1 | Dataset TRAIN y población evaluada, procedencia | S + D + A.detail | Parcial | Contrastar relación y fingerprints; defaults del resumen no acreditan evidencia; equivalencia entre versiones no automática |
| A2 | Split y población atribuida al resultado | A.detail + evaluations + select_dataset_sample_ids/records | Parcial | Nombre de split no prueba población; exactitud histórica y consistencia entre lecturas |
| A3 | Claves, etiquetas, población completa y alineación | A.results + A.detail + sample_repository | Parcial | Cobertura/completitud, conflictos y denominadores no expuestos; históricos sin correspondencia universal; páginas mutables |
| A4 | Configuración persistida y políticas efectivas | S.run_configurations/training; R.get_run | Parcial | Normalización y procedencia de augmentación/snapshots; no inferir configuración efectiva desde defaults |
| A5 | Artifact, TRAIN, época/política y estados físicos separados | S + ArtifactReadRepository.get + verificadores existentes | Parcial | Vista resumen pierde id/hash; falta adaptador consultivo .keras si se requiere comprobar bytes; nunca obligatorio para métricas trazables |
| A6 | Evaluación/intento, protocolo, scores/clases, regla, resultados | A.detail/results; S.evaluations/metrics; calibración como contexto | Parcial | Selección histórica exacta, vínculo a métricas/calibración, tipado y snapshot; no confundir métricas E6 VAL y TEST ni definiciones v1/v2 |

## 5. Propuesta de contrato tipado (diseño, no implementación)

Usar Pydantic BaseModel/UUID/Literal y equivalente TypeScript, snake_case y `contract_version='scc_pre_1'`, siguiendo scc_core_1. El versionado identifica el contrato de respuesta, no un preflight de versiones PostgreSQL. Tipos siguientes son notación TypeScript documental; UUID y SHA256 se validan en backend, DateTime es ISO-8601 con zona; números finitos, conteos enteros no negativos.

```ts
type UUID = string;
type SHA256 = string;
type DateTime = string;
type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
type ScientificState = 'COMPARABLE' | 'COMPARABLE_CON_ADVERTENCIAS'
  | 'NO_COMPARABLE' | 'EVIDENCIA_INSUFICIENTE';
type Dimension = 'A1' | 'A2' | 'A3' | 'A4' | 'A5' | 'A6';
type Split = 'train' | 'val' | 'test';

type Observation<T> =
  | { state: 'known'; value: T; evidence_ids: string[] }
  | { state: 'unknown' | 'not_applicable' | 'not_checked'; reason: string;
      evidence_ids: string[] }
  | { state: 'query_error'; error_ids: string[] };

type EvaluationRef =
  | { source: 'assessment'; identity_id: UUID; attempt_id: UUID;
      identity_hash: SHA256; attempt_state: string }
  | { source: 'evaluations'; evaluation_id: UUID; execution_run_id: UUID;
      source_assessment_attempt_id: UUID | null };

interface Selection {
  selection_id: string;
  training_run_id: UUID;
  evaluation: Observation<EvaluationRef>;
  split: Observation<Split>;
  checkpoint: Observation<{ artifact_id: UUID; model_version_id: UUID | null;
    sha256: Observation<SHA256>; epoch: Observation<number>;
    policy: Observation<string> }>;
  explain_attempt_ids: UUID[];
}
interface Scope {
  scope_id: string;
  requested_training_run_ids: UUID[];
  participating_training_run_ids: UUID[];
  selection_ids: string[];
  excluded: { training_run_id: UUID; reason_ids: string[] }[];
  population: 'original' | 'intersection' | 'explicit_subset' | 'not_applicable';
  population_id: string | null;
  question: string; // afirmación evaluada: descriptiva, pareada, controlada, etc.
}
interface EvidenceRef {
  evidence_id: string;
  source: string; // vocabulario de fuentes de dominio, no una ruta de disco
  operation: string; // nombre de lector canónico / método y ruta HTTP
  record_keys: { [key: string]: string };
  field: string | null; // campo o JSON Pointer exacto
  selection_ids: string[];
  observed_at: DateTime;
  verification: 'static' | 'operational' | 'not_verified';
  value: Observation<Json>;
  content_hash: SHA256 | null;
}
interface Finding {
  reason_id: string;
  code: string; // estable para frontend
  kind: 'difference' | 'warning' | 'missing' | 'incompatibility';
  message: string;
  condition: string;
  affected_selection_ids: string[];
  affected_training_run_ids: UUID[];
  evidence_ids: string[];
  values: { selection_id: string; value: Observation<Json> }[];
}
type Verdict =
  | { evaluation_status: 'evaluated'; scientific_state: ScientificState;
      error_ids: string[] }
  | { evaluation_status: 'not_evaluated'; scientific_state: null;
      error_ids: string[] }; // no vacío: error técnico que impide dictamen
interface DimensionResult {
  dimension: Dimension;
  scope: Scope;
  verdict: Verdict;
  evidence_ids: string[];
  findings: Finding[];
}
interface AnalysisResult {
  analysis_id: string; // único por análisis concreto y alcance
  module_id: string; // curves, metrics, consensus, xai, pca, umap, cka
  scope: Scope;
  verdict: Verdict;
  dimension_refs: { dimension: Dimension; scope_id: string }[];
  evidence_ids: string[];
  findings: Finding[];
  individual_data: { selection_id: string;
    availability: Observation<boolean>; references: string[] }[];
  interpretation_limits: string[];
}
interface PopulationCoverage {
  population_id: string;
  scope_id: string;
  alignment_key: Observation<'dataset_source_records.id'>;
  complete: Observation<boolean>;
  per_selection: { selection_id: string;
    expected_unique: Observation<number>; retrieved_rows: Observation<number>;
    retrieved_unique: Observation<number>; original_unique: Observation<number>;
    exclusive_count: Observation<number>; missing_count: Observation<number>;
    duplicate_count: Observation<number>; label_conflict_count: Observation<number>;
    numerator: Observation<number>; denominator: Observation<number>;
    ratio: Observation<number>; evidence_ids: string[] }[];
  intersection_unique: Observation<number>;
  identity_references: string[]; // identidades completas recuperables, no solo conteos
  subset_rule: string | null;
  exclusions: Finding[];
}
interface CheckpointCheck {
  selection_id: string;
  artifact_id: UUID;
  lineage: Observation<boolean>;
  availability: 'not_checked' | 'available' | 'missing' | 'verification_error';
  integrity: 'not_checked' | 'verified' | 'mismatch' | 'unverifiable' | 'verification_error';
  checked_at: DateTime | null;
  evidence_ids: string[];
  error_ids: string[];
}
interface TechnicalError {
  error_id: string;
  state: 'ERROR_DE_CONSULTA';
  code: string; message: string; operation: string;
  scope_ids: string[]; selection_ids: string[];
  http_status: number | null;
  correlation_id: string;
  retryable: boolean;
}
interface PreflightResponse {
  contract_version: 'scc_pre_1';
  generated_at: DateTime;
  correlation_id: string;
  consistency: { mode: 'repeatable_read' | 'partial';
    started_at: DateTime; completed_at: DateTime; limitations: string[] };
  selections: Selection[];
  dimensions: DimensionResult[];
  analyses: AnalysisResult[];
  evidence: EvidenceRef[];
  populations: PopulationCoverage[];
  checkpoints: CheckpointCheck[];
  technical_errors: TechnicalError[];
  summary: { by_state: Record<ScientificState, number>;
    not_evaluated: number; analysis_count: number;
    warning_reason_ids: string[]; technical_error_ids: string[] };
}
```

Semántica y validaciones:

- Todos los campos declarados son obligatorios; ausencia se expresa mediante Observation, no omisión ni defaults científicos. `known:false`, cero, unknown y not_applicable son distintos. Arrays vacíos solo indican colección consultada sin elementos o alcance sin elementos, nunca un error oculto. Una entrada EvidenceRef.value query_error conserva el error, sin fabricar valor.
- UUID pertenecen a namespaces explícitos: TRAIN, identity, attempt, evaluations, artifact y dataset_source_record no son intercambiables. La petición debe fijar TRAIN y selecciones exactas por fuente; el servidor resuelve y contrasta split/checkpoint/parentesco. Si no se seleccionó evaluación, Observation unknown con motivo permite mostrar curvas, sin elegir una automáticamente. Selecciones contradictorias producen hallazgos verificables; UUID mal formado es 422.
- No hay estado global. Cada dimensión puede repetirse por scope_id para conservar condiciones distintas. Cada análisis tiene un analysis_id único; si necesita dos alcances, se desglosa en dos entradas, sin precedencia artificial entre incompatibilidad e insuficiencia. Un subconjunto no representa la selección completa; siempre se conserva el dictamen del alcance solicitado y sus exclusiones.
- Error técnico que impide dictamen → not_evaluated/null con error_ids, nunca EVIDENCIA_INSUFICIENTE por sustitución. Si quedan pruebas suficientes para un dictamen, puede coexistir evaluated con errores de consultas auxiliares y hallazgos independientes. El resumen cuenta cada analysis_id una vez; suma by_state + not_evaluated = analysis_count.
- Coverage no transporta predicciones masivas: referencias de evidencia permiten recuperar todas las claves con paginación estable. B.2 puede determinar conjuntos/conteos de cobertura según P4; no recalcula métricas de desempeño sobre la intersección. El análisis de métricas originales conserva population=original.
- CheckpointCheck separa linaje/bytes; ausencia física no altera automáticamente el estado de métricas. `checked_at=null` cuando not_checked. mismatch exige comparación efectiva de contenido. Hash ausente → unverifiable, no mismatch.
- Evidencia pública sin rutas locales, comandos ni errores SQL crudos; reutilizar public_evidence y envelope/correlation_id actuales. Motivos estables más mensaje legible, identidades y campo consultado permiten revisión verificable. El reporte no certifica lo no consultado.

## 6. Diseño mínimo recomendado para SCC-PRE.1B.2

1. **Endpoint nuevo y acotado:** `POST /models/comparison/preflight`, consulta sin persistencia. El cuerpo permite pares TRAIN/selección y análisis/alcances sin query strings ambiguos. No ampliar `/models/comparison`, que tiene semántica de resumen distinta; tampoco alterar el contrato single-TRAIN de scientific-results. Límite de TRAIN según `scc_max_comparison_runs` existente. POST no autoriza ejecución ni escritura.
2. **Servicio:** `ScientificPreflightService` propuesto, orquestador de evidencia y reglas SCC-PRE.1A, sin SQL en ruta ni frontend. No llamar a ejecución, E7.compare, prepare/verify de E6, publicadores ni regeneradores de artefactos.
3. **Reutilización:** ScientificReadRepository/read_scientific_results, AssessmentReadRepository, ArtifactReadRepository, consultas de dataset gobernado y sample_repository. Proyectar campos necesarios sin hacer que una lectura de configuración cargue toda la evidencia XAI/predicciones. Mantener cada decisión SQL en su dominio; adaptar el lector canónico, no copiar consultas en un catálogo nuevo.
4. **Extensiones mínimas:** conexión externa opcional para lecturas compartidas; selección de evaluations.id con validación TRAIN y source_assessment_attempt_id; conteos/páginas por intento y fuente exacta con orden total; recuperación de calibración por vínculo de evaluación y configuración XAI por method_configuration_id. Solo si faltan datos en snapshots públicos, proyección consultiva de train_execution_records/sessions. Agregar comprobación opcional de bytes del checkpoint únicamente si un análisis la necesita; por defecto not_checked.
5. **Selección:** aceptar fuente discriminada assessment/evaluations, sin defaults de intento. Verificar TRAIN, identity, checkpoint, split y población; conservar intentos fallidos/interrumpidos/activos como evidencia parcial con estado original. No mezclar páginas ni métricas de distintos intentos ni elegir por desempeño.
6. **Consistencia y fallos:** transacción READ ONLY + REPEATABLE READ y timeout para las consultas del reporte, con savepoints por dominio. Consultas parametrizadas y solo para IDs seleccionados. Si se usa lectura parcial o se alcanza un límite, registrar complete=false/unknown y limitación; nunca declarar población completa por truncamiento. Fallos de autorización no revelan datos de ese dominio y se transportan separados cuando el reporte pueda continuar; autenticación general fallida mantiene 401.
7. **Permisos:** exigir RUNS_READ y MODELS_READ para el reporte; comprobar DATASETS_READ, PREDICTIONS_READ y ARTIFACTS_READ al acceder a esos dominios. Reutilizar require_permission/Principal sin inferir permisos por la actual falta de guard en R/A. No proponer aquí una refactorización global de seguridad. No usar wrappers de ejecución que persistan evidencia de auditoría científica.
8. **Solo lectura comprobable:** SQL read-only a nivel PostgreSQL, ninguna llamada a loaders Keras, runtime, dispatch, subprocess, scheduler, escritura de resultados o generación. Las referencias a archivos son consulta gobernada y no reconstrucción. La respuesta se calcula en memoria sin nuevas tablas/migraciones.

## 7. Validación futura y decisiones que condicionan B.2

Pruebas necesarias, sin ejecutar campañas ni procesos científicos:

- Contrato: múltiples análisis con estados mixtos, error técnico con scientific_state=null, conteo único del resumen, exclusiones/subconjuntos y sanitización; ausencia distinta de false/0/N/A.
- Identidad: dos evaluaciones y dos intentos del mismo TRAIN, selección de uno antiguo explícito, vínculo histórico source_assessment_attempt_id, checkpoint de otro TRAIN, EXPLAIN sin padre; ninguna selección latest.
- Población: más de una página, timestamps empatados, intento activo con inserciones, terminal inmutable, duplicados entre fuentes, conflicto de etiquetas, intersección vacía/parcial y denominador cero/desconocido; no recalcular métricas sobre intersección.
- A4/A6: configuración faltante sin defaults, diferencias permitidas de arquitectura/semilla, umbrales y definiciones distintos; configuración declarada sin resultados observados.
- A5/XAI: métricas trazables con checkpoint ausente, hash mismatch, storage inaccesible, not_checked; SHAP sin background, capa/clase ausentes, método configurado distinto; artefacto existente sin contrato de representación.
- Integración en base de pruebas aislada: READ ONLY rechaza DML, snapshot consistente entre dominios, error SQL recuperable mediante savepoint, timeout y caída de conexión; confirmar PK/guards que sostienen estabilidad. Probar 401/403, UUID inválido y límites. Ninguna prueba contra resultados científicos reales con mutaciones.
- Regresión focalizada: suites existentes `backend_api/tests/test_scc_core.py`, `test_scc_art.py`, `test_scientific_results_v2.py` y `malaria_dl_local_project/tests/test_assessment_api_e6.py`, después de revisar fixtures y ejecutar solo con entorno de prueba apropiado. Los tests con mocks acreditan contrato, no despliegue operativo.

Decisiones pendientes para revisión técnica:

| Decisión | Recomendación / efecto |
|---|---|
| Alcances y preguntas iniciales | Definir analysis_id y condiciones por módulo; no inventar comparación controlada ni equivalencia de protocolos. Sin ello no puede emitirse un dictamen justificado |
| Fuentes de evaluación soportadas en primera entrega | E6 tiene selección exacta lista; soportar también evaluations requiere el lector por id descrito. Históricos sin correspondencia quedan individuales/insuficientes, sin alineación ficticia |
| Garantía de consistencia y volumen | Aprobar snapshot compartido y paginación/completitud; verificar operativamente guards de terminales. Evitar respuestas ilimitadas de samples y truncamientos silenciosos |
| Permisos del nuevo orquestador | Aplicar permisos por dominio y probarlos; llamadas internas no heredan automáticamente guards HTTP |
| Verificación física | Mantener not_checked por defecto; comprobar bytes solo con alcance explícito y mecanismo gobernado. No condicionar métricas a archivo accesible |

La cobertura real por TRAIN y la presencia de representaciones permanecen pendientes de consultas controladas durante B.2; esa incertidumbre debe representarse en el contrato y no obliga a generar datos. El diseño puede implementarse conservando los estados mixtos de SCC-PRE.1A y reutilizando el acceso distribuido existente.
