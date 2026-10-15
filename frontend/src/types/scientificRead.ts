import type { ModelSummary } from './api';

export type ScientificRecord = Record<string, unknown>;
export interface TrainingReference {
  training_run_id: string;
  status: string;
  run_name: string | null;
  dataset_version_id: string | null;
  started_at: string | null;
}
export interface ModelCatalog {
  items: (ModelSummary & {
    training_runs: TrainingReference[];
    has_training_runs: boolean;
    has_completed_training: boolean;
  })[];
  comparison: { scc_max_comparison_runs: number };
}
export interface ScientificTraceability {
  contract_version: 'scc_core_1';
  training_run_id: string;
  model: ScientificRecord | null;
  training: ScientificRecord;
  evidence: Record<string, unknown>;
  assessments: (ScientificRecord & {
    identity_id: string;
    attempt_id: string;
    training_run_id: string;
    assessment_type: 'EVALUATE' | 'EXPLAIN' | 'TEST';
    split: string | null;
  })[];
  evidence_status: Record<string, 'available' | 'not_persisted'>;
  references: Record<string, string>;
}

export type ScientificModelCatalog = Omit<ModelCatalog, 'items'> & {
  items: Omit<ModelCatalog['items'][number],
    'best_accuracy' | 'best_recall' | 'best_f1_score' | 'best_auc'>[];
};
