export type TraceCategory = 'false_negative' | 'false_positive' | 'true_positive' | 'true_negative';

export interface ActivationTraceSummary {
  sample_id: string; created_at: string; label: number | null; predicted: number | null; score: number;
  persisted_score: number | null; consistent: boolean; split: string; bytes: number;
}

export interface ActivationTraceCatalog {
  available: boolean; reason: string | null; split: string | null; items: ActivationTraceSummary[]; used_bytes: number; max_bytes: number;
}

export interface ActivationTraceCandidate { sample_id: string; label: number; predicted: number; score: number; threshold: number; explained?: boolean }

export interface ActivationTraceStep {
  layer: string; block: string; kind: 'spatial' | 'vector' | 'output'; shape: number[];
  stats: { min: number; max: number; mean: number; std: number; active: number };
  /** min/max per channel exist from activation_trace_v2: older traces can only be drawn on their own scale. */
  maps: { channel: number; mean: number; png: string; min?: number; max?: number }[]; top: { index: number; value: number }[];
  histogram?: { counts: number[]; edges: number[] } | null;
  /** ViT: tokens del tensor (parches + clase); los mapas son la rejilla de parches, uno por dimensión del token. */
  tokens?: number;
  /** ViT: atención del token de clase sobre los parches (promedio de las cabezas), en la misma rejilla. */
  attention?: { png: string; min: number; max: number } | null;
  /** ViT: similitud coseno del token de clase con el del último bloque. */
  cls_similarity?: number;
}

export interface ActivationTrace extends ActivationTraceSummary {
  version: string; training_run_id: string; attempt_id: string; checkpoint_sha256: string; threshold: number | null;
  logit: number; selection: string; input_image: string; steps: ActivationTraceStep[];
}
