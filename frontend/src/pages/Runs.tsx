import { useEffect, useState } from 'react';

import { Loading } from '../components/Loading';
import { RunSummaryRow } from '../components/reports/RunSummaryRow';
import { api } from '../services/api';
import type { RunDashboard } from '../types/api';
import '../styles/report-components.css';

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
      <section className="panel report-panel">
        {runs.length === 0 ? (
          <div className="report-empty">Sin ejecuciones registradas</div>
        ) : (
          <div
            aria-label="Resumen de ejecuciones"
            aria-rowcount={runs.length + 1}
            className="report-table"
            role="table"
          >
            <div className="report-table__header" role="row">
              <span className="report-section-title" role="columnheader">RUN</span>
              <span className="report-section-title" role="columnheader">Modelo</span>
              <span className="report-section-title" role="columnheader">Resultados</span>
              <span className="report-section-title" role="columnheader">Análisis automático</span>
            </div>
            {runs.map((run) => (
              <RunSummaryRow key={run.run_id} run={run} onRunSelect={onRunSelect} />
            ))}
          </div>
        )}
      </section>
    </section>
  );
}
