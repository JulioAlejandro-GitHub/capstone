BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_agg(t) FROM (SELECT r.* FROM assessment_results r JOIN assessment_attempts a ON a.id=r.attempt_id JOIN assessment_identities i ON i.id=a.identity_id WHERE i.training_run_id='87b3eff7-e09a-41c8-945d-bf31b3541adb' AND i.kind IN ('explain','represent') ORDER BY r.attempt_id,r.sample_id)t;
COMMIT;
