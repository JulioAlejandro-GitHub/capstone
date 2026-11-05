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

export interface LearningRateGroup { group: string | null; learning_rate: number | null; parameters?: number | null }

export interface ArchitecturePhase {
  phase: string; trainable_parameters: number | null; trainable_tensors: number | null; encoder: string | null;
  /** ViT: el conjunto entrenable registrado frente al que declara la base registrada. */
  structure_check?: 'match' | 'mismatch' | null;
  /** Learning rate inicial de cada grupo del optimizador en la fase (Keras: un grupo «model»). */
  learning_rates?: LearningRateGroup[];
}

/** Estructura de un ViT derivada una vez desde la base registrada (SHA-256), no desde pesos entrenados. */
export interface ArchitectureStructure {
  origin: 'derived'; base_sha256: string; vit_blocks: number | null; patch_size: number[] | null; width: number | null;
  patches: number | null; tokens: number | null;
}

export interface ModelArchitecture {
  training_run_id: string; state: 'available' | 'missing'; issues: string[]; model_name: string | null; architecture: string | null;
  family: ArchitectureFamily; framework: string | null; input_shape: ArchitectureShape; output: ArchitectureOutput | null;
  total_parameters: number | null; checkpoint: { artifact_id: string | null; selected_epoch: number | null; phase: string | null };
  phases: ArchitecturePhase[]; blocks: ArchitectureBlock[]; layers: ArchitectureLayer[];
  structure?: ArchitectureStructure | null;
  /** TRAIN lógico (zero-shot): protocolo congelado de la versión registrada; no hubo entrenamiento. */
  zero_shot?: { model_version_id: string; prompts: string[]; class_order: string[]; training_performed: boolean } | null;
}
