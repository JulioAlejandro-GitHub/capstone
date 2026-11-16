import { useCallback, useEffect, useRef, useState } from 'react';

import { ApiError, api, type SmearWorkflowResponse } from '../../../services/api';
import { isActivelyProcessing } from '../adapters/analysisModel';

export type ExistingAnalysisState =
  | { status: 'loading' }
  | { status: 'ready'; response: SmearWorkflowResponse; refreshing: boolean }
  | { status: 'unavailable'; reason: 'not_found' | 'forbidden' | 'error'; message: string };

const POLL_INTERVAL_MS = 5000;

const unavailableFrom = (error: unknown): ExistingAnalysisState => {
  if (error instanceof ApiError && error.status === 404) {
    return { status: 'unavailable', reason: 'not_found', message: 'El análisis solicitado no existe.' };
  }
  if (error instanceof ApiError && error.status === 403) {
    return {
      status: 'unavailable',
      reason: 'forbidden',
      message: 'Tu rol no autoriza la consulta de este análisis (scientific.analysis.read).',
    };
  }
  return {
    status: 'unavailable',
    reason: 'error',
    message: 'No fue posible recuperar el análisis. Verifica la conexión con el backend.',
  };
};

/**
 * Recupera un análisis persistido por `analysisId` usando exclusivamente el
 * contrato de lectura existente (`GET /scientific/analysis-history/:id`).
 * Nunca crea, reintenta ni modifica RUNs: abrir un análisis es una consulta.
 */
export function useExistingAnalysis(analysisId: string) {
  const [state, setState] = useState<ExistingAnalysisState>({ status: 'loading' });
  const requestRef = useRef(0);

  const load = useCallback((background: boolean) => {
    const request = ++requestRef.current;
    setState((current) => (
      background && current.status === 'ready'
        ? { ...current, refreshing: true }
        : { status: 'loading' }
    ));
    api.getSmearAnalysisHistoryDetail(analysisId)
      .then((response) => {
        if (request === requestRef.current) {
          setState({ status: 'ready', response, refreshing: false });
        }
      })
      .catch((error) => {
        if (request !== requestRef.current) return;
        // Un fallo durante un refresco en segundo plano conserva lo último recuperado.
        setState((current) => (
          background && current.status === 'ready'
            ? { ...current, refreshing: false }
            : unavailableFrom(error)
        ));
      });
  }, [analysisId]);

  useEffect(() => {
    load(false);
    return () => {
      requestRef.current += 1;
    };
  }, [load]);

  // Mientras el backend informa un proceso activo se refleja su estado real.
  const activeStage = state.status === 'ready' && isActivelyProcessing(state.response.stage);
  useEffect(() => {
    if (!activeStage) return undefined;
    const timer = window.setInterval(() => load(true), POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [activeStage, load]);

  const refresh = useCallback(() => load(true), [load]);
  return { state, refresh };
}
