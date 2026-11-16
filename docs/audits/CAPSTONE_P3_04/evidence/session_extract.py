exec((__import__('pathlib').Path(__file__).parent/'extract.py').read_text().split('cols=query')[0])
query('training_sessions',"SELECT json_agg(t) FROM (SELECT * FROM train_execution_sessions ORDER BY run_id)t;")
query('principal_calibration_record',"SELECT json_agg(t) FROM (SELECT * FROM train_execution_records WHERE run_id='87b3eff7-e09a-41c8-945d-bf31b3541adb' AND kind='calibration')t;")
