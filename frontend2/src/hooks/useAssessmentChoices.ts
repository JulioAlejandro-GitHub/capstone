import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { AssessmentChoice } from '../types/api';

export function useAssessmentChoices(offset: number) {
  const [items, setItems] = useState<AssessmentChoice[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    api.getAssessments(offset, controller.signal).then(result => {
      if (!controller.signal.aborted) setItems(result.items);
    }).catch((cause: Error) => {
      if (!controller.signal.aborted) setError(cause.message);
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [offset]);
  return { items, loading, error };
}
