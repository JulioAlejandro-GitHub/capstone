import { useEffect, useState } from 'react';

import { DataTable } from '../components/DataTable';
import { DomainBadge } from '../components/DomainBadge';
import { Loading } from '../components/Loading';
import { MetricCard } from '../components/MetricCard';
import { StatusBadge } from '../components/StatusBadge';
import { api } from '../services/api';
import type { ClinicalDashboard, DashboardSummary, RunDashboard } from '../types/api';
import { formatDate, formatMetric } from '../utils/format';

interface DashboardProps {
  datasource: string;
  onRunSelect: (runId: string) => void;
}

export function Dashboard({ datasource, onRunSelect }: DashboardProps) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [clinical, setClinical] = useState<ClinicalDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    Promise.all([api.getDashboardSummary(datasource), api.getClinicalDashboard(datasource)])
      .then(([dashboardSummary, clinicalSummary]) => {
        setSummary(dashboardSummary);
        setClinical(clinicalSummary);
      })
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

      <section className="panel">
        <div className="section-heading">
          <h2>Dashboard clinico</h2>
          <span>Sistema experimental de apoyo</span>
        </div>
        {clinical?.latest_run ? (
          <>
            <div className="metrics-grid">
              <MetricCard label="Ultimo modelo" value={clinical.latest_run.model_name ?? '-'} />
              <MetricCard label="Estado" value={clinical.latest_run.status ?? '-'} />
              <MetricCard label="F2 parasitized" value={formatMetric(clinical.latest_run.f2_parasitized)} />
              <MetricCard label="PR-AUC parasitized" value={formatMetric(clinical.latest_run.pr_auc_parasitized)} />
              <MetricCard label="Recall parasitized" value={formatMetric(clinical.latest_run.recall_parasitized)} />
              <MetricCard label="Specificity" value={formatMetric(clinical.latest_run.specificity)} />
              <MetricCard label="Balanced accuracy" value={formatMetric(clinical.latest_run.balanced_accuracy)} />
              <MetricCard label="Threshold used" value={formatMetric(clinical.latest_run.threshold_used)} />
            </div>
            <div className="facts-grid dashboard-clinical-facts">
              <span>Checkpoint policy <strong>{clinical.latest_run.checkpoint_policy ?? '-'}</strong></span>
              <span>Threshold source <strong>{clinical.latest_run.threshold_source ?? '-'}</strong></span>
              <span>Prediction collapse <strong>{clinical.latest_run.prediction_collapse_detected === true ? 'Si' : clinical.latest_run.prediction_collapse_detected === false ? 'No' : '-'}</strong></span>
            </div>
            {clinical.warnings.length > 0 ? (
              <div className="warning-list">
                {clinical.warnings.map((warning, index) => (
                  <button
                    key={`${warning.run_id}-${warning.type}-${index}`}
                    type="button"
                    className="warning-item"
                    onClick={() => warning.run_id && onRunSelect(warning.run_id)}
                  >
                    <strong>{warning.type}</strong>
                    <span>{warning.message}</span>
                  </button>
                ))}
              </div>
            ) : null}
          </>
        ) : (
          <p className="muted-text">No hay runs clinicos registrados todavia.</p>
        )}
      </section>

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
