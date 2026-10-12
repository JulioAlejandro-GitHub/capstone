import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { AssessmentDetail } from '../types/api';

interface AssessmentLoadState {
  attemptId: string | undefined;
  data: AssessmentDetail | null;
  error: string | null;
  loading: boolean;
}

export function useAssessment(attemptId: string | undefined) {
  const [state, setState] = useState<AssessmentLoadState>({
    attemptId, data: null, error: null, loading: true,
  });
  useEffect(() => {
    if (!attemptId) return;
    const controller = new AbortController();
    setState({ attemptId, data: null, error: null, loading: true });
    api.getAssessment(attemptId, controller.signal).then((data) => {
      if (controller.signal.aborted) return;
      if (data.id !== attemptId || data.kind !== 'evaluate') {
        setState({ attemptId, data: null, error: 'La respuesta no corresponde a la evaluación solicitada.', loading: false });
        return;
      }
      setState({ attemptId, data, error: null, loading: false });
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) {
        setState({ attemptId, data: null, error: error instanceof Error ? error.message : 'No fue posible cargar la evaluación.', loading: false });
      }
    });
    return () => controller.abort();
  }, [attemptId]);
  return state.attemptId === attemptId ? state : { data: null, error: null, loading: true };
}
