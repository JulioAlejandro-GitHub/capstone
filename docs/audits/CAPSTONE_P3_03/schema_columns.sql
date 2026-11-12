BEGIN READ ONLY;
SELECT json_agg(t) FROM (SELECT table_name,column_name,data_type FROM information_schema.columns WHERE table_schema='public' AND table_name IN ('runs','models','run_configurations','run_metrics','run_clinical_metrics','training_history','train_execution_records','assessment_identities','assessment_attempts','assessment_results','assessment_artifacts','run_checkpoint_policy','run_threshold_calibration','deployed_model_versions','model_versions','run_model_deployments','stage2_model_publications','artifacts') ORDER BY table_name,ordinal_position)t;
COMMIT;
