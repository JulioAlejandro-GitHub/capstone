import { useEffect, useState } from 'react';

import { DataTable } from '../components/DataTable';
import { Loading } from '../components/Loading';
import { api } from '../services/api';
import type { ModelSummary } from '../types/api';
import { formatDate, formatMetric } from '../utils/format';

interface ModelComparisonProps {
  datasource: string;
}

export function ModelComparison({ datasource }: ModelComparisonProps) {
  const [models, setModels] = useState<ModelSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    api
      .getModels(datasource)
      .then((response) => setModels(response.items))
      .catch((err: Error) => setError(err.message));
  }, [datasource]);

  if (error) return <section className="panel error">{error}</section>;
  if (!models) return <Loading />;

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>Comparacion de modelos</h1>
          <p>Resumen por modelo desde `vw_model_run_summary`.</p>
        </div>
      </div>
      <section className="panel">
        <DataTable<ModelSummary>
          rows={models}
          columns={[
            { header: 'Modelo', render: (row) => row.model_name },
            { header: 'Tipo', render: (row) => row.model_type },
            { header: 'Framework', render: (row) => row.framework ?? '-' },
            { header: 'Runs', render: (row) => row.total_runs },
            { header: 'Completadas', render: (row) => row.completed_runs },
            { header: 'Fallidas', render: (row) => row.failed_runs },
            { header: 'Accuracy', render: (row) => formatMetric(row.best_accuracy) },
            { header: 'Recall', render: (row) => formatMetric(row.best_recall) },
            { header: 'F1', render: (row) => formatMetric(row.best_f1_score) },
            { header: 'AUC', render: (row) => formatMetric(row.best_auc) },
            { header: 'Ultimo run', render: (row) => formatDate(row.last_run_at) },
          ]}
        />
      </section>
    </section>
  );
}
