import type { ActivationTraceStep, ActivationTraceSummary, TraceCategory } from '../../types/activationTrace';

export const traceCategories: Record<TraceCategory, string> = {
  false_negative: 'Falso negativo', false_positive: 'Falso positivo', true_positive: 'Verdadero positivo', true_negative: 'Verdadero negativo',
};

export const outcomeOf = ({ label, predicted }: Pick<ActivationTraceSummary, 'label' | 'predicted'>) => {
  if (label == null || predicted == null) return 'Sin evidencia';
  return traceCategories[label ? (predicted ? 'true_positive' : 'false_negative') : (predicted ? 'false_positive' : 'true_negative')];
};
export const number = (value: number | null | undefined, digits = 4) => value == null ? 'Sin evidencia' : value.toLocaleString('es-CL', { maximumFractionDigits: digits });
export const percent = (value: number) => `${(value * 100).toLocaleString('es-CL', { maximumFractionDigits: 1 })} %`;
export const points = (value: number) => `${(value * 100).toLocaleString('es-CL', { maximumFractionDigits: 1 })} pp`;
export const megabytes = (bytes: number) => `${(bytes / 1048576).toLocaleString('es-CL', { maximumFractionDigits: 1 })} MB`;

/** Change against the previous step that shares its kind of tensor; 1D and 2D means are not comparable. */
export function stepChange(steps: ActivationTraceStep[], index: number) {
  const current = steps[index], previous = steps[index - 1];
  if (!previous || previous.kind !== current.kind) return null;
  return { active: current.stats.active - previous.stats.active, mean: current.stats.mean - previous.stats.mean };
}
