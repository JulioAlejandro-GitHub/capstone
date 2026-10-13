\set ON_ERROR_STOP on
BEGIN READ ONLY;
SELECT jsonb_build_object('explain_evaluation_links',jsonb_agg(to_jsonb(x))) FROM (SELECT i.identity->'explanation'->>'method' method,count(*) identities,count(*) FILTER (WHERE i.identity->'evaluation'->>'attempt_id' IS NOT NULL) explicit_evaluation_reference,count(*) FILTER (WHERE a.id IS NOT NULL AND e.kind='evaluate' AND e.training_run_id=i.training_run_id AND a.state='verified') verified_same_train_reference FROM assessment_identities i LEFT JOIN assessment_attempts a ON a.id::text=i.identity->'evaluation'->>'attempt_id' LEFT JOIN assessment_identities e ON e.id=a.identity_id WHERE i.kind='explain' GROUP BY 1) x;
COMMIT;
