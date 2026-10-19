import type { JsonValue, Observation, PreflightResponse, Dimension } from '../types/scientificPreflight';

// Object order is immaterial; array order, types, identifiers and numeric values are not.
export function stableValue(value: JsonValue): string {
  if (Array.isArray(value)) return `[${value.map(stableValue).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stableValue(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}
function completeValue(value: JsonValue): boolean {
  if (value === null || value === '' || value === 'Sin evidencia') return false;
  if (typeof value !== 'object') return true;
  const items = Array.isArray(value) ? value : Object.values(value);
  return items.length > 0 && items.every(completeValue);
}
export function equalityKey(value: Observation | undefined): string | undefined {
  return value?.state === 'known' && completeValue(value.value) ? stableValue(value.value) : undefined;
}
export function compareValues(values: (Observation | undefined)[]) {
  const keys = values.map(equalityKey);
  const present = keys.filter((key): key is string => key !== undefined);
  const repeated = [...new Set(present)].filter(key => present.filter(item => item === key).length > 1).sort();
  const complete = present.length === values.length && values.length > 1;
  return { complete, group: new Set(present).size > 1 ? 'Con diferencias' : complete ? 'Sin diferencias' : 'Comparables',
    matches: keys.map(key => key === undefined || !repeated.includes(key) ? undefined : keys.flatMap((item, index) => item === key ? [String.fromCharCode(65 + index)] : []).join('')) };
}
export function projectField(data: PreflightResponse, source: Dimension, selectionId: string, field: string): Observation | undefined {
  const refs = data.evidence.filter(ref => ref.source === source && ref.selection_ids.includes(selectionId));
  const observations = refs.flatMap(ref => {
    const value = ref.value.state === 'known' ? ref.value.value : null;
    const projected = field.split('.').reduce<JsonValue | undefined>((item, key) => item && typeof item === 'object' && !Array.isArray(item) ? item[key] : undefined, value);
    return projected !== undefined && projected !== null
      ? [{ state: 'known' as const, value: projected, evidence_ids: [ref.evidence_id] }] : [];
  });
  const error = refs.find(ref => ref.value.state === 'query_error');
  if (error) return error.value;
  if (new Set(observations.map(value => stableValue(value.value))).size > 1) return {
    state: 'unknown', reason: 'Fuentes contradictorias; consulte la evidencia original.', evidence_ids: observations.flatMap(value => value.evidence_ids),
  };
  return observations[0];
}

// A historical evaluation can have no independent assessment attempt by contract.
// Preserve that null in the displayed evidence, but compare its actual identity.
export function evaluationComparison(observation: Observation | undefined): Observation | undefined {
  if (observation?.state !== 'known' || !observation.value || typeof observation.value !== 'object' || Array.isArray(observation.value)) return observation;
  return {...observation, value: Object.fromEntries(Object.entries(observation.value).filter(([field, value]) => field !== 'source_assessment_attempt_id' || value !== null))};
}

export interface DetailField { label: string; values: (Observation | undefined)[] }

// Fields are compared before formatting. Missing and failed observations never prove equality.
export function classifyFields(fields: DetailField[]) {
  return fields.map(field => ({ ...field, ...compareValues(field.values) }));
}

export const evaluationFields = ['evaluation_role', 'purpose', 'threshold', 'sample_count', 'metric_definition',
  'protocol', 'decision', 'metrics_definition', 'protocol_hash', 'evaluation_id', 'checkpoint_artifact_id',
  'source_assessment_attempt_id', 'attempt_id', 'identity_id', 'identity_hash', 'attempt_state', 'batch_size'] as const;
export function evaluationDetails(data: PreflightResponse): DetailField[] {
  return evaluationFields.map(label => ({ label, values: data.selections.map(selection => evaluationField(data, selection.selection_id, label)) }));
}

export function openEvidenceTarget(target: HTMLElement | null) {
  if (!target) return;
  let ancestor: HTMLElement | null = target;
  while (ancestor) {
    if (ancestor.tagName === 'DETAILS') (ancestor as HTMLDetailsElement).open = true;
    ancestor = ancestor.parentElement;
  }
  target.scrollIntoView({ block: 'center' });
  target.focus({ preventScroll: true });
}

function evaluationField(data: PreflightResponse, selectionId: string, field: string): Observation | undefined {
  const projected = projectField(data, 'A6', selectionId, field);
  if (projected) return projected;
  const selection = data.selections.find(item => item.selection_id === selectionId)!;
  if (field === 'checkpoint_artifact_id') return selection.checkpoint;
  const identity = selection.evaluation;
  if (identity.state !== 'known') return identity;
  if (identity.value && typeof identity.value === 'object' && !Array.isArray(identity.value) && field in identity.value) {
    return { ...identity, value: identity.value[field] };
  }
  return undefined;
}
