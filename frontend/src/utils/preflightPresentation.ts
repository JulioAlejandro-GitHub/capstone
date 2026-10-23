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
  let tab: HTMLElement | null = null;
  while (ancestor) {
    if (ancestor.tagName === 'DETAILS') (ancestor as HTMLDetailsElement).open = true;
    // A hidden tab panel is revealed through its own tab, so the owning component keeps the selection.
    if (ancestor.hidden && ancestor.getAttribute('role') === 'tabpanel') tab = document.getElementById(ancestor.getAttribute('aria-labelledby') ?? '') ?? tab;
    ancestor = ancestor.parentElement;
  }
  const reveal = () => { target.scrollIntoView({ block: 'center' }); target.focus({ preventScroll: true }); };
  if (tab) { tab.click(); requestAnimationFrame(reveal); } else reveal();
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

export interface MissingEvidence {
  evidence: string[]; selectionIds: string[]; cause: string; state: string;
  analyses: string[]; evidenceIds: string[]; errorIds: string[];
}
// Group only identical causes and states; retain the precise affected selections.
export function missingEvidence(data: PreflightResponse, fields: DetailField[]): MissingEvidence[] {
  const groups = new Map<string, MissingEvidence>();
  const add = (entry: MissingEvidence) => {
    const key = JSON.stringify([entry.state, entry.cause, [...entry.selectionIds].sort()]);
    const previous = groups.get(key);
    groups.set(key, previous ? { ...entry,
      evidence: [...new Set([...previous.evidence, ...entry.evidence])],
      analyses: [...new Set([...previous.analyses, ...entry.analyses])],
      evidenceIds: [...new Set([...previous.evidenceIds, ...entry.evidenceIds])],
      errorIds: [...new Set([...previous.errorIds, ...entry.errorIds])],
    } : entry);
  };
  for (const field of fields) field.values.forEach((value, index) => {
    if (value?.state === 'known' && completeValue(value.value)) return;
    const ids = value && 'evidence_ids' in value ? value.evidence_ids : [];
    const errors = value?.state === 'query_error' ? value.error_ids : [];
    add({ evidence: [field.label], selectionIds: [data.selections[index].selection_id],
      cause: value && 'reason' in value ? value.reason : errors.length ? errors.map(id => data.technical_errors.find(error => error.error_id === id)?.message ?? id).join('; ') : 'Dato no acreditado en la respuesta consultada.',
      state: value?.state === 'query_error' ? 'Error de consulta' : value?.state === 'not_checked' ? (field.label === 'Disponibilidad e integridad física del checkpoint' ? 'No verificado físicamente' : 'No verificado') : value?.state === 'not_applicable' ? 'No aplicable' : 'Evidencia insuficiente',
      analyses: data.analyses.filter(analysis => analysis.evidence_ids.some(id => ids.includes(id)) || analysis.verdict.error_ids.some(id => errors.includes(id))).map(analysis => analysis.analysis_id), evidenceIds: ids, errorIds: errors });
  });
  for (const result of [...data.dimensions, ...data.analyses]) for (const finding of result.findings) {
    if (finding.kind !== 'missing') continue;
    for (const selectionId of finding.affected_selection_ids.length ? finding.affected_selection_ids : ['']) add({ evidence: [finding.message], selectionIds: selectionId ? [selectionId] : [], cause: finding.condition,
      state: 'Evidencia insuficiente', analyses: data.analyses.filter(analysis => analysis.findings.some(item => item.reason_id === finding.reason_id)).map(analysis => analysis.analysis_id), evidenceIds: finding.evidence_ids, errorIds: [] });
  }
  for (const error of data.technical_errors) for (const selectionId of error.selection_ids.length ? error.selection_ids : ['']) add({ evidence: [error.operation], selectionIds: selectionId ? [selectionId] : [], cause: error.message, state: 'Error de consulta', analyses: data.analyses.filter(analysis => error.scope_ids.includes(analysis.scope.scope_id) || analysis.verdict.error_ids.includes(error.error_id)).map(analysis => analysis.analysis_id), evidenceIds: [], errorIds: [error.error_id] });
  return [...groups.values()];
}
