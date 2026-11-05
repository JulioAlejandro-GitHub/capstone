import { useCallback, useEffect, useMemo, useState } from 'react';

import { api } from '../../services/api';
import type { AssessmentDetail } from '../../types/api';
import { cellComparison } from './AssessmentXAI';
import type { XAIComparison } from './xai/comparison';

/** The part of a saved cell (activation trace) that «Vista ampliada» needs: its EVALUATE attempt and its result. */
export interface CellOutcomeSource {
  sample_id: string; attempt_id: string; split: string;
  label: number | null; predicted: number | null; score: number; threshold: number | null;
}

/**
 * «Vista ampliada» of a cell: the same comparison as Explicabilidad, read from the EVALUATE that produced the cell
 * (GET /assessments/{attempt_id}) and completed with its outcome (real class, prediction, score and threshold).
 */
export function useCellComparison(runId: string, cell: CellOutcomeSource | null) {
  const [context, setContext] = useState<AssessmentDetail | null>(null);
  const [contextError, setContextError] = useState<string | null>(null);
  const attemptId = cell?.attempt_id ?? null;

  useEffect(() => {
    setContext(null); setContextError(null);
    if (!attemptId) return;
    const controller = new AbortController();
    api.getExplainContext(attemptId, controller.signal).then(value => {
      if (controller.signal.aborted) return;
      if (value.id !== attemptId || value.training_run_id !== runId) setContextError('El contexto de la célula no corresponde a este TRAIN.');
      else setContext(value);
    }).catch((cause: unknown) => { if (!controller.signal.aborted) setContextError(cause instanceof Error ? cause.message : 'Contexto no disponible.'); });
    return () => controller.abort();
  }, [attemptId, runId]);

  const comparison = useMemo<XAIComparison | null>(() => {
    if (!context || !cell) return null;
    const base = cellComparison(context, cell.sample_id);
    return cell.label != null && cell.predicted != null && cell.threshold != null
      ? { ...base, outcome: { label: cell.label, predicted: cell.predicted, score: cell.score, threshold: cell.threshold, split: cell.split, attemptId: cell.attempt_id } }
      : base;
  }, [context, cell]);

  return { comparison, contextError, loading: Boolean(attemptId && !context && !contextError) };
}

/**
 * Click on a cell image → «Vista ampliada». A click that arrives before the comparison is ready is kept and opens the
 * view as soon as it is; each new value of `signal` opens it (XAIComparisonViewer `expandSignal`).
 */
export function useExpandRequest(ready: boolean) {
  const [signal, setSignal] = useState(0);
  const [pending, setPending] = useState(false);
  useEffect(() => {
    if (ready && pending) { setPending(false); setSignal(value => value + 1); }
  }, [ready, pending]);
  const request = useCallback(() => { if (ready) setSignal(value => value + 1); else setPending(true); }, [ready]);
  return { signal, request, pending };
}
