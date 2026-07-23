export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type JsonRecord = Record<string, JsonValue>;

export interface ConfusionMatrixValues {
  tn?: number | null;
  fp?: number | null;
  fn?: number | null;
  tp?: number | null;
  true_negative?: number | null;
  false_positive?: number | null;
  false_negative?: number | null;
  true_positive?: number | null;
}

export interface Datasource {
  key: string;
  label: string;
  domain: string;
  enabled: boolean;
  database: string;
}

export interface ModelVersionRow {
  id: string; training_run_id: string; model_name: string; version_number: number | null;
  status: string; lineage_status: string; artifact_sha256: string | null;
  artifact_size_bytes: number | null; framework: string | null; framework_version: string | null;
  created_at: string | null; validated_at?: string | null; threshold_used?: number | null;
  recall_parasitized?: number | null; specificity?: number | null; f2_parasitized?: number | null;
  evaluation_run_id?: string | null; explainability_available?: boolean;
  active_deployment_id?: string | null; deployment_alias?: string | null; deployment_environment?: string | null;
  threshold_profile_id?: string | null;
  preprocessing_profile_snapshot?: JsonRecord;
  class_mapping?: JsonRecord;
  input_signature?: JsonRecord;
  output_signature?: JsonRecord;
  metadata?: JsonRecord;
}

export interface DeploymentRow {
  id: string; deployment_name: string; environment: string; alias: string;
  model_version_id: string; status: string; threshold_value: number;
  deployed_at: string | null; retired_at: string | null; deployed_by: string | null;
  created_at?: string | null;
  metadata?: JsonRecord; supersedes_deployment_id?: string|null; rollback_of_deployment_id?: string|null;
  training_run_id?:string;model_name?:string;version_number?:number|null;model_version_status?:string;
}

export interface DeploymentRequirement {
  key:string; label:string; status:'pass'|'pending'|'blocked'|'not_applicable'; detail:string;
}

export interface DeploymentReadiness {
  deployment_id:string;model_version_id:string;training_run_id:string;model_name:string;
  version_number:number|null;environment:string;alias:string;deployment_status:string;
  can_run_smoke:boolean;can_activate:boolean;validation_errors:string[];
  requirements:DeploymentRequirement[];smoke_test:JsonRecord|null;
}

export interface AvailableModel extends DeploymentRow {
  training_run_id: string; model_name: string; version_number: number;
  model_version_status: string;
}

export interface InferenceResult {
  inference_run_id:string; image_analysis_job_id:string; deployed_model_version_id:string;
  model_version_id:string; model_name:string; model_version:number;
  probability_parasitized:number; probability_uninfected:number;
  predicted_class:0|1; predicted_label:'uninfected'|'parasitized'; threshold_used:number;
}

export interface ModelVersionLineageRow {
  id: string; parent_run_id: string; child_run_id: string; relationship_type: string;
  model_version_id: string; checkpoint_artifact_id: string | null; confidence: string | null; created_at: string;
}

export type PromotionNextAction =
  | 'prepare_release'
  | 'review_model_version'
  | 'approve_model_version'
  | 'create_deployment'
  | 'review_pending_deployment'
  | 'view_active_deployment'
  | 'unavailable';

export interface PromotionBlockingReason {
  code: string;
  message: string;
}

export interface PromotionThreshold {
  value: number;
  source: string;
  evaluated_on_test: boolean;
}

export interface TrainingPromotionStatus {
  training_run_id: string;
  training_status: string | null;
  model_name: string | null;
  model_version_id: string | null;
  model_version_status: string | null;
  lineage_status: string;
  evaluation_run_id: string | null;
  explainability_run_ids: string[];
  checkpoint_sha256: string | null;
  threshold: PromotionThreshold | null;
  can_release: boolean;
  can_deploy: boolean;
  deployment_id: string | null;
  deployment_status: string | null;
  environment: string | null;
  alias: string | null;
  next_action: PromotionNextAction;
  button_label: string;
  button_enabled: boolean;
  blocking_reasons: PromotionBlockingReason[];
  target_url: string | null;
}

export interface RunDashboard {
  run_id: string;
  run_name: string | null;
  run_type: string;
  status: string;
  model_name: string | null;
  dataset_name: string | null;
  optimizer: string | null;
  command?: string | null;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  auc: number | null;
  recall_parasitized?: number | null;
  sensitivity_parasitized?: number | null;
  specificity?: number | null;
  f2_score?: number | null;
  f2_parasitized?: number | null;
  roc_auc?: number | null;
  roc_auc_parasitized?: number | null;
  tn?: number | null;
  fp?: number | null;
  fn?: number | null;
  tp?: number | null;
  true_negative?: number | null;
  false_positive?: number | null;
  false_negative?: number | null;
  true_positive?: number | null;
  confusion_matrix?: number[][] | ConfusionMatrixValues | null;
  prediction_collapse_detected?: boolean | null;
}

export type RunLineageConfidence =
  | 'explicit'
  | 'inferred_exact_checkpoint'
  | 'inferred_model_version'
  | 'inferred_heuristic'
  | 'unknown';

export interface EvaluationLineageRun {
  run_id: string;
  run_name: string | null;
  run_type: 'evaluation';
  status: string;
  started_at: string | null;
  finished_at?: string | null;
  duration_seconds?: number | null;
  model_name?: string | null;
  optimizer?: string | null;
  command?: string | null;
  relationship_type: string | null;
  confidence: RunLineageConfidence | null;
  checkpoint_path: string | null;
  accuracy?: number | null;
  recall: number | null;
  specificity: number | null;
  f2_score: number | null;
  auc: number | null;
  tn?: number | null;
  fp?: number | null;
  fn?: number | null;
  tp?: number | null;
  true_negative?: number | null;
  false_positive?: number | null;
  false_negative?: number | null;
  true_positive?: number | null;
  confusion_matrix?: number[][] | ConfusionMatrixValues | null;
  lineage_status?: string | null;
  lineage_warning?: string | null;
  candidate_training_run_ids?: string[];
}

export interface ExplainabilityLineageRun {
  run_id: string;
  run_name: string | null;
  run_type: 'explainability';
  status: string;
  started_at: string | null;
  finished_at?: string | null;
  duration_seconds?: number | null;
  model_name?: string | null;
  optimizer?: string | null;
  command?: string | null;
  relationship_type: string | null;
  confidence: RunLineageConfidence | null;
  checkpoint_path: string | null;
  method: string | null;
  methods?: string[];
  total_explanations: number;
  success_count: number;
  failed_count: number;
  lineage_status?: string | null;
  lineage_warning?: string | null;
  candidate_training_run_ids?: string[];
}

export interface TrainingRunLineageGroup {
  training: RunDashboard;
  evaluations: EvaluationLineageRun[];
  explainability: ExplainabilityLineageRun[];
}

export interface UnlinkedLineageRun {
  run_id: string;
  run_name: string | null;
  run_type: 'evaluation' | 'explainability';
  status: string;
  started_at: string | null;
  finished_at?: string | null;
  duration_seconds?: number | null;
  model_name?: string | null;
  optimizer?: string | null;
  command?: string | null;
  relationship_type?: null;
  confidence?: RunLineageConfidence | null;
  checkpoint_path?: string | null;
  lineage_status?: string | null;
  lineage_warning?: string | null;
}

export type UnresolvedLineageRun =
  | UnlinkedLineageRun
  | EvaluationLineageRun
  | ExplainabilityLineageRun;

export interface GroupedRunLineageResponse {
  items: TrainingRunLineageGroup[];
  unlinked: {
    evaluations: UnlinkedLineageRun[];
    explainability: UnlinkedLineageRun[];
  };
  conflicts: {
    evaluations: EvaluationLineageRun[];
    explainability: ExplainabilityLineageRun[];
  };
  totals: {
    training_runs: number;
    linked_evaluations: number;
    linked_explainability: number;
    unlinked_evaluations: number;
    unlinked_explainability: number;
    conflicting_evaluations: number;
    conflicting_explainability: number;
  };
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

export interface RunRecord extends JsonRecord {
  id: string;
  run_name: string | null;
  run_type: string;
  execution_type: string | null;
  status: string;
  command: string | null;
  script_name: string | null;
  model_name: string | null;
  model_type: string | null;
  dataset_name: string | null;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  fine_tuning_start_epoch: number | null;
  total_epochs: number | null;
  completed_epochs: number;
  parameters: JsonValue;
  execution_parameters: JsonValue;
}

export interface TrainingHistoryRow extends JsonRecord {
  epoch: number;
  phase: string;
  train_accuracy: number | null;
  accuracy: number | null;
  val_accuracy: number | null;
  train_loss: number | null;
  loss: number | null;
  val_loss: number | null;
  learning_rate: number | null;
}

export interface RunDetailResponse {
  run: RunRecord;
  metrics: MetricRow[];
  artifacts: ArtifactRow[];
  training_history: TrainingHistoryRow[];
  errors: JsonRecord[];
}

export interface LabelMapping {
  '0': string;
  '1': string;
  negative_class?: string;
  negative_class_index?: number;
  positive_class: string;
  positive_class_index: number;
  raw_model_score_meaning: string;
  decision_rule?: string;
}

export interface ClinicalMetrics {
  accuracy?: number | null;
  precision_parasitized?: number | null;
  recall_parasitized?: number | null;
  sensitivity_parasitized?: number | null;
  specificity?: number | null;
  f1_parasitized?: number | null;
  f2_parasitized?: number | null;
  roc_auc_parasitized?: number | null;
  pr_auc_parasitized?: number | null;
  balanced_accuracy?: number | null;
  prediction_collapse_detected?: boolean | null;
}

export interface ConfusionMatrix {
  labels: [string, string] | string[];
  matrix: number[][];
  tn?: number | null;
  fp?: number | null;
  fn?: number | null;
  tp?: number | null;
}

export interface CheckpointPolicySummary {
  policy?: string | null;
  checkpoint_policy?: string | null;
  min_recall_required?: number | null;
  selected_epoch?: number | null;
  policy_satisfied?: boolean | null;
  selected_metric?: string | null;
  selected_metric_value?: number | null;
  warning?: string | null;
  checkpoint_warning?: string | null;
  checkpoint_path?: string | null;
  created_at?: string | null;
}

export interface ThresholdCalibrationSummary {
  enabled?: boolean | null;
  threshold_policy?: string | null;
  threshold_source?: string | null;
  threshold_selected?: number | null;
  threshold_used?: number | null;
  default_threshold?: number | null;
  target_recall?: number | null;
  target_recall_satisfied?: boolean | null;
  validation_recall_at_threshold?: number | null;
  validation_specificity_at_threshold?: number | null;
  validation_f2_at_threshold?: number | null;
  threshold_warning?: string | null;
  warning?: string | null;
  calibration_split?: string | null;
  created_at?: string | null;
}

export interface RunArtifact {
  id?: string;
  artifact_type: string | null;
  artifact_path?: string | null;
  path?: string | null;
  exists?: boolean | null;
  created_at?: string | null;
  name?: string | null;
  mime_type?: string | null;
  file_size_bytes?: number | null;
}

export interface RunImagePrediction {
  run_image_prediction_id?: string;
  run_id: string;
  image_id?: string | null;
  split_name?: string | null;
  usage_context?: string | null;
  filename?: string | null;
  relative_path?: string | null;
  image_path?: string | null;
  image_url?: string | null;
  source_image_path?: string | null;
  source_image_url?: string | null;
  source_image_id?: string | null;
  crop_path?: string | null;
  crop_url?: string | null;
  true_label?: number | null;
  true_label_name?: string | null;
  predicted_label?: number | null;
  predicted_label_name?: string | null;
  probability_parasitized?: number | null;
  probability_uninfected?: number | null;
  raw_model_score?: number | null;
  raw_model_score_meaning?: string | null;
  threshold_used?: number | null;
  threshold_source?: string | null;
  is_correct?: boolean | null;
  case_type?: string | null;
  created_at?: string | null;
}

export interface ClinicalRunSummary {
  run_id: string;
  run_name?: string | null;
  model_name?: string | null;
  script_name?: string | null;
  run_type?: string | null;
  status?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  checkpoint_policy?: string | null;
  threshold_source?: string | null;
  threshold_used?: number | null;
  target_recall?: number | null;
  accuracy?: number | null;
  recall_parasitized?: number | null;
  specificity?: number | null;
  f2_parasitized?: number | null;
  pr_auc_parasitized?: number | null;
  roc_auc_parasitized?: number | null;
  balanced_accuracy?: number | null;
  prediction_collapse_detected?: boolean | null;
  checkpoint_warning?: string | null;
  threshold_warning?: string | null;
}

export interface RunClinicalSummary {
  run_id: string;
  model_name: string | null;
  script_name: string | null;
  run_type: string | null;
  status: string | null;
  started_at: string | null;
  finished_at: string | null;
  label_mapping: LabelMapping;
  clinical_metrics: ClinicalMetrics;
  confusion_matrix: ConfusionMatrix;
  checkpoint_policy: CheckpointPolicySummary;
  clinical_threshold: ThresholdCalibrationSummary;
  artifacts_count: number;
  image_predictions_count: number;
}

export interface ClinicalDashboard {
  latest_run: ClinicalRunSummary | null;
  items: ClinicalRunSummary[];
  warnings: Array<{ run_id: string | null; type: string; message: string | null }>;
  label_mapping: LabelMapping;
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

export interface ExplainabilityCase {
  [key: string]: JsonValue | undefined;
  explainability_id: string;
  prediction_id?: string | null;
  run_id?: string | null;
  experiment_id?: string | null;
  model_id?: string | null;
  model_name?: string | null;
  model_type?: string | null;
  dataset_id?: string | null;
  dataset_name?: string | null;
  run_name?: string | null;
  run_type?: string | null;
  run_status?: string | null;
  script_name?: string | null;
  command?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_at?: string | null;
  duration_seconds?: number | null;
  method?: string | null;
  case_type?: string | null;
  true_label?: string | null;
  predicted_label?: string | null;
  positive_label?: string | null;
  score?: number | null;
  score_positive_label?: number | null;
  probability_parasitized?: number | null;
  probability_uninfected?: number | null;
  threshold?: number | null;
  threshold_used?: number | null;
  threshold_source?: string | null;
  is_correct?: boolean | null;
  confidence_status?: string | null;
  confidence_level?: string | null;
  image_id?: string | null;
  image_path?: string | null;
  image_url?: string | null;
  image_stored_path?: string | null;
  original_image_path?: string | null;
  image_original_path?: string | null;
  original_filename?: string | null;
  uploaded_at?: string | null;
  prediction_upload_id?: string | null;
  source_image_path?: string | null;
  source_image_url?: string | null;
  source_image_id?: string | null;
  crop_path?: string | null;
  crop_url?: string | null;
  explanation_output_path?: string | null;
  explanation_url?: string | null;
  artifact_id?: string | null;
  artifact_path?: string | null;
  artifact_type?: string | null;
  last_conv_layer?: string | null;
  explanation_parameters?: JsonValue | null;
  prediction_metadata?: JsonValue | null;
  explainability_metadata?: JsonValue | null;
  run_parameters?: JsonValue | null;
  run_metadata?: JsonValue | null;
  interpretation?: string | null;
  success?: boolean | null;
  error_message?: string | null;
  dataset_split?: string | null;
  dataset_index?: number | null;
  manifest_id?: string | null;
  original_tfds_label?: string | number | null;
  remapped_label?: string | number | null;
  patient_id?: string | null;
  slide_id?: string | null;
  bbox_x?: number | null;
  bbox_y?: number | null;
  bbox_width?: number | null;
  bbox_height?: number | null;
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
