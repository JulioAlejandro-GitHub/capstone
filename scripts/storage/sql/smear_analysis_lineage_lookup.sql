BEGIN;
SET TRANSACTION READ ONLY;
SET LOCAL statement_timeout='30s';
SET LOCAL lock_timeout='5s';
-- analysis_id: sustituir NULL por UUID o enlazar CAST(:analysis_id AS uuid) desde cliente.
SELECT a.id analysis_run_id,b.id ingestion_batch_id,rs.id subject_id,c.id case_id,
 bs.id sample_id,ss.id slide_id,im.id microscopy_image_id,ari.id analysis_run_image_id,
 dr.id detection_run_id,ic.id connected_component_id,cd.id detection_id,cc.id crop_id,
 cr.id classification_run_id,ci.id classification_input_id,cp.id cell_prediction_id,
 ce.id cell_explanation_id,sa.id summary_id,
 im.storage_key image_storage_key,cc.relative_storage_key crop_storage_key,
 ce.heatmap_storage_key,ce.overlay_storage_key
FROM public.blood_samples bs
JOIN public.scientific_cases c ON c.id=bs.case_id
LEFT JOIN public.research_subjects rs ON rs.id=c.subject_id
LEFT JOIN public.smear_slides ss ON ss.sample_id=bs.id
LEFT JOIN public.image_ingestion_batches b ON b.slide_id=ss.id
LEFT JOIN public.microscopy_images im ON im.slide_id=ss.id AND im.ingestion_batch_id IS NOT DISTINCT FROM b.id
LEFT JOIN public.microscopy_analysis_run_images ari ON ari.microscopy_image_id=im.id
LEFT JOIN public.microscopy_analysis_runs a ON a.id=ari.analysis_run_id
LEFT JOIN public.cell_detection_runs dr ON dr.analysis_run_id=a.id
LEFT JOIN public.image_connected_components ic ON ic.detection_run_id=dr.id AND ic.analysis_run_image_id=ari.id
LEFT JOIN public.cell_detections cd ON cd.connected_component_id=ic.id AND cd.detection_run_id=dr.id
LEFT JOIN public.cell_crops cc ON cc.cell_detection_id=cd.id
LEFT JOIN public.cell_classification_runs cr ON cr.detection_run_id=dr.id AND cr.analysis_run_id=a.id
LEFT JOIN public.cell_classification_inputs ci ON ci.classification_run_id=cr.id AND ci.cell_detection_id=cd.id AND ci.crop_id=cc.id
LEFT JOIN public.cell_predictions cp ON cp.classification_input_id=ci.id
LEFT JOIN public.cell_explanations ce ON ce.cell_prediction_id=cp.id
LEFT JOIN public.smear_analysis_summaries sa ON sa.classification_run_id=cr.id
WHERE a.id = CAST(NULL AS uuid)
ORDER BY bs.id,ss.id,b.id,a.id,im.id,dr.id,ic.id,cd.id,cr.id,ci.id,cp.id,ce.id;
-- sample_id: sustituir NULL por UUID o enlazar CAST(:sample_id AS uuid) desde cliente.
SELECT a.id analysis_run_id,b.id ingestion_batch_id,rs.id subject_id,c.id case_id,
 bs.id sample_id,ss.id slide_id,im.id microscopy_image_id,ari.id analysis_run_image_id,
 dr.id detection_run_id,ic.id connected_component_id,cd.id detection_id,cc.id crop_id,
 cr.id classification_run_id,ci.id classification_input_id,cp.id cell_prediction_id,
 ce.id cell_explanation_id,sa.id summary_id,
 im.storage_key image_storage_key,cc.relative_storage_key crop_storage_key,
 ce.heatmap_storage_key,ce.overlay_storage_key
FROM public.blood_samples bs
JOIN public.scientific_cases c ON c.id=bs.case_id
LEFT JOIN public.research_subjects rs ON rs.id=c.subject_id
LEFT JOIN public.smear_slides ss ON ss.sample_id=bs.id
LEFT JOIN public.image_ingestion_batches b ON b.slide_id=ss.id
LEFT JOIN public.microscopy_images im ON im.slide_id=ss.id AND im.ingestion_batch_id IS NOT DISTINCT FROM b.id
LEFT JOIN public.microscopy_analysis_run_images ari ON ari.microscopy_image_id=im.id
LEFT JOIN public.microscopy_analysis_runs a ON a.id=ari.analysis_run_id
LEFT JOIN public.cell_detection_runs dr ON dr.analysis_run_id=a.id
LEFT JOIN public.image_connected_components ic ON ic.detection_run_id=dr.id AND ic.analysis_run_image_id=ari.id
LEFT JOIN public.cell_detections cd ON cd.connected_component_id=ic.id AND cd.detection_run_id=dr.id
LEFT JOIN public.cell_crops cc ON cc.cell_detection_id=cd.id
LEFT JOIN public.cell_classification_runs cr ON cr.detection_run_id=dr.id AND cr.analysis_run_id=a.id
LEFT JOIN public.cell_classification_inputs ci ON ci.classification_run_id=cr.id AND ci.cell_detection_id=cd.id AND ci.crop_id=cc.id
LEFT JOIN public.cell_predictions cp ON cp.classification_input_id=ci.id
LEFT JOIN public.cell_explanations ce ON ce.cell_prediction_id=cp.id
LEFT JOIN public.smear_analysis_summaries sa ON sa.classification_run_id=cr.id
WHERE bs.id = CAST(NULL AS uuid)
ORDER BY bs.id,ss.id,b.id,a.id,im.id,dr.id,ic.id,cd.id,cr.id,ci.id,cp.id,ce.id;
-- history_id: sustituir NULL por UUID o enlazar CAST(:history_id AS uuid) desde cliente.
SELECT a.id analysis_run_id,b.id ingestion_batch_id,rs.id subject_id,c.id case_id,
 bs.id sample_id,ss.id slide_id,im.id microscopy_image_id,ari.id analysis_run_image_id,
 dr.id detection_run_id,ic.id connected_component_id,cd.id detection_id,cc.id crop_id,
 cr.id classification_run_id,ci.id classification_input_id,cp.id cell_prediction_id,
 ce.id cell_explanation_id,sa.id summary_id,
 im.storage_key image_storage_key,cc.relative_storage_key crop_storage_key,
 ce.heatmap_storage_key,ce.overlay_storage_key
FROM public.blood_samples bs
JOIN public.scientific_cases c ON c.id=bs.case_id
LEFT JOIN public.research_subjects rs ON rs.id=c.subject_id
LEFT JOIN public.smear_slides ss ON ss.sample_id=bs.id
LEFT JOIN public.image_ingestion_batches b ON b.slide_id=ss.id
LEFT JOIN public.microscopy_images im ON im.slide_id=ss.id AND im.ingestion_batch_id IS NOT DISTINCT FROM b.id
LEFT JOIN public.microscopy_analysis_run_images ari ON ari.microscopy_image_id=im.id
LEFT JOIN public.microscopy_analysis_runs a ON a.id=ari.analysis_run_id
LEFT JOIN public.cell_detection_runs dr ON dr.analysis_run_id=a.id
LEFT JOIN public.image_connected_components ic ON ic.detection_run_id=dr.id AND ic.analysis_run_image_id=ari.id
LEFT JOIN public.cell_detections cd ON cd.connected_component_id=ic.id AND cd.detection_run_id=dr.id
LEFT JOIN public.cell_crops cc ON cc.cell_detection_id=cd.id
LEFT JOIN public.cell_classification_runs cr ON cr.detection_run_id=dr.id AND cr.analysis_run_id=a.id
LEFT JOIN public.cell_classification_inputs ci ON ci.classification_run_id=cr.id AND ci.cell_detection_id=cd.id AND ci.crop_id=cc.id
LEFT JOIN public.cell_predictions cp ON cp.classification_input_id=ci.id
LEFT JOIN public.cell_explanations ce ON ce.cell_prediction_id=cp.id
LEFT JOIN public.smear_analysis_summaries sa ON sa.classification_run_id=cr.id
WHERE a.id = CAST(NULL AS uuid)
ORDER BY bs.id,ss.id,b.id,a.id,im.id,dr.id,ic.id,cd.id,cr.id,ci.id,cp.id,ce.id;
ROLLBACK;
