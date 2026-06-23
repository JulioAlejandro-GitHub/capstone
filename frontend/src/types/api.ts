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

export interface DatasetSplitRow extends JsonRecord {
  split_name: string;
  display_name: string;
  uninfected: number;
  parasitized: number;
  total: number;
}

export interface DatasetBrowserSummary {
  dataset: {
    name: string;
    source: string;
    source_url: string;
    nih_nlm_url?: string | null;
    description: string;
    dataset_dir: string;
    original_dataset_modified: boolean;
  };
  label_mapping: {
    '0': string;
    '1': string;
    negative_class: string;
    negative_class_index: number;
    positive_class: string;
    positive_class_index: number;
    version: string;
    raw_model_score_meaning: string;
  };
  split_process: {
    type: string;
    train_ratio: number;
    val_ratio: number;
    test_ratio: number;
    seed: number;
    description: string;
  };
  counts: {
    train: { uninfected: number; parasitized: number; total: number };
    val: { uninfected: number; parasitized: number; total: number };
    test: { uninfected: number; parasitized: number; total: number };
    total: number;
  };
  split_table: DatasetSplitRow[];
  summary_rows: JsonRecord[];
}

export interface DatasetImageItem extends JsonRecord {
  image_id: string;
  filename: string;
  split_name: string;
  display_split_name: string;
  class_name: string;
  class_index: number;
  relative_path: string;
  image_url: string;
  image_width: number | null;
  image_height: number | null;
  file_size_bytes: number | null;
}

export interface DatasetImagePage {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  filters: {
    split: string | null;
    class_name: string | null;
  };
  items: DatasetImageItem[];
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
  artifact_id: string | null;
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

export interface UploadedPrediction extends JsonRecord {
  prediction_id: string;
  run_id: string;
  experiment_id: string | null;
  model_id: string | null;
  model_name: string | null;
  model_type: string | null;
  run_name: string | null;
  run_type: string | null;
  run_status: string | null;
  script_name: string | null;
  command: string | null;
  started_at: string | null;
  finished_at: string | null;
  workflow: string | null;
  image_id: string | null;
  image_path: string | null;
  artifact_id: string | null;
  artifact_path: string | null;
  image_stored_path: string | null;
  image_original_path: string | null;
  original_image_path: string | null;
  original_filename: string | null;
  stored_filename: string | null;
  mime_type: string | null;
  file_size_bytes: number | null;
  checksum: string | null;
  true_label: string | null;
  predicted_label: string | null;
  probability_parasitized: number | null;
  probability_uninfected: number | null;
  score: number | null;
  score_positive_label: number | null;
  threshold: number | null;
  is_correct: boolean | null;
  case_type: string | null;
  confidence_level: string | null;
  decision: string | null;
  decision_code: string | null;
  human_readable_response: string | null;
  quality_passed: boolean | null;
  quality_warnings: JsonValue | null;
  quality_metrics: JsonValue | null;
  raw_model_score: number | null;
  raw_model_score_meaning: string | null;
  label_mapping_version: string | null;
  label_mapping: JsonValue | null;
  positive_class_name: string | null;
  positive_class_index: number | null;
  negative_class_name: string | null;
  negative_class_index: number | null;
  calibration_method: string | null;
  calibration_applied: boolean | null;
  tta_applied: boolean | null;
  tta: boolean | null;
  n_aug: number | null;
  ensemble_applied: boolean | null;
  ensemble_models: JsonValue | null;
  ensemble_weights: JsonValue | null;
  explainability_method: string | null;
  explainability_path: string | null;
  explainability_success: boolean | null;
  prediction_metadata: JsonValue | null;
  artifact_metadata: JsonValue | null;
  run_parameters: JsonValue | null;
  run_metadata: JsonValue | null;
  created_at: string | null;
}
