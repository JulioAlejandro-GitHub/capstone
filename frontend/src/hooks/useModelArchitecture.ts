import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { ModelArchitecture } from '../types/modelArchitecture';

export function useModelArchitecture(datasource: string, runId: string | null) {
  const [data, setData] = useState<ModelArchitecture | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    setData(null);
    setError(null);
    if (!runId) return;
    const controller = new AbortController();
    api.getModelArchitecture(datasource, runId, controller.signal)
      .then(response => { if (!controller.signal.aborted) setData(response); })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'No fue posible cargar la arquitectura.');
      });
    return () => controller.abort();
  }, [datasource, runId, revision]);
  return { data, error, loading: Boolean(runId && !data && !error), retry: () => setRevision(value => value + 1) };
}
