import { useEffect, useState } from 'react';

import { DataTable } from '../components/DataTable';
import { Loading } from '../components/Loading';
import { api } from '../services/api';
import type { ExplainabilityRow, JsonRecord } from '../types/api';
import { formatMetric } from '../utils/format';

interface ExplainabilityProps {
  datasource: string;
}

export function Explainability({ datasource }: ExplainabilityProps) {
  const [summary, setSummary] = useState<JsonRecord[]>([]);
  const [items, setItems] = useState<ExplainabilityRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    api
      .getExplainability(datasource)
      .then((response) => {
        setSummary(response.summary);
        setItems(response.items);
      })
      .catch((err: Error) => setError(err.message));
  }, [datasource]);

  if (error) return <section className="panel error">{error}</section>;
  if (!items) return <Loading />;

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>Explicabilidad</h1>
          <p>Resultados Grad-CAM, LIME y SHAP registrados en PostgreSQL.</p>
        </div>
      </div>

      <section className="panel">
        <h2>Resumen</h2>
        <DataTable
          rows={summary}
          columns={[
            { header: 'Run', render: (row) => String(row.run_name ?? row.run_id ?? '-') },
            { header: 'Modelo', render: (row) => String(row.model_name ?? '-') },
            { header: 'Metodo', render: (row) => String(row.method ?? '-') },
            { header: 'Total', render: (row) => String(row.total_explanations ?? 0) },
            { header: 'Exitosas', render: (row) => String(row.successful_explanations ?? 0) },
            { header: 'Fallidas', render: (row) => String(row.failed_explanations ?? 0) },
          ]}
        />
      </section>

      <section className="panel">
        <h2>Imagenes y casos</h2>
        <div className="artifact-grid">
          {items.map((item) => (
            <article key={item.id} className="artifact-card">
              <strong>{item.method}</strong>
              <small>{item.model_name ?? item.run_name ?? item.run_id}</small>
              <span>{item.case_type ?? '-'} / score {formatMetric(item.score)}</span>
              <span>{item.true_label ?? '-'} {'->'} {item.predicted_label ?? '-'}</span>
              {item.output_path ? (
                <img src={api.artifactUrl(item.output_path)} alt={`${item.method} ${item.id}`} />
              ) : null}
              {item.error_message ? <p className="error-text">{item.error_message}</p> : null}
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}
