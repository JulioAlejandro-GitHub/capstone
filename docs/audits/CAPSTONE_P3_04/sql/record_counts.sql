BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_agg(t) FROM (SELECT run_id,kind,count(*) FROM train_execution_records GROUP BY run_id,kind ORDER BY run_id,kind)t;
COMMIT;
