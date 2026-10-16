import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import type { ExplainState } from '../types/explainGeneration';
import { groupXAIComparisons, XAI_METHODS, type XAIComparison, type XAIMethod } from '../components/reports/xai/comparison';

export function explainFailure(failure: unknown): string {
  let message = failure instanceof Error ? failure.message : 'No fue posible consultar EXPLAIN.';
  try {
    const parsed: unknown = JSON.parse(message);
    if (parsed && typeof parsed === 'object' && 'error' in parsed && parsed.error && typeof parsed.error === 'object'
        && 'message' in parsed.error && typeof parsed.error.message === 'string') message = parsed.error.message;
  } catch { /* The shared client can also return plain error messages. */ }
  if (message === 'GLOBAL_EXPERIMENT_BUSY') return 'Hay otra operación científica en ejecución. Reintenta cuando termine.';
  return message;
}

export function useExplainGeneration(comparison: XAIComparison, active?: boolean, onEvidenceChange?: () => void) {
  const evidenceCallback = useRef(onEvidenceChange);
  evidenceCallback.current = onEvidenceChange;
  const retained = useRef<{ key: string; running: boolean } | null>(null);
  const source = comparison.original?.attemptId;
  const sample = comparison.sampleId;
  const enabled = Boolean(source && sample && !comparison.comparabilityIssue && comparison.split === 'val' && comparison.purpose === 'development');
  const targetClass = comparison.targetClass ?? 1;
  const key = `${source}:${sample}:${targetClass}`;
  const current = useRef(key);
  current.current = key;
  const [state, setState] = useState<{key: string; value: ExplainState} | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const refresh = useCallback(async (signal?: AbortSignal) => {
    if (!source || !sample || !enabled) return;
    const value = await api.getExplainState(source, sample, signal, targetClass);
    if (signal?.aborted || current.current !== key) return;
    if (value.training_run_id !== comparison.trainingRunId || value.dataset_version_id !== comparison.datasetVersionId || value.sample_id !== sample) {
      throw new Error('La respuesta XAI no corresponde al contexto seleccionado.');
    }
    const running = value.methods.some(item => ['pending', 'running'].includes(item.state));
    const completed = retained.current?.key === key && retained.current.running && !running;
    retained.current = { key, running };
    if (completed) evidenceCallback.current?.();
    setState({key, value});
  }, [source, sample, enabled, key, comparison.trainingRunId, comparison.datasetVersionId, targetClass]);
  const running = state?.key === key && state.value.methods.some(item => ['pending', 'running'].includes(item.state));
  useEffect(() => {
    setError(null); setSubmitting(false);
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try { await refresh(controller.signal); }
      catch (failure: unknown) { if (!controller.signal.aborted) setError(explainFailure(failure)); }
      if (!controller.signal.aborted && enabled && active !== false && (active === undefined || retained.current?.running)) timer = setTimeout(() => { void poll(); }, 4000);
    };
    if (enabled && active !== false && (active === undefined || retained.current?.key !== key || retained.current.running)) void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [refresh, enabled, active, key, running]);
  const value = state?.key === key ? state.value : null;
  const execute = async (methods: XAIMethod[]) => {
    if (!enabled || !source || !sample || !value?.authorized || submitting) return;
    setSubmitting(true); setError(null);
    try {
      const response = await api.generateExplanation({source_attempt_id: source, sample_id: sample, methods, class_id: targetClass});
      if (current.current !== key) return;
      const failures = response.operations.filter(operation => operation.error);
      if (failures.length) setError(failures.map(operation => `${operation.method}: ${operation.error}`).join(' · '));
      await refresh();
      onEvidenceChange?.();
    } catch (failure: unknown) {
      if (current.current === key) setError(explainFailure(failure));
    } finally { if (current.current === key) setSubmitting(false); }
  };
  const updated: XAIComparison = {...comparison, methods: {...comparison.methods}};
  for (const method of value?.methods ?? []) {
    if (method.state === 'completed' && method.detail) {
      const rows = groupXAIComparisons([{detail: method.detail, artifacts: method.artifacts}], comparison.trainingRunId);
      const row = rows.find(row => row.sampleId === sample && !row.comparabilityIssue
        && row.checkpointArtifactId === comparison.checkpointArtifactId && row.modelVersionId === comparison.modelVersionId
        && row.datasetVersionId === comparison.datasetVersionId && row.split === comparison.split && row.purpose === comparison.purpose
        && (row.targetClass === undefined || row.targetClass === targetClass));
      if (row?.methods[method.method]) updated.methods[method.method] = row.methods[method.method];
    } else if (method.state !== 'not_executed') {
      updated.methods[method.method] = {method: method.method, execution: method.state,
        availability: 'no_evidence', attemptId: method.attempt_id, assessmentIdentityId: method.identity_id,
        message: method.error ?? undefined};
    }
  }
  const generation = Object.fromEntries(XAI_METHODS.map(method => [method, {
    authorized: Boolean(value?.authorized && enabled && !submitting && !value.methods.some(item => ['pending', 'running'].includes(item.state))),
    reason: submitting ? 'Preparando EXPLAIN…' : value?.methods.some(item => ['pending', 'running'].includes(item.state)) ? 'Hay una generación en curso.' : !enabled ? 'El contexto no admite generación EXPLAIN.' : !value ? 'Consultando disponibilidad…' : 'Permiso de generación requerido.',
    execute: async () => execute([method]),
  }]));
  return {comparison: updated, generation, error, submitting,
    canGenerate: Boolean(enabled && value?.authorized && !submitting && !value.methods.some(item => ['pending', 'running'].includes(item.state))),
    generateAll: () => execute([...XAI_METHODS])};
}
