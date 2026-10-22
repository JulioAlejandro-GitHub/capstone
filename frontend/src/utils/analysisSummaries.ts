import type { ClinicalEvidence, ConsensusEvidence, CurveEvidence } from '../types/scientificReport';

// Descriptive summaries of evidence already returned by the report modules; nothing is recalculated.
export const FINE_TUNING_PHASE = 'fine_tuning';

export function curveSummary(run: CurveEvidence) {
  const fineExecuted = run.epochs.filter(epoch => epoch.phase === FINE_TUNING_PHASE).length;
  const baseExecuted = run.epochs.length ? run.epochs.length - fineExecuted : run.executed_epochs;
  const selected = run.checkpoint.selected_epoch;
  const atCheckpoint = run.epochs.find(epoch => epoch.epoch === selected)?.values ?? {};
  const trainLoss = atCheckpoint.loss ?? null;
  const valLoss = atCheckpoint.val_loss ?? null;
  return {
    baseExecuted, fineExecuted,
    baseConfigured: run.max_epochs ?? null,
    fineConfigured: run.fine_tune_epochs ?? null,
    configuredTotal: run.max_epochs == null ? null : run.max_epochs + (run.fine_tune_epochs ?? 0),
    checkpointEpoch: selected,
    checkpointPhase: run.checkpoint.phase,
    trainLoss, valLoss,
    gap: trainLoss != null && valLoss != null ? valLoss - trainLoss : null,
    // Fine-tuning ran but the selection policy kept a base-phase checkpoint.
    baseCheckpointAfterFineTuning: fineExecuted > 0 && run.checkpoint.phase != null && run.checkpoint.phase !== FINE_TUNING_PHASE,
  };
}

export function metricRange(runs: ClinicalEvidence[], key: string) {
  const values = runs.flatMap(run => {
    const metric = run.state === 'available' ? run.clinical?.metrics[key]?.value : null;
    return metric == null ? [] : [metric];
  });
  return values.length ? { min: Math.min(...values), max: Math.max(...values) } : null;
}

export function pairwise(matrix: number[][] | undefined) {
  const pairs: { i: number; j: number; count: number }[] = [];
  matrix?.forEach((row, i) => row.forEach((count, j) => { if (j > i) pairs.push({ i, j, count }); }));
  return pairs;
}

export function consensusSummary(data: ConsensusEvidence) {
  const n = data.common_count ?? 0;
  const errors = pairwise(data.error_overlap);
  const agreement = pairwise(data.agreement);
  const fewestSharedErrors = errors.length ? errors.reduce((best, pair) => pair.count < best.count ? pair : best) : null;
  const ratios = agreement.map(pair => n ? pair.count / n : 0);
  return { n, fewestSharedErrors, agreementRange: ratios.length ? { min: Math.min(...ratios), max: Math.max(...ratios) } : null };
}

// Cell intensity for heatmaps: 0 → no tint, 1 → full tint.
export const intensity = (count: number, total: number) => total > 0 ? Math.max(0, Math.min(1, count / total)) : 0;
