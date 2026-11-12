import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { ScientificModelCatalog } from '../types/scientificRead';

export function useComparisonCatalog(datasource: string) {
  const [catalog, setCatalog] = useState<ScientificModelCatalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    setCatalog(null);
    setError(null);
    api.getScientificModels(datasource, true).then(data => {
      if (active) setCatalog(data);
    }).catch((cause: Error) => { if (active) setError(cause.message); });
    return () => { active = false; };
  }, [datasource, revision]);
  return { catalog, error, retry: () => setRevision(value => value + 1) };
}
