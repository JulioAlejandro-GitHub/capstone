import type { CurveEvidence } from '../../types/scientificReport';
import type { TrainingTrajectories } from '../../types/trainingTrajectories';

/**
 * Historia del TRAIN para la vista «Entrenamiento». Todo se calcula desde lo que TRAIN registró
 * (épocas y predicciones VAL por época); nada se interpola ni se completa.
 */

export type TrainingView = 'flujo' | 'curvas' | 'lr' | 'trayectorias' | 'checkpoints';
export type EvidenceOrigin = 'registrado' | 'derivable' | 'sin_evidencia';

export const TRAINING_VIEWS: { id: TrainingView; label: string; origin: EvidenceOrigin | null }[] = [
  { id: 'flujo', label: 'Flujo de tensores', origin: null },
  { id: 'curvas', label: 'Curvas por época', origin: 'registrado' },
  { id: 'lr', label: 'Learning rate', origin: 'registrado' },
  { id: 'trayectorias', label: 'Trayectoria de células', origin: 'registrado' },
  { id: 'checkpoints', label: 'Análisis de checkpoints', origin: 'derivable' },
];

export const ORIGIN_LABELS: Record<EvidenceOrigin, string> = {
  registrado: 'Registrado en TRAIN', derivable: 'Derivable del checkpoint', sin_evidencia: 'Sin evidencia',
};

export const viewFrom = (value: string | null): TrainingView => TRAINING_VIEWS.find(view => view.id === value)?.id ?? 'flujo';

/* ── Learning rate ─────────────────────────────────────────────────────────── */

export interface LearningRatePoint { epoch: number; phase: string; lr: number }
export interface LearningRateChange { epoch: number; phase: string; from: number; to: number; factor: number; phaseStart: boolean }

export function learningRateSeries(curve: CurveEvidence | null): LearningRatePoint[] {
  return (curve?.epochs ?? [])
    .filter(epoch => Number.isFinite(epoch.values.learning_rate) && epoch.values.learning_rate > 0)
    .map(epoch => ({ epoch: epoch.epoch, phase: epoch.phase, lr: epoch.values.learning_rate }))
    .sort((a, b) => a.epoch - b.epoch);
}

/** Cambios entre épocas consecutivas registradas; no se atribuye la causa (callback o fase) sin evidencia. */
export function learningRateChanges(points: LearningRatePoint[]): LearningRateChange[] {
  const changes: LearningRateChange[] = [];
  for (let i = 1; i < points.length; i++) {
    const [before, after] = [points[i - 1], points[i]];
    if (Math.abs(after.lr - before.lr) > Math.max(before.lr, after.lr) * 1e-6) {
      changes.push({ epoch: after.epoch, phase: after.phase, from: before.lr, to: after.lr, factor: after.lr / before.lr, phaseStart: after.phase !== before.phase });
    }
  }
  return changes;
}

/* ── Trayectorias ──────────────────────────────────────────────────────────── */

/** Probabilidad que el modelo asignó a la clase real de la célula. */
export const trueClassProbability = (label: 0 | 1, score: number | null) => score == null ? null : label === 1 ? score : 1 - score;
const correct = (label: 0 | 1, score: number | null, threshold: number) => score == null ? null : (score >= threshold ? 1 : 0) === label;

export type TrajectoryOutcome = 'aprendida' | 'olvidada' | 'nunca' | 'inestable';
export const OUTCOME_LABELS: Record<TrajectoryOutcome, string> = {
  aprendida: 'Aprendida y estable', olvidada: 'Olvidada al final', nunca: 'Nunca bien clasificada', inestable: 'Bien al final, con oscilaciones',
};

export interface SampleTrajectory {
  index: number;
  sample: string;
  label: 0 | 1;
  sampleId: string | null;
  /** Primera época desde la cual queda bien clasificada hasta la última registrada; null si termina mal. */
  learnedAt: number | null;
  flips: number;
  outcome: TrajectoryOutcome;
}

export function sampleTrajectories(data: TrainingTrajectories): SampleTrajectory[] {
  const threshold = data.training_threshold;
  return data.samples.map((sample, index) => {
    const marks = data.scores[index].map(score => correct(sample.label, score, threshold));
    let flips = 0;
    for (let i = 1; i < marks.length; i++) if (marks[i] != null && marks[i - 1] != null && marks[i] !== marks[i - 1]) flips++;
    let start = marks.length;
    while (start > 0 && marks[start - 1] === true) start--;
    const learnedAt = start < marks.length ? data.epochs[start].epoch : null;
    const everRight = marks.some(mark => mark === true);
    const outcome: TrajectoryOutcome = learnedAt == null ? (everRight ? 'olvidada' : 'nunca') : flips > 1 ? 'inestable' : 'aprendida';
    return { index, sample: sample.sample, label: sample.label, sampleId: sample.sample_id, learnedAt, flips, outcome };
  });
}

/** Orden del mapa: por clase, luego por época de aprendizaje (las nunca aprendidas al final). */
export function orderTrajectories(items: SampleTrajectory[]): SampleTrajectory[] {
  const rank = (item: SampleTrajectory) => item.learnedAt ?? Number.MAX_SAFE_INTEGER;
  return [...items].sort((a, b) => b.label - a.label || rank(a) - rank(b) || b.flips - a.flips || a.sample.localeCompare(b.sample));
}

export interface EpochAccuracy { epoch: number; phase: string; parasitized: number | null; uninfected: number | null; all: number | null }

/** Fracción bien clasificada por clase en cada época, al umbral con que TRAIN registró las predicciones. */
export function accuracyByEpoch(data: TrainingTrajectories): EpochAccuracy[] {
  return data.epochs.map((epoch, column) => {
    const tally = { 1: [0, 0], 0: [0, 0] } as Record<0 | 1, [number, number]>;
    data.samples.forEach((sample, row) => {
      const mark = correct(sample.label, data.scores[row][column], data.training_threshold);
      if (mark == null) return;
      tally[sample.label][1]++;
      if (mark) tally[sample.label][0]++;
    });
    const ratio = ([ok, total]: [number, number]) => total ? ok / total : null;
    const all: [number, number] = [tally[0][0] + tally[1][0], tally[0][1] + tally[1][1]];
    return { epoch: epoch.epoch, phase: epoch.phase, parasitized: ratio(tally[1]), uninfected: ratio(tally[0]), all: ratio(all) };
  });
}

export function outcomeCounts(items: SampleTrajectory[]): Record<TrajectoryOutcome, number> {
  const counts: Record<TrajectoryOutcome, number> = { aprendida: 0, olvidada: 0, nunca: 0, inestable: 0 };
  items.forEach(item => { counts[item.outcome]++; });
  return counts;
}

export const fineTuneStart = (phases: { epoch: number; phase: string }[]) => phases.find(item => item.phase === 'fine_tuning')?.epoch ?? null;

/* ── Análisis derivables de checkpoints (aún no calculados) ───────────────── */

export const CHECKPOINT_ANALYSES: { title: string; origin: EvidenceOrigin; question: string; source: string }[] = [
  { title: 'Movimiento de pesos', origin: 'derivable', question: 'Qué capas cambian, cuánto y en qué fase.', source: 'Norma y cambio relativo por capa entre checkpoints de épocas consecutivas.' },
  { title: 'Embeddings por época', origin: 'derivable', question: 'Cuándo se separan las clases en la representación.', source: 'PCA/UMAP de la misma población VAL en cada checkpoint, con medida de separación.' },
  { title: 'Estabilización por capa', origin: 'derivable', question: 'Qué capas se fijan primero.', source: 'CKA de cada capa contra el checkpoint seleccionado.' },
  { title: 'Grad-CAM a través de épocas', origin: 'derivable', question: 'Cómo se desplaza la atención sobre una misma célula.', source: 'Grad-CAM de la célula sobre cada checkpoint por época.' },
  { title: 'Recorrido de activación por época', origin: 'derivable', question: 'Cómo cambia lo que cada bloque responde a la célula.', source: 'El recorrido actual, aplicado a cualquier checkpoint y arquitectura.' },
  { title: 'Dentro de cada batch', origin: 'sin_evidencia', question: 'Loss por paso, gradientes aplicados e imágenes de cada batch.', source: 'No se observa dentro del fit: hacerlo cambia la ejecución (TRACE.*). Se muestra como no demostrado.' },
];
