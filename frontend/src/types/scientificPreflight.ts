// Mirrors backend_api/app/schemas/scientific_preflight.py (scc_pre_1).
export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };
export type Observation<T = JsonValue> =
  | { state: 'known'; value: T; evidence_ids: string[] }
  | { state: 'unknown' | 'not_applicable' | 'not_checked'; reason: string; evidence_ids: string[] }
  | { state: 'query_error'; error_ids: string[] };
export type ScientificState = 'COMPARABLE' | 'COMPARABLE_CON_ADVERTENCIAS' | 'NO_COMPARABLE' | 'EVIDENCIA_INSUFICIENTE';
export type Dimension = 'A1' | 'A2' | 'A3' | 'A4' | 'A5' | 'A6';
export type Module = 'curves' | 'metrics' | 'consensus' | 'xai' | 'embeddings' | 'pca' | 'umap' | 'cka';
export type Split = 'train' | 'val' | 'test';
export interface RequestedSelection {
  training_run_id: string;
  evaluation?: { source: 'assessment'; identity_id: string; attempt_id: string } | { source: 'evaluations'; evaluation_id: string } | null;
  split?: Split | null;
  checkpoint_artifact_id?: string | null;
}
export interface PreflightRequest { selections: RequestedSelection[] }
export interface EffectiveSelection {
  selection_id: string; training_run_id: string; dataset_version_id: Observation<string>;
  evaluation: Observation; split: Observation<Split>; checkpoint: Observation<string>; selection_reason: string;
}
export interface Scope {
  scope_id: string; requested_training_run_ids: string[]; participating_training_run_ids: string[];
  selection_ids: string[]; population: 'original' | 'intersection' | 'not_applicable'; question: string;
}
export interface Finding {
  reason_id: string; code: string; kind: 'difference' | 'warning' | 'missing' | 'incompatibility';
  message: string; condition: string; affected_selection_ids: string[]; evidence_ids: string[];
}
export type Verdict = { evaluation_status: 'evaluated'; scientific_state: ScientificState; error_ids: string[] }
  | { evaluation_status: 'not_evaluated'; scientific_state: null; error_ids: string[] };
export interface DimensionResult { dimension: Dimension; scope: Scope; verdict: Verdict; evidence_ids: string[]; findings: Finding[] }
export interface AnalysisResult {
  analysis_id: string; module_id: Module; scope: Scope; verdict: Verdict; dimension_refs: string[];
  evidence_ids: string[]; findings: Finding[]; interpretation_limits: string[];
  individual_data: { selection_id: string; availability: Observation<boolean>; references: string[] }[];
}
export interface EvidenceRef {
  evidence_id: string; source: string; operation: string; record_keys: Record<string, string>;
  field: string | null; selection_ids: string[]; observed_at: string;
  verification: 'operational' | 'not_verified'; value: Observation;
}
export interface PopulationMember {
  selection_id: string; expected_unique: Observation<number>; retrieved_rows: Observation<number>;
  retrieved_unique: Observation<number>; duplicate_count: Observation<number>; label_conflict_count: Observation<number>;
  missing_count: Observation<number>; exclusive_count: Observation<number>; numerator: Observation<number>;
  denominator: Observation<number>; ratio: Observation<number>; evidence_ids: string[];
}
export interface PopulationCoverage {
  population_id: string; scope_id: string; alignment_key: Observation<string>; complete: Observation<boolean>;
  per_selection: PopulationMember[]; intersection_unique: Observation<number>; identity_references: string[]; subset_rule: string | null;
}
export interface CheckpointCheck {
  selection_id: string; artifact_id: string; registered: Observation<boolean>; lineage: Observation<boolean>;
  availability: 'not_checked'; integrity: 'not_checked'; checked_at: null; evidence_ids: string[]; error_ids: string[];
}
export interface PreflightResponse {
  contract_version: 'scc_pre_1'; generated_at: string; correlation_id: string;
  consistency: { mode: 'repeatable_read' | 'partial'; started_at: string; completed_at: string; limitations: string[] };
  selections: EffectiveSelection[]; dimensions: DimensionResult[]; analyses: AnalysisResult[];
  evidence: EvidenceRef[]; populations: PopulationCoverage[]; checkpoints: CheckpointCheck[];
  technical_errors: { error_id: string; state: 'ERROR_DE_CONSULTA'; code: string; message: string; operation: string;
    scope_ids: string[]; selection_ids: string[]; correlation_id: string; retryable: boolean }[];
  summary: { by_state: Record<ScientificState, number>; not_evaluated: number; analysis_count: number;
    warning_reason_ids: string[]; technical_error_ids: string[] };
}
