BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_agg(t) FROM (SELECT * FROM train_execution_records WHERE kind='runtime' ORDER BY run_id,event_sequence)t;
COMMIT;
