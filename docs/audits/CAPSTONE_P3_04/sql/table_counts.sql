BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_build_object('training_history',(SELECT count(*) FROM training_history),'predictions',(SELECT count(*) FROM predictions),'xai_evidence',(SELECT count(*) FROM xai_evidence),'assessment_results',(SELECT count(*) FROM assessment_results));
COMMIT;
