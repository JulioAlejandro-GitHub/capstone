BEGIN READ ONLY;
SELECT json_build_object('campaigns',(SELECT json_agg(t) FROM (SELECT id,name,state,created_at FROM experimental_campaigns)t),'run_campaigns',(SELECT json_agg(t) FROM (SELECT r.id,r.campaign_id,m.name model,r.status,r.started_at,c.optimizer,c.random_seed FROM runs r JOIN models m ON m.id=r.model_id LEFT JOIN run_configurations c ON c.run_id=r.id ORDER BY started_at)t),'locks',(SELECT json_agg(to_jsonb(t)) FROM assessment_final_locks t));
COMMIT;
