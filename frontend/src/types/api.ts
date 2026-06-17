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
