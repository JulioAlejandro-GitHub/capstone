# DBV2.2 — Comparación de contrato

DBV2.2 BLOCKED — DBV2.1 CONTRACT CONFLICT

El modelo aprobado (`../dbv2_1_xai_model.md`, sección Métricas, N:M y congelación) exige insertar evaluación y miembros en una transacción, con validación diferida. El SQL aprobado declara las tablas con `xai_quantitative_evaluations.id` y `xai_evaluation_members.evaluation_id`, sin el otro campo (líneas 242 y 252; las declaraciones exactas también constan en el CSV de columnas).

Sin embargo, `../dbv2_1_target_schema.sql:2834` contiene en `dbv21_xai_evaluation_complete`:

```sql
eid:=CASE WHEN TG_TABLE_NAME='xai_quantitative_evaluations' THEN NEW.id ELSE NEW.evaluation_id END;
```

Los triggers de las líneas 5489 y 5491 conectan esa función a ambas tablas. PostgreSQL resuelve los campos de ambas ramas de la expresión antes de seleccionar el resultado. La reproducción mínima en PostgreSQL 17.9 devuelve:

- xai_quantitative_evaluations: SQLSTATE 42703, `record "new" has no field "evaluation_id"`.
- xai_evaluation_members: SQLSTATE 42703, `record "new" has no field "id"`.

Por tanto, materializar literalmente este SQL no permite la inserción N:M válida exigida por el documento XAI. Corregirlo silenciosamente produciría una función distinta de la aprobada. Se detiene DBV2.2 por las secciones 5 y 33 de la solicitud.

Resolución propuesta para decisión explícita: sustituir la expresión CASE por un IF/ELSE PL/pgSQL con una asignación separada por tabla, aprobar la corrección de DBV2.1 y revalidar sus artefactos. No se aplicó esa propuesta ni se certificó su implementación.

## Delta previo a cualquier modificación

CURRENT_V2_BASELINE vs APPROVED_DBV2.1_TARGET. Comparación de AST por identidad; los conteos siguientes son documentales, no catálogo PostgreSQL instalado. CHECK/PK/FK/UNIQUE se agrupan en constraints. Índices aquí significa CREATE INDEX explícitos. La categoría tablas compara declaraciones de columnas; los cambios en constraints e índices se enumeran aparte.

| Categoría | CURRENT | TARGET | Identidades diferentes |
|---|---:|---:|---:|
| tables | 102 | 104 | 9 |
| constraints | 952 | 950 | 87 |
| indexes | 231 | 232 | 9 |
| functions | 79 | 79 | 7 |
| triggers | 99 | 105 | 10 |
| views | 33 | 33 | 1 |

Definiciones EXPECTED/ACTUAL completas por identidad en `dbv2_2_baseline_delta.json`. No se aplicó el delta.

### tables

- REMOVE model_governance_backfill_audit
- MODIFY run_configurations
- REMOVE schema_migrations
- ADD xai_evaluation_members
- ADD xai_evaluation_protocols
- MODIFY xai_evidence
- ADD xai_method_configurations
- MODIFY xai_quantitative_evaluations
- ADD xai_region_attributions
### constraints

- MODIFY ['artifacts', 'artifacts_run_id_fkey']
- MODIFY ['dataset_split_images', 'dataset_split_images_dataset_id_fkey']
- MODIFY ['dataset_splits', 'dataset_splits_dataset_id_fkey']
- MODIFY ['environment_packages', 'environment_packages_run_id_fkey']
- MODIFY ['errors', 'errors_run_id_fkey']
- MODIFY ['execution_logs', 'execution_logs_run_id_fkey']
- MODIFY ['explainability_results', 'explainability_results_prediction_id_fkey']
- MODIFY ['explainability_results', 'explainability_results_run_id_fkey']
- REMOVE ['model_governance_backfill_audit', 'chk_model_governance_audit_after_object']
- REMOVE ['model_governance_backfill_audit', 'chk_model_governance_audit_before_object']
- REMOVE ['model_governance_backfill_audit', 'chk_model_governance_audit_event_type']
- REMOVE ['model_governance_backfill_audit', 'chk_model_governance_audit_metadata_object']
- REMOVE ['model_governance_backfill_audit', 'chk_model_governance_audit_result_status']
- REMOVE ['model_governance_backfill_audit', 'chk_model_governance_audit_reversal']
- REMOVE ['model_governance_backfill_audit', 'fk_model_governance_audit_reversal']
- REMOVE ['model_governance_backfill_audit', 'model_governance_backfill_audit_pkey']
- MODIFY ['predictions', 'predictions_dataset_id_fkey']
- MODIFY ['predictions', 'predictions_run_id_fkey']
- MODIFY ['run_checkpoint_policy', 'run_checkpoint_policy_run_id_fkey']
- MODIFY ['run_clinical_metrics', 'run_clinical_metrics_model_id_fkey']
- MODIFY ['run_clinical_metrics', 'run_clinical_metrics_run_id_fkey']
- MODIFY ['run_configurations', 'v2_run_configurations_check_d6094850fee4']
- MODIFY ['run_dataset_images', 'run_dataset_images_image_id_fkey']
- MODIFY ['run_dataset_images', 'run_dataset_images_run_id_fkey']
- MODIFY ['run_image_predictions', 'run_image_predictions_image_id_fkey']
- MODIFY ['run_image_predictions', 'run_image_predictions_run_id_fkey']
- MODIFY ['run_io_records', 'run_io_records_run_id_fkey']
- MODIFY ['run_metrics', 'run_metrics_run_id_fkey']
- MODIFY ['run_threshold_calibration', 'ck_v2_calibration_val']
- MODIFY ['run_threshold_calibration', 'run_threshold_calibration_run_id_fkey']
- MODIFY ['runs', 'runs_dataset_id_fkey']
- MODIFY ['runs', 'runs_experiment_id_fkey']
- MODIFY ['runs', 'runs_model_id_fkey']
- REMOVE ['schema_migrations', 'chk_schema_migrations_checksum_sha256']
- REMOVE ['schema_migrations', 'schema_migrations_pkey']
- MODIFY ['synthetic_data_runs', 'synthetic_data_runs_run_id_fkey']
- MODIFY ['synthetic_data_runs', 'synthetic_data_runs_source_dataset_id_fkey']
- MODIFY ['training_history', 'training_history_run_id_fkey']
- MODIFY ['xai_artifacts', 'v2_xai_artifacts_check_eb359eee6311']
- ADD ['xai_evaluation_members', 'ck_xai_member_role']
- ADD ['xai_evaluation_members', 'fk_xai_member_evaluation']
- ADD ['xai_evaluation_members', 'fk_xai_member_evidence']
- ADD ['xai_evaluation_members', 'xai_evaluation_members_pkey']
- ADD ['xai_evaluation_protocols', 'ck_protocol_hash_xai_protocol']
- ADD ['xai_evaluation_protocols', 'ck_xai_evaluation_protocols_parameters']
- ADD ['xai_evaluation_protocols', 'ck_xai_protocol_identity']
- ADD ['xai_evaluation_protocols', 'uq_xai_protocol_hash']
- ADD ['xai_evaluation_protocols', 'uq_xai_protocol_metric']
- ADD ['xai_evaluation_protocols', 'xai_evaluation_protocols_pkey']
- ADD ['xai_evidence', 'ck_xai_prediction_score']
- ADD ['xai_evidence', 'ck_xai_provisional_checkpoint']
- ADD ['xai_evidence', 'fk_xai_method_configuration']
- REMOVE ['xai_evidence', 'v2_xai_evidence_check_0b0c8b6b4dc8']
- REMOVE ['xai_evidence', 'v2_xai_evidence_check_3321a4aaab96']
- REMOVE ['xai_evidence', 'v2_xai_evidence_check_5e31bead5512']
- REMOVE ['xai_evidence', 'v2_xai_evidence_check_94a05a1bd653']
- REMOVE ['xai_evidence', 'v2_xai_evidence_check_f1eec802dae7']
- ADD ['xai_method_configurations', 'ck_configuration_hash_xai_method']
- ADD ['xai_method_configurations', 'ck_xai_method_configurations_parameters']
- ADD ['xai_method_configurations', 'ck_xai_method_identity']
- ADD ['xai_method_configurations', 'uq_xai_method_configuration_hash']
- ADD ['xai_method_configurations', 'xai_method_configurations_pkey']
- ADD ['xai_quantitative_evaluations', 'ck_xai_details_tuple']
- ADD ['xai_quantitative_evaluations', 'ck_xai_membership_hash']
- ADD ['xai_quantitative_evaluations', 'ck_xai_metric_defined']
- ADD ['xai_quantitative_evaluations', 'ck_xai_reference_tuple']
- ADD ['xai_quantitative_evaluations', 'ck_xai_sample_count']
- ADD ['xai_quantitative_evaluations', 'fk_xai_metric_protocol']
- ADD ['xai_quantitative_evaluations', 'fk_xai_reference_annotation']
- REMOVE ['xai_quantitative_evaluations', 'v2_xai_quantitative_evaluations_check_00fb2e80d9b2']
- REMOVE ['xai_quantitative_evaluations', 'v2_xai_quantitative_evaluations_check_0652739ad678']
- REMOVE ['xai_quantitative_evaluations', 'v2_xai_quantitative_evaluations_check_21cdf11ae847']
- REMOVE ['xai_quantitative_evaluations', 'v2_xai_quantitative_evaluations_check_4778c641fdd8']
- REMOVE ['xai_quantitative_evaluations', 'v2_xai_quantitative_evaluations_check_4d27ef172e06']
- REMOVE ['xai_quantitative_evaluations', 'v2_xai_quantitative_evaluations_check_599c4acec50d']
- REMOVE ['xai_quantitative_evaluations', 'v2_xai_quantitative_evaluations_check_655d0810bc12']
- REMOVE ['xai_quantitative_evaluations', 'v2_xai_quantitative_evaluations_check_887951a61b99']
- REMOVE ['xai_quantitative_evaluations', 'v2_xai_quantitative_evaluations_check_91eb3dc34528']
- REMOVE ['xai_quantitative_evaluations', 'v2_xai_quantitative_evaluations_check_bcd82843d42a']
- REMOVE ['xai_quantitative_evaluations', 'v2_xai_quantitative_evaluations_check_ffe78f63e439']
- REMOVE ['xai_quantitative_evaluations', 'v2_xai_quantitative_evaluations_foreign_159f07174869']
- REMOVE ['xai_quantitative_evaluations', 'v2_xai_quantitative_evaluations_foreign_4b080b42e888']
- REMOVE ['xai_quantitative_evaluations', 'v2_xai_quantitative_evaluations_foreign_851f5820eb59']
- REMOVE ['xai_quantitative_evaluations', 'v2_xai_quantitative_evaluations_unique_ecdefdc0d70a']
- ADD ['xai_region_attributions', 'ck_xai_region_domain']
- ADD ['xai_region_attributions', 'fk_xai_region_evidence']
- ADD ['xai_region_attributions', 'xai_region_attributions_pkey']
### indexes

- REMOVE idx_model_governance_audit_batch
- REMOVE idx_model_governance_audit_record
- REMOVE idx_model_governance_audit_reversal
- MODIFY ix_xai_evaluation
- ADD ix_xai_member_evidence
- ADD ix_xai_method_configuration
- ADD ix_xai_metric_protocol
- ADD ix_xai_reference_annotation
- MODIFY ix_xai_same_image
### functions

- ADD public.dbv21_xai_configuration_guard
- ADD public.dbv21_xai_evaluation_complete
- REMOVE public.prevent_model_governance_audit_mutation
- MODIFY public.v2_calibration_pair_guard
- MODIFY public.v2_configuration_guard
- REMOVE public.v2_xai_comparison_guard
- MODIFY public.v2_xai_lineage_guard
### triggers

- REMOVE ['model_governance_backfill_audit', 'trg_model_governance_audit_append_only']
- ADD ['xai_evaluation_members', 'dbv21_immutable']
- ADD ['xai_evaluation_members', 'dbv21_xai_evaluation_complete']
- ADD ['xai_evaluation_protocols', 'dbv21_configuration_guard']
- ADD ['xai_evaluation_protocols', 'dbv21_immutable']
- ADD ['xai_method_configurations', 'dbv21_configuration_guard']
- ADD ['xai_method_configurations', 'dbv21_immutable']
- ADD ['xai_quantitative_evaluations', 'dbv21_xai_evaluation_complete']
- REMOVE ['xai_quantitative_evaluations', 'v2_xai_comparison_guard']
- ADD ['xai_region_attributions', 'dbv21_immutable']
### views

- MODIFY vw_v2_xai_comparison

Comparación catálogo PostgreSQL ↔ DBV2.1: NOT RUN — bloqueada antes de modificar/instalar baseline.
