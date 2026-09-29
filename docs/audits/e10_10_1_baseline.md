# E10.10.1 — Baseline e integridad de PostgreSQL

**E10.10.1 — BASELINE VERIFICADO.** Fotografía de la base operativa; observaciones y riesgos abiertos abajo. Se detiene antes de E10.10.2.

Captura UTC: `2026-09-29T02:34:49.403485+00:00`; fin: `2026-09-29 02:34:52.660779+00:00`. En America/Santiago corresponde al 28-09-2026. Commit: `c63a9509f7eb8a4f02b8a1e808cafcb9c8d5efaa`.

## Alcance y reproducción

Se leyó íntegramente `revision-bd-malaria.md` y se contrastó con catálogos y datos operativos. Se usó una única transacción **REPEATABLE READ, READ ONLY**, finalizada con ROLLBACK, para la captura final. Hubo consultas preliminares también de lectura. No se ejecutaron DDL, DML, ANALYZE, VACUUM, resets estadísticos, migraciones, TRAIN ni TEST clínico. No se recalculó el split ni se crearon datos.

El [JSON adjunto](e10_10_1_baseline.json) contiene el inventario completo con definiciones, columnas, estado de índices/triggers/restricciones, conteos exactos, tamaños en bytes, estadísticas, todas las consultas y el script ejecutable (`collection_script`). No contiene contraseñas ni hashes de contraseñas individuales; las tablas protegidas se comparan mediante huellas agregadas. Las funciones se inventariaron, no se ejecutaron sus operaciones de negocio.

Para reproducir la captura de lectura, desde el repositorio con Docker activo:

```bash
python - <<'PY'
import json
from pathlib import Path
b = json.loads(Path("docs/audits/e10_10_1_baseline.json").read_text())
Path("/tmp/e10_baseline.py").write_text(b["collection_script"])
PY
docker exec -i capstone_backend python < /tmp/e10_baseline.py > /tmp/e10_baseline_raw.json
```

El resultado reproducido es la captura cruda; la comparación con evidencia previa está en `protected_comparison` y `reconstruction_differences`. `evidence_files` registra SHA-256 de las fuentes locales. Las estadísticas y tamaños no son una instantánea MVCC estricta y pueden evolucionar por actividad/autovacuum; los datos y catálogos sí comparten snapshot. Las consultas de esta auditoría afectan contadores de lectura, aunque no modifican datos de aplicación.

## Identidad y migraciones

| Dato | Valor |
| --- | --- |
| Contenedor / servicio / proyecto | capstone_db / db / capstone-malaria |
| ID contenedor | 2604ff9884655b3b78ffc85997cbe30d6392afca7b904b5df2b37dacedb30d89 |
| Imagen | postgres:17.9 |
| ID imagen | sha256:2a0d0fe14825b0939f78a8cad5cd4e6aa68bf94d0e5dd96e24b6d23af4315545 |
| Volumen | capstone-malaria_postgres_data → /var/lib/postgresql/data |
| Conexión backend | db:5432/malaria_experiments → 172.19.0.3:5432 |
| Cluster system_identifier | 7668020338728398886 |
| OID base / esquema | 1600436 / public |
| Servidor | PostgreSQL 17.9 (Debian 17.9-1.pgdg13+1) on aarch64-unknown-linux-gnu, compiled by gcc (Debian 14.2.0-19) 14.2.0, 64-bit |
| Alembic vigente / head | 20260922_01 / 20260922_01 |
| Ledger ML | 22 registros en schema_migrations |
| Transacción / snapshot | on / repeatable read / 127880:127880: |
| Extensiones | pgcrypto 1.3; plpgsql 1.0 (lenguaje predeterminado) |

La IP observada coincide con el contenedor inspeccionado. El OID 1600436 coincide con la candidata promovida en `cutover.json`; el origen OID 16384 permanece como `malaria_pre_reset3_20260929`, sin conexiones permitidas. No se consultó su contenido.

## Comparación con la auditoría obligatoria

| Objeto o hipótesis | Auditoría anterior | Actual / conclusión |
| --- | --- | --- |
| Tablas | 97 | 97; todas con PK |
| Índices | 228; 38 únicos; 222 btree / 6 GIN | 389 físicos = 97 PK + 64 UNIQUE de restricciones + 228 independientes (38 únicos; 222 btree / 6 GIN). El total anterior corresponde a independientes. |
| FK / CHECK | 208 / 416 | 208 / 416; todos validados y sin infracciones actuales |
| Triggers | 77 | 77 de aplicación + 832 internos; todos habilitados. No todos los 77 son de inmutabilidad. |
| Funciones | 65 | 65 propias + 36 de pgcrypto = 101; se conservan sobrecargas en el JSON |
| Vistas | 26 / llamadas vw_* | 27 = 25 vw_* + inference_runs + legacy_cell_predictions. No se puede atribuir una vista agregada sin inventario nominal del dump. |
| JSONB | 223 en 72 tablas | 130 en 72 tablas; 169 incluyendo columnas de vistas. Cifra anterior no reproducida; no implica eliminación comprobada. |
| runs | 56 columnas; 26 text; 10 JSONB | 56 columnas; 26 text; 5 JSONB. Discrepancia anterior. |
| Extensiones | Sólo pgcrypto | pgcrypto y plpgsql incorporado; pgcrypto sigue siendo la única adicional. |
| FK sin índice primera columna | 79, de ellas 60 RESTRICT | Confirmado con el criterio anterior. 109 sin prefijo completo ordenado válido/no parcial: criterio más conservador, no lista automática de índices a crear. |
| ON DELETE | 154 RESTRICT / 25 NO ACTION / 20 CASCADE / 9 SET NULL | Coincide. NO ACTION no implica que las 25 sean diferibles ni que fueran omisiones; ver condeferrable en JSON. |
| Seis tablas sin referencias | Supuestamente abandonadas | Refutado: migraciones 20260914_01, 20260914_02, 20260915_01 y malaria_dl_local_project/src/malaria_dl/execution/repository.py las usan. Gate contiene 1 fila técnica. |
| Cuatro índices redundantes | Candidatos a eliminar | Los cuatro pares existen; prefijo común no prueba redundancia económica ni autoriza borrado. |
| Dos dominios / ledgers | ML y clínico en public | Confirmado: predictions, cell_predictions, legacy_cell_predictions y ambos ledgers. No se concluye que coexistir pruebe fallos. |
| Vistas sin uso | Consulta basada en pg_stat_statements | Extensión no instalada; no se puede verificar uso. Buscar nombres textuales tampoco probaría ausencia de dependencias indirectas. |
| Dependencias / 34 errores CI | Afirmación externa al esquema | No se ejecutó CI ni se comprobó su estado actual; no se conserva como hallazgo operativo probado. |

La ausencia de índice JSONB no es por sí sola un defecto. Se mantienen 6 GIN; los snapshots siguen presentes. El tamaño de un dump comprimido (111 MB en la auditoría) no es comparable con tamaño físico actual de relaciones.

## Integridad científica y autenticación

El UUID solicitado identifica **dataset_versions**, no la PK de `datasets`. La versión `Malaria Patient Split v1` está FROZEN, con semilla 42 y agrupación por paciente.

| Partición | Asignaciones | Parasitized | Uninfected | Pacientes únicos |
| --- | --- | --- | --- | --- |
| TRAIN | 22180 | 11137 | 11043 | 161 |
| VALIDATION (val) | 2693 | 1325 | 1368 | 20 |
| TEST | 2685 | 1317 | 1368 | 20 |
| Total | 27558 | 13779 | 13779 | 201 |

Comprobaciones nuevas por SELECT: 0 pacientes en más de una partición; 0 registros asignados más de una vez; 0 fuentes sin asignación; 0 discrepancias entre identidad/clase de asignación y fuente; 0 evidencias con identidad discordante; 0 hashes de archivo o píxeles compartidos entre particiones. Las 201 identidades PATIENT y 27.558 fuentes están VERIFIED; no faltan hashes ni identidades de fuente. Las 12 validaciones almacenadas están PASS, y se distinguen de las comprobaciones nuevas anteriores.

Materialización `e15dc166-1c4b-558e-b77b-727b1783430c`: READY/PASS, 27.558 registros. Sus conteos almacenados coinciden con las asignaciones. Los contratos congelados y las filas científicas coinciden por SHA-256 con la evidencia de reconstrucción y limpieza. No se reabrieron los archivos de imágenes: READY/PASS y reconciliación física son evidencia histórica almacenada.

`dataset_split_images` conserva dos registros de inventario de 27.558 imágenes cada uno: la raíz oficial reproduce 22.180/2.693/2.685; la raíz antigua `malaria_physical_split` tiene 22.046/2.756/2.756. Las 55.116 filas tienen FK de versión y materialización NULL; no son huérfanos según las FK opcionales, pero sí una ambigüedad de linaje para consumidores que no filtren la raíz. `dataset_materialization_activations` y `dataset_splits` están vacías. La fuente de verdad del split verificado es `dataset_split_assignments`.

Autenticación: 1 usuario activo con hash no vacío, 5 roles y 1 asociación administrator. Ningún usuario sin rol ni asociaciones huérfanas. Se verifica integridad SQL, no un login nuevo ni la validez criptográfica de la contraseña.

Las 208 FK se comprobaron por anti-join y los 416 CHECK con `IS FALSE` (NULL conserva semántica SQL). Todas las FK son MATCH SIMPLE; el algoritmo omite correctamente claves con NULL. 0 restricciones no validadas, 0 índices inválidos/no listos y 0 triggers deshabilitados. Las PK y UNIQUE están inventariadas y respaldadas por índices válidos; no se ejercitaron triggers mediante escrituras.

## Estado experimental y reconstrucción

Las 77 tablas de la política histórica están inventariadas: 76 vacías y `audit_events` con 1 fila `USER_LOGIN_SUCCEEDED`, de 2026-09-29 00:37:56 UTC. Es autenticación posterior a la reconstrucción, no historial experimental. No hay runs, campañas, intentos, sesiones TRAIN, evaluaciones, predicciones, análisis clínicos, artefactos ni publicaciones. El gate conserva una única fila con owner/db_pid/blocked_reason NULL y process_evidence vacío. Por tanto, estado experimental limpio; la condición literal “todas las tablas HISTORY_TABLES a cero” es falsa y no se oculta.

Diferencias acreditadas por evidencia local anterior/posterior:

- Cambio de OID canónico 16384 → 1600436; sólo queda public en la base operativa. Los 9 schemas de pruebas del origen no están presentes.
- El catálogo previo a reconstrucción tenía 786 restricciones, 908 triggers y 100 funciones. El actual tiene 787, 909 y 101. Aparecen `train_event_metadata`, `train_event_guard` y el trigger `a_train_event_guard` de `train_execution_records`; la reconstrucción restauró objetos de la revisión vigente. Esto es comparación con `source_before.json`, distinta del dump de la auditoría obligatoria.
- Cuatro CHECK cambian la representación de casts de arrays (casts por elemento en vez del array completo); no se observa cambio de valores permitidos. Ambas definiciones quedan en el JSON.
- 15/17 tablas protegidas coinciden íntegramente con la evidencia anterior a reconstrucción. `models` pasó de 4 a 3 filas; el motivo y la identidad de la fila retirada no se deducen de hashes agregados. `users` cambió; last_login_at coincide temporalmente con el login registrado, sin probar que sea el único cambio de campo.
- 16/17 tablas coinciden con la verificación inmediata posterior a reconstrucción (sólo difiere users); **17/17 coinciden con la evidencia posterior a limpieza de almacenamiento**. No se presenta esto como preservación completa frente al origen.

## Tamaños y estadísticas del optimizador

Base completa: **173,143,731 bytes**. Relaciones de usuario: **161,693,696 bytes**, de los cuales **120,037,376** son tablas/TOAST y **41,656,320** índices propios. La diferencia con el tamaño de base incluye catálogos y otros objetos. Índices TOAST forman parte de pg_table_size, no se suman otra vez.

Hay estadísticas de columna para 70 columnas. Autoanalyze alcanzó las cinco tablas principales con población (clinical_identities, dataset_source_records, dataset_split_assignments, dataset_split_images e identity_evidence) alrededor de 00:22 UTC. Las tablas pequeñas carecen de last_analyze/last_autoanalyze; `audit_events` tiene reltuples=-1 pese a 1 fila real. `stats_reset` es NULL: no se inventa una fecha de reset; el reinicio del servidor fue 2026-09-08 y la reconstrucción posterior. No hay carga representativa para recomendar podar índices.

El JSON incluye todas las métricas de pg_stat_user_tables, pg_stat_user_indexes, pg_stat_database, pg_stats sin valores sensibles y parámetros del optimizador. No se ejecutó ANALYZE para no alterar el baseline. Los conteos siguientes son exactos, no n_live_tup.

## Inventario de tablas, filas y tamaños

| Tabla | Clase | Filas | Tabla/TOAST bytes | Índices bytes | Total bytes |
| --- | --- | --- | --- | --- | --- |
| alembic_version | técnica | 1 | 8192 | 16384 | 24576 |
| artifacts | histórica | 0 | 8192 | 73728 | 81920 |
| assessment_artifacts | histórica | 0 | 8192 | 16384 | 24576 |
| assessment_attempts | histórica | 0 | 8192 | 40960 | 49152 |
| assessment_campaign_consumers | histórica | 0 | 0 | 8192 | 8192 |
| assessment_final_locks | histórica | 0 | 8192 | 16384 | 24576 |
| assessment_identities | histórica | 0 | 8192 | 24576 | 32768 |
| assessment_results | histórica | 0 | 8192 | 8192 | 16384 |
| audit_events | histórica | 1 | 16384 | 65536 | 81920 |
| blood_samples | histórica | 0 | 8192 | 40960 | 49152 |
| campaign_attempts | histórica | 0 | 8192 | 49152 | 57344 |
| campaign_configurations | histórica | 0 | 8192 | 8192 | 16384 |
| campaign_controlled_requests | histórica | 0 | 8192 | 32768 | 40960 |
| campaign_execution_events | histórica | 0 | 8192 | 8192 | 16384 |
| campaign_members | histórica | 0 | 8192 | 32768 | 40960 |
| campaign_technical_revisions | histórica | 0 | 8192 | 16384 | 24576 |
| cell_classification_events | histórica | 0 | 8192 | 32768 | 40960 |
| cell_classification_inputs | histórica | 0 | 0 | 73728 | 73728 |
| cell_classification_reviews | histórica | 0 | 8192 | 24576 | 32768 |
| cell_classification_runs | histórica | 0 | 8192 | 73728 | 81920 |
| cell_crops | histórica | 0 | 8192 | 32768 | 40960 |
| cell_detection_events | histórica | 0 | 8192 | 24576 | 32768 |
| cell_detection_runs | histórica | 0 | 8192 | 49152 | 57344 |
| cell_detections | histórica | 0 | 0 | 49152 | 49152 |
| cell_explanations | histórica | 0 | 8192 | 24576 | 32768 |
| cell_predictions | histórica | 0 | 8192 | 65536 | 73728 |
| classification_reports | histórica | 0 | 8192 | 16384 | 24576 |
| clinical_identities | protegida | 201 | 40960 | 49152 | 90112 |
| confusion_matrices | histórica | 0 | 8192 | 16384 | 24576 |
| dataset_materialization_activations | protegida | 0 | 8192 | 32768 | 40960 |
| dataset_materializations | protegida | 1 | 16384 | 49152 | 65536 |
| dataset_source_records | protegida | 27558 | 16293888 | 10420224 | 26714112 |
| dataset_split_assignments | protegida | 27558 | 9347072 | 2719744 | 12066816 |
| dataset_split_images | protegida | 55116 | 72474624 | 23216128 | 95690752 |
| dataset_split_statistics | protegida | 1 | 16384 | 32768 | 49152 |
| dataset_split_validation_checks | protegida | 12 | 16384 | 32768 | 49152 |
| dataset_splits | protegida | 0 | 8192 | 8192 | 16384 |
| dataset_version_sources | protegida | 1 | 16384 | 32768 | 49152 |
| dataset_versions | protegida | 1 | 32768 | 49152 | 81920 |
| datasets | protegida | 2 | 16384 | 32768 | 49152 |
| deployed_model_versions | histórica | 0 | 8192 | 73728 | 81920 |
| environment_packages | histórica | 0 | 8192 | 16384 | 24576 |
| errors | histórica | 0 | 8192 | 16384 | 24576 |
| execution_logs | histórica | 0 | 8192 | 16384 | 24576 |
| experiment_execution_events | histórica | 0 | 8192 | 8192 | 16384 |
| experiment_execution_gate | técnica | 1 | 16384 | 16384 | 32768 |
| experimental_campaigns | histórica | 0 | 8192 | 16384 | 24576 |
| experiments | histórica | 0 | 8192 | 8192 | 16384 |
| explainability_results | histórica | 0 | 8192 | 49152 | 57344 |
| identity_evidence | protegida | 27558 | 21078016 | 1990656 | 23068672 |
| image_analysis_jobs | histórica | 0 | 8192 | 73728 | 81920 |
| image_connected_components | histórica | 0 | 8192 | 40960 | 49152 |
| image_ingestion_batches | histórica | 0 | 8192 | 24576 | 32768 |
| image_quality_assessments | histórica | 0 | 8192 | 16384 | 24576 |
| local_execution_jobs | histórica | 0 | 8192 | 32768 | 40960 |
| microscopy_analysis_events | histórica | 0 | 8192 | 16384 | 24576 |
| microscopy_analysis_run_images | histórica | 0 | 0 | 32768 | 32768 |
| microscopy_analysis_runs | histórica | 0 | 8192 | 40960 | 49152 |
| microscopy_images | histórica | 0 | 8192 | 65536 | 73728 |
| model_governance_backfill_audit | histórica | 0 | 8192 | 32768 | 40960 |
| model_versions | histórica | 0 | 8192 | 98304 | 106496 |
| models | protegida | 3 | 16384 | 16384 | 32768 |
| predictions | histórica | 0 | 8192 | 139264 | 147456 |
| quality_assessment_queue_items | histórica | 0 | 8192 | 32768 | 40960 |
| quality_gate_decisions | histórica | 0 | 8192 | 16384 | 24576 |
| research_subjects | histórica | 0 | 8192 | 32768 | 40960 |
| roles | protegida | 5 | 16384 | 32768 | 49152 |
| run_checkpoint_policy | histórica | 0 | 8192 | 32768 | 40960 |
| run_clinical_metrics | histórica | 0 | 8192 | 32768 | 40960 |
| run_dataset_images | histórica | 0 | 8192 | 49152 | 57344 |
| run_image_predictions | histórica | 0 | 8192 | 32768 | 40960 |
| run_io_records | histórica | 0 | 8192 | 98304 | 106496 |
| run_lineage | histórica | 0 | 8192 | 73728 | 81920 |
| run_metrics | histórica | 0 | 8192 | 24576 | 32768 |
| run_model_deployments | histórica | 0 | 8192 | 49152 | 57344 |
| run_threshold_calibration | histórica | 0 | 8192 | 40960 | 49152 |
| runs | histórica | 0 | 8192 | 139264 | 147456 |
| schema_migrations | técnica | 22 | 16384 | 16384 | 32768 |
| scientific_cases | histórica | 0 | 8192 | 32768 | 40960 |
| scientific_reviews | histórica | 0 | 8192 | 24576 | 32768 |
| scientific_validation_annotation_events | histórica | 0 | 8192 | 32768 | 40960 |
| scientific_validation_annotations | histórica | 0 | 8192 | 57344 | 65536 |
| scientific_validation_classification_runs | histórica | 0 | 0 | 8192 | 8192 |
| scientific_validation_detection_runs | histórica | 0 | 0 | 8192 | 8192 |
| scientific_validation_images | histórica | 0 | 0 | 16384 | 16384 |
| scientific_validation_sessions | histórica | 0 | 8192 | 24576 | 32768 |
| smear_analysis_summaries | histórica | 0 | 8192 | 40960 | 49152 |
| smear_slides | histórica | 0 | 8192 | 32768 | 40960 |
| stage2_model_publication_events | histórica | 0 | 8192 | 16384 | 24576 |
| stage2_model_publications | histórica | 0 | 8192 | 32768 | 40960 |
| synthetic_data_runs | histórica | 0 | 8192 | 8192 | 16384 |
| train_execution_records | histórica | 0 | 8192 | 24576 | 32768 |
| train_execution_revisions | histórica | 0 | 0 | 8192 | 8192 |
| train_execution_sessions | histórica | 0 | 8192 | 32768 | 40960 |
| training_history | histórica | 0 | 8192 | 24576 | 32768 |
| user_roles | protegida | 1 | 8192 | 16384 | 24576 |
| users | protegida | 1 | 16384 | 49152 | 65536 |

## Inventario nominal completo de objetos

Las definiciones SQL completas, columnas, PK, FK, UNIQUE, CHECK y restricciones de trigger están en el JSON. Este índice nominal permite ubicar todos los objetos sin repetir cuerpos SQL extensos.

### Vistas

| Nombre | Tipo |
| --- | --- |
| inference_runs | v |
| legacy_cell_predictions | v |
| vw_case_level_explainability | v |
| vw_case_type_summary | v |
| vw_checkpoint_policy_summary | v |
| vw_clinical_inference_predictions | v |
| vw_clinical_run_summary | v |
| vw_dataset_browser_images | v |
| vw_dataset_browser_summary | v |
| vw_dataset_split_images_summary | v |
| vw_evaluation_lineage | v |
| vw_explainability_gallery | v |
| vw_explainability_lineage | v |
| vw_explainability_summary | v |
| vw_false_negative_cases | v |
| vw_false_positive_cases | v |
| vw_low_confidence_cases | v |
| vw_model_run_summary | v |
| vw_run_artifacts_summary | v |
| vw_run_dashboard | v |
| vw_run_dataset_usage_summary | v |
| vw_run_image_predictions_summary | v |
| vw_run_io_summary | v |
| vw_run_lineage | v |
| vw_threshold_calibration_summary | v |
| vw_uploaded_predictions | v |
| vw_visual_explainability_audit | v |

### Funciones y procedimientos

| Nombre y firma | Origen |
| --- | --- |
| armor(bytea) | extensión |
| armor(bytea, text[], text[]) | extensión |
| assessment_attempt_guard() | aplicación |
| assessment_canonical(v jsonb) | aplicación |
| assessment_consumer_guard() | aplicación |
| assessment_identity_guard() | aplicación |
| assessment_immutable() | aplicación |
| assessment_result_guard() | aplicación |
| assessment_structural_hash(v jsonb) | aplicación |
| campaign_attempt_guard() | aplicación |
| campaign_attempt_state() | aplicación |
| campaign_audit() | aplicación |
| campaign_catalog_identity_guard() | aplicación |
| campaign_configuration_guard() | aplicación |
| campaign_configuration_valid(v jsonb) | aplicación |
| campaign_contract_valid(v jsonb) | aplicación |
| campaign_environment_identity(v jsonb) | aplicación |
| campaign_guard() | aplicación |
| campaign_json_integer(v jsonb, minimum_value numeric) | aplicación |
| campaign_json_object(v jsonb, required_keys text[]) | aplicación |
| campaign_json_string(v jsonb) | aplicación |
| campaign_member_guard() | aplicación |
| campaign_model_matches(run_id uuid, member uuid) | aplicación |
| campaign_run_identity_guard() | aplicación |
| campaign_technical_guard() | aplicación |
| controlled_binding_guard() | aplicación |
| controlled_pause_guard() | aplicación |
| controlled_run_guard() | aplicación |
| crypt(text, text) | extensión |
| dearmor(text) | extensión |
| decrypt(bytea, bytea, text) | extensión |
| decrypt_iv(bytea, bytea, bytea, text) | extensión |
| digest(bytea, text) | extensión |
| digest(text, text) | extensión |
| encrypt(bytea, bytea, text) | extensión |
| encrypt_iv(bytea, bytea, bytea, text) | extensión |
| enforce_activation_materialization_consistency() | aplicación |
| enforce_dataset_assignment_consistency() | aplicación |
| enforce_dataset_version_lifecycle() | aplicación |
| enforce_model_version_governance() | aplicación |
| enforce_run_lineage_governance() | aplicación |
| execution_event_immutable() | aplicación |
| experiment_require_owner() | aplicación |
| experiment_reservation_guard() | aplicación |
| gen_random_bytes(integer) | extensión |
| gen_random_uuid() | extensión |
| gen_salt(text) | extensión |
| gen_salt(text, integer) | extensión |
| hmac(bytea, bytea, text) | extensión |
| hmac(text, text, text) | extensión |
| pgp_armor_headers(text, OUT key text, OUT value text) | extensión |
| pgp_key_id(bytea) | extensión |
| pgp_pub_decrypt(bytea, bytea) | extensión |
| pgp_pub_decrypt(bytea, bytea, text) | extensión |
| pgp_pub_decrypt(bytea, bytea, text, text) | extensión |
| pgp_pub_decrypt_bytea(bytea, bytea) | extensión |
| pgp_pub_decrypt_bytea(bytea, bytea, text) | extensión |
| pgp_pub_decrypt_bytea(bytea, bytea, text, text) | extensión |
| pgp_pub_encrypt(text, bytea) | extensión |
| pgp_pub_encrypt(text, bytea, text) | extensión |
| pgp_pub_encrypt_bytea(bytea, bytea) | extensión |
| pgp_pub_encrypt_bytea(bytea, bytea, text) | extensión |
| pgp_sym_decrypt(bytea, text) | extensión |
| pgp_sym_decrypt(bytea, text, text) | extensión |
| pgp_sym_decrypt_bytea(bytea, text) | extensión |
| pgp_sym_decrypt_bytea(bytea, text, text) | extensión |
| pgp_sym_encrypt(text, text) | extensión |
| pgp_sym_encrypt(text, text, text) | extensión |
| pgp_sym_encrypt_bytea(bytea, text) | extensión |
| pgp_sym_encrypt_bytea(bytea, text, text) | extensión |
| prevent_audit_event_mutation() | aplicación |
| prevent_model_governance_audit_mutation() | aplicación |
| prevent_stage2_publication_event_mutation() | aplicación |
| prevent_validation_annotation_event_mutation() | aplicación |
| prevent_validation_membership_mutation() | aplicación |
| protect_cell_classification_run() | aplicación |
| protect_cell_detection_run_identity() | aplicación |
| protect_cell_explanation() | aplicación |
| protect_deployed_model_version_payload() | aplicación |
| protect_frozen_dataset_assignment_updates() | aplicación |
| protect_frozen_dataset_assignments() | aplicación |
| protect_frozen_dataset_version_sources() | aplicación |
| protect_governed_artifact_identity() | aplicación |
| protect_validation_annotation() | aplicación |
| protect_validation_snapshot() | aplicación |
| reject_cell_analysis_row_mutation() | aplicación |
| reject_cell_classification_row_mutation() | aplicación |
| train_event_guard() | aplicación |
| train_record_guard() | aplicación |
| train_revision_binding_guard() | aplicación |
| train_session_guard() | aplicación |
| validate_cell_classification_input_snapshot() | aplicación |
| validate_cell_classification_insert_state() | aplicación |
| validate_cell_classification_review() | aplicación |
| validate_cell_classification_run_snapshot() | aplicación |
| validate_cell_explanation_contract() | aplicación |
| validate_cell_prediction_input() | aplicación |
| validate_deployed_model_version() | aplicación |
| validate_image_analysis_job() | aplicación |
| validate_run_model_deployment() | aplicación |
| validate_smear_analysis_summary() | aplicación |

### Índices y restricciones por tabla

#### alembic_version

Índices: `alembic_version_pkc`.

PK: `alembic_version_pkc`.

#### artifacts

Índices: `artifacts_pkey`, `idx_artifacts_artifact_type`, `idx_artifacts_checksum`, `idx_artifacts_governance_status`, `idx_artifacts_metadata_source`, `idx_artifacts_run_id`, `idx_artifacts_type_path`, `idx_artifacts_uri`, `uq_artifacts_id_run_id`.

PK: `artifacts_pkey`.

FK: `artifacts_run_id_fkey`.

CHECK: `chk_artifacts_governance_status`.

Triggers de aplicación: `trg_artifacts_protect_governed_identity`.

#### assessment_artifacts

Índices: `assessment_artifacts_artifact_id_key`, `assessment_artifacts_pkey`.

PK: `assessment_artifacts_pkey`.

FK: `assessment_artifacts_attempt_id_fkey`.

UNIQUE: `assessment_artifacts_artifact_id_key`.

CHECK: `assessment_artifacts_payload_check`, `assessment_artifacts_payload_check1`, `assessment_artifacts_payload_check2`, `assessment_artifacts_payload_check3`.

Triggers de aplicación: `assessment_artifact_guard`.

#### assessment_attempts

Índices: `assessment_attempts_artifact_root_key`, `assessment_attempts_identity_id_ordinal_key`, `assessment_attempts_pkey`, `uq_assessment_live`, `uq_global_assessment_active`.

PK: `assessment_attempts_pkey`.

FK: `assessment_attempts_identity_id_fkey`.

UNIQUE: `assessment_attempts_artifact_root_key`, `assessment_attempts_identity_id_ordinal_key`.

CHECK: `assessment_attempts_check`, `assessment_attempts_ordinal_check`, `assessment_attempts_pid_check`, `assessment_attempts_state_check`.

Triggers de aplicación: `assessment_attempt_guard`, `global_assessment_reservation`.

#### assessment_campaign_consumers

Índices: `assessment_campaign_consumers_pkey`.

PK: `assessment_campaign_consumers_pkey`.

FK: `assessment_campaign_consumers_campaign_id_fkey`, `assessment_campaign_consumers_identity_id_fkey`, `assessment_campaign_consumers_member_id_fkey`.

Triggers de aplicación: `assessment_consumer_guard`, `assessment_consumer_immutable`.

#### assessment_final_locks

Índices: `assessment_final_locks_identity_hash_key`, `assessment_final_locks_pkey`.

PK: `assessment_final_locks_pkey`.

UNIQUE: `assessment_final_locks_identity_hash_key`.

CHECK: `assessment_final_locks_check`, `assessment_final_locks_evidence_check`, `assessment_final_locks_evidence_check1`, `assessment_final_locks_evidence_check2`, `assessment_final_locks_evidence_check3`, `assessment_final_locks_identity_hash_check`.

Triggers de aplicación: `assessment_lock_immutable`.

#### assessment_identities

Índices: `assessment_identities_identity_hash_key`, `assessment_identities_pkey`, `assessment_identities_structural_hash_key`.

PK: `assessment_identities_pkey`.

FK: `assessment_identities_training_run_id_fkey`.

UNIQUE: `assessment_identities_identity_hash_key`, `assessment_identities_structural_hash_key`.

CHECK: `assessment_identities_check`, `assessment_identities_check1`, `assessment_identities_check2`, `assessment_identities_check3`, `assessment_identities_identity_check`, `assessment_identities_identity_check1`, `assessment_identities_identity_check10`, `assessment_identities_identity_check11`, `assessment_identities_identity_check12`, `assessment_identities_identity_check13`, `assessment_identities_identity_check14`, `assessment_identities_identity_check2`, `assessment_identities_identity_check3`, `assessment_identities_identity_check4`, `assessment_identities_identity_check5`, `assessment_identities_identity_check6`, `assessment_identities_identity_check7`, `assessment_identities_identity_check8`, `assessment_identities_identity_check9`, `assessment_identities_identity_hash_check`, `assessment_identities_kind_check`.

Triggers de aplicación: `assessment_identity_guard`, `assessment_identity_immutable`.

#### assessment_results

Índices: `assessment_results_pkey`.

PK: `assessment_results_pkey`.

FK: `assessment_results_attempt_id_fkey`.

CHECK: `assessment_results_check`, `assessment_results_payload_check`.

Triggers de aplicación: `assessment_result_guard`.

#### audit_events

Índices: `audit_events_pkey`, `ix_audit_events_actor`, `ix_audit_events_created_at`, `ix_audit_events_resource`.

PK: `audit_events_pkey`.

FK: `audit_events_actor_user_id_fkey`.

Triggers de aplicación: `audit_events_append_only`.

#### blood_samples

Índices: `blood_samples_pkey`, `ix_blood_samples_case`, `ix_blood_samples_status_created`, `uq_blood_samples_case_code`, `uq_blood_samples_external_identity`.

PK: `blood_samples_pkey`.

FK: `blood_samples_archived_by_fkey`, `blood_samples_case_id_fkey`, `blood_samples_created_by_fkey`, `blood_samples_updated_by_fkey`.

UNIQUE: `uq_blood_samples_case_code`.

CHECK: `blood_samples_metadata_json_check`, `blood_samples_sample_code_check`, `blood_samples_status_check`, `ck_blood_sample_archive_state`, `ck_blood_sample_chronology`, `ck_blood_samples_expected_count`, `ck_blood_samples_identity_origin`, `ck_blood_samples_ingestion_status`.

#### campaign_attempts

Índices: `campaign_attempts_member_id_id_key`, `campaign_attempts_member_id_ordinal_key`, `campaign_attempts_pkey`, `campaign_attempts_training_run_id_key`, `ix_campaign_attempt_state`, `uq_campaign_one_active_attempt`.

PK: `campaign_attempts_pkey`.

FK: `campaign_attempts_member_id_fkey`, `campaign_attempts_training_run_id_fkey`.

UNIQUE: `campaign_attempts_member_id_id_key`, `campaign_attempts_member_id_ordinal_key`, `campaign_attempts_training_run_id_key`.

CHECK: `campaign_attempts_check`, `campaign_attempts_check1`, `campaign_attempts_check2`, `campaign_attempts_ordinal_check`, `campaign_attempts_state_check`.

Triggers de aplicación: `campaign_attempt_audit`, `campaign_attempt_guard`, `campaign_attempt_state`, `global_attempt_reservation`.

#### campaign_configurations

Índices: `campaign_configurations_pkey`.

PK: `campaign_configurations_pkey`.

FK: `campaign_configurations_campaign_id_fkey`.

CHECK: `campaign_configurations_configuration_check`, `campaign_configurations_configuration_hash_check`, `campaign_configurations_requests_check`, `ck_campaign_configuration_required_v2`.

Triggers de aplicación: `campaign_configuration_audit`, `campaign_configuration_guard`.

#### campaign_controlled_requests

Índices: `campaign_controlled_requests_attempt_id_key`, `campaign_controlled_requests_pkey`, `campaign_controlled_requests_previous_attempt_id_key`, `campaign_controlled_requests_run_id_key`.

PK: `campaign_controlled_requests_pkey`.

FK: `campaign_controlled_requests_attempt_id_fkey`, `campaign_controlled_requests_campaign_id_fkey`, `campaign_controlled_requests_campaign_id_revision_id_fkey`, `campaign_controlled_requests_member_id_fkey`, `campaign_controlled_requests_previous_attempt_id_fkey`, `campaign_controlled_requests_run_id_fkey`.

UNIQUE: `campaign_controlled_requests_attempt_id_key`, `campaign_controlled_requests_previous_attempt_id_key`, `campaign_controlled_requests_run_id_key`.

CHECK: `campaign_controlled_requests_reason_check`.

Restricción de trigger: `controlled_binding_guard`.

Triggers de aplicación: `controlled_binding_guard`, `controlled_request_guard`.

#### campaign_execution_events

Índices: `campaign_execution_events_pkey`.

PK: `campaign_execution_events_pkey`.

FK: `campaign_execution_events_campaign_id_fkey`.

#### campaign_members

Índices: `campaign_members_campaign_id_configuration_hash_seed_key`, `campaign_members_campaign_id_position_key`, `campaign_members_pkey`, `ix_campaign_member_state`.

PK: `campaign_members_pkey`.

FK: `campaign_members_campaign_id_configuration_hash_fkey`, `campaign_members_campaign_id_fkey`, `fk_member_accepted_attempt`.

UNIQUE: `campaign_members_campaign_id_configuration_hash_seed_key`, `campaign_members_campaign_id_position_key`.

CHECK: `campaign_members_check`, `campaign_members_check1`, `campaign_members_exclusion_reason_check`, `campaign_members_position_check`, `campaign_members_seed_check`, `campaign_members_state_check`.

Triggers de aplicación: `campaign_member_audit`, `campaign_member_guard`.

#### campaign_technical_revisions

Índices: `campaign_technical_revisions_campaign_id_id_key`, `campaign_technical_revisions_pkey`.

PK: `campaign_technical_revisions_pkey`.

FK: `campaign_technical_revisions_campaign_id_fkey`.

UNIQUE: `campaign_technical_revisions_campaign_id_id_key`.

CHECK: `campaign_technical_revisions_check`, `campaign_technical_revisions_check1`, `campaign_technical_revisions_payload_hash_check`.

Triggers de aplicación: `technical_revision_guard`.

#### cell_classification_events

Índices: `cell_classification_events_pkey`, `ix_cell_classification_events_run_created`, `ix_cell_classification_events_run_detection`, `ix_cell_classification_events_run_prediction`.

PK: `cell_classification_events_pkey`.

FK: `cell_classification_events_cell_detection_id_fkey`, `cell_classification_events_classification_run_id_fkey`, `fk_cell_classification_event_prediction`.

CHECK: `cell_classification_events_event_type_check`, `cell_classification_events_metadata_json_check`, `cell_classification_events_progress_current_check`, `cell_classification_events_progress_total_check`, `cell_classification_events_status_check`, `ck_cell_classification_event_progress`.

Triggers de aplicación: `trg_cell_classification_events_append_only`.

#### cell_classification_inputs

Índices: `cell_classification_inputs_pkey`, `ix_cell_classification_inputs_crop`, `ix_cell_classification_inputs_detection`, `ix_cell_classification_inputs_run_eligible_order`, `ix_cell_classification_inputs_run_image_cell`, `uq_cell_classification_inputs_crop`, `uq_cell_classification_inputs_detection`, `uq_cell_classification_inputs_order`, `uq_cell_classification_inputs_prediction_owner`.

PK: `cell_classification_inputs_pkey`.

FK: `fk_cell_classification_input_crop`, `fk_cell_classification_input_detection`, `fk_cell_classification_input_run_detection`.

UNIQUE: `uq_cell_classification_inputs_crop`, `uq_cell_classification_inputs_detection`, `uq_cell_classification_inputs_order`, `uq_cell_classification_inputs_prediction_owner`.

CHECK: `cell_classification_inputs_cell_code_check`, `cell_classification_inputs_cell_index_check`, `cell_classification_inputs_detector_algorithm_version_check`, `cell_classification_inputs_detector_key_check`, `cell_classification_inputs_detector_version_check`, `cell_classification_inputs_image_sequence_number_check`, `cell_classification_inputs_input_order_check`, `ck_cell_classification_input_crop_metadata`, `ck_cell_classification_input_eligibility`, `ck_cell_classification_input_review`.

Triggers de aplicación: `trg_cell_classification_inputs_append_only`, `trg_cell_classification_inputs_insert_state`, `trg_cell_classification_inputs_snapshot`.

#### cell_classification_reviews

Índices: `cell_classification_reviews_pkey`, `ix_cell_classification_reviews_actor_created`, `ix_cell_classification_reviews_prediction_created`.

PK: `cell_classification_reviews_pkey`.

FK: `cell_classification_reviews_actor_user_id_fkey`, `cell_classification_reviews_cell_prediction_id_fkey`.

CHECK: `cell_classification_reviews_decision_check`, `cell_classification_reviews_reviewed_label_check`, `ck_cell_classification_review_payload`.

Triggers de aplicación: `trg_cell_classification_reviews_append_only`, `trg_cell_classification_reviews_validate`.

#### cell_classification_runs

Índices: `cell_classification_runs_classification_run_code_key`, `cell_classification_runs_pkey`, `ix_cell_classification_runs_analysis_created`, `ix_cell_classification_runs_detection_created`, `ix_cell_classification_runs_model_created`, `ix_cell_classification_runs_status_created`, `uq_cell_classification_runs_detection_identity`, `uq_cell_classification_runs_equivalent_active`, `uq_cell_classification_runs_identity`.

PK: `cell_classification_runs_pkey`.

FK: `cell_classification_runs_requested_by_fkey`, `cell_classification_runs_retry_of_run_id_fkey`, `fk_cell_classification_run_deployment_version`, `fk_cell_classification_run_detection_analysis`, `fk_cell_classification_run_publication_version`.

UNIQUE: `cell_classification_runs_classification_run_code_key`, `uq_cell_classification_runs_detection_identity`, `uq_cell_classification_runs_identity`.

CHECK: `cell_classification_runs_classification_run_code_check`, `cell_classification_runs_eligible_count_check`, `cell_classification_runs_excluded_count_check`, `cell_classification_runs_failed_count_check`, `cell_classification_runs_input_count_check`, `cell_classification_runs_input_manifest_sha256_check`, `cell_classification_runs_model_name_check`, `cell_classification_runs_model_snapshot_check`, `cell_classification_runs_near_threshold_count_check`, `cell_classification_runs_parasitized_count_check`, `cell_classification_runs_processed_count_check`, `cell_classification_runs_status_check`, `cell_classification_runs_uninfected_count_check`, `ck_cell_classification_run_counts`, `ck_cell_classification_run_model_version`, `ck_cell_classification_run_retry`, `ck_cell_classification_run_terminal_state`, `ck_cell_classification_run_time_order`.

Triggers de aplicación: `trg_cell_classification_runs_protected`, `trg_cell_classification_runs_snapshot`.

#### cell_crops

Índices: `cell_crops_pkey`, `uq_cell_crops_detection`, `uq_cell_crops_id_detection`, `uq_cell_crops_storage_key`.

PK: `cell_crops_pkey`.

FK: `fk_cell_crops_detection`.

UNIQUE: `uq_cell_crops_detection`, `uq_cell_crops_storage_key`.

CHECK: `cell_crops_file_size_bytes_check`, `cell_crops_format_check`, `cell_crops_height_px_check`, `cell_crops_padding_px_check`, `cell_crops_relative_storage_key_check`, `cell_crops_sha256_check`, `cell_crops_width_px_check`.

Triggers de aplicación: `trg_cell_crops_append_only`.

#### cell_detection_events

Índices: `cell_detection_events_pkey`, `ix_cell_detection_events_run_created`, `ix_cell_detection_events_run_image`.

PK: `cell_detection_events_pkey`.

FK: `cell_detection_events_detection_run_id_fkey`, `cell_detection_events_microscopy_image_id_fkey`.

CHECK: `cell_detection_events_event_type_check`, `cell_detection_events_metadata_json_check`, `cell_detection_events_progress_current_check`, `cell_detection_events_progress_total_check`, `cell_detection_events_stage_check`, `cell_detection_events_status_check`, `ck_cell_detection_event_progress`.

Triggers de aplicación: `trg_cell_detection_events_append_only`.

#### cell_detection_runs

Índices: `cell_detection_runs_detection_run_code_key`, `cell_detection_runs_pkey`, `ix_cell_detection_runs_analysis_created`, `ix_cell_detection_runs_status_created`, `uq_cell_detection_runs_equivalent_active`, `uq_cell_detection_runs_identity`.

PK: `cell_detection_runs_pkey`.

FK: `cell_detection_runs_analysis_run_id_fkey`, `cell_detection_runs_requested_by_fkey`.

UNIQUE: `cell_detection_runs_detection_run_code_key`, `uq_cell_detection_runs_identity`.

CHECK: `cell_detection_runs_algorithm_version_check`, `cell_detection_runs_check`, `cell_detection_runs_component_count_check`, `cell_detection_runs_crop_count_check`, `cell_detection_runs_detection_count_check`, `cell_detection_runs_detection_run_code_check`, `cell_detection_runs_detector_key_check`, `cell_detection_runs_detector_version_check`, `cell_detection_runs_image_count_check`, `cell_detection_runs_input_manifest_sha256_check`, `cell_detection_runs_profile_snapshot_check`, `cell_detection_runs_status_check`, `cell_detection_runs_warning_count_check`, `ck_cell_detection_run_terminal_state`.

Triggers de aplicación: `trg_cell_detection_runs_immutable_identity`.

#### cell_detections

Índices: `cell_detections_pkey`, `ix_cell_detections_run_image`, `uq_cell_detections_cell_code`, `uq_cell_detections_component`, `uq_cell_detections_identity`, `uq_cell_detections_run_index`.

PK: `cell_detections_pkey`.

FK: `fk_cell_detections_component`, `fk_cell_detections_run_analysis`.

UNIQUE: `uq_cell_detections_cell_code`, `uq_cell_detections_component`, `uq_cell_detections_identity`, `uq_cell_detections_run_index`.

CHECK: `cell_detections_automated_status_check`, `cell_detections_bbox_height_check`, `cell_detections_bbox_width_check`, `cell_detections_bbox_x_check`, `cell_detections_bbox_y_check`, `cell_detections_cell_code_check`, `cell_detections_cell_index_check`, `cell_detections_coordinate_space_check`, `cell_detections_detector_score_check`.

Triggers de aplicación: `trg_cell_detections_append_only`.

#### cell_explanations

Índices: `cell_explanations_cell_prediction_id_key`, `cell_explanations_pkey`, `ix_cell_explanations_status_created`.

PK: `cell_explanations_pkey`.

FK: `cell_explanations_cell_prediction_id_fkey`.

UNIQUE: `cell_explanations_cell_prediction_id_key`.

CHECK: `cell_explanations_method_check`, `cell_explanations_method_version_check`, `cell_explanations_parameters_json_check`, `cell_explanations_status_check`, `ck_cell_explanation_dimensions`, `ck_cell_explanation_hashes`, `ck_cell_explanation_heatmap_key`, `ck_cell_explanation_overlay_key`, `ck_cell_explanation_sizes`, `ck_cell_explanation_state`, `ck_cell_explanation_time_order`.

Triggers de aplicación: `trg_cell_explanations_contract`, `trg_cell_explanations_protected`.

#### cell_predictions

Índices: `cell_predictions_classification_input_id_key`, `cell_predictions_pkey`, `ix_cell_predictions_crop`, `ix_cell_predictions_detection`, `ix_cell_predictions_run_label`, `ix_cell_predictions_run_near_threshold`, `ix_cell_predictions_run_status`, `uq_cell_predictions_run_identity`.

PK: `cell_predictions_pkey`.

FK: `fk_cell_prediction_input_owner`.

UNIQUE: `cell_predictions_classification_input_id_key`, `uq_cell_predictions_run_identity`.

CHECK: `cell_predictions_prediction_status_check`, `cell_predictions_preprocessing_snapshot_check`, `cell_predictions_raw_output_check`, `cell_predictions_threshold_source_check`, `ck_cell_prediction_class_index`, `ck_cell_prediction_completed_payload`, `ck_cell_prediction_decision_margin`, `ck_cell_prediction_duration`, `ck_cell_prediction_label_index`, `ck_cell_prediction_margin`, `ck_cell_prediction_positive_class`, `ck_cell_prediction_probability_parasitized`, `ck_cell_prediction_probability_sum`, `ck_cell_prediction_probability_uninfected`, `ck_cell_prediction_threshold`.

Triggers de aplicación: `trg_cell_predictions_append_only`, `trg_cell_predictions_insert_state`, `trg_cell_predictions_validate_input`.

#### classification_reports

Índices: `classification_reports_pkey`, `idx_classification_reports_run_id`.

PK: `classification_reports_pkey`.

FK: `classification_reports_run_id_fkey`.

#### clinical_identities

Índices: `clinical_identities_pkey`, `uq_clinical_identities_source`.

PK: `clinical_identities_pkey`.

FK: `clinical_identities_dataset_id_fkey`.

UNIQUE: `uq_clinical_identities_source`.

CHECK: `chk_clinical_identities_metadata_object`, `chk_clinical_identities_status`, `chk_clinical_identities_type`.

#### confusion_matrices

Índices: `confusion_matrices_pkey`, `idx_confusion_matrices_run_id`.

PK: `confusion_matrices_pkey`.

FK: `confusion_matrices_run_id_fkey`.

#### dataset_materialization_activations

Índices: `dataset_materialization_activations_pkey`, `ix_dataset_materialization_activations_dataset_version_id`, `ix_dataset_materialization_activations_materialization_id`, `uq_dataset_materialization_activations_current_family`.

PK: `dataset_materialization_activations_pkey`.

FK: `dataset_materialization_activations_dataset_version_id_fkey`, `dataset_materialization_activations_materialization_id_fkey`.

CHECK: `chk_dataset_materialization_activations_interval`, `chk_dataset_materialization_activations_metadata_object`.

Triggers de aplicación: `trg_activation_materialization_consistency`.

#### dataset_materializations

Índices: `dataset_materializations_pkey`, `ix_dataset_materializations_dataset_version_id`, `uq_dataset_materializations_attempt`.

PK: `dataset_materializations_pkey`.

FK: `dataset_materializations_dataset_version_id_fkey`.

UNIQUE: `uq_dataset_materializations_attempt`.

CHECK: `chk_dataset_materializations_attempt`, `chk_dataset_materializations_manifest_object`, `chk_dataset_materializations_metadata_object`, `chk_dataset_materializations_reconciliation`, `chk_dataset_materializations_record_count`, `chk_dataset_materializations_relative_root`, `chk_dataset_materializations_status`.

#### dataset_source_records

Índices: `dataset_source_records_pkey`, `ix_dataset_source_records_clinical_identity_id`, `ix_dataset_source_records_dataset_id`, `ix_dataset_source_records_decoded_pixel_sha256`, `ix_dataset_source_records_source_file_sha256`, `uq_dataset_source_records_key`.

PK: `dataset_source_records_pkey`.

FK: `dataset_source_records_clinical_identity_id_fkey`, `dataset_source_records_dataset_id_fkey`.

UNIQUE: `uq_dataset_source_records_key`.

CHECK: `chk_dataset_source_records_dimensions`, `chk_dataset_source_records_identity_status`, `chk_dataset_source_records_metadata_object`, `chk_dataset_source_records_pixel_sha256`, `chk_dataset_source_records_source_sha256`.

#### dataset_split_assignments

Índices: `dataset_split_assignments_pkey`, `ix_dataset_split_assignments_clinical_identity_id`, `ix_dataset_split_assignments_dataset_version_id`, `uq_dataset_split_assignments_record`.

PK: `dataset_split_assignments_pkey`.

FK: `dataset_split_assignments_clinical_identity_id_fkey`, `dataset_split_assignments_dataset_version_id_fkey`, `dataset_split_assignments_source_record_id_fkey`.

UNIQUE: `uq_dataset_split_assignments_record`.

CHECK: `chk_dataset_split_assignments_metadata_object`, `chk_dataset_split_assignments_split`.

Triggers de aplicación: `trg_dataset_assignment_consistency`, `trg_protect_frozen_dataset_assignment_updates`, `trg_protect_frozen_dataset_assignments_delete`.

#### dataset_split_images

Índices: `dataset_split_images_pkey`, `idx_dataset_split_images_class`, `idx_dataset_split_images_dataset_dir`, `idx_dataset_split_images_dataset_id`, `idx_dataset_split_images_relative_path`, `idx_dataset_split_images_split`, `ix_dataset_split_images_dataset_materialization_id`, `ix_dataset_split_images_dataset_version_id`, `uq_dataset_split_images_path`.

PK: `dataset_split_images_pkey`.

FK: `dataset_split_images_dataset_id_fkey`, `dataset_split_images_dataset_materialization_id_fkey`, `dataset_split_images_dataset_version_id_fkey`.

UNIQUE: `uq_dataset_split_images_path`.

CHECK: `chk_dataset_split_images_class_index`, `chk_dataset_split_images_class_name`, `chk_dataset_split_images_split`.

#### dataset_split_statistics

Índices: `dataset_split_statistics_pkey`, `ix_dataset_split_statistics_version_metric`.

PK: `dataset_split_statistics_pkey`.

FK: `dataset_split_statistics_dataset_version_id_fkey`.

CHECK: `chk_dataset_split_statistics_details_object`, `chk_dataset_split_statistics_value`.

#### dataset_split_validation_checks

Índices: `dataset_split_validation_checks_pkey`, `ix_dataset_split_validation_checks_version_name`.

PK: `dataset_split_validation_checks_pkey`.

FK: `dataset_split_validation_checks_dataset_version_id_fkey`.

CHECK: `chk_dataset_split_validation_checks_details_object`, `chk_dataset_split_validation_checks_status`.

#### dataset_splits

Índices: `dataset_splits_pkey`.

PK: `dataset_splits_pkey`.

FK: `dataset_splits_dataset_id_fkey`.

#### dataset_version_sources

Índices: `dataset_version_sources_pkey`, `ix_dataset_version_sources_dataset_id`.

PK: `dataset_version_sources_pkey`.

FK: `dataset_version_sources_dataset_id_fkey`, `dataset_version_sources_dataset_version_id_fkey`.

CHECK: `chk_dataset_version_sources_role`.

Triggers de aplicación: `trg_protect_frozen_dataset_version_sources`.

#### dataset_versions

Índices: `dataset_versions_pkey`, `ix_dataset_versions_status`, `uq_dataset_versions_name_semver`.

PK: `dataset_versions_pkey`.

UNIQUE: `uq_dataset_versions_name_semver`.

CHECK: `chk_dataset_versions_class_mapping_object`, `chk_dataset_versions_methodology_object`, `chk_dataset_versions_ratio_sum`, `chk_dataset_versions_source_count`, `chk_dataset_versions_status`, `chk_dataset_versions_test_ratio`, `chk_dataset_versions_train_ratio`, `chk_dataset_versions_val_ratio`.

Triggers de aplicación: `trg_dataset_version_lifecycle`.

#### datasets

Índices: `datasets_pkey`, `idx_datasets_metadata_gin`.

PK: `datasets_pkey`.

#### deployed_model_versions

Índices: `deployed_model_versions_pkey`, `idx_deployed_model_versions_checkpoint_artifact`, `idx_deployed_model_versions_model_version`, `idx_deployed_model_versions_slot_history`, `idx_deployed_model_versions_status`, `idx_deployed_model_versions_threshold_calibration`, `uq_deployed_model_versions_active_slot`, `uq_deployed_model_versions_id_version`, `uq_deployed_model_versions_one_production_champion`.

PK: `deployed_model_versions_pkey`.

FK: `fk_deployed_model_versions_rollback`, `fk_deployed_model_versions_supersedes`, `fk_deployed_model_versions_threshold_version`, `fk_deployed_model_versions_version_artifact`.

CHECK: `chk_deployed_model_versions_active_mapping`, `chk_deployed_model_versions_active_timestamps`, `chk_deployed_model_versions_artifact_size`, `chk_deployed_model_versions_clinical_convention`, `chk_deployed_model_versions_distinct_history`, `chk_deployed_model_versions_names`, `chk_deployed_model_versions_retired_timestamp`, `chk_deployed_model_versions_sha256`, `chk_deployed_model_versions_snapshots`, `chk_deployed_model_versions_status`, `chk_deployed_model_versions_threshold`, `chk_deployed_model_versions_timestamp_order`.

Triggers de aplicación: `trg_deployed_model_versions_10_immutable`, `trg_deployed_model_versions_20_validate`.

#### environment_packages

Índices: `environment_packages_pkey`, `idx_environment_packages_run_id`.

PK: `environment_packages_pkey`.

FK: `environment_packages_run_id_fkey`.

#### errors

Índices: `errors_pkey`, `idx_errors_run_id`.

PK: `errors_pkey`.

FK: `errors_run_id_fkey`.

#### execution_logs

Índices: `execution_logs_pkey`, `idx_execution_logs_run_id`.

PK: `execution_logs_pkey`.

FK: `execution_logs_run_id_fkey`.

#### experiment_execution_events

Índices: `experiment_execution_events_pkey`.

PK: `experiment_execution_events_pkey`.

Triggers de aplicación: `global_execution_event_immutable`.

#### experiment_execution_gate

Índices: `experiment_execution_gate_pkey`.

PK: `experiment_execution_gate_pkey`.

CHECK: `experiment_execution_gate_singleton_check`.

#### experimental_campaigns

Índices: `experimental_campaigns_pkey`, `ix_campaign_dataset_state`.

PK: `experimental_campaigns_pkey`.

FK: `experimental_campaigns_dataset_evidence_id_fkey`, `experimental_campaigns_dataset_version_id_fkey`, `experimental_campaigns_experiment_id_fkey`.

CHECK: `ck_campaign_frozen_required_v2`, `experimental_campaigns_actor_check`, `experimental_campaigns_check`, `experimental_campaigns_check1`, `experimental_campaigns_dataset_snapshot_check`, `experimental_campaigns_environment_check`, `experimental_campaigns_expected_count_check`, `experimental_campaigns_name_check`, `experimental_campaigns_protocol_check`, `experimental_campaigns_purpose_check`, `experimental_campaigns_requested_check`, `experimental_campaigns_state_check`.

Triggers de aplicación: `campaign_audit`, `campaign_guard`, `controlled_pause_guard`.

#### experiments

Índices: `experiments_pkey`.

PK: `experiments_pkey`.

#### explainability_results

Índices: `explainability_results_pkey`, `idx_explainability_case_method`, `idx_explainability_method`, `idx_explainability_output_path`, `idx_explainability_run_id`, `idx_explainability_success`.

PK: `explainability_results_pkey`.

FK: `explainability_results_prediction_id_fkey`, `explainability_results_run_id_fkey`.

#### identity_evidence

Índices: `identity_evidence_pkey`, `ix_identity_evidence_clinical_identity_id`, `ix_identity_evidence_source_record_id`.

PK: `identity_evidence_pkey`.

FK: `identity_evidence_clinical_identity_id_fkey`, `identity_evidence_source_record_id_fkey`.

CHECK: `chk_identity_evidence_json_object`.

#### image_analysis_jobs

Índices: `idx_image_analysis_jobs_deployment`, `idx_image_analysis_jobs_input_artifact`, `idx_image_analysis_jobs_model_version`, `idx_image_analysis_jobs_run`, `idx_image_analysis_jobs_source_image`, `idx_image_analysis_jobs_status_created`, `image_analysis_jobs_pkey`, `uq_image_analysis_jobs_idempotency`, `uq_image_analysis_jobs_identity`.

PK: `image_analysis_jobs_pkey`.

FK: `fk_image_analysis_jobs_input_artifact`, `fk_image_analysis_jobs_run_deployment_version`, `fk_image_analysis_jobs_source_image`.

CHECK: `chk_image_analysis_jobs_counts`, `chk_image_analysis_jobs_idempotency_key`, `chk_image_analysis_jobs_payload_objects`, `chk_image_analysis_jobs_quality_status`, `chk_image_analysis_jobs_source`, `chk_image_analysis_jobs_status`, `chk_image_analysis_jobs_status_timestamps`, `chk_image_analysis_jobs_threshold`, `chk_image_analysis_jobs_timestamp_order`.

Triggers de aplicación: `trg_image_analysis_jobs_validate`.

#### image_connected_components

Índices: `image_connected_components_pkey`, `ix_image_connected_components_run_image`, `ix_image_connected_components_status`, `uq_image_connected_components_identity`, `uq_image_connected_components_run_image_index`.

PK: `image_connected_components_pkey`.

FK: `fk_components_detection_analysis`, `fk_components_frozen_image`.

UNIQUE: `uq_image_connected_components_identity`, `uq_image_connected_components_run_image_index`.

CHECK: `ck_connected_component_rejection`, `image_connected_components_area_px_check`, `image_connected_components_bbox_height_check`, `image_connected_components_bbox_width_check`, `image_connected_components_bbox_x_check`, `image_connected_components_bbox_y_check`, `image_connected_components_centroid_x_check`, `image_connected_components_centroid_y_check`, `image_connected_components_circularity_check`, `image_connected_components_component_index_check`, `image_connected_components_component_status_check`, `image_connected_components_metrics_json_check`, `image_connected_components_perimeter_px_check`, `image_connected_components_solidity_check`.

Triggers de aplicación: `trg_image_connected_components_append_only`.

#### image_ingestion_batches

Índices: `image_ingestion_batches_pkey`, `ix_ingestion_batches_sample`, `uq_ingestion_batches_source_group`.

PK: `image_ingestion_batches_pkey`.

FK: `image_ingestion_batches_case_id_fkey`, `image_ingestion_batches_created_by_fkey`, `image_ingestion_batches_sample_id_fkey`, `image_ingestion_batches_slide_id_fkey`, `image_ingestion_batches_subject_id_fkey`.

CHECK: `image_ingestion_batches_acquisition_origin_check`, `image_ingestion_batches_expected_image_count_check`, `image_ingestion_batches_metadata_json_check`, `image_ingestion_batches_received_image_count_check`, `image_ingestion_batches_status_check`.

#### image_quality_assessments

Índices: `image_quality_assessments_analysis_run_id_microscopy_image__key`, `image_quality_assessments_pkey`.

PK: `image_quality_assessments_pkey`.

FK: `image_quality_assessments_analysis_run_id_fkey`, `image_quality_assessments_analysis_run_image_id_analysis_r_fkey`, `image_quality_assessments_microscopy_image_id_fkey`.

UNIQUE: `image_quality_assessments_analysis_run_id_microscopy_image__key`.

CHECK: `image_quality_assessments_analysis_scale_check`, `image_quality_assessments_analyzed_height_px_check`, `image_quality_assessments_analyzed_width_px_check`, `image_quality_assessments_assessment_status_check`, `image_quality_assessments_bright_pixel_ratio_check`, `image_quality_assessments_dark_pixel_ratio_check`, `image_quality_assessments_failure_codes_check`, `image_quality_assessments_height_px_check`, `image_quality_assessments_metrics_json_check`, `image_quality_assessments_near_black_border_ratio_check`, `image_quality_assessments_pixel_count_check`, `image_quality_assessments_quality_verdict_check`, `image_quality_assessments_usable_field_ratio_check`, `image_quality_assessments_warning_codes_check`, `image_quality_assessments_width_px_check`.

#### local_execution_jobs

Índices: `local_execution_jobs_owner_key`, `local_execution_jobs_pkey`, `local_execution_jobs_run_id_key`, `local_one_active`.

PK: `local_execution_jobs_pkey`.

FK: `local_execution_jobs_campaign_id_fkey`, `local_execution_jobs_run_id_fkey`.

UNIQUE: `local_execution_jobs_owner_key`, `local_execution_jobs_run_id_key`.

CHECK: `local_execution_jobs_state_check`.

#### microscopy_analysis_events

Índices: `ix_microscopy_analysis_events_run`, `microscopy_analysis_events_pkey`.

PK: `microscopy_analysis_events_pkey`.

FK: `microscopy_analysis_events_analysis_run_id_fkey`, `microscopy_analysis_events_microscopy_image_id_fkey`.

CHECK: `microscopy_analysis_events_progress_current_check`, `microscopy_analysis_events_progress_total_check`.

#### microscopy_analysis_run_images

Índices: `microscopy_analysis_run_image_analysis_run_id_microscopy_im_key`, `microscopy_analysis_run_image_analysis_run_id_sequence_numb_key`, `microscopy_analysis_run_image_id_analysis_run_id_microscopy_key`, `microscopy_analysis_run_images_pkey`.

PK: `microscopy_analysis_run_images_pkey`.

FK: `microscopy_analysis_run_images_analysis_run_id_fkey`, `microscopy_analysis_run_images_microscopy_image_id_fkey`.

UNIQUE: `microscopy_analysis_run_image_analysis_run_id_microscopy_im_key`, `microscopy_analysis_run_image_analysis_run_id_sequence_numb_key`, `microscopy_analysis_run_image_id_analysis_run_id_microscopy_key`.

CHECK: `microscopy_analysis_run_images_input_file_size_bytes_check`, `microscopy_analysis_run_images_input_height_px_check`, `microscopy_analysis_run_images_input_width_px_check`, `microscopy_analysis_run_images_quality_status_check`, `microscopy_analysis_run_images_sequence_number_check`.

#### microscopy_analysis_runs

Índices: `ix_microscopy_analysis_runs_status`, `ix_microscopy_analysis_runs_subject`, `microscopy_analysis_runs_pkey`, `microscopy_analysis_runs_run_code_key`, `uq_microscopy_analysis_equivalent`.

PK: `microscopy_analysis_runs_pkey`.

FK: `microscopy_analysis_runs_case_id_fkey`, `microscopy_analysis_runs_ingestion_batch_id_fkey`, `microscopy_analysis_runs_requested_by_fkey`, `microscopy_analysis_runs_sample_id_fkey`, `microscopy_analysis_runs_slide_id_fkey`, `microscopy_analysis_runs_subject_id_fkey`.

UNIQUE: `microscopy_analysis_runs_run_code_key`.

CHECK: `microscopy_analysis_runs_active_stage_check`, `microscopy_analysis_runs_input_image_count_check`, `microscopy_analysis_runs_quality_gate_status_check`, `microscopy_analysis_runs_quality_profile_snapshot_check`, `microscopy_analysis_runs_run_status_check`.

#### microscopy_images

Índices: `ix_microscopy_images_ingestion_batch`, `ix_microscopy_images_sha256`, `ix_microscopy_images_slide`, `ix_microscopy_images_status_created`, `microscopy_images_pkey`, `uq_microscopy_images_external_path`, `uq_microscopy_images_slide_code`, `uq_microscopy_images_slide_sha256`.

PK: `microscopy_images_pkey`.

FK: `microscopy_images_archived_by_fkey`, `microscopy_images_created_by_fkey`, `microscopy_images_ingestion_batch_id_fkey`, `microscopy_images_slide_id_fkey`, `microscopy_images_updated_by_fkey`.

UNIQUE: `uq_microscopy_images_slide_code`, `uq_microscopy_images_slide_sha256`.

CHECK: `ck_microscopy_image_archive_state`, `ck_microscopy_images_acquisition_origin`, `ck_microscopy_images_channels`, `ck_microscopy_images_sequence`, `microscopy_images_bit_depth_check`, `microscopy_images_file_size_bytes_check`, `microscopy_images_height_px_check`, `microscopy_images_image_code_check`, `microscopy_images_magnification_check`, `microscopy_images_metadata_json_check`, `microscopy_images_mime_type_check`, `microscopy_images_sha256_check`, `microscopy_images_status_check`, `microscopy_images_storage_key_check`, `microscopy_images_width_px_check`.

#### model_governance_backfill_audit

Índices: `idx_model_governance_audit_batch`, `idx_model_governance_audit_record`, `idx_model_governance_audit_reversal`, `model_governance_backfill_audit_pkey`.

PK: `model_governance_backfill_audit_pkey`.

FK: `fk_model_governance_audit_reversal`.

CHECK: `chk_model_governance_audit_after_object`, `chk_model_governance_audit_before_object`, `chk_model_governance_audit_event_type`, `chk_model_governance_audit_metadata_object`, `chk_model_governance_audit_result_status`, `chk_model_governance_audit_reversal`.

Triggers de aplicación: `trg_model_governance_audit_append_only`.

#### model_versions

Índices: `idx_model_versions_checkpoint_artifact`, `idx_model_versions_model`, `idx_model_versions_sha256`, `idx_model_versions_status_lineage`, `idx_model_versions_training_run`, `model_versions_pkey`, `uq_model_versions_checkpoint_artifact`, `uq_model_versions_id_checkpoint_artifact`, `uq_model_versions_id_training_run`, `uq_model_versions_name_number`, `uq_model_versions_training_version_name`, `uq_model_versions_unjustified_sha256`.

PK: `model_versions_pkey`.

FK: `fk_model_versions_checkpoint_artifact_owner`, `model_versions_model_id_fkey`, `model_versions_training_run_id_fkey`.

CHECK: `chk_model_versions_artifact_requires_training`, `chk_model_versions_artifact_size`, `chk_model_versions_governed_hash`, `chk_model_versions_lineage_status`, `chk_model_versions_profile_objects`, `chk_model_versions_resolved_training`, `chk_model_versions_sha256`, `chk_model_versions_status`, `chk_model_versions_version_number`.

Triggers de aplicación: `trg_model_versions_governance`.

#### models

Índices: `models_pkey`.

PK: `models_pkey`.

Triggers de aplicación: `campaign_catalog_identity_guard`.

#### predictions

Índices: `idx_predictions_analysis_job`, `idx_predictions_case_type`, `idx_predictions_case_type_run`, `idx_predictions_classifier_model_version`, `idx_predictions_created_at`, `idx_predictions_deployed_model_version`, `idx_predictions_detector_model_version`, `idx_predictions_inference_run`, `idx_predictions_metadata_source`, `idx_predictions_metadata_workflow`, `idx_predictions_model_version`, `idx_predictions_predicted_label`, `idx_predictions_review_status`, `idx_predictions_run_id`, `idx_predictions_true_pred`, `predictions_pkey`, `uq_predictions_job_cell_index`.

PK: `predictions_pkey`.

FK: `fk_predictions_analysis_job`, `fk_predictions_classifier_model_version`, `fk_predictions_crop_artifact`, `fk_predictions_deployed_model_version`, `fk_predictions_detector_model_version`, `fk_predictions_explanation_artifact`, `fk_predictions_inference_run`, `fk_predictions_job_provenance`, `fk_predictions_model_version`, `fk_predictions_source_image`, `predictions_dataset_id_fkey`, `predictions_run_id_fkey`.

CHECK: `chk_predictions_bbox`, `chk_predictions_cell_requirements`, `chk_predictions_class_label`, `chk_predictions_confidence_level`, `chk_predictions_predicted_class`, `chk_predictions_probability_parasitized`, `chk_predictions_probability_uninfected`, `chk_predictions_quality_status`, `chk_predictions_review_status`, `chk_predictions_reviewed_label`, `chk_predictions_scope`, `chk_predictions_threshold_used`.

#### quality_assessment_queue_items

Índices: `ix_quality_queue_order`, `ix_quality_queue_priority_requested`, `quality_assessment_queue_items_pkey`, `uq_quality_queue_active_run`.

PK: `quality_assessment_queue_items_pkey`.

FK: `quality_assessment_queue_items_analysis_run_id_fkey`, `quality_assessment_queue_items_requested_by_fkey`.

CHECK: `quality_assessment_queue_items_attempt_count_check`, `quality_assessment_queue_items_priority_check`, `quality_assessment_queue_items_status_check`.

#### quality_gate_decisions

Índices: `ix_quality_gate_decisions_run`, `quality_gate_decisions_pkey`.

PK: `quality_gate_decisions_pkey`.

FK: `quality_gate_decisions_actor_user_id_fkey`, `quality_gate_decisions_analysis_run_id_fkey`.

CHECK: `quality_gate_decisions_comment_check`, `quality_gate_decisions_decision_check`.

#### research_subjects

Índices: `ix_research_subjects_status_created`, `research_subjects_pkey`, `research_subjects_subject_code_key`, `uq_research_subjects_external_identity`.

PK: `research_subjects_pkey`.

FK: `research_subjects_archived_by_fkey`, `research_subjects_created_by_fkey`, `research_subjects_updated_by_fkey`.

UNIQUE: `research_subjects_subject_code_key`.

CHECK: `ck_research_subject_archive_state`, `research_subjects_metadata_json_check`, `research_subjects_status_check`, `research_subjects_subject_code_check`.

#### roles

Índices: `roles_name_key`, `roles_pkey`.

PK: `roles_pkey`.

UNIQUE: `roles_name_key`.

#### run_checkpoint_policy

Índices: `idx_run_checkpoint_policy_artifact`, `idx_run_checkpoint_policy_model_version`, `idx_run_checkpoint_policy_run_id`, `run_checkpoint_policy_pkey`.

PK: `run_checkpoint_policy_pkey`.

FK: `fk_run_checkpoint_policy_artifact_owner`, `fk_run_checkpoint_policy_model_version_owner`, `fk_run_checkpoint_policy_version_artifact`, `run_checkpoint_policy_run_id_fkey`.

#### run_clinical_metrics

Índices: `idx_run_clinical_metrics_model_name`, `idx_run_clinical_metrics_run_id`, `idx_run_clinical_metrics_split_name`, `run_clinical_metrics_pkey`.

PK: `run_clinical_metrics_pkey`.

FK: `run_clinical_metrics_model_id_fkey`, `run_clinical_metrics_run_id_fkey`.

CHECK: `chk_run_clinical_metrics_split`.

#### run_dataset_images

Índices: `idx_run_dataset_images_image_id`, `idx_run_dataset_images_run_id`, `idx_run_dataset_images_split`, `idx_run_dataset_images_usage_context`, `run_dataset_images_pkey`, `uq_run_dataset_images_usage`.

PK: `run_dataset_images_pkey`.

FK: `run_dataset_images_image_id_fkey`, `run_dataset_images_run_id_fkey`.

UNIQUE: `uq_run_dataset_images_usage`.

CHECK: `chk_run_dataset_images_class_index`, `chk_run_dataset_images_class_name`, `chk_run_dataset_images_split`, `chk_run_dataset_images_usage_context`.

#### run_image_predictions

Índices: `idx_run_image_predictions_case_type`, `idx_run_image_predictions_run_id`, `idx_run_image_predictions_split`, `run_image_predictions_pkey`.

PK: `run_image_predictions_pkey`.

FK: `run_image_predictions_image_id_fkey`, `run_image_predictions_run_id_fkey`.

CHECK: `chk_run_image_predictions_case_type`, `chk_run_image_predictions_split`, `chk_run_image_predictions_usage_context`.

#### run_io_records

Índices: `idx_run_io_records_clinical_metadata_gin`, `idx_run_io_records_created_at`, `idx_run_io_records_model_metadata_gin`, `idx_run_io_records_model_name`, `idx_run_io_records_run_id`, `idx_run_io_records_run_type`, `idx_run_io_records_script_name`, `ix_run_io_records_dataset_materialization_id`, `ix_run_io_records_dataset_version_id`, `run_io_records_pkey`.

PK: `run_io_records_pkey`.

FK: `run_io_records_dataset_materialization_id_fkey`, `run_io_records_dataset_version_id_fkey`, `run_io_records_run_id_fkey`.

#### run_lineage

Índices: `idx_run_lineage_checkpoint_artifact`, `idx_run_lineage_checkpoint_path`, `idx_run_lineage_child_run_id`, `idx_run_lineage_model_version`, `idx_run_lineage_parent_run_id`, `idx_run_lineage_relationship_type`, `run_lineage_pkey`, `uq_run_lineage_parent_child_type`, `uq_run_lineage_single_evaluation_training_parent`.

PK: `run_lineage_pkey`.

FK: `fk_run_lineage_checkpoint_artifact_owner`, `fk_run_lineage_model_version_owner`, `fk_run_lineage_version_artifact`, `run_lineage_child_run_id_fkey`, `run_lineage_parent_run_id_fkey`.

UNIQUE: `uq_run_lineage_parent_child_type`.

CHECK: `chk_run_lineage_confidence`, `chk_run_lineage_distinct_runs`, `chk_run_lineage_relationship_type`.

Triggers de aplicación: `trg_run_lineage_governance`.

#### run_metrics

Índices: `idx_run_metrics_name`, `idx_run_metrics_run_id`, `run_metrics_pkey`.

PK: `run_metrics_pkey`.

FK: `run_metrics_run_id_fkey`.

#### run_model_deployments

Índices: `idx_run_model_deployments_deployment`, `idx_run_model_deployments_model_version`, `run_model_deployments_pkey`, `uq_run_model_deployments_binding`, `uq_run_model_deployments_primary`, `uq_run_model_deployments_run_deployment_version`.

PK: `run_model_deployments_pkey`.

FK: `fk_run_model_deployments_deployment_version`, `fk_run_model_deployments_run`.

CHECK: `chk_run_model_deployments_metadata`, `chk_run_model_deployments_ordinal`, `chk_run_model_deployments_role`, `chk_run_model_deployments_weight`.

Triggers de aplicación: `trg_run_model_deployments_validate`.

#### run_threshold_calibration

Índices: `idx_run_threshold_calibration_artifact`, `idx_run_threshold_calibration_model_version`, `idx_run_threshold_calibration_run_id`, `run_threshold_calibration_pkey`, `uq_run_threshold_calibration_id_version`.

PK: `run_threshold_calibration_pkey`.

FK: `fk_run_threshold_calibration_artifact_owner`, `fk_run_threshold_calibration_model_version`, `run_threshold_calibration_run_id_fkey`.

CHECK: `chk_run_threshold_calibration_positive_label`, `chk_run_threshold_calibration_score_name`, `chk_run_threshold_calibration_split`, `chk_run_threshold_calibration_status`.

#### runs

Índices: `idx_runs_dataset_id`, `idx_runs_execution_parameters_gin`, `idx_runs_execution_type`, `idx_runs_inference_script`, `idx_runs_metadata_gin`, `idx_runs_model_id`, `idx_runs_parameters_gin`, `idx_runs_run_type`, `idx_runs_started_at`, `idx_runs_status`, `idx_runs_training_release_status`, `ix_runs_dataset_version_id`, `runs_pkey`, `uq_runs_single_productive_stage2`.

PK: `runs_pkey`.

FK: `runs_campaign_id_fkey`, `runs_dataset_id_fkey`, `runs_dataset_version_id_fkey`, `runs_experiment_id_fkey`, `runs_model_id_fkey`.

CHECK: `chk_runs_configuration_object`, `ck_runs_release_status_requires_timestamp`, `ck_runs_release_status_training_vocabulary`.

Triggers de aplicación: `campaign_run_identity_guard`, `controlled_run_guard`.

#### schema_migrations

Índices: `schema_migrations_pkey`.

PK: `schema_migrations_pkey`.

CHECK: `chk_schema_migrations_checksum_sha256`.

#### scientific_cases

Índices: `ix_scientific_cases_status_created`, `ix_scientific_cases_subject`, `scientific_cases_case_code_key`, `scientific_cases_pkey`.

PK: `scientific_cases_pkey`.

FK: `scientific_cases_archived_by_fkey`, `scientific_cases_created_by_fkey`, `scientific_cases_subject_id_fkey`, `scientific_cases_updated_by_fkey`.

UNIQUE: `scientific_cases_case_code_key`.

CHECK: `ck_scientific_case_archive_state`, `scientific_cases_case_code_check`, `scientific_cases_metadata_json_check`, `scientific_cases_priority_check`, `scientific_cases_source_type_check`, `scientific_cases_status_check`.

#### scientific_reviews

Índices: `ix_scientific_reviews_actor_created`, `ix_scientific_reviews_entity_created`, `scientific_reviews_pkey`.

PK: `scientific_reviews_pkey`.

FK: `scientific_reviews_actor_user_id_fkey`, `scientific_reviews_entity_id_fkey`.

CHECK: `ck_scientific_review_comment`, `scientific_reviews_decision_check`, `scientific_reviews_entity_type_check`.

Triggers de aplicación: `trg_scientific_reviews_append_only`.

#### scientific_validation_annotation_events

Índices: `ix_validation_annotation_events_actor_created`, `ix_validation_annotation_events_annotation_created`, `scientific_validation_annotat_annotation_id_annotation_vers_key`, `scientific_validation_annotation_events_pkey`.

PK: `scientific_validation_annotation_events_pkey`.

FK: `scientific_validation_annotation_eve_validation_session_id_fkey`, `scientific_validation_annotation_events_actor_user_id_fkey`, `scientific_validation_annotation_events_annotation_id_fkey`.

UNIQUE: `scientific_validation_annotat_annotation_id_annotation_vers_key`.

CHECK: `ck_validation_annotation_event_before`, `scientific_validation_annotation_event_annotation_version_check`, `scientific_validation_annotation_events_after_state_check`, `scientific_validation_annotation_events_event_type_check`.

Triggers de aplicación: `trg_validation_annotation_events_append_only`.

#### scientific_validation_annotations

Índices: `ix_validation_annotations_general_target`, `ix_validation_annotations_session_analysis`, `ix_validation_annotations_session_category`, `ix_validation_annotations_session_cell`, `ix_validation_annotations_session_created`, `ix_validation_annotations_session_sample`, `scientific_validation_annotations_pkey`.

PK: `scientific_validation_annotations_pkey`.

FK: `scientific_validation_annotations_analysis_run_id_fkey`, `scientific_validation_annotations_cell_detection_id_fkey`, `scientific_validation_annotations_created_by_fkey`, `scientific_validation_annotations_sample_id_fkey`, `scientific_validation_annotations_updated_by_fkey`, `scientific_validation_annotations_validation_session_id_fkey`.

CHECK: `ck_validation_annotation_exact_target`, `scientific_validation_annotations_category_check`, `scientific_validation_annotations_content_check`, `scientific_validation_annotations_target_type_check`, `scientific_validation_annotations_version_check`.

Triggers de aplicación: `trg_validation_annotation_protected`.

#### scientific_validation_classification_runs

Índices: `scientific_validation_classification_runs_pkey`.

PK: `scientific_validation_classification_runs_pkey`.

FK: `scientific_validation_classification_classification_run_id_fkey`, `scientific_validation_classification_runs_session_id_fkey`.

Triggers de aplicación: `trg_validation_classification_runs_immutable`.

#### scientific_validation_detection_runs

Índices: `scientific_validation_detection_runs_pkey`.

PK: `scientific_validation_detection_runs_pkey`.

FK: `scientific_validation_detection_runs_detection_run_id_fkey`, `scientific_validation_detection_runs_session_id_fkey`.

Triggers de aplicación: `trg_validation_detection_runs_immutable`.

#### scientific_validation_images

Índices: `scientific_validation_images_pkey`, `scientific_validation_images_session_id_sequence_number_key`.

PK: `scientific_validation_images_pkey`.

FK: `scientific_validation_images_microscopy_image_id_fkey`, `scientific_validation_images_session_id_fkey`.

UNIQUE: `scientific_validation_images_session_id_sequence_number_key`.

CHECK: `scientific_validation_images_image_sha256_check`, `scientific_validation_images_sequence_number_check`.

Triggers de aplicación: `trg_validation_images_immutable`.

#### scientific_validation_sessions

Índices: `ix_validation_sessions_creator_created`, `ix_validation_sessions_status_created`, `scientific_validation_sessions_pkey`.

PK: `scientific_validation_sessions_pkey`.

FK: `scientific_validation_sessions_archived_by_fkey`, `scientific_validation_sessions_created_by_fkey`, `scientific_validation_sessions_updated_by_fkey`.

CHECK: `ck_validation_session_archive`, `scientific_validation_sessions_datasource_check`, `scientific_validation_sessions_initial_snapshot_check`, `scientific_validation_sessions_matching_iou_threshold_check`, `scientific_validation_sessions_name_check`, `scientific_validation_sessions_protocol_key_check`, `scientific_validation_sessions_protocol_version_check`, `scientific_validation_sessions_snapshot_sha256_check`, `scientific_validation_sessions_status_check`.

Triggers de aplicación: `trg_validation_snapshot_protected`.

#### smear_analysis_summaries

Índices: `ix_smear_analysis_summaries_analysis_created`, `ix_smear_analysis_summaries_detection_created`, `ix_smear_analysis_summaries_outcome_created`, `smear_analysis_summaries_classification_run_id_key`, `smear_analysis_summaries_pkey`.

PK: `smear_analysis_summaries_pkey`.

FK: `fk_smear_summary_classification_lineage`.

UNIQUE: `smear_analysis_summaries_classification_run_id_key`.

CHECK: `ck_smear_summary_counts`, `ck_smear_summary_fraction`, `ck_smear_summary_probabilities`, `smear_analysis_summaries_aggregation_policy_snapshot_check`, `smear_analysis_summaries_classified_cell_count_check`, `smear_analysis_summaries_eligible_cell_count_check`, `smear_analysis_summaries_failed_prediction_count_check`, `smear_analysis_summaries_near_threshold_count_check`, `smear_analysis_summaries_outcome_check`, `smear_analysis_summaries_parasitized_candidate_count_check`, `smear_analysis_summaries_per_image_summary_check`, `smear_analysis_summaries_uninfected_candidate_count_check`.

Triggers de aplicación: `trg_smear_analysis_summaries_append_only`, `trg_smear_analysis_summaries_insert_state`, `trg_smear_analysis_summaries_validate`.

#### smear_slides

Índices: `ix_smear_slides_sample`, `ix_smear_slides_status_created`, `smear_slides_pkey`, `uq_smear_slides_sample_code`.

PK: `smear_slides_pkey`.

FK: `smear_slides_archived_by_fkey`, `smear_slides_created_by_fkey`, `smear_slides_sample_id_fkey`, `smear_slides_updated_by_fkey`.

UNIQUE: `uq_smear_slides_sample_code`.

CHECK: `ck_smear_slide_archive_state`, `smear_slides_metadata_json_check`, `smear_slides_slide_code_check`, `smear_slides_smear_type_check`, `smear_slides_status_check`.

#### stage2_model_publication_events

Índices: `idx_stage2_publication_events_publication`, `stage2_model_publication_events_pkey`.

PK: `stage2_model_publication_events_pkey`.

FK: `stage2_model_publication_events_publication_id_fkey`.

CHECK: `chk_stage2_publication_event_metadata`, `chk_stage2_publication_event_status`, `chk_stage2_publication_event_type`.

Triggers de aplicación: `trg_stage2_publication_events_append_only`.

#### stage2_model_publications

Índices: `idx_stage2_publication_candidates`, `stage2_model_publications_pkey`, `uq_stage2_model_publications_id_version`, `uq_stage2_publication_active_version`.

PK: `stage2_model_publications_pkey`.

FK: `fk_stage2_publication_evaluation`, `fk_stage2_publication_training`, `fk_stage2_publication_version_artifact`.

CHECK: `chk_stage2_publication_metadata`, `chk_stage2_publication_scope`, `chk_stage2_publication_state`, `chk_stage2_publication_status`.

#### synthetic_data_runs

Índices: `synthetic_data_runs_pkey`.

PK: `synthetic_data_runs_pkey`.

FK: `synthetic_data_runs_run_id_fkey`, `synthetic_data_runs_source_dataset_id_fkey`.

#### train_execution_records

Índices: `train_event_id_unique`, `train_event_sequence_unique`, `train_execution_records_pkey`.

PK: `train_execution_records_pkey`.

FK: `train_execution_records_run_id_fkey`.

CHECK: `train_event_metadata`, `train_execution_records_payload_check`.

Triggers de aplicación: `a_train_event_guard`, `train_record_guard`.

#### train_execution_revisions

Índices: `train_execution_revisions_pkey`.

PK: `train_execution_revisions_pkey`.

FK: `train_execution_revisions_attempt_id_fkey`, `train_execution_revisions_campaign_id_fkey`, `train_execution_revisions_campaign_id_revision_id_fkey`.

Restricción de trigger: `train_revision_binding_guard`.

Triggers de aplicación: `train_execution_revision_immutable`, `train_revision_binding_guard`.

#### train_execution_sessions

Índices: `train_execution_sessions_artifact_root_key`, `train_execution_sessions_attempt_id_key`, `train_execution_sessions_pkey`, `uq_global_train_active`.

PK: `train_execution_sessions_pkey`.

FK: `train_execution_sessions_attempt_id_fkey`, `train_execution_sessions_run_id_fkey`.

UNIQUE: `train_execution_sessions_artifact_root_key`, `train_execution_sessions_attempt_id_key`.

CHECK: `train_execution_sessions_check`, `train_execution_sessions_check1`, `train_execution_sessions_parent_pid_check`, `train_execution_sessions_state_check`.

Triggers de aplicación: `global_train_reservation`, `train_session_guard`.

#### training_history

Índices: `idx_training_history_run_id`, `idx_training_history_run_phase_epoch`, `training_history_pkey`.

PK: `training_history_pkey`.

FK: `training_history_run_id_fkey`.

#### user_roles

Índices: `user_roles_pkey`.

PK: `user_roles_pkey`.

FK: `user_roles_role_id_fkey`, `user_roles_user_id_fkey`.

#### users

Índices: `users_email_key`, `users_pkey`, `users_username_key`.

PK: `users_pkey`.

UNIQUE: `users_email_key`, `users_username_key`.

CHECK: `users_status_check`.

Los 832 triggers internos de integridad referencial se enumeran individualmente en `triggers` del JSON, incluyendo nombre, tabla, definición y habilitación; no son objetos omitidos del inventario.

### Secuencias

| Secuencia | Inicio / incremento / cache | Último valor | Ciclo |
| --- | --- | --- | --- |
| experiment_execution_events_id_seq | 1 / 1 / 1 | None | False |

last_value NULL no implica error: la única secuencia corresponde a una tabla vacía; no se llamó nextval ni setval.

## Riesgos y límites pendientes

- 79 FK sin cobertura por primera columna (60 RESTRICT); 109 no satisfacen la prueba conservadora de prefijo completo ordenado, válido y no parcial. No equivale a recomendar 109 índices: verificar permutaciones, métodos, consultas y cardinalidad.
- 55116 imágenes legadas carecen de dataset_version_id y dataset_materialization_id; dos raíces distintas, una oficial y otra histórica. No usar el total global para resolver el split oficial. Cero activaciones de materialización.
- La tabla models pasó de 4 a 3 filas entre la evidencia previa y posterior a la reconstrucción; la evidencia agregada no identifica la fila retirada. No se afirma preservación íntegra de models respecto del origen.
- users cambió respecto del corte de reconstrucción; el login posterior y last_login_at son evidencia compatible, pero un hash agregado no prueba que sea el único campo cambiado. Coincide íntegramente con la evidencia posterior de limpieza.
- Estadísticas recientes y sin pg_stat_statements: no inferir inutilidad de índices/vistas ni bloat a partir de contadores o tamaños. Las lecturas de esta auditoría también incrementan contadores.
- Override publica PostgreSQL en 0.0.0.0:5432 y [::]:5432 y mantiene CAPSTONE_LOCAL_EXECUTION_ENABLED=1; diferencia respecto del contrato documental, no cambiada aquí.
- Base de recuperación malaria_pre_reset3_20260929 conserva historial con datallowconn=false. Limpieza verificada únicamente en la base operativa.
- Coexisten alembic_version y schema_migrations en public; vigencia de ambos registrada, sin asumir incompatibilidad por su mera coexistencia.
- Estado READY/PASS y hashes de materialización son evidencia almacenada; no se releen bytes de archivos físicos en esta auditoría PostgreSQL.

Ninguna observación autoriza un cambio en esta etapa. Los riesgos quedan registrados para revisión posterior, sin introducir optimizaciones E10.

**E10.10.1 — BASELINE VERIFICADO.**
