import { useEffect, useState } from 'react';

import { DataTable } from '../components/DataTable';
import { Loading } from '../components/Loading';
import { api } from '../services/api';
import type { ClinicalRunSummary } from '../types/api';
import { formatDate, formatMetric } from '../utils/format';

interface ClinicalEvaluationProps {
  datasource: string;
  onRunSelect: (runId: string) => void;
}

function collapseText(value: boolean | null | undefined) {
  if (value === true) return 'Si';
  if (value === false) return 'No';
  return '-';
}

export function ClinicalEvaluation({ datasource, onRunSelect }: ClinicalEvaluationProps) {
  const [rows, setRows] = useState<ClinicalRunSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    api
      .getClinicalModelComparison(datasource)
      .then((response) => setRows(response.items))
      .catch((err: Error) => setError(err.message));
  }, [datasource]);

  if (error) return <section className="panel error">{error}</section>;
  if (!rows) return <Loading />;

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>Evaluacion clinica</h1>
          <p>Auditoria de runs con metricas clinicas, threshold y checkpoint policy.</p>
        </div>
      </div>

      <section className="panel clinical-disclaimer">
        <strong>Sistema experimental de apoyo</strong>
        <p>
          La decision binaria usa probability_parasitized contra el threshold registrado.
          Convencion: 0 = uninfected, 1 = parasitized.
        </p>
      </section>

      <section className="panel">
        <DataTable<ClinicalRunSummary>
          rows={rows}
          columns={[
            {
              header: 'Run',
              render: (row) => (
                <button className="link-button" onClick={() => onRunSelect(row.run_id)} type="button">
                  {row.run_name ?? row.run_id}
                </button>
              ),
            },
            { header: 'Modelo', render: (row) => row.model_name ?? '-' },
            { header: 'Tipo', render: (row) => row.run_type ?? '-' },
            { header: 'F2', render: (row) => formatMetric(row.f2_parasitized) },
            { header: 'PR-AUC', render: (row) => formatMetric(row.pr_auc_parasitized) },
            { header: 'Recall parasitized', render: (row) => formatMetric(row.recall_parasitized) },
            { header: 'Specificity', render: (row) => formatMetric(row.specificity) },
            { header: 'Balanced acc.', render: (row) => formatMetric(row.balanced_accuracy) },
            { header: 'Threshold', render: (row) => formatMetric(row.threshold_used) },
            { header: 'Threshold source', render: (row) => row.threshold_source ?? '-' },
            { header: 'Policy', render: (row) => row.checkpoint_policy ?? '-' },
            { header: 'Collapse', render: (row) => collapseText(row.prediction_collapse_detected) },
            { header: 'Inicio', render: (row) => formatDate(row.started_at) },
          ]}
          getRowKey={(row) => row.run_id}
        />
      </section>
    </section>
  );
}
