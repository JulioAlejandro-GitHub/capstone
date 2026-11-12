import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { AssessmentArtifact } from '../types/api';

export function useAssessmentArtifacts(attemptId: string, offset: number) {
  const [state, setState] = useState<{attemptId: string; offset: number; items: AssessmentArtifact[]; loading: boolean; error: string | null}>({attemptId, offset, items: [], loading: true, error: null});
  useEffect(() => {
    const controller = new AbortController();
    setState({attemptId, offset, items: [], loading: true, error: null});
    api.getAssessmentArtifacts(attemptId, offset, controller.signal).then(({items}) => {
      if (!controller.signal.aborted) setState({attemptId, offset, items, loading: false, error: null});
    }).catch(() => {
      if (!controller.signal.aborted) setState({attemptId, offset, items: [], loading: false, error: 'No fue posible cargar las referencias de artefactos.'});
    });
    return () => controller.abort();
  }, [attemptId, offset]);
  return state.attemptId === attemptId && state.offset === offset
    ? state : {items: [], loading: true, error: null};
}
