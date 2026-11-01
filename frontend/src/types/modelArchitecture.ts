export type ArchitectureOrigin = 'recorded' | 'derived' | 'reference';
export type ArchitectureFamily = 'custom_cnn' | 'vgg16' | 'densenet121' | 'biomedclip' | 'generic';
export type ArchitectureShape = (number | null)[] | null;

export interface ArchitectureLayer {
  name: string; type: string; block: string; output_shape: ArchitectureShape; inputs: string[];
  parameters: number | null; trainable_phases: string[]; settings: Record<string, unknown>;
}

export interface ArchitectureBlock {
  id: string; label: string; kind: 'input' | 'convolution' | 'dense' | 'transition' | 'encoder' | 'head' | 'output';
  layers: number; units: number | null; output_shape: ArchitectureShape; parameters: number | null;
  trainable_phases: string[]; origin: ArchitectureOrigin;
}

export interface ArchitectureOutput {
  neurons: number | null; activation: string | null; loss: string | null; from_logits: boolean | null;
  meaning: string | null; embedding_features?: number | null;
}

export interface ArchitecturePhase {
  phase: string; trainable_parameters: number | null; trainable_tensors: number | null; encoder: string | null;
}

export interface ModelArchitecture {
  training_run_id: string; state: 'available' | 'missing'; issues: string[]; model_name: string | null; architecture: string | null;
  family: ArchitectureFamily; framework: string | null; input_shape: ArchitectureShape; output: ArchitectureOutput | null;
  total_parameters: number | null; checkpoint: { artifact_id: string | null; selected_epoch: number | null; phase: string | null };
  phases: ArchitecturePhase[]; blocks: ArchitectureBlock[]; layers: ArchitectureLayer[];
}
