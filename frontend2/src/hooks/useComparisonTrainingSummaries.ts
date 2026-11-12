import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { TrainingSummaryCollection } from '../types/api';

// The selector stays mounted after closing, retaining the read-only report response.
export function useComparisonTrainingSummaries(datasource: string, enabled: boolean) {
  const [summaries, setSummaries] = useState<TrainingSummaryCollection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    setSummaries(null);
    setError(null);
    const timer = window.setTimeout(() => {
      api.getTrainingSummaries({ datasource, limit: 500, signal: controller.signal })
        .then(data => { if (!controller.signal.aborted) setSummaries(data); })
        .catch((cause: unknown) => {
          if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'No fue posible cargar las ejecuciones.');
        });
    }, 0);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [datasource, enabled, revision]);
  return { summaries, error, retry: () => setRevision(value => value + 1) };
}
