export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type JsonRecord = Record<string, JsonValue>;

export interface Datasource {
  key: string;
  label: string;
  domain: string;
  enabled: boolean;
  database: string;
}

export interface RunDashboard {
  run_id: string;
  run_name: string | null;
  run_type: string;
  status: string;
  model_name: string | null;
  dataset_name: string | null;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  auc: number | null;
}

export interface ModelSummary {
  model_id: string;
  model_name: string;
  model_type: string;
  total_runs: number;
  completed_runs: number;
  failed_runs: number;
  last_run_at: string | null;
  best_accuracy: number | null;
  best_recall: number | null;
  best_f1_score: number | null;
  best_auc: number | null;
  framework?: string | null;
  architecture?: string | null;
}

export interface DashboardSummary {
  datasource: string;
  domain: string;
  totals: {
    total_runs: number;
    completed_runs: number;
    failed_runs: number;
    started_runs: number;
  };
  best_metrics: {
    best_accuracy: number | null;
    best_recall: number | null;
    best_f1_score: number | null;
    best_auc: number | null;
  };
  runs_by_model: ModelSummary[];
  recent_runs: RunDashboard[];
  domains: Array<{ key: string; domain: string; enabled: boolean }>;
}

export interface MetricRow extends JsonRecord {
  id: string;
  run_id: string;
  metric_name: string;
  metric_value: number | null;
  split_name: string | null;
  class_name: string | null;
  epoch: number | null;
}

export interface ArtifactRow extends JsonRecord {
  id: string;
  artifact_type: string;
  name: string | null;
  path: string;
  mime_type: string | null;
}

export interface RunDetailResponse {
  run: JsonRecord;
  metrics: MetricRow[];
  artifacts: ArtifactRow[];
  training_history: JsonRecord[];
  errors: JsonRecord[];
}

export interface ExplainabilityRow extends JsonRecord {
  id: string;
  run_id: string;
  method: string;
  output_path: string | null;
  true_label: string | null;
  predicted_label: string | null;
  score: number | null;
  case_type: string | null;
  success: boolean;
  error_message: string | null;
  run_name: string | null;
  model_name: string | null;
}

export interface PagedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ExplainabilityCase extends JsonRecord {
  explainability_id: string;
  prediction_id: string | null;
  run_id: string;
  experiment_id: string | null;
  model_id: string | null;
  model_name: string | null;
  model_type: string | null;
  dataset_id: string | null;
  dataset_name: string | null;
  run_name: string | null;
  run_type: string | null;
  run_status: string | null;
  script_name: string | null;
  command: string | null;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  method: string;
  case_type: string | null;
  true_label: string | null;
  predicted_label: string | null;
  positive_label: string | null;
  score: number | null;
  score_positive_label: number | null;
  threshold: number | null;
  is_correct: boolean | null;
  image_id: string | null;
  image_path: string | null;
  explanation_output_path: string | null;
  artifact_path: string | null;
  artifact_type: string | null;
  last_conv_layer: string | null;
  success: boolean | null;
  error_message: string | null;
}

export interface ExplainabilityCaseSummary extends JsonRecord {
  model_name: string | null;
  dataset_name: string | null;
  method: string | null;
  case_type: string | null;
  total_cases: number;
  avg_score: number | null;
  min_score: number | null;
  max_score: number | null;
  latest_run_at: string | null;
}
