BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_build_object('stage2',(SELECT json_agg(to_jsonb(p)) FROM stage2_model_publications p),'deployments',(SELECT json_agg(to_jsonb(d)) FROM deployed_model_versions d),'model_versions',(SELECT json_agg(to_jsonb(m)) FROM model_versions m WHERE training_run_id IN (SELECT training_run_id FROM stage2_model_publications) OR id IN (SELECT model_version_id FROM deployed_model_versions)));
COMMIT;
