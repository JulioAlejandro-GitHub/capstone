BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_agg(t) FROM (SELECT viewname,definition FROM pg_views WHERE schemaname='public' AND viewname IN ('vw_model_run_summary','vw_clinical_run_summary','vw_clinical_inference_predictions'))t;
COMMIT;
