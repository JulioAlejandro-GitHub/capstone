export type CellReviewStatus =
  | 'unreviewed'
  | 'accepted'
  | 'rejected'
  | 'needs_attention';

export type CellReviewFilter = 'all' | CellReviewStatus;

export type CellDetectionRunStatus =
  | 'created'
  | 'processing'
  | 'completed'
  | 'completed_with_warnings'
  | 'failed';

export type CellReviewDecision =
  | 'accepted'
  | 'rejected'
  | 'needs_attention'
  | 'comment_only';

export interface CellReviewCounts {
  unreviewed: number;
  accepted: number;
  rejected: number;
  needs_attention: number;
}

export interface CellRunReviewCounts {
  reviewed?: number;
  pending?: number;
  unreviewed?: number;
  accepted: number;
  rejected: number;
  needs_attention: number;
}

export interface EligibleCellAnalysisRun {
  id: string;
  run_code: string;
  subject_code: string;
  sample_code: string;
  slide_code: string;
  input_image_count: number;
  quality_gate_status: string;
  ready_for_analysis: boolean;
  created_at: string;
}

export interface CellDetectionRunSummary {
  id: string;
  detection_run_code: string;
  analysis_run_id: string;
  analysis_run_code: string;
  subject_code: string;
  sample_code: string;
  slide_code: string;
  detector_key: string;
  detector_version: string;
  algorithm_version: string;
  status: CellDetectionRunStatus;
  image_count: number;
  processed_image_count: number;
  component_count: number;
  detection_count: number;
  crop_count: number;
  warning_count: number;
  reviewed_count: number;
  pending_review_count: number;
  created_at: string;
  started_at?: string | null;
  completed_at: string | null;
}

export interface CellDetectionRunDetail extends CellDetectionRunSummary {
  profile_snapshot: Record<string, unknown>;
  review_counts: CellRunReviewCounts;
  images?: CellDetectionImage[];
  error_code?: string | null;
  error_message?: string | null;
}

export interface CellDetectionImage {
  analysis_run_image_id: string;
  microscopy_image_id: string;
  sequence_number: number;
  safe_name: string;
  width_px: number;
  height_px: number;
  mime_type: string;
  detection_count: number;
  reviewed_count: number;
  warning_count: number;
  content_url: string;
}

export interface CellCropSummary {
  id: string;
  sha256: string;
  width_px: number;
  height_px: number;
  format: string;
  padding_px: number;
  content_url: string;
}

export interface ConnectedComponentSummary {
  area_px: number;
  perimeter_px: number | null;
  circularity: number | null;
  solidity: number | null;
  touches_border: boolean;
  metrics_json: Record<string, unknown>;
}

export interface CellDetectionSummary {
  id: string;
  cell_code: string;
  cell_index: number;
  bbox_x: number;
  bbox_y: number;
  bbox_width: number;
  bbox_height: number;
  coordinate_space: 'original_image_pixels';
  detector_score: number | null;
  automated_status: string;
  review_status: CellReviewStatus;
  crop: CellCropSummary | null;
  component: ConnectedComponentSummary;
  technical_warnings?: string[];
}

export interface ScientificCellReview {
  id: string;
  entity_type?: 'cell_detection';
  entity_id?: string;
  decision: CellReviewDecision;
  comment: string | null;
  actor_user_id: string;
  actor_username?: string | null;
  created_at: string;
}

export interface CellDetectionDetail extends CellDetectionSummary {
  detection_run_code: string;
  detector_key?: string;
  detector_version?: string;
  algorithm_version?: string;
  detector?: {
    key: string;
    version: string;
    algorithm_version: string;
  };
  analysis_run_image_id?: string;
  microscopy_image_id?: string;
  source_image?: {
    microscopy_image_id: string;
    sequence_number: number;
    safe_name: string;
    width_px: number;
    height_px: number;
  };
  safe_name?: string;
  latest_review: ScientificCellReview | null;
  review_history: ScientificCellReview[];
}

export interface CellDetectionReviewResult extends ScientificCellReview {
  effective_review_status: CellReviewStatus;
}

export interface CellAnalysisPage<T> {
  items: T[];
  total: number;
  limit?: number;
  offset?: number;
}
