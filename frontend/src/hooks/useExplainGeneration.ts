import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import type { ExplainState } from '../types/explainGeneration';
import { groupXAIComparisons, XAI_METHODS, type XAIComparison, type XAIMethod } from '../components/reports/xai/comparison';

export const executorUnavailable = 'Agente de GPU no activo. Inícialo en el host con scripts/host_services.sh start explain.';

export function explainFailure(failure: unknown): string {
  let message = failure instanceof Error ? failure.message : 'No fue posible consultar EXPLAIN.';
  try {
    const parsed: unknown = JSON.parse(message);
    if (parsed && typeof parsed === 'object' && 'error' in parsed && parsed.error && typeof parsed.error === 'object'
        && 'message' in parsed.error && typeof parsed.error.message === 'string') message = parsed.error.message;
  } catch { /* The shared client can also return plain error messages. */ }
  if (message === 'GLOBAL_EXPERIMENT_BUSY') return 'Hay otra operación científica en ejecución. Reintenta cuando termine.';
  if (message === 'EXPLAIN_HOST_EXECUTOR_UNAVAILABLE') return executorUnavailable;
  return message;
}

// lazy: the state query (it verifies the whole EXPLAIN population) starts only after a request; until then
// missing methods come from the persisted comparison and authorization from the user's permission.
// blocked: an external precondition (no GPU agent) that overrides any authorization.
export function useExplainGeneration(comparison: XAIComparison, active?: boolean, onEvidenceChange?: () => void, options: {lazy?: boolean; authorized?: boolean; blocked?: string | null} = {}) {
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
  const [started, setStarted] = useState<string | null>(null);
  // Methods requested from this screen are shown as in flight from the click until the backend state confirms them.
  const [requested, setRequested] = useState<{key: string; methods: XAIMethod[]} | null>(null);
  // Synchronous guard: a second click can arrive before React re-renders the disabled button.
  const locked = useRef(false);
  const polling = !options.lazy || started === key;
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
  useEffect(() => { setError(null); setSubmitting(false); setRequested(null); locked.current = false; }, [key]);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try { await refresh(controller.signal); }
      catch (failure: unknown) { if (!controller.signal.aborted) setError(explainFailure(failure)); }
      if (!controller.signal.aborted && enabled && active !== false && (active === undefined || retained.current?.running)) timer = setTimeout(() => { void poll(); }, 4000);
    };
    if (polling && enabled && active !== false && (active === undefined || retained.current?.key !== key || retained.current.running)) void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [refresh, enabled, active, key, running, polling]);
  const value = state?.key === key ? state.value : null;
  const authorized = !options.blocked && (value ? value.authorized : Boolean(options.lazy && options.authorized));
  const execute = async (methods: XAIMethod[]) => {
    if (locked.current || !enabled || !source || !sample || !authorized || submitting) return;
    locked.current = true;
    setSubmitting(true); setError(null); setStarted(key); setRequested({key, methods});
    try {
      const response = await api.generateExplanation({source_attempt_id: source, sample_id: sample, methods, class_id: targetClass});
      if (current.current !== key) return;
      const failures = response.operations.filter(operation => operation.error);
      if (failures.length) setError(failures.map(operation => `${operation.method}: ${operation.error}`).join(' · '));
      await refresh();
      onEvidenceChange?.();
    } catch (failure: unknown) {
      if (current.current === key) setError(explainFailure(failure));
    } finally {
      // From here the backend state (pending/running) keeps the methods locked.
      if (current.current === key) { setSubmitting(false); setRequested(null); }
      locked.current = false;
    }
  };
  const updated: XAIComparison = {...comparison, methods: {...comparison.methods}};
  for (const method of value?.methods ?? []) {
    // Persisted evidence already on screen is never replaced by the state projection.
    if (comparison.methods[method.method]?.artifact) continue;
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
    authorized: Boolean(authorized && enabled && !submitting && !value?.methods.some(item => ['pending', 'running'].includes(item.state))),
    reason: options.blocked ? options.blocked : submitting ? 'Preparando EXPLAIN…' : value?.methods.some(item => ['pending', 'running'].includes(item.state)) ? 'Hay una generación en curso.' : !enabled ? 'El contexto no admite generación EXPLAIN.' : !value && !options.lazy ? 'Consultando disponibilidad…' : 'Permiso de generación requerido.',
    execute: async () => execute([method]),
  }]));
  // Only methods without evidence or a live execution are requested; the worker re-checks reuse under the global gate.
  const asked = requested?.key === key ? requested.methods : [];
  const missing = XAI_METHODS.filter(method => !updated.methods[method]?.artifact && !asked.includes(method) && !['pending', 'running', 'completed'].includes(updated.methods[method]?.execution ?? 'not_executed'));
  const inFlight = XAI_METHODS.filter(method => !updated.methods[method]?.artifact && (['pending', 'running'].includes(updated.methods[method]?.execution ?? 'not_executed')
    || (asked.includes(method) && !['completed', 'failed'].includes(updated.methods[method]?.execution ?? 'not_executed'))));
  return {comparison: updated, generation, error, submitting, missing, inFlight,
    canGenerate: Boolean(enabled && authorized && !submitting && missing.length && !value?.methods.some(item => ['pending', 'running'].includes(item.state))),
    generateAll: () => missing.length ? execute(missing) : Promise.resolve()};
}
