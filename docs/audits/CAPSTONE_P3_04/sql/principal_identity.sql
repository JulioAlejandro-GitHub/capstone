BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_build_object('database',current_database(),'user',current_user,'captured_at',now(),'read_only',current_setting('transaction_read_only'),'runs',(SELECT json_agg(r) FROM runs r WHERE id='00b8d407-c672-4b68-9814-53c092d034ba'),'identities',(SELECT json_agg(i) FROM assessment_identities i WHERE id='00b8d407-c672-4b68-9814-53c092d034ba' OR training_run_id='00b8d407-c672-4b68-9814-53c092d034ba'),'attempts',(SELECT json_agg(a) FROM assessment_attempts a WHERE id='00b8d407-c672-4b68-9814-53c092d034ba'));
COMMIT;
