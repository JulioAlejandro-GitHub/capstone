import { useEffect, useState } from 'react';

import { DataTable } from '../components/DataTable';
import { Loading } from '../components/Loading';
import { StatusBadge } from '../components/StatusBadge';
import { api } from '../services/api';
import type { RunDashboard } from '../types/api';
import { formatDate, formatMetric } from '../utils/format';

interface RunsProps {
  datasource: string;
  onRunSelect: (runId: string) => void;
}

export function Runs({ datasource, onRunSelect }: RunsProps) {
  const [runs, setRuns] = useState<RunDashboard[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    api
      .getRuns(datasource)
      .then((response) => setRuns(response.items))
      .catch((err: Error) => setError(err.message));
  }, [datasource]);

  if (error) return <section className="panel error">{error}</section>;
  if (!runs) return <Loading />;

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>Ejecuciones</h1>
          <p>Listado read-only de runs registrados por el tracking.</p>
        </div>
      </div>
      <section className="panel">
        <DataTable<RunDashboard>
          rows={runs}
          columns={[
            {
              header: 'Run',
              render: (row) => (
                <button className="link-button" onClick={() => onRunSelect(row.run_id)} type="button">
                  {row.run_name ?? row.run_id}
                </button>
              ),
            },
            { header: 'Tipo', render: (row) => row.run_type },
            { header: 'Estado', render: (row) => <StatusBadge status={row.status} /> },
            { header: 'Modelo', render: (row) => row.model_name ?? '-' },
            { header: 'Accuracy', render: (row) => formatMetric(row.accuracy) },
            { header: 'Recall', render: (row) => formatMetric(row.recall) },
            { header: 'F1', render: (row) => formatMetric(row.f1_score) },
            { header: 'AUC', render: (row) => formatMetric(row.auc) },
            { header: 'Inicio', render: (row) => formatDate(row.started_at) },
          ]}
        />
      </section>
    </section>
  );
}

