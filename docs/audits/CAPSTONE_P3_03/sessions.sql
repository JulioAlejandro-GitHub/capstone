BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT coalesce(json_agg(to_jsonb(t)),'[]') FROM train_execution_sessions t;
COMMIT;
