BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_agg(t) FROM (SELECT i.id identity_id,i.training_run_id,i.kind,i.identity-'samples' identity,jsonb_array_length(i.identity->'samples') sample_count,a.* FROM assessment_identities i JOIN assessment_attempts a ON a.identity_id=i.id ORDER BY i.training_run_id,a.started_at)t;
COMMIT;
