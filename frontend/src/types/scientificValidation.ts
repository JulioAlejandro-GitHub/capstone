export type ScientificValidationTarget = 'cell' | 'analysis' | 'sample';

export interface ScientificValidationSessionSummary {
  id: string;
  status: 'draft' | 'annotation_in_progress' | 'ready_for_analysis' | 'completed' | 'archived';
  created_at: string;
}

export interface ScientificValidationSession extends ScientificValidationSessionSummary {
  detection_run_ids: string[];
  classification_run_ids: string[];
  image_ids: string[];
}

export interface ScientificValidationAnnotation {
  id: string;
  validation_session_id: string;
  target_type: ScientificValidationTarget;
  cell_detection_id: string | null;
  analysis_run_id: string | null;
  sample_id: string | null;
  category: string;
  content: string;
  created_by: string;
  created_by_username?: string | null;
  created_at: string;
  updated_by: string;
  updated_by_username?: string | null;
  updated_at: string;
  version: number;
}

export interface ScientificValidationAnnotationEvent {
  id: string;
  event_type: 'created' | 'updated' | 'archived';
  actor_user_id: string;
  actor_username?: string | null;
  annotation_version: number;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  created_at: string;
}

export interface ScientificValidationPage<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
