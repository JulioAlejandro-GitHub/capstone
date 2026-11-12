import { useEffect, useState } from 'react';

import { ApiError, api, type SmearWorkflowResponse } from '../services/api';

export function useSmearAnalysisHistoryDetail(analysisRunId: string) {
  const [data, setData] = useState<SmearWorkflowResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    setData(null);
    api.getSmearAnalysisHistoryDetail(analysisRunId)
      .then((response) => {
        if (active) setData(response);
      })
      .catch((reason) => {
        if (!active) return;
        setError(
          reason instanceof ApiError && reason.status === 404
            ? 'El análisis histórico solicitado no existe.'
            : 'No fue posible recuperar el análisis histórico.',
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [analysisRunId]);

  return { data, loading, error };
}
