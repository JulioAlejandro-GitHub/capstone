import type {
  CellCropSummary,
  CellDetectionSummary,
} from './cellReview';

export type CellClassificationRunStatus =
  | 'created'
  | 'processing'
  | 'completed'
  | 'completed_with_warnings'
  | 'failed';

export type CellPredictionStatus = 'completed' | 'failed';
export type CanonicalCellLabel = 'uninfected' | 'parasitized';

export type CellExplanationStatus =
  | 'pending'
  | 'generated'
  | 'failed'
  | 'unsupported'
  | 'not_requested';

export type CellClassificationReviewDecision =
  | 'confirmed'
  | 'corrected'
  | 'needs_attention'
  | 'comment_only';

export type CellClassificationReviewStatus =
  | 'unreviewed'
  | 'confirmed'
  | 'corrected'
  | 'needs_attention';

export interface ProductiveModelDisplay {
  model_registry_id: string;
  model_name: string;
  model_version: string | null;
  production_model_id?: string | null;
  stage2_publication_id?: string;
  checkpoint_sha256?: string | null;
  threshold?: number | null;
  threshold_source?: string | null;
  technical_validation?: 'pending_inference';
  input_width?: number;
  input_height?: number;
  input_channels?: number;
  preprocessing?: Record<string, unknown>;
}

export interface CellClassificationModelSnapshot extends ProductiveModelDisplay {
  checkpoint_sha256: string;
  threshold: number;
  threshold_source: string;
  source_training_run_id?: string | null;
  source_evaluation_run_id?: string | null;
  checkpoint_artifact_id?: string | null;
  framework?: string;
  architecture?: string;
  label_mapping?: Record<string, string | number>;
  positive_label: 'parasitized';
  positive_class_index: 1;
  calibration_metadata?: Record<string, unknown> | null;
  published_at?: string | null;
  production_status?: string;
  stage2_default?: string | boolean | Record<string, unknown>;
  stage2_publication?: Record<string, unknown>;
  loader_version?: string;
  inference_version?: string;
  review_margin?: number;
  batch_size?: number;
  [key: string]: unknown;
}

export interface EligibleCellClassificationRun {
  detection_run_id: string;
  detection_run_code?: string;
  analysis_run_id?: string;
  eligible: boolean;
  reason_code?: string | null;
  message?: string | null;
  input_count?: number;
  eligible_count?: number;
  excluded_count?: number;
  productive_model: ProductiveModelDisplay | null;
}

export interface CellClassificationEvent {
  id: string;
  classification_run_id: string;
  cell_detection_id: string | null;
  cell_prediction_id: string | null;
  event_type: string;
  status: string;
  message_code: string | null;
  message: string | null;
  progress_current: number | null;
  progress_total: number | null;
  created_at: string;
}

export interface CellClassificationReviewCounts {
  unreviewed: number;
  confirmed: number;
  corrected: number;
  needs_attention: number;
}

export interface CellClassificationRunDetail {
  id: string;
  analysis_run_id: string;
  detection_run_id: string;
  classification_run_code: string;
  production_model_id: string | null;
  stage2_publication_id: string;
  model_name: string;
  model_version: string | null;
  model_snapshot: CellClassificationModelSnapshot;
  input_manifest_sha256: string;
  status: CellClassificationRunStatus;
  input_count: number;
  eligible_count: number;
  excluded_count: number;
  processed_count: number;
  parasitized_count: number;
  uninfected_count: number;
  near_threshold_count: number;
  failed_count: number;
  requested_by: string;
  retry_of_run_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  events?: CellClassificationEvent[];
  review_counts?: Partial<CellClassificationReviewCounts>;
  reused?: boolean;
  idempotent?: boolean;
}

export interface CellExplanation {
  id: string;
  cell_prediction_id: string;
  method: string;
  method_version: string;
  status: CellExplanationStatus;
  last_conv_layer: string | null;
  parameters_json: Record<string, unknown>;
  width_px: number | null;
  height_px: number | null;
  started_at: string | null;
  completed_at: string | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
}

export interface CellClassificationReview {
  id: string;
  cell_prediction_id: string;
  decision: CellClassificationReviewDecision;
  reviewed_label: CanonicalCellLabel | null;
  comment: string | null;
  actor_user_id: string;
  actor_username?: string | null;
  created_at: string;
}

export interface CellPredictionSummary {
  id: string;
  classification_run_id: string;
  analysis_run_id?: string;
  detection_run_id?: string;
  classification_input_id: string;
  cell_detection_id: string;
  crop_id: string;
  microscopy_image_id: string;
  image_sequence_number: number;
  cell_code: string;
  cell_index: number;
  prediction_status: CellPredictionStatus;
  probability_parasitized: number | null;
  probability_uninfected: number | null;
  predicted_label: CanonicalCellLabel | null;
  predicted_class_index: 0 | 1 | null;
  positive_label: 'parasitized';
  positive_class_index: 1;
  threshold_used: number;
  threshold_source: string;
  decision_margin: number | null;
  near_threshold: boolean;
  inference_duration_ms?: number | null;
  error_code: string | null;
  error_message: string | null;
  explanation: CellExplanation | null;
  explanation_status?: CellExplanationStatus;
  latest_review: CellClassificationReview | null;
  review_status: CellClassificationReviewStatus;
  detection?: CellDetectionSummary;
  crop?: CellCropSummary | null;
  bbox_x?: number;
  bbox_y?: number;
  bbox_width?: number;
  bbox_height?: number;
  coordinate_space?: 'original_image_pixels';
  detector_score?: number | null;
  automated_status?: string;
  detection_review_status?: CellDetectionSummary['review_status'];
  component?: CellDetectionSummary['component'];
  technical_warnings?: string[];
  created_at: string;
}

export interface CellPredictionDetail extends CellPredictionSummary {
  raw_output: Record<string, unknown> | unknown[];
  preprocessing_snapshot: Record<string, unknown>;
  model_name?: string;
  model_version?: string | null;
  checkpoint_sha256?: string;
  detection_detail?: CellDetectionSummary;
  review_history?: CellClassificationReview[];
}

export interface SmearReviewedSummary {
  outcome: 'suspicious_cells_detected' | 'no_suspicious_cells_detected' | 'inconclusive';
  eligible_cell_count: number;
  classified_cell_count: number;
  parasitized_candidate_count: number;
  uninfected_candidate_count: number;
  near_threshold_count: number;
  failed_prediction_count: number;
  parasitized_candidate_fraction: number | null;
}

export interface SmearAnalysisSummary {
  id: string;
  classification_run_id: string;
  analysis_run_id: string;
  detection_run_id: string;
  outcome: 'suspicious_cells_detected' | 'no_suspicious_cells_detected' | 'inconclusive';
  eligible_cell_count: number;
  classified_cell_count: number;
  parasitized_candidate_count: number;
  uninfected_candidate_count: number;
  near_threshold_count: number;
  failed_prediction_count: number;
  parasitized_candidate_fraction: number | null;
  maximum_probability_parasitized: number | null;
  mean_probability_parasitized: number | null;
  median_probability_parasitized: number | null;
  per_image_summary: Record<string, unknown>;
  aggregation_policy_snapshot: Record<string, unknown>;
  reviewed_summary?: SmearReviewedSummary | null;
  created_at: string;
}

export interface CellClassificationPage<T> {
  items: T[];
  total: number;
  limit?: number;
  offset?: number;
}

export interface CellClassificationReviewCreate {
  decision: CellClassificationReviewDecision;
  reviewed_label?: CanonicalCellLabel;
  comment?: string;
}
