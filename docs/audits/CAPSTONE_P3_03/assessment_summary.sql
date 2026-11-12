BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT coalesce(json_agg(t),'[]') FROM (SELECT i.id identity_id,i.training_run_id,i.kind,i.identity-'samples' identity,a.id attempt_id,a.ordinal,a.state,a.started_at,a.finished_at,a.artifact_root,a.verification FROM assessment_identities i JOIN assessment_attempts a ON a.identity_id=i.id WHERE i.kind IN ('evaluate','test') ORDER BY i.training_run_id,a.started_at)t;
COMMIT;
