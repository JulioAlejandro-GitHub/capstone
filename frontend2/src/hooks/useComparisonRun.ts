import { useEffect, useState } from 'react';
import { ApiError, api } from '../services/api';
import type { RunRecord } from '../types/api';

export function useComparisonRun(datasource: string, id: string) {
  const [run, setRun] = useState<RunRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    setRun(null);
    setError(null);
    api.getRun(datasource, id).then(data => {
      if (!active) return;
      if (data.run.id !== id || data.run.run_type !== 'training') {
        setError('TRAIN no disponible');
      } else setRun(data.run);
    }).catch((cause: Error) => {
      if (active) setError(cause instanceof ApiError && cause.status === 404
        ? 'TRAIN eliminado o no disponible' : cause.message);
    });
    return () => { active = false; };
  }, [datasource, id, revision]);
  return { run, error, retry: () => setRevision(value => value + 1) };
}
