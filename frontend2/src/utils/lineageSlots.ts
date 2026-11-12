import type { AssessmentExplanationChild, TrainingLineageChildren } from '../types/api';
import type { EvaluationChoice } from '../types/scientificReport';

// Fixed lineage of a TRAIN: TRAIN → EVALUATE VAL / EVALUATE TEST / EXPLAIN [gradcam, shap, lime].
export type EvaluationSlot = 'train' | 'val' | 'test';
export const evaluationSlots: { id: EvaluationSlot; label: string; detail: string }[] = [
  { id: 'train', label: 'TRAIN · VAL', detail: 'Validación registrada por el entrenamiento' },
  { id: 'val', label: 'EVALUATE · VAL', detail: 'Evaluación independiente de desarrollo' },
  { id: 'test', label: 'EVALUATE · TEST', detail: 'Evaluación independiente final' },
];
export const defaultEvaluationSlot: EvaluationSlot = 'test';
const fallbackOrder: EvaluationSlot[] = ['test', 'val', 'train'];
export const explainMethods = [
  { id: 'gradcam', label: 'Grad-CAM' }, { id: 'shap', label: 'SHAP' }, { id: 'lime', label: 'LIME' },
] as const;

export const roleLabels: Record<string, string> = {
  independent_evaluate: 'Evaluación independiente',
  training_validation_final: 'Validación final del entrenamiento',
  calibration_selected: 'Calibración · umbral seleccionado',
  calibration_default: 'Calibración · umbral 0,5',
};

export const choiceKey = (choice: EvaluationChoice) => choice.evaluation_id ?? choice.attempt_id ?? '';

export function slotOf(choice: EvaluationChoice): EvaluationSlot {
  if (choice.evaluation_role !== 'independent_evaluate') return 'train';
  return choice.split === 'test' ? 'test' : 'val';
}

// Keeps the catalog order (most recent first) inside each slot.
export function groupEvaluations(choices: EvaluationChoice[]) {
  const groups: Record<EvaluationSlot, EvaluationChoice[]> = { train: [], val: [], test: [] };
  for (const choice of choices) groups[slotOf(choice)].push(choice);
  return groups;
}

// The analysis protocol applies to every RUN; an explicit choice in a card overrides it for that RUN only.
export function effectiveSlot(groups: Record<EvaluationSlot, EvaluationChoice[]>, protocol: EvaluationSlot, override: EvaluationSlot | null) {
  if (override && groups[override].length) return override;
  if (groups[protocol].length) return protocol;
  return fallbackOrder.find(slot => groups[slot].length) ?? null;
}

export const isAssessmentExplanation = (child: TrainingLineageChildren['explainabilities'][number]): child is AssessmentExplanationChild =>
  child.source_kind === 'assessment_explain_e6';

export function groupExplanations(children: AssessmentExplanationChild[]) {
  const groups: Record<string, AssessmentExplanationChild[]> = {};
  for (const child of [...children].sort((a, b) => b.started_at.localeCompare(a.started_at))) {
    const method = (child.method ?? 'sin_metodo').toLowerCase().replace(/[^a-z]/g, '');
    (groups[method] ??= []).push(child);
  }
  return groups;
}

// Population EXPLAIN (a split) is chosen in the card; per-cell EXPLAIN generated from the report is always
// included, since each one covers a different cell.
export const isCellExplanation = (child: AssessmentExplanationChild) => child.result_count === 1;
export function splitExplanations(children: AssessmentExplanationChild[] = []) {
  return { population: children.filter(child => !isCellExplanation(child)), cells: children.filter(isCellExplanation) };
}
