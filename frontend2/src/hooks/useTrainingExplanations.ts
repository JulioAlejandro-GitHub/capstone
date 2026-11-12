import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { AssessmentExplanationChild } from '../types/api';

export function useTrainingExplanations(trainingRunId: string | null, datasource: string, version = 0) {
  const key = `${datasource}:${trainingRunId}:${version}`;
  const [state, setState] = useState<{
    key: string; items: AssessmentExplanationChild[]; loading: boolean; error: string | null;
  }>({key, items: [], loading: Boolean(trainingRunId), error: null});
  useEffect(() => {
    if (!trainingRunId) return;
    const controller = new AbortController();
    setState({key, items: [], loading: true, error: null});
    const parentId = trainingRunId;
    async function load() {
      const items: AssessmentExplanationChild[] = [];
      let offset = 0;
      while (!controller.signal.aborted) {
        const page = await api.getTrainingLineageChildren({trainingRunId: parentId, datasource, offset, limit: 100, signal: controller.signal});
        if (controller.signal.aborted) return;
        if (page.training_run_id !== trainingRunId) throw new Error('El linaje no corresponde al TRAIN solicitado.');
        for (const child of page.explainabilities) {
          if (child.source_kind !== 'assessment_explain_e6') continue;
          if (child.training_run_id !== trainingRunId) throw new Error('El intento no pertenece al TRAIN solicitado.');
          items.push(child);
        }
        if (!page.truncated) break;
        const count = page.evaluations.length + page.explainabilities.length;
        if (!count) throw new Error('No fue posible completar la consulta de linaje.');
        offset += count;
      }
      if (!controller.signal.aborted) setState({key, items, loading: false, error: null});
    }
    void load().catch((error: unknown) => {
      if (!controller.signal.aborted) setState({key, items: [], loading: false,
        error: error instanceof Error ? error.message : 'No fue posible cargar los intentos EXPLAIN.'});
    });
    return () => controller.abort();
  }, [trainingRunId, datasource, key]);
  return state.key === key ? state : {items: [], loading: Boolean(trainingRunId), error: null};
}
