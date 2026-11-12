BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT coalesce(json_agg(to_jsonb(t)),'[]') FROM training_history t;
COMMIT;
