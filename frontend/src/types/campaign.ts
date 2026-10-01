// SWV2.2 campaign configuration contract (campaign_configuration_v1). The backend catalog is the
// only source of models, parameters, domains and defaults; nothing here enumerates architectures.

export type ParameterValue = boolean | number | string;
export type ParameterType = 'boolean' | 'integer' | 'number' | 'enum';

export interface CampaignParameter {
  key: string;
  label: string;
  section: 'architecture' | 'fine_tuning' | 'training' | 'selection';
  type: ParameterType;
  path: string;
  editable: boolean;
  default: ParameterValue;
  minimum?: number;
  maximum?: number;
  exclusive_maximum?: boolean;
  choices?: string[];
  note?: string;
  source: string;
}

export interface CampaignModel {
  id: string;
  label: string;
  adapter_version: string;
  strategies: string[];
  optimizers: string[];
  input_contract: string;
  output_contract: string;
  parameters: CampaignParameter[];
}

export interface CampaignOptimizer {
  id: string;
  label: string;
  learning_rate: number;
  fine_tune_learning_rate: number;
  parameters: Record<string, ParameterValue | null>;
  source: string;
}

export interface CampaignProtocolValues {
  early_stopping: { enabled: boolean; patience: number; min_delta: number; restore_best_weights: boolean };
  budget: { max_attempts_per_member: number };
}

export interface CampaignVariant {
  name: string;
  parameters: Record<string, Record<string, ParameterValue>>;
}

export interface CampaignConfiguration {
  version: string;
  models: string[];
  optimizers: string[];
  seeds: number[];
  variants: CampaignVariant[];
  protocol: CampaignProtocolValues;
}

export interface CampaignCatalog {
  version: string;
  models: CampaignModel[];
  optimizers: CampaignOptimizer[];
  seeds: { minimum: number; maximum: number; scope: string; default: number[]; source: string };
  protocol: {
    template_version: string;
    source: string;
    objective: string;
    editable: Array<{ key: string; type: ParameterType; label: string; default: ParameterValue; minimum?: number }>;
    fixed: Record<string, ParameterValue | null>;
  };
  presets: Array<{ id: string; label: string; configuration: CampaignConfiguration }>;
  default_preset: string;
  experiment_formula: string;
}

export interface CampaignFieldError { field: string; code: string }

export interface CampaignSummary {
  models: number;
  optimizers: number;
  variants: number;
  seeds: number;
  configurations: number;
  total_experiments: number;
  experiments_per_model: Record<string, number>;
  configuration_list: Array<{ configuration_hash: string; model_id: string; optimizer: string; variants: string[] }>;
}

export interface CampaignPreview {
  valid: boolean;
  checks: Array<{ check: string; label: string; status: 'PASS' | 'FAIL'; errors: CampaignFieldError[] }>;
  errors: CampaignFieldError[];
  summary: CampaignSummary | null;
  protocol: { version: string; sensitivity_target: number } | null;
  dataset: { dataset_version_id: string; status: string; trainable: boolean } | null;
}

export interface SavedCampaign {
  campaign_id: string;
  name: string;
  purpose: string;
  state: string;
  contract_hash: string;
  frozen_at: string;
  dataset_version_id: string;
  dataset: { counts: Record<string, number> | null; dataset_materialization_id: string | null; dataset_evidence_id: string };
  models: string[];
  optimizers: string[];
  seeds: number[];
  protocol: { version: string; early_stopping: Record<string, ParameterValue | null>; budget: Record<string, number> };
  configurations: Array<{ configuration_hash: string; model_id: string; optimizer: string; variants: string[] }>;
  experiments: Array<{ position: number; member_id: string; model_id: string; optimizer: string; seed: number; state: string }>;
  total_experiments: number;
  experiments_per_model: Record<string, number>;
  command: string;
  execution_boundary: string;
}
