import { useEffect, useMemo, useState } from 'react';

import { api } from '../../services/api';
import type { ActivationTrace, ActivationTraceCatalog } from '../../types/activationTrace';
import type { AssessmentDetail } from '../../types/api';
import { cellComparison } from '../reports/AssessmentXAI';
import type { XAIComparison } from '../reports/xai/comparison';
import { cellCategory, tracePng, type TrainingCell } from './cellModel';

export { CELL_CATEGORY_LABELS, cellCategory, classText, type TrainingCell } from './cellModel';

/**
 * Célula seleccionada: uno de los recorridos de activación guardados del TRAIN (GET /runs/{id}/activation-traces).
 * Abre la de la URL (`muestra`) o, si no está, la más reciente, igual que Arquitectura del modelo.
 * Para «Ampliar comparación» lee el contexto EVALUATE del recorrido (GET /assessments/{attempt_id}).
 */
export function useTrainingCell(datasource: string, runId: string, requested: string | null) {
  const [catalog, setCatalog] = useState<ActivationTraceCatalog | null>(null);
  const [trace, setTrace] = useState<ActivationTrace | null>(null);
  const [context, setContext] = useState<AssessmentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [contextError, setContextError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setCatalog(null); setError(null);
    api.getActivationTraces(datasource, runId, controller.signal).then(setCatalog)
      .catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'No fue posible consultar las células.'); });
    return () => controller.abort();
  }, [datasource, runId]);

  const sampleId = catalog?.items.find(item => item.sample_id === requested)?.sample_id ?? catalog?.items[0]?.sample_id ?? null;
  useEffect(() => {
    setTrace(null);
    if (!sampleId) return;
    const controller = new AbortController();
    api.getActivationTrace(runId, sampleId, controller.signal).then(value => { if (!controller.signal.aborted) setTrace(value); })
      .catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'No fue posible abrir la célula.'); });
    return () => controller.abort();
  }, [runId, sampleId]);

  const attemptId = trace?.attempt_id ?? null;
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

  const cell = useMemo<TrainingCell | null>(() => trace ? {
    sampleId: trace.sample_id, image: tracePng(trace.input_image), label: trace.label, predicted: trace.predicted, score: trace.score,
    threshold: trace.threshold, split: trace.split, attemptId: trace.attempt_id, category: cellCategory(trace),
  } : null, [trace]);

  // La misma comparación que Explicabilidad, con el resultado del recorrido (clase real, predicción, score y umbral).
  const comparison = useMemo<XAIComparison | null>(() => {
    if (!context || !trace) return null;
    const base = cellComparison(context, trace.sample_id);
    return trace.label != null && trace.predicted != null && trace.threshold != null
      ? { ...base, outcome: { label: trace.label, predicted: trace.predicted, score: trace.score, threshold: trace.threshold, split: trace.split, attemptId: trace.attempt_id } }
      : base;
  }, [context, trace]);

  return { catalog, cell, comparison, sampleId, error, contextError, loading: Boolean(!error && (!catalog || (sampleId && !trace))) };
}
