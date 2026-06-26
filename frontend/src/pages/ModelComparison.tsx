import { useEffect, useState } from 'react';

import { DataTable } from '../components/DataTable';
import { Loading } from '../components/Loading';
import { api } from '../services/api';
import type { ClinicalRunSummary, ModelSummary } from '../types/api';
import { formatDate, formatMetric } from '../utils/format';

interface ModelComparisonProps {
  datasource: string;
}

type SortKey =
  | 'f2_parasitized'
  | 'recall_parasitized'
  | 'specificity'
  | 'pr_auc_parasitized'
  | 'balanced_accuracy';

export function ModelComparison({ datasource }: ModelComparisonProps) {
  const [models, setModels] = useState<ModelSummary[] | null>(null);
  const [clinicalRows, setClinicalRows] = useState<ClinicalRunSummary[]>([]);
  const [sortKey, setSortKey] = useState<SortKey>('f2_parasitized');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    Promise.all([api.getModels(datasource), api.getClinicalModelComparison(datasource)])
      .then(([modelsResponse, clinicalResponse]) => {
        setModels(modelsResponse.items);
        setClinicalRows(clinicalResponse.items);
      })
      .catch((err: Error) => setError(err.message));
  }, [datasource]);

  if (error) return <section className="panel error">{error}</section>;
  if (!models) return <Loading />;

  const sortedClinicalRows = [...clinicalRows].sort(
    (a, b) => Number(b[sortKey] ?? -1) - Number(a[sortKey] ?? -1),
  );

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>Comparacion de modelos</h1>
          <p>Comparacion clinica experimental por run y resumen historico por modelo.</p>
        </div>
      </div>

      <section className="panel clinical-disclaimer">
        <strong>Comparacion responsable</strong>
        <p>
          No compares modelos si fueron evaluados con splits, preprocessing o thresholds
          distintos. La decision binaria usa probability_parasitized contra el threshold
          registrado.
        </p>
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>Comparacion clinica por run</h2>
          <label className="inline-control">
            Ordenar por
            <select value={sortKey} onChange={(event) => setSortKey(event.target.value as SortKey)}>
              <option value="f2_parasitized">F2-score</option>
              <option value="recall_parasitized">Recall parasitized</option>
              <option value="specificity">Specificity</option>
              <option value="pr_auc_parasitized">PR-AUC</option>
              <option value="balanced_accuracy">Balanced accuracy</option>
            </select>
          </label>
        </div>
        <DataTable<ClinicalRunSummary>
          rows={sortedClinicalRows}
          columns={[
            { header: 'Modelo', render: (row) => row.model_name ?? '-' },
            { header: 'Run ID', render: (row) => <code>{row.run_id}</code> },
            { header: 'Policy', render: (row) => row.checkpoint_policy ?? '-' },
            { header: 'Threshold source', render: (row) => row.threshold_source ?? '-' },
            { header: 'Recall parasitized', render: (row) => formatMetric(row.recall_parasitized) },
            { header: 'Specificity', render: (row) => formatMetric(row.specificity) },
            { header: 'F2', render: (row) => formatMetric(row.f2_parasitized) },
            { header: 'PR-AUC', render: (row) => formatMetric(row.pr_auc_parasitized) },
            { header: 'ROC-AUC', render: (row) => formatMetric(row.roc_auc_parasitized) },
            { header: 'Balanced acc.', render: (row) => formatMetric(row.balanced_accuracy) },
            {
              header: 'Collapse',
              render: (row) => row.prediction_collapse_detected === true ? 'Si' : row.prediction_collapse_detected === false ? 'No' : '-',
            },
          ]}
          getRowKey={(row) => row.run_id}
        />
      </section>

      <section className="panel">
        <h2>Resumen historico por modelo</h2>
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
