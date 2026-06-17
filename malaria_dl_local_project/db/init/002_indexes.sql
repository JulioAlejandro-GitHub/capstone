CREATE INDEX IF NOT EXISTS idx_runs_model_id ON runs(model_id);
CREATE INDEX IF NOT EXISTS idx_runs_dataset_id ON runs(dataset_id);
CREATE INDEX IF NOT EXISTS idx_runs_run_type ON runs(run_type);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at);

CREATE INDEX IF NOT EXISTS idx_run_metrics_run_id ON run_metrics(run_id);
CREATE INDEX IF NOT EXISTS idx_run_metrics_name ON run_metrics(metric_name);

CREATE INDEX IF NOT EXISTS idx_predictions_run_id ON predictions(run_id);
CREATE INDEX IF NOT EXISTS idx_predictions_case_type ON predictions(case_type);

CREATE INDEX IF NOT EXISTS idx_artifacts_run_id ON artifacts(run_id);

CREATE INDEX IF NOT EXISTS idx_explainability_run_id ON explainability_results(run_id);
CREATE INDEX IF NOT EXISTS idx_explainability_method ON explainability_results(method);

CREATE INDEX IF NOT EXISTS idx_training_history_run_id ON training_history(run_id);
CREATE INDEX IF NOT EXISTS idx_confusion_matrices_run_id ON confusion_matrices(run_id);
CREATE INDEX IF NOT EXISTS idx_classification_reports_run_id ON classification_reports(run_id);
CREATE INDEX IF NOT EXISTS idx_errors_run_id ON errors(run_id);
CREATE INDEX IF NOT EXISTS idx_execution_logs_run_id ON execution_logs(run_id);
CREATE INDEX IF NOT EXISTS idx_environment_packages_run_id ON environment_packages(run_id);

CREATE INDEX IF NOT EXISTS idx_runs_parameters_gin ON runs USING GIN(parameters);
CREATE INDEX IF NOT EXISTS idx_runs_metadata_gin ON runs USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_datasets_metadata_gin ON datasets USING GIN(metadata);
