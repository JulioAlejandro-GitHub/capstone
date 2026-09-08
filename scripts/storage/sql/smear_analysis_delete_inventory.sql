BEGIN;
SET TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '30s';
SET LOCAL lock_timeout = '5s';
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SHOW transaction_read_only;
SET LOCAL jit = off;
-- Inventario B.3C.2. Alcance: análisis e ingestas persistidas y su linaje exacto.
-- Los candidatos NO autorizan una purga: cualquier FAIL o auditoría ambigua la bloquea.
-- Filas sin relación demostrada con un análisis se preservan y se cuentan aparte.
-- PK/FK verificadas en PostgreSQL 17.9, Alembic 20260901_01.
-- Cantidades observadas: ver informe adjunto; ningún conteo está codificado en la selección.
-- 1. cell_explanations; PK id; pertenencia definida por CTE target_cell_explanations; cantidad observada 13.
-- FOREIGN KEY (cell_prediction_id) REFERENCES cell_predictions(id) ON DELETE RESTRICT
-- 2. cell_classification_reviews; PK id; pertenencia definida por CTE target_cell_classification_reviews; cantidad observada 4.
-- FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT
-- FOREIGN KEY (cell_prediction_id) REFERENCES cell_predictions(id) ON DELETE RESTRICT
-- 3. cell_classification_events; PK id; pertenencia definida por CTE target_cell_classification_events; cantidad observada 2191.
-- FOREIGN KEY (cell_detection_id) REFERENCES cell_detections(id) ON DELETE RESTRICT
-- FOREIGN KEY (classification_run_id) REFERENCES cell_classification_runs(id) ON DELETE RESTRICT
-- FOREIGN KEY (cell_prediction_id, classification_run_id) REFERENCES cell_predictions(id, classification_run_id) ON DELETE RESTRICT
-- 4. smear_analysis_summaries; PK id; pertenencia definida por CTE target_smear_analysis_summaries; cantidad observada 34.
-- FOREIGN KEY (classification_run_id, analysis_run_id, detection_run_id) REFERENCES cell_classification_runs(id, analysis_run_id, detection_run_id) ON DELETE RESTRICT
-- 5. cell_predictions; PK id; pertenencia definida por CTE target_cell_predictions; cantidad observada 1901.
-- FOREIGN KEY (classification_input_id, classification_run_id, cell_detection_id, crop_id) REFERENCES cell_classification_inputs(id, classification_run_id, cell_detection_id, crop_id) ON DELETE RESTRICT
-- 6. cell_classification_inputs; PK id; pertenencia definida por CTE target_cell_classification_inputs; cantidad observada 2291.
-- FOREIGN KEY (crop_id, cell_detection_id) REFERENCES cell_crops(id, cell_detection_id) ON DELETE RESTRICT
-- FOREIGN KEY (cell_detection_id, detection_run_id, microscopy_image_id) REFERENCES cell_detections(id, detection_run_id, microscopy_image_id) ON DELETE RESTRICT
-- FOREIGN KEY (classification_run_id, detection_run_id) REFERENCES cell_classification_runs(id, detection_run_id) ON DELETE RESTRICT
-- 7. cell_classification_runs; PK id; pertenencia definida por CTE target_cell_classification_runs; cantidad observada 41.
-- FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE RESTRICT
-- FOREIGN KEY (retry_of_run_id) REFERENCES cell_classification_runs(id) ON DELETE RESTRICT
-- FOREIGN KEY (production_model_id, model_registry_id) REFERENCES deployed_model_versions(id, model_version_id) ON DELETE RESTRICT
-- FOREIGN KEY (detection_run_id, analysis_run_id) REFERENCES cell_detection_runs(id, analysis_run_id) ON DELETE RESTRICT
-- FOREIGN KEY (stage2_publication_id, model_registry_id) REFERENCES stage2_model_publications(id, model_version_id) ON DELETE RESTRICT
-- 8. scientific_reviews; PK id; pertenencia definida por CTE target_scientific_reviews; cantidad observada 11.
-- FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT
-- FOREIGN KEY (entity_id) REFERENCES cell_detections(id) ON DELETE RESTRICT
-- 9. cell_crops; PK id; pertenencia definida por CTE target_cell_crops; cantidad observada 2505.
-- FOREIGN KEY (cell_detection_id) REFERENCES cell_detections(id) ON DELETE RESTRICT
-- 10. cell_detection_events; PK id; pertenencia definida por CTE target_cell_detection_events; cantidad observada 182.
-- FOREIGN KEY (detection_run_id) REFERENCES cell_detection_runs(id) ON DELETE RESTRICT
-- FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images(id) ON DELETE RESTRICT
-- 11. cell_detections; PK id; pertenencia definida por CTE target_cell_detections; cantidad observada 2505.
-- FOREIGN KEY (connected_component_id, detection_run_id, analysis_run_image_id, microscopy_image_id) REFERENCES image_connected_components(id, detection_run_id, analysis_run_image_id, microscopy_image_id) ON DELETE RESTRICT
-- FOREIGN KEY (detection_run_id, analysis_run_id) REFERENCES cell_detection_runs(id, analysis_run_id) ON DELETE RESTRICT
-- 12. image_connected_components; PK id; pertenencia definida por CTE target_image_connected_components; cantidad observada 3718.
-- FOREIGN KEY (detection_run_id, analysis_run_id) REFERENCES cell_detection_runs(id, analysis_run_id) ON DELETE RESTRICT
-- FOREIGN KEY (analysis_run_image_id, analysis_run_id, microscopy_image_id) REFERENCES microscopy_analysis_run_images(id, analysis_run_id, microscopy_image_id) ON DELETE RESTRICT
-- 13. cell_detection_runs; PK id; pertenencia definida por CTE target_cell_detection_runs; cantidad observada 45.
-- FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT
-- FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE RESTRICT
-- 14. quality_gate_decisions; PK id; pertenencia definida por CTE target_quality_gate_decisions; cantidad observada 4.
-- FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT
-- FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT
-- 15. quality_assessment_queue_items; PK id; pertenencia definida por CTE target_quality_assessment_queue_items; cantidad observada 50.
-- FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT
-- FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE RESTRICT
-- 16. microscopy_analysis_events; PK id; pertenencia definida por CTE target_microscopy_analysis_events; cantidad observada 258.
-- FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT
-- FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images(id) ON DELETE RESTRICT
-- 17. image_quality_assessments; PK id; pertenencia definida por CTE target_image_quality_assessments; cantidad observada 52.
-- FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT
-- FOREIGN KEY (analysis_run_image_id, analysis_run_id, microscopy_image_id) REFERENCES microscopy_analysis_run_images(id, analysis_run_id, microscopy_image_id) ON DELETE RESTRICT
-- FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images(id) ON DELETE RESTRICT
-- 18. microscopy_analysis_run_images; PK id; pertenencia definida por CTE target_microscopy_analysis_run_images; cantidad observada 52.
-- FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT
-- FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images(id) ON DELETE RESTRICT
-- 19. microscopy_analysis_runs; PK id; pertenencia definida por CTE target_microscopy_analysis_runs; cantidad observada 50.
-- FOREIGN KEY (case_id) REFERENCES scientific_cases(id) ON DELETE RESTRICT
-- FOREIGN KEY (ingestion_batch_id) REFERENCES image_ingestion_batches(id) ON DELETE RESTRICT
-- FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE RESTRICT
-- FOREIGN KEY (sample_id) REFERENCES blood_samples(id) ON DELETE RESTRICT
-- FOREIGN KEY (slide_id) REFERENCES smear_slides(id) ON DELETE RESTRICT
-- FOREIGN KEY (subject_id) REFERENCES research_subjects(id) ON DELETE RESTRICT
-- 20. microscopy_images; PK id; pertenencia definida por CTE target_microscopy_images; cantidad observada 59.
-- FOREIGN KEY (archived_by) REFERENCES users(id) ON DELETE RESTRICT
-- FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
-- FOREIGN KEY (ingestion_batch_id) REFERENCES image_ingestion_batches(id) ON DELETE RESTRICT
-- FOREIGN KEY (slide_id) REFERENCES smear_slides(id) ON DELETE RESTRICT
-- FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT
-- 21. image_ingestion_batches; PK id; pertenencia definida por CTE target_image_ingestion_batches; cantidad observada 53.
-- FOREIGN KEY (case_id) REFERENCES scientific_cases(id) ON DELETE RESTRICT
-- FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
-- FOREIGN KEY (sample_id) REFERENCES blood_samples(id) ON DELETE RESTRICT
-- FOREIGN KEY (slide_id) REFERENCES smear_slides(id) ON DELETE RESTRICT
-- FOREIGN KEY (subject_id) REFERENCES research_subjects(id) ON DELETE RESTRICT
-- 22. smear_slides; PK id; pertenencia definida por CTE target_smear_slides; cantidad observada 53.
-- FOREIGN KEY (archived_by) REFERENCES users(id) ON DELETE RESTRICT
-- FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
-- FOREIGN KEY (sample_id) REFERENCES blood_samples(id) ON DELETE RESTRICT
-- FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT
-- 23. blood_samples; PK id; pertenencia definida por CTE target_blood_samples; cantidad observada 53.
-- FOREIGN KEY (archived_by) REFERENCES users(id) ON DELETE RESTRICT
-- FOREIGN KEY (case_id) REFERENCES scientific_cases(id) ON DELETE RESTRICT
-- FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
-- FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT
-- 24. scientific_cases; PK id; pertenencia definida por CTE target_scientific_cases; cantidad observada 53.
-- FOREIGN KEY (archived_by) REFERENCES users(id) ON DELETE RESTRICT
-- FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
-- FOREIGN KEY (subject_id) REFERENCES research_subjects(id) ON DELETE RESTRICT
-- FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT
-- 25. research_subjects; PK id; pertenencia definida por CTE target_research_subjects; cantidad observada 53.
-- FOREIGN KEY (archived_by) REFERENCES users(id) ON DELETE RESTRICT
-- FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT
-- FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT
-- Autorreferencia cell_classification_runs.retry_of_run_id: descendientes antes que origen;
-- mismo DELETE por conjunto completo satisface la FK; por fila usar profundidad descendente.

-- REPORT summary
WITH RECURSIVE
target_image_ingestion_batches AS (SELECT r.* FROM public.image_ingestion_batches r),
target_microscopy_analysis_runs AS (SELECT r.* FROM public.microscopy_analysis_runs r),
target_microscopy_analysis_run_images AS (SELECT r.* FROM public.microscopy_analysis_run_images r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_cell_detection_runs AS (SELECT r.* FROM public.cell_detection_runs r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_cell_detections AS (SELECT r.* FROM public.cell_detections r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_image_connected_components AS (SELECT r.* FROM public.image_connected_components r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_cell_crops AS (SELECT r.* FROM public.cell_crops r JOIN target_cell_detections p ON r.cell_detection_id=p.id),
target_cell_detection_events AS (SELECT r.* FROM public.cell_detection_events r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_scientific_reviews AS (SELECT r.* FROM public.scientific_reviews r JOIN target_cell_detections p ON r.entity_id=p.id),
target_cell_classification_runs AS (SELECT r.* FROM public.cell_classification_runs r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_cell_classification_inputs AS (SELECT r.* FROM public.cell_classification_inputs r JOIN target_cell_classification_runs p ON r.classification_run_id=p.id),
target_cell_predictions AS (SELECT r.* FROM public.cell_predictions r JOIN target_cell_classification_inputs p ON r.classification_input_id=p.id),
target_cell_explanations AS (SELECT r.* FROM public.cell_explanations r JOIN target_cell_predictions p ON r.cell_prediction_id=p.id),
target_cell_classification_reviews AS (SELECT r.* FROM public.cell_classification_reviews r JOIN target_cell_predictions p ON r.cell_prediction_id=p.id),
target_cell_classification_events AS (SELECT r.* FROM public.cell_classification_events r JOIN target_cell_classification_runs p ON r.classification_run_id=p.id),
target_smear_analysis_summaries AS (SELECT r.* FROM public.smear_analysis_summaries r JOIN target_cell_classification_runs p ON r.classification_run_id=p.id),
target_image_quality_assessments AS (SELECT r.* FROM public.image_quality_assessments r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_quality_gate_decisions AS (SELECT r.* FROM public.quality_gate_decisions r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_quality_assessment_queue_items AS (SELECT r.* FROM public.quality_assessment_queue_items r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_microscopy_analysis_events AS (SELECT r.* FROM public.microscopy_analysis_events r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_microscopy_images AS (SELECT r.* FROM public.microscopy_images r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_run_images p WHERE p.microscopy_image_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.id=r.ingestion_batch_id)),
target_smear_slides AS (SELECT r.* FROM public.smear_slides r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.slide_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.slide_id=r.id)),
target_blood_samples AS (SELECT r.* FROM public.blood_samples r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.sample_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.sample_id=r.id)),
target_scientific_cases AS (SELECT r.* FROM public.scientific_cases r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.case_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.case_id=r.id)),
target_research_subjects AS (SELECT r.* FROM public.research_subjects r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.subject_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.subject_id=r.id)),
table_catalog(delete_order,table_name,primary_key_column,selection_reason) AS (VALUES (1,'cell_explanations','id','JOIN cell_prediction_id al conjunto cell_predictions'),
(2,'cell_classification_reviews','id','JOIN cell_prediction_id al conjunto cell_predictions'),
(3,'cell_classification_events','id','JOIN classification_run_id al conjunto cell_classification_runs'),
(4,'smear_analysis_summaries','id','JOIN classification_run_id al conjunto cell_classification_runs'),
(5,'cell_predictions','id','JOIN classification_input_id al conjunto cell_classification_inputs'),
(6,'cell_classification_inputs','id','JOIN classification_run_id al conjunto cell_classification_runs'),
(7,'cell_classification_runs','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(8,'scientific_reviews','id','JOIN entity_id al conjunto cell_detections'),
(9,'cell_crops','id','JOIN cell_detection_id al conjunto cell_detections'),
(10,'cell_detection_events','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(11,'cell_detections','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(12,'image_connected_components','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(13,'cell_detection_runs','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(14,'quality_gate_decisions','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(15,'quality_assessment_queue_items','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(16,'microscopy_analysis_events','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(17,'image_quality_assessments','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(18,'microscopy_analysis_run_images','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(19,'microscopy_analysis_runs','id','Raíz del flujo de ingesta o análisis'),
(20,'microscopy_images','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(21,'image_ingestion_batches','id','Raíz del flujo de ingesta o análisis'),
(22,'smear_slides','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(23,'blood_samples','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(24,'scientific_cases','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(25,'research_subjects','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga')),
targets AS (SELECT 1 delete_order, 'cell_explanations'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_predictions'::text parent_table, r.cell_prediction_id::text parent_record_id, 'JOIN cell_prediction_id al conjunto cell_predictions'::text selection_reason, jsonb_build_array(r.cell_prediction_id,r.heatmap_storage_key,r.id,r.overlay_storage_key,r.status) fingerprint_values FROM target_cell_explanations r
UNION ALL
SELECT 2 delete_order, 'cell_classification_reviews'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_predictions'::text parent_table, r.cell_prediction_id::text parent_record_id, 'JOIN cell_prediction_id al conjunto cell_predictions'::text selection_reason, jsonb_build_array(r.actor_user_id,r.cell_prediction_id,r.id) fingerprint_values FROM target_cell_classification_reviews r
UNION ALL
SELECT 3 delete_order, 'cell_classification_events'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_runs'::text parent_table, r.classification_run_id::text parent_record_id, 'JOIN classification_run_id al conjunto cell_classification_runs'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.cell_prediction_id,r.classification_run_id,r.id,r.status) fingerprint_values FROM target_cell_classification_events r
UNION ALL
SELECT 4 delete_order, 'smear_analysis_summaries'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_runs'::text parent_table, r.classification_run_id::text parent_record_id, 'JOIN classification_run_id al conjunto cell_classification_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.classification_run_id,r.detection_run_id,r.id) fingerprint_values FROM target_smear_analysis_summaries r
UNION ALL
SELECT 5 delete_order, 'cell_predictions'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_inputs'::text parent_table, r.classification_input_id::text parent_record_id, 'JOIN classification_input_id al conjunto cell_classification_inputs'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.classification_input_id,r.classification_run_id,r.crop_id,r.id) fingerprint_values FROM target_cell_predictions r
UNION ALL
SELECT 6 delete_order, 'cell_classification_inputs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_runs'::text parent_table, r.classification_run_id::text parent_record_id, 'JOIN classification_run_id al conjunto cell_classification_runs'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.classification_run_id,r.crop_id,r.detection_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_cell_classification_inputs r
UNION ALL
SELECT 7 delete_order, 'cell_classification_runs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.detection_run_id,r.id,r.model_registry_id,r.production_model_id,r.requested_by,r.retry_of_run_id,r.stage2_publication_id,r.status) fingerprint_values FROM target_cell_classification_runs r
UNION ALL
SELECT 8 delete_order, 'scientific_reviews'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detections'::text parent_table, r.entity_id::text parent_record_id, 'JOIN entity_id al conjunto cell_detections'::text selection_reason, jsonb_build_array(r.actor_user_id,r.entity_id,r.id) fingerprint_values FROM target_scientific_reviews r
UNION ALL
SELECT 9 delete_order, 'cell_crops'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detections'::text parent_table, r.cell_detection_id::text parent_record_id, 'JOIN cell_detection_id al conjunto cell_detections'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.id,r.relative_storage_key) fingerprint_values FROM target_cell_crops r
UNION ALL
SELECT 10 delete_order, 'cell_detection_events'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.detection_run_id,r.id,r.microscopy_image_id,r.status) fingerprint_values FROM target_cell_detection_events r
UNION ALL
SELECT 11 delete_order, 'cell_detections'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.analysis_run_image_id,r.connected_component_id,r.detection_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_cell_detections r
UNION ALL
SELECT 12 delete_order, 'image_connected_components'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.analysis_run_image_id,r.detection_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_image_connected_components r
UNION ALL
SELECT 13 delete_order, 'cell_detection_runs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.requested_by,r.status) fingerprint_values FROM target_cell_detection_runs r
UNION ALL
SELECT 14 delete_order, 'quality_gate_decisions'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.actor_user_id,r.analysis_run_id,r.id) fingerprint_values FROM target_quality_gate_decisions r
UNION ALL
SELECT 15 delete_order, 'quality_assessment_queue_items'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.requested_by,r.status) fingerprint_values FROM target_quality_assessment_queue_items r
UNION ALL
SELECT 16 delete_order, 'microscopy_analysis_events'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.microscopy_image_id,r.status) fingerprint_values FROM target_microscopy_analysis_events r
UNION ALL
SELECT 17 delete_order, 'image_quality_assessments'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.analysis_run_image_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_image_quality_assessments r
UNION ALL
SELECT 18 delete_order, 'microscopy_analysis_run_images'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_microscopy_analysis_run_images r
UNION ALL
SELECT 19 delete_order, 'microscopy_analysis_runs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'image_ingestion_batches'::text parent_table, r.ingestion_batch_id::text parent_record_id, 'Raíz del flujo de ingesta o análisis'::text selection_reason, jsonb_build_array(r.case_id,r.id,r.ingestion_batch_id,r.requested_by,r.run_status,r.sample_id,r.slide_id,r.subject_id) fingerprint_values FROM target_microscopy_analysis_runs r
UNION ALL
SELECT 20 delete_order, 'microscopy_images'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'smear_slides'::text parent_table, r.slide_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.ingestion_batch_id,r.slide_id,r.status,r.storage_key,r.updated_by) fingerprint_values FROM target_microscopy_images r
UNION ALL
SELECT 21 delete_order, 'image_ingestion_batches'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'smear_slides'::text parent_table, r.slide_id::text parent_record_id, 'Raíz del flujo de ingesta o análisis'::text selection_reason, jsonb_build_array(r.case_id,r.created_by,r.id,r.sample_id,r.slide_id,r.status,r.subject_id) fingerprint_values FROM target_image_ingestion_batches r
UNION ALL
SELECT 22 delete_order, 'smear_slides'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'blood_samples'::text parent_table, r.sample_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.sample_id,r.status,r.updated_by) fingerprint_values FROM target_smear_slides r
UNION ALL
SELECT 23 delete_order, 'blood_samples'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'scientific_cases'::text parent_table, r.case_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.case_id,r.created_by,r.id,r.status,r.updated_by) fingerprint_values FROM target_blood_samples r
UNION ALL
SELECT 24 delete_order, 'scientific_cases'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'research_subjects'::text parent_table, r.subject_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.source_type,r.status,r.subject_id,r.updated_by) fingerprint_values FROM target_scientific_cases r
UNION ALL
SELECT 25 delete_order, 'research_subjects'::text table_name, 'id'::text primary_key_column, r.id::text record_id, NULL::text parent_table, NULL::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.status,r.updated_by) fingerprint_values FROM target_research_subjects r),
clinical_storage AS (SELECT 'microscopy_images'::text source_table,id::text record_id,'storage_key'::text storage_column,storage_key::text storage_key,file_size_bytes expected_size,sha256::text expected_sha256,'microscopy_images'::text clinical_entity_type FROM target_microscopy_images WHERE storage_key IS NOT NULL UNION ALL SELECT 'cell_crops'::text source_table,id::text record_id,'relative_storage_key'::text storage_column,relative_storage_key::text storage_key,file_size_bytes expected_size,sha256::text expected_sha256,'cell_crops'::text clinical_entity_type FROM target_cell_crops WHERE relative_storage_key IS NOT NULL UNION ALL SELECT 'cell_explanations'::text source_table,id::text record_id,'heatmap_storage_key'::text storage_column,heatmap_storage_key::text storage_key,heatmap_file_size_bytes expected_size,heatmap_sha256::text expected_sha256,'cell_explanations'::text clinical_entity_type FROM target_cell_explanations WHERE heatmap_storage_key IS NOT NULL UNION ALL SELECT 'cell_explanations'::text source_table,id::text record_id,'overlay_storage_key'::text storage_column,overlay_storage_key::text storage_key,overlay_file_size_bytes expected_size,overlay_sha256::text expected_sha256,'cell_explanations'::text clinical_entity_type FROM target_cell_explanations WHERE overlay_storage_key IS NOT NULL),
clinical_evidence AS MATERIALIZED (SELECT record_id AS value FROM targets UNION SELECT storage_key FROM clinical_storage)
SELECT c.delete_order,c.table_name,c.primary_key_column,count(t.record_id) target_count,c.selection_reason FROM table_catalog c LEFT JOIN targets t USING(table_name) GROUP BY c.delete_order,c.table_name,c.primary_key_column,c.selection_reason ORDER BY c.delete_order,c.table_name;

-- REPORT exact_ids
WITH RECURSIVE
target_image_ingestion_batches AS (SELECT r.* FROM public.image_ingestion_batches r),
target_microscopy_analysis_runs AS (SELECT r.* FROM public.microscopy_analysis_runs r),
target_microscopy_analysis_run_images AS (SELECT r.* FROM public.microscopy_analysis_run_images r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_cell_detection_runs AS (SELECT r.* FROM public.cell_detection_runs r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_cell_detections AS (SELECT r.* FROM public.cell_detections r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_image_connected_components AS (SELECT r.* FROM public.image_connected_components r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_cell_crops AS (SELECT r.* FROM public.cell_crops r JOIN target_cell_detections p ON r.cell_detection_id=p.id),
target_cell_detection_events AS (SELECT r.* FROM public.cell_detection_events r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_scientific_reviews AS (SELECT r.* FROM public.scientific_reviews r JOIN target_cell_detections p ON r.entity_id=p.id),
target_cell_classification_runs AS (SELECT r.* FROM public.cell_classification_runs r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_cell_classification_inputs AS (SELECT r.* FROM public.cell_classification_inputs r JOIN target_cell_classification_runs p ON r.classification_run_id=p.id),
target_cell_predictions AS (SELECT r.* FROM public.cell_predictions r JOIN target_cell_classification_inputs p ON r.classification_input_id=p.id),
target_cell_explanations AS (SELECT r.* FROM public.cell_explanations r JOIN target_cell_predictions p ON r.cell_prediction_id=p.id),
target_cell_classification_reviews AS (SELECT r.* FROM public.cell_classification_reviews r JOIN target_cell_predictions p ON r.cell_prediction_id=p.id),
target_cell_classification_events AS (SELECT r.* FROM public.cell_classification_events r JOIN target_cell_classification_runs p ON r.classification_run_id=p.id),
target_smear_analysis_summaries AS (SELECT r.* FROM public.smear_analysis_summaries r JOIN target_cell_classification_runs p ON r.classification_run_id=p.id),
target_image_quality_assessments AS (SELECT r.* FROM public.image_quality_assessments r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_quality_gate_decisions AS (SELECT r.* FROM public.quality_gate_decisions r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_quality_assessment_queue_items AS (SELECT r.* FROM public.quality_assessment_queue_items r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_microscopy_analysis_events AS (SELECT r.* FROM public.microscopy_analysis_events r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_microscopy_images AS (SELECT r.* FROM public.microscopy_images r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_run_images p WHERE p.microscopy_image_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.id=r.ingestion_batch_id)),
target_smear_slides AS (SELECT r.* FROM public.smear_slides r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.slide_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.slide_id=r.id)),
target_blood_samples AS (SELECT r.* FROM public.blood_samples r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.sample_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.sample_id=r.id)),
target_scientific_cases AS (SELECT r.* FROM public.scientific_cases r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.case_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.case_id=r.id)),
target_research_subjects AS (SELECT r.* FROM public.research_subjects r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.subject_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.subject_id=r.id)),
table_catalog(delete_order,table_name,primary_key_column,selection_reason) AS (VALUES (1,'cell_explanations','id','JOIN cell_prediction_id al conjunto cell_predictions'),
(2,'cell_classification_reviews','id','JOIN cell_prediction_id al conjunto cell_predictions'),
(3,'cell_classification_events','id','JOIN classification_run_id al conjunto cell_classification_runs'),
(4,'smear_analysis_summaries','id','JOIN classification_run_id al conjunto cell_classification_runs'),
(5,'cell_predictions','id','JOIN classification_input_id al conjunto cell_classification_inputs'),
(6,'cell_classification_inputs','id','JOIN classification_run_id al conjunto cell_classification_runs'),
(7,'cell_classification_runs','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(8,'scientific_reviews','id','JOIN entity_id al conjunto cell_detections'),
(9,'cell_crops','id','JOIN cell_detection_id al conjunto cell_detections'),
(10,'cell_detection_events','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(11,'cell_detections','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(12,'image_connected_components','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(13,'cell_detection_runs','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(14,'quality_gate_decisions','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(15,'quality_assessment_queue_items','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(16,'microscopy_analysis_events','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(17,'image_quality_assessments','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(18,'microscopy_analysis_run_images','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(19,'microscopy_analysis_runs','id','Raíz del flujo de ingesta o análisis'),
(20,'microscopy_images','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(21,'image_ingestion_batches','id','Raíz del flujo de ingesta o análisis'),
(22,'smear_slides','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(23,'blood_samples','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(24,'scientific_cases','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(25,'research_subjects','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga')),
targets AS (SELECT 1 delete_order, 'cell_explanations'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_predictions'::text parent_table, r.cell_prediction_id::text parent_record_id, 'JOIN cell_prediction_id al conjunto cell_predictions'::text selection_reason, jsonb_build_array(r.cell_prediction_id,r.heatmap_storage_key,r.id,r.overlay_storage_key,r.status) fingerprint_values FROM target_cell_explanations r
UNION ALL
SELECT 2 delete_order, 'cell_classification_reviews'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_predictions'::text parent_table, r.cell_prediction_id::text parent_record_id, 'JOIN cell_prediction_id al conjunto cell_predictions'::text selection_reason, jsonb_build_array(r.actor_user_id,r.cell_prediction_id,r.id) fingerprint_values FROM target_cell_classification_reviews r
UNION ALL
SELECT 3 delete_order, 'cell_classification_events'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_runs'::text parent_table, r.classification_run_id::text parent_record_id, 'JOIN classification_run_id al conjunto cell_classification_runs'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.cell_prediction_id,r.classification_run_id,r.id,r.status) fingerprint_values FROM target_cell_classification_events r
UNION ALL
SELECT 4 delete_order, 'smear_analysis_summaries'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_runs'::text parent_table, r.classification_run_id::text parent_record_id, 'JOIN classification_run_id al conjunto cell_classification_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.classification_run_id,r.detection_run_id,r.id) fingerprint_values FROM target_smear_analysis_summaries r
UNION ALL
SELECT 5 delete_order, 'cell_predictions'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_inputs'::text parent_table, r.classification_input_id::text parent_record_id, 'JOIN classification_input_id al conjunto cell_classification_inputs'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.classification_input_id,r.classification_run_id,r.crop_id,r.id) fingerprint_values FROM target_cell_predictions r
UNION ALL
SELECT 6 delete_order, 'cell_classification_inputs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_runs'::text parent_table, r.classification_run_id::text parent_record_id, 'JOIN classification_run_id al conjunto cell_classification_runs'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.classification_run_id,r.crop_id,r.detection_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_cell_classification_inputs r
UNION ALL
SELECT 7 delete_order, 'cell_classification_runs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.detection_run_id,r.id,r.model_registry_id,r.production_model_id,r.requested_by,r.retry_of_run_id,r.stage2_publication_id,r.status) fingerprint_values FROM target_cell_classification_runs r
UNION ALL
SELECT 8 delete_order, 'scientific_reviews'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detections'::text parent_table, r.entity_id::text parent_record_id, 'JOIN entity_id al conjunto cell_detections'::text selection_reason, jsonb_build_array(r.actor_user_id,r.entity_id,r.id) fingerprint_values FROM target_scientific_reviews r
UNION ALL
SELECT 9 delete_order, 'cell_crops'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detections'::text parent_table, r.cell_detection_id::text parent_record_id, 'JOIN cell_detection_id al conjunto cell_detections'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.id,r.relative_storage_key) fingerprint_values FROM target_cell_crops r
UNION ALL
SELECT 10 delete_order, 'cell_detection_events'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.detection_run_id,r.id,r.microscopy_image_id,r.status) fingerprint_values FROM target_cell_detection_events r
UNION ALL
SELECT 11 delete_order, 'cell_detections'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.analysis_run_image_id,r.connected_component_id,r.detection_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_cell_detections r
UNION ALL
SELECT 12 delete_order, 'image_connected_components'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.analysis_run_image_id,r.detection_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_image_connected_components r
UNION ALL
SELECT 13 delete_order, 'cell_detection_runs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.requested_by,r.status) fingerprint_values FROM target_cell_detection_runs r
UNION ALL
SELECT 14 delete_order, 'quality_gate_decisions'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.actor_user_id,r.analysis_run_id,r.id) fingerprint_values FROM target_quality_gate_decisions r
UNION ALL
SELECT 15 delete_order, 'quality_assessment_queue_items'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.requested_by,r.status) fingerprint_values FROM target_quality_assessment_queue_items r
UNION ALL
SELECT 16 delete_order, 'microscopy_analysis_events'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.microscopy_image_id,r.status) fingerprint_values FROM target_microscopy_analysis_events r
UNION ALL
SELECT 17 delete_order, 'image_quality_assessments'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.analysis_run_image_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_image_quality_assessments r
UNION ALL
SELECT 18 delete_order, 'microscopy_analysis_run_images'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_microscopy_analysis_run_images r
UNION ALL
SELECT 19 delete_order, 'microscopy_analysis_runs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'image_ingestion_batches'::text parent_table, r.ingestion_batch_id::text parent_record_id, 'Raíz del flujo de ingesta o análisis'::text selection_reason, jsonb_build_array(r.case_id,r.id,r.ingestion_batch_id,r.requested_by,r.run_status,r.sample_id,r.slide_id,r.subject_id) fingerprint_values FROM target_microscopy_analysis_runs r
UNION ALL
SELECT 20 delete_order, 'microscopy_images'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'smear_slides'::text parent_table, r.slide_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.ingestion_batch_id,r.slide_id,r.status,r.storage_key,r.updated_by) fingerprint_values FROM target_microscopy_images r
UNION ALL
SELECT 21 delete_order, 'image_ingestion_batches'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'smear_slides'::text parent_table, r.slide_id::text parent_record_id, 'Raíz del flujo de ingesta o análisis'::text selection_reason, jsonb_build_array(r.case_id,r.created_by,r.id,r.sample_id,r.slide_id,r.status,r.subject_id) fingerprint_values FROM target_image_ingestion_batches r
UNION ALL
SELECT 22 delete_order, 'smear_slides'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'blood_samples'::text parent_table, r.sample_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.sample_id,r.status,r.updated_by) fingerprint_values FROM target_smear_slides r
UNION ALL
SELECT 23 delete_order, 'blood_samples'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'scientific_cases'::text parent_table, r.case_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.case_id,r.created_by,r.id,r.status,r.updated_by) fingerprint_values FROM target_blood_samples r
UNION ALL
SELECT 24 delete_order, 'scientific_cases'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'research_subjects'::text parent_table, r.subject_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.source_type,r.status,r.subject_id,r.updated_by) fingerprint_values FROM target_scientific_cases r
UNION ALL
SELECT 25 delete_order, 'research_subjects'::text table_name, 'id'::text primary_key_column, r.id::text record_id, NULL::text parent_table, NULL::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.status,r.updated_by) fingerprint_values FROM target_research_subjects r),
clinical_storage AS (SELECT 'microscopy_images'::text source_table,id::text record_id,'storage_key'::text storage_column,storage_key::text storage_key,file_size_bytes expected_size,sha256::text expected_sha256,'microscopy_images'::text clinical_entity_type FROM target_microscopy_images WHERE storage_key IS NOT NULL UNION ALL SELECT 'cell_crops'::text source_table,id::text record_id,'relative_storage_key'::text storage_column,relative_storage_key::text storage_key,file_size_bytes expected_size,sha256::text expected_sha256,'cell_crops'::text clinical_entity_type FROM target_cell_crops WHERE relative_storage_key IS NOT NULL UNION ALL SELECT 'cell_explanations'::text source_table,id::text record_id,'heatmap_storage_key'::text storage_column,heatmap_storage_key::text storage_key,heatmap_file_size_bytes expected_size,heatmap_sha256::text expected_sha256,'cell_explanations'::text clinical_entity_type FROM target_cell_explanations WHERE heatmap_storage_key IS NOT NULL UNION ALL SELECT 'cell_explanations'::text source_table,id::text record_id,'overlay_storage_key'::text storage_column,overlay_storage_key::text storage_key,overlay_file_size_bytes expected_size,overlay_sha256::text expected_sha256,'cell_explanations'::text clinical_entity_type FROM target_cell_explanations WHERE overlay_storage_key IS NOT NULL),
clinical_evidence AS MATERIALIZED (SELECT record_id AS value FROM targets UNION SELECT storage_key FROM clinical_storage)
SELECT delete_order,table_name,primary_key_column,record_id,parent_table,parent_record_id,selection_reason FROM targets ORDER BY delete_order,table_name,record_id;

-- REPORT storage_keys
WITH RECURSIVE
target_image_ingestion_batches AS (SELECT r.* FROM public.image_ingestion_batches r),
target_microscopy_analysis_runs AS (SELECT r.* FROM public.microscopy_analysis_runs r),
target_microscopy_analysis_run_images AS (SELECT r.* FROM public.microscopy_analysis_run_images r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_cell_detection_runs AS (SELECT r.* FROM public.cell_detection_runs r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_cell_detections AS (SELECT r.* FROM public.cell_detections r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_image_connected_components AS (SELECT r.* FROM public.image_connected_components r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_cell_crops AS (SELECT r.* FROM public.cell_crops r JOIN target_cell_detections p ON r.cell_detection_id=p.id),
target_cell_detection_events AS (SELECT r.* FROM public.cell_detection_events r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_scientific_reviews AS (SELECT r.* FROM public.scientific_reviews r JOIN target_cell_detections p ON r.entity_id=p.id),
target_cell_classification_runs AS (SELECT r.* FROM public.cell_classification_runs r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_cell_classification_inputs AS (SELECT r.* FROM public.cell_classification_inputs r JOIN target_cell_classification_runs p ON r.classification_run_id=p.id),
target_cell_predictions AS (SELECT r.* FROM public.cell_predictions r JOIN target_cell_classification_inputs p ON r.classification_input_id=p.id),
target_cell_explanations AS (SELECT r.* FROM public.cell_explanations r JOIN target_cell_predictions p ON r.cell_prediction_id=p.id),
target_cell_classification_reviews AS (SELECT r.* FROM public.cell_classification_reviews r JOIN target_cell_predictions p ON r.cell_prediction_id=p.id),
target_cell_classification_events AS (SELECT r.* FROM public.cell_classification_events r JOIN target_cell_classification_runs p ON r.classification_run_id=p.id),
target_smear_analysis_summaries AS (SELECT r.* FROM public.smear_analysis_summaries r JOIN target_cell_classification_runs p ON r.classification_run_id=p.id),
target_image_quality_assessments AS (SELECT r.* FROM public.image_quality_assessments r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_quality_gate_decisions AS (SELECT r.* FROM public.quality_gate_decisions r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_quality_assessment_queue_items AS (SELECT r.* FROM public.quality_assessment_queue_items r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_microscopy_analysis_events AS (SELECT r.* FROM public.microscopy_analysis_events r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_microscopy_images AS (SELECT r.* FROM public.microscopy_images r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_run_images p WHERE p.microscopy_image_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.id=r.ingestion_batch_id)),
target_smear_slides AS (SELECT r.* FROM public.smear_slides r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.slide_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.slide_id=r.id)),
target_blood_samples AS (SELECT r.* FROM public.blood_samples r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.sample_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.sample_id=r.id)),
target_scientific_cases AS (SELECT r.* FROM public.scientific_cases r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.case_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.case_id=r.id)),
target_research_subjects AS (SELECT r.* FROM public.research_subjects r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.subject_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.subject_id=r.id)),
table_catalog(delete_order,table_name,primary_key_column,selection_reason) AS (VALUES (1,'cell_explanations','id','JOIN cell_prediction_id al conjunto cell_predictions'),
(2,'cell_classification_reviews','id','JOIN cell_prediction_id al conjunto cell_predictions'),
(3,'cell_classification_events','id','JOIN classification_run_id al conjunto cell_classification_runs'),
(4,'smear_analysis_summaries','id','JOIN classification_run_id al conjunto cell_classification_runs'),
(5,'cell_predictions','id','JOIN classification_input_id al conjunto cell_classification_inputs'),
(6,'cell_classification_inputs','id','JOIN classification_run_id al conjunto cell_classification_runs'),
(7,'cell_classification_runs','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(8,'scientific_reviews','id','JOIN entity_id al conjunto cell_detections'),
(9,'cell_crops','id','JOIN cell_detection_id al conjunto cell_detections'),
(10,'cell_detection_events','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(11,'cell_detections','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(12,'image_connected_components','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(13,'cell_detection_runs','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(14,'quality_gate_decisions','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(15,'quality_assessment_queue_items','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(16,'microscopy_analysis_events','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(17,'image_quality_assessments','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(18,'microscopy_analysis_run_images','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(19,'microscopy_analysis_runs','id','Raíz del flujo de ingesta o análisis'),
(20,'microscopy_images','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(21,'image_ingestion_batches','id','Raíz del flujo de ingesta o análisis'),
(22,'smear_slides','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(23,'blood_samples','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(24,'scientific_cases','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(25,'research_subjects','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga')),
targets AS (SELECT 1 delete_order, 'cell_explanations'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_predictions'::text parent_table, r.cell_prediction_id::text parent_record_id, 'JOIN cell_prediction_id al conjunto cell_predictions'::text selection_reason, jsonb_build_array(r.cell_prediction_id,r.heatmap_storage_key,r.id,r.overlay_storage_key,r.status) fingerprint_values FROM target_cell_explanations r
UNION ALL
SELECT 2 delete_order, 'cell_classification_reviews'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_predictions'::text parent_table, r.cell_prediction_id::text parent_record_id, 'JOIN cell_prediction_id al conjunto cell_predictions'::text selection_reason, jsonb_build_array(r.actor_user_id,r.cell_prediction_id,r.id) fingerprint_values FROM target_cell_classification_reviews r
UNION ALL
SELECT 3 delete_order, 'cell_classification_events'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_runs'::text parent_table, r.classification_run_id::text parent_record_id, 'JOIN classification_run_id al conjunto cell_classification_runs'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.cell_prediction_id,r.classification_run_id,r.id,r.status) fingerprint_values FROM target_cell_classification_events r
UNION ALL
SELECT 4 delete_order, 'smear_analysis_summaries'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_runs'::text parent_table, r.classification_run_id::text parent_record_id, 'JOIN classification_run_id al conjunto cell_classification_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.classification_run_id,r.detection_run_id,r.id) fingerprint_values FROM target_smear_analysis_summaries r
UNION ALL
SELECT 5 delete_order, 'cell_predictions'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_inputs'::text parent_table, r.classification_input_id::text parent_record_id, 'JOIN classification_input_id al conjunto cell_classification_inputs'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.classification_input_id,r.classification_run_id,r.crop_id,r.id) fingerprint_values FROM target_cell_predictions r
UNION ALL
SELECT 6 delete_order, 'cell_classification_inputs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_runs'::text parent_table, r.classification_run_id::text parent_record_id, 'JOIN classification_run_id al conjunto cell_classification_runs'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.classification_run_id,r.crop_id,r.detection_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_cell_classification_inputs r
UNION ALL
SELECT 7 delete_order, 'cell_classification_runs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.detection_run_id,r.id,r.model_registry_id,r.production_model_id,r.requested_by,r.retry_of_run_id,r.stage2_publication_id,r.status) fingerprint_values FROM target_cell_classification_runs r
UNION ALL
SELECT 8 delete_order, 'scientific_reviews'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detections'::text parent_table, r.entity_id::text parent_record_id, 'JOIN entity_id al conjunto cell_detections'::text selection_reason, jsonb_build_array(r.actor_user_id,r.entity_id,r.id) fingerprint_values FROM target_scientific_reviews r
UNION ALL
SELECT 9 delete_order, 'cell_crops'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detections'::text parent_table, r.cell_detection_id::text parent_record_id, 'JOIN cell_detection_id al conjunto cell_detections'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.id,r.relative_storage_key) fingerprint_values FROM target_cell_crops r
UNION ALL
SELECT 10 delete_order, 'cell_detection_events'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.detection_run_id,r.id,r.microscopy_image_id,r.status) fingerprint_values FROM target_cell_detection_events r
UNION ALL
SELECT 11 delete_order, 'cell_detections'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.analysis_run_image_id,r.connected_component_id,r.detection_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_cell_detections r
UNION ALL
SELECT 12 delete_order, 'image_connected_components'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.analysis_run_image_id,r.detection_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_image_connected_components r
UNION ALL
SELECT 13 delete_order, 'cell_detection_runs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.requested_by,r.status) fingerprint_values FROM target_cell_detection_runs r
UNION ALL
SELECT 14 delete_order, 'quality_gate_decisions'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.actor_user_id,r.analysis_run_id,r.id) fingerprint_values FROM target_quality_gate_decisions r
UNION ALL
SELECT 15 delete_order, 'quality_assessment_queue_items'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.requested_by,r.status) fingerprint_values FROM target_quality_assessment_queue_items r
UNION ALL
SELECT 16 delete_order, 'microscopy_analysis_events'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.microscopy_image_id,r.status) fingerprint_values FROM target_microscopy_analysis_events r
UNION ALL
SELECT 17 delete_order, 'image_quality_assessments'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.analysis_run_image_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_image_quality_assessments r
UNION ALL
SELECT 18 delete_order, 'microscopy_analysis_run_images'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_microscopy_analysis_run_images r
UNION ALL
SELECT 19 delete_order, 'microscopy_analysis_runs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'image_ingestion_batches'::text parent_table, r.ingestion_batch_id::text parent_record_id, 'Raíz del flujo de ingesta o análisis'::text selection_reason, jsonb_build_array(r.case_id,r.id,r.ingestion_batch_id,r.requested_by,r.run_status,r.sample_id,r.slide_id,r.subject_id) fingerprint_values FROM target_microscopy_analysis_runs r
UNION ALL
SELECT 20 delete_order, 'microscopy_images'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'smear_slides'::text parent_table, r.slide_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.ingestion_batch_id,r.slide_id,r.status,r.storage_key,r.updated_by) fingerprint_values FROM target_microscopy_images r
UNION ALL
SELECT 21 delete_order, 'image_ingestion_batches'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'smear_slides'::text parent_table, r.slide_id::text parent_record_id, 'Raíz del flujo de ingesta o análisis'::text selection_reason, jsonb_build_array(r.case_id,r.created_by,r.id,r.sample_id,r.slide_id,r.status,r.subject_id) fingerprint_values FROM target_image_ingestion_batches r
UNION ALL
SELECT 22 delete_order, 'smear_slides'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'blood_samples'::text parent_table, r.sample_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.sample_id,r.status,r.updated_by) fingerprint_values FROM target_smear_slides r
UNION ALL
SELECT 23 delete_order, 'blood_samples'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'scientific_cases'::text parent_table, r.case_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.case_id,r.created_by,r.id,r.status,r.updated_by) fingerprint_values FROM target_blood_samples r
UNION ALL
SELECT 24 delete_order, 'scientific_cases'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'research_subjects'::text parent_table, r.subject_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.source_type,r.status,r.subject_id,r.updated_by) fingerprint_values FROM target_scientific_cases r
UNION ALL
SELECT 25 delete_order, 'research_subjects'::text table_name, 'id'::text primary_key_column, r.id::text record_id, NULL::text parent_table, NULL::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.status,r.updated_by) fingerprint_values FROM target_research_subjects r),
clinical_storage AS (SELECT 'microscopy_images'::text source_table,id::text record_id,'storage_key'::text storage_column,storage_key::text storage_key,file_size_bytes expected_size,sha256::text expected_sha256,'microscopy_images'::text clinical_entity_type FROM target_microscopy_images WHERE storage_key IS NOT NULL UNION ALL SELECT 'cell_crops'::text source_table,id::text record_id,'relative_storage_key'::text storage_column,relative_storage_key::text storage_key,file_size_bytes expected_size,sha256::text expected_sha256,'cell_crops'::text clinical_entity_type FROM target_cell_crops WHERE relative_storage_key IS NOT NULL UNION ALL SELECT 'cell_explanations'::text source_table,id::text record_id,'heatmap_storage_key'::text storage_column,heatmap_storage_key::text storage_key,heatmap_file_size_bytes expected_size,heatmap_sha256::text expected_sha256,'cell_explanations'::text clinical_entity_type FROM target_cell_explanations WHERE heatmap_storage_key IS NOT NULL UNION ALL SELECT 'cell_explanations'::text source_table,id::text record_id,'overlay_storage_key'::text storage_column,overlay_storage_key::text storage_key,overlay_file_size_bytes expected_size,overlay_sha256::text expected_sha256,'cell_explanations'::text clinical_entity_type FROM target_cell_explanations WHERE overlay_storage_key IS NOT NULL),
clinical_evidence AS MATERIALIZED (SELECT record_id AS value FROM targets UNION SELECT storage_key FROM clinical_storage)
SELECT * FROM clinical_storage WHERE storage_key !~ '^/' ORDER BY source_table,record_id,storage_column;

-- REPORT fingerprints
WITH RECURSIVE
target_image_ingestion_batches AS (SELECT r.* FROM public.image_ingestion_batches r),
target_microscopy_analysis_runs AS (SELECT r.* FROM public.microscopy_analysis_runs r),
target_microscopy_analysis_run_images AS (SELECT r.* FROM public.microscopy_analysis_run_images r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_cell_detection_runs AS (SELECT r.* FROM public.cell_detection_runs r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_cell_detections AS (SELECT r.* FROM public.cell_detections r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_image_connected_components AS (SELECT r.* FROM public.image_connected_components r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_cell_crops AS (SELECT r.* FROM public.cell_crops r JOIN target_cell_detections p ON r.cell_detection_id=p.id),
target_cell_detection_events AS (SELECT r.* FROM public.cell_detection_events r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_scientific_reviews AS (SELECT r.* FROM public.scientific_reviews r JOIN target_cell_detections p ON r.entity_id=p.id),
target_cell_classification_runs AS (SELECT r.* FROM public.cell_classification_runs r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_cell_classification_inputs AS (SELECT r.* FROM public.cell_classification_inputs r JOIN target_cell_classification_runs p ON r.classification_run_id=p.id),
target_cell_predictions AS (SELECT r.* FROM public.cell_predictions r JOIN target_cell_classification_inputs p ON r.classification_input_id=p.id),
target_cell_explanations AS (SELECT r.* FROM public.cell_explanations r JOIN target_cell_predictions p ON r.cell_prediction_id=p.id),
target_cell_classification_reviews AS (SELECT r.* FROM public.cell_classification_reviews r JOIN target_cell_predictions p ON r.cell_prediction_id=p.id),
target_cell_classification_events AS (SELECT r.* FROM public.cell_classification_events r JOIN target_cell_classification_runs p ON r.classification_run_id=p.id),
target_smear_analysis_summaries AS (SELECT r.* FROM public.smear_analysis_summaries r JOIN target_cell_classification_runs p ON r.classification_run_id=p.id),
target_image_quality_assessments AS (SELECT r.* FROM public.image_quality_assessments r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_quality_gate_decisions AS (SELECT r.* FROM public.quality_gate_decisions r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_quality_assessment_queue_items AS (SELECT r.* FROM public.quality_assessment_queue_items r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_microscopy_analysis_events AS (SELECT r.* FROM public.microscopy_analysis_events r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_microscopy_images AS (SELECT r.* FROM public.microscopy_images r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_run_images p WHERE p.microscopy_image_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.id=r.ingestion_batch_id)),
target_smear_slides AS (SELECT r.* FROM public.smear_slides r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.slide_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.slide_id=r.id)),
target_blood_samples AS (SELECT r.* FROM public.blood_samples r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.sample_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.sample_id=r.id)),
target_scientific_cases AS (SELECT r.* FROM public.scientific_cases r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.case_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.case_id=r.id)),
target_research_subjects AS (SELECT r.* FROM public.research_subjects r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.subject_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.subject_id=r.id)),
table_catalog(delete_order,table_name,primary_key_column,selection_reason) AS (VALUES (1,'cell_explanations','id','JOIN cell_prediction_id al conjunto cell_predictions'),
(2,'cell_classification_reviews','id','JOIN cell_prediction_id al conjunto cell_predictions'),
(3,'cell_classification_events','id','JOIN classification_run_id al conjunto cell_classification_runs'),
(4,'smear_analysis_summaries','id','JOIN classification_run_id al conjunto cell_classification_runs'),
(5,'cell_predictions','id','JOIN classification_input_id al conjunto cell_classification_inputs'),
(6,'cell_classification_inputs','id','JOIN classification_run_id al conjunto cell_classification_runs'),
(7,'cell_classification_runs','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(8,'scientific_reviews','id','JOIN entity_id al conjunto cell_detections'),
(9,'cell_crops','id','JOIN cell_detection_id al conjunto cell_detections'),
(10,'cell_detection_events','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(11,'cell_detections','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(12,'image_connected_components','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(13,'cell_detection_runs','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(14,'quality_gate_decisions','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(15,'quality_assessment_queue_items','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(16,'microscopy_analysis_events','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(17,'image_quality_assessments','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(18,'microscopy_analysis_run_images','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(19,'microscopy_analysis_runs','id','Raíz del flujo de ingesta o análisis'),
(20,'microscopy_images','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(21,'image_ingestion_batches','id','Raíz del flujo de ingesta o análisis'),
(22,'smear_slides','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(23,'blood_samples','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(24,'scientific_cases','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(25,'research_subjects','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga')),
targets AS (SELECT 1 delete_order, 'cell_explanations'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_predictions'::text parent_table, r.cell_prediction_id::text parent_record_id, 'JOIN cell_prediction_id al conjunto cell_predictions'::text selection_reason, jsonb_build_array(r.cell_prediction_id,r.heatmap_storage_key,r.id,r.overlay_storage_key,r.status) fingerprint_values FROM target_cell_explanations r
UNION ALL
SELECT 2 delete_order, 'cell_classification_reviews'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_predictions'::text parent_table, r.cell_prediction_id::text parent_record_id, 'JOIN cell_prediction_id al conjunto cell_predictions'::text selection_reason, jsonb_build_array(r.actor_user_id,r.cell_prediction_id,r.id) fingerprint_values FROM target_cell_classification_reviews r
UNION ALL
SELECT 3 delete_order, 'cell_classification_events'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_runs'::text parent_table, r.classification_run_id::text parent_record_id, 'JOIN classification_run_id al conjunto cell_classification_runs'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.cell_prediction_id,r.classification_run_id,r.id,r.status) fingerprint_values FROM target_cell_classification_events r
UNION ALL
SELECT 4 delete_order, 'smear_analysis_summaries'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_runs'::text parent_table, r.classification_run_id::text parent_record_id, 'JOIN classification_run_id al conjunto cell_classification_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.classification_run_id,r.detection_run_id,r.id) fingerprint_values FROM target_smear_analysis_summaries r
UNION ALL
SELECT 5 delete_order, 'cell_predictions'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_inputs'::text parent_table, r.classification_input_id::text parent_record_id, 'JOIN classification_input_id al conjunto cell_classification_inputs'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.classification_input_id,r.classification_run_id,r.crop_id,r.id) fingerprint_values FROM target_cell_predictions r
UNION ALL
SELECT 6 delete_order, 'cell_classification_inputs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_runs'::text parent_table, r.classification_run_id::text parent_record_id, 'JOIN classification_run_id al conjunto cell_classification_runs'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.classification_run_id,r.crop_id,r.detection_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_cell_classification_inputs r
UNION ALL
SELECT 7 delete_order, 'cell_classification_runs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.detection_run_id,r.id,r.model_registry_id,r.production_model_id,r.requested_by,r.retry_of_run_id,r.stage2_publication_id,r.status) fingerprint_values FROM target_cell_classification_runs r
UNION ALL
SELECT 8 delete_order, 'scientific_reviews'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detections'::text parent_table, r.entity_id::text parent_record_id, 'JOIN entity_id al conjunto cell_detections'::text selection_reason, jsonb_build_array(r.actor_user_id,r.entity_id,r.id) fingerprint_values FROM target_scientific_reviews r
UNION ALL
SELECT 9 delete_order, 'cell_crops'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detections'::text parent_table, r.cell_detection_id::text parent_record_id, 'JOIN cell_detection_id al conjunto cell_detections'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.id,r.relative_storage_key) fingerprint_values FROM target_cell_crops r
UNION ALL
SELECT 10 delete_order, 'cell_detection_events'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.detection_run_id,r.id,r.microscopy_image_id,r.status) fingerprint_values FROM target_cell_detection_events r
UNION ALL
SELECT 11 delete_order, 'cell_detections'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.analysis_run_image_id,r.connected_component_id,r.detection_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_cell_detections r
UNION ALL
SELECT 12 delete_order, 'image_connected_components'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.analysis_run_image_id,r.detection_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_image_connected_components r
UNION ALL
SELECT 13 delete_order, 'cell_detection_runs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.requested_by,r.status) fingerprint_values FROM target_cell_detection_runs r
UNION ALL
SELECT 14 delete_order, 'quality_gate_decisions'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.actor_user_id,r.analysis_run_id,r.id) fingerprint_values FROM target_quality_gate_decisions r
UNION ALL
SELECT 15 delete_order, 'quality_assessment_queue_items'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.requested_by,r.status) fingerprint_values FROM target_quality_assessment_queue_items r
UNION ALL
SELECT 16 delete_order, 'microscopy_analysis_events'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.microscopy_image_id,r.status) fingerprint_values FROM target_microscopy_analysis_events r
UNION ALL
SELECT 17 delete_order, 'image_quality_assessments'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.analysis_run_image_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_image_quality_assessments r
UNION ALL
SELECT 18 delete_order, 'microscopy_analysis_run_images'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_microscopy_analysis_run_images r
UNION ALL
SELECT 19 delete_order, 'microscopy_analysis_runs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'image_ingestion_batches'::text parent_table, r.ingestion_batch_id::text parent_record_id, 'Raíz del flujo de ingesta o análisis'::text selection_reason, jsonb_build_array(r.case_id,r.id,r.ingestion_batch_id,r.requested_by,r.run_status,r.sample_id,r.slide_id,r.subject_id) fingerprint_values FROM target_microscopy_analysis_runs r
UNION ALL
SELECT 20 delete_order, 'microscopy_images'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'smear_slides'::text parent_table, r.slide_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.ingestion_batch_id,r.slide_id,r.status,r.storage_key,r.updated_by) fingerprint_values FROM target_microscopy_images r
UNION ALL
SELECT 21 delete_order, 'image_ingestion_batches'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'smear_slides'::text parent_table, r.slide_id::text parent_record_id, 'Raíz del flujo de ingesta o análisis'::text selection_reason, jsonb_build_array(r.case_id,r.created_by,r.id,r.sample_id,r.slide_id,r.status,r.subject_id) fingerprint_values FROM target_image_ingestion_batches r
UNION ALL
SELECT 22 delete_order, 'smear_slides'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'blood_samples'::text parent_table, r.sample_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.sample_id,r.status,r.updated_by) fingerprint_values FROM target_smear_slides r
UNION ALL
SELECT 23 delete_order, 'blood_samples'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'scientific_cases'::text parent_table, r.case_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.case_id,r.created_by,r.id,r.status,r.updated_by) fingerprint_values FROM target_blood_samples r
UNION ALL
SELECT 24 delete_order, 'scientific_cases'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'research_subjects'::text parent_table, r.subject_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.source_type,r.status,r.subject_id,r.updated_by) fingerprint_values FROM target_scientific_cases r
UNION ALL
SELECT 25 delete_order, 'research_subjects'::text table_name, 'id'::text primary_key_column, r.id::text record_id, NULL::text parent_table, NULL::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.status,r.updated_by) fingerprint_values FROM target_research_subjects r),
clinical_storage AS (SELECT 'microscopy_images'::text source_table,id::text record_id,'storage_key'::text storage_column,storage_key::text storage_key,file_size_bytes expected_size,sha256::text expected_sha256,'microscopy_images'::text clinical_entity_type FROM target_microscopy_images WHERE storage_key IS NOT NULL UNION ALL SELECT 'cell_crops'::text source_table,id::text record_id,'relative_storage_key'::text storage_column,relative_storage_key::text storage_key,file_size_bytes expected_size,sha256::text expected_sha256,'cell_crops'::text clinical_entity_type FROM target_cell_crops WHERE relative_storage_key IS NOT NULL UNION ALL SELECT 'cell_explanations'::text source_table,id::text record_id,'heatmap_storage_key'::text storage_column,heatmap_storage_key::text storage_key,heatmap_file_size_bytes expected_size,heatmap_sha256::text expected_sha256,'cell_explanations'::text clinical_entity_type FROM target_cell_explanations WHERE heatmap_storage_key IS NOT NULL UNION ALL SELECT 'cell_explanations'::text source_table,id::text record_id,'overlay_storage_key'::text storage_column,overlay_storage_key::text storage_key,overlay_file_size_bytes expected_size,overlay_sha256::text expected_sha256,'cell_explanations'::text clinical_entity_type FROM target_cell_explanations WHERE overlay_storage_key IS NOT NULL),
clinical_evidence AS MATERIALIZED (SELECT record_id AS value FROM targets UNION SELECT storage_key FROM clinical_storage)
SELECT c.delete_order,c.table_name,count(t.record_id) target_count,md5(COALESCE(string_agg(t.fingerprint_values::text,E'\n' ORDER BY t.record_id COLLATE "C"),'')) fingerprint_md5 FROM table_catalog c LEFT JOIN targets t USING(table_name) GROUP BY c.delete_order,c.table_name ORDER BY c.delete_order;

-- REPORT preservation
WITH RECURSIVE
target_image_ingestion_batches AS (SELECT r.* FROM public.image_ingestion_batches r),
target_microscopy_analysis_runs AS (SELECT r.* FROM public.microscopy_analysis_runs r),
target_microscopy_analysis_run_images AS (SELECT r.* FROM public.microscopy_analysis_run_images r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_cell_detection_runs AS (SELECT r.* FROM public.cell_detection_runs r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_cell_detections AS (SELECT r.* FROM public.cell_detections r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_image_connected_components AS (SELECT r.* FROM public.image_connected_components r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_cell_crops AS (SELECT r.* FROM public.cell_crops r JOIN target_cell_detections p ON r.cell_detection_id=p.id),
target_cell_detection_events AS (SELECT r.* FROM public.cell_detection_events r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_scientific_reviews AS (SELECT r.* FROM public.scientific_reviews r JOIN target_cell_detections p ON r.entity_id=p.id),
target_cell_classification_runs AS (SELECT r.* FROM public.cell_classification_runs r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_cell_classification_inputs AS (SELECT r.* FROM public.cell_classification_inputs r JOIN target_cell_classification_runs p ON r.classification_run_id=p.id),
target_cell_predictions AS (SELECT r.* FROM public.cell_predictions r JOIN target_cell_classification_inputs p ON r.classification_input_id=p.id),
target_cell_explanations AS (SELECT r.* FROM public.cell_explanations r JOIN target_cell_predictions p ON r.cell_prediction_id=p.id),
target_cell_classification_reviews AS (SELECT r.* FROM public.cell_classification_reviews r JOIN target_cell_predictions p ON r.cell_prediction_id=p.id),
target_cell_classification_events AS (SELECT r.* FROM public.cell_classification_events r JOIN target_cell_classification_runs p ON r.classification_run_id=p.id),
target_smear_analysis_summaries AS (SELECT r.* FROM public.smear_analysis_summaries r JOIN target_cell_classification_runs p ON r.classification_run_id=p.id),
target_image_quality_assessments AS (SELECT r.* FROM public.image_quality_assessments r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_quality_gate_decisions AS (SELECT r.* FROM public.quality_gate_decisions r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_quality_assessment_queue_items AS (SELECT r.* FROM public.quality_assessment_queue_items r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_microscopy_analysis_events AS (SELECT r.* FROM public.microscopy_analysis_events r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_microscopy_images AS (SELECT r.* FROM public.microscopy_images r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_run_images p WHERE p.microscopy_image_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.id=r.ingestion_batch_id)),
target_smear_slides AS (SELECT r.* FROM public.smear_slides r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.slide_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.slide_id=r.id)),
target_blood_samples AS (SELECT r.* FROM public.blood_samples r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.sample_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.sample_id=r.id)),
target_scientific_cases AS (SELECT r.* FROM public.scientific_cases r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.case_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.case_id=r.id)),
target_research_subjects AS (SELECT r.* FROM public.research_subjects r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.subject_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.subject_id=r.id)),
table_catalog(delete_order,table_name,primary_key_column,selection_reason) AS (VALUES (1,'cell_explanations','id','JOIN cell_prediction_id al conjunto cell_predictions'),
(2,'cell_classification_reviews','id','JOIN cell_prediction_id al conjunto cell_predictions'),
(3,'cell_classification_events','id','JOIN classification_run_id al conjunto cell_classification_runs'),
(4,'smear_analysis_summaries','id','JOIN classification_run_id al conjunto cell_classification_runs'),
(5,'cell_predictions','id','JOIN classification_input_id al conjunto cell_classification_inputs'),
(6,'cell_classification_inputs','id','JOIN classification_run_id al conjunto cell_classification_runs'),
(7,'cell_classification_runs','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(8,'scientific_reviews','id','JOIN entity_id al conjunto cell_detections'),
(9,'cell_crops','id','JOIN cell_detection_id al conjunto cell_detections'),
(10,'cell_detection_events','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(11,'cell_detections','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(12,'image_connected_components','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(13,'cell_detection_runs','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(14,'quality_gate_decisions','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(15,'quality_assessment_queue_items','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(16,'microscopy_analysis_events','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(17,'image_quality_assessments','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(18,'microscopy_analysis_run_images','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(19,'microscopy_analysis_runs','id','Raíz del flujo de ingesta o análisis'),
(20,'microscopy_images','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(21,'image_ingestion_batches','id','Raíz del flujo de ingesta o análisis'),
(22,'smear_slides','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(23,'blood_samples','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(24,'scientific_cases','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(25,'research_subjects','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga')),
targets AS (SELECT 1 delete_order, 'cell_explanations'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_predictions'::text parent_table, r.cell_prediction_id::text parent_record_id, 'JOIN cell_prediction_id al conjunto cell_predictions'::text selection_reason, jsonb_build_array(r.cell_prediction_id,r.heatmap_storage_key,r.id,r.overlay_storage_key,r.status) fingerprint_values FROM target_cell_explanations r
UNION ALL
SELECT 2 delete_order, 'cell_classification_reviews'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_predictions'::text parent_table, r.cell_prediction_id::text parent_record_id, 'JOIN cell_prediction_id al conjunto cell_predictions'::text selection_reason, jsonb_build_array(r.actor_user_id,r.cell_prediction_id,r.id) fingerprint_values FROM target_cell_classification_reviews r
UNION ALL
SELECT 3 delete_order, 'cell_classification_events'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_runs'::text parent_table, r.classification_run_id::text parent_record_id, 'JOIN classification_run_id al conjunto cell_classification_runs'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.cell_prediction_id,r.classification_run_id,r.id,r.status) fingerprint_values FROM target_cell_classification_events r
UNION ALL
SELECT 4 delete_order, 'smear_analysis_summaries'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_runs'::text parent_table, r.classification_run_id::text parent_record_id, 'JOIN classification_run_id al conjunto cell_classification_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.classification_run_id,r.detection_run_id,r.id) fingerprint_values FROM target_smear_analysis_summaries r
UNION ALL
SELECT 5 delete_order, 'cell_predictions'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_inputs'::text parent_table, r.classification_input_id::text parent_record_id, 'JOIN classification_input_id al conjunto cell_classification_inputs'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.classification_input_id,r.classification_run_id,r.crop_id,r.id) fingerprint_values FROM target_cell_predictions r
UNION ALL
SELECT 6 delete_order, 'cell_classification_inputs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_runs'::text parent_table, r.classification_run_id::text parent_record_id, 'JOIN classification_run_id al conjunto cell_classification_runs'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.classification_run_id,r.crop_id,r.detection_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_cell_classification_inputs r
UNION ALL
SELECT 7 delete_order, 'cell_classification_runs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.detection_run_id,r.id,r.model_registry_id,r.production_model_id,r.requested_by,r.retry_of_run_id,r.stage2_publication_id,r.status) fingerprint_values FROM target_cell_classification_runs r
UNION ALL
SELECT 8 delete_order, 'scientific_reviews'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detections'::text parent_table, r.entity_id::text parent_record_id, 'JOIN entity_id al conjunto cell_detections'::text selection_reason, jsonb_build_array(r.actor_user_id,r.entity_id,r.id) fingerprint_values FROM target_scientific_reviews r
UNION ALL
SELECT 9 delete_order, 'cell_crops'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detections'::text parent_table, r.cell_detection_id::text parent_record_id, 'JOIN cell_detection_id al conjunto cell_detections'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.id,r.relative_storage_key) fingerprint_values FROM target_cell_crops r
UNION ALL
SELECT 10 delete_order, 'cell_detection_events'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.detection_run_id,r.id,r.microscopy_image_id,r.status) fingerprint_values FROM target_cell_detection_events r
UNION ALL
SELECT 11 delete_order, 'cell_detections'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.analysis_run_image_id,r.connected_component_id,r.detection_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_cell_detections r
UNION ALL
SELECT 12 delete_order, 'image_connected_components'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.analysis_run_image_id,r.detection_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_image_connected_components r
UNION ALL
SELECT 13 delete_order, 'cell_detection_runs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.requested_by,r.status) fingerprint_values FROM target_cell_detection_runs r
UNION ALL
SELECT 14 delete_order, 'quality_gate_decisions'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.actor_user_id,r.analysis_run_id,r.id) fingerprint_values FROM target_quality_gate_decisions r
UNION ALL
SELECT 15 delete_order, 'quality_assessment_queue_items'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.requested_by,r.status) fingerprint_values FROM target_quality_assessment_queue_items r
UNION ALL
SELECT 16 delete_order, 'microscopy_analysis_events'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.microscopy_image_id,r.status) fingerprint_values FROM target_microscopy_analysis_events r
UNION ALL
SELECT 17 delete_order, 'image_quality_assessments'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.analysis_run_image_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_image_quality_assessments r
UNION ALL
SELECT 18 delete_order, 'microscopy_analysis_run_images'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_microscopy_analysis_run_images r
UNION ALL
SELECT 19 delete_order, 'microscopy_analysis_runs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'image_ingestion_batches'::text parent_table, r.ingestion_batch_id::text parent_record_id, 'Raíz del flujo de ingesta o análisis'::text selection_reason, jsonb_build_array(r.case_id,r.id,r.ingestion_batch_id,r.requested_by,r.run_status,r.sample_id,r.slide_id,r.subject_id) fingerprint_values FROM target_microscopy_analysis_runs r
UNION ALL
SELECT 20 delete_order, 'microscopy_images'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'smear_slides'::text parent_table, r.slide_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.ingestion_batch_id,r.slide_id,r.status,r.storage_key,r.updated_by) fingerprint_values FROM target_microscopy_images r
UNION ALL
SELECT 21 delete_order, 'image_ingestion_batches'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'smear_slides'::text parent_table, r.slide_id::text parent_record_id, 'Raíz del flujo de ingesta o análisis'::text selection_reason, jsonb_build_array(r.case_id,r.created_by,r.id,r.sample_id,r.slide_id,r.status,r.subject_id) fingerprint_values FROM target_image_ingestion_batches r
UNION ALL
SELECT 22 delete_order, 'smear_slides'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'blood_samples'::text parent_table, r.sample_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.sample_id,r.status,r.updated_by) fingerprint_values FROM target_smear_slides r
UNION ALL
SELECT 23 delete_order, 'blood_samples'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'scientific_cases'::text parent_table, r.case_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.case_id,r.created_by,r.id,r.status,r.updated_by) fingerprint_values FROM target_blood_samples r
UNION ALL
SELECT 24 delete_order, 'scientific_cases'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'research_subjects'::text parent_table, r.subject_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.source_type,r.status,r.subject_id,r.updated_by) fingerprint_values FROM target_scientific_cases r
UNION ALL
SELECT 25 delete_order, 'research_subjects'::text table_name, 'id'::text primary_key_column, r.id::text record_id, NULL::text parent_table, NULL::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.status,r.updated_by) fingerprint_values FROM target_research_subjects r),
clinical_storage AS (SELECT 'microscopy_images'::text source_table,id::text record_id,'storage_key'::text storage_column,storage_key::text storage_key,file_size_bytes expected_size,sha256::text expected_sha256,'microscopy_images'::text clinical_entity_type FROM target_microscopy_images WHERE storage_key IS NOT NULL UNION ALL SELECT 'cell_crops'::text source_table,id::text record_id,'relative_storage_key'::text storage_column,relative_storage_key::text storage_key,file_size_bytes expected_size,sha256::text expected_sha256,'cell_crops'::text clinical_entity_type FROM target_cell_crops WHERE relative_storage_key IS NOT NULL UNION ALL SELECT 'cell_explanations'::text source_table,id::text record_id,'heatmap_storage_key'::text storage_column,heatmap_storage_key::text storage_key,heatmap_file_size_bytes expected_size,heatmap_sha256::text expected_sha256,'cell_explanations'::text clinical_entity_type FROM target_cell_explanations WHERE heatmap_storage_key IS NOT NULL UNION ALL SELECT 'cell_explanations'::text source_table,id::text record_id,'overlay_storage_key'::text storage_column,overlay_storage_key::text storage_key,overlay_file_size_bytes expected_size,overlay_sha256::text expected_sha256,'cell_explanations'::text clinical_entity_type FROM target_cell_explanations WHERE overlay_storage_key IS NOT NULL),
clinical_evidence AS MATERIALIZED (SELECT record_id AS value FROM targets UNION SELECT storage_key FROM clinical_storage),
audit_types(resource_type,table_name) AS (VALUES ('blood_sample','blood_samples'),('cell_classification_event','cell_classification_events'),('cell_classification_input','cell_classification_inputs'),('cell_classification_review','cell_classification_reviews'),('cell_classification_run','cell_classification_runs'),('cell_crop','cell_crops'),('cell_detection','cell_detections'),('cell_detection_event','cell_detection_events'),('cell_detection_run','cell_detection_runs'),('cell_explanation','cell_explanations'),('cell_prediction','cell_predictions'),('image_connected_component','image_connected_components'),('image_ingestion_batch','image_ingestion_batches'),('image_ingestion_batche','image_ingestion_batches'),('image_quality_assessment','image_quality_assessments'),('microscopy_analysis_event','microscopy_analysis_events'),('microscopy_analysis_run','microscopy_analysis_runs'),('microscopy_analysis_run_image','microscopy_analysis_run_images'),('microscopy_image','microscopy_images'),('quality_assessment_queue_item','quality_assessment_queue_items'),('quality_gate_decision','quality_gate_decisions'),('research_subject','research_subjects'),('scientific_case','scientific_cases'),('scientific_image','microscopy_images'),('scientific_review','scientific_reviews'),('scientific_sample','blood_samples'),('scientific_slide','smear_slides'),('scientific_subject','research_subjects'),('smear_analysis_summarie','smear_analysis_summaries'),('smear_slide','smear_slides')),
audit_resources AS MATERIALIZED (SELECT m.resource_type,t.record_id FROM audit_types m JOIN targets t ON t.table_name=m.table_name),
audit_classified AS (
 SELECT a.id::text record_id,
 CASE
 WHEN a.resource_type IN ('user','role','authentication') OR a.action IN ('login','logout','password-change','user-create','user-update','role-grant','role-revoke') THEN 'security_preserved'
 WHEN a.resource_type IN ('run','model_version','dataset','artifact','deployment','publication','image_analysis_job','prediction') OR a.resource_type LIKE 'scientific_validation_%' THEN 'experimental_preserved'
 WHEN (a.resource_type,a.resource_id) IN (SELECT resource_type,record_id FROM audit_resources) THEN 'clinical_delete_target'
 WHEN EXISTS (SELECT 1 FROM audit_types m WHERE m.resource_type=a.resource_type)
 OR EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(a.before_state,a.after_state,a.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence))
 OR a.request_path ~ '^/api/v1/(analysis|scientific/(workflows|images)|cell-analysis|cell-classification)(/|$)'
 THEN 'ambiguous'
 ELSE 'unrelated_preserved' END classification,
 a.resource_type,a.resource_id,
 md5(jsonb_build_array(a.id,a.resource_type,a.resource_id,a.event_type,a.action,a.success,
  (SELECT jsonb_agg(v ORDER BY v COLLATE "C") FROM
   (SELECT DISTINCT j.value #>> '{}' AS v FROM jsonb_path_query(jsonb_build_array(a.before_state,a.after_state,a.metadata),'strict $.** ? (@.type() == "string")') j(value)
    WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)) evidence)
 )::text) fingerprint_md5
 FROM public.audit_events a
),
validations AS (SELECT 'unscoped_rows:cell_explanations'::text validation_name,(SELECT count(*) FROM public.cell_explanations r WHERE NOT EXISTS (SELECT 1 FROM target_cell_explanations x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:cell_classification_reviews'::text validation_name,(SELECT count(*) FROM public.cell_classification_reviews r WHERE NOT EXISTS (SELECT 1 FROM target_cell_classification_reviews x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:cell_classification_events'::text validation_name,(SELECT count(*) FROM public.cell_classification_events r WHERE NOT EXISTS (SELECT 1 FROM target_cell_classification_events x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:smear_analysis_summaries'::text validation_name,(SELECT count(*) FROM public.smear_analysis_summaries r WHERE NOT EXISTS (SELECT 1 FROM target_smear_analysis_summaries x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:cell_predictions'::text validation_name,(SELECT count(*) FROM public.cell_predictions r WHERE NOT EXISTS (SELECT 1 FROM target_cell_predictions x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:cell_classification_inputs'::text validation_name,(SELECT count(*) FROM public.cell_classification_inputs r WHERE NOT EXISTS (SELECT 1 FROM target_cell_classification_inputs x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:cell_classification_runs'::text validation_name,(SELECT count(*) FROM public.cell_classification_runs r WHERE NOT EXISTS (SELECT 1 FROM target_cell_classification_runs x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:scientific_reviews'::text validation_name,(SELECT count(*) FROM public.scientific_reviews r WHERE NOT EXISTS (SELECT 1 FROM target_scientific_reviews x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:cell_crops'::text validation_name,(SELECT count(*) FROM public.cell_crops r WHERE NOT EXISTS (SELECT 1 FROM target_cell_crops x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:cell_detection_events'::text validation_name,(SELECT count(*) FROM public.cell_detection_events r WHERE NOT EXISTS (SELECT 1 FROM target_cell_detection_events x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:cell_detections'::text validation_name,(SELECT count(*) FROM public.cell_detections r WHERE NOT EXISTS (SELECT 1 FROM target_cell_detections x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:image_connected_components'::text validation_name,(SELECT count(*) FROM public.image_connected_components r WHERE NOT EXISTS (SELECT 1 FROM target_image_connected_components x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:cell_detection_runs'::text validation_name,(SELECT count(*) FROM public.cell_detection_runs r WHERE NOT EXISTS (SELECT 1 FROM target_cell_detection_runs x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:quality_gate_decisions'::text validation_name,(SELECT count(*) FROM public.quality_gate_decisions r WHERE NOT EXISTS (SELECT 1 FROM target_quality_gate_decisions x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:quality_assessment_queue_items'::text validation_name,(SELECT count(*) FROM public.quality_assessment_queue_items r WHERE NOT EXISTS (SELECT 1 FROM target_quality_assessment_queue_items x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:microscopy_analysis_events'::text validation_name,(SELECT count(*) FROM public.microscopy_analysis_events r WHERE NOT EXISTS (SELECT 1 FROM target_microscopy_analysis_events x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:image_quality_assessments'::text validation_name,(SELECT count(*) FROM public.image_quality_assessments r WHERE NOT EXISTS (SELECT 1 FROM target_image_quality_assessments x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:microscopy_analysis_run_images'::text validation_name,(SELECT count(*) FROM public.microscopy_analysis_run_images r WHERE NOT EXISTS (SELECT 1 FROM target_microscopy_analysis_run_images x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:microscopy_analysis_runs'::text validation_name,(SELECT count(*) FROM public.microscopy_analysis_runs r WHERE NOT EXISTS (SELECT 1 FROM target_microscopy_analysis_runs x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:microscopy_images'::text validation_name,(SELECT count(*) FROM public.microscopy_images r WHERE NOT EXISTS (SELECT 1 FROM target_microscopy_images x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:image_ingestion_batches'::text validation_name,(SELECT count(*) FROM public.image_ingestion_batches r WHERE NOT EXISTS (SELECT 1 FROM target_image_ingestion_batches x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:smear_slides'::text validation_name,(SELECT count(*) FROM public.smear_slides r WHERE NOT EXISTS (SELECT 1 FROM target_smear_slides x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:blood_samples'::text validation_name,(SELECT count(*) FROM public.blood_samples r WHERE NOT EXISTS (SELECT 1 FROM target_blood_samples x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:scientific_cases'::text validation_name,(SELECT count(*) FROM public.scientific_cases r WHERE NOT EXISTS (SELECT 1 FROM target_scientific_cases x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'unscoped_rows:research_subjects'::text validation_name,(SELECT count(*) FROM public.research_subjects r WHERE NOT EXISTS (SELECT 1 FROM target_research_subjects x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:blood_samples_case_id_fkey'::text validation_name,(SELECT count(*) FROM public.blood_samples r WHERE EXISTS (SELECT 1 FROM target_scientific_cases p WHERE r.case_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_blood_samples x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:cell_classification_events_cell_detection_id_fkey'::text validation_name,(SELECT count(*) FROM public.cell_classification_events r WHERE EXISTS (SELECT 1 FROM target_cell_detections p WHERE r.cell_detection_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_cell_classification_events x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:cell_classification_events_classification_run_id_fkey'::text validation_name,(SELECT count(*) FROM public.cell_classification_events r WHERE EXISTS (SELECT 1 FROM target_cell_classification_runs p WHERE r.classification_run_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_cell_classification_events x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:fk_cell_classification_event_prediction'::text validation_name,(SELECT count(*) FROM public.cell_classification_events r WHERE EXISTS (SELECT 1 FROM target_cell_predictions p WHERE r.cell_prediction_id=p.id AND r.classification_run_id=p.classification_run_id) AND NOT EXISTS (SELECT 1 FROM target_cell_classification_events x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:fk_cell_classification_input_crop'::text validation_name,(SELECT count(*) FROM public.cell_classification_inputs r WHERE EXISTS (SELECT 1 FROM target_cell_crops p WHERE r.crop_id=p.id AND r.cell_detection_id=p.cell_detection_id) AND NOT EXISTS (SELECT 1 FROM target_cell_classification_inputs x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:fk_cell_classification_input_detection'::text validation_name,(SELECT count(*) FROM public.cell_classification_inputs r WHERE EXISTS (SELECT 1 FROM target_cell_detections p WHERE r.cell_detection_id=p.id AND r.detection_run_id=p.detection_run_id AND r.microscopy_image_id=p.microscopy_image_id) AND NOT EXISTS (SELECT 1 FROM target_cell_classification_inputs x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:fk_cell_classification_input_run_detection'::text validation_name,(SELECT count(*) FROM public.cell_classification_inputs r WHERE EXISTS (SELECT 1 FROM target_cell_classification_runs p WHERE r.classification_run_id=p.id AND r.detection_run_id=p.detection_run_id) AND NOT EXISTS (SELECT 1 FROM target_cell_classification_inputs x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:cell_classification_reviews_cell_prediction_id_fkey'::text validation_name,(SELECT count(*) FROM public.cell_classification_reviews r WHERE EXISTS (SELECT 1 FROM target_cell_predictions p WHERE r.cell_prediction_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_cell_classification_reviews x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:cell_classification_runs_retry_of_run_id_fkey'::text validation_name,(SELECT count(*) FROM public.cell_classification_runs r WHERE EXISTS (SELECT 1 FROM target_cell_classification_runs p WHERE r.retry_of_run_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_cell_classification_runs x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:fk_cell_classification_run_detection_analysis'::text validation_name,(SELECT count(*) FROM public.cell_classification_runs r WHERE EXISTS (SELECT 1 FROM target_cell_detection_runs p WHERE r.detection_run_id=p.id AND r.analysis_run_id=p.analysis_run_id) AND NOT EXISTS (SELECT 1 FROM target_cell_classification_runs x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:fk_cell_crops_detection'::text validation_name,(SELECT count(*) FROM public.cell_crops r WHERE EXISTS (SELECT 1 FROM target_cell_detections p WHERE r.cell_detection_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_cell_crops x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:cell_detection_events_detection_run_id_fkey'::text validation_name,(SELECT count(*) FROM public.cell_detection_events r WHERE EXISTS (SELECT 1 FROM target_cell_detection_runs p WHERE r.detection_run_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_cell_detection_events x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:cell_detection_events_microscopy_image_id_fkey'::text validation_name,(SELECT count(*) FROM public.cell_detection_events r WHERE EXISTS (SELECT 1 FROM target_microscopy_images p WHERE r.microscopy_image_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_cell_detection_events x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:cell_detection_runs_analysis_run_id_fkey'::text validation_name,(SELECT count(*) FROM public.cell_detection_runs r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE r.analysis_run_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_cell_detection_runs x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:fk_cell_detections_component'::text validation_name,(SELECT count(*) FROM public.cell_detections r WHERE EXISTS (SELECT 1 FROM target_image_connected_components p WHERE r.connected_component_id=p.id AND r.detection_run_id=p.detection_run_id AND r.analysis_run_image_id=p.analysis_run_image_id AND r.microscopy_image_id=p.microscopy_image_id) AND NOT EXISTS (SELECT 1 FROM target_cell_detections x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:fk_cell_detections_run_analysis'::text validation_name,(SELECT count(*) FROM public.cell_detections r WHERE EXISTS (SELECT 1 FROM target_cell_detection_runs p WHERE r.detection_run_id=p.id AND r.analysis_run_id=p.analysis_run_id) AND NOT EXISTS (SELECT 1 FROM target_cell_detections x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:cell_explanations_cell_prediction_id_fkey'::text validation_name,(SELECT count(*) FROM public.cell_explanations r WHERE EXISTS (SELECT 1 FROM target_cell_predictions p WHERE r.cell_prediction_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_cell_explanations x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:fk_cell_prediction_input_owner'::text validation_name,(SELECT count(*) FROM public.cell_predictions r WHERE EXISTS (SELECT 1 FROM target_cell_classification_inputs p WHERE r.classification_input_id=p.id AND r.classification_run_id=p.classification_run_id AND r.cell_detection_id=p.cell_detection_id AND r.crop_id=p.crop_id) AND NOT EXISTS (SELECT 1 FROM target_cell_predictions x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:fk_components_detection_analysis'::text validation_name,(SELECT count(*) FROM public.image_connected_components r WHERE EXISTS (SELECT 1 FROM target_cell_detection_runs p WHERE r.detection_run_id=p.id AND r.analysis_run_id=p.analysis_run_id) AND NOT EXISTS (SELECT 1 FROM target_image_connected_components x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:fk_components_frozen_image'::text validation_name,(SELECT count(*) FROM public.image_connected_components r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_run_images p WHERE r.analysis_run_image_id=p.id AND r.analysis_run_id=p.analysis_run_id AND r.microscopy_image_id=p.microscopy_image_id) AND NOT EXISTS (SELECT 1 FROM target_image_connected_components x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:image_ingestion_batches_case_id_fkey'::text validation_name,(SELECT count(*) FROM public.image_ingestion_batches r WHERE EXISTS (SELECT 1 FROM target_scientific_cases p WHERE r.case_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_image_ingestion_batches x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:image_ingestion_batches_sample_id_fkey'::text validation_name,(SELECT count(*) FROM public.image_ingestion_batches r WHERE EXISTS (SELECT 1 FROM target_blood_samples p WHERE r.sample_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_image_ingestion_batches x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:image_ingestion_batches_slide_id_fkey'::text validation_name,(SELECT count(*) FROM public.image_ingestion_batches r WHERE EXISTS (SELECT 1 FROM target_smear_slides p WHERE r.slide_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_image_ingestion_batches x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:image_ingestion_batches_subject_id_fkey'::text validation_name,(SELECT count(*) FROM public.image_ingestion_batches r WHERE EXISTS (SELECT 1 FROM target_research_subjects p WHERE r.subject_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_image_ingestion_batches x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:image_quality_assessments_analysis_run_id_fkey'::text validation_name,(SELECT count(*) FROM public.image_quality_assessments r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE r.analysis_run_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_image_quality_assessments x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:image_quality_assessments_analysis_run_image_id_analysis_r_fkey'::text validation_name,(SELECT count(*) FROM public.image_quality_assessments r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_run_images p WHERE r.analysis_run_image_id=p.id AND r.analysis_run_id=p.analysis_run_id AND r.microscopy_image_id=p.microscopy_image_id) AND NOT EXISTS (SELECT 1 FROM target_image_quality_assessments x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:image_quality_assessments_microscopy_image_id_fkey'::text validation_name,(SELECT count(*) FROM public.image_quality_assessments r WHERE EXISTS (SELECT 1 FROM target_microscopy_images p WHERE r.microscopy_image_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_image_quality_assessments x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:microscopy_analysis_events_analysis_run_id_fkey'::text validation_name,(SELECT count(*) FROM public.microscopy_analysis_events r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE r.analysis_run_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_microscopy_analysis_events x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:microscopy_analysis_events_microscopy_image_id_fkey'::text validation_name,(SELECT count(*) FROM public.microscopy_analysis_events r WHERE EXISTS (SELECT 1 FROM target_microscopy_images p WHERE r.microscopy_image_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_microscopy_analysis_events x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:microscopy_analysis_run_images_analysis_run_id_fkey'::text validation_name,(SELECT count(*) FROM public.microscopy_analysis_run_images r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE r.analysis_run_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_microscopy_analysis_run_images x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:microscopy_analysis_run_images_microscopy_image_id_fkey'::text validation_name,(SELECT count(*) FROM public.microscopy_analysis_run_images r WHERE EXISTS (SELECT 1 FROM target_microscopy_images p WHERE r.microscopy_image_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_microscopy_analysis_run_images x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:microscopy_analysis_runs_case_id_fkey'::text validation_name,(SELECT count(*) FROM public.microscopy_analysis_runs r WHERE EXISTS (SELECT 1 FROM target_scientific_cases p WHERE r.case_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_microscopy_analysis_runs x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:microscopy_analysis_runs_ingestion_batch_id_fkey'::text validation_name,(SELECT count(*) FROM public.microscopy_analysis_runs r WHERE EXISTS (SELECT 1 FROM target_image_ingestion_batches p WHERE r.ingestion_batch_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_microscopy_analysis_runs x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:microscopy_analysis_runs_sample_id_fkey'::text validation_name,(SELECT count(*) FROM public.microscopy_analysis_runs r WHERE EXISTS (SELECT 1 FROM target_blood_samples p WHERE r.sample_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_microscopy_analysis_runs x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:microscopy_analysis_runs_slide_id_fkey'::text validation_name,(SELECT count(*) FROM public.microscopy_analysis_runs r WHERE EXISTS (SELECT 1 FROM target_smear_slides p WHERE r.slide_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_microscopy_analysis_runs x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:microscopy_analysis_runs_subject_id_fkey'::text validation_name,(SELECT count(*) FROM public.microscopy_analysis_runs r WHERE EXISTS (SELECT 1 FROM target_research_subjects p WHERE r.subject_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_microscopy_analysis_runs x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:microscopy_images_ingestion_batch_id_fkey'::text validation_name,(SELECT count(*) FROM public.microscopy_images r WHERE EXISTS (SELECT 1 FROM target_image_ingestion_batches p WHERE r.ingestion_batch_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_microscopy_images x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:microscopy_images_slide_id_fkey'::text validation_name,(SELECT count(*) FROM public.microscopy_images r WHERE EXISTS (SELECT 1 FROM target_smear_slides p WHERE r.slide_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_microscopy_images x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:quality_assessment_queue_items_analysis_run_id_fkey'::text validation_name,(SELECT count(*) FROM public.quality_assessment_queue_items r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE r.analysis_run_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_quality_assessment_queue_items x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:quality_gate_decisions_analysis_run_id_fkey'::text validation_name,(SELECT count(*) FROM public.quality_gate_decisions r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE r.analysis_run_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_quality_gate_decisions x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:scientific_cases_subject_id_fkey'::text validation_name,(SELECT count(*) FROM public.scientific_cases r WHERE EXISTS (SELECT 1 FROM target_research_subjects p WHERE r.subject_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_scientific_cases x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:scientific_reviews_entity_id_fkey'::text validation_name,(SELECT count(*) FROM public.scientific_reviews r WHERE EXISTS (SELECT 1 FROM target_cell_detections p WHERE r.entity_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_scientific_reviews x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:scientific_validation_annotations_analysis_run_id_fkey'::text validation_name,(SELECT count(*) FROM public.scientific_validation_annotations r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE r.analysis_run_id=p.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:scientific_validation_annotations_cell_detection_id_fkey'::text validation_name,(SELECT count(*) FROM public.scientific_validation_annotations r WHERE EXISTS (SELECT 1 FROM target_cell_detections p WHERE r.cell_detection_id=p.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:scientific_validation_annotations_sample_id_fkey'::text validation_name,(SELECT count(*) FROM public.scientific_validation_annotations r WHERE EXISTS (SELECT 1 FROM target_blood_samples p WHERE r.sample_id=p.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:scientific_validation_classification_classification_run_id_fkey'::text validation_name,(SELECT count(*) FROM public.scientific_validation_classification_runs r WHERE EXISTS (SELECT 1 FROM target_cell_classification_runs p WHERE r.classification_run_id=p.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:scientific_validation_detection_runs_detection_run_id_fkey'::text validation_name,(SELECT count(*) FROM public.scientific_validation_detection_runs r WHERE EXISTS (SELECT 1 FROM target_cell_detection_runs p WHERE r.detection_run_id=p.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:scientific_validation_images_microscopy_image_id_fkey'::text validation_name,(SELECT count(*) FROM public.scientific_validation_images r WHERE EXISTS (SELECT 1 FROM target_microscopy_images p WHERE r.microscopy_image_id=p.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:fk_smear_summary_classification_lineage'::text validation_name,(SELECT count(*) FROM public.smear_analysis_summaries r WHERE EXISTS (SELECT 1 FROM target_cell_classification_runs p WHERE r.classification_run_id=p.id AND r.analysis_run_id=p.analysis_run_id AND r.detection_run_id=p.detection_run_id) AND NOT EXISTS (SELECT 1 FROM target_smear_analysis_summaries x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'inbound:smear_slides_sample_id_fkey'::text validation_name,(SELECT count(*) FROM public.smear_slides r WHERE EXISTS (SELECT 1 FROM target_blood_samples p WHERE r.sample_id=p.id) AND NOT EXISTS (SELECT 1 FROM target_smear_slides x WHERE x.id=r.id))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:artifacts'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='artifacts')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:artifacts'::text validation_name,(SELECT count(*) FROM public.artifacts r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.run_id,r.path,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:classification_reports'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='classification_reports')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:classification_reports'::text validation_name,(SELECT count(*) FROM public.classification_reports r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.run_id,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:clinical_identities'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='clinical_identities')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:clinical_identities'::text validation_name,(SELECT count(*) FROM public.clinical_identities r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.dataset_id,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:confusion_matrices'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='confusion_matrices')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:confusion_matrices'::text validation_name,(SELECT count(*) FROM public.confusion_matrices r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.run_id,r.matrix,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:dataset_materialization_activations'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='dataset_materialization_activations')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:dataset_materialization_activations'::text validation_name,(SELECT count(*) FROM public.dataset_materialization_activations r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.dataset_version_id,r.materialization_id,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:dataset_materializations'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='dataset_materializations')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:dataset_materializations'::text validation_name,(SELECT count(*) FROM public.dataset_materializations r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.dataset_version_id,r.manifest_metadata,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:dataset_source_records'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='dataset_source_records')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:dataset_source_records'::text validation_name,(SELECT count(*) FROM public.dataset_source_records r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.dataset_id,r.clinical_identity_id,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:dataset_split_assignments'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='dataset_split_assignments')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:dataset_split_assignments'::text validation_name,(SELECT count(*) FROM public.dataset_split_assignments r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.dataset_version_id,r.source_record_id,r.clinical_identity_id,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:dataset_split_images'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='dataset_split_images')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:dataset_split_images'::text validation_name,(SELECT count(*) FROM public.dataset_split_images r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.image_id,r.dataset_id,r.relative_path,r.absolute_path,r.metadata,r.dataset_version_id,r.dataset_materialization_id),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:dataset_split_statistics'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='dataset_split_statistics')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:dataset_split_statistics'::text validation_name,(SELECT count(*) FROM public.dataset_split_statistics r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.dataset_version_id,r.details_json),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:dataset_split_validation_checks'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='dataset_split_validation_checks')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:dataset_split_validation_checks'::text validation_name,(SELECT count(*) FROM public.dataset_split_validation_checks r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.dataset_version_id,r.details_json),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:dataset_splits'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='dataset_splits')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:dataset_splits'::text validation_name,(SELECT count(*) FROM public.dataset_splits r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.dataset_id,r.class_distribution,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:dataset_version_sources'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='dataset_version_sources')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:dataset_version_sources'::text validation_name,(SELECT count(*) FROM public.dataset_version_sources r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.dataset_version_id,r.dataset_id),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:dataset_versions'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='dataset_versions')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:dataset_versions'::text validation_name,(SELECT count(*) FROM public.dataset_versions r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.class_mapping,r.methodology_json),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:datasets'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='datasets')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:datasets'::text validation_name,(SELECT count(*) FROM public.datasets r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.class_distribution,r.local_path,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:deployed_model_versions'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='deployed_model_versions')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:deployed_model_versions'::text validation_name,(SELECT count(*) FROM public.deployed_model_versions r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.model_version_id,r.checkpoint_artifact_id,r.threshold_calibration_id,r.threshold_profile_snapshot,r.preprocessing_profile_snapshot,r.image_quality_policy_snapshot,r.label_mapping_snapshot,r.supersedes_deployment_id,r.rollback_of_deployment_id,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:environment_packages'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='environment_packages')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:environment_packages'::text validation_name,(SELECT count(*) FROM public.environment_packages r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.run_id),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:errors'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='errors')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:errors'::text validation_name,(SELECT count(*) FROM public.errors r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.run_id,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:execution_logs'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='execution_logs')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:execution_logs'::text validation_name,(SELECT count(*) FROM public.execution_logs r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.run_id,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:experiments'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='experiments')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:experiments'::text validation_name,(SELECT count(*) FROM public.experiments r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:explainability_results'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='explainability_results')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:explainability_results'::text validation_name,(SELECT count(*) FROM public.explainability_results r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.run_id,r.prediction_id,r.image_path,r.output_path,r.explanation_parameters,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:identity_evidence'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='identity_evidence')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:identity_evidence'::text validation_name,(SELECT count(*) FROM public.identity_evidence r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.source_record_id,r.clinical_identity_id,r.evidence_json),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:image_analysis_jobs'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='image_analysis_jobs')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:image_analysis_jobs'::text validation_name,(SELECT count(*) FROM public.image_analysis_jobs r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.inference_run_id,r.deployed_model_version_id,r.model_version_id,r.input_artifact_id,r.source_image_id,r.quality_metrics,r.summary,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:model_governance_backfill_audit'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='model_governance_backfill_audit')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:model_governance_backfill_audit'::text validation_name,(SELECT count(*) FROM public.model_governance_backfill_audit r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.batch_id,r.reversal_of_audit_id,r.record_id,r.before_values,r.after_values,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:model_versions'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='model_versions')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:model_versions'::text validation_name,(SELECT count(*) FROM public.model_versions r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.model_id,r.checkpoint_path,r.final_model_path,r.best_model_path,r.training_run_id,r.metadata,r.checkpoint_artifact_id,r.preprocessing_profile_snapshot,r.class_mapping,r.input_signature,r.output_signature),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:models'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='models')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:models'::text validation_name,(SELECT count(*) FROM public.models r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:predictions'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='predictions')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:predictions'::text validation_name,(SELECT count(*) FROM public.predictions r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.run_id,r.dataset_id,r.image_path,r.metadata,r.image_analysis_job_id,r.model_version_id,r.deployed_model_version_id,r.inference_run_id,r.classifier_model_version_id,r.detector_model_version_id,r.source_image_id,r.crop_artifact_id,r.explanation_artifact_id),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:roles'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='roles')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:roles'::text validation_name,(SELECT count(*) FROM public.roles r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:run_checkpoint_policy'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='run_checkpoint_policy')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:run_checkpoint_policy'::text validation_name,(SELECT count(*) FROM public.run_checkpoint_policy r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.run_checkpoint_policy_id,r.run_id,r.checkpoint_policy_config,r.checkpoint_path,r.checkpoint_policy_summary_path,r.model_metadata_path,r.metadata,r.model_version_id,r.checkpoint_artifact_id),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:run_clinical_metrics'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='run_clinical_metrics')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:run_clinical_metrics'::text validation_name,(SELECT count(*) FROM public.run_clinical_metrics r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.run_clinical_metric_id,r.run_id,r.model_id,r.confusion_matrix,r.classification_report,r.prediction_distribution,r.prediction_collapse,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:run_dataset_images'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='run_dataset_images')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:run_dataset_images'::text validation_name,(SELECT count(*) FROM public.run_dataset_images r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.run_dataset_image_id,r.run_id,r.image_id,r.relative_path,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:run_image_predictions'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='run_image_predictions')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:run_image_predictions'::text validation_name,(SELECT count(*) FROM public.run_image_predictions r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.run_image_prediction_id,r.run_id,r.image_id,r.relative_path,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:run_io_records'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='run_io_records')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:run_io_records'::text validation_name,(SELECT count(*) FROM public.run_io_records r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.run_io_id,r.run_id,r.input_parameters,r.output_results,r.output_artifacts,r.dataset_metadata,r.metadata,r.model_metadata,r.clinical_metadata,r.dataset_version_id,r.dataset_materialization_id),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:run_lineage'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='run_lineage')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:run_lineage'::text validation_name,(SELECT count(*) FROM public.run_lineage r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.parent_run_id,r.child_run_id,r.checkpoint_path,r.checkpoint_artifact_id,r.model_version_id,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:run_metrics'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='run_metrics')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:run_metrics'::text validation_name,(SELECT count(*) FROM public.run_metrics r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.run_id,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:run_model_deployments'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='run_model_deployments')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:run_model_deployments'::text validation_name,(SELECT count(*) FROM public.run_model_deployments r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.run_id,r.deployed_model_version_id,r.model_version_id,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:run_threshold_calibration'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='run_threshold_calibration')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:run_threshold_calibration'::text validation_name,(SELECT count(*) FROM public.run_threshold_calibration r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.run_threshold_calibration_id,r.run_id,r.default_threshold_metrics,r.selected_threshold_metrics,r.threshold_calibration_path,r.model_metadata_path,r.metadata,r.model_version_id,r.calibration_artifact_id),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:runs'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='runs')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:runs'::text validation_name,(SELECT count(*) FROM public.runs r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.experiment_id,r.model_id,r.dataset_id,r.gpu_devices,r.parameters,r.metadata,r.execution_parameters,r.configuration,r.dataset_version_id),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:schema_migrations'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='schema_migrations')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:schema_migrations'::text validation_name,(SELECT count(*) FROM public.schema_migrations r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.execution_metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:scientific_validation_annotation_events'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='scientific_validation_annotation_events')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:scientific_validation_annotation_events'::text validation_name,(SELECT count(*) FROM public.scientific_validation_annotation_events r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.annotation_id,r.validation_session_id,r.actor_user_id,r.before_state,r.after_state),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:scientific_validation_annotations'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='scientific_validation_annotations')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:scientific_validation_annotations'::text validation_name,(SELECT count(*) FROM public.scientific_validation_annotations r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.validation_session_id,r.cell_detection_id,r.analysis_run_id,r.created_by,r.updated_by,r.sample_id),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:scientific_validation_classification_runs'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='scientific_validation_classification_runs')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:scientific_validation_classification_runs'::text validation_name,(SELECT count(*) FROM public.scientific_validation_classification_runs r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.session_id,r.classification_run_id),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:scientific_validation_detection_runs'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='scientific_validation_detection_runs')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:scientific_validation_detection_runs'::text validation_name,(SELECT count(*) FROM public.scientific_validation_detection_runs r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.session_id,r.detection_run_id),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:scientific_validation_images'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='scientific_validation_images')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:scientific_validation_images'::text validation_name,(SELECT count(*) FROM public.scientific_validation_images r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.session_id,r.microscopy_image_id),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:scientific_validation_sessions'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='scientific_validation_sessions')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:scientific_validation_sessions'::text validation_name,(SELECT count(*) FROM public.scientific_validation_sessions r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.initial_snapshot,r.created_by,r.updated_by,r.archived_by),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:stage2_model_publication_events'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='stage2_model_publication_events')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:stage2_model_publication_events'::text validation_name,(SELECT count(*) FROM public.stage2_model_publication_events r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.publication_id,r.model_version_id,r.training_run_id,r.evaluation_run_id,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:stage2_model_publications'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='stage2_model_publications')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:stage2_model_publications'::text validation_name,(SELECT count(*) FROM public.stage2_model_publications r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.model_version_id,r.training_run_id,r.evaluation_run_id,r.checkpoint_artifact_id,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:synthetic_data_runs'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='synthetic_data_runs')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:synthetic_data_runs'::text validation_name,(SELECT count(*) FROM public.synthetic_data_runs r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.run_id,r.source_dataset_id,r.output_path,r.generation_parameters,r.quality_checks,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:training_history'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='training_history')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:training_history'::text validation_name,(SELECT count(*) FROM public.training_history r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id,r.run_id,r.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:user_roles'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='user_roles')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:user_roles'::text validation_name,(SELECT count(*) FROM public.user_roles r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.user_id,r.role_id),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'excluded_table:users'::text validation_name,(SELECT count(*) FROM targets WHERE table_name='users')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserved_exact_reference:users'::text validation_name,(SELECT count(*) FROM public.users r WHERE EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(r.id),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserve:TRAIN'::text validation_name,(SELECT count(*) FROM targets WHERE table_name IN ('runs','run_lineage','model_versions','explainability_results'))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserve:EVALUATE'::text validation_name,(SELECT count(*) FROM targets WHERE table_name IN ('runs','run_lineage','model_versions','explainability_results'))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserve:EXPLAIN'::text validation_name,(SELECT count(*) FROM targets WHERE table_name IN ('runs','run_lineage','model_versions','explainability_results'))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'preserve:release_*'::text validation_name,(SELECT count(*) FROM targets WHERE table_name IN ('runs','run_lineage','model_versions','explainability_results'))::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'schema_contract'::text validation_name,(SELECT count(*) FROM (VALUES ('blood_samples','blood_samples_archived_by_fkey','FOREIGN KEY (archived_by) REFERENCES users(id) ON DELETE RESTRICT'),('blood_samples','blood_samples_case_id_fkey','FOREIGN KEY (case_id) REFERENCES scientific_cases(id) ON DELETE RESTRICT'),('blood_samples','blood_samples_created_by_fkey','FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT'),('blood_samples','blood_samples_pkey','PRIMARY KEY (id)'),('blood_samples','blood_samples_updated_by_fkey','FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT'),('cell_classification_events','cell_classification_events_cell_detection_id_fkey','FOREIGN KEY (cell_detection_id) REFERENCES cell_detections(id) ON DELETE RESTRICT'),('cell_classification_events','cell_classification_events_classification_run_id_fkey','FOREIGN KEY (classification_run_id) REFERENCES cell_classification_runs(id) ON DELETE RESTRICT'),('cell_classification_events','cell_classification_events_pkey','PRIMARY KEY (id)'),('cell_classification_events','fk_cell_classification_event_prediction','FOREIGN KEY (cell_prediction_id, classification_run_id) REFERENCES cell_predictions(id, classification_run_id) ON DELETE RESTRICT'),('cell_classification_inputs','cell_classification_inputs_pkey','PRIMARY KEY (id)'),('cell_classification_inputs','fk_cell_classification_input_crop','FOREIGN KEY (crop_id, cell_detection_id) REFERENCES cell_crops(id, cell_detection_id) ON DELETE RESTRICT'),('cell_classification_inputs','fk_cell_classification_input_detection','FOREIGN KEY (cell_detection_id, detection_run_id, microscopy_image_id) REFERENCES cell_detections(id, detection_run_id, microscopy_image_id) ON DELETE RESTRICT'),('cell_classification_inputs','fk_cell_classification_input_run_detection','FOREIGN KEY (classification_run_id, detection_run_id) REFERENCES cell_classification_runs(id, detection_run_id) ON DELETE RESTRICT'),('cell_classification_reviews','cell_classification_reviews_actor_user_id_fkey','FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT'),('cell_classification_reviews','cell_classification_reviews_cell_prediction_id_fkey','FOREIGN KEY (cell_prediction_id) REFERENCES cell_predictions(id) ON DELETE RESTRICT'),('cell_classification_reviews','cell_classification_reviews_pkey','PRIMARY KEY (id)'),('cell_classification_runs','cell_classification_runs_pkey','PRIMARY KEY (id)'),('cell_classification_runs','cell_classification_runs_requested_by_fkey','FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE RESTRICT'),('cell_classification_runs','cell_classification_runs_retry_of_run_id_fkey','FOREIGN KEY (retry_of_run_id) REFERENCES cell_classification_runs(id) ON DELETE RESTRICT'),('cell_classification_runs','fk_cell_classification_run_deployment_version','FOREIGN KEY (production_model_id, model_registry_id) REFERENCES deployed_model_versions(id, model_version_id) ON DELETE RESTRICT'),('cell_classification_runs','fk_cell_classification_run_detection_analysis','FOREIGN KEY (detection_run_id, analysis_run_id) REFERENCES cell_detection_runs(id, analysis_run_id) ON DELETE RESTRICT'),('cell_classification_runs','fk_cell_classification_run_publication_version','FOREIGN KEY (stage2_publication_id, model_registry_id) REFERENCES stage2_model_publications(id, model_version_id) ON DELETE RESTRICT'),('cell_crops','cell_crops_pkey','PRIMARY KEY (id)'),('cell_crops','fk_cell_crops_detection','FOREIGN KEY (cell_detection_id) REFERENCES cell_detections(id) ON DELETE RESTRICT'),('cell_detection_events','cell_detection_events_detection_run_id_fkey','FOREIGN KEY (detection_run_id) REFERENCES cell_detection_runs(id) ON DELETE RESTRICT'),('cell_detection_events','cell_detection_events_microscopy_image_id_fkey','FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images(id) ON DELETE RESTRICT'),('cell_detection_events','cell_detection_events_pkey','PRIMARY KEY (id)'),('cell_detection_runs','cell_detection_runs_analysis_run_id_fkey','FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT'),('cell_detection_runs','cell_detection_runs_pkey','PRIMARY KEY (id)'),('cell_detection_runs','cell_detection_runs_requested_by_fkey','FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE RESTRICT'),('cell_detections','cell_detections_pkey','PRIMARY KEY (id)'),('cell_detections','fk_cell_detections_component','FOREIGN KEY (connected_component_id, detection_run_id, analysis_run_image_id, microscopy_image_id) REFERENCES image_connected_components(id, detection_run_id, analysis_run_image_id, microscopy_image_id) ON DELETE RESTRICT'),('cell_detections','fk_cell_detections_run_analysis','FOREIGN KEY (detection_run_id, analysis_run_id) REFERENCES cell_detection_runs(id, analysis_run_id) ON DELETE RESTRICT'),('cell_explanations','cell_explanations_cell_prediction_id_fkey','FOREIGN KEY (cell_prediction_id) REFERENCES cell_predictions(id) ON DELETE RESTRICT'),('cell_explanations','cell_explanations_pkey','PRIMARY KEY (id)'),('cell_predictions','cell_predictions_pkey','PRIMARY KEY (id)'),('cell_predictions','fk_cell_prediction_input_owner','FOREIGN KEY (classification_input_id, classification_run_id, cell_detection_id, crop_id) REFERENCES cell_classification_inputs(id, classification_run_id, cell_detection_id, crop_id) ON DELETE RESTRICT'),('image_connected_components','fk_components_detection_analysis','FOREIGN KEY (detection_run_id, analysis_run_id) REFERENCES cell_detection_runs(id, analysis_run_id) ON DELETE RESTRICT'),('image_connected_components','fk_components_frozen_image','FOREIGN KEY (analysis_run_image_id, analysis_run_id, microscopy_image_id) REFERENCES microscopy_analysis_run_images(id, analysis_run_id, microscopy_image_id) ON DELETE RESTRICT'),('image_connected_components','image_connected_components_pkey','PRIMARY KEY (id)'),('image_ingestion_batches','image_ingestion_batches_case_id_fkey','FOREIGN KEY (case_id) REFERENCES scientific_cases(id) ON DELETE RESTRICT'),('image_ingestion_batches','image_ingestion_batches_created_by_fkey','FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT'),('image_ingestion_batches','image_ingestion_batches_pkey','PRIMARY KEY (id)'),('image_ingestion_batches','image_ingestion_batches_sample_id_fkey','FOREIGN KEY (sample_id) REFERENCES blood_samples(id) ON DELETE RESTRICT'),('image_ingestion_batches','image_ingestion_batches_slide_id_fkey','FOREIGN KEY (slide_id) REFERENCES smear_slides(id) ON DELETE RESTRICT'),('image_ingestion_batches','image_ingestion_batches_subject_id_fkey','FOREIGN KEY (subject_id) REFERENCES research_subjects(id) ON DELETE RESTRICT'),('image_quality_assessments','image_quality_assessments_analysis_run_id_fkey','FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT'),('image_quality_assessments','image_quality_assessments_analysis_run_image_id_analysis_r_fkey','FOREIGN KEY (analysis_run_image_id, analysis_run_id, microscopy_image_id) REFERENCES microscopy_analysis_run_images(id, analysis_run_id, microscopy_image_id) ON DELETE RESTRICT'),('image_quality_assessments','image_quality_assessments_microscopy_image_id_fkey','FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images(id) ON DELETE RESTRICT'),('image_quality_assessments','image_quality_assessments_pkey','PRIMARY KEY (id)'),('microscopy_analysis_events','microscopy_analysis_events_analysis_run_id_fkey','FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT'),('microscopy_analysis_events','microscopy_analysis_events_microscopy_image_id_fkey','FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images(id) ON DELETE RESTRICT'),('microscopy_analysis_events','microscopy_analysis_events_pkey','PRIMARY KEY (id)'),('microscopy_analysis_run_images','microscopy_analysis_run_images_analysis_run_id_fkey','FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT'),('microscopy_analysis_run_images','microscopy_analysis_run_images_microscopy_image_id_fkey','FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images(id) ON DELETE RESTRICT'),('microscopy_analysis_run_images','microscopy_analysis_run_images_pkey','PRIMARY KEY (id)'),('microscopy_analysis_runs','microscopy_analysis_runs_case_id_fkey','FOREIGN KEY (case_id) REFERENCES scientific_cases(id) ON DELETE RESTRICT'),('microscopy_analysis_runs','microscopy_analysis_runs_ingestion_batch_id_fkey','FOREIGN KEY (ingestion_batch_id) REFERENCES image_ingestion_batches(id) ON DELETE RESTRICT'),('microscopy_analysis_runs','microscopy_analysis_runs_pkey','PRIMARY KEY (id)'),('microscopy_analysis_runs','microscopy_analysis_runs_requested_by_fkey','FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE RESTRICT'),('microscopy_analysis_runs','microscopy_analysis_runs_sample_id_fkey','FOREIGN KEY (sample_id) REFERENCES blood_samples(id) ON DELETE RESTRICT'),('microscopy_analysis_runs','microscopy_analysis_runs_slide_id_fkey','FOREIGN KEY (slide_id) REFERENCES smear_slides(id) ON DELETE RESTRICT'),('microscopy_analysis_runs','microscopy_analysis_runs_subject_id_fkey','FOREIGN KEY (subject_id) REFERENCES research_subjects(id) ON DELETE RESTRICT'),('microscopy_images','microscopy_images_archived_by_fkey','FOREIGN KEY (archived_by) REFERENCES users(id) ON DELETE RESTRICT'),('microscopy_images','microscopy_images_created_by_fkey','FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT'),('microscopy_images','microscopy_images_ingestion_batch_id_fkey','FOREIGN KEY (ingestion_batch_id) REFERENCES image_ingestion_batches(id) ON DELETE RESTRICT'),('microscopy_images','microscopy_images_pkey','PRIMARY KEY (id)'),('microscopy_images','microscopy_images_slide_id_fkey','FOREIGN KEY (slide_id) REFERENCES smear_slides(id) ON DELETE RESTRICT'),('microscopy_images','microscopy_images_updated_by_fkey','FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT'),('quality_assessment_queue_items','quality_assessment_queue_items_analysis_run_id_fkey','FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT'),('quality_assessment_queue_items','quality_assessment_queue_items_pkey','PRIMARY KEY (id)'),('quality_assessment_queue_items','quality_assessment_queue_items_requested_by_fkey','FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE RESTRICT'),('quality_gate_decisions','quality_gate_decisions_actor_user_id_fkey','FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT'),('quality_gate_decisions','quality_gate_decisions_analysis_run_id_fkey','FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT'),('quality_gate_decisions','quality_gate_decisions_pkey','PRIMARY KEY (id)'),('research_subjects','research_subjects_archived_by_fkey','FOREIGN KEY (archived_by) REFERENCES users(id) ON DELETE RESTRICT'),('research_subjects','research_subjects_created_by_fkey','FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT'),('research_subjects','research_subjects_pkey','PRIMARY KEY (id)'),('research_subjects','research_subjects_updated_by_fkey','FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT'),('scientific_cases','scientific_cases_archived_by_fkey','FOREIGN KEY (archived_by) REFERENCES users(id) ON DELETE RESTRICT'),('scientific_cases','scientific_cases_created_by_fkey','FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT'),('scientific_cases','scientific_cases_pkey','PRIMARY KEY (id)'),('scientific_cases','scientific_cases_subject_id_fkey','FOREIGN KEY (subject_id) REFERENCES research_subjects(id) ON DELETE RESTRICT'),('scientific_cases','scientific_cases_updated_by_fkey','FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT'),('scientific_reviews','scientific_reviews_actor_user_id_fkey','FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT'),('scientific_reviews','scientific_reviews_entity_id_fkey','FOREIGN KEY (entity_id) REFERENCES cell_detections(id) ON DELETE RESTRICT'),('scientific_reviews','scientific_reviews_pkey','PRIMARY KEY (id)'),('scientific_validation_annotations','scientific_validation_annotations_analysis_run_id_fkey','FOREIGN KEY (analysis_run_id) REFERENCES microscopy_analysis_runs(id) ON DELETE RESTRICT'),('scientific_validation_annotations','scientific_validation_annotations_cell_detection_id_fkey','FOREIGN KEY (cell_detection_id) REFERENCES cell_detections(id) ON DELETE RESTRICT'),('scientific_validation_annotations','scientific_validation_annotations_sample_id_fkey','FOREIGN KEY (sample_id) REFERENCES blood_samples(id) ON DELETE RESTRICT'),('scientific_validation_classification_runs','scientific_validation_classification_classification_run_id_fkey','FOREIGN KEY (classification_run_id) REFERENCES cell_classification_runs(id) ON DELETE RESTRICT'),('scientific_validation_detection_runs','scientific_validation_detection_runs_detection_run_id_fkey','FOREIGN KEY (detection_run_id) REFERENCES cell_detection_runs(id) ON DELETE RESTRICT'),('scientific_validation_images','scientific_validation_images_microscopy_image_id_fkey','FOREIGN KEY (microscopy_image_id) REFERENCES microscopy_images(id) ON DELETE RESTRICT'),('smear_analysis_summaries','fk_smear_summary_classification_lineage','FOREIGN KEY (classification_run_id, analysis_run_id, detection_run_id) REFERENCES cell_classification_runs(id, analysis_run_id, detection_run_id) ON DELETE RESTRICT'),('smear_analysis_summaries','smear_analysis_summaries_pkey','PRIMARY KEY (id)'),('smear_slides','smear_slides_archived_by_fkey','FOREIGN KEY (archived_by) REFERENCES users(id) ON DELETE RESTRICT'),('smear_slides','smear_slides_created_by_fkey','FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT'),('smear_slides','smear_slides_pkey','PRIMARY KEY (id)'),('smear_slides','smear_slides_sample_id_fkey','FOREIGN KEY (sample_id) REFERENCES blood_samples(id) ON DELETE RESTRICT'),('smear_slides','smear_slides_updated_by_fkey','FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE RESTRICT')) expected(child,name,definition) FULL JOIN (SELECT conrelid::regclass::text child,conname name,pg_get_constraintdef(oid) definition FROM pg_constraint WHERE connamespace='public'::regnamespace AND contype IN ('p','f') AND (conrelid::regclass::text IN (SELECT table_name FROM table_catalog) OR confrelid::regclass::text IN (SELECT table_name FROM table_catalog))) actual USING(child,name) WHERE expected.definition IS DISTINCT FROM actual.definition)::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'invalid_clinical_storage'::text validation_name,(SELECT count(*) FROM clinical_storage WHERE storage_key !~ '^(microscopy-images|cell-crops|cell-explanations)/' OR storage_key ~ '(^|/)\.\.?(/|$)' OR storage_key LIKE '%//%')::bigint conflict_count,0::bigint expected_count
UNION ALL
SELECT 'ambiguous_audit'::text validation_name,(SELECT count(*) FROM audit_classified WHERE classification='ambiguous')::bigint conflict_count,0::bigint expected_count)
SELECT *,CASE WHEN conflict_count=expected_count THEN 'PASS' ELSE 'FAIL' END status FROM validations ORDER BY validation_name;

-- REPORT audit
WITH RECURSIVE
target_image_ingestion_batches AS (SELECT r.* FROM public.image_ingestion_batches r),
target_microscopy_analysis_runs AS (SELECT r.* FROM public.microscopy_analysis_runs r),
target_microscopy_analysis_run_images AS (SELECT r.* FROM public.microscopy_analysis_run_images r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_cell_detection_runs AS (SELECT r.* FROM public.cell_detection_runs r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_cell_detections AS (SELECT r.* FROM public.cell_detections r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_image_connected_components AS (SELECT r.* FROM public.image_connected_components r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_cell_crops AS (SELECT r.* FROM public.cell_crops r JOIN target_cell_detections p ON r.cell_detection_id=p.id),
target_cell_detection_events AS (SELECT r.* FROM public.cell_detection_events r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_scientific_reviews AS (SELECT r.* FROM public.scientific_reviews r JOIN target_cell_detections p ON r.entity_id=p.id),
target_cell_classification_runs AS (SELECT r.* FROM public.cell_classification_runs r JOIN target_cell_detection_runs p ON r.detection_run_id=p.id),
target_cell_classification_inputs AS (SELECT r.* FROM public.cell_classification_inputs r JOIN target_cell_classification_runs p ON r.classification_run_id=p.id),
target_cell_predictions AS (SELECT r.* FROM public.cell_predictions r JOIN target_cell_classification_inputs p ON r.classification_input_id=p.id),
target_cell_explanations AS (SELECT r.* FROM public.cell_explanations r JOIN target_cell_predictions p ON r.cell_prediction_id=p.id),
target_cell_classification_reviews AS (SELECT r.* FROM public.cell_classification_reviews r JOIN target_cell_predictions p ON r.cell_prediction_id=p.id),
target_cell_classification_events AS (SELECT r.* FROM public.cell_classification_events r JOIN target_cell_classification_runs p ON r.classification_run_id=p.id),
target_smear_analysis_summaries AS (SELECT r.* FROM public.smear_analysis_summaries r JOIN target_cell_classification_runs p ON r.classification_run_id=p.id),
target_image_quality_assessments AS (SELECT r.* FROM public.image_quality_assessments r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_quality_gate_decisions AS (SELECT r.* FROM public.quality_gate_decisions r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_quality_assessment_queue_items AS (SELECT r.* FROM public.quality_assessment_queue_items r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_microscopy_analysis_events AS (SELECT r.* FROM public.microscopy_analysis_events r JOIN target_microscopy_analysis_runs p ON r.analysis_run_id=p.id),
target_microscopy_images AS (SELECT r.* FROM public.microscopy_images r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_run_images p WHERE p.microscopy_image_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.id=r.ingestion_batch_id)),
target_smear_slides AS (SELECT r.* FROM public.smear_slides r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.slide_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.slide_id=r.id)),
target_blood_samples AS (SELECT r.* FROM public.blood_samples r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.sample_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.sample_id=r.id)),
target_scientific_cases AS (SELECT r.* FROM public.scientific_cases r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.case_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.case_id=r.id)),
target_research_subjects AS (SELECT r.* FROM public.research_subjects r WHERE EXISTS (SELECT 1 FROM target_microscopy_analysis_runs p WHERE p.subject_id=r.id) OR EXISTS (SELECT 1 FROM target_image_ingestion_batches b WHERE b.subject_id=r.id)),
table_catalog(delete_order,table_name,primary_key_column,selection_reason) AS (VALUES (1,'cell_explanations','id','JOIN cell_prediction_id al conjunto cell_predictions'),
(2,'cell_classification_reviews','id','JOIN cell_prediction_id al conjunto cell_predictions'),
(3,'cell_classification_events','id','JOIN classification_run_id al conjunto cell_classification_runs'),
(4,'smear_analysis_summaries','id','JOIN classification_run_id al conjunto cell_classification_runs'),
(5,'cell_predictions','id','JOIN classification_input_id al conjunto cell_classification_inputs'),
(6,'cell_classification_inputs','id','JOIN classification_run_id al conjunto cell_classification_runs'),
(7,'cell_classification_runs','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(8,'scientific_reviews','id','JOIN entity_id al conjunto cell_detections'),
(9,'cell_crops','id','JOIN cell_detection_id al conjunto cell_detections'),
(10,'cell_detection_events','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(11,'cell_detections','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(12,'image_connected_components','id','JOIN detection_run_id al conjunto cell_detection_runs'),
(13,'cell_detection_runs','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(14,'quality_gate_decisions','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(15,'quality_assessment_queue_items','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(16,'microscopy_analysis_events','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(17,'image_quality_assessments','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(18,'microscopy_analysis_run_images','id','JOIN analysis_run_id al conjunto microscopy_analysis_runs'),
(19,'microscopy_analysis_runs','id','Raíz del flujo de ingesta o análisis'),
(20,'microscopy_images','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(21,'image_ingestion_batches','id','Raíz del flujo de ingesta o análisis'),
(22,'smear_slides','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(23,'blood_samples','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(24,'scientific_cases','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'),
(25,'research_subjects','id','Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga')),
targets AS (SELECT 1 delete_order, 'cell_explanations'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_predictions'::text parent_table, r.cell_prediction_id::text parent_record_id, 'JOIN cell_prediction_id al conjunto cell_predictions'::text selection_reason, jsonb_build_array(r.cell_prediction_id,r.heatmap_storage_key,r.id,r.overlay_storage_key,r.status) fingerprint_values FROM target_cell_explanations r
UNION ALL
SELECT 2 delete_order, 'cell_classification_reviews'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_predictions'::text parent_table, r.cell_prediction_id::text parent_record_id, 'JOIN cell_prediction_id al conjunto cell_predictions'::text selection_reason, jsonb_build_array(r.actor_user_id,r.cell_prediction_id,r.id) fingerprint_values FROM target_cell_classification_reviews r
UNION ALL
SELECT 3 delete_order, 'cell_classification_events'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_runs'::text parent_table, r.classification_run_id::text parent_record_id, 'JOIN classification_run_id al conjunto cell_classification_runs'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.cell_prediction_id,r.classification_run_id,r.id,r.status) fingerprint_values FROM target_cell_classification_events r
UNION ALL
SELECT 4 delete_order, 'smear_analysis_summaries'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_runs'::text parent_table, r.classification_run_id::text parent_record_id, 'JOIN classification_run_id al conjunto cell_classification_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.classification_run_id,r.detection_run_id,r.id) fingerprint_values FROM target_smear_analysis_summaries r
UNION ALL
SELECT 5 delete_order, 'cell_predictions'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_inputs'::text parent_table, r.classification_input_id::text parent_record_id, 'JOIN classification_input_id al conjunto cell_classification_inputs'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.classification_input_id,r.classification_run_id,r.crop_id,r.id) fingerprint_values FROM target_cell_predictions r
UNION ALL
SELECT 6 delete_order, 'cell_classification_inputs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_classification_runs'::text parent_table, r.classification_run_id::text parent_record_id, 'JOIN classification_run_id al conjunto cell_classification_runs'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.classification_run_id,r.crop_id,r.detection_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_cell_classification_inputs r
UNION ALL
SELECT 7 delete_order, 'cell_classification_runs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.detection_run_id,r.id,r.model_registry_id,r.production_model_id,r.requested_by,r.retry_of_run_id,r.stage2_publication_id,r.status) fingerprint_values FROM target_cell_classification_runs r
UNION ALL
SELECT 8 delete_order, 'scientific_reviews'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detections'::text parent_table, r.entity_id::text parent_record_id, 'JOIN entity_id al conjunto cell_detections'::text selection_reason, jsonb_build_array(r.actor_user_id,r.entity_id,r.id) fingerprint_values FROM target_scientific_reviews r
UNION ALL
SELECT 9 delete_order, 'cell_crops'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detections'::text parent_table, r.cell_detection_id::text parent_record_id, 'JOIN cell_detection_id al conjunto cell_detections'::text selection_reason, jsonb_build_array(r.cell_detection_id,r.id,r.relative_storage_key) fingerprint_values FROM target_cell_crops r
UNION ALL
SELECT 10 delete_order, 'cell_detection_events'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.detection_run_id,r.id,r.microscopy_image_id,r.status) fingerprint_values FROM target_cell_detection_events r
UNION ALL
SELECT 11 delete_order, 'cell_detections'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.analysis_run_image_id,r.connected_component_id,r.detection_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_cell_detections r
UNION ALL
SELECT 12 delete_order, 'image_connected_components'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'cell_detection_runs'::text parent_table, r.detection_run_id::text parent_record_id, 'JOIN detection_run_id al conjunto cell_detection_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.analysis_run_image_id,r.detection_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_image_connected_components r
UNION ALL
SELECT 13 delete_order, 'cell_detection_runs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.requested_by,r.status) fingerprint_values FROM target_cell_detection_runs r
UNION ALL
SELECT 14 delete_order, 'quality_gate_decisions'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.actor_user_id,r.analysis_run_id,r.id) fingerprint_values FROM target_quality_gate_decisions r
UNION ALL
SELECT 15 delete_order, 'quality_assessment_queue_items'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.requested_by,r.status) fingerprint_values FROM target_quality_assessment_queue_items r
UNION ALL
SELECT 16 delete_order, 'microscopy_analysis_events'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.microscopy_image_id,r.status) fingerprint_values FROM target_microscopy_analysis_events r
UNION ALL
SELECT 17 delete_order, 'image_quality_assessments'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.analysis_run_image_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_image_quality_assessments r
UNION ALL
SELECT 18 delete_order, 'microscopy_analysis_run_images'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'microscopy_analysis_runs'::text parent_table, r.analysis_run_id::text parent_record_id, 'JOIN analysis_run_id al conjunto microscopy_analysis_runs'::text selection_reason, jsonb_build_array(r.analysis_run_id,r.id,r.microscopy_image_id) fingerprint_values FROM target_microscopy_analysis_run_images r
UNION ALL
SELECT 19 delete_order, 'microscopy_analysis_runs'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'image_ingestion_batches'::text parent_table, r.ingestion_batch_id::text parent_record_id, 'Raíz del flujo de ingesta o análisis'::text selection_reason, jsonb_build_array(r.case_id,r.id,r.ingestion_batch_id,r.requested_by,r.run_status,r.sample_id,r.slide_id,r.subject_id) fingerprint_values FROM target_microscopy_analysis_runs r
UNION ALL
SELECT 20 delete_order, 'microscopy_images'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'smear_slides'::text parent_table, r.slide_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.ingestion_batch_id,r.slide_id,r.status,r.storage_key,r.updated_by) fingerprint_values FROM target_microscopy_images r
UNION ALL
SELECT 21 delete_order, 'image_ingestion_batches'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'smear_slides'::text parent_table, r.slide_id::text parent_record_id, 'Raíz del flujo de ingesta o análisis'::text selection_reason, jsonb_build_array(r.case_id,r.created_by,r.id,r.sample_id,r.slide_id,r.status,r.subject_id) fingerprint_values FROM target_image_ingestion_batches r
UNION ALL
SELECT 22 delete_order, 'smear_slides'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'blood_samples'::text parent_table, r.sample_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.sample_id,r.status,r.updated_by) fingerprint_values FROM target_smear_slides r
UNION ALL
SELECT 23 delete_order, 'blood_samples'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'scientific_cases'::text parent_table, r.case_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.case_id,r.created_by,r.id,r.status,r.updated_by) fingerprint_values FROM target_blood_samples r
UNION ALL
SELECT 24 delete_order, 'scientific_cases'::text table_name, 'id'::text primary_key_column, r.id::text record_id, 'research_subjects'::text parent_table, r.subject_id::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.source_type,r.status,r.subject_id,r.updated_by) fingerprint_values FROM target_scientific_cases r
UNION ALL
SELECT 25 delete_order, 'research_subjects'::text table_name, 'id'::text primary_key_column, r.id::text record_id, NULL::text parent_table, NULL::text parent_record_id, 'Linaje exacto de análisis o ingesta; hijos fuera del alcance bloquean purga'::text selection_reason, jsonb_build_array(r.archived_by,r.created_by,r.id,r.status,r.updated_by) fingerprint_values FROM target_research_subjects r),
clinical_storage AS (SELECT 'microscopy_images'::text source_table,id::text record_id,'storage_key'::text storage_column,storage_key::text storage_key,file_size_bytes expected_size,sha256::text expected_sha256,'microscopy_images'::text clinical_entity_type FROM target_microscopy_images WHERE storage_key IS NOT NULL UNION ALL SELECT 'cell_crops'::text source_table,id::text record_id,'relative_storage_key'::text storage_column,relative_storage_key::text storage_key,file_size_bytes expected_size,sha256::text expected_sha256,'cell_crops'::text clinical_entity_type FROM target_cell_crops WHERE relative_storage_key IS NOT NULL UNION ALL SELECT 'cell_explanations'::text source_table,id::text record_id,'heatmap_storage_key'::text storage_column,heatmap_storage_key::text storage_key,heatmap_file_size_bytes expected_size,heatmap_sha256::text expected_sha256,'cell_explanations'::text clinical_entity_type FROM target_cell_explanations WHERE heatmap_storage_key IS NOT NULL UNION ALL SELECT 'cell_explanations'::text source_table,id::text record_id,'overlay_storage_key'::text storage_column,overlay_storage_key::text storage_key,overlay_file_size_bytes expected_size,overlay_sha256::text expected_sha256,'cell_explanations'::text clinical_entity_type FROM target_cell_explanations WHERE overlay_storage_key IS NOT NULL),
clinical_evidence AS MATERIALIZED (SELECT record_id AS value FROM targets UNION SELECT storage_key FROM clinical_storage),
audit_types(resource_type,table_name) AS (VALUES ('blood_sample','blood_samples'),('cell_classification_event','cell_classification_events'),('cell_classification_input','cell_classification_inputs'),('cell_classification_review','cell_classification_reviews'),('cell_classification_run','cell_classification_runs'),('cell_crop','cell_crops'),('cell_detection','cell_detections'),('cell_detection_event','cell_detection_events'),('cell_detection_run','cell_detection_runs'),('cell_explanation','cell_explanations'),('cell_prediction','cell_predictions'),('image_connected_component','image_connected_components'),('image_ingestion_batch','image_ingestion_batches'),('image_ingestion_batche','image_ingestion_batches'),('image_quality_assessment','image_quality_assessments'),('microscopy_analysis_event','microscopy_analysis_events'),('microscopy_analysis_run','microscopy_analysis_runs'),('microscopy_analysis_run_image','microscopy_analysis_run_images'),('microscopy_image','microscopy_images'),('quality_assessment_queue_item','quality_assessment_queue_items'),('quality_gate_decision','quality_gate_decisions'),('research_subject','research_subjects'),('scientific_case','scientific_cases'),('scientific_image','microscopy_images'),('scientific_review','scientific_reviews'),('scientific_sample','blood_samples'),('scientific_slide','smear_slides'),('scientific_subject','research_subjects'),('smear_analysis_summarie','smear_analysis_summaries'),('smear_slide','smear_slides')),
audit_resources AS MATERIALIZED (SELECT m.resource_type,t.record_id FROM audit_types m JOIN targets t ON t.table_name=m.table_name),
audit_classified AS (
 SELECT a.id::text record_id,
 CASE
 WHEN a.resource_type IN ('user','role','authentication') OR a.action IN ('login','logout','password-change','user-create','user-update','role-grant','role-revoke') THEN 'security_preserved'
 WHEN a.resource_type IN ('run','model_version','dataset','artifact','deployment','publication','image_analysis_job','prediction') OR a.resource_type LIKE 'scientific_validation_%' THEN 'experimental_preserved'
 WHEN (a.resource_type,a.resource_id) IN (SELECT resource_type,record_id FROM audit_resources) THEN 'clinical_delete_target'
 WHEN EXISTS (SELECT 1 FROM audit_types m WHERE m.resource_type=a.resource_type)
 OR EXISTS (SELECT 1 FROM jsonb_path_query(jsonb_build_array(a.before_state,a.after_state,a.metadata),'strict $.** ? (@.type() == "string")') j(value) WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence))
 OR a.request_path ~ '^/api/v1/(analysis|scientific/(workflows|images)|cell-analysis|cell-classification)(/|$)'
 THEN 'ambiguous'
 ELSE 'unrelated_preserved' END classification,
 a.resource_type,a.resource_id,
 md5(jsonb_build_array(a.id,a.resource_type,a.resource_id,a.event_type,a.action,a.success,
  (SELECT jsonb_agg(v ORDER BY v COLLATE "C") FROM
   (SELECT DISTINCT j.value #>> '{}' AS v FROM jsonb_path_query(jsonb_build_array(a.before_state,a.after_state,a.metadata),'strict $.** ? (@.type() == "string")') j(value)
    WHERE j.value #>> '{}' IN (SELECT value FROM clinical_evidence)) evidence)
 )::text) fingerprint_md5
 FROM public.audit_events a
)
SELECT *, (SELECT md5(COALESCE(string_agg(jsonb_build_array(record_id,fingerprint_md5)::text,E'\n' ORDER BY record_id COLLATE "C"),'')) FROM audit_classified WHERE classification='clinical_delete_target') clinical_audit_set_fingerprint
FROM audit_classified ORDER BY classification,record_id;

-- REPORT triggers_blocking_future_purge
SELECT DISTINCT event_object_table,trigger_name,action_statement FROM information_schema.triggers WHERE trigger_schema='public' AND event_manipulation='DELETE' AND event_object_table IN ('cell_explanations','cell_classification_reviews','cell_classification_events','smear_analysis_summaries','cell_predictions','cell_classification_inputs','cell_classification_runs','scientific_reviews','cell_crops','cell_detection_events','cell_detections','image_connected_components','cell_detection_runs','quality_gate_decisions','quality_assessment_queue_items','microscopy_analysis_events','image_quality_assessments','microscopy_analysis_run_images','microscopy_analysis_runs','microscopy_images','image_ingestion_batches','smear_slides','blood_samples','scientific_cases','research_subjects','audit_events') ORDER BY event_object_table,trigger_name;

ROLLBACK;
