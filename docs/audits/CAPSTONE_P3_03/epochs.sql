BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT coalesce(json_agg(t),'[]') FROM (SELECT run_id,kind,phase,record_key,payload FROM train_execution_records WHERE kind IN ('epoch','phase') ORDER BY run_id,kind,phase,record_key)t;
COMMIT;
