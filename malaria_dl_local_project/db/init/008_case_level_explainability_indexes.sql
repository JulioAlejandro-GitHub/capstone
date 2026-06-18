CREATE INDEX IF NOT EXISTS idx_predictions_case_type_run
ON predictions(case_type, run_id);

CREATE INDEX IF NOT EXISTS idx_predictions_true_pred
ON predictions(true_label, predicted_label);

CREATE INDEX IF NOT EXISTS idx_explainability_case_method
ON explainability_results(case_type, method);

CREATE INDEX IF NOT EXISTS idx_explainability_success
ON explainability_results(success);

CREATE INDEX IF NOT EXISTS idx_explainability_output_path
ON explainability_results(output_path);

CREATE INDEX IF NOT EXISTS idx_artifacts_type_path
ON artifacts(artifact_type, path);
