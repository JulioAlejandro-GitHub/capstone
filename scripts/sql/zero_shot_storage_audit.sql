-- Read-only operational audit; no migration revision or schema preflight.
BEGIN READ ONLY;
SELECT id,name,model_type,framework,pretrained,pretrained_source,metadata
FROM public.models WHERE model_type='zero_shot';
SELECT r.id,r.model_id,r.run_type,r.status,r.total_epochs,r.duration_seconds,
       r.dataset_version_id,r.release_status,r.metadata
FROM public.runs r JOIN public.models m ON m.id=r.model_id WHERE m.model_type='zero_shot';
SELECT v.* FROM public.model_versions v JOIN public.models m ON m.id=v.model_id
WHERE m.model_type='zero_shot';
SELECT a.* FROM public.artifacts a JOIN public.runs r ON r.id=a.run_id
JOIN public.models m ON m.id=r.model_id WHERE m.model_type='zero_shot';
-- Feed these identities to verified_file; SQL does not inspect the host filesystem.
SELECT a.id,a.path,a.checksum AS sha256,a.file_size_bytes AS bytes,a.artifact_status
FROM public.artifacts a JOIN public.runs r ON r.id=a.run_id
JOIN public.models m ON m.id=r.model_id WHERE m.model_type='zero_shot';
SELECT v.model_id,v.artifact_sha256,count(*) AS versions,array_agg(v.id) AS version_ids
FROM public.model_versions v JOIN public.models m ON m.id=v.model_id
WHERE m.model_type='zero_shot' GROUP BY v.model_id,v.artifact_sha256 HAVING count(*)>1;
SELECT p.id,p.model_version_id,p.training_run_id,p.status,p.is_active,
       p.evaluation_run_id,p.evaluation_attempt_id
FROM public.stage2_model_publications p JOIN public.runs r ON r.id=p.training_run_id
JOIN public.models m ON m.id=r.model_id WHERE m.model_type='zero_shot';
SELECT conrelid::regclass,conname,pg_get_constraintdef(oid)
FROM pg_constraint WHERE conrelid IN ('public.models'::regclass,'public.runs'::regclass,
 'public.artifacts'::regclass,'public.model_versions'::regclass);
ROLLBACK;
