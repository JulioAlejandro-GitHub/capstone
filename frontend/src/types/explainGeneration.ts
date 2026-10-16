import type { AssessmentArtifact, AssessmentDetail } from './api';
import type { XAIMethod } from '../components/reports/xai/comparison';

export interface ExplainRequest {
  source_attempt_id: string;
  sample_id: string;
  methods: XAIMethod[];
  class_id?: 0 | 1;
}
export interface ExplainState {
  training_run_id: string;
  dataset_version_id: string;
  sample_id: string;
  authorized: boolean;
  methods: Array<{
    method: XAIMethod;
    state: 'not_executed' | 'pending' | 'running' | 'completed' | 'failed';
    attempt_id?: string;
    identity_id?: string;
    error?: string;
    detail?: AssessmentDetail;
    artifacts: AssessmentArtifact[];
  }>;
}
export interface ExplainSubmission {
  operations: Array<{method: XAIMethod; operation_id?: string; attempt_id?: string; state?: 'pending' | 'running' | 'completed'; error?: string}>;
}
