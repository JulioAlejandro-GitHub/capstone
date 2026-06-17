import { useEffect, useState } from 'react';

import { DataTable } from '../components/DataTable';
import { DomainBadge } from '../components/DomainBadge';
import { Loading } from '../components/Loading';
import { MetricCard } from '../components/MetricCard';
import { StatusBadge } from '../components/StatusBadge';
import { api } from '../services/api';
import type { DashboardSummary, RunDashboard } from '../types/api';
import { formatDate, formatMetric } from '../utils/format';

interface DashboardProps {
  datasource: string;
  onRunSelect: (runId: string) => void;
}

export function Dashboard({ datasource, onRunSelect }: DashboardProps) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    api
      .getDashboardSummary(datasource)
      .then(setSummary)
      .catch((err: Error) => setError(err.message));
  }, [datasource]);

  if (error) return <section className="panel error">{error}</section>;
  if (!summary) return <Loading />;

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>Dashboard general</h1>
          <p>Resumen de ejecuciones, modelos y metricas del datasource activo.</p>
        </div>
        <DomainBadge domain={summary.domain} />
      </div>

      <div className="metrics-grid">
        <MetricCard label="Total ejecuciones" value={summary.totals.total_runs} />
        <MetricCard label="Completadas" value={summary.totals.completed_runs} />
        <MetricCard label="Fallidas" value={summary.totals.failed_runs} />
        <MetricCard label="Mejor accuracy" value={formatMetric(summary.best_metrics.best_accuracy)} />
        <MetricCard label="Mejor recall" value={formatMetric(summary.best_metrics.best_recall)} />
        <MetricCard label="Mejor F1" value={formatMetric(summary.best_metrics.best_f1_score)} />
        <MetricCard label="Mejor AUC" value={formatMetric(summary.best_metrics.best_auc)} />
      </div>

      <div className="grid-two">
        <section className="panel">
          <h2>Ejecuciones por modelo</h2>
          <DataTable
            rows={summary.runs_by_model}
            columns={[
              { header: 'Modelo', render: (row) => row.model_name },
              { header: 'Tipo', render: (row) => row.model_type },
              { header: 'Runs', render: (row) => row.total_runs },
              { header: 'Accuracy', render: (row) => formatMetric(row.best_accuracy) },
              { header: 'AUC', render: (row) => formatMetric(row.best_auc) },
            ]}
          />
        </section>

        <section className="panel">
          <h2>Dominios preparados</h2>
          <div className="domain-list">
            {summary.domains.map((item) => (
              <div key={item.key}>
                <DomainBadge domain={item.domain} />
                <span>{item.key}</span>
                <small>{item.enabled ? 'activo' : 'inactivo'}</small>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="panel">
        <h2>Ejecuciones recientes</h2>
        <DataTable<RunDashboard>
          rows={summary.recent_runs}
          columns={[
            {
              header: 'Run',
              render: (row) => (
                <button className="link-button" onClick={() => onRunSelect(row.run_id)} type="button">
                  {row.run_name ?? row.run_id}
                </button>
              ),
            },
            { header: 'Estado', render: (row) => <StatusBadge status={row.status} /> },
            { header: 'Modelo', render: (row) => row.model_name ?? '-' },
            { header: 'Accuracy', render: (row) => formatMetric(row.accuracy) },
            { header: 'AUC', render: (row) => formatMetric(row.auc) },
            { header: 'Inicio', render: (row) => formatDate(row.started_at) },
          ]}
        />
      </section>
    </section>
  );
}

