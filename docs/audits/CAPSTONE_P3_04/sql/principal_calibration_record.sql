BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_agg(t) FROM (SELECT * FROM train_execution_records WHERE run_id='87b3eff7-e09a-41c8-945d-bf31b3541adb' AND kind='calibration')t;
COMMIT;
