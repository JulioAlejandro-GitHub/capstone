-- PENDING AUTHORIZATION: evidence and concrete destination plan only.
-- No UPDATE is supplied: the current checkpoint path and version are immutable.
-- Do not disable triggers. A replacement ingestion/version must preserve the old
-- records and be published separately through the existing activation service.
-- Approval must cover copying bytes, new run/artifact/version rows and (separately)
-- replacing the productive selection. This query does not authorize those actions.
BEGIN READ ONLY;
SELECT a.id,a.run_id,a.artifact_type,a.metadata->>'role' AS role,a.path AS current_path,
       a.checksum,a.file_size_bytes,
       'outputs/train_runs/<new_run_id>/' ||
       CASE WHEN a.metadata->>'role' IN ('text_config','tokenizer_config','vocabulary')
         THEN 'text/' ELSE '' END || a.name AS proposed_relative_path
FROM public.artifacts a
WHERE a.run_id='31d27b2d-6e90-4530-a589-ae92c91281df';
SELECT v.id,v.status,v.checkpoint_artifact_id,v.training_run_id,v.artifact_sha256
FROM public.model_versions v WHERE v.model_id='1cf3e462-c0f7-4f72-92fe-306b8aaaa203';
SELECT pg_get_functiondef(oid) FROM pg_proc
WHERE proname IN ('protect_governed_artifact_identity','enforce_model_version_governance');
ROLLBACK;
